from __future__ import annotations

import asyncio
import threading
import time
from typing import Optional

from PySide6.QtCore import QObject, Signal

from localdog.proxy import run_proxy_async, request_stop, is_running


class ProxyRunner(QObject):
    started = Signal()
    stopped = Signal()
    failed = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def is_running(self) -> bool:
        return is_running()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return

        def target() -> None:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self._loop = loop
            try:
                self.started.emit()
                loop.run_until_complete(run_proxy_async())
            except Exception as exc:
                self.failed.emit(str(exc))
            finally:
                self.stopped.emit()
                self._loop = None

        self._thread = threading.Thread(target=target, name="localdog-proxy", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        print("[DEBUG] ProxyRunner.stop() called")
        request_stop()
        if self._thread and self._thread.is_alive():
            deadline = time.monotonic() + 3.0
            while self._thread.is_alive() and time.monotonic() < deadline:
                time.sleep(0.05)
            if self._thread.is_alive() and self._loop is not None:
                print("[DEBUG] Force stopping event loop and cancelling all tasks")
                self._loop.call_soon_threadsafe(lambda: [t.cancel() for t in asyncio.all_tasks(self._loop) if t is not asyncio.current_task()])
                time.sleep(0.2)
                self._loop.call_soon_threadsafe(self._loop.stop)
                time.sleep(0.5)
            if self._thread.is_alive():
                print("[DEBUG] Proxy thread still alive after force stop")
            else:
                print("[DEBUG] Proxy thread finished after force stop")