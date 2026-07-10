import requests
import hashlib
import json
import re
import sys
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

BASE_URL = "https://web.chelaile.net.cn/api"
AES_KEY = b"FF32AE65FBFD19414EAAFF6291A54B42"
SIGN_SALT = "qwihrnbtmj"

class PresetBuilder:
    def __init__(self):
        self._d = {}

    def add(self, key, value):
        self._d[key] = value
        return self

    def build(self):
        return dict(self._d)

def build_preset():
    return (
        PresetBuilder()
        .add("s", "h5")
        .add("wxs", "wx_app")
        .add("sign", "1")
        .add("h5RealData", 1)
        .add("v", "3.11.40")
        .add("src", "weixinapp_cx")
        .add("ctm_mp", "mp_wx")
        .add("vc", "2")
        .add("cityId", "014")
        .add("favoriteGray", 1)
        .add("localCityId", "014")
        .add("userId", "okBHq0BC3EzD75QaWtkEItKTwLBs")
        .add("h5Id", "okBHq0BC3EzD75QaWtkEItKTwLBs")
        .add("unionId", "oSpTTjheiUKyzCDJmRqpWWCL36O0")
        .add("accountId", "")
        .add("secret", "")
        .add("lat", 22.55328941345215)
        .add("lng", 113.8830795288086)
        .add("geo_lat", 22.55328941345215)
        .add("geo_lng", 113.8830795288086)
        .add("gpstype", "wgs")
        .add("geo_type", "wgs")
        .add("scene", 1256)
        .build()
    )

PRESET = build_preset()

def merge_preserved_order(base, extra):
    result = dict(base)
    for k, v in extra.items():
        result[k] = v
    return result

def make_sign(data: dict) -> str:
    raw = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
    sign_input = raw[1:-1].replace(":", "=").replace(",", "&") + SIGN_SALT
    return hashlib.md5(sign_input.encode()).hexdigest()

def decrypt(encrypted: str) -> dict:
    if re.match(r'^[0-9a-f]+$', encrypted):
        raw = bytes.fromhex(encrypted)
    else:
        import base64
        raw = base64.b64decode(encrypted)
    cipher = AES.new(AES_KEY, AES.MODE_ECB)
    try:
        dec = unpad(cipher.decrypt(raw), AES.block_size)
    except ValueError:
        dec = cipher.decrypt(raw)
    return json.loads(dec.decode("utf-8"))

def parse_response(text: str) -> dict:
    m = re.search(r'\*\*YGKJ(.+?)YGKJ##', text)
    if m:
        wrapper = json.loads(m.group(1))
        if wrapper["jsonr"]["status"] != "00":
            raise Exception(f"API error: status={wrapper['jsonr']['status']}, msg={wrapper['jsonr'].get('errmsg')}")
        data = wrapper["jsonr"]["data"]
        if "encryptResult" in data:
            return decrypt(data["encryptResult"])
        return data
    return json.loads(text)

def api_get(endpoint: str, params: dict = None) -> dict:
    full = merge_preserved_order(PRESET, params or {})
    sign = make_sign(full)
    full["cryptoSign"] = sign
    url = f"{BASE_URL}{endpoint}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0.0.0 MicroMessenger/7.0.20.1781 MiniProgramEnv/Windows WindowsWechat/WMPF",
        "xweb_xhr": "1",
        "Referer": "https://servicewechat.com/wx71d589ea01ce3321/828/page-frame.html",
        "Accept": "*/*",
    }
    resp = requests.get(url, params=full, headers=headers, timeout=15, verify=False)
    resp.encoding = "utf-8"
    return parse_response(resp.text)

if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"

    if cmd == "line_detail":
        line_id = sys.argv[2] if len(sys.argv) > 2 else "0755-07940-1"
        station_id = sys.argv[3] if len(sys.argv) > 3 else "0755-11919"
        target_order = int(sys.argv[4]) if len(sys.argv) > 4 else 13
        result = api_get("/bus/line!encryptedBusDetail.action", {
            "lineId": line_id,
            "targetOrder": target_order,
            "specialTargetOrder": target_order,
            "specail": 0,
            "stationId": station_id,
            "cshow": "busDetail",
        })
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif cmd == "line_info":
        line_id = sys.argv[2] if len(sys.argv) > 2 else "0755-07940-1"
        result = api_get("/bus/line!encryptedLineDetail.action", {
            "lineId": line_id,
            "cityId": "014",
            "grey_city": 0,
            "cshow": "busDetail",
            "permission": 0,
        })
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif cmd == "line_by_no":
        line_no = sys.argv[2] if len(sys.argv) > 2 else "07940"
        direction = int(sys.argv[3]) if len(sys.argv) > 3 else 0
        result = api_get("/bus/line!encryptedLineDetail.action", {
            "cityId": "014",
            "lineNo": line_no,
            "direction": direction,
            "grey_city": 0,
            "permission": 0,
        })
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif cmd == "real_time":
        line_stn = sys.argv[2] if len(sys.argv) > 2 else "0755-07940-1,0755-11919,,28"
        result = api_get("/bus/line!encryptedTsfRealInfos.action", {
            "lineStn": line_stn,
            "reqSrc": 2,
            "permission": 0,
        })
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif cmd == "search":
        keyword = sys.argv[2] if len(sys.argv) > 2 else "E36"
        result = api_get("/bus/query!nSearch.action", {
            "key": keyword,
            "supportPhyStn": "true",
        })
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif cmd == "city_config":
        result = api_get("/bus/cityMaxInterval.action", {
            "cityId": "014",
            "src": "weixinapp_cx",
        })
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif cmd == "sign_test":
        test_data = merge_preserved_order(PRESET, {
            "lineId": "0755-07940-0",
            "targetOrder": 6,
            "specialTargetOrder": 6,
            "specail": 0,
            "stationId": "0755-3426",
            "cshow": "busDetail",
        })
        print("Sign:", make_sign(test_data))
        print("Expected: 453634c672d2c90d593d713a0cba2c27")

    else:
        print("Usage:")
        print("  python chelaile_api.py search <keyword>")
        print("  python chelaile_api.py line_detail <lineId>")
        print("  python chelaile_api.py line_info <lineId>")
        print("  python chelaile_api.py line_by_no <lineNo> <direction>")
        print("  python chelaile_api.py real_time <lineStn>")
        print("  python chelaile_api.py city_config")
        print("  python chelaile_api.py sign_test")
