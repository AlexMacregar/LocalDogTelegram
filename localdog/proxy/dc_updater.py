from __future__ import annotations

import asyncio
import random
from typing import Dict, List, Optional

import aiohttp

from localdog.proxy.config import proxy_config, DC_LIST_URL

async def fetch_dc_servers() -> Dict[int, List[str]]:
    result: Dict[int, List[str]] = {}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(DC_LIST_URL, timeout=10) as resp:
                if resp.status == 200:
                    text = await resp.text()
                    for line in text.splitlines():
                        line = line.strip()
                        if not line or line.startswith('#'):
                            continue
                        if ':' not in line:
                            continue
                        dc_part, ips_part = line.split(':', 1)
                        try:
                            dc = int(dc_part)
                            ips = [ip.strip() for ip in ips_part.split(',') if ip.strip()]
                            if ips:
                                result[dc] = ips
                        except ValueError:
                            continue
    except Exception:
        pass
    return result

async def update_dc_redirects():
    servers = await fetch_dc_servers()
    if servers:
        new_redirects = {}
        for dc, ips in servers.items():
            if ips:
                new_redirects[dc] = ips[0]  # first as primary
        if new_redirects:
            proxy_config.dc_redirects = new_redirects
            return True
    return False

class DcBalancer:
    def __init__(self):
        self._current: Dict[int, int] = {}
        self._ips: Dict[int, List[str]] = {}

    def set_ips(self, dc: int, ips: List[str]):
        if ips:
            self._ips[dc] = ips
            self._current.setdefault(dc, 0)

    def get_next_ip(self, dc: int) -> Optional[str]:
        ips = self._ips.get(dc)
        if not ips:
            return None
        idx = self._current.get(dc, 0)
        ip = ips[idx % len(ips)]
        self._current[dc] = idx + 1
        return ip

    async def check_availability(self, ip: str, port: int = 443, timeout: float = 2.0) -> bool:
        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(ip, port), timeout=timeout)
            writer.close()
            await writer.wait_closed()
            return True
        except Exception:
            return False

    async def get_working_ip(self, dc: int, timeout: float = 1.5) -> Optional[str]:
        ips = self._ips.get(dc)
        if not ips:
            return None
        # Shuffle to avoid always checking same first
        shuffled = ips.copy()
        random.shuffle(shuffled)
        for ip in shuffled:
            if await self.check_availability(ip, timeout=timeout):
                return ip
        return None

balancer = DcBalancer()