def execute_python(code):
    try:
        exec(code)
        return "Execution successful"
    except Exception as e:
        return f"Execution error: {e}"