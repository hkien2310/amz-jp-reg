import os
import platform
import sys

def get_browser_path():
    """
    Tự động dò tìm đường dẫn thực thi của Google Chrome hoặc Microsoft Edge
    trên các hệ điều hành khác nhau (macOS, Windows, Linux).
    Trả về: (executable_path, browser_name) hoặc (None, None)
    """
    system = platform.system()
    
    if system == "Darwin":  # macOS
        paths = [
            ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "Chrome"),
            ("/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge", "Edge"),
            (os.path.expanduser("~/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"), "Chrome"),
            (os.path.expanduser("~/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"), "Edge")
        ]
        for path, name in paths:
            if os.path.exists(path):
                return path, name
                
    elif system == "Windows":  # Windows
        # Một số biến môi trường phổ biến trên Windows
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        program_files = os.environ.get("ProgramFiles", "C:\\Program Files")
        program_files_x86 = os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")
        
        paths = [
            (os.path.join(program_files, "Google\\Chrome\\Application\\chrome.exe"), "Chrome"),
            (os.path.join(program_files_x86, "Google\\Chrome\\Application\\chrome.exe"), "Chrome"),
            (os.path.join(local_app_data, "Google\\Chrome\\Application\\chrome.exe") if local_app_data else "", "Chrome"),
            (os.path.join(program_files_x86, "Microsoft\\Edge\\Application\\msedge.exe"), "Edge"),
            (os.path.join(program_files, "Microsoft\\Edge\\Application\\msedge.exe"), "Edge")
        ]
        for path, name in paths:
            if path and os.path.exists(path):
                return path, name
                
    elif system == "Linux":  # Linux
        paths = [
            ("/usr/bin/google-chrome", "Chrome"),
            ("/usr/bin/chrome", "Chrome"),
            ("/usr/bin/microsoft-edge", "Edge"),
            ("/usr/bin/chromium-browser", "Chromium"),
            ("/usr/bin/chromium", "Chromium")
        ]
        for path, name in paths:
            if os.path.exists(path):
                return path, name
                
    return None, None

if __name__ == "__main__":
    path, name = get_browser_path()
    if path:
        print(f"Tìm thấy trình duyệt: {name}")
        print(f"Đường dẫn: {path}")
    else:
        print("Không tìm thấy Chrome hoặc Edge trên máy này.")
