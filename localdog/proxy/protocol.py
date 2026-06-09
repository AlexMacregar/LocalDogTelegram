from __future__ import annotations

import hashlib
import os
import struct
from typing import Optional, Tuple

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

ZERO_64 = b"\x00" * 64
HANDSHAKE_LEN = 64
SKIP_LEN = 8
PREKEY_LEN = 32
KEY_LEN = 32
IV_LEN = 16
PROTO_TAG_POS = 56
DC_IDX_POS = 60

PROTO_TAG_ABRIDGED = b"\xef\xef\xef\xef"
PROTO_TAG_INTERMEDIATE = b"\xee\xee\xee\xee"
PROTO_TAG_SECURE = b"\xdd\xdd\xdd\xdd"

PROTO_ABRIDGED_INT = 0xEFEFEFEF
PROTO_INTERMEDIATE_INT = 0xEEEEEEEE
PROTO_PADDED_INTERMEDIATE_INT = 0xDDDDDDDD

RESERVED_FIRST_BYTES = {0xEF}
RESERVED_STARTS = {
    b"\x48\x45\x41\x44",  # HEAD
    b"\x50\x4f\x53\x54",  # POST
    b"\x47\x45\x54\x20",  # GET
    b"\xee\xee\xee\xee",
    b"\xdd\xdd\xdd\xdd",
    b"\x16\x03\x01\x02",
}
RESERVED_CONTINUE = b"\x00\x00\x00\x00"


def decode_client_init(handshake: bytes, secret: bytes
                       ) -> Optional[Tuple[int, bool, bytes, bytes]]:
    prekey_iv = handshake[SKIP_LEN:SKIP_LEN + PREKEY_LEN + IV_LEN]
    prekey = prekey_iv[:PREKEY_LEN]
    iv = prekey_iv[PREKEY_LEN:]

    key = hashlib.sha256(prekey + secret).digest()
    decryptor = Cipher(algorithms.AES(key), modes.CTR(iv)).encryptor()
    decrypted = decryptor.update(handshake)

    proto_tag = decrypted[PROTO_TAG_POS:PROTO_TAG_POS + 4]
    if proto_tag not in (PROTO_TAG_ABRIDGED, PROTO_TAG_INTERMEDIATE,
                          PROTO_TAG_SECURE):
        return None

    dc_idx = int.from_bytes(
        decrypted[DC_IDX_POS:DC_IDX_POS + 2], "little", signed=True)
    return abs(dc_idx), dc_idx < 0, proto_tag, prekey_iv


def generate_relay_init(proto_tag: bytes, dc_idx: int) -> bytes:
    while True:
        rnd = bytearray(os.urandom(HANDSHAKE_LEN))
        if rnd[0] in RESERVED_FIRST_BYTES:
            continue
        if bytes(rnd[:4]) in RESERVED_STARTS:
            continue
        if rnd[4:8] == RESERVED_CONTINUE:
            continue
        break

    raw = bytes(rnd)
    enc_key = raw[SKIP_LEN:SKIP_LEN + PREKEY_LEN]
    enc_iv = raw[SKIP_LEN + PREKEY_LEN:SKIP_LEN + PREKEY_LEN + IV_LEN]
    encryptor = Cipher(algorithms.AES(enc_key), modes.CTR(enc_iv)).encryptor()

    tail_plain = proto_tag + struct.pack("<h", dc_idx) + os.urandom(2)
    encrypted_full = encryptor.update(raw)
    keystream_tail = bytes(encrypted_full[i] ^ raw[i] for i in range(56, 64))
    encrypted_tail = bytes(tail_plain[i] ^ keystream_tail[i] for i in range(8))

    out = bytearray(raw)
    out[PROTO_TAG_POS:HANDSHAKE_LEN] = encrypted_tail
    return bytes(out)


class CryptoContext:
    __slots__ = ("clt_dec", "clt_enc", "tg_enc", "tg_dec")

    def __init__(self, clt_dec, clt_enc, tg_enc, tg_dec):
        self.clt_dec = clt_dec
        self.clt_enc = clt_enc
        self.tg_enc = tg_enc
        self.tg_dec = tg_dec


def build_crypto_context(client_prekey_iv: bytes, secret: bytes,
                         relay_init: bytes) -> CryptoContext:
    clt_dec_prekey = client_prekey_iv[:PREKEY_LEN]
    clt_dec_iv = client_prekey_iv[PREKEY_LEN:]
    clt_dec_key = hashlib.sha256(clt_dec_prekey + secret).digest()

    clt_enc_prekey_iv = client_prekey_iv[::-1]
    clt_enc_key = hashlib.sha256(
        clt_enc_prekey_iv[:PREKEY_LEN] + secret).digest()
    clt_enc_iv = clt_enc_prekey_iv[PREKEY_LEN:]

    clt_dec = Cipher(algorithms.AES(clt_dec_key),
                     modes.CTR(clt_dec_iv)).encryptor()
    clt_enc = Cipher(algorithms.AES(clt_enc_key),
                     modes.CTR(clt_enc_iv)).encryptor()
    clt_dec.update(ZERO_64)

    relay_enc_key = relay_init[SKIP_LEN:SKIP_LEN + PREKEY_LEN]
    relay_enc_iv = relay_init[SKIP_LEN + PREKEY_LEN:
                              SKIP_LEN + PREKEY_LEN + IV_LEN]
    relay_dec_prekey_iv = relay_init[SKIP_LEN:
                                     SKIP_LEN + PREKEY_LEN + IV_LEN][::-1]
    relay_dec_key = relay_dec_prekey_iv[:KEY_LEN]
    relay_dec_iv = relay_dec_prekey_iv[KEY_LEN:]

    tg_enc = Cipher(algorithms.AES(relay_enc_key),
                    modes.CTR(relay_enc_iv)).encryptor()
    tg_dec = Cipher(algorithms.AES(relay_dec_key),
                    modes.CTR(relay_dec_iv)).encryptor()
    tg_enc.update(ZERO_64)

    return CryptoContext(clt_dec, clt_enc, tg_enc, tg_dec)


def proto_tag_to_int(proto_tag: bytes) -> int:
    if proto_tag == PROTO_TAG_ABRIDGED:
        return PROTO_ABRIDGED_INT
    if proto_tag == PROTO_TAG_INTERMEDIATE:
        return PROTO_INTERMEDIATE_INT
    return PROTO_PADDED_INTERMEDIATE_INT
