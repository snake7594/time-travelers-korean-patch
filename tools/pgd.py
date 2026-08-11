# -*- coding: utf-8 -*-
"""PGD decryption, ported from the public amctrl/kirk reference implementation.

Only the paths a drm_type==1 game-data PGD needs are implemented: KIRK CMD4
(AES-128-CBC encrypt, IV 0) and CMD7 (decrypt), the BBMac construction and
the BBCipher stream.  No fuse id and no PRNG are required, so nothing here
depends on a particular console.

The version key is recovered from the stored MAC via bbmac_getkey, which is
what lets us open the file without the key the game passes at runtime.
"""
import struct
from Crypto.Cipher import AES

from kirkkeys import KIRK47

LOC_1CD4 = bytes.fromhex('e350ed1d910a1fd029bb1c3ef34077fb')
LOC_1CE4 = bytes.fromhex('135fa47cab395ba476b8cca98f3a0445')
LOC_1CF4 = bytes.fromhex('678d7fa32a9ca0d1508ad8385e4b017e')
DNAS_1A90 = bytes.fromhex('ede25d2dbbf812e53c5c5932fae3e243')
DNAS_1AA0 = bytes.fromhex('2774fbeba4a001d702569e338c195783')

BUFSZ = 0x900


def _cbc_enc(seed, data):
    return AES.new(KIRK47[seed], AES.MODE_CBC, bytes(16)).encrypt(data)


def _cbc_dec(seed, data):
    return AES.new(KIRK47[seed], AES.MODE_CBC, bytes(16)).decrypt(data)


class Kirk:
    """Models the shared 'kirk_buf' the reference code passes around."""

    def __init__(self):
        self.buf = bytearray(BUFSZ)

    def cmd4(self, size, seed):
        # in  : buf[0x14 : 0x14+size]      out : same place
        self.buf[0x14:0x14 + size] = _cbc_enc(seed, bytes(self.buf[0x14:0x14 + size]))

    def cmd7(self, size, seed):
        # in  : buf[0x14 : 0x14+size]      out : buf[0 : size]   (note the shift)
        self.buf[0:size] = _cbc_dec(seed, bytes(self.buf[0x14:0x14 + size]))


def _sub_158(k, size, key, seed):
    """CBC-MAC step: xor the running key in, encrypt, keep the last block."""
    for i in range(16):
        k.buf[0x14 + i] ^= key[i]
    k.cmd4(size, seed)
    key[:] = k.buf[size + 4:size + 4 + 16]


def _sub_1F8(k, size, key, seed):
    tmp = bytes(k.buf[size + 0x14 - 16:size + 0x14])
    k.cmd7(size, seed)
    for i in range(16):
        k.buf[i] ^= key[i]
    key[:] = tmp


def _dbl(b):
    """GF(2^128) doubling, as used to derive the CMAC subkeys."""
    t = 0x87 if (b[0] & 0x80) else 0
    out = bytearray(16)
    for i in range(15):
        out[i] = ((b[i] << 1) | (b[i + 1] >> 7)) & 0xFF
    out[15] = ((b[15] << 1) & 0xFF) ^ t
    return out


class MacKey:
    def __init__(self, type_):
        self.type = type_
        self.key = bytearray(16)
        self.pad = bytearray(16)
        self.pad_size = 0


def bbmac_update(k, m, data):
    size = len(data)
    if m.pad_size + size <= 16:
        m.pad[m.pad_size:m.pad_size + size] = data
        m.pad_size += size
        return
    p = m.pad_size
    k.buf[0x14:0x14 + p] = m.pad[:p]
    m.pad_size = (m.pad_size + size) & 0x0F or 16
    size -= m.pad_size
    m.pad[:m.pad_size] = data[size:size + m.pad_size]
    seed = 0x3A if m.type == 2 else 0x38
    off = 0
    while size:
        ksize = min(size + p, 0x0800)
        k.buf[0x14 + p:0x14 + ksize] = data[off:off + ksize - p]
        _sub_158(k, ksize, m.key, seed)
        size -= ksize - p
        off += ksize - p
        p = 0


