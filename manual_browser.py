import asyncio
import openpyxl
from playwright.async_api import async_playwright
import os
import sys

async def main():
    print("Đang đọc proxy từ AmazonJP_test.xlsx...")
    proxy_str = None
    row_idx = 2
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        row_idx = int(sys.argv[1])
        
    try:
        wb = openpyxl.load_workbook("AmazonJP_test.xlsx")
        sheet = wb["Proxies"]
        proxy_str = sheet.cell(row=row_idx, column=1).value
        wb.close()
    except Exception as e:
        print(f"Không thể đọc file Excel: {e}")
        
    proxy_config = None
    if proxy_str:
        parts = proxy_str.split(":")
        if len(parts) == 4:
            ip, port, user, pwd = parts
            proxy_config = {
                "server": f"http://{ip}:{port}",
                "username": user,
                "password": pwd
            }
        elif len(parts) == 2:
            ip, port = parts
            proxy_config = {
                "server": f"http://{ip}:{port}"
            }
            
    print(f"Sử dụng proxy: {proxy_str}")
    
    # Tìm browser path từ config
    import json
    browser_path = ""
    try:
        with open("config.json", "r") as f:
            conf = json.load(f)
            browser_path = conf.get("browser_path", "")
    except:
        pass

    async with async_playwright() as p:
        print(f"Đang khởi chạy trình duyệt: {browser_path or 'Mặc định'}")
        
        launch_args = {
            "headless": False,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--no-sandbox",
                "--lang=ja-JP"
            ]
        }
        if browser_path and "Chromium.app" in browser_path:
            launch_args["executable_path"] = browser_path
        elif browser_path and os.path.exists(os.path.join(browser_path, "chromium-145.0.7632.109.2/Chromium.app/Contents/MacOS/Chromium")):
            launch_args["executable_path"] = os.path.join(browser_path, "chromium-145.0.7632.109.2/Chromium.app/Contents/MacOS/Chromium")

            
        browser = await p.chromium.launch(**launch_args)
        
        context = await browser.new_context(
            proxy=proxy_config,
            viewport={"width": 1280, "height": 800},
            locale="ja-JP",
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        print("Đã mở trình duyệt! Bạn có thể tự thao tác đăng ký bằng tay ngay bây giờ.")
        print("Truy cập trang chủ Amazon JP...")
        try:
            await page.goto("https://www.amazon.co.jp/")
        except:
            pass
            
        print("Trình duyệt đang mở... (Bấm Ctrl+C trên terminal để thoát)")
        # Giữ cho trình duyệt mở mãi mãi để test
        while True:
            await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
