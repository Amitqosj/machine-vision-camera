"""Qt logging bridge to show runtime logs in desktop UI."""

from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Signal


class QtLogEmitter(QObject):
    """Signal emitter used to forward log records to UI thread."""

    log_message = Signal(str)


class QtLogHandler(logging.Handler):
    """Custom logging handler that emits Qt signals."""

    def __init__(self) -> None:
        super().__init__()
        self.emitter = QtLogEmitter()

    def emit(self, record: logging.LogRecord) -> None:
        message = self.format(record)
        self.emitter.log_message.emit(message)

