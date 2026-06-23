"""Inicializador do Cassol PreCalc empacotado para Windows."""

from __future__ import annotations

import os
import socket
import sys
from pathlib import Path


def _bundle_dir() -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))


def _working_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def main() -> None:
    os.chdir(_working_dir())
    app_path = _bundle_dir() / "app.py"
    if not app_path.exists():
        raise FileNotFoundError("O arquivo interno app.py nao foi encontrado.")

    port = _free_port()
    sys.argv = [
        "streamlit",
        "run",
        str(app_path),
        "--server.address=127.0.0.1",
        "--server.port={}".format(port),
        "--server.headless=false",
        "--server.fileWatcherType=none",
        "--browser.gatherUsageStats=false",
        "--global.developmentMode=false",
    ]

    from streamlit.web.cli import main as streamlit_main

    streamlit_main()


if __name__ == "__main__":
    main()
