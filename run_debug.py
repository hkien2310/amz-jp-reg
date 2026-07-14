import json
import sys
from main import AmazonRegisterApp
import threading

def cli_logger(msg):
    print(f"[LOG] {msg}")

def run_debug():
    print("=== BẮT ĐẦU CHẾ ĐỘ DEBUG (CLI) ===")
    # Khởi tạo app nhưng ẩn đi
    app = AmazonRegisterApp()
    app.withdraw()
    
    # Trỏ logger ra console
    app.write_log = cli_logger
    
    # Ghi đè các hàm gọi UI để tránh lỗi
    def mock_after(delay, func, *args):
        try:
            func(*args)
        except:
            pass
            
    app.after = mock_after
    app.update_worker_status_gui = lambda w_id, status: print(f"[Worker {w_id}]: {status}")
    app.update_stats_label = lambda: print(f"[Tiến trình] {app.accounts_processed}/{app.total_accounts_to_run} - Thành công: {app.accounts_success} - Thất bại: {app.accounts_failed}")
    app.reset_gui_after_run = lambda: print("=== CHẠY XONG TẤT CẢ LUỒNG ===")

    # Lấy cấu hình
    config = app.load_config()
    excel_path = config.get("excel_path", "")
    if not excel_path:
        print("Lỗi: Không tìm thấy excel_path trong config.json")
        sys.exit(1)
        
    use_proxy = config.get("use_proxy", True)
    limit_str = config.get("limit", "")
    limit = int(limit_str) if str(limit_str).isdigit() else None
    
    num_workers = config.get("workers", 1)
    headless = config.get("headless", False)
    debug_mode = config.get("debug_mode", True)
    browser_path_val = config.get("browser_path", "")
    
    print(f"Cấu hình nạp: Workers={num_workers}, Proxy={use_proxy}, Limit={limit}, Headless={headless}")

    # Chạy quy trình nạp
    app.cached_excel_path = excel_path
    success_init = app.load_pending_accounts_to_queue(excel_path, use_proxy, limit)
    if not success_init:
        print("Dừng vì nạp Excel thất bại.")
        sys.exit(1)
        
    app.is_running = True
    
    # Gọi trực tiếp coordinator, nó sẽ block thread này cho tới khi worker xong
    app.run_coordinator(num_workers, headless, debug_mode, browser_path_val)

if __name__ == "__main__":
    run_debug()
