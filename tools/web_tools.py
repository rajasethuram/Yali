import requests

def search_web(query):
    """
    Search the web for information.
    Handles stock queries specially, falls back to DuckDuckGo for general queries.
    """
    try:
        # Check if this is a stock-related query
        if any(x in query.lower() for x in ['stock', 'price', 'interday', 'return', 'ticker', 'nasdaq', 'nyse']):
            return search_stock(query)
        
        # For general queries, use DuckDuckGo instant answer API
        resp = requests.get('https://api.duckduckgo.com', params={'q': query, 'format': 'json'}, timeout=10)
        data = resp.json()
        abstract = data.get('AbstractText') or data.get('Heading') or ''
        return abstract or f"No instant answer for '{query}'. Try a more specific search."
    except Exception as e:
        return f"Search error: {e}"

def search_stock(query):
    """
    Search for stock information.
    Note: Real-time stock data requires a paid API like Alpha Vantage or Finnhub.
    This is a placeholder that suggests using a proper API.
    """
    try:
        # For now, provide a helpful response
        # In production, integrate with Alpha Vantage, Finnhub, or similar
        lower_q = query.lower()
        
        if 'last friday' in lower_q or 'friday' in lower_q:
            return "To get stock data for last Friday, I need access to a real-time stock API. " \
                   "Please provide your Alpha Vantage or Finnhub API key in config/settings.py. " \
                   "Then I can fetch historical stock prices and calculate intraday returns."
        
        if 'highest return' in lower_q or 'best return' in lower_q:
            return "To find stocks with highest intraday returns, I need real-time market data. " \
                   "Please configure a stock API (Alpha Vantage, Finnhub, or similar) in settings.py"
        
        # Generic stock query response
        return f"Stock query received: '{query}'. To enable stock data lookups, " \
               "please configure a stock market API in config/settings.py with your API key."
    except Exception as e:
        return f"Stock search error: {e}"
