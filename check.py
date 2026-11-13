import urllib.error
import urllib.request

# آدرس‌هایی که امتحان می‌شوند. بعضی‌ها ممکن است آدرس درستی نباشند؛ اشکالی ندارد.
URLS = [
    ("Nobitex", "https://api.nobitex.ir/market/stats?srcCurrency=usdt&dstCurrency=rls"),
    ("Wallex", "https://api.wallex.ir/v1/markets"),
    ("OMPFinex", "https://api.ompfinex.com/v1/market"),
    ("Tabdeal", "https://api1.tabdeal.org/r/api/v1/depth?symbol=BTCUSDT"),
    ("Telegram", "https://api.telegram.org"),
    ("Binance", "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"),
    ("CoinGecko", "https://api.coingecko.com/api/v3/ping"),
]

for name, url in URLS:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            body = r.read(200).decode("utf-8", "replace").replace("\n", " ")
            print(f"[OK ] {name}: HTTP {r.status} | {body[:120]}")
    except urllib.error.HTTPError as e:
        # سرور جواب داده (مثلاً 403 یا 404)؛ یعنی آدرس پیدا شده
        print(f"[REACHED] {name}: HTTP {e.code}")
    except Exception as e:
        print(f"[FAIL] {name}: {type(e).__name__}: {e}")
