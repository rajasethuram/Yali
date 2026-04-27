"""
Yali Finance Agent — 4 modes:
  1. Market Briefing  — "market update", "what's happening"
  2. Stock Analysis   — "analyze INFY", "how is TCS"
  3. Market Q&A       — general finance questions
  4. Yali Predict     — "predict", "forecast", "simulate" → MiroFish
"""

import logging
import requests
from core.llm_client import ask
from core import memory
from tools.finance_tool import get_price, get_market_overview, get_news, build_mirofish_seed
from brain.prompt_engine import FINANCE_SYSTEM
from config.settings import MIROFISH_PORT

logger = logging.getLogger('yali')

_BRIEFING_KEYWORDS = ['market update', "what's happening", 'market brief', 'morning update', 'market open']
_ANALYSIS_KEYWORDS = ['analyze', 'analyse', 'tell me about', 'how is', 'how are', 'stock analysis']
_PREDICT_KEYWORDS = ['predict', 'forecast', 'simulate', 'what will', 'tomorrow', 'next week', 'will nifty', 'will sensex']


def _detect_mode(query: str) -> str:
    q = query.lower()
    if any(k in q for k in _PREDICT_KEYWORDS):
        return "predict"
    if any(k in q for k in _BRIEFING_KEYWORDS):
        return "briefing"
    if any(k in q for k in _ANALYSIS_KEYWORDS):
        return "analysis"
    return "qa"


def _extract_symbol(query: str) -> str:
    """Pull stock symbol from query — simple heuristic."""
    known = ["INFY", "TCS", "HDFC", "RELIANCE", "WIPRO", "ICICIBANK", "SBIN",
             "HCLTECH", "AXISBANK", "BAJFINANCE", "NIFTY", "SENSEX", "BANKNIFTY",
             "TATAMOTORS", "MARUTI", "SUNPHARMA", "DRREDDY", "ONGC", "NTPC"]
    q = query.upper()
    for sym in known:
        if sym in q:
            return sym
    # fallback: grab word after keyword
    import re
    m = re.search(r'(?:analyze|analyse|about|how is|how are)\s+([A-Z]{2,10})', query, re.I)
    return m.group(1).upper() if m else ""


class FinanceAgent:
    async def handle(self, query: str) -> str:
        mode = _detect_mode(query)
        logger.info(f"Finance mode: {mode} | query: {query}")

        if mode == "briefing":
            return await self._briefing()
        elif mode == "analysis":
            symbol = _extract_symbol(query)
            return await self._analysis(symbol, query)
        elif mode == "predict":
            return await self._predict(query)
        else:
            return await self._qa(query)

    async def _briefing(self) -> str:
        overview = get_market_overview()
        news = get_news(n=3)

        nifty = overview["nifty"]
        sensex = overview["sensex"]
        bnk = overview["banknifty"]

        market_data = (
            f"Nifty: {nifty.get('price','N/A')} ({nifty.get('change_pct','N/A')}%)\n"
            f"Sensex: {sensex.get('price','N/A')} ({sensex.get('change_pct','N/A')}%)\n"
            f"Bank Nifty: {bnk.get('price','N/A')} ({bnk.get('change_pct','N/A')}%)\n"
            f"Top headlines:\n" + "\n".join(f"- {n['title']}" for n in news)
        )

        ctx = memory.get_context()
        resp = ask(
            user_prompt=f"Give Raja a concise 60-second market briefing based on this data:\n{market_data}",
            system_prompt=FINANCE_SYSTEM,
            memory_context=ctx,
            max_tokens=300,
        )
        return resp or market_data

    async def _analysis(self, symbol: str, query: str) -> str:
        if not symbol:
            return "Specify stock symbol. Example: analyze INFY"

        data = get_price(symbol)
        if "error" in data:
            return f"Could not fetch data for {symbol}: {data['error']}"

        news = get_news(query=f"{symbol} NSE stock", n=3)
        price_block = (
            f"{symbol}: ₹{data['price']} | Change: {data['change_pct']}%\n"
            f"52W High: {data['high_52w']} | 52W Low: {data['low_52w']}\n"
            f"Volume: {data['volume']:,}\n"
            f"Recent news:\n" + "\n".join(f"- {n['title']}" for n in news)
        )

        ctx = memory.get_context()
        resp = ask(
            user_prompt=f"Analyze {symbol} for Raja. Format: Trend | Key levels | Recent catalyst | Risk\nData:\n{price_block}",
            system_prompt=FINANCE_SYSTEM,
            memory_context=ctx,
            max_tokens=350,
        )
        return resp or price_block

    async def _qa(self, query: str) -> str:
        ctx = memory.get_context()
        # check if live price needed
        symbol = _extract_symbol(query)
        price_block = ""
        if symbol:
            data = get_price(symbol)
            if "error" not in data:
                price_block = f"\nLive data for {symbol}: ₹{data['price']} ({data['change_pct']}%)"

        resp = ask(
            user_prompt=query + price_block,
            system_prompt=FINANCE_SYSTEM,
            memory_context=ctx,
            max_tokens=400,
        )
        return resp or "Finance data unavailable."

    async def _predict(self, query: str) -> str:
        mem_data = memory.recall_all()
        watchlist = mem_data.get("watchlist", [])
        sectors = mem_data.get("sector_interests", [])

        seed = build_mirofish_seed(query, watchlist=watchlist, sector_focus=sectors)

        # Try MiroFish if running
        mirofish_result = _call_mirofish(seed)
        if mirofish_result:
            ctx = memory.get_context()
            resp = ask(
                user_prompt=f"MiroFish simulation result:\n{mirofish_result}\n\nSummarize prediction for Raja concisely.",
                system_prompt=FINANCE_SYSTEM,
                memory_context=ctx,
                max_tokens=350,
            )
            result = resp or mirofish_result
            _save_prediction_from_text(query, result)
            return result

        # MiroFish not running — LLM-only prediction with seed data
        ctx = memory.get_context()
        resp = ask(
            user_prompt=f"Based on this market data, give Raja a directional prediction with confidence % and key risks:\n{seed}",
            system_prompt=FINANCE_SYSTEM,
            memory_context=ctx,
            max_tokens=400,
        )
        result = resp or "Prediction unavailable — MiroFish offline and LLM call failed."
        _save_prediction_from_text(query, result)
        return result


def _call_mirofish(seed: str) -> str:
    try:
        r = requests.post(
            f"http://localhost:{MIROFISH_PORT}/api/simulate",
            json={"seed": seed},
            timeout=60,
        )
        if r.status_code == 200:
            return r.json().get("result", "")
    except Exception:
        pass
    return ""


def _save_prediction_from_text(question: str, result: str):
    r = result.lower()
    if "bullish" in r or "upward" in r or "rise" in r:
        direction = "bullish"
    elif "bearish" in r or "downward" in r or "fall" in r:
        direction = "bearish"
    else:
        direction = "sideways"

    import re
    m = re.search(r'(\d{1,3})\s*%', result)
    confidence = int(m.group(1)) if m else 60

    memory.save_prediction(question, direction, confidence)
