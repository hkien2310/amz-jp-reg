"""
sms_service.py — Lấy số điện thoại + OTP qua API DongVanFB.
"""
import threading
import time
import requests
import json
import os

log = lambda msg: print(f"[SMS_SERVICE] {msg}")

def get_sms_base():
    return get_sms_config().get("sms_base_url", "https://tools.dongvanfb.net")

_apikey: str = ""
_apikey: str = ""
_apikey_expires: float = 0.0
_apikey_lock = threading.Lock()

def get_sms_config():
    """Lấy config sms từ config.json."""
    config_path = "config.json"
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            return json.load(f)
    return {}

def _get_apikey() -> str:
    """Lấy apikey từ file cache hoặc gọi API nếu hết hạn. Thread-safe."""
    global _apikey, _apikey_expires

    with _apikey_lock:
        now = time.time()
        
        # 1. Memory cache check
        if _apikey and now < _apikey_expires - 300:
            return _apikey

        # 2. File cache check
        config_data = get_sms_config()
        file_key = config_data.get("sms_api_key", "")
        file_expires = config_data.get("sms_api_key_expires", 0.0)
        
        if file_key and now < file_expires - 300:
            _apikey = file_key
            _apikey_expires = file_expires
            return _apikey

        # 3. Request new apikey
        sms_username = config_data.get("sms_username", "")
        sms_password = config_data.get("sms_password", "")
        
        if not sms_username or not sms_password:
            raise RuntimeError("sms_username / sms_password chưa được cấu hình trong config.json")

        log("Lấy SMS apikey mới từ API...")
        resp = requests.post(
            f"{get_sms_base()}/api/ext/getKey",
            json={"username": sms_username, "password": sms_password},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        if data.get("status") != "success":
            raise RuntimeError(f"getKey thất bại: {data}")

        _apikey = data["apikey"]
        _apikey_expires = data["expires_at"] / 1000
        
        # Lưu vào config.json
        try:
            config_data["sms_api_key"] = _apikey
            config_data["sms_api_key_expires"] = _apikey_expires
            with open("config.json", "w") as f:
                json.dump(config_data, f, indent=4)
            log("Đã lưu SMS apikey mới vào config.json.")
        except Exception as e:
            log(f"Không ghi được config.json: {e}")

        log(f"✅ Apikey OK (hết hạn: {time.strftime('%H:%M:%S', time.localtime(_apikey_expires))})")
        return _apikey

def clear_cache():
    global _apikey, _apikey_expires
    with _apikey_lock:
        _apikey = ""
        _apikey_expires = 0.0
        config_data = get_sms_config()
        if "sms_api_key" in config_data:
            config_data["sms_api_key"] = ""
            config_data["sms_api_key_expires"] = 0.0
            try:
                with open("config.json", "w") as f:
                    json.dump(config_data, f, indent=4)
            except:
                pass

def order_phone(retry: bool = True) -> dict:
    apikey = _get_apikey()
    config_data = get_sms_config()
    service_id = config_data.get("sms_service_id", "1002") # 1002 = Amazon JP in some systems
    server = config_data.get("sms_server", "1")
    country = config_data.get("sms_country", "jpn")
    
    params = {
        "apikey":    apikey,
        "serviceId": service_id,
        "server":    server,
        "country":   country,
    }
    log(f"📱 Order phone | country={country} serviceId={service_id}")

    resp = requests.get(f"{get_sms_base()}/api/ext/order", params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    if data.get("status") != "success":
        msg = str(data.get("message", data.get("msg", data)))
        if "không hợp lệ" in msg.lower() and retry:
            log("API key lỗi lúc order, xoá cache và thử lại...")
            clear_cache()
            return order_phone(retry=False)
        raise RuntimeError(f"order thất bại: {msg}")

    pkey = data["pkey"]
    phone = data.get("phone", "").strip()

    if not phone or "xin số" in phone or not any(c.isdigit() for c in phone):
        log("📱 Đang poll getSms để lấy số thực tế...")
        max_attempts = 10
        for attempt in range(1, max_attempts + 1):
            time.sleep(1.5)
            try:
                get_resp = requests.get(
                    f"{get_sms_base()}/api/ext/getSms",
                    params={"apikey": apikey, "pkey": pkey},
                    timeout=10,
                )
                get_data = get_resp.json()
                curr_phone = get_data.get("phone", "").strip()
                if curr_phone and "xin số" not in curr_phone and any(c.isdigit() for c in curr_phone):
                    phone = curr_phone
                    log(f"  [SUCCESS] Lấy số thực tế thành công: {phone}")
                    break
            except Exception as e:
                log(f"  Poll số điện thoại thất bại: {e}")
        
        if not phone or "xin số" in phone or not any(c.isdigit() for c in phone):
            log("❌ Không lấy được số điện thoại thực tế từ API sau 15s — đang hủy số...")
            try:
                requests.get(f"{get_sms_base()}/api/ext/cancel", params={"apikey": apikey, "pkey": pkey}, timeout=10)
            except:
                pass
            raise RuntimeError("Không lấy được số điện thoại thực tế từ API!")

    log(f"✅ Phone: {phone} | pkey: {pkey[:12]}...")
    return {
        "phone":      phone,
        "pkey":       pkey,
        "country":    country
    }

def poll_sms_otp(pkey: str, timeout: int = 180, poll_interval: int = 5) -> str:
    deadline = time.time() + timeout
    log(f"⏳ Poll OTP | pkey: {pkey[:12]}... | timeout: {timeout}s")

    while time.time() < deadline:
        try:
            apikey = _get_apikey()
            resp = requests.get(
                f"{get_sms_base()}/api/ext/getSms",
                params={"apikey": apikey, "pkey": pkey},
                timeout=10,
            )
            data = resp.json()
            
            if data.get("status") == "error":
                msg = str(data.get("message", data.get("msg", "")))
                if "không hợp lệ" in msg.lower():
                    log("API key lỗi lúc poll, xoá cache...")
                    clear_cache()
                    continue

            otp = data.get("otp", "")
            state = data.get("state", "")

            if otp and state == "Hoàn thành":
                log(f"✅ SMS OTP: {otp}")
                return otp

        except Exception as e:
            log(f"  getSms lỗi: {e}")

        time.sleep(poll_interval)

    log(f"⏰ Timeout {timeout}s — không nhận được SMS OTP")
    return None

def cancel(pkey: str, retry: bool = True) -> bool:
    try:
        apikey = _get_apikey()
        resp = requests.get(
            f"{get_sms_base()}/api/ext/cancel",
            params={"apikey": apikey, "pkey": pkey},
            timeout=10,
        )
        data = resp.json()
        if data.get("status") == "success":
            log("✅ Hủy số thành công")
            return True
            
        msg = str(data.get("message", data.get("msg", data)))
        if "không hợp lệ" in msg.lower() and retry:
            clear_cache()
            return cancel(pkey, retry=False)
            
        log(f"Hủy số thất bại: {msg}")
    except Exception as e:
        log(f"cancel lỗi: {e}")
    return False
