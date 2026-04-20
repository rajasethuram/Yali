"""
Fallback planner for when Ollama LLM is not available.
Handles common commands without needing external LLM.
"""
import re

class FallbackPlanner:
    """Simple rule-based task planner that doesn't require LLM"""
    
    @staticmethod
    def plan(task: str) -> list:
        """
        Convert a task into steps without LLM.
        Returns a list of command strings.
        """
        task = task.lower().strip()
        
        # Open application commands
        if 'open' in task:
            return FallbackPlanner._parse_open(task)
        
        # Create file commands
        if 'create' in task or 'write' in task:
            return FallbackPlanner._parse_create(task)
        
        # Help/capability commands
        if any(x in task for x in ['what can you do', 'what else', 'other things', 'help', 'who are you', 'what are other']):
            return ['say I can open applications, search the web, create files, and run system commands for you.']

        # Search/Info commands
        if any(x in task for x in ['weather', 'what is', 'who is', 'search for', 'stock', 'price']):
            return FallbackPlanner._parse_search(task)
        
        # Run/Execute commands
        if 'run' in task or 'execute' in task or 'start' in task:
            return FallbackPlanner._parse_run(task)
        
        # Default: treat as shell command
        return [task]
    
    @staticmethod
    def _parse_open(task: str) -> list:
        """Parse 'open X' commands"""
        apps = {
            'notepad': 'notepad.exe',
            'calc': 'calc.exe',
            'calculator': 'calc.exe',
            'paint': 'mspaint.exe',
            'word': 'winword.exe',
            'excel': 'excel.exe',
            'chrome': 'chrome.exe',
            'firefox': 'firefox.exe',
            'explorer': 'explorer.exe',
            'powershell': 'powershell.exe',
            'cmd': 'cmd.exe',
            'settings': 'ms-settings:',
            'task manager': 'taskmgr.exe',
        }
        
        for app_name, cmd in apps.items():
            if app_name in task:
                return [f'open {cmd}']
        
        # Generic open
        match = re.search(r'open\s+(\w+)', task)
        if match:
            return [f'open {match.group(1)}.exe']
        
        return ['open notepad.exe']
    
    @staticmethod
    def _parse_create(task: str) -> list:
        """Parse 'create file' or 'write' commands"""
        match = re.search(r'(create|write).*?(?:file|called)?\s+(\w+\.?\w*)', task)
        if match:
            filename = match.group(2)
            if '.' not in filename:
                filename += '.txt'
            return [f'create {filename}', f'write Hello from YALI AI_OS']
        
        return ['create test.txt']
    
    @staticmethod
    def _parse_search(task: str) -> list:
        """Parse search/info queries"""
        # Handle stock queries specially
        if any(x in task.lower() for x in ['stock', 'price', 'nasdaq', 'nyse', 'ticker', 'return', 'interday', 'friday']):
            # Extract relevant parts for stock query
            return [f'search {task}']
        
        # For general queries, extract the actual question
        question = task.replace('what is', '').replace('who is', '').replace('search for', '').strip()
        return [f'search {question}']
    
    @staticmethod
    def _parse_run(task: str) -> list:
        """Parse run/execute commands"""
        # Extract program name
        match = re.search(r'(?:run|execute|start)\s+(\w+(?:\.\w+)?)', task)
        if match:
            prog = match.group(1)
            if '.' not in prog:
                prog += '.exe'
            return [f'open {prog}']
        
        return [task]
