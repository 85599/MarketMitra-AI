"""Asset-class detection and per-class benchmark sets."""
import re

CRYPTO_RE = re.compile(r"^[A-Z0-9]{2,10}-[A-Z]{3,4}$")


def asset_class(symbol: str) -> str:
    s = symbol.upper()
    if s.startswith("^"):
        return "index"
    if s.endswith("=F"):
        return "commodity"
    if s.endswith("=X"):
        return "forex"
    if CRYPTO_RE.match(s):
        return "crypto"
    return "equity"


BENCH_BY_CLASS = {
    "equity": {"^NSEI": "Nifty 50", "^GSPC": "S&P 500", "^IXIC": "Nasdaq"},
    "index": {"^GSPC": "S&P 500", "^IXIC": "Nasdaq"},
    "crypto": {"BTC-USD": "Bitcoin", "ETH-USD": "Ethereum", "^GSPC": "S&P 500"},
    "forex": {"DX-Y.NYB": "Dollar Index", "^GSPC": "S&P 500"},
    "commodity": {"DX-Y.NYB": "Dollar Index", "^GSPC": "S&P 500"},
}

CLASS_LABELS = {
    "equity": "Stock / ETF",
    "index": "Index",
    "crypto": "Crypto",
    "forex": "Forex",
    "commodity": "Commodity",
}
