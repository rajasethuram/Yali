import json
import os
from datetime import datetime

FILE_PATH = "memory/logs.json"


# -----------------------------
# INIT STORAGE FILE
# -----------------------------
def _init_file():
    os.makedirs("memory", exist_ok=True)

    if not os.path.exists(FILE_PATH):
        with open(FILE_PATH, "w") as f:
            json.dump([], f)


# -----------------------------
# SAVE MEMORY
# -----------------------------
def save(task, response):
    _init_file()

    data = {
        "timestamp": str(datetime.now()),
        "task": task,
        "response": response
    }

    with open(FILE_PATH, "r") as f:
        logs = json.load(f)

    logs.append(data)

    with open(FILE_PATH, "w") as f:
        json.dump(logs, f, indent=4)

    print("💾 Memory saved")


# -----------------------------
# LOAD MEMORY
# -----------------------------
def load_all():
    _init_file()

    with open(FILE_PATH, "r") as f:
        return json.load(f)