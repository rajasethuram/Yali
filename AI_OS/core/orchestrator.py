import asyncio
import logging
from swarm.planner_agent import PlannerAgent
from swarm.executor_agent import ExecutorAgent
from swarm.validator_agent import ValidatorAgent
from swarm.self_healing_agent import SelfHealingAgent
from core import memory
from core.text_to_speech import speak
from ui.server import broadcast_status

logger = logging.getLogger('yali')

_FINANCE_KEYWORDS = [
    'market', 'stock', 'nifty', 'sensex', 'share', 'invest', 'price',
    'trading', 'bse', 'nse', 'predict', 'analyse', 'analyze', 'finance',
    'rupee', 'index', 'mutual fund', 'etf', 'portfolio', 'dividend',
    'earnings', 'results', 'fii', 'dii', 'crude', 'gdp', 'rbi', 'inflation',
    'forecast', 'tomorrow', 'simulate',
]


def _is_finance(task: str) -> bool:
    t = task.lower()
    return any(k in t for k in _FINANCE_KEYWORDS)


class Orchestrator:
    def __init__(self):
        self.planner = PlannerAgent()
        self.executor = ExecutorAgent()
        self.validator = ValidatorAgent()
        self.self_healer = SelfHealingAgent()
        self._finance_agent = None

    def _get_finance_agent(self):
        if self._finance_agent is None:
            from core.agents.finance_agent import FinanceAgent
            self._finance_agent = FinanceAgent()
        return self._finance_agent

    async def handle_task(self, task: str):
        logger.info(f"Orchestrator: task received: {task}")
        await broadcast_status({"pipeline": "planning", "task": task})

        if _is_finance(task):
            logger.info("Routing to finance agent")
            await broadcast_status({"pipeline": "finance", "task": task})
            agent = self._get_finance_agent()
            result = await agent.handle(task)
            memory.write(task, result, agent="finance")
            memory.auto_tag(task, result)
            speak(result[:300])
            await broadcast_status({"pipeline": "completed", "task": task, "results": [{"step": task, "ok": True}]})
            return result

        steps = await self.planner.plan(task)
        await broadcast_status({"pipeline": "planned", "task": task, "steps": len(steps)})

        results = []
        for step in steps:
            await broadcast_status({"pipeline": "executing", "step": step})
            try:
                res = await self.self_healer.attempt(self.executor.execute_step, step)
            except Exception as e:
                res = f"Execution failed: {e}"
            ok, msg = await self.validator.validate(res, step)
            await broadcast_status({"pipeline": "validated", "step": step, "ok": ok, "msg": msg})
            results.append({"step": step, "result": res, "ok": ok, "msg": msg})
            if not ok:
                logger.warning(f"Validation failed: {step} → {res}")

        final = '\n'.join([f"{r['step']} => {r['result']}" for r in results])
        memory.write(task, final)
        memory.auto_tag(task, final)
        await broadcast_status({"pipeline": "completed", "task": task, "results": [{"step": r['step'], "ok": r['ok']} for r in results]})
        speak("Task completed")
        return results
