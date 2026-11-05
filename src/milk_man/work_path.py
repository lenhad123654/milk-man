import os
import sys


path = os.getcwd()


def change_path(new_path: str) -> str:
    try:
        expanded = os.path.expanduser(new_path)
        os.chdir(expanded)
        global path
        path = os.getcwd()
        return new_path
    except OSError as e:
        return f"Error changing path: {e}"


# to get the path of the python executble in the working directory
# fallback to the global python executable if not found
def get_exec_path() -> str:
    venv_dirs = [".venv", "venv"]
    candidates: list[str] = []

    if sys.platform == "win32":
        for vdir in venv_dirs:
            candidates.extend(
                [
                    os.path.join(path, vdir, "Scripts", "python.exe"),
                    os.path.join(path, vdir, "Scripts", "python"),
                    os.path.join(path, vdir, "bin", "python.exe"),
                    os.path.join(path, vdir, "bin", "python"),
                ]
            )
    else:
        for vdir in venv_dirs:
            candidates.extend(
                [
                    os.path.join(path, vdir, "bin", "python"),
                    os.path.join(path, vdir, "bin", "python3"),
                    os.path.join(path, vdir, "Scripts", "python.exe"),
                    os.path.join(path, vdir, "Scripts", "python"),
                ]
            )

    for venv_python in candidates:
        if os.path.exists(venv_python):
            return venv_python

    return sys.executable
