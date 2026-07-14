import asyncio
import imaplib
import email
import re
import time
import os
import random
import string
from patchright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
from playwright_stealth import Stealth
from browser_helper import get_browser_path

# Import các bước đăng ký từ thư mục steps
from steps import step_email, step_intent, step_register, step_otp, step_verify_device, step_captcha

def generate_random_password(length=12):
    """Sinh mật khẩu ngẫu nhiên mạnh gồm chữ hoa, chữ thường, số và ký tự đặc biệt."""
    # Đảm bảo mật khẩu có đủ các loại ký tự
    lower = string.ascii_lowercase
    upper = string.ascii_uppercase
    digits = string.digits
    special = "!@#$%^&*"
    
    password = [
        random.choice(lower),
        random.choice(upper),
        random.choice(digits),
        random.choice(special)
    ]
    
    all_chars = lower + upper + digits + special
    for _ in range(length - 4):
        password.append(random.choice(all_chars))
        
    random.shuffle(password)
    return "".join(password)

def generate_random_name():
    """Sinh tên tiếng Anh ngẫu nhiên."""
    first_names = ["James", "John", "Robert", "Michael", "William", "David", "Richard", "Joseph", "Thomas", "Charles",
                   "Mary", "Patricia", "Jennifer", "Linda", "Elizabeth", "Barbara", "Susan", "Jessica", "Sarah", "Karen",
                   "Rebecca", "Lisa", "Amy", "Casey", "Ryan", "Mark", "Elizabeth", "Rebecca", "Rachel", "Emily"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Miller", "Davis", "Garcia", "Rodriguez", "Wilson",
                  "Martinez", "Anderson", "Taylor", "Thomas", "Hernandez", "Moore", "Martin", "Jackson", "Thompson", "White",
                  "Wong", "Marks", "Mercer", "Ward", "Hernandez", "Patton", "Johnson"]
    return f"{random.choice(first_names)} {random.choice(last_names)}"

def fetch_otp_from_email(email_addr, email_pass, log_func, timeout_sec=90):
    """
    Kết nối IMAP để lấy mã OTP từ hòm thư Hotmail/Outlook.
    Trả về: chuỗi OTP 6 chữ số hoặc None nếu thất bại.
    """
    log_func(f"Đang kiểm tra hòm thư {email_addr} qua IMAP...")
    start_time = time.time()
    
    import socket
    while time.time() - start_time < timeout_sec:
        try:
            import ssl
            socket.setdefaulttimeout(15)
            # Tạo context TLS v1.2 để tránh lỗi handshake timeout
            context = ssl.create_default_context()
            context.minimum_version = ssl.TLSVersion.TLSv1_2
            context.maximum_version = ssl.TLSVersion.TLSv1_2
            
            # Kết nối tới IMAP Office365 sử dụng context TLS v1.2
            mail = imaplib.IMAP4_SSL("outlook.office365.com", 993, ssl_context=context)
            # Cài đặt timeout ngắn để không bị treo
            mail.socket().settimeout(10)
            
            mail.login(email_addr, email_pass)
            mail.select("inbox")
            
            # Tìm email từ amazon.co.jp hoặc chứa OTP
            status, messages = mail.search(None, '(FROM "amazon.co.jp")')
            if status == "OK" and messages[0]:
                mail_ids = messages[0].split()
                # Kiểm tra các email mới nhận trước (ở cuối danh sách)
                for mail_id in reversed(mail_ids):
                    status, msg_data = mail.fetch(mail_id, "(RFC822)")
                    if status == "OK":
                        raw_email = msg_data[0][1]
                        msg = email.message_from_bytes(raw_email)
                        
                        # Lấy nội dung email
                        body = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                content_type = part.get_content_type()
                                if content_type in ["text/plain", "text/html"]:
                                    payload = part.get_payload(decode=True)
                                    if payload:
                                        body += payload.decode('utf-8', errors='ignore')
                        else:
                            payload = msg.get_payload(decode=True)
                            if payload:
                                body = payload.decode('utf-8', errors='ignore')
                                
                        # Tìm mã OTP 6 chữ số
                        # Tìm mẫu dạng: verification code hoặc OTP, và lấy 6 chữ số
                        otp_match = re.search(r'\b(\d{6})\b', body)
                        if otp_match:
                            otp = otp_match.group(1)
                            log_func(f"Đã tự động tìm thấy OTP: {otp}")
                            try:
                                mail.close()
                                mail.logout()
                            except:
                                pass
                            return otp
            
            try:
                mail.close()
                mail.logout()
            except:
                pass
                
        except Exception as e:
            # In ra log lỗi nếu IMAP bị từ chối/block
            log_func(f"Lỗi IMAP (Bị Microsoft chặn/Thiết bị lạ): {str(e)}")
            # Trả về None ngay để chuyển sang nhập tay, tránh chờ đợi vô ích
            return None
            
        time.sleep(8)
        
    return None
