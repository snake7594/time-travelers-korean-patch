# -*- coding: utf-8 -*-
"""Write a marker into a disc's PARAM.SFO title.

Diagnostic builds are indistinguishable once they are on the memory stick, so
each one says which it is in the name the console lists it under. Only the
TITLE string is touched, inside the room the field already has, so nothing
moves and DISC_ID and the rest are left exactly as they were.

  python sfotag.py "Time Travelers (KR) C-lua.iso" "[C-lua]"
  python sfotag.py <iso>                 -- just print what is there now
"""
import struct
import sys

MAGIC = b'\x00PSF'
FMT_UTF8 = 0x0204


SECTOR = 2048


def find_sfo(f):
    """Offset of the game's PARAM.SFO, from its ISO9660 directory record.

    Scanning for the magic does not work here: the file sits past the 557 MB
    mark, well beyond where anything else in the image lives.
    """
    f.seek(0)
    head = f.read(1 << 20)
    j = head.find(b'PARAM.SFO')
    while j >= 0:
        rec = j - 33
        if rec > 0 and head[rec + 32] == 9:
            lba = struct.unpack('<I', head[rec + 2:rec + 6])[0]
            at = lba * SECTOR
            f.seek(at)
            if f.read(4) == MAGIC:
                return at
        j = head.find(b'PARAM.SFO', j + 1)
    raise SystemExit('PARAM.SFO 를 찾지 못했습니다')


def entries(f, base):
    """[(key, (fmt, length, room, data_offset))] for the SFO at `base`."""
    f.seek(base)
    head = f.read(0x14)
    if head[:4] != MAGIC:
        raise ValueError('not an SFO')
    key_at, data_at, count = struct.unpack('<III', head[8:0x14])
    if not 0 < count < 256:
        raise ValueError('entry count %d' % count)
    f.seek(base + 0x14)
    raw = f.read(count * 16)
    f.seek(base + key_at)
    keys = f.read(data_at - key_at)
    out = []
    for i in range(count):
        ko, fmt, ln, room, off = struct.unpack('<HHIII', raw[i * 16:i * 16 + 16])
        name = keys[ko:keys.find(b'\x00', ko)].decode('ascii', 'replace')
        out.append((name, (fmt, ln, room, base + data_at + off)))
    return out


def show(path):
    with open(path, 'rb') as f:
        base = find_sfo(f)
        print('PARAM.SFO @ %d (0x%X)' % (base, base))
        for name, (fmt, ln, room, off) in entries(f, base):
            f.seek(off)
            raw = f.read(ln)
            val = (raw.rstrip(b'\x00').decode('utf-8', 'replace')
                   if fmt == FMT_UTF8 else struct.unpack('<I', raw[:4])[0])
            print('  %-16s fmt %#06x  %3d/%3d  %r' % (name, fmt, ln, room, val))


def tag(path, marker):
    with open(path, 'r+b') as f:
        base = find_sfo(f)
        found = dict(entries(f, base))
        if 'TITLE' not in found:
            raise SystemExit('TITLE 항목이 없습니다')
        fmt, ln, room, off = found['TITLE']
        f.seek(off)
        old = f.read(ln).rstrip(b'\x00').decode('utf-8', 'replace')
        stem = old.split('  ')[0]
        new = ('%s  %s' % (stem, marker)).encode('utf-8') + b'\x00'
        if len(new) > room:
            raise SystemExit('제목이 %d 바이트로 %d 바이트 칸을 넘습니다'
                             % (len(new), room))
        f.seek(off)
        f.write(new + b'\x00' * (room - len(new)))
        for i, (name, _) in enumerate(entries(f, base)):
            if name == 'TITLE':
                # entry: key_offset u16 | data_fmt u16 | len u32 | room u32 | off u32
                f.seek(base + 0x14 + i * 16 + 2)
                f.write(struct.pack('<HII', fmt, len(new), room))
                break
        print('%s\n  %r -> %r' % (path, old, new.rstrip(b'\x00').decode('utf-8')))


if __name__ == '__main__':
    if len(sys.argv) == 2:
        show(sys.argv[1])
    else:
        tag(sys.argv[1], sys.argv[2])
