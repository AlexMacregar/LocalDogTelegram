from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Signal


class LogBridge(QObject):
    line = Signal(str)


class _Handler(logging.Handler):
    def __init__(self, bridge: LogBridge):
        super().__init__()
        self.bridge = bridge

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
        except Exception:
            return
        self.bridge.line.emit(msg)


def install(bridge: LogBridge, *, verbose: bool = False) -> None:
    handler = _Handler(bridge)
    handler.setFormatter(logging.Formatter(
        "%(asctime)s  %(levelname)-5s  %(message)s", datefmt="%H:%M:%S"))
    root = logging.getLogger()
    root.setLevel(logging.DEBUG if verbose else logging.INFO)
    if not any(isinstance(h, _Handler) for h in root.handlers):
        root.addHandler(handler)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
