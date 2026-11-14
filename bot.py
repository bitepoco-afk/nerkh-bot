import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

CHAT_ID = os.environ.get("CHAT_ID", "@nerkh_roooz")
UA = {"User-Agent": "Mozilla/5.0"}
TEHRAN = timezone(timedelta(hours=3, minutes=30))

# دارایی‌ها: (نماد, نام فارسی). برای افزودن یا حذف ارز همین لیست را عوض کنید.
ASSETS = [
    ("BTC", "بیتکوین"),
    ("ETH", "اتریوم"),
    ("XRP", "ریپل"),
    ("TRX", "ترون"),
    ("GRAM", "گرام (تون)"),
    ("XAUT", "تتر گلد"),
    ("PAXG", "پکس گلد"),
]
SYMS = [a for a, _ in ASSETS]

# "T" = قیمت به تومان، "U" = قیمت به دلار (تتر)
# منبعی «سالم» است که این سه قیمت را داشته باشد
CORE = [("USDT", "T"), ("BTC", "T"), ("BTC", "U")]

FA = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


# ----------------------------------------------------------------- ابزارها
def fa(s):
    return str(s).translate(FA)


def num(x):
    """عدد مثبت یا None (مثلاً برای '-' یا صفر)."""
    try:
        v = float(str(x).replace(",", "").strip())
    except (TypeError, ValueError):
        return None
    return v if v == v and v > 0 else None


def flt(x):
    """عدد (حتی منفی) یا None."""
    try:
        v = float(str(x).replace(",", "").strip())
    except (TypeError, ValueError):
        return None
    return v if v == v else None


def http_get(url, timeout=20, tries=2):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            last = e
            if e.code in (400, 401, 403, 404, 451):
                break
        except Exception as e:  # noqa: BLE001
            last = e
        if i + 1 < tries:
            time.sleep(1.5)
    raise last


def http_json(url, timeout=20, tries=2):
    return json.loads(http_get(url, timeout, tries))


