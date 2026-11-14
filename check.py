import json
import urllib.error
import urllib.request

UA = {"User-Agent": "Mozilla/5.0"}


def get(url, timeout=15):
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:  # noqa: BLE001
        return None, f"{type(e).__name__}: {e}"


def head(title):
    print()
    print("=" * 8, title, "=" * 8, flush=True)


# ---------------------------------------------------------------- 1) TGJU
head("1) TGJU: exact keys for coin / gold")
st, body = get("https://call3.tgju.org/ajax.json")
print("status", st, "size", len(body), flush=True)
PREFIXES = ("sek", "nim", "rob", "gerami", "geram18", "geram24", "oil_brent", "ons", "price_dollar_rl")


def walk(o, path=""):
    if isinstance(o, dict):
        for k, v in o.items():
            p = f"{path}/{k}"
            if isinstance(v, dict) and "p" in v:
                yield k, p, v
            else:
                yield from walk(v, p)


try:
    data = json.loads(body)
    n = 0
    for k, p, v in walk(data):
        if k.lower().startswith(PREFIXES):
            print(f"  {p}: p={v.get('p')} dp={v.get('dp')} d={v.get('d')} "
                  f"h={v.get('h')} l={v.get('l')} ts={v.get('ts')}", flush=True)
            n += 1
            if n >= 60:
                break
    print("  entries printed:", n, flush=True)
except Exception as e:  # noqa: BLE001
    print("  parse error:", type(e).__name__, e, flush=True)

# -------------------------------------------------------------- 2) Talasea
head("2) Talasea body")
st, body = get("https://api.talasea.ir/api/market/getGoldPrice")
print("status", st, "|", body[:560].replace("\n", " "), flush=True)

# ----------------------------------------------------------------- 3) Exir
head("3) Exir: toman markets + keys")
st, body = get("https://api.exir.io/v2/tickers")
print("status", st, flush=True)
try:
    t = json.loads(body)
    irt = [k for k in t if k.endswith("-irt")]
    print("  irt markets count:", len(irt), flush=True)
    for k in ["btc-irt", "eth-irt", "usdt-irt", "xrp-irt", "trx-irt", "paxg-irt",
              "xaut-irt", "gram-irt", "ton-irt", "gram-usdt", "ton-usdt", "trx-usdt"]:
        print(f"  {k}: {t.get(k, 'NOT FOUND')}", flush=True)
except Exception as e:  # noqa: BLE001
    print("  parse error:", type(e).__name__, e, flush=True)

# -------------------------------------------------------------- 4) Tabdeal
head("4) Tabdeal: toman trades")
st, body = get("https://api1.tabdeal.org/r/api/v1/exchangeInfo")
try:
    names = [x.get("symbol") for x in json.loads(body)]
    print("  GRAM/TON symbols:", [n for n in names if n and n[:3] in ("GRA", "TON")], flush=True)
except Exception as e:  # noqa: BLE001
    print("  parse error:", type(e).__name__, e, flush=True)
for sym in ["BTCIRT", "USDTIRT", "ETHIRT", "XRPIRT", "TRXIRT", "XAUTIRT", "PAXGIRT", "GRAMIRT"]:
    st, body = get(f"https://api1.tabdeal.org/r/api/v1/trades?symbol={sym}&limit=1")
    print(f"  {sym}: status={st} | {body[:130]}", flush=True)

print()
print("DONE", flush=True)
