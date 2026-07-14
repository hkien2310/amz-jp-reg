import asyncio
from steps.mouse_helper import click_element

async def detect(page):
    """Kiểm tra xem có phải trang xác minh thiết bị (デバイスを確認中...) không."""
    url = page.url
    if "/cvf/" in url or "approval" in url.lower():
        # Nếu có ô nhập số điện thoại, KHÔNG PHẢI là trang device verify
        has_tel_input = await page.query_selector("input[type='tel']")
        if has_tel_input:
            return False
            
        # Nếu không có ô nhập text nào, và có nút submit, thì đó là trang device verify
        has_text_input = await page.query_selector("input[type='text']")
        has_submit_btn = await page.query_selector("input.a-button-input, input[type='submit']")
        
        if not has_text_input and has_submit_btn:
            return True
            
        # Hoặc tìm bằng chữ
        body_text = await page.inner_text("body")
        if "デバイスを確認中" in body_text or "device being verified" in body_text.lower():
            return True
            
    return False

async def execute(page, log):
    """Thực hiện click nút Tiếp tục (Next / 次に進む)"""
    log("Phát hiện màn hình Xác minh thiết bị. Đang bấm Tiếp tục...")
    await page.wait_for_load_state("domcontentloaded")
    
    btn = await page.query_selector("input.a-button-input") or await page.query_selector("input[type='submit']")
    if btn:
        await btn.click()
    else:
        raise Exception("Không tìm thấy nút Next trên trang Xác minh thiết bị")
        
    await asyncio.sleep(1)
    await page.wait_for_load_state("domcontentloaded")
