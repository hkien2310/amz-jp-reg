async def detect(page):
    """Kiểm tra xem có phải trang xác nhận Intent (Tài khoản mới) không."""
    url = page.url
    if "/claim/intent" in url:
        return True
    
    body_text = await page.inner_text("body")
    if "looks like you're new to amazon" in body_text.lower():
        return True
    return False

async def execute(page, log):
    """Thực hiện bấm nút Proceed to create an account."""
    log("Phát hiện màn hình xác nhận tài khoản mới (Intent). Đang bấm Proceed...")
    # Chờ trang load xong form
    await page.wait_for_load_state("domcontentloaded")
    try:
        await page.wait_for_selector("#createAccountSubmit, #continue, input[type='submit'], .a-button-input, text=Proceed to create an account", timeout=5000)
    except:
        pass

    # Bấm nút submit đầu tiên tìm thấy trên form
    # Nút này có thể là id="createAccountSubmit", "continue", hoặc tag input submit
    btn = (
        await page.query_selector("#createAccountSubmit") or 
        await page.query_selector("#continue") or 
        await page.query_selector("input[type='submit']") or 
        await page.query_selector(".a-button-input") or
        await page.query_selector("text=Proceed to create an account")
    )
    
    if btn:
        await btn.click()
    else:
        # Nếu không tìm thấy, dump 1 phần HTML để debug
        html = await page.content()
        with open("intent_debug.html", "w", encoding="utf-8") as f:
            f.write(html)
        raise Exception("Không tìm thấy nút Proceed để tiếp tục. Đã lưu HTML ra intent_debug.html")
            
    await page.wait_for_load_state("domcontentloaded")
