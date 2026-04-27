"""
Finance data tools — all free, no API key needed for price data.
yfinance → NSE/BSE prices
NewsAPI  → market headlines (key optional, falls back to RSS)
"""

import requests
from datetime import datetime
from config.settings import NEWS_API_KEY

try:
    import yfinance as yf
    _YF_OK = True
except ImportError:
    _YF_OK = False


# NSE symbol → Yahoo Finance ticker map
_NSE_MAP = {
    "NIFTY": "^NSEI",
    "SENSEX": "^BSESN",
    "BANKNIFTY": "^NSEBANK",
}


def _nse_ticker(symbol: str) -> str:
    s = symbol.upper()
    if s in _NSE_MAP:
        return _NSE_MAP[s]
    return f"{s}.NS"


def get_price(symbol: str) -> dict:
    """Returns latest price info for NSE symbol."""
    if not _YF_OK:
        return {"error": "yfinance not installed"}
    try:
        ticker = _nse_ticker(symbol)
        t = yf.Ticker(ticker)
        hist = t.history(period="2d")
        if hist.empty:
            return {"error": f"No data for {symbol}"}
        latest = hist.iloc[-1]
        prev = hist.iloc[-2] if len(hist) > 1 else latest
        change = latest["Close"] - prev["Close"]
        pct = (change / prev["Close"]) * 100
        info = t.info
        return {
            "symbol": symbol.upper(),
            "price": round(latest["Close"], 2),
            "change": round(change, 2),
            "change_pct": round(pct, 2),
            "high_52w": info.get("fiftyTwoWeekHigh", "N/A"),
            "low_52w": info.get("fiftyTwoWeekLow", "N/A"),
            "volume": int(latest["Volume"]),
            "as_of": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
    except Exception as e:
        return {"error": str(e)}


def get_market_overview() -> dict:
    """Nifty + Sensex + Bank Nifty snapshot."""
    return {
        "nifty": get_price("NIFTY"),
        "sensex": get_price("SENSEX"),
        "banknifty": get_price("BANKNIFTY"),
        "as_of": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


def get_news(query: str = "Indian stock market NSE Nifty", n: int = 5) -> list:
    """
    Fetch market news headlines.
    Uses NewsAPI if key available, else falls back to Google News RSS.
    """
    if NEWS_API_KEY:
        try:
            url = "https://newsapi.org/v2/everything"
            params = {
                "q": query,
                "language": "en",
                "sortBy": "publishedAt",
                "pageSize": n,
                "apiKey": NEWS_API_KEY,
            }
            r = requests.get(url, params=params, timeout=8)
            data = r.json()
            articles = data.get("articles", [])
            return [
                {"title": a["title"], "source": a["source"]["name"], "published": a["publishedAt"][:10]}
                for a in articles[:n]
            ]
        except Exception:
            pass

    # RSS fallback — no key needed
    try:
        rss = f"https://news.google.com/rss/search?q={query.replace(' ', '+')}&hl=en-IN&gl=IN&ceid=IN:en"
        r = requests.get(rss, timeout=8)
        import re
        titles = re.findall(r'<item>.*?<title>(.*?)</title>', r.text, re.DOTALL)
        return [{"title": t, "source": "Google News", "published": datetime.now().strftime("%Y-%m-%d")} for t in titles[:n]]
    except Exception:
        return [{"title": "News unavailable", "source": "N/A", "published": ""}]


def build_mirofish_seed(
    question: str,
    watchlist: list = None,
    sector_focus: list = None,
) -> str:
    """Build structured seed for MiroFish simulation."""
    overview = get_market_overview()
    nifty = overview["nifty"]
    sensex = overview["sensex"]
    news = get_news(n=3)

    nifty_level = nifty.get("price", "N/A")
    sensex_level = sensex.get("price", "N/A")
    news_lines = "\n".join([f"{i+1}. {n['title']}" for i, n in enumerate(news)])
    watchlist_str = ", ".join(watchlist) if watchlist else "None set"
    sector_str = ", ".join(sector_focus) if sector_focus else "General"

    return f"""Date: {datetime.now().strftime('%Y-%m-%d')}
Market: Nifty {nifty_level} | Sensex: {sensex_level}

Top news today:
{news_lines}

Raja's watchlist: {watchlist_str}
Sector focus: {sector_str}

Prediction question:
{question}

Simulate market participant behavior and return:
direction, confidence %, key risks, agent consensus summary."""
