import os
import threading
import time
import webbrowser

import uvicorn

from app import FRONTEND_URL, app as fastapi_app

HOST = os.getenv("MVS_HOST", "127.0.0.1")
PORT = int(os.getenv("MVS_PORT", "8000"))
OPEN_BROWSER = os.getenv("MVS_OPEN_BROWSER", "1").lower() not in {"0", "false", "no"}


def open_browser() -> None:
    time.sleep(2)
    webbrowser.open(FRONTEND_URL)


if __name__ == "__main__":
    if OPEN_BROWSER:
        threading.Thread(target=open_browser, daemon=True).start()
    uvicorn.run(fastapi_app, host=HOST, port=PORT, reload=False)

