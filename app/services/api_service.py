"""Background runner for optional FastAPI status server."""

from __future__ import annotations

import logging
import threading

import uvicorn
from fastapi import FastAPI


class ApiService:
    """Run FastAPI app in background thread for local monitoring endpoints."""

    def __init__(
        self,
        api_app: FastAPI,
        host: str,
        port: int,
        logger: logging.Logger | None = None,
    ) -> None:
        self._api_app = api_app
        self._host = host
        self._port = port
        self._logger = logger or logging.getLogger("app")
        self._server: uvicorn.Server | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        """Start API server in daemon thread."""
        if self._thread is not None and self._thread.is_alive():
            return
        config = uvicorn.Config(
            app=self._api_app,
            host=self._host,
            port=self._port,
            log_level="info",
        )
        self._server = uvicorn.Server(config=config)
        self._thread = threading.Thread(target=self._server.run, daemon=True, name="api-thread")
        self._thread.start()
        self._logger.info("API service started at http://%s:%s", self._host, self._port)

    def stop(self) -> None:
        """Signal API server to shut down."""
        if self._server is not None:
            self._server.should_exit = True
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._logger.info("API service stopped.")

