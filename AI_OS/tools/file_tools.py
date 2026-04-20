import os

def read_file(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Read error: {e}"

def write_file(path, content):
    try:
        dirpath = os.path.dirname(path)
        if dirpath and not os.path.exists(dirpath):
            os.makedirs(dirpath, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return "OK"
    except Exception as e:
        return f"Write error: {e}"
