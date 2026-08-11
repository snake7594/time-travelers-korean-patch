# -*- coding: utf-8 -*-
"""Check the EBOOT patch inside the built ISO."""
import json, sys
import isowalk, pack_korean as P

ISO = sys.argv[1] if len(sys.argv) > 1 else P.DST
gm = json.load(open(P.GLYPH_MAP, encoding='utf-8'))
back = {chr(v): k for k, v in gm.items()}
unpunct = {v: k for k, v in P.PUNCT.items()}

lba = size = None
for path, l, s in isowalk.walk(ISO):
    if path.endswith('/EBOOT.BIN') and 'UPDATE' not in path:
        lba, size = l, s
f = open(ISO, 'rb')
f.seek(lba * 2048)
d = f.read(size)
print('EBOOT.BIN %d bytes, magic %r' % (size, d[:4]))

doc = json.load(open(r'D:\psp\타임트레블러즈\ui_json\eboot.json',
                     encoding='utf-8'))
ok = bad = 0
for e in doc['entries']:
    if not e['ko'].strip():
        continue
    off = int(e['id'].split('@')[1])
    raw = d[off:off + e['room']]
    got = raw.split(b'\x00')[0].decode('cp932', 'replace')
    got = ''.join(back.get(c, unpunct.get(c, c)) for c in got)
    want = P.full_stops(e['ko'])
    if got.replace('．', '.') == want.replace('．', '.'):
        ok += 1
    else:
        bad += 1
        if bad <= 5:
            print('  mismatch %s\n    want %r\n    got  %r'
                  % (e['id'], want[:50], got[:50]))
print('%d strings match in the ISO, %d differ' % (ok, bad))

# nothing outside the string slots may have moved
orig = open(P.EBOOT_DUMP, 'rb').read()
slots = sorted((int(e['id'].split('@')[1]), e['room'])
               for e in doc['entries'] if e['ko'].strip())
diff = []
prev = 0
for off, room in slots:
    if orig[prev:off] != d[prev:off]:
        diff.append(('%d..%d' % (prev, off)))
    prev = off + room
if orig[prev:] != d[prev:]:
    diff.append('%d..end' % prev)
print('bytes changed outside the string slots: %s' % (diff[:3] or 'none'))
