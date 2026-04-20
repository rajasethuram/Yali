import os
import platform
import subprocess
import webbrowser


def open_app(app_name):
    try:
        system = platform.system().lower()

        if system == "windows":
            apps = {
                "notepad": "notepad",
                "calculator": "calc",
                "chrome": "start chrome",
                "vscode": "code"
            }

            if app_name in apps:
                os.system(apps[app_name])
                return f"Opening {app_name}"
            else:
                return "App not mapped"

        return "Unsupported OS"

    except Exception as e:
        return str(e)


def open_website(url):
    webbrowser.open(url)
    return f"Opening {url}"


def system_action(command):
    command = command.lower()

    if "shutdown" in command:
        os.system("shutdown /s /t 1")
        return "Shutting down"

    elif "restart" in command:
        os.system("shutdown /r /t 1")
        return "Restarting"

    return "Unknown command"