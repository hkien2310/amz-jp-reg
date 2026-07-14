import re

async def detect(page):
    """Kiểm tra xem có phải trang nhập OTP xác minh hòm thư không."""
    url = page.url
    is_cvf_url = "/cvf/" in url or "approval" in url.lower()
    
    # Check các selector OTP cụ thể
    for selector in ["#cvf-aep-otp-code", "#cvf-input-code", "input[name='code']", "input[name*='otp' i]"]:
        if await page.query_selector(selector):
            return selector
            
    # Nếu là URL cvf và có ô input nhưng không phải trang đăng ký
    if is_cvf_url:
        has_text_input = await page.query_selector("input[type='text']")
        has_register_fields = await page.query_selector("#ap_customer_name")
        if has_text_input and not has_register_fields:
            return "input[type='text']"
            
    return None
import requests
import os
import time
SEEN_OTPS_FILE = "data/seen_otps.txt"

def load_seen_otps():
    if not os.path.exists("data"):
        os.makedirs("data", exist_ok=True)
    if os.path.exists(SEEN_OTPS_FILE):
        with open(SEEN_OTPS_FILE, "r") as f:
            return set(f.read().splitlines())
    return set()

def save_seen_otp(otp):
    if not os.path.exists("data"):
        os.makedirs("data", exist_ok=True)
    with open(SEEN_OTPS_FILE, "a") as f:
        f.write(f"{otp}\n")

async def fetch_otp_from_dongvanfb(email_addr, refresh_token, client_id, log):
    seen_otps = load_seen_otps()

    log(f"Đang gọi API DongVanFB để lấy OTP cho email {email_addr}...")
    url = "https://tools.dongvanfb.net/api/get_messages_oauth2"
    payload = {
        "email": email_addr,
        "refresh_token": refresh_token,
        "client_id": client_id
    }
    
    import asyncio
    start_time = time.time()
    while time.time() - start_time < 90:
        try:
            res = await asyncio.to_thread(requests.post, url, json=payload, timeout=15)
            if res.status_code == 200:
                resp_json = res.json()
                
                messages = []
                if isinstance(resp_json, dict):
                    if "data" in resp_json and isinstance(resp_json["data"], list):
                        messages = resp_json["data"]
                    elif "messages" in resp_json and isinstance(resp_json["messages"], list):
                        messages = resp_json["messages"]
                elif isinstance(resp_json, list):
                    messages = resp_json
                    
                if isinstance(resp_json, dict) and "status" in resp_json and str(resp_json["status"]).lower() in ["error", "false"]:
                    log(f"DongVanFB API từ chối token. Hủy lấy OTP qua DongVanFB.")
                    return None
                    
                for msg in messages:
                    from_addr = str(msg.get("from", "")).lower()
                    subject = str(msg.get("subject", ""))
                    message_body = str(msg.get("message", ""))
                    
                    if "amazon" in from_addr or "amazon" in subject.lower():
                        # Dùng regex (?<![#\w])(\d{6})(?![\w]) để tránh bắt trúng mã màu như #007185
                        match = re.search(r'(?<![#\w])(\d{6})(?![\w])', message_body)
                        if match:
                            otp_code = match.group(1)
                            if otp_code in seen_otps:
                                continue
                                
                            save_seen_otp(otp_code)
                            log(f"==> LẤY ĐƯỢC MÃ OTP THÀNH CÔNG TỪ DONGVANFB API: {otp_code}")
                            return otp_code
        except Exception as e:
            log(f"Lỗi khi gọi API DongVanFB: {e}")
            
        await asyncio.sleep(5)
        
    return None
