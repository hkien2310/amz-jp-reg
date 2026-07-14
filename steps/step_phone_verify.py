import asyncio

async def detect(page):
    """Kiểm tra xem có phải trang yêu cầu thêm số điện thoại không (携帯電話番号を追加する)."""
    url = page.url
    if "/cvf/" in url or "approval" in url.lower():
        # Tìm ô input sdt trước cho chắc ăn vì nó là điểm phân biệt mạnh nhất
        has_tel_input = await page.query_selector("input[type='tel']")
        if has_tel_input:
            return True
            
        body_text = await page.inner_text("body")
        if "携帯電話番号を追加する" in body_text or "add a mobile number" in body_text.lower():
            return True
            
    return False

async def execute(page, log):
    """Xử lý trang yêu cầu thêm số điện thoại"""
    log("Phát hiện màn hình yêu cầu thêm SĐT. Đang lấy số từ hệ thống SMS API...")
    import sys
    sys.path.append("/Users/hoangkien/NLV/bot-amazon-jp")
    from src.core import sms_service
    
    try:
        # 1. Order phone
        order = sms_service.order_phone()
        phone_raw = order["phone"]
        pkey = order["pkey"]
        country = order["country"].lower()
        log(f"Đã lấy số: {phone_raw} (pkey: {pkey[:8]}...)")
        
        # 2. Format phone (Bỏ số 0 ở đầu nếu là Nhật Bản)
        phone_formatted = phone_raw
        if country == "jpn" and phone_raw.startswith("0"):
            phone_formatted = phone_raw[1:]
            
        # 3. Chọn mã vùng (Country code) - Dùng Javascript tương tự bản bot cũ
        try:
            result = await page.evaluate(f"""
                () => {{
                    var keywords = ['japan', 'jp'];
                    var selects = document.querySelectorAll('select');
                    for (var sel of selects) {{
                        for (var opt of sel.options) {{
                            var txt = (opt.text || opt.value || '').toLowerCase();
                            for (var kw of keywords) {{
                                if (txt.indexOf(kw) !== -1) {{
                                    sel.value = opt.value;
                                    sel.dispatchEvent(new Event('change', {{bubbles: true}}));
                                    return 'selected:' + opt.text + ':' + opt.value;
                                }}
                            }}
                        }}
                    }}
                    return 'not_found';
                }}
            """)
            log(f"Chọn Country Code: {result}")
        except Exception as e:
            log(f"Lỗi chọn Country Code: {e}")
            
        # 4. Điền số
        phone_input = await page.query_selector("#ap_phone_number") or await page.query_selector("input[type='tel']")
        if not phone_input:
            sms_service.cancel(pkey)
            raise Exception("Không tìm thấy ô nhập số điện thoại")
            
        from steps.mouse_helper import click_element, human_type
        await click_element(page, phone_input)
        await phone_input.fill("")
        await human_type(page, "#ap_phone_number" if await page.query_selector("#ap_phone_number") else "input[type='tel']", phone_formatted)
        
        # 5. Bấm Submit
        submit_btn = await page.query_selector("input[type='submit']") or await page.query_selector("button:has-text('Add mobile number')")
        if submit_btn:
            await click_element(page, submit_btn)
        else:
            await page.evaluate("document.querySelector('form').submit()")
            
        await page.wait_for_timeout(3000)
        
        # 6. Check lỗi ngay sau submit
        body_text = await page.inner_text("body")
        if "not valid" in body_text.lower() or "invalid" in body_text.lower() or "please enter a valid" in body_text.lower():
            sms_service.cancel(pkey)
            raise Exception("Số điện thoại báo lỗi invalid sau khi submit")
            
        # 7. Đợi OTP
        log(f"Đang đợi Amazon gửi OTP về số {phone_raw}...")
        otp_code = sms_service.poll_sms_otp(pkey, timeout=120)
        
        if not otp_code:
            sms_service.cancel(pkey)
            raise Exception("Timeout không nhận được SMS OTP")
            
        # 8. Nhập OTP
        otp_input = await page.query_selector("#cvf-input-code") or await page.query_selector("input[name='code']") or await page.query_selector("input[autocomplete='one-time-code']")
        if not otp_input:
            raise Exception("Không tìm thấy ô nhập SMS OTP")
            
        await click_element(page, otp_input)
        await human_type(page, "#cvf-input-code" if await page.query_selector("#cvf-input-code") else "input[name='code']", otp_code)
        
        verify_btn = await page.query_selector("#cvf-submit-otp-button") or await page.query_selector("input[type='submit']")
        if verify_btn:
            await click_element(page, verify_btn)
            
        log("Đã gửi mã SMS OTP thành công!")
        await page.wait_for_timeout(4000)
        
        return phone_raw
        
    except Exception as e:
        log(f"Lỗi quy trình Phone OTP: {e}")
        try:
            sms_service.cancel(pkey)
        except:
            pass
        raise e
