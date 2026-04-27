"""
Yali Finance Agent — 4 modes:
  1. Market Briefing  — "market update", "what's happening"
  2. Stock Analysis   — "analyze INFY", "how is TCS"
  3. Market Q&A       — general finance questions
  4. Yali Predict     — "predict", "forecast", "simulate" → MiroFish / Gemini

LLM routing:
  Primary  → Gemini 2.0 Flash + Google Search grounding (live news, macro context)
  Fallback → Groq llama-3.3-70b (if GEMINI_API_KEY not set)
  Prices   → yfinance (always, for exact NSE/BSE numbers)
"""

import logging
import requests
from core import memory
from tools.finance_tool import get_price, get_market_overview, get_news, build_mirofish_seed
from brain.prompt_engine import FINANCE_SYSTEM
from config.settings import MIROFISH_PORT

logger = logging.getLogger("yali")

_BRIEFING_KEYWORDS = ["market update", "what's happening", "market brief",
                       "morning update", "market open", "how is market",
                       "market today", "daily brief"]
_ANALYSIS_KEYWORDS = ["analyze", "analyse", "tell me about", "how is", "how are",
                       "stock analysis", "check stock", "what about"]
_PREDICT_KEYWORDS  = ["predict", "forecast", "simulate", "what will", "tomorrow",
                       "next week", "will nifty", "will sensex", "direction"]


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
    known = ["INFY", "TCS", "HDFC", "RELIANCE", "WIPRO", "ICICIBANK", "SBIN",
             "HCLTECH", "AXISBANK", "BAJFINANCE", "NIFTY", "SENSEX", "BANKNIFTY",
             "TATAMOTORS", "MARUTI", "SUNPHARMA", "DRREDDY", "ONGC", "NTPC",
             "ADANIENT", "ADANIPORTS", "HINDUNILVR", "ASIANPAINT", "TITAN"]
    q = query.upper()
    for sym in known:
        if sym in q:
            return sym
    import re
    m = re.search(r"(?:analyze|analyse|about|how is|how are|check)\s+([A-Z]{2,12})", query, re.I)
    return m.group(1).upper() if m else ""


def _llm_ask(
    user_prompt: str,
    use_search: bool = True,
    max_tokens: int = 400,
    terminal_data: str = "",
) -> str:
    """
    LLM routing for finance queries:
      1. Claude claude-opus-4-5 + web_search tool + terminal data (if ANTHROPIC_API_KEY)
      2. Gemini 2.5 Flash + Google Search grounding (if GEMINI_API_KEY)
      3. Groq llama-3.3-70b (always available, no search)
    """
    # 1 — Claude with web search + terminal context
    if use_search:
        try:
            from core.claude_web_client import ask_with_websearch, is_available as claude_ok
            if claude_ok():
                result = ask_with_websearch(
                    user_prompt,
                    system_prompt=FINANCE_SYSTEM,
                    terminal_data=terminal_data,
                    max_tokens=max_tokens,
                )
                if result:
                    return result
        except Exception as e:
            logger.warning(f"Claude web search failed, trying Gemini: {e}")

    # 2 — Gemini with Google Search grounding
    try:
        from core.gemini_client import ask_with_search, ask as gemini_ask, is_available as gem_ok
        if gem_ok():
            fn = ask_with_search if use_search else gemini_ask
            ctx = f"{terminal_data}\n\n" if terminal_data else ""
            result = fn(ctx + user_prompt, system_prompt=FINANCE_SYSTEM, max_tokens=max_tokens)
            if result:
                return result
    except Exception as e:
        logger.warning(f"Gemini failed, falling back to Groq: {e}")

    # 3 — Groq (no live search, but has yfinance data in prompt)
    from core.llm_client import ask as groq_ask
    mem_ctx = memory.get_context()
    full = f"{terminal_data}\n\n{user_prompt}" if terminal_data else user_prompt
    return groq_ask(user_prompt=full, system_prompt=FINANCE_SYSTEM,
                    memory_context=mem_ctx, max_tokens=max_tokens) or ""


