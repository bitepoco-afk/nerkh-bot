import json
import urllib.error
import urllib.request

UA = {"User-Agent": "Mozilla/5.0"}
COINS = ["XRP", "XAUT", "USOON", "PAXG"]


def get(url, timeout=20):
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:  # noqa: BLE001
        return None, f"{type(e).__name__}: {e}"


def snippet(body, word, width=170):
    i = body.lower().find(word.lower())
    if i < 0:
        return None
    return body[max(0, i - 30): i + width].replace("\n", " ")


def head(title):
    print()
    print("=" * 8, title, "=" * 8, flush=True)


def line(msg):
    print(msg, flush=True)


# ---------------------------------------------------------------- 1) صرافی‌ها
head("1) EXCHANGES: reachability + coins")
EXCHANGES = [
    ("Nobitex", "https://api.nobitex.ir/market/stats?srcCurrency=btc,usdt,xrp,xaut,paxg&dstCurrency=rls,usdt"),
    ("Wallex", "https://api.wallex.ir/v1/markets"),
    ("OMPFinex", "https://api.ompfinex.com/v1/market"),
    ("Tabdeal", "https://api1.tabdeal.org/r/api/v1/exchangeInfo"),
    ("Bitpin (URL is a guess)", "https://api.bitpin.ir/api/v1/mkt/tickers/"),
    ("Ramzinex (URL is a guess)", "https://publicapi.ramzinex.com/exchange/api/v1.0/exchange/pairs"),
    ("Exir (URL is a guess)", "https://api.exir.io/v2/tickers"),
]
bodies = {}
for name, url in EXCHANGES:
    st, body = get(url)
    bodies[name] = body
    if st is None:
        line(f"[FAIL] {name}: {body}")
        continue
    line(f"[{'OK' if st == 200 else 'HTTP ' + str(st)}] {name}: status={st}, size={len(body)}")
    if st != 200:
        continue
    for c in COINS:
        s = snippet(body, c)
        line(f"    {c}: {'FOUND -> ' + s if s else 'not found'}")

# جزئیات دقیق‌تر والکس و اُمپ‌فینکس
head("1b) Wallex details")
try:
    syms = json.loads(bodies["Wallex"])["result"]["symbols"]
    for k, v in sorted(syms.items()):
        if v.get("baseAsset") in COINS or k in ("PAXGTMN", "PAXGUSDT"):
            st = v.get("stats", {})
            line(f"  {k}: last={st.get('lastPrice')} ch24={st.get('24h_ch')}")
except Exception as e:  # noqa: BLE001
    line(f"  parse error: {type(e).__name__}: {e}")

head("1c) OMPFinex details")
try:
    for m in json.loads(bodies["OMPFinex"])["data"]:
        b = (m.get("base_currency") or {}).get("id")
        if b in COINS:
            q = (m.get("quote_currency") or {}).get("id")
            line(f"  {b}/{q}: last={m.get('last_price')} ch24={m.get('day_change_percent')}")
except Exception as e:  # noqa: BLE001
    line(f"  parse error: {type(e).__name__}: {e}")

head("1d) Tabdeal symbols + price endpoint guesses")
try:
    names = [x.get("symbol") for x in json.loads(bodies["Tabdeal"])]
    line("  symbols: " + str([n for n in names if n and n.split("_")[0][:3] in ("XRP", "XAU", "USO", "PAX")]))
except Exception as e:  # noqa: BLE001
    line(f"  parse error: {type(e).__name__}: {e}")
for path in [
    "ticker/24hr?symbol=BTCUSDT",
    "ticker/price?symbol=BTCUSDT",
    "klines?symbol=BTCUSDT&interval=1m&limit=1",
    "trades?symbol=BTCUSDT&limit=1",
    "depth?symbol=XRPUSDT&limit=5",
]:
    st, body = get("https://api1.tabdeal.org/r/api/v1/" + path)
    line(f"  /{path}: status={st} | {body[:140]}")

# ------------------------------------------------------------ 2) قیمت بشکه نفت
head("2) GLOBAL OIL (per barrel, USD)")
for label, sym in [("Brent", "BZ=F"), ("WTI", "CL=F")]:
    st, body = get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1d&range=1d")
    try:
        meta = json.loads(body)["chart"]["result"][0]["meta"]
        line(f"[OK] Yahoo {label}: price={meta.get('regularMarketPrice')} prevClose={meta.get('chartPreviousClose')}")
    except Exception:  # noqa: BLE001
        line(f"[FAIL] Yahoo {label}: status={st} | {body[:120]}")
for label, sym in [("Brent", "cb.f"), ("WTI", "cl.f")]:
    st, body = get(f"https://stooq.com/q/l/?s={sym}&f=sd2t2ohlc&h&e=csv")
    line(f"[{st}] Stooq {label}: {body[:160].strip()}")

# --------------------------------------------- 3) سکه امامی و طلای ۱۸ عیار ایران
head("3) IRAN GOLD / EMAMI COIN sources")
GOLD = [
    ("TGJU ajax call3", "https://call3.tgju.org/ajax.json"),
    ("TGJU ajax call5", "https://call5.tgju.org/ajax.json"),
    ("TGJU website", "https://www.tgju.org/"),
    ("Talasea (URL is a guess)", "https://api.talasea.ir/api/market/getGoldPrice"),
]
for name, url in GOLD:
    st, body = get(url)
    if st is None:
        line(f"[FAIL] {name}: {body}")
        continue
    line(f"[{'OK' if st == 200 else 'HTTP ' + str(st)}] {name}: status={st}, size={len(body)}")
    if st != 200:
        continue
    for kw in ["sekee", "geram18", "سکه امامی", "طلای 18"]:
        s = snippet(body, kw, 230)
        if s:
            line(f"    {kw}: {s}")

print()
print("DONE", flush=True)
