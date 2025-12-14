"""
macOS desktop wrapper for the FastAPI web UI.

- Starts the FastAPI server on localhost (random free port)
- Opens an embedded browser window via pywebview
- Shuts down the server when the window closes
"""

from __future__ import annotations

import socket
import threading
import time

import uvicorn
import webview


def _pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def main() -> None:
    from src.webapp.app import app

    port = _pick_free_port()
    config = uvicorn.Config(
        app=app,
        host="127.0.0.1",
        port=port,
        log_level="warning",
        access_log=False,
    )
    server = uvicorn.Server(config)

    t = threading.Thread(target=server.run, daemon=True)
    t.start()

    # Give uvicorn a moment to bind
    for _ in range(80):
        if server.started:
            break
        time.sleep(0.05)

    url = f"http://127.0.0.1:{port}/"
    webview.create_window("UmetaFlow", url, width=1200, height=820)
    webview.start()

    # Request server shutdown after window closes
    server.should_exit = True
    t.join(timeout=2.0)


if __name__ == "__main__":
    main()

