from __future__ import annotations

import socket


def link_host(host: str) -> str:
    if host in ("0.0.0.0", ""):
        return "127.0.0.1"
    return host


def build_link(host: str, port: int, secret: str) -> str:
    return (
        f"tg://proxy?server={link_host(host)}"
        f"&port={port}&secret=dd{secret}"
    )
