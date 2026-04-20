class ValidatorAgent:
    async def validate(self, step_result):
        # Very simple validation heuristics
        if isinstance(step_result, str) and (step_result.lower().startswith('error') or 'error' in step_result.lower()):
            return False, 'Error detected'
        return True, 'OK'
