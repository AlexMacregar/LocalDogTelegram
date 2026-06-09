from __future__ import annotations

import asyncio
import base64
import os
import socket as _socket
import ssl
import struct
from typing import List, Optional, Tuple

_ssl_ctx = ssl.create_default_context()
_ssl_ctx.check_hostname = False
_ssl_ctx.verify_mode = ssl.CERT_NONE

_st_BB = struct.Struct(">BB")
_st_BBH = struct.Struct(">BBH")
_st_BBQ = struct.Struct(">BBQ")
_st_BB4s = struct.Struct(">BB4s")
_st_BBH4s = struct.Struct(">BBH4s")
_st_BBQ4s = struct.Struct(">BBQ4s")
_st_H = struct.Struct(">H")
_st_Q = struct.Struct(">Q")


class WsHandshakeError(Exception):
    def __init__(self, status: int, line: str, location: Optional[str] = None):
        self.status = status
        self.line = line
        self.location = location
        super().__init__(f"HTTP {status}: {line}")

    @property
    def is_redirect(self) -> bool:
        return self.status in (301, 302, 303, 307, 308)


def tune_socket(transport, buffer_size: int) -> None:
    sock = transport.get_extra_info("socket")
    if sock is None:
        return
    try:
        sock.setsockopt(_socket.IPPROTO_TCP, _socket.TCP_NODELAY, 1)
    except (OSError, AttributeError):
        pass
    try:
        sock.setsockopt(_socket.SOL_SOCKET, _socket.SO_RCVBUF, buffer_size)
        sock.setsockopt(_socket.SOL_SOCKET, _socket.SO_SNDBUF, buffer_size)
    except OSError:
        pass


def _xor_mask(data: bytes, mask: bytes) -> bytes:
    if not data:
        return data
    n = len(data)
    rep = (mask * (n // 4 + 1))[:n]
    return (int.from_bytes(data, "big")
            ^ int.from_bytes(rep, "big")).to_bytes(n, "big")


class WebSocket:

    __slots__ = ("reader", "writer", "_closed")

    OP_BINARY = 0x2
    OP_CLOSE = 0x8
    OP_PING = 0x9
    OP_PONG = 0xA

    def __init__(self, reader, writer):
        self.reader = reader
        self.writer = writer
        self._closed = False

    @property
    def closed(self) -> bool:
        return self._closed

    @staticmethod
    async def connect(host: str, sni: str, *, timeout: float = 10.0,
                      buffer_size: int = 256 * 1024,
                      path: str = "/apiws",
                      dst: Optional[str] = None) -> "WebSocket":
        """Connect to WebSocket, optionally adding ?dst= parameter for Cloudflare Worker."""
        if dst:
            path = f"/apiws?dst={dst}"
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, 443, ssl=_ssl_ctx,
                                    server_hostname=sni),
            timeout=min(timeout, 10),
        )
        tune_socket(writer.transport, buffer_size)

        ws_key = base64.b64encode(os.urandom(16)).decode()
        req = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {sni}\r\n"
            f"Upgrade: websocket\r\n"
            f"Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {ws_key}\r\n"
            f"Sec-WebSocket-Version: 13\r\n"
            f"Sec-WebSocket-Protocol: binary\r\n"
            f"\r\n"
        ).encode()
        writer.write(req)
        await writer.drain()

        lines: List[str] = []
        try:
            while True:
                line = await asyncio.wait_for(reader.readline(),
                                              timeout=timeout)
                if line in (b"\r\n", b"\n", b""):
                    break
                lines.append(line.decode("utf-8", errors="replace").strip())
        except asyncio.TimeoutError:
            writer.close()
            raise

        if not lines:
            writer.close()
            raise WsHandshakeError(0, "empty response")

        first = lines[0]
        parts = first.split(" ", 2)
        try:
            status = int(parts[1]) if len(parts) >= 2 else 0
        except ValueError:
            status = 0

        if status == 101:
            return WebSocket(reader, writer)

        headers = {}
        for h in lines[1:]:
            if ":" in h:
                k, v = h.split(":", 1)
                headers[k.strip().lower()] = v.strip()
        writer.close()
        raise WsHandshakeError(status, first, headers.get("location"))

    async def send(self, data: bytes) -> None:
        if self._closed:
            raise ConnectionError("WebSocket closed")
        self.writer.write(self._frame(self.OP_BINARY, data))
        await self.writer.drain()

    async def send_batch(self, parts: List[bytes]) -> None:
        if self._closed:
            raise ConnectionError("WebSocket closed")
        for part in parts:
            self.writer.write(self._frame(self.OP_BINARY, part))
        await self.writer.drain()

    async def recv(self) -> Optional[bytes]:
        while not self._closed:
            op, payload = await self._read_frame()
            if op == self.OP_CLOSE:
                self._closed = True
                try:
                    self.writer.write(self._frame(
                        self.OP_CLOSE, payload[:2] if payload else b""))
                    await self.writer.drain()
                except Exception:
                    pass
                return None
            if op == self.OP_PING:
                try:
                    self.writer.write(self._frame(self.OP_PONG, payload))
                    await self.writer.drain()
                except Exception:
                    pass
                continue
            if op == self.OP_PONG:
                continue
            if op in (0x1, 0x2):
                return payload
        return None

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            self.writer.write(self._frame(self.OP_CLOSE, b""))
            await self.writer.drain()
        except Exception:
            pass
        try:
            self.writer.close()
            await self.writer.wait_closed()
        except Exception:
            pass

    @staticmethod
    def _frame(op: int, data: bytes) -> bytes:
        n = len(data)
        fb = 0x80 | op
        mask = os.urandom(4)
        masked = _xor_mask(data, mask)
        if n < 126:
            return _st_BB4s.pack(fb, 0x80 | n, mask) + masked
        if n < 65536:
            return _st_BBH4s.pack(fb, 0x80 | 126, n, mask) + masked
        return _st_BBQ4s.pack(fb, 0x80 | 127, n, mask) + masked

    async def _read_frame(self) -> Tuple[int, bytes]:
        hdr = await self.reader.readexactly(2)
        op = hdr[0] & 0x0F
        n = hdr[1] & 0x7F
        if n == 126:
            n = _st_H.unpack(await self.reader.readexactly(2))[0]
        elif n == 127:
            n = _st_Q.unpack(await self.reader.readexactly(8))[0]
        if hdr[1] & 0x80:
            mask = await self.reader.readexactly(4)
            payload = await self.reader.readexactly(n)
            return op, _xor_mask(payload, mask)
        return op, await self.reader.readexactly(n)