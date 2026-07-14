import asyncio
import sys
from playwright.async_api import async_playwright

async def main():
    # Lấy proxy từ file excel (ví dụ)
    proxy_str = "residential.byteproxies.io:8888:pool-basic-cc-jp-sid-84393332-ttl-30:v7t62ukpvup29t8m"
    parts = proxy_str.split(":")
    
    proxy_config = {
        "server": f"http://{parts[0]}:{parts[1]}",
        "username": parts[2],
        "password": parts[3]
    }
    
    browser_path = "/Users/hoangkien/.cloakbrowser/chromium-145.0.7632.109.2/Chromium.app/Contents/MacOS/Chromium"
    
    print("=== ĐANG KHỞI CHẠY TRÌNH DUYỆT ĐỂ BÁC THAO TÁC TAY ===")
    print("Playwright Inspector sẽ hiện ra. Bác ấn nút 'Record' trên Inspector, sau đó thao tác trên trình duyệt.")
    print("Mọi hành động bác làm sẽ được Inspector ghi lại thành code (chỉ lưu element/click, không lưu toạ độ chuột)!")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            executable_path=browser_path,
            headless=False,
            proxy=proxy_config,
            args=["--disable-blink-features=AutomationControlled"]
        )
        
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            locale="ja-JP",
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        page = await context.new_page()
        
        # Bắt sự kiện console.log từ web để ghi vào file
        import time
        with open("manual_interaction.log", "w") as f:
            f.write(f"=== BẮT ĐẦU RECORD GIAO DỊCH LÚC {time.strftime('%H:%M:%S')} ===\\n")
            
        def log_to_file(msg):
            with open("manual_interaction.log", "a") as f:
                f.write(f"[{msg.type}] {msg.text}\\n")
                
        page.on("console", log_to_file)
        
        # Inject JS để tự động log các hành động click/type ra console
        await page.add_init_script("""
            document.addEventListener('click', e => {
                console.log('[USER CLICK]', e.target.tagName, e.target.id, e.target.className);
            }, true);
            document.addEventListener('keydown', e => {
                console.log('[USER KEY]', e.key);
            }, true);
        """)
        
        # Mở sẵn Amazon
        await page.goto("https://www.amazon.co.jp/")
        
        print("Trình duyệt đã mở! Cửa sổ Inspector bị lỗi đen thui thì bác cứ mặc kệ nó (kéo sang 1 bên).")
        print("Bác cứ thao tác Đăng ký thẳng trên trang Amazon.")
        print("Tui đã cấy mã theo dõi ngầm, tui sẽ tự động log các thao tác của bác ra cửa sổ terminal này.")
        
        # Giữ trình duyệt mở không giới hạn để bác thao tác
        while True:
            await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
