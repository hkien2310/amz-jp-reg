async def detect(page):
    """Kiểm tra xem có phải trang điền thông tin đăng ký (Tên, Password) không."""
    name_inp = await page.query_selector("#ap_customer_name")
    pw_inp = await page.query_selector("#ap_password")
    return name_inp is not None and pw_inp is not None

async def execute(page, name, password, log):
    """Thực hiện điền Tên, Password và ấn Đăng ký."""
    log("Đang kiểm tra cảnh báo lỗi từ Amazon...")
    body_text = await page.inner_text("body")
    if "account creation failed" in body_text.lower() or "unusual activity" in body_text.lower():
        raise Exception("Amazon chặn đăng ký (Account creation failed / Unusual activity)")

    log("Đang điền thông tin form đăng ký (Tên và Mật khẩu)...")
    import asyncio
    import random
    
    name_inp = await page.query_selector("#ap_customer_name")
    from steps.mouse_helper import human_type, click_element
    await human_type(page, "#ap_customer_name", name)
    await asyncio.sleep(random.uniform(0.5, 1.2))
    
    # Dùng cách paste (insert_text) cho password vì password ngẫu nhiên người thật thường copy-paste
    await click_element(page, "#ap_password")
    await asyncio.sleep(random.uniform(0.2, 0.5))
    await page.keyboard.insert_text(password)
    await asyncio.sleep(random.uniform(0.5, 1.2))
    
    await click_element(page, "#ap_password_check")
    await asyncio.sleep(random.uniform(0.2, 0.5))
    await page.keyboard.insert_text(password)
    await asyncio.sleep(random.uniform(0.8, 1.8))
    
    await click_element(page, "#continue")
    await page.wait_for_load_state("domcontentloaded")
