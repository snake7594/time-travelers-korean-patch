# -*- coding: utf-8 -*-
"""Dialogue-expansion test ISO.

Lengthens one line in psp/txt/event/pck/A01.pck by appending a run of
full-width digits, so it is obvious on screen how many extra characters
survive before the engine wraps, clips or breaks.

Strings inside a blob are addressed by ordinal (blob header field [4] is the
string count, [3] the total string bytes), so changing a length needs no
internal offset fixups -- only the blob header, the .pck blob table and the
CPK TOC row.
"""
import os, shutil, struct, sys, zlib

import cpk, dnsfile, crilayla, pgd

SRC = r'D:\psp\타임트레블러즈\Time Travelers.iso'
DST = r'D:\psp\타임트레블러즈\Time Travelers (expand test).iso'
DNS_LBA = 285712
SEC = 2048
TARGET = 'A01.pck'
SUFFIX = ('０１２３４５６７８９' * 3).encode('shift_jis')   # 30 full-width chars


def parse_pck(d):
    n = struct.unpack('<I', d[:4])[0]
    recs = [struct.unpack('<III', d[4 + i * 12:16 + i * 12]) for i in range(n)]
    return n, recs


def rebuild_blob(b, pick):
    """Append SUFFIX to the pick-th string of this blob."""
    H = list(struct.unpack('<5I', b[:20]))
    base = H[2] + 4
    head, tail = b[:base], b[base:]
    strs, i = [], 0
    while i < len(tail) and len(strs) < H[4]:
        j = tail.find(b'\x00', i)
        if j < 0:
            break
        strs.append(tail[i:j])
        i = j + 1
    assert len(strs) == H[4], (len(strs), H[4])
    strs[pick] = strs[pick] + SUFFIX
    blob_strings = b''.join(s + b'\x00' for s in strs)
    H[3] = len(blob_strings)
    pad = (-len(blob_strings)) % 4
    new = bytearray(head) + blob_strings + bytes(pad)
    new[:20] = struct.pack('<5I', *H)
    return bytes(new)


def main():
    d = dnsfile.DNSFile()
    c = cpk.CPK(d)
    ent = [e for e in c.files if e['name'] == TARGET][0]
    files = sorted(c.files, key=lambda e: e['offset'])
    nxt = min((e['offset'] for e in files if e['offset'] > ent['offset']))
    slot = nxt - ent['offset']
    print('%s: stored %d, extract %d, slot %d bytes' % (TARGET, ent['size'], ent['extract'], slot))

    raw = c.read(ent)
    n, recs = parse_pck(raw)

    # pick the blob/string holding a long quoted line
    pick = None
    for bi, (h, off, sz) in enumerate(recs):
        b = raw[off:off + sz]
        if len(b) < 20:
            continue
        H = struct.unpack('<5I', b[:20])
        if H[2] + 4 >= len(b) or H[4] == 0 or H[4] > 500:
            continue
        base = H[2] + 4
        tail = b[base:]
        i, k = 0, 0
        while i < len(tail) and k < H[4]:
            j = tail.find(b'\x00', i)
            if j < 0:
                break
            s = tail[i:j]
            if b'\x81\x75' in s and 40 <= len(s) <= 120:
                pick = (bi, k, len(s))
                break
            i = j + 1
            k += 1
        if pick:
            break
    assert pick, 'no suitable line found'
    bi, si, oldlen = pick
    print('target: blob[%d] string #%d, %d bytes -> %d bytes (+%d)'
          % (bi, si, oldlen, oldlen + len(SUFFIX), len(SUFFIX)))

    # rebuild the blob, then the .pck
    blobs = [bytearray(raw[o:o + s]) for _, o, s in recs]
    blobs[bi] = bytearray(rebuild_blob(bytes(blobs[bi]), si))
    hdr = bytearray(struct.pack('<I', n))
    off = 4 + n * 12
    body = bytearray()
    for i, (h, _, _) in enumerate(recs):
        hdr += struct.pack('<III', h, off + len(body), len(blobs[i]))
        body += blobs[i]
    newpck = bytes(hdr) + bytes(body)
    print('.pck: %d -> %d bytes' % (len(raw), len(newpck)))

    comp = crilayla.compress(newpck, effort=256)
    assert cpk.crilayla(comp) == newpck, 'compressor round-trip failed'
    print('compressed: %d bytes (slot %d)' % (len(comp), slot))
    assert len(comp) <= slot, 'does not fit the slot'
    comp += bytes(slot - len(comp) if len(comp) < ent['size'] else 0)

    # ---- collect edits in DNS decrypted-stream space ----
    edits = [(ent['offset'], comp)]

    toc_off = c.header['TocOffset']
    toc = cpk.read_chunk(d, toc_off, b'TOC ')
    idx = [i for i, r in enumerate(toc.rows)
           if r['FileName'] == TARGET and r['DirName'] == ent['dir']][0]
    row = toc_off + 16 + 8 + toc.rows_off + idx * toc.row_len
    edits.append((row + 8, struct.pack('>I', len(comp))))
    edits.append((row + 12, struct.pack('>I', len(newpck))))
    print('TOC row %d: FileSize %d -> %d, ExtractSize %d -> %d'
          % (idx, ent['size'], len(comp), ent['extract'], len(newpck)))

    # ---- apply to a copy of the ISO, re-encrypting whole PGD blocks ----
    if not os.path.exists(DST):
        print('copying ISO ...')
        shutil.copyfile(SRC, DST)
    base = DNS_LBA * SEC
    f = open(DST, 'r+b')
    f.seek(base)
    p = pgd.PGD(f.read(0x90), 2)
    bs = p.block_size
    touched = {}
    for off, blob in edits:
        for k in range(off // bs, (off + len(blob) - 1) // bs + 1):
            if k not in touched:
                f.seek(base + p.data_offset + k * bs)
                touched[k] = bytearray(p.decrypt_block(k, f.read(bs)))
        for i, byte in enumerate(blob):
            k, o = divmod(off + i, bs)
            touched[k][o] = byte
    for k, buf in touched.items():
        f.seek(base + p.data_offset + k * bs)
        f.write(p.decrypt_block(k, bytes(buf)))     # cipher is symmetric
    f.close()
    print('patched %d PGD blocks -> %s' % (len(touched), DST))

    # ---- verify by reading the new ISO back ----
    d2 = dnsfile.DNSFile(iso=DST)
    c2 = cpk.CPK(d2)
    e2 = [e for e in c2.files if e['name'] == TARGET][0]
    back = c2.read(e2)
    print('verify: TOC now %d/%d, decompressed %d, matches rebuild: %s'
          % (e2['size'], e2['extract'], len(back), back == newpck))


if __name__ == '__main__':
    main()