def g2j(gy, gm, gd):
    """تبدیل تاریخ میلادی به شمسی."""
    g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    gy2 = gy + 1 if gm > 2 else gy
    days = (355666 + (365 * gy) + ((gy2 + 3) // 4) - ((gy2 + 99) // 100)
            + ((gy2 + 399) // 400) + gd + g_d_m[gm - 1])
    jy = -1595 + (33 * (days // 12053))
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    if days < 186:
        jm = 1 + days // 31
        jd = 1 + days % 31
    else:
        jm = 7 + (days - 186) // 30
        jd = 1 + (days - 186) % 30
    return jy, jm, jd


# ------------------------------------------------------------------ صرافی‌ها
# هر تابع یک دیکشنری برمی‌گرداند: {(نماد, "T" یا "U"): (قیمت, درصد تغییر یا None)}
def src_nobitex():
    q, reached = {}, False
    for sym in ["usdt"] + [s.lower() for s in SYMS]:
        dst = "rls" if sym == "usdt" else "rls,usdt"
        url = ("https://api.nobitex.ir/market/stats?srcCurrency=%s&dstCurrency=%s"
               % (sym, dst))
        try:
            d = http_json(url, tries=1)
        except urllib.error.HTTPError:
            reached = True
            continue
        except Exception:  # noqa: BLE001
            if not reached:
                raise  # اتصال اصلاً برقرار نیست؛ این منبع از کار افتاده
            continue
        reached = True
        if d.get("status") != "ok":
            continue
        for key, s in (d.get("stats") or {}).items():
            try:
                a, b = key.split("-")
            except ValueError:
                continue
            p = num(s.get("latest"))
            if not p:
                continue
            ch = flt(s.get("dayChange"))
            if b == "rls":
                q[(a.upper(), "T")] = (p / 10, ch)  # ریال به تومان
            elif b == "usdt":
                q[(a.upper(), "U")] = (p, ch)
    return q


def src_wallex():
    syms = http_json("https://api.wallex.ir/v1/markets")["result"]["symbols"]
    q = {}

    def put(sym, asset, kind):
        st = (syms.get(sym) or {}).get("stats") or {}
        p = num(st.get("lastPrice"))
        if p:
            q[(asset, kind)] = (p, flt(st.get("24h_ch")))

    put("USDTTMN", "USDT", "T")
    for a in SYMS:
        put(a + "TMN", a, "T")
        put(a + "USDT", a, "U")
    return q


def src_omp():
    items = http_json("https://api.ompfinex.com/v1/market")["data"]
    wanted = set(SYMS) | {"USDT"}
    q = {}
    for m in items:
        base = (m.get("base_currency") or {}).get("id")
        quote = (m.get("quote_currency") or {}).get("id")
        if base not in wanted:
            continue
        p = num(m.get("last_price"))
        if not p:
            continue
        ch = flt(m.get("day_change_percent"))
        if quote == "IRR":  # قیمت به ریال است
            q.setdefault((base, "T"), (p / 10, ch))
        elif quote == "USDT" and base != "USDT":
            q.setdefault((base, "U"), (p, ch))
    return q


def src_exir():
    t = http_json("https://api.exir.io/v2/tickers")
    q = {}

    def put(sym, asset, kind):
        s = t.get(sym) or {}
        p = num(s.get("last"))
        if not p:
            return
        o = num(s.get("open"))
        ch = (p - o) / o * 100 if o else None
        q[(asset, kind)] = (p, ch)

    put("usdt-irt", "USDT", "T")
    for a in SYMS:
        put(a.lower() + "-irt", a, "T")
        put(a.lower() + "-usdt", a, "U")
    return q


def src_tabdeal():
    t0 = time.monotonic()
    q = {}

    def put(sym, asset, kind):
        if time.monotonic() - t0 > 90:
            raise RuntimeError("Tabdeal too slow")
        try:
            d = http_json(
                "https://api1.tabdeal.org/r/api/v1/trades?symbol=%s&limit=1" % sym,
                timeout=15, tries=1)
        except urllib.error.HTTPError:
            return
        p = num(d[0].get("price")) if d else None
        if p:
            q[(asset, kind)] = (p, None)  # تبدیل درصد تغییر نمی‌دهد

    put("USDTIRT", "USDT", "T")
    for a in SYMS:
        put(a + "IRT", a, "T")
        put(a + "USDT", a, "U")
    return q


# ترتیب اولویت: اولین منبع سالم استفاده می‌شود
SOURCES = [
    ("نوبیتکس", src_nobitex),
    ("والکس", src_wallex),
    ("اُمپ‌فینکس", src_omp),
    ("اکسیر", src_exir),
    ("تبدیل", src_tabdeal),
]


def pick_source():
    for name, fn in SOURCES:
        try:
            q = fn()
        except Exception as e:  # noqa: BLE001
            print(f"[skip] {name}: {type(e).__name__}: {e}")
            continue
        missing = [k for k in CORE if k not in q]
        if missing:
            print(f"[skip] {name}: missing core prices {missing}")
            continue
        print(f"[use] {name}: {len(q)} prices")
        return name, q
    raise RuntimeError("No healthy price source; nothing posted")


# ---------------------------------------------------------- طلا، سکه و نفت
def get_tgju(now):
    """قیمت طلای ۱۸ عیار و سکه امامی از tgju (به تومان)."""
    cur, last = None, None
    for host in ("call3", "call5"):
        try:
            cur = http_json("https://%s.tgju.org/ajax.json" % host)["current"]
            break
        except Exception as e:  # noqa: BLE001
            last = e
    if cur is None:
        raise last
    out = {}
    for key in ("geram18", "sekee"):
        e = cur.get(key) or {}
        p = num(e.get("p"))
        if not p:
            continue
        try:  # قیمت قدیمی (بیش از ۳ روز) نمایش داده نمی‌شود
            ts = datetime.strptime(e.get("ts", ""), "%Y-%m-%d %H:%M:%S")
            if now.replace(tzinfo=None) - ts > timedelta(days=3):
                continue
        except ValueError:
            continue
        dp = flt(e.get("dp"))
        if dp is not None:
            dp = -abs(dp) if e.get("dt") == "low" else abs(dp)
        out[key] = (p / 10, dp)  # ریال به تومان
    return out


def get_brent():
    """قیمت هر بشکه نفت برنت به دلار از Yahoo Finance."""
    d = http_json("https://query1.finance.yahoo.com/v8/finance/chart/BZ=F"
                  "?interval=1d&range=1d")
    meta = d["chart"]["result"][0]["meta"]
    p = num(meta.get("regularMarketPrice"))
    if not p:
        return None
    prev = num(meta.get("chartPreviousClose")) or num(meta.get("previousClose"))
    ch = (p - prev) / prev * 100 if prev else None
    return p, ch


def safe(label, fn, *args):
    try:
        return fn(*args)
    except Exception as e:  # noqa: BLE001
        print(f"[skip] {label}: {type(e).__name__}: {e}")
        return None


# -------------------------------------------------------------- ساخت پیام
def dot(ch):
    if ch is None or round(ch, 2) == 0:
        return "⚪"
    return "🟢" if ch > 0 else "🔴"


def pct(ch, persian):
    if ch is None:
        return ""
    if round(ch, 2) == 0:
        s = "0.00"
        return f" ({fa(s)}٪)" if persian else f" ({s}%)"
    arrow = "↑" if ch > 0 else "↓"
    s = f"{abs(ch):.2f}"
    return f" ({arrow}{fa(s)}٪)" if persian else f" ({arrow}{s}%)"


def fmt_usd(p):
    if p >= 100:
        return f"{p:,.0f}"
    if p >= 1:
        return f"{p:,.2f}"
    return f"{p:.6f}".rstrip("0").rstrip(".")


def fmt_toman(p):
    return fa(f"{p:,.0f}")


def build_message(src_name, q, tgju, brent, now):
    usd_lines = []
    for sym, _ in ASSETS:
        v = q.get((sym, "U"))
        if v:
            usd_lines.append(f"{dot(v[1])} {sym}: ${fmt_usd(v[0])}{pct(v[1], False)}")

    toman_lines = []
    for sym, name in [("USDT", "تتر")] + ASSETS:
        v = q.get((sym, "T"))
        if v:
            toman_lines.append(
                f"{dot(v[1])} {name}: {fmt_toman(v[0])} تومان{pct(v[1], True)}")

    extra = []
    sources = [f"منبع: {src_name}"]
    if brent:
        extra.append(f"{dot(brent[1])} نفت برنت (هر بشکه): "
                     f"${brent[0]:.2f}{pct(brent[1], False)}")
        sources.append("نفت: Yahoo Finance")
    g18 = (tgju or {}).get("geram18")
    if g18:
        extra.append(f"{dot(g18[1])} طلای ۱۸ عیار: {fmt_toman(g18[0])} تومان{pct(g18[1], True)}")
    else:
        paxg = q.get(("PAXG", "T"))
        if paxg:  # جایگزین محاسباتی وقتی tgju در دسترس نیست
            est = paxg[0] / 31.1035 * 0.75
            extra.append(f"{dot(paxg[1])} طلای ۱۸ عیار (محاسباتی): "
                         f"{fmt_toman(est)} تومان{pct(paxg[1], True)}")
    coin = (tgju or {}).get("sekee")
    if coin:
        extra.append(f"{dot(coin[1])} سکه امامی: {fmt_toman(coin[0])} تومان{pct(coin[1], True)}")
    if tgju:
        sources.append("طلا و سکه: tgju")

    if not (usd_lines or toman_lines):
        raise RuntimeError("No prices to post")

    jy, jm, jd = g2j(now.year, now.month, now.day)
    footer = (f"⏰ {fa(now.strftime('%H:%M'))} – {fa(f'{jy}/{jm:02d}/{jd:02d}')}\n"
              + " | ".join(sources))

    parts = ["📊 <b>قیمت لحظه‌ای بازار</b>"]
    for block in (usd_lines, toman_lines, extra):
        if block:
            parts.append("\n".join(block))
    parts.append(footer)
    return "\n\n".join(parts)


def send(text):
    token = os.environ["BOT_TOKEN"]
    body = urllib.parse.urlencode({
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": "true",
    }).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage", data=body)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            print(r.read().decode())
    except urllib.error.HTTPError as e:
        print("Telegram error:", e.code, e.read().decode("utf-8", "replace"))
        raise


def main():
    now = datetime.now(TEHRAN)
    src_name, q = pick_source()
    tgju = safe("tgju", get_tgju, now)
    brent = safe("brent", get_brent)
    text = build_message(src_name, q, tgju, brent, now)
    print(text)
    send(text)


if __name__ == "__main__":
    main()
