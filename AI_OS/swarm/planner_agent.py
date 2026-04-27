import logging
from core.llm_client import ask
from core import memory
from brain.prompt_engine import PLANNER_SYSTEM, plan_prompt
from swarm.fallback_planner import FallbackPlanner

logger = logging.getLogger('yali')

_SIMPLE_KEYWORDS = [
    'open ', 'create ', 'write ', 'search ', 'what can you do',
    'help', 'who are you',
]


class PlannerAgent:
    async def plan(self, task: str) -> list:
        task_l = task.lower().strip()
        if any(k in task_l for k in _SIMPLE_KEYWORDS):
            steps = FallbackPlanner.plan(task)
            logger.info(f"Fallback plan: {steps}")
            return steps

        ctx = memory.get_context()
        resp = ask(
            user_prompt=plan_prompt(task),
            system_prompt=PLANNER_SYSTEM,
            memory_context=ctx,
            max_tokens=400,
            timeout=10,
        )

        if not resp:
            steps = FallbackPlanner.plan(task)
            logger.info(f"LLM unavailable, fallback plan: {steps}")
            return steps

        if resp.upper().startswith("DIRECT"):
            return [resp.split("—", 1)[-1].strip() if "—" in resp else task]

        steps = [l.strip() for l in resp.split('\n') if l.strip()]
        steps = [s.lstrip("0123456789.-) ") for s in steps if s]
        if not steps:
            return FallbackPlanner.plan(task)

        logger.info(f"LLM plan ({len(steps)} steps): {steps}")
        return steps
