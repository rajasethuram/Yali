import asyncio
from tools.system_tools import run_shell, open_application
from tools.file_tools import write_file
from tools.web_tools import search_web
from core.text_to_speech import speak

class ExecutorAgent:
    async def execute_step(self, step):
        # Very simple rule-based step execution
        step_l = step.lower()
        if step_l.startswith('open '):
            app = step.split(' ', 1)[1]
            return open_application(app)
        if step_l.startswith('search '):
            query = step.split(' ', 1)[1]
            result = search_web(query)
            return result
        if step_l.startswith('say '):
            text = step.split(' ', 1)[1]
            speak(text)
            return text
        if step_l.startswith('create file') or 'create file' in step_l:
            # parse "create file filename with content"
            try:
                parts = step.split('create file',1)[1].strip()
                if 'with' in parts:
                    fname, content = parts.split('with',1)
                    fname = fname.strip()
                    content = content.strip()
                else:
                    fname = parts.strip(); content = ''
                res = write_file(fname, content)
                return res
            except Exception as e:
                return str(e)
        # fallback: run shell
        return run_shell(step)
