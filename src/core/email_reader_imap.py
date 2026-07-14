"""
email_reader_imap.py - Module lấy mã OTP của Amazon từ Email thông qua giao thức IMAP (dùng App Password)
"""
import imaplib
import email
from email.header import decode_header
import re
import time
from datetime import datetime
import dateutil.parser

def _get_imap_server(email_address: str) -> str:
    """Trả về IMAP server tương ứng với đuôi email."""
    domain = email_address.split("@")[-1].lower()
    if domain in ["gmail.com", "googlemail.com"]:
        return "imap.gmail.com"
    elif domain in ["icloud.com", "me.com", "mac.com"]:
        return "imap.mail.me.com"
    else:
        # Mặc định thử gmail nếu không rõ
        return "imap.gmail.com"

def get_amazon_otp_imap(
    target_email: str,
    otp_email: str,
    otp_pass: str,
    log_func,
    timeout: int = 90,
    since_ts: float = 0
) -> str:
    """
    Kết nối vào hộp thư `otp_email` bằng IMAP và mật khẩu ứng dụng `otp_pass`.
    Quét hộp thư INBOX để tìm email gửi từ amazon.
    Lọc các email có nội dung đề cập tới `target_email` (nếu dùng alias).
    Trả về chuỗi 6 số hoặc chuỗi rỗng nếu thất bại/hết giờ.
    
    :param target_email: Email thật dùng để đăng ký (ví dụ: alias+1@gmail.com)
    :param otp_email: Email gốc dùng để login IMAP (ví dụ: alias@gmail.com)
    :param otp_pass: App Password của email gốc
    :param log_func: Hàm log của worker
    :param timeout: Thời gian chờ tối đa (giây)
    :param since_ts: Chỉ lấy mail nhận SAU mốc thời gian này (timestamp)
    """
    if not otp_email or not otp_pass:
        log_func(f"[{target_email}] Thiếu otp_email hoặc otp_pass để đăng nhập IMAP.")
        return ""

    imap_server = _get_imap_server(otp_email)
    log_func(f"[{target_email}] Đang chờ OTP từ {otp_email} qua {imap_server} (Timeout: {timeout}s)")
    
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            # 1. Kết nối IMAP
            mail = imaplib.IMAP4_SSL(imap_server)
            mail.login(otp_email, otp_pass)
            mail.select("inbox")
            
            # 2. Tìm kiếm email từ Amazon
            # Tìm theo keyword amazon để bắt hết các sub-domain amazon.co.jp
            status, messages = mail.search(None, '(FROM "amazon")')
            
            if status == "OK" and messages[0]:
                msg_nums = messages[0].split()
                # Duyệt từ mail mới nhất (số to nhất) lùi về
                for num in reversed(msg_nums):
                    res, msg_data = mail.fetch(num, "(BODY.PEEK[])")
                    if res != "OK":
                        continue
                        
                    raw_email = next(
                        (p[1] for p in msg_data if isinstance(p, tuple) and p[1]),
                        None
                    )
                    if not raw_email:
                        continue
                    
                    msg = email.message_from_bytes(raw_email)
                    
                    # 3. Lấy thời gian nhận mail
                    date_tuple = email.utils.parsedate_tz(msg['Date'])
                    if date_tuple:
                        local_date = datetime.fromtimestamp(email.utils.mktime_tz(date_tuple))
                        mail_ts = local_date.timestamp()
                        
                        # Bỏ qua mail cũ
                        if since_ts > 0 and mail_ts < since_ts:
                            continue
                            
                    # 4. Kiểm tra TO address có chứa target_email không (cho Alias)
                    to_address = str(msg.get("To", "")).lower()
                    
                    # 5. Lấy nội dung body
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            content_type = part.get_content_type()
                            if content_type == "text/plain":
                                try:
                                    charset = part.get_content_charset() or 'utf-8'
                                    body = part.get_payload(decode=True).decode(charset, errors='replace')
                                except:
                                    pass
                    else:
                        try:
                            charset = msg.get_content_charset() or 'utf-8'
                            body = msg.get_payload(decode=True).decode(charset, errors='replace')
                        except:
                            pass
                            
                    # Nếu body rỗng thử lấy từ HTML
                    if not body and msg.is_multipart():
                        for part in msg.walk():
                            content_type = part.get_content_type()
                            if content_type == "text/html":
                                try:
                                    charset = part.get_content_charset() or 'utf-8'
                                    body = part.get_payload(decode=True).decode(charset, errors='replace')
                                except:
                                    pass
                                    
                    # Kiểm tra xem body hoặc to_address có chứa mã 6 số
                    if body:
                        # Kiểm tra xem target_email có nằm trong email này không (để tránh lấy nhầm alias khác)
                        # TO address hoặc nội dung body
                        if target_email.lower() in to_address or target_email.lower() in body.lower():
                            # Regex tránh bắt trúng mã màu như #007185
                            match = re.search(r'(?<![#\w])(\d{6})(?![\w])', body)
                            if match:
                                otp_code = match.group(1)
                                log_func(f"[{target_email}] Đã tìm thấy mã OTP qua IMAP: {otp_code}")
                                mail.logout()
                                return otp_code
            
            mail.logout()
        except Exception as e:
            # log_func(f"[{target_email}] Lỗi IMAP: {e}")
            pass
            
        time.sleep(5)
        
    log_func(f"[{target_email}] Hết thời gian ({timeout}s) không nhận được OTP qua IMAP.")
    return ""
