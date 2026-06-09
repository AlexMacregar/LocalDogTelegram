from __future__ import annotations

import asyncio
import logging
import struct
from typing import List, Optional

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from localdog.proxy.protocol import (
    PROTO_ABRIDGED_INT,
    PROTO_INTERMEDIATE_INT,
    PROTO_PADDED_INTERMEDIATE_INT,
    ZERO_64,
    CryptoContext,
)
from localdog.proxy.stats import stats
from localdog.proxy.ws import WebSocket

log = logging.getLogger("localdog")

_st_I_le = struct.Struct("<I")


class MsgSplitter:
    __slots__ = ("_dec", "_proto", "_cipher", "_plain", "_disabled")

    def __init__(self, relay_init: bytes, proto_int: int):
        cipher = Cipher(algorithms.AES(relay_init[8:40]),
                        modes.CTR(relay_init[40:56]))
        self._dec = cipher.encryptor()
        self._dec.update(ZERO_64)
        self._proto = proto_int
        self._cipher = bytearray()
        self._plain = bytearray()
        self._disabled = False

    def split(self, chunk: bytes) -> List[bytes]:
        if not chunk:
            return []
        if self._disabled:
            return [chunk]

        self._cipher.extend(chunk)
        self._plain.extend(self._dec.update(chunk))

        out: List[bytes] = []
        while self._cipher:
            n = self._next_len()
            if n is None:
                break
            if n <= 0:
                out.append(bytes(self._cipher))
                self._cipher.clear()
                self._plain.clear()
                self._disabled = True
                break
            out.append(bytes(self._cipher[:n]))
            del self._cipher[:n]
            del self._plain[:n]
        return out

    def flush(self) -> List[bytes]:
        if not self._cipher:
            return []
        tail = bytes(self._cipher)
        self._cipher.clear()
        self._plain.clear()
        return [tail]

    def _next_len(self) -> Optional[int]:
        if not self._plain:
            return None
        if self._proto == PROTO_ABRIDGED_INT:
            first = self._plain[0]
            if first in (0x7F, 0xFF):
                if len(self._plain) < 4:
                    return None
                payload = int.from_bytes(self._plain[1:4], "little") * 4
                head = 4
            else:
                payload = (first & 0x7F) * 4
                head = 1
            if payload <= 0:
                return 0
            total = head + payload
            return total if len(self._plain) >= total else None
        if self._proto in (PROTO_INTERMEDIATE_INT,
                            PROTO_PADDED_INTERMEDIATE_INT):
            if len(self._plain) < 4:
                return None
            payload = _st_I_le.unpack_from(self._plain, 0)[0] & 0x7FFFFFFF
            if payload <= 0:
                return 0
            total = 4 + payload
            return total if len(self._plain) >= total else None
        return 0


async def bridge_ws(reader, writer, ws: WebSocket, *, label: str,
                    ctx: CryptoContext, dc: int, is_media: bool,
                    splitter: Optional[MsgSplitter] = None) -> None:
    media_tag = "m" if is_media else ""
    up = down = 0

    async def tcp_to_ws():
        nonlocal up
        try:
            while True:
                chunk = await reader.read(65536)
                if not chunk:
                    if splitter:
                        tail = splitter.flush()
                        if tail:
                            await ws.send(tail[0])
                    break
                up += len(chunk)
                stats.bytes_up += len(chunk)
                plain = ctx.clt_dec.update(chunk)
                cipher = ctx.tg_enc.update(plain)
                if splitter:
                    parts = splitter.split(cipher)
                    if not parts:
                        continue
                    if len(parts) == 1:
                        await ws.send(parts[0])
                    else:
                        await ws.send_batch(parts)
                else:
                    await ws.send(cipher)
        except (asyncio.CancelledError, ConnectionError, OSError):
            return
        except Exception as exc:
            log.debug("[%s] tcp->ws ended: %s", label, exc)

    async def ws_to_tcp():
        nonlocal down
        try:
            while True:
                data = await ws.recv()
                if data is None:
                    break
                down += len(data)
                stats.bytes_down += len(data)
                plain = ctx.tg_dec.update(data)
                writer.write(ctx.clt_enc.update(plain))
                await writer.drain()
        except (asyncio.CancelledError, ConnectionError, OSError):
            return
        except Exception as exc:
            log.debug("[%s] ws->tcp ended: %s", label, exc)

    tasks = [asyncio.create_task(tcp_to_ws()),
             asyncio.create_task(ws_to_tcp())]
    try:
        await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    finally:
        for t in tasks:
            t.cancel()
        for t in tasks:
            try:
                await t
            except BaseException:
                pass
        log.info("[%s] DC%d%s ws closed up=%dB down=%dB",
                 label, dc, media_tag, up, down)
        await ws.close()
        try:
            writer.close()
            await writer.wait_closed()
        except BaseException:
            pass


async def bridge_tcp(reader, writer, dst: str, port: int, *,
                    label: str, ctx: CryptoContext,
                    relay_init: bytes) -> bool:
    try:
        rr, rw = await asyncio.wait_for(
            asyncio.open_connection(dst, port), timeout=10)
    except Exception as exc:
        log.warning("[%s] TCP fallback %s:%d failed: %s",
                    label, dst, port, repr(exc))
        return False

    stats.connections_tcp += 1
    rw.write(relay_init)
    await rw.drain()

    async def forward(src, dst_w, is_up):
        try:
            while True:
                data = await src.read(65536)
                if not data:
                    break
                if is_up:
                    stats.bytes_up += len(data)
                    plain = ctx.clt_dec.update(data)
                    data = ctx.tg_enc.update(plain)
                else:
                    stats.bytes_down += len(data)
                    plain = ctx.tg_dec.update(data)
                    data = ctx.clt_enc.update(plain)
                dst_w.write(data)
                await dst_w.drain()
        except (asyncio.CancelledError, ConnectionError, OSError):
            return
        except Exception as exc:
            log.debug("[%s] forward ended: %s", label, exc)

    tasks = [
        asyncio.create_task(forward(reader, rw, True)),
        asyncio.create_task(forward(rr, writer, False)),
    ]
    try:
        await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    finally:
        for t in tasks:
            t.cancel()
        for t in tasks:
            try:
                await t
            except BaseException:
                pass
        for w in (writer, rw):
            try:
                w.close()
                await w.wait_closed()
            except BaseException:
                pass
    return True
