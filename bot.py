import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ.get("CHAT_ID", "@nerkh_roooz")

# منبع قیمت: صرافی والکس (قیمت‌ها از قبل به تومان هستند)
WALLEX_URL = "https://api.wallex.ir/v1/markets"

# (نماد پایه در والکس, نام فارسی) -- برای افزودن یا حذف ارز همین لیست را عوض کنید
COINS = [
    ("BTC", "بیتکوین"),
    ("ETH", "اتریوم"),
    ("TRX", "ترون"),
    ("GRAM", "گرام (تون)"),
]

FA = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def fa(s):
    return str(s).translate(FA)


def fetch_markets():
    last = None
    for _ in range(3):
        try:
            req = urllib.request.Request(
                WALLEX_URL, headers={"User-Agent": "Mozilla/5.0"}
            )
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)["result"]["symbols"]
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(3)
    raise RuntimeError(f"Wallex fetch failed: {last}")


def get(syms, symbol):
    """قیمت آخر و درصد تغییر ۲۴ ساعته؛ اگر نبود (None, None)."""
    stats = (syms.get(symbol) or {}).get("stats") or {}
    try:
        price = float(stats["lastPrice"])
    except (KeyError, ValueError, TypeError):
        return None, None
    try:
        change = float(stats["24h_ch"])
    except (KeyError, ValueError, TypeError):
        change = 0.0
    return price, change


def dot(change):
    return "🟢" if change >= 0 else "🔴"


def fmt_usd(p):
    if p >= 100:
        return f"{p:,.0f}"
    if p >= 1:
        return f"{p:,.2f}"
    return f"{p:.6f}".rstrip("0").rstrip(".")


def build_message(syms):
    usd_lines = []
    toman_lines = []

    # بخش دلاری
    for base, _ in COINS:
        p, ch = get(syms, base + "USDT")
        if p is None:
            continue
        arrow = "↑" if ch >= 0 else "↓"
        usd_lines.append(f"{dot(ch)} {base}: ${fmt_usd(p)} ({arrow}{abs(ch):.2f}%)")

    # بخش تومانی: اول تتر، بعد بقیه
    for base, name in [("USDT", "تتر")] + COINS:
        p, ch = get(syms, base + "TMN")
        if p is None:
            continue
        arrow = "↑" if ch >= 0 else "↓"
        toman_lines.append(
            f"{dot(ch)} {name}: {fa(f'{p:,.0f}')} تومان ({arrow}{fa(f'{abs(ch):.2f}')}٪)"
        )

    if not usd_lines and not toman_lines:
        raise RuntimeError("No prices found in Wallex response")

    # طلای ۱۸ عیار: محاسباتی از روی PAXG (هر PAXG برابر یک اونس طلا)
    gold_block = ""
    paxg_tmn, _ = get(syms, "PAXGTMN")
    paxg_usd, _ = get(syms, "PAXGUSDT")
    if paxg_tmn:
        gram18 = paxg_tmn / 31.1035 * 0.75
        gold_block = (
            "\n\n<blockquote expandable>🟡 قیمت طلا (محاسباتی از روی PAXG)\n"
            f"طلای ۱۸ عیار: {fa(f'{gram18:,.0f}')} تومان"
        )
        if paxg_usd:
            gold_block += f"\nاونس جهانی: ${fmt_usd(paxg_usd)}"
        gold_block += "</blockquote>"

    tehran = datetime.now(timezone(timedelta(hours=3, minutes=30)))
    footer = (
        f"\n\n⏰ {fa(tehran.strftime('%H:%M'))} – {fa(tehran.strftime('%Y/%m/%d'))}"
        "\nمنبع: والکس"
    )

    parts = ["📊 <b>قیمت لحظه‌ای بازار</b>"]
    if usd_lines:
        parts.append("\n".join(usd_lines))
    if toman_lines:
        parts.append("\n".join(toman_lines))
    return "\n\n".join(parts) + gold_block + footer


def send(text):
    body = urllib.parse.urlencode(
        {
            "chat_id": CHAT_ID,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": "true",
        }
    ).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data=body
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            print(r.read().decode())
    except urllib.error.HTTPError as e:
        # متن خطای تلگرام را چاپ می‌کنیم تا علت مشخص شود
        print("Telegram error:", e.code, e.read().decode("utf-8", "replace"))
        raise


if __name__ == "__main__":
    send(build_message(fetch_markets()))
