import logging
from brain.prompt_engine import plan_prompt
from brain.ollama_client import ask_llm
from swarm.fallback_planner import FallbackPlanner

logger = logging.getLogger('yali')

class PlannerAgent:
    async def plan(self, task):
        try:
            # Try LLM first
            prompt = plan_prompt(task)
            resp = ask_llm(prompt)
            
            # Check if response is an error or too short
            if not resp or 'Error' in resp or 'error' in resp or 'timeout' in resp.lower() or len(resp) < 5:
                logger.warning(f"LLM error or empty response: {resp[:100] if resp else 'empty'}")
                raise Exception("LLM unavailable")
            
            # Parse LLM response - filter out empty lines
            steps = [line.strip() for line in resp.split('\n') if line.strip() and not line.startswith('Error')]
            if not steps:
                raise Exception("No steps generated")
            
            logger.info(f"Using LLM-generated plan with {len(steps)} steps: {steps}")
            return steps
            
        except Exception as e:
            # Fallback to rule-based planner
            logger.info(f"LLM failed ({type(e).__name__}), using fallback planner for: {task}")
            steps = FallbackPlanner.plan(task)
            logger.info(f"Fallback plan: {steps}")
            return steps
