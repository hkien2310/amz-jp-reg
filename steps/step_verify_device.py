async def detect(page):
    """Kiểm tra xem có phải trang Verifying your device (xác minh trình duyệt/thiết bị) không."""
    url = page.url
    # Nếu chứa /ap/cvf/ và có từ khóa verifying
    if "/ap/cvf/" in url:
        body_text = await page.inner_text("body")
        if "verifying your device" in body_text.lower() or "verification complete" in body_text.lower():
            return True
    return False

async def execute(page, log):
    """Bấm nút Continue để tiếp tục quá trình đăng ký."""
    log("Phát hiện màn hình xác minh thiết bị (Verifying your device). Đang bấm Continue...")
    # Thử click nút submit hoặc Continue
    btn = await page.query_selector("input[type='submit']") or await page.query_selector("input[value='Continue']")
    if btn:
        await btn.click()
    else:
        # Click dự phòng
        btn_text = await page.query_selector("text=Continue")
        if btn_text:
            await btn_text.click()
        else:
            raise Exception("Không tìm thấy nút Continue để tiếp tục qua trang OTP")
            
    await page.wait_for_load_state("domcontentloaded")
