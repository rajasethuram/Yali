"""
3-tier memory for Yali OS.
  short_term  — RAM only, last 20 exchanges, cleared on restart
  mid_term    — JSON, last 50 entries, auto-prune oldest
  long_term   — JSON, never auto-pruned: watchlist, predictions, preferences
"""

import json
import os
from collections import deque
from datetime import datetime
from pathlib import Path

_MEMORY_FILE = Path(__file__).parent.parent / "memory" / "yali_memory.json"

_short_term: deque = deque(maxlen=20)

_LONG_TERM_DEFAULTS = {
    "watchlist": [],
    "sector_interests": [],
    "predictions": [],
    "preferences": {
        "market_focus": "NSE",
        "brief_length": "short",
        "risk_profile": "moderate",
    },
}


def _load() -> dict:
    if not _MEMORY_FILE.exists():
        return {"mid_term": [], "long_term": _LONG_TERM_DEFAULTS.copy()}
    try:
        with open(_MEMORY_FILE, "r") as f:
            data = json.load(f)
        if "long_term" not in data:
            data["long_term"] = _LONG_TERM_DEFAULTS.copy()
        return data
    except Exception:
        return {"mid_term": [], "long_term": _LONG_TERM_DEFAULTS.copy()}


def _save(data: dict):
    os.makedirs(_MEMORY_FILE.parent, exist_ok=True)
    with open(_MEMORY_FILE, "w") as f:
        json.dump(data, f, indent=2)


def write(query: str, response: str, agent: str = ""):
    """Save interaction to short-term (RAM) and mid-term (JSON)."""
    entry = {
        "ts": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "query": query,
        "response": response[:400],
        "agent": agent,
    }
    _short_term.append(entry)

    data = _load()
    data["mid_term"].append(entry)
    if len(data["mid_term"]) > 50:
        data["mid_term"] = data["mid_term"][-50:]
    _save(data)


def get_context(n_short: int = 5, n_mid: int = 3) -> str:
    """Build memory context string for injection into system prompt."""
    parts = []

    recent = list(_short_term)[-n_short:]
    if recent:
        lines = [f"  [{e['ts']}] Raja: {e['query'][:80]} → Yali: {e['response'][:80]}" for e in recent]
        parts.append("Recent session:\n" + "\n".join(lines))

    data = _load()
    watchlist = data["long_term"].get("watchlist", [])
    if watchlist:
        parts.append(f"Raja's watchlist: {', '.join(watchlist)}")

    sectors = data["long_term"].get("sector_interests", [])
    if sectors:
        parts.append(f"Sector interests: {', '.join(sectors)}")

    preds = data["long_term"].get("predictions", [])[-3:]
    if preds:
        pred_lines = [f"  {p['date']}: {p['question']} → {p['direction']} ({p['confidence']}%)" for p in preds]
        parts.append("Recent predictions:\n" + "\n".join(pred_lines))

    return "\n".join(parts) if parts else ""


def add_to_watchlist(symbol: str):
    symbol = symbol.upper().strip()
    data = _load()
    if symbol not in data["long_term"]["watchlist"]:
        data["long_term"]["watchlist"].append(symbol)
        _save(data)


def add_sector_interest(sector: str):
    sector = sector.strip().title()
    data = _load()
    if sector not in data["long_term"]["sector_interests"]:
        data["long_term"]["sector_interests"].append(sector)
        _save(data)


def save_prediction(question: str, direction: str, confidence: int, source: str = "mirofish"):
    data = _load()
    data["long_term"]["predictions"].append({
        "date": datetime.now().strftime("%Y-%m-%d"),
        "question": question,
        "direction": direction,
        "confidence": confidence,
        "source": source,
        "outcome": "pending",
    })
    _save(data)


def update_prediction_outcome(date: str, outcome: str):
    data = _load()
    for p in data["long_term"]["predictions"]:
        if p["date"] == date and p["outcome"] == "pending":
            p["outcome"] = outcome
    _save(data)


def auto_tag(query: str, response: str):
    """
    Lightweight symbol/sector detection from query text.
    No LLM call — pure keyword matching to avoid token waste.
    """
    nse_keywords = {
        "INFY": ["infy", "infosys"],
        "TCS": ["tcs", "tata consultancy"],
        "HDFC": ["hdfc"],
        "RELIANCE": ["reliance", "ril"],
        "WIPRO": ["wipro"],
        "ICICIBANK": ["icici"],
        "SBIN": ["sbi", "state bank"],
        "HCLTECH": ["hcltech", "hcl tech"],
        "AXISBANK": ["axis bank", "axisbank"],
        "BAJFINANCE": ["bajaj finance", "bajfinance"],
    }
    sector_keywords = {
        "IT": ["it sector", "software", "tech", "technology"],
        "Banking": ["bank", "banking", "nifty bank"],
        "Pharma": ["pharma", "drug", "medicine"],
        "Auto": ["auto", "automobile", "car", "ev"],
        "FMCG": ["fmcg", "consumer goods", "fmcg"],
    }

    text = (query + " " + response).lower()

    symbol_counts: dict = {}
    data = _load()
    for sym, keywords in nse_keywords.items():
        if any(k in text for k in keywords):
            symbol_counts[sym] = symbol_counts.get(sym, 0) + 1

    for sym, count in symbol_counts.items():
        existing = data["long_term"]["watchlist"]
        mentions = sum(1 for e in data.get("mid_term", []) if sym.lower() in e.get("query", "").lower())
        if mentions >= 2 and sym not in existing:
            add_to_watchlist(sym)

    for sector, keywords in sector_keywords.items():
        if any(k in text for k in keywords):
            add_sector_interest(sector)


def recall_all() -> dict:
    """Returns full long-term memory dict — for 'Yali what do you know about me'."""
    return _load()["long_term"]