def bbmac_final(k, m, vkey):
    seed = 0x3A if m.type == 2 else 0x38
    k.buf[0x14:0x14 + 16] = bytes(16)
    k.cmd4(16, seed)
    tmp = _dbl(bytes(k.buf[0x14:0x24]))
    if m.pad_size < 16:
        tmp = _dbl(bytes(tmp))
        m.pad[m.pad_size] = 0x80
        for i in range(m.pad_size + 1, 16):
            m.pad[i] = 0
    for i in range(16):
        m.pad[i] ^= tmp[i]
    k.buf[0x14:0x24] = m.pad
    tmp1 = bytearray(m.key)
    _sub_158(k, 0x10, tmp1, seed)
    for i in range(16):
        tmp1[i] ^= LOC_1CD4[i]
    if m.type == 2:
        raise NotImplementedError('mac_type 2 needs the console fuse id')
    if vkey is not None:
        for i in range(16):
            tmp1[i] ^= vkey[i]
        k.buf[0x14:0x24] = tmp1
        k.cmd4(0x10, seed)
        tmp1 = bytearray(k.buf[0x14:0x24])
    m.key = bytearray(16); m.pad = bytearray(16); m.pad_size = 0
    return bytes(tmp1)


def bbmac_final2(k, m, stored, vkey):
    t = m.type
    tmp = bbmac_final(k, m, vkey)
    if t == 3:
        k.buf[0x14:0x24] = stored
        k.cmd7(0x10, 0x63)
    else:
        k.buf[0:16] = stored
    return bytes(k.buf[0:16]) == tmp


def bbmac_getkey(k, m, stored):
    t = m.type
    tmp = bbmac_final(k, m, None)
    if t == 3:
        k.buf[0x14:0x24] = stored
        k.cmd7(0x10, 0x63)
    else:
        k.buf[0:16] = stored
    k.buf[0x14:0x24] = k.buf[0:16]
    k.cmd7(0x10, 0x3A if t == 2 else 0x38)
    return bytes(tmp[i] ^ k.buf[i] for i in range(16))


class CipherKey:
    def __init__(self, type_, header_key, version_key, seed):
        self.type = type_
        self.seed = seed + 1
        self.key = bytearray(header_key[:16])
        if version_key:
            for i in range(16):
                self.key[i] ^= version_key[i]


def _sub_428(k, data, off, size, ck):
    k.buf[0x14:0x24] = ck.key
    for i in range(16):
        k.buf[0x14 + i] ^= LOC_1CF4[i]
    if ck.type == 2:
        raise NotImplementedError('cipher_type 2 needs the console fuse id')
    k.cmd7(16, 0x39)
    for i in range(16):
        k.buf[i] ^= LOC_1CE4[i]
    tmp2 = bytes(k.buf[0:16])
    if ck.seed == 1:
        tmp1 = bytearray(16)
    else:
        tmp1 = bytearray(tmp2)
        tmp1[12:16] = struct.pack('<I', ck.seed - 1)
    for i in range(0, size, 16):
        k.buf[0x14 + i:0x14 + i + 12] = tmp2[:12]
        k.buf[0x14 + i + 12:0x14 + i + 16] = struct.pack('<I', ck.seed)
        ck.seed += 1
    _sub_1F8(k, size, tmp1, 0x63)
    for i in range(size):
        data[off + i] ^= k.buf[i]


def bbcipher_update(k, ck, data, off=0, size=None):
    size = len(data) - off if size is None else size
    p = 0
    while size > 0:
        d = min(size, 0x0800)
        _sub_428(k, data, off + p, d, ck)
        size -= d
        p += d


class PGD:
    def __init__(self, header, pgd_flag=2):
        k = self.k = Kirk()
        h = bytearray(header)
        self.key_index, self.drm_type = struct.unpack('<II', h[4:12])
        if self.drm_type == 1:
            self.mac_type = 3 if self.key_index > 1 else 1
            self.cipher_type = 1
        else:
            self.mac_type, self.cipher_type = 2, 2

        fkey = DNAS_1A90 if pgd_flag & 2 else (DNAS_1AA0 if pgd_flag & 1 else None)
        if fkey is None:
            raise ValueError('bad pgd_flag')

        m = MacKey(self.mac_type)
        bbmac_update(k, m, h[0x00:0x80])
        if not bbmac_final2(k, m, bytes(h[0x80:0x90]), fkey):
            raise ValueError('MAC_0x80 check failed (wrong pgd_flag?)')

        m = MacKey(self.mac_type)
        bbmac_update(k, m, h[0x00:0x70])
        self.vkey = bbmac_getkey(k, m, bytes(h[0x70:0x80]))

        ck = CipherKey(self.cipher_type, bytes(h[0x10:0x20]), self.vkey, 0)
        bbcipher_update(k, ck, h, 0x30, 0x30)

        self.data_size, self.block_size, self.data_offset = struct.unpack('<III', h[0x44:0x50])
        self.dkey = bytes(h[0x30:0x40])

    def decrypt_block(self, index, raw):
        ck = CipherKey(self.cipher_type, self.dkey, self.vkey,
                       (index * self.block_size) >> 4)
        buf = bytearray(raw)
        bbcipher_update(self.k, ck, buf)
        return bytes(buf)
