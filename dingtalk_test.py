import os
import time
import hmac
import base64
import hashlib
import urllib.parse
import requests


def load_env(path=".env"):
    if not os.path.exists(path):
        raise FileNotFoundError(".env 文件不存在")

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            if "=" in line:
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip()


def build_signed_url(webhook, secret):
    timestamp = str(round(time.time() * 1000))
    string_to_sign = f"{timestamp}\n{secret}"

    hmac_code = hmac.new(
        secret.encode("utf-8"),
        string_to_sign.encode("utf-8"),
        digestmod=hashlib.sha256
    ).digest()

    sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
    return f"{webhook}&timestamp={timestamp}&sign={sign}"


def send_dingtalk_markdown(title, text):
    webhook = os.getenv("DINGTALK_WEBHOOK")
    secret = os.getenv("DINGTALK_SECRET")

    if not webhook:
        raise ValueError("缺少 DINGTALK_WEBHOOK")
    if not secret:
        raise ValueError("缺少 DINGTALK_SECRET")

    url = build_signed_url(webhook, secret)

    payload = {
        "msgtype": "markdown",
        "markdown": {
            "title": title,
            "text": text
        }
    }

    response = requests.post(url, json=payload, timeout=10)
    print("HTTP状态码：", response.status_code)
    print("钉钉返回：", response.text)


def main():
    load_env()

    title = "BTC/ETH 看盘系统测试"
    text = """### ✅ BTC/ETH 看盘系统测试

机器人连接成功。

- 系统：V3.1
- 状态：钉钉 webhook 已打通
- 下一步：只在允许出手时推送信号
"""

    send_dingtalk_markdown(title, text)


if __name__ == "__main__":
    main()
