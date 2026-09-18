"""SQLite-backed store for AI predictions and their outcomes."""
import os
import sqlite3
import threading
from pathlib import Path

_DEFAULT_DB = Path(__file__).resolve().parent.parent / "predictions.db"
DB_PATH = Path(os.environ.get("MM_DB_PATH", _DEFAULT_DB))
_LOCK = threading.Lock()


def _conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _LOCK, _conn() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                created_at TEXT NOT NULL,
                target_date TEXT NOT NULL,
                last_close REAL NOT NULL,
                predicted_price REAL NOT NULL,
                predicted_return REAL NOT NULL,
                low80 REAL, high80 REAL,
                actual_price REAL,
                UNIQUE(symbol, created_at)
            )
        """)


def save_prediction(symbol, created_at, target_date, last_close, predicted_price,
                    predicted_return, low80, high80):
    with _LOCK, _conn() as c:
        c.execute("""
            INSERT OR IGNORE INTO predictions
            (symbol, created_at, target_date, last_close, predicted_price,
             predicted_return, low80, high80)
            VALUES (?,?,?,?,?,?,?,?)
        """, (symbol, created_at, target_date, last_close, predicted_price,
              predicted_return, low80, high80))


def resolve_pending(symbol: str, closes: dict[str, float]):
    """Fill actual_price for past predictions using a date->close map."""
    with _LOCK, _conn() as c:
        rows = c.execute(
            "SELECT id, target_date FROM predictions WHERE symbol=? AND actual_price IS NULL",
            (symbol,),
        ).fetchall()
        for r in rows:
            actual = closes.get(r["target_date"])
            if actual is not None:
                c.execute("UPDATE predictions SET actual_price=? WHERE id=?",
                          (actual, r["id"]))


def list_predictions(symbol: str, limit: int = 50):
    with _LOCK, _conn() as c:
        rows = c.execute(
            "SELECT * FROM predictions WHERE symbol=? ORDER BY created_at DESC LIMIT ?",
            (symbol, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def performance(symbol: str) -> dict:
    with _LOCK, _conn() as c:
        rows = c.execute(
            "SELECT * FROM predictions WHERE symbol=? AND actual_price IS NOT NULL",
            (symbol,),
        ).fetchall()
    total = len(rows)
    if total == 0:
        return {"resolved": 0, "directionAccuracy": None, "mape": None,
                "within80Band": None, "avgError": None}
    dir_hits = 0
    apes = []
    in_band = 0
    for r in rows:
        pred_dir = r["predicted_price"] >= r["last_close"]
        act_dir = r["actual_price"] >= r["last_close"]
        if pred_dir == act_dir:
            dir_hits += 1
        if r["actual_price"] > 0:
            apes.append(abs(r["predicted_price"] - r["actual_price"]) / r["actual_price"])
        if r["low80"] is not None and r["low80"] <= r["actual_price"] <= r["high80"]:
            in_band += 1
    return {
        "resolved": total,
        "directionAccuracy": round(dir_hits / total, 3),
        "mape": round(sum(apes) / len(apes) * 100, 3) if apes else None,
        "within80Band": round(in_band / total, 3),
        "avgError": round(sum(abs(r["predicted_price"] - r["actual_price"]) for r in rows) / total, 3),
    }
