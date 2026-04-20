import asyncio
import logging
from swarm.planner_agent import PlannerAgent
from swarm.executor_agent import ExecutorAgent
from swarm.validator_agent import ValidatorAgent
from swarm.self_healing_agent import SelfHealingAgent
from memory.memory_store import save as mem_save
from core.text_to_speech import speak
from ui.server import broadcast_status

logger = logging.getLogger('yali')

class Orchestrator:
    def __init__(self):
        self.planner = PlannerAgent()
        self.executor = ExecutorAgent()
        self.validator = ValidatorAgent()
        self.self_healer = SelfHealingAgent()

    async def handle_task(self, task):
        logger.info(f"Orchestrator: planning for task: {task}")
        await broadcast_status({"pipeline": "planning", "task": task})
        steps = await self.planner.plan(task)
        logger.info(f"Plan: {steps}")
        await broadcast_status({"pipeline": "planned", "task": task, "steps": len(steps)})

        results = []
        for step in steps:
            # execute with self-healing
            await broadcast_status({"pipeline": "executing", "step": step})
            try:
                res = await self.self_healer.attempt(self.executor.execute_step, step)
            except Exception as e:
                res = f"Execution failed: {e}"
            ok, msg = await self.validator.validate(res)
            await broadcast_status({"pipeline": "validated", "step": step, "ok": ok, "msg": msg})
            results.append({'step': step, 'result': res, 'ok': ok, 'msg': msg})
            if not ok:
                logger.warning(f"Validation failed for step: {step} -> {res}")
        final = '\n'.join([f"{r['step']} => {r['result']}" for r in results])
        mem_save(task, final)
        await broadcast_status({"pipeline": "completed", "task": task, "results": [{"step": r['step'], "ok": r['ok']} for r in results]})
        speak("Task completed")
        return results
