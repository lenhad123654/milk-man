import os


DEFAULT_CLIENT_PORT = 8000
_client_port = int(os.environ.get("MILK_MAN_CLIENT_PORT", str(DEFAULT_CLIENT_PORT)))


def get_client_port() -> int:
    return _client_port


def set_client_port(port: int) -> None:
    if not 1 <= port <= 65535:
        raise ValueError("Port must be between 1 and 65535.")

    global _client_port
    _client_port = port
