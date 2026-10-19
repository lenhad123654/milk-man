import os
import sys


path = os.getcwd()


def change_path(new_path: str) -> str:
    try:
        os.chdir(new_path)
        global path
        path = os.getcwd()
        return new_path
    except OSError as e:
        return f"Error changing path: {e}"


def get_exec_path() -> str:
    if not os.path.exists(os.path.join(path, "venv", "bin", "python")):
        return sys.executable
    else:
        return os.path.join(path, "venv", "bin")
