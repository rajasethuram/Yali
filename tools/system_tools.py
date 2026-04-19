import os
import subprocess

def open_application(app_name):
    try:
        system = os.name
        if os.name == 'nt':
            if app_name.lower() == 'chrome':
                os.system('start chrome')
            elif app_name.lower() == 'notepad':
                os.system('start notepad')
            elif app_name.lower() == 'vscode':
                os.system('start code')
            else:
                subprocess.Popen(app_name)
        else:
            subprocess.Popen([app_name])
        return f"Opened {app_name}"
    except Exception as e:
        return str(e)

def run_shell(command):
    try:
        result = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT, universal_newlines=True)
        return result
    except subprocess.CalledProcessError as e:
        return f"Command error: {e.output}"
