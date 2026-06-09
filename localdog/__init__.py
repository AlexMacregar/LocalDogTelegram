from __future__ import annotations

__app_name__ = "LocalDog"
__version__ = "1.0.0"

from localdog.proxy import ProxyConfig, proxy_config, parse_dc_ip_list
from localdog.proxy import run_proxy, run_proxy_async, request_stop, is_running
from localdog.proxy import stats
from localdog.proxy import build_link, link_host

__all__ = [
    "ProxyConfig",
    "proxy_config",
    "parse_dc_ip_list",
    "run_proxy",
    "run_proxy_async",
    "request_stop",
    "is_running",
    "stats",
    "build_link",
    "link_host",
]