from __future__ import annotations

import asyncio
import logging
import socket as _socket
import time
from typing import Dict, List, Optional, Set, Tuple

from localdog.proxy.bridge import MsgSplitter, bridge_tcp, bridge_ws
from localdog.proxy.config import proxy_config
from localdog.proxy.protocol import (
    HANDSHAKE_LEN,
    build_crypto_context,
    decode_client_init,
    generate_relay_init,
    proto_tag_to_int,
)
from localdog.proxy.stats import stats
from localdog.proxy.ws import WebSocket, tune_socket, WsHandshakeError

log = logging.getLogger("localdog")

DC_FAIL_COOLDOWN = 30.0
WS_FAIL_TIMEOUT = 2.0

_DC_DEFAULT_IPS: Dict[int, str] = {
    1: "149.154.175.50",
    2: "149.154.167.51",
    3: "149.154.175.100",
    4: "149.154.167.91",
    5: "149.154.171.5",
}

_ws_blacklist: Set[str] = set()
_dc_fail_until: Dict[str, float] = {}

_server: Optional[asyncio.AbstractServer] = None
_stop_event: Optional[asyncio.Event] = None
_loop: Optional[asyncio.AbstractEventLoop] = None
_clients: Set[asyncio.Task] = set()


def _ws_domains(dc: int, is_media: bool) -> List[str]:
    if dc == 203:
        dc = 2
    a, b = f"kws{dc}-1.web.telegram.org", f"kws{dc}.web.telegram.org"
    return [a, b] if is_media else [b, a]


async def _handle(reader, writer, secret: bytes) -> None:
    stats.connections_total += 1
    stats.connections_active += 1
    peer = writer.get_extra_info("peername")
    label = f"{peer[0]}:{peer[1]}" if peer else "?"
    tune_socket(writer.transport, proxy_config.buffer_kb * 1024)

    try:
        try:
            handshake = await asyncio.wait_for(
                reader.readexactly(HANDSHAKE_LEN), timeout=10)
        except asyncio.IncompleteReadError:
            log.debug("[%s] disconnected before handshake", label)
            return

        decoded = decode_client_init(handshake, secret)
        if decoded is None:
            stats.connections_bad += 1
            log.warning("[%s] bad handshake (wrong secret?)", label)
            try:
                while await reader.read(4096):
                    pass
            except Exception:
                pass
            return

        dc, is_media, proto_tag, prekey_iv = decoded
        if dc == 203:
            dc = 2
        proto_int = proto_tag_to_int(proto_tag)
        dc_idx = -dc if is_media else dc
        dc_key = f"{dc}{'m' if is_media else ''}"
        media_tag = " media" if is_media else ""

        relay_init = generate_relay_init(proto_tag, dc_idx)
        ctx = build_crypto_context(prekey_iv, secret, relay_init)
        log.debug("[%s] handshake DC%d%s proto=0x%08X",
                  label, dc, media_tag, proto_int)

        target = proxy_config.dc_redirects.get(dc)
        ws: Optional[WebSocket] = None
        all_redirects = True
        ws_redirected = False

        # Cloudflare handling
        cf_mode = proxy_config.cf_mode
        cf_domain = proxy_config.cf_domain
        cf_worker = proxy_config.cf_worker_domain

        if cf_mode == "cf_proxy" and cf_domain:
            try:
                url = f"wss://{cf_domain}/apiws"
                log.info("[%s] DC%d%s -> CF Proxy %s", label, dc, media_tag, url)
                ws = await WebSocket.connect(
                    cf_domain, cf_domain, timeout=proxy_config.ws_timeout,
                    buffer_size=proxy_config.buffer_size,
                    path=proxy_config.ws_path)
                all_redirects = False
            except Exception as exc:
                log.warning("[%s] CF Proxy failed: %s", label, exc)
        elif cf_mode == "cf_worker" and cf_worker:
            if target:
                try:
                    url = f"wss://{cf_worker}/apiws?dst={target}"
                    log.info("[%s] DC%d%s -> CF Worker %s", label, dc, media_tag, url)
                    ws = await WebSocket.connect(
                        cf_worker, cf_worker, timeout=proxy_config.ws_timeout,
                        buffer_size=proxy_config.buffer_size,
                        path=proxy_config.ws_path,
                        dst=target)
                    all_redirects = False
                except Exception as exc:
                    log.warning("[%s] CF Worker failed: %s", label, exc)

        if ws is None:
            if target and dc_key not in _ws_blacklist:
                now = time.monotonic()
                fail_until = _dc_fail_until.get(dc_key, 0)
                ws_timeout = WS_FAIL_TIMEOUT if now < fail_until else 10.0

                for domain in _ws_domains(dc, is_media):
                    url = f"wss://{domain}/apiws"
                    log.info("[%s] DC%d%s -> %s via %s",
                             label, dc, media_tag, url, target)
                    try:
                        ws = await WebSocket.connect(
                            target, domain, timeout=ws_timeout,
                            buffer_size=proxy_config.buffer_kb * 1024,
                            path=proxy_config.ws_path)
                        all_redirects = False
                        break
                    except (WsHandshakeError, TimeoutError, asyncio.TimeoutError) as exc:
                        stats.ws_errors += 1
                        if isinstance(exc, WsHandshakeError) and exc.is_redirect:
                            ws_redirected = True
                            log.warning("[%s] DC%d%s %d from %s",
                                        label, dc, media_tag, exc.status, domain)
                            continue
                        all_redirects = False
                        msg = exc.line if isinstance(exc, WsHandshakeError) else repr(exc)
                        log.warning("[%s] DC%d%s ws: %s",
                                    label, dc, media_tag, msg)
                    except Exception as exc:
                        stats.ws_errors += 1
                        all_redirects = False
                        log.warning("[%s] DC%d%s ws connect failed: %s",
                                    label, dc, media_tag, repr(exc))

        if ws is None:
            if ws_redirected and all_redirects:
                _ws_blacklist.add(dc_key)
            elif ws_redirected:
                _dc_fail_until[dc_key] = time.monotonic() + DC_FAIL_COOLDOWN
            else:
                _dc_fail_until[dc_key] = time.monotonic() + DC_FAIL_COOLDOWN

            fallback = _DC_DEFAULT_IPS.get(dc) or target
            if not fallback:
                log.warning("[%s] DC%d%s no route", label, dc, media_tag)
                return
            log.info("[%s] DC%d%s -> TCP fallback %s:443",
                     label, dc, media_tag, fallback)
            await bridge_tcp(reader, writer, fallback, 443,
                             label=label, ctx=ctx, relay_init=relay_init)
            return

        _dc_fail_until.pop(dc_key, None)
        stats.connections_ws += 1

        try:
            splitter = MsgSplitter(relay_init, proto_int)
        except Exception:
            splitter = None

        await ws.send(relay_init)
        await bridge_ws(reader, writer, ws, label=label, ctx=ctx,
                        dc=dc, is_media=is_media, splitter=splitter)

    except asyncio.TimeoutError:
        log.warning("[%s] timeout", label)
    except asyncio.IncompleteReadError:
        log.debug("[%s] disconnected", label)
    except asyncio.CancelledError:
        log.debug("[%s] cancelled", label)
    except ConnectionResetError:
        log.debug("[%s] reset", label)
    except Exception as exc:
        log.error("[%s] unexpected: %s", label, exc, exc_info=True)
    finally:
        stats.connections_active -= 1
        try:
            writer.close()
            await writer.wait_closed()
        except BaseException:
            pass


