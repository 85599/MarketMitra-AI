"""Asset-class detection covers every supported instrument type."""
import pytest

from app.assets import BENCH_BY_CLASS, CLASS_LABELS, asset_class


@pytest.mark.parametrize("symbol,expected", [
    ("RELIANCE.NS", "equity"),
    ("AAPL", "equity"),
    ("^NSEI", "index"),
    ("^GSPC", "index"),
    ("BTC-USD", "crypto"),
    ("ETH-USD", "crypto"),
    ("EURUSD=X", "forex"),
    ("GC=F", "commodity"),
])
def test_asset_class(symbol, expected):
    assert asset_class(symbol) == expected


def test_asset_class_is_case_insensitive():
    assert asset_class("btc-usd") == "crypto"
    assert asset_class("reliance.ns") == "equity"


def test_every_class_has_label_and_benchmarks():
    for cls in ("equity", "index", "crypto", "forex", "commodity"):
        assert cls in CLASS_LABELS
        assert cls in BENCH_BY_CLASS
        assert BENCH_BY_CLASS[cls], f"{cls} has no benchmarks"
