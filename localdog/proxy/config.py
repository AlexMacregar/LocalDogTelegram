from __future__ import annotations

import json
import os
import socket
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Literal

DEFAULT_DC_REDIRECTS: Dict[int, str] = {
    2: "149.154.167.220",
    4: "149.154.167.220",
}

GITHUB_REPO = "AlexMacregar/LocalDogTelegram"
GITHUB_RELEASES_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
DC_LIST_URL = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/DCServers.txt"

@dataclass
class ProxyConfig:
    host: str = "127.0.0.1"
    port: int = 1443
    secret: str = field(default_factory=lambda: os.urandom(16).hex())
    dc_redirects: Dict[int, str] = field(default_factory=lambda: dict(DEFAULT_DC_REDIRECTS))
    buffer_kb: int = 256
    pool_size: int = 4
    verbose: bool = False
    auto_start: bool = False
    minimize_to_tray_on_start: bool = False
    notification_api: str = ""
    last_notification_id: int = 0
    theme: str = "system"
    cf_mode: Literal["off", "cf_proxy", "cf_worker"] = "off"
    cf_domain: str = ""
    cf_worker_domain: str = ""
    language: str = "ru"
    fake_tls: bool = False
    zapret_enabled: bool = False
    zapret_list_path: str = ""
    ws_path: str = "/apiws"
    ws_timeout: float = 10.0
    dc_ip_lists: Dict[int, List[str]] = field(default_factory=dict)

    def link_host(self) -> str:
        if self.host in ("0.0.0.0", ""):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                    s.connect(("8.8.8.8", 80))
                    return s.getsockname()[0]
            except OSError:
                return "127.0.0.1"
        return self.host

    @property
    def buffer_size(self) -> int:
        return max(4, self.buffer_kb) * 1024

proxy_config = ProxyConfig()

def parse_dc_ip_list(items: List[str]) -> Dict[int, str]:
    result: Dict[int, str] = {}
    for entry in items:
        if ":" not in entry:
            raise ValueError(f"expected DC:IP, got {entry!r}")
        dc_s, ip_s = entry.split(":", 1)
        try:
            dc = int(dc_s)
            socket.inet_aton(ip_s)
        except (ValueError, OSError) as exc:
            raise ValueError(f"invalid DC:IP {entry!r}") from exc
        result[dc] = ip_s
    return result

def config_path(path: str | None = None) -> Path:
    if path:
        return Path(path)
    base = os.environ.get("LOCALDOG_HOME")
    if base:
        return Path(base) / "config.json"
    if os.name == "nt":
        root = Path(os.environ.get("APPDATA", str(Path.home())))
        return root / "LocalDog" / "config.json"
    return Path.home() / ".config" / "localdog" / "config.json"

def load_config(path: str | None = None) -> ProxyConfig:
    path = config_path(path)
    if not path.exists():
        return proxy_config
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return proxy_config
    dc = data.get("dc_redirects") or {}
    proxy_config.dc_redirects = {int(k): str(v) for k, v in dc.items()} or dict(DEFAULT_DC_REDIRECTS)
    dc_lists = data.get("dc_ip_lists") or {}
    proxy_config.dc_ip_lists = {int(k): v for k, v in dc_lists.items()}
    for key in ("host", "port", "secret", "buffer_kb", "pool_size", "verbose",
                "auto_start", "minimize_to_tray_on_start", "notification_api",
                "last_notification_id", "theme", "cf_mode", "cf_domain", "cf_worker_domain",
                "language", "fake_tls", "zapret_enabled", "zapret_list_path", "ws_path", "ws_timeout"):
        if key in data:
            setattr(proxy_config, key, data[key])
    return proxy_config

def save_config(cfg: ProxyConfig | None = None) -> None:
    cfg = cfg or proxy_config
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = asdict(cfg)
    data["dc_redirects"] = {str(k): v for k, v in cfg.dc_redirects.items()}
    data["dc_ip_lists"] = {str(k): v for k, v in cfg.dc_ip_lists.items()}
    with path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)


def analyze_zapret_list(path: str) -> tuple[int, int, bool]:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Zapret list not found: {path}")
    total = 0
    matched = 0
    patterns = ("telegram", "web.telegram.org", "kws", "apiws", "mtproto")
    with path.open("r", encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            total += 1
            lower = line.lower()
            if any(pattern in lower for pattern in patterns):
                matched += 1
    return total, matched, matched > 0


def _normalize_strategy_name(name: str) -> str:
    clean = name.strip()
    clean = clean.replace("_", " ").replace("-", " ")
    if clean.lower().startswith("general"):
        clean = clean[7:].strip()
    clean = clean.strip("() ")
    if not clean:
        clean = "General"
    words: list[str] = []
    for part in clean.split():
        if part.isupper():
            words.append(part.title())
        else:
            words.append(part.capitalize())
    return " ".join(words)


def scan_zapret_strategies(path: str) -> list[str]:
    root = Path(path)
    if not root.exists():
        return []

    search_dirs: list[Path] = []
    if root.is_file():
        search_dirs.append(root.parent)
        if root.parent.name == "lists":
            search_dirs.append(root.parent.parent)

    search_dirs.extend(root.parents[:3])
    found: list[str] = []
    seen: set[str] = set()

    for directory in search_dirs:
        if not directory.exists():
            continue
        candidates = sorted(directory.glob("general*.bat"))
        if not candidates:
            candidates = sorted(directory.glob("*.bat"))
        for candidate in candidates:
            name = _normalize_strategy_name(candidate.stem)
            if name in seen:
                continue
            seen.add(name)
            found.append(name)
        if found:
            return found

    return []


def find_zapret_list_path(root: str | None = None) -> str:
    root_path = Path(root or Path.cwd())
    if not root_path.exists():
        return ""
    patterns = ["list-general.txt", "list-google.txt", "ipset-all.txt", "list-*.txt"]
    for pattern in patterns:
        for candidate in sorted(root_path.rglob(pattern)):
            if candidate.is_file():
                return str(candidate)
    return ""
