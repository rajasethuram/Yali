"""
Claude web search client for YALI Finance.
- Runs terminal commands (yfinance, system queries) → captures output
- Feeds terminal output as grounded context to Claude
- Claude uses web_search tool for live news + macro data
- Falls back to Gemini → Groq if ANTHROPIC_API_KEY not set
"""

import subprocess
import logging
from config.settings import ANTHROPIC_API_KEY

logger = logging.getLogger("yali")

_CLAUDE_MODEL = "claude-opus-4-5"
_WEB_SEARCH_TOOL = {"type": "web_search_20250305", "name": "web_search"}


def run_terminal(cmd: str, timeout: int = 20) -> str:
    """Run a shell command, return stdout. Used for arbitrary system queries."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        out = result.stdout.strip()
        err = result.stderr.strip()
        return out if out else (err if err else "(no output)")
    except subprocess.TimeoutExpired:
        return "(command timed out)"
    except Exception as e:
        return f"(error: {e})"


def get_finance_terminal_data(symbols: list = None) -> str:
    """
    Fetch live NSE/BSE prices via yfinance and format as terminal-style output.
    This is injected as grounded context for Claude's web search call.
    Symbols: list of Yahoo Finance tickers (e.g. ['^NSEI', 'INFY.NS'])
    """
    if not symbols:
        symbols = ["^NSEI", "^BSESN", "^NSEBANK"]

    try:
        import yfinance as yf
        lines = [f"$ yfinance price-check {' '.join(symbols)}"]
        for sym in symbols:
            try:
                t = yf.Ticker(sym)
                h = t.history(period="2d")
                if h.empty:
                    lines.append(f"{sym}: no data")
                    continue
                r = h.iloc[-1]
                p = h.iloc[-2] if len(h) > 1 else r
                chg = ((r["Close"] - p["Close"]) / p["Close"]) * 100
                lines.append(
                    f"{sym}: close={r['Close']:.2f}  change={chg:+.2f}%  vol={int(r['Volume']):,}"
                )
            except Exception as e:
                lines.append(f"{sym}: error — {e}")
        return "\n".join(lines)
    except ImportError:
        return "(yfinance not installed)"
    except Exception as e:
        return f"(price fetch failed: {e})"


def ask_with_websearch(
    user_prompt: str,
    system_prompt: str = "",
    terminal_data: str = "",
    max_tokens: int = 700,
) -> str:
    """
    Claude + web_search_20250305 tool + terminal data context.
    Returns '' on failure so caller can fall back to Gemini/Groq.
    """
    if not ANTHROPIC_API_KEY:
        return ""

    try:
        import anthropic

        full_prompt = user_prompt
        if terminal_data:
            full_prompt = (
                f"Live terminal data (yfinance / system):\n"
                f"```\n{terminal_data}\n```\n\n"
                f"{user_prompt}"
            )

        kwargs = {
            "model": _CLAUDE_MODEL,
            "max_tokens": max_tokens,
            "tools": [_WEB_SEARCH_TOOL],
            "messages": [{"role": "user", "content": full_prompt}],
        }
        if system_prompt:
            kwargs["system"] = system_prompt

        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(**kwargs)

        # Collect all text blocks (tool_result blocks are skipped)
        parts = [b.text for b in response.content if hasattr(b, "text") and b.text]
        return "\n".join(parts).strip()

    except Exception as e:
        logger.warning(f"Claude web search failed: {e}")
        return ""


def is_available() -> bool:
    return bool(ANTHROPIC_API_KEY)
