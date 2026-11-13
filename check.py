import json
import urllib.error
import urllib.request

TARGETS = {"USDT", "BTC", "ETH", "TRX", "TON", "GRAM", "PAXG", "OIL", "GOLD", "XAU"}


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def cut(obj, n=450):
    return json.dumps(obj, ensure_ascii=False)[:n]


print("===== WALLEX =====")
st, body = get("https://api.wallex.ir/v1/markets")
print("status:", st)
try:
    syms = json.loads(body)["result"]["symbols"]
    first = next(iter(syms.values()))
    print("sample entry keys:", list(first.keys()))
    print("sample entry:", cut(first, 700))
    found = {k: v for k, v in syms.items() if v.get("baseAsset") in TARGETS}
    print("matching symbols:", sorted(found.keys()))
    for k in ["USDTTMN", "BTCTMN", "ETHTMN", "TRXTMN", "TONTMN", "GRAMTMN",
              "PAXGUSDT", "PAXGTMN", "BTCUSDT", "TONUSDT", "TRXUSDT", "ETHUSDT"]:
        if k in syms:
            print(k, "->", cut(syms[k].get("stats", syms[k]), 400))
except Exception as e:
    print("parse error:", type(e).__name__, e)

print()
print("===== OMPFINEX =====")
st, body = get("https://api.ompfinex.com/v1/market")
print("status:", st)
try:
    items = json.loads(body)["data"]
    print("count:", len(items))
    print("sample entry keys:", list(items[0].keys()))
    print("sample entry:", cut(items[0], 700))
    hits = [m for m in items if (m.get("base_currency") or {}).get("id") in TARGETS]
    print("matching:", [(m["base_currency"]["id"], (m.get("quote_currency") or {}).get("id"),
                         m.get("id")) for m in hits])
    for m in hits[:6]:
        print("-", cut({k: v for k, v in m.items() if k not in ("base_currency", "quote_currency")}, 400))
except Exception as e:
    print("parse error:", type(e).__name__, e)

print()
print("===== TABDEAL =====")
for path in ["exchangeInfo", "ticker/price", "ticker/24hr"]:
    st, body = get("https://api1.tabdeal.org/r/api/v1/" + path)
    print(f"/{path}: status {st} | {body[:200].replace(chr(10), ' ')}")
    if path == "exchangeInfo" and st == 200:
        try:
            s = json.loads(body).get("symbols", [])
            names = [x.get("symbol") for x in s]
            print("symbol count:", len(names))
            print("matching:", [n for n in names if n and any(
                n.startswith(t) for t in TARGETS)][:60])
        except Exception as e:
            print("parse error:", type(e).__name__, e)
