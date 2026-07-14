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
    log("Phát hiện màn hình yêu cầu thêm SĐT. Hiện tại chưa hỗ trợ API số điện thoại.")
    raise Exception("Bị yêu cầu Add SĐT (Phone Verification Required)")
