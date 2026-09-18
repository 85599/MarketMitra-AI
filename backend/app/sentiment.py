"""Lightweight lexicon-based sentiment scoring for financial headlines."""

POSITIVE = {
    "surge", "surges", "soar", "soars", "rally", "rallies", "gain", "gains", "jump",
    "jumps", "rise", "rises", "climb", "climbs", "beat", "beats", "strong", "record",
    "high", "upgrade", "upgraded", "bullish", "buy", "outperform", "growth", "profit",
    "boom", "recover", "recovers", "rebound", "rebounds", "expand", "expands", "wins",
    "win", "positive", "optimistic", "boost", "boosts", "momentum", "breakout",
}
NEGATIVE = {
    "fall", "falls", "drop", "drops", "plunge", "plunges", "slump", "slumps", "decline",
    "declines", "miss", "misses", "weak", "loss", "losses", "downgrade", "downgraded",
    "bearish", "sell", "selloff", "crash", "crashes", "fear", "risk", "cut", "cuts",
    "probe", "fraud", "default", "bankrupt", "lawsuit", "sued", "warning", "negative",
    "pessimistic", "tumble", "tumbles", "sink", "sinks", "slip", "slips", "debt",
    "layoffs", "recall", "investigation", "penalty", "fine", "fined",
}
INTENSIFIERS = {"sharply", "strongly", "big", "huge", "massive", "deep", "rapid", "rapidly"}
NEGATORS = {"not", "no", "never", "without", "barely"}


def score_text(text: str) -> float:
    words = [w.strip(".,!?()\"'").lower() for w in text.split()]
    score = 0.0
    for i, w in enumerate(words):
        val = 0.0
        if w in POSITIVE:
            val = 1.0
        elif w in NEGATIVE:
            val = -1.0
        if val == 0.0:
            continue
        if i > 0 and words[i - 1] in NEGATORS:
            val = -val
        if i > 0 and words[i - 1] in INTENSIFIERS:
            val *= 1.5
        score += val
    if not words:
        return 0.0
    return max(-1.0, min(1.0, score / 3.0))


def label(score: float) -> str:
    if score > 0.15:
        return "positive"
    if score < -0.15:
        return "negative"
    return "neutral"


def analyze_news(items: list[dict]) -> dict:
    scored = []
    for it in items:
        s = score_text(it.get("title", ""))
        scored.append({**it, "sentimentScore": round(s, 3), "sentiment": label(s)})
    if scored:
        avg = sum(x["sentimentScore"] for x in scored) / len(scored)
    else:
        avg = 0.0
    counts = {"positive": 0, "neutral": 0, "negative": 0}
    for x in scored:
        counts[x["sentiment"]] += 1
    return {
        "overallScore": round(avg, 3),
        "overallLabel": label(avg),
        "counts": counts,
        "articles": scored,
    }
