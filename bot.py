import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ.get("CHAT_ID", "@nerkh_roooz")

# (نماد نوبیتکس, نام فارسی) -- نمادها را می‌توانید اینجا تغییر دهید
USD_COINS = [
    ("btc", "بیتکوین"),
    ("eth", "اتریوم"),
    ("trx", "ترون"),
    ("gram", "گرام (تون)"),
    ("oil", "توکن نفت"),  # اگر در نوبیتکس نبود، خودکار رد می‌شود
]
TOMAN_COINS = [
    ("usdt", "تتر"),
    ("btc", "بیتکوین"),
    ("eth", "اتریوم"),
    ("trx", "ترون"),
    ("gram", "گرام (تون)"),
]

FA = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def fa(s):
    return str(s).translate(FA)


def fetch_stats():
    symbols = sorted({c for c, _ in USD_COINS + TOMAN_COINS} | {"paxg"})
    qs = urllib.parse.urlencode(
        {"srcCurrency": ",".join(symbols), "dstCurrency": "rls,usdt"}
    )
    req = urllib.request.Request(
        "https://api.nobitex.ir/market/stats?" + qs,
        headers={"User-Agent": "Mozilla/5.0"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    if data.get("status") != "ok":
        raise RuntimeError(f"Nobitex error: {data}")
    return data["stats"]


def get(stats, src, dst):
    s = stats.get(f"{src}-{dst}")
    if not s or not s.get("latest"):
        return None, None
    return float(s["latest"]), float(s.get("dayChange") or 0)


def dot(change):
    return "🟢" if change >= 0 else "🔴"


def fmt_usd(p):
    if p >= 100:
        return f"{p:,.0f}"
    if p >= 1:
        return f"{p:,.2f}"
    return f"{p:.6f}".rstrip("0").rstrip(".")


def build_message(stats):
    lines = []

    # بخش دلاری
    for sym, _ in USD_COINS:
        p, ch = get(stats, sym, "usdt")
        if p is None:
            continue
        arrow = "↑" if ch >= 0 else "↓"
        lines.append(f"{dot(ch)} {sym.upper()}: ${fmt_usd(p)} ({arrow}{abs(ch):.2f}%)")

    lines.append("")

    # بخش تومانی (قیمت‌ها در API به ریال است)
    for sym, name in TOMAN_COINS:
        p, ch = get(stats, sym, "rls")
        if p is None:
            continue
        toman = p / 10
        arrow = "↑" if ch >= 0 else "↓"
        lines.append(
            f"{dot(ch)} {name}: {fa(f'{toman:,.0f}')} تومان ({fa(f'{abs(ch):.2f}')}٪{arrow})"
        )

    # طلای ۱۸ عیار محاسبه‌ای از روی PAXG (هر PAXG = یک اونس)
    paxg, ch = get(stats, "paxg", "usdt")
    usdt_rls, _ = get(stats, "usdt", "rls")
    gold_block = ""
    if paxg and usdt_rls:
        gram18_toman = paxg / 31.1035 * 0.75 * usdt_rls / 10
        gold_block = (
            "\n<blockquote expandable>"
            f"🟡 طلای ۱۸ عیار (محاسباتی): {fa(f'{gram18_toman:,.0f}')} تومان\n"
            f"اونس جهانی (PAXG): ${fmt_usd(paxg)}"
            "</blockquote>"
        )

    tehran = datetime.now(timezone(timedelta(hours=3, minutes=30)))
    footer = f"\n⏰ {fa(tehran.strftime('%H:%M'))} – {fa(tehran.strftime('%Y/%m/%d'))}"

    return "📊 <b>نرخ لحظه‌ای بازار</b>\n\n" + "\n".join(lines) + "\n" + gold_block + footer


def send(text):
    body = urllib.parse.urlencode(
        {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML",
         "disable_web_page_preview": "true"}
    ).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data=body
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        print(r.read().decode())


if __name__ == "__main__":
    send(build_message(fetch_stats()))
