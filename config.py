import json
import os

TWOCAPTCHA_API_KEY = ""
CAPTCHA_ENABLED = True
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
GLOBAL_STOP = False

try:
    with open("config.json", "r") as f:
        _config = json.load(f)
        if "twocaptcha_key" in _config:
            TWOCAPTCHA_API_KEY = _config["twocaptcha_key"]
except Exception:
    pass
