import asyncio
import logging

logger = logging.getLogger('yali')

class SelfHealingAgent:
    def __init__(self, max_retries=3):
        self.max_retries = max_retries

    async def attempt(self, coro, *args, **kwargs):
        last_exc = None
        for attempt in range(1, self.max_retries+1):
            try:
                return await coro(*args, **kwargs)
            except Exception as e:
                last_exc = e
                logger.warning(f"Attempt {attempt} failed: {e}")
                await asyncio.sleep(attempt)
        raise last_exc
