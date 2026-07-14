import asyncio
import random

async def detect(page):
    """Kiểm tra xem có phải trang điền Email đăng nhập/đăng ký không."""
    has_email = (await page.query_selector("#ap_email_login") is not None) or (await page.query_selector("#ap_email") is not None)
    has_register_fields = (await page.query_selector("#ap_customer_name") is not None)
    return has_email and not has_register_fields

async def execute(page, email_addr, log):
    """Thực hiện điền email và ấn Continue."""
    email_input = await page.query_selector("#ap_email_login") or await page.query_selector("#ap_email")
    from steps.mouse_helper import human_type
    await human_type(page, "#ap_email_login, #ap_email", email_addr)
    await asyncio.sleep(random.uniform(0.8, 1.8))
    log("Đã tự động điền email đăng ký.")
    
    from steps.mouse_helper import click_element
    success = await click_element(page, "#continue")
    if not success:
        success = await click_element(page, "input[type='submit']")
        
    if success:
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=10000)
        except Exception:
            pass