async def fetch_otp_from_email_web(page, email_addr, email_pass, log):
    log("Đang mở tab mới trong cùng browser để đăng nhập Outlook Web Mail lấy OTP...")
    outlook_page = await page.context.new_page()
    try:
        log("Đang truy cập login.live.com...")
        await outlook_page.goto("https://login.live.com/", wait_until="load")
        await outlook_page.wait_for_timeout(2000)
        
        # 1. Điền Email
        email_input = await outlook_page.wait_for_selector("input[type='email'], input[name='loginfmt'], #usernameEntry, #i0116", timeout=15000)
        await email_input.fill(email_addr)
        
        # Click Next
        next_btn = await outlook_page.wait_for_selector("button[type='submit'], #idSIButton9, input[type='submit']", timeout=10000)
        await next_btn.click()
        await outlook_page.wait_for_timeout(3000)
        
        # 2. Điền Mật khẩu
        pw_input = await outlook_page.wait_for_selector("input[type='password'], input[name='passwd']", timeout=15000)
        await pw_input.fill(email_pass)
        
        # Click Sign In
        signin_btn = await outlook_page.wait_for_selector("button[type='submit'], #idSIButton9, input[type='submit']", timeout=10000)
        await signin_btn.click()
        await outlook_page.wait_for_timeout(4000)
        
        # 3. Stay signed in?
        no_btn = await outlook_page.query_selector("#idBtn_Back")
        if no_btn:
            await no_btn.click()
            await outlook_page.wait_for_timeout(4000)
        else:
            yes_btn = await outlook_page.query_selector("#idSIButton9")
            if yes_btn:
                await yes_btn.click()
                await outlook_page.wait_for_timeout(4000)
                
        # 4. Kiểm tra MFA
        body_text = await outlook_page.inner_text("body")
        if "protect your account" in body_text.lower() or "verify your identity" in body_text.lower():
            log("Cảnh báo: Microsoft yêu cầu xác minh bảo mật nâng cao (MFA/Backup email) cho Hotmail!")
            await outlook_page.screenshot(path=f"debug_screenshots/outlook_mfa_{email_addr.split('@')[0]}.png")
            return None
            
        # 5. Vào Inbox
        log("Đang chuyển hướng vào hòm thư Outlook...")
        await outlook_page.goto("https://outlook.live.com/mail/0/", wait_until="load")
        
        log("Đang chờ danh sách thư tải xong...")
        try:
            await outlook_page.wait_for_selector("div[role='listbox'], #MailList, div[data-app-section='MailList']", timeout=25000)
        except Exception as list_err:
            log(f"Cảnh báo khi đợi danh sách thư: {list_err}. Tiếp tục tìm...")
            
        await outlook_page.wait_for_timeout(5000)
        
        # Quét email trong inbox
        email_spans = await outlook_page.query_selector_all("span:has-text('Amazon')")
        if not email_spans:
            other_tab = await outlook_page.query_selector("span:has-text('Other')")
            if other_tab:
                await other_tab.click()
                await outlook_page.wait_for_timeout(4000)
                email_spans = await outlook_page.query_selector_all("span:has-text('Amazon')")
                
        if email_spans:
            log("Tìm thấy thư liên quan tới Amazon. Đang mở thư...")
            await email_spans[0].click()
            await outlook_page.wait_for_timeout(4000)
            
            mail_content = await outlook_page.inner_text("body")
            otp_match = re.search(r'\b(\d{6})\b', mail_content)
            if otp_match:
                otp = otp_match.group(1)
                log(f"==> LẤY ĐƯỢC MÃ OTP THÀNH CÔNG TỪ WEB MAIL: {otp}")
                return otp
                
        log("Không tìm thấy thư nào từ Amazon hoặc OTP trong Inbox.")
    except Exception as e:
        log(f"Lỗi khi cào OTP từ Web Mail: {e}")
        try:
            await outlook_page.screenshot(path=f"debug_screenshots/outlook_error_{email_addr.split('@')[0]}.png")
        except:
            pass
    finally:
        try:
            await outlook_page.close()
        except:
            pass
    return None

async def execute(page, email_addr, email_pass, refresh_token, client_id, otp_callback, fetch_otp_from_email, log, otp_email=None, otp_pass=None):
    """Thực hiện lấy OTP (IMAP hoặc popup hoặc web cào) và điền OTP gửi đi."""
    selector = await detect(page)
    if not selector:
        raise Exception("Không tìm thấy ô nhập OTP")
        
    log("Phát hiện màn hình OTP. Đang tiến hành lấy mã xác minh...")
    
    otp_code = None
    
    # 0. Thử lấy bằng IMAP Gmail/iCloud
    if otp_email and otp_pass:
        from src.core.email_reader_imap import get_amazon_otp_imap
        otp_code = get_amazon_otp_imap(email_addr, otp_email, otp_pass, log)
        
    # 1. Thử lấy bằng API DongVanFB nếu có refresh_token
    if not otp_code and refresh_token and client_id:
        otp_code = await fetch_otp_from_dongvanfb(email_addr, refresh_token, client_id, log)
        
    # 2. Thử lấy OTP tự động qua IMAP nếu DongVanFB không có hoặc không thành công
    if not otp_code:
        otp_code = fetch_otp_from_email(email_addr, email_pass, log)
    
    # Nếu IMAP thất bại, tự động chuyển sang cào Web Mail qua cổng 443!
    if not otp_code:
        log("Kết nối IMAP thất bại hoặc bị chặn Basic Auth. Tự động chuyển sang cào OTP trực tiếp từ Outlook Web...")
        otp_code = await fetch_otp_from_email_web(page, email_addr, email_pass, log)
        
    # Nếu cả hai cách tự động không được, gọi callback để người dùng nhập thủ công trên GUI
    if not otp_code:
        log("Không tự động đọc được OTP bằng cả hai phương pháp. Đang mở popup yêu cầu nhập tay...")
        otp_code = otp_callback(email_addr)
        
    if not otp_code:
        raise Exception("Bỏ qua OTP")
        
    log(f"Đang điền mã OTP: {otp_code}...")
    otp_input = await page.query_selector(selector)
    from steps.mouse_helper import human_type
    await human_type(page, selector, str(otp_code))
    
    # Bấm gửi OTP
    submit_btn = await page.query_selector("input[type='submit']") or await page.query_selector("#cvf-submit-otp-button")
    await submit_btn.click()
    
    # Cần wait lâu hơn để request hoàn thành và redirect
    await page.wait_for_timeout(5000)
    try:
        await page.wait_for_load_state("domcontentloaded", timeout=15000)
    except Exception:
        pass
