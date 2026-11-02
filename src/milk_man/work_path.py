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


# to get the path of the python executble in the working directory
# fallback to the global python executable if not found
def get_exec_path() -> str:
    venv_python = os.path.join(path, ".venv", "bin", "python")

    if os.path.exists(venv_python):
        return venv_python

    return sys.executable
