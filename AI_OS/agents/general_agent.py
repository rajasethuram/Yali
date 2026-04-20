from tools.system_control import open_app, open_website, system_action


def run(ai, task):
    task_lower = task.lower()

    print("⚙️ Agent received task:", task)

    # -----------------------------
    # APP CONTROL
    # -----------------------------
    if "open" in task_lower:

        if "notepad" in task_lower:
            return open_app("notepad")

        elif "calculator" in task_lower:
            return open_app("calculator")

        elif "chrome" in task_lower:
            return open_app("chrome")

        elif "vscode" in task_lower:
            return open_app("vscode")

        elif "youtube" in task_lower:
            return open_website("https://youtube.com")

        elif "google" in task_lower:
            return open_website("https://google.com")

        else:
            return "App not recognized"

    # -----------------------------
    # SYSTEM CONTROL
    # -----------------------------
    if "shutdown" in task_lower or "restart" in task_lower:
        return system_action(task_lower)

    # -----------------------------
    # AI FALLBACK
    # -----------------------------
    return ai.ask(task)