async def run_proxy_async(stop_event: Optional[asyncio.Event] = None) -> None:
    global _server, _stop_event, _loop
    _stop_event = stop_event or asyncio.Event()
    _loop = asyncio.get_running_loop()
    _ws_blacklist.clear()
    _dc_fail_until.clear()
    _clients.clear()
    stats.reset()

    secret_bytes = bytes.fromhex(proxy_config.secret)

    def on_client(r, w):
        task = asyncio.create_task(_handle(r, w, secret_bytes))
        _clients.add(task)
        task.add_done_callback(_clients.discard)

    server = await asyncio.start_server(
        on_client, proxy_config.host, proxy_config.port)
    _server = server

    for sock in server.sockets:
        try:
            sock.setsockopt(_socket.IPPROTO_TCP, _socket.TCP_NODELAY, 1)
        except (OSError, AttributeError):
            pass

    log.info("LocalDog listening on %s:%d", proxy_config.host,
             proxy_config.port)
    log.info("secret=%s", proxy_config.secret)
    if proxy_config.cf_mode == "cf_proxy" and proxy_config.cf_domain:
        log.info("Cloudflare Proxy mode enabled (domain=%s)", proxy_config.cf_domain)
    elif proxy_config.cf_mode == "cf_worker" and proxy_config.cf_worker_domain:
        log.info("Cloudflare Worker mode enabled (worker=%s)", proxy_config.cf_worker_domain)
    else:
        for dc in sorted(proxy_config.dc_redirects):
            log.info("  DC%d -> %s", dc, proxy_config.dc_redirects[dc])

    try:
        async with server:
            serve_task = asyncio.create_task(server.serve_forever())
            stop_task = asyncio.create_task(_stop_event.wait())
            done, pending = await asyncio.wait(
                [serve_task, stop_task], return_when=asyncio.FIRST_COMPLETED)
            # Отменяем оставшиеся задачи
            for task in pending:
                task.cancel()
            if stop_task in done:
                server.close()
                try:
                    await server.wait_closed()
                except asyncio.CancelledError:
                    pass
    finally:
        # Отменяем клиентские задачи
        for task in _clients:
            task.cancel()
        if _clients:
            try:
                await asyncio.wait_for(asyncio.gather(*_clients, return_exceptions=True), timeout=1.0)
            except asyncio.TimeoutError:
                log.debug("Timeout while cancelling client tasks")
        _server = None
        _loop = None
        log.info("LocalDog stopped (%s)", stats.summary())
        print("[DEBUG] run_proxy_async finished")


def is_running() -> bool:
    return _server is not None


def request_stop() -> None:
    print("[DEBUG] request_stop() called")
    global _loop, _stop_event
    if _loop is None or _stop_event is None:
        print("[DEBUG] request_stop: loop or event is None")
        return
    _loop.call_soon_threadsafe(_stop_event.set)
    print("[DEBUG] request_stop: stop event set")


def run_proxy(stop_event: Optional[asyncio.Event] = None) -> None:
    try:
        asyncio.run(run_proxy_async(stop_event))
    except KeyboardInterrupt:
        log.info("interrupted")