async def is_logged_in(page):
    """Kiểm tra xem trình duyệt đã đăng nhập thành công vào Amazon JP hay chưa."""
    try:
        # 1. Kiểm tra cookie xác thực của Amazon
        cookies = await page.context.cookies()
        has_session = any(c['name'] in ['at-main', 'x-main'] for c in cookies)
        if has_session:
            return True
            
        # 2. Kiểm tra phần tử nút Đăng xuất trên trang
        signout_btn = await page.query_selector("a[href*='signout'], #nav-item-signout")
        if signout_btn:
            return True
            
        # 3. Kiểm tra text chào mừng không chứa 'Sign in' / 'ログイン'
        nav_line = await page.query_selector("#nav-link-accountList-nav-line-1")
        if nav_line:
            text = await nav_line.inner_text()
            if "Sign in" not in text and "ログイン" not in text:
                return True
    except Exception:
        pass
    return False
async def register_amazon_account(
    worker_id,
    email_addr,
    email_pass,
    proxy_str,
    headless,
    debug_mode,
    otp_callback,
    log_callback,
    pre_name=None,
    pre_password=None,
    refresh_token="",
    client_id="",
    custom_browser_path=""
):
    """
    Thực hiện quá trình đăng ký tài khoản trên Amazon JP bằng Playwright.
    Trả về: (status, phone, name, password, error_message)
    """
    def log(msg):
        log_callback(worker_id, msg)

    log(f"Bắt đầu xử lý đăng ký cho {email_addr}")
    
    # 1. Tìm trình duyệt mặc định trên máy
    chrome_path, browser_name = get_browser_path()
    if not chrome_path:
        log("LỖI: Không tìm thấy trình duyệt Google Chrome hoặc MS Edge trên máy!")
        return "FAILED", None, None, None, "Không tìm thấy Chrome/Edge"
        
    log(f"Sử dụng trình duyệt: {browser_name} ({chrome_path})")
    
    # 2. Tạo thông tin tài khoản tự sinh hoặc dùng thông tin truyền vào
    name = pre_name if pre_name else generate_random_name()
    password = pre_password if pre_password else generate_random_password()
    log(f"Thông tin tài khoản -> Tên: {name} | Mật khẩu: {password}")
    
    start_time = time.time()
    
    # Khởi tạo Playwright
    async with async_playwright() as p:
        # Cấu hình proxy nếu có
        launch_args = ["--incognito", "--disable-blink-features=AutomationControlled"]
        proxy_config = None
        
        if proxy_str:
            parts = proxy_str.split(":")
            if len(parts) >= 4:
                host, port, user, pswd = parts[0], parts[1], parts[2], parts[3]
                proxy_config = {
                    "server": f"http://{host}:{port}",
                    "username": user,
                    "password": pswd
                }
                log(f"Sử dụng proxy: {host}:{port}")
            elif len(parts) == 2:
                host, port = parts[0], parts[1]
                proxy_config = {
                    "server": f"http://{host}:{port}"
                }
                log(f"Sử dụng proxy (không auth): {host}:{port}")
                
        try:
            # Khởi chạy trình duyệt nhân Chrome/Edge cài sẵn
            import os
            if custom_browser_path and os.path.isdir(custom_browser_path):
                if custom_browser_path.rstrip('/').endswith('.cloakbrowser'):
                    custom_browser_path = os.path.join(custom_browser_path, "chromium-145.0.7632.109.2/Chromium.app/Contents/MacOS/Chromium")
            
            executable_path = custom_browser_path if custom_browser_path else "/Users/hoangkien/.cloakbrowser/chromium-145.0.7632.109.2/Chromium.app/Contents/MacOS/Chromium"
            print(f"Sử dụng Browser: {executable_path}")
            browser = await p.chromium.launch(
                headless=headless,
                executable_path=executable_path,
                args=launch_args
            )
            
            # Cấu hình Context ẩn danh sạch, khớp với IP Nhật Bản
            context = await browser.new_context(
                proxy=proxy_config,
                viewport={"width": 1280, "height": 800},
                locale="ja-JP",
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            
            # Khởi tạo trang mới
            page = await context.new_page()
            
            # Tăng timeout tải trang lên 60s
            page.set_default_timeout(60000)
            
            # Truy cập trang chủ trước để lấy cookie và hành vi tự nhiên
            log("Đang truy cập trang chủ Amazon JP...")
            await page.goto("https://www.amazon.co.jp/", wait_until="load")
            
            # Đợi ngẫu nhiên 2-4 giây
            import asyncio
            import random
            await asyncio.sleep(random.uniform(2.0, 4.0))
            
            log("Đang click vào nút Đăng nhập...")
            try:
                # Chờ nút Đăng nhập xuất hiện để tránh click hụt
                btn = await page.wait_for_selector("#nav-link-accountList", state="visible", timeout=10000)
                await btn.scroll_into_view_if_needed()
                from steps.mouse_helper import click_element
                success = await click_element(page, "#nav-link-accountList")
                if success:
                    await page.wait_for_load_state("domcontentloaded")
                else:
                    raise Exception("Click function returned False")
            except Exception as e:
                log(f"Không tìm thấy nút đăng nhập trên trang chủ ({str(e)}), dùng fallback URL...")
                # Link đăng nhập đổi ngôn ngữ mặc định sang Tiếng Anh
                signin_url = (
                    "https://www.amazon.co.jp/ap/signin"
                    "?openid.pape.max_auth_age=0"
                    "&openid.return_to=https%3A%2F%2Fwww.amazon.co.jp%2F%3Fref_%3Dnav_signin"
                    "&openid.identity=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select"
                    "&openid.assoc_handle=jpflex&openid.mode=checkid_setup"
                    "&openid.claimed_id=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select"
                    "&openid.ns=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0"
                )
                try:
                    await page.goto(signin_url, wait_until="domcontentloaded")
                except Exception as ex:
                    if "ERR_ABORTED" in str(ex):
                        log("Cảnh báo: ERR_ABORTED khi tải trang đăng nhập, bỏ qua và kiểm tra trang...")
                    else:
                        raise ex
            
            # Kiểm tra xem có bị dính WAF/Captcha không
            if "ショッピング" in await page.title() or await page.query_selector("button:has-text('ショッピングを続ける')"):
                log("Cảnh báo: Phát hiện robot check (WAF). Tạm dừng 15s chờ người dùng giải captcha/nhấn nút...")
                # Nếu chạy headless, ta đành chịu, còn có head thì user click được.
                await page.wait_for_timeout(15000)
                
            # Vòng lặp State Machine: tự động nhận diện trang và chạy function tương ứng
            max_attempts = 15
            attempt = 0
            completed = False
            otp_submitted = False
            
            while attempt < max_attempts and not completed:
                attempt += 1
                await page.wait_for_timeout(2000)  # Chờ trang ổn định sau chuyển đổi
                
                current_url = page.url
                current_title = await page.title()
                
                # Kiểm tra lỗi chặn (Unusual activity / Account creation failed)
                body_text = await page.inner_text("body")
                if "account creation failed" in body_text.lower() or "unusual activity" in body_text.lower():
                    log("Amazon chặn đăng ký (Account creation failed / Unusual activity)")
                    raise Exception("Amazon chặn đăng ký (Unusual activity)")
                
                # A0. Kiểm tra Captcha
                if await step_captcha.is_present(page):
                    log("Phát hiện Captcha! Đang tiến hành giải mã tự động...")
                    await step_captcha.solve(page)
                    continue

                # A. Kiểm tra trang Đăng ký (Name, Password Form)
                if await step_register.detect(page):
                    await step_register.execute(page, name, password, log)
                    continue
                    
                # B. Kiểm tra màn hình Xác minh thiết bị (Màn hình trung gian trước khi tới OTP)
                import steps.step_device_verify as step_device_verify
                if await step_device_verify.detect(page):
                    await step_device_verify.execute(page, log)
                    continue
                    
                otp_selector = await step_otp.detect(page)
                if otp_selector:
                    await step_otp.execute(page, email_addr, email_pass, refresh_token, client_id, otp_callback, fetch_otp_from_email, log)
                    otp_submitted = True
                    continue
                    
                # C. Kiểm tra trang Xác minh thiết bị (Verifying your device)
                if await step_verify_device.detect(page):
                    await step_verify_device.execute(page, log)
                    continue
                    
                # D. Kiểm tra trang Intent (Xác nhận tạo tài khoản mới)
                if await step_intent.detect(page):
                    await step_intent.execute(page, log)
                    continue
                    
                # E. Kiểm tra màn hình đòi Add Số Điện Thoại
                import steps.step_phone_verify as step_phone_verify
                if await step_phone_verify.detect(page):
                    await step_phone_verify.execute(page, log)
                    continue
                    
                # F. Kiểm tra trang Xác minh thiết bị (Verifying your device - màn hình captcha/browser)
                if await step_verify_device.detect(page):
                    await step_verify_device.execute(page, log)
                    continue
                    
                # G. Kiểm tra trang điền Email
                if await step_email.detect(page):
                    await step_email.execute(page, email_addr, log)
                    continue
                    
                # F. Kiểm tra thành công (chuyển hướng ra ngoài các trang đăng nhập/đăng ký)
                is_auth = await is_logged_in(page)
                if is_auth:
                    log("Phát hiện trạng thái đã đăng nhập (Authentic cookies / Signout button). Đăng ký thành công!")
                    completed = True
                    break
                    
                if otp_submitted and "signin" not in current_url and "register" not in current_url and "claim" not in current_url and "/cvf/" not in current_url:
                    log("Đã điền OTP và chuyển hướng thành công ra ngoài các trang đăng ký/đăng nhập!")
                    completed = True
                    break
                    
                # G. Kiểm tra dính CAPTCHA / Robot check / FunCAPTCHA
                body_text = await page.inner_text("body")
                is_captcha = ("captcha" in current_url or 
                              await page.query_selector("#captchacharacters") or 
                              "robot" in current_title.lower() or 
                              "solve this puzzle" in body_text.lower() or 
                              "protect your account" in body_text.lower())
                              
                if is_captcha:
                    log("CẢNH BÁO: Phát hiện CAPTCHA bảo mật (FunCAPTCHA / Text CAPTCHA)! Tạm dừng 20s để giải trên trình duyệt...")
                    await page.wait_for_timeout(20000)
                    continue
                    
                log(f"Đang đợi trang load... URL hiện tại: {current_url[:60]}")
                
            if not completed:
                raise Exception("Không thể hoàn thành đăng ký (Quá số bước tối đa)")
                
            log("ĐĂNG KÝ ACCOUNT THÀNH CÔNG!")
            await browser.close()
            return "SUCCESS", None, name, password, None
            
        except Exception as ex:
            error_str = str(ex)
            log(f"LỖI trong quá trình tự động hóa: {error_str}")
            if debug_mode and 'page' in locals() and page:
                try:
                    os.makedirs("debug_screenshots", exist_ok=True)
                    filename = f"debug_screenshots/error_{email_addr.split('@')[0]}_{int(time.time())}.png"
                    await page.screenshot(path=filename)
                    log(f"Chế độ Debug: Đã chụp ảnh màn hình lỗi lưu tại {filename}")
                except Exception as screenshot_err:
                    log(f"Không thể chụp ảnh màn hình lỗi: {screenshot_err}")
            try:
                await browser.close()
            except:
                pass
            return "FAILED", None, name, password, error_str
