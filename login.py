#!/usr/bin/env python3
"""Standalone QR login script — run this once to get credentials.json."""
import asyncio
import json
import sys
import time
from pathlib import Path

import httpx

BASE_URL = "https://ilinkai.weixin.qq.com"
BOT_TYPE = "3"
QR_LONG_POLL_TIMEOUT = 35.0
LOGIN_TOTAL_TIMEOUT = 5 * 60   # 5 minutes
MAX_QR_REFRESH = 3


async def fetch_qr(base_url: str) -> dict:
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(f"{base_url}/ilink/bot/get_bot_qrcode?bot_type={BOT_TYPE}")
        resp.raise_for_status()
        return resp.json()


async def poll_status(base_url: str, qrcode: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=QR_LONG_POLL_TIMEOUT + 2) as client:
            resp = await client.get(
                f"{base_url}/ilink/bot/get_qrcode_status?qrcode={qrcode}",
                headers={"iLink-App-ClientVersion": "1"},
                timeout=QR_LONG_POLL_TIMEOUT,
            )
            resp.raise_for_status()
            return resp.json()
    except httpx.TimeoutException:
        return {"status": "wait"}


def show_qr(url: str) -> None:
    print(f"\n二维码链接：{url}\n")
    try:
        import qrcode
        qr = qrcode.QRCode()
        qr.add_data(url)
        qr.make(fit=True)
        qr.print_ascii(invert=True)
    except ImportError:
        print("（提示：安装 qrcode[pil] 可在终端显示二维码图形）")


async def login(base_url: str = BASE_URL) -> dict:
    print("正在获取登录二维码…")
    qr_resp = await fetch_qr(base_url)
    qrcode_id: str = qr_resp["qrcode"]
    qrcode_url: str = qr_resp["qrcode_img_content"]
    show_qr(qrcode_url)
    print("请用手机微信扫描上方二维码，然后在微信中确认授权。\n")

    deadline = time.time() + LOGIN_TOTAL_TIMEOUT
    refresh_count = 0
    scanned = False

    while time.time() < deadline:
        status_resp = await poll_status(base_url, qrcode_id)
        status = status_resp.get("status", "wait")

        if status == "scaned" and not scanned:
            print("✅ 已扫码，请在手机上点击确认…")
            scanned = True

        elif status == "confirmed":
            return {
                "token": status_resp.get("bot_token", ""),
                "base_url": status_resp.get("baseurl", base_url),
                "bot_id": status_resp.get("ilink_bot_id", ""),
                "user_id": status_resp.get("ilink_user_id", ""),
            }

        elif status == "expired":
            refresh_count += 1
            if refresh_count > MAX_QR_REFRESH:
                raise RuntimeError("二维码多次过期，登录超时，请重新运行 login.py")
            print(f"⏳ 二维码已过期，正在刷新（{refresh_count}/{MAX_QR_REFRESH}）…")
            qr_resp = await fetch_qr(base_url)
            qrcode_id = qr_resp["qrcode"]
            qrcode_url = qr_resp["qrcode_img_content"]
            scanned = False
            show_qr(qrcode_url)

        await asyncio.sleep(1)

    raise TimeoutError("登录超时（5 分钟），请重新运行 login.py")


def main() -> None:
    try:
        credentials = asyncio.run(login())
    except (RuntimeError, TimeoutError) as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n已取消")
        sys.exit(0)

    out = Path("credentials.json")
    out.write_text(json.dumps(credentials, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n✅ 登录成功！凭证已保存到 {out}")
    print(f"   bot_id : {credentials.get('bot_id')}")
    print(f"   user_id: {credentials.get('user_id')}")
    print(f"   base_url: {credentials.get('base_url')}")
    print("\n接下来：编辑 config.yaml，填入 LLM provider 配置，然后运行：")
    print("   python -m src.main")


if __name__ == "__main__":
    main()