class FinanceAgent:
    async def handle(self, query: str) -> str:
        mode = _detect_mode(query)
        logger.info(f"FinanceAgent mode={mode} | query={query[:60]}")

        if mode == "briefing":
            return await self._briefing()
        elif mode == "analysis":
            return await self._analysis(_extract_symbol(query), query)
        elif mode == "predict":
            return await self._predict(query)
        else:
            return await self._qa(query)

    async def _briefing(self) -> str:
        from core.claude_web_client import get_finance_terminal_data
        # Pull live prices via terminal (yfinance subprocess)
        terminal_data = get_finance_terminal_data()

        # Also get yfinance dict for fallback display
        overview = get_market_overview()
        nifty, sensex, bnk = overview["nifty"], overview["sensex"], overview["banknifty"]
        fallback = (
            f"Nifty: {nifty.get('price','N/A')} ({nifty.get('change_pct','N/A')}%)\n"
            f"Sensex: {sensex.get('price','N/A')} ({sensex.get('change_pct','N/A')}%)\n"
            f"Bank Nifty: {bnk.get('price','N/A')} ({bnk.get('change_pct','N/A')}%)"
        )

        prompt = (
            f"Raja needs a concise 60-second Indian market briefing for today.\n\n"
            f"Search for today's top NSE/Nifty news, FII/DII activity, global cues, "
            f"and key sector movers. Give: market tone, top 2 movers, macro risk, "
            f"one actionable insight."
        )
        resp = _llm_ask(prompt, use_search=True, max_tokens=400, terminal_data=terminal_data)
        return resp or fallback

    async def _analysis(self, symbol: str, query: str) -> str:
        if not symbol:
            return "Specify stock symbol. Example: analyze INFY"

        data = get_price(symbol)
        if "error" in data:
            return f"Could not fetch data for {symbol}: {data['error']}"

        from core.claude_web_client import get_finance_terminal_data
        # Get terminal data for this specific symbol
        nse_sym = f"{symbol}.NS" if symbol not in ("NIFTY","SENSEX","BANKNIFTY") else (
            {"NIFTY": "^NSEI", "SENSEX": "^BSESN", "BANKNIFTY": "^NSEBANK"}[symbol]
        )
        terminal_data = get_finance_terminal_data(symbols=[nse_sym])

        price_ctx = (
            f"{symbol}: ₹{data['price']} | Change: {data['change_pct']}%\n"
            f"52W High: {data['high_52w']} | 52W Low: {data['low_52w']}\n"
            f"Volume: {data['volume']:,}"
        )

        prompt = (
            f"Analyze NSE:{symbol} for Raja.\n\n"
            f"Search for latest news, analyst ratings, recent events for {symbol}.\n"
            f"Format:\n"
            f"Trend: [bullish/bearish/sideways + reason]\n"
            f"Key levels: [support / resistance]\n"
            f"Recent catalyst: [latest news]\n"
            f"Risk: [key downside risk]\n"
            f"Verdict: [1-line opinion]"
        )
        resp = _llm_ask(prompt, use_search=True, max_tokens=450,
                        terminal_data=f"{terminal_data}\n{price_ctx}")
        return resp or price_ctx

    async def _qa(self, query: str) -> str:
        symbol = _extract_symbol(query)
        terminal_data = ""
        if symbol:
            from core.claude_web_client import get_finance_terminal_data
            nse_sym = f"{symbol}.NS" if symbol not in ("NIFTY","SENSEX","BANKNIFTY") else (
                {"NIFTY": "^NSEI", "SENSEX": "^BSESN", "BANKNIFTY": "^NSEBANK"}[symbol]
            )
            terminal_data = get_finance_terminal_data(symbols=[nse_sym])

        prompt = f"{query}\n\nAnswer for Raja concisely. Search for latest data."
        resp = _llm_ask(prompt, use_search=True, max_tokens=450, terminal_data=terminal_data)
        return resp or "Finance data unavailable."

    async def _predict(self, query: str) -> str:
        from core.claude_web_client import get_finance_terminal_data
        mem_data = memory.recall_all()
        watchlist = mem_data.get("watchlist", [])
        sectors   = mem_data.get("sector_interests", [])

        # Get live terminal data for Nifty + watchlist
        syms = ["^NSEI", "^BSESN"]
        for w in watchlist[:3]:
            syms.append(f"{w}.NS")
        terminal_data = get_finance_terminal_data(symbols=syms)

        seed = build_mirofish_seed(query, watchlist=watchlist, sector_focus=sectors)

        # Try MiroFish first
        mirofish_result = _call_mirofish(seed)
        if mirofish_result:
            prompt = (
                f"MiroFish swarm simulation:\n{mirofish_result}\n\n"
                f"Summarize for Raja: direction, confidence %, key risk."
            )
            resp = _llm_ask(prompt, use_search=False, max_tokens=300, terminal_data=terminal_data)
            result = resp or mirofish_result
            _save_prediction_from_text(query, result)
            return result

        prompt = (
            f"Raja asks: {query}\n\n"
            f"Search for today's Nifty/Sensex technical outlook, FII/DII data, "
            f"global cues (Dow futures, SGX Nifty, crude oil). Predict:\n"
            f"Direction: [bullish/bearish/sideways]\n"
            f"Confidence: [X%]\n"
            f"Key risk: [main risk]\n"
            f"Reasoning: [2-3 lines]"
        )
        resp = _llm_ask(prompt, use_search=True, max_tokens=500, terminal_data=terminal_data)
        result = resp or "Prediction unavailable."
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
    if "bullish" in r or "upward" in r or "rise" in r or "up " in r:
        direction = "bullish"
    elif "bearish" in r or "downward" in r or "fall" in r or "down " in r:
        direction = "bearish"
    else:
        direction = "sideways"

    import re
    m = re.search(r"(\d{1,3})\s*%", result)
    confidence = int(m.group(1)) if m else 60
    confidence = min(max(confidence, 10), 99)

    memory.save_prediction(question, direction, confidence, source="gemini")
