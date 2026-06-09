from __future__ import annotations

import time
from dataclasses import dataclass, field


def human_bytes(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if abs(n) < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def human_speed(bps: float) -> str:
    if bps < 1024:
        return f"{bps:.0f} B/s"
    elif bps < 1024 * 1024:
        return f"{bps/1024:.1f} KB/s"
    else:
        return f"{bps/(1024*1024):.1f} MB/s"


@dataclass
class Stats:
    connections_total: int = 0
    connections_active: int = 0
    connections_ws: int = 0
    connections_tcp: int = 0
    connections_bad: int = 0
    ws_errors: int = 0
    bytes_up: int = 0
    bytes_down: int = 0
    # for speed calculation
    _last_bytes_up: int = field(default=0, repr=False)
    _last_bytes_down: int = field(default=0, repr=False)
    _last_time: float = field(default_factory=time.time, repr=False)
    _speed_up: float = 0.0
    _speed_down: float = 0.0

    def reset(self) -> None:
        for f in self.__dataclass_fields__:
            if not f.startswith("_"):
                setattr(self, f, 0)
        self._last_bytes_up = 0
        self._last_bytes_down = 0
        self._last_time = time.time()
        self._speed_up = 0.0
        self._speed_down = 0.0

    def update_speed(self) -> None:
        now = time.time()
        delta = now - self._last_time
        if delta >= 0.5:
            up_diff = self.bytes_up - self._last_bytes_up
            down_diff = self.bytes_down - self._last_bytes_down
            self._speed_up = up_diff / delta if delta > 0 else 0
            self._speed_down = down_diff / delta if delta > 0 else 0
            self._last_bytes_up = self.bytes_up
            self._last_bytes_down = self.bytes_down
            self._last_time = now

    @property
    def speed_up(self) -> float:
        return self._speed_up

    @property
    def speed_down(self) -> float:
        return self._speed_down

    def summary(self) -> str:
        return (
            f"active={self.connections_active}  "
            f"total={self.connections_total}  "
            f"ws={self.connections_ws}  "
            f"tcp={self.connections_tcp}  "
            f"up={human_bytes(self.bytes_up)}  "
            f"down={human_bytes(self.bytes_down)}"
        )


stats = Stats()