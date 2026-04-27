import logging
from core.llm_client import ask
from brain.prompt_engine import VALIDATOR_SYSTEM, validate_prompt

logger = logging.getLogger('yali')


class ValidatorAgent:
    async def validate(self, step_result: str, step: str = "") -> tuple:
        if not isinstance(step_result, str):
            step_result = str(step_result)

        if step_result.lower().startswith('error') or 'traceback' in step_result.lower():
            return False, 'Error detected in result'

        if step:
            resp = ask(
                user_prompt=validate_prompt(step, step_result),
                system_prompt=VALIDATOR_SYSTEM,
                max_tokens=80,
            )
            if resp.upper().startswith("FAIL"):
                reason = resp.split("—", 1)[-1].strip() if "—" in resp else resp
                return False, reason

        return True, 'OK'
