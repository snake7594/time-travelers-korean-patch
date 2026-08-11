# -*- coding: utf-8 -*-
"""Check the built ISO: window text exact, dialogue periods full-width."""
import json, collections
import cpk, dnsfile, pack_korean as P, build_expand2 as B

gm = json.load(open(P.GLYPH_MAP, encoding='utf-8'))
P.SYLLABLES[:] = sorted(gm)
ui = P.load_ui()
d = dnsfile.DNSFile(iso=P.DST)
c = cpk.CPK(d)

stat = collections.Counter()
for e in sorted((x for x in c.files if x['dir'] in P.CFG_DIRS),
                key=lambda x: x['name']):
    got = P.split_cfg(c.read(e))
    if not got:
        continue
    _, _, strs = got
    for i, s in enumerate(strs):
        k = '%s#%d' % (e['name'], i)
        if k not in ui:
            continue
        ja, ko = ui[k]
        want = P.recode(P.normalize(ja, ko), gm)
        s = s.lstrip(b'\xff')
        group = e['dir'].rsplit('/', 1)[-1]
        if s == want:
            stat[group + ' exact'] += 1
        elif want.startswith(s):
            stat[group + ' TRIMMED'] += 1
        else:
            stat[group + ' DIFFERENT'] += 1
for k in sorted(stat):
    print('  %-22s %d' % (k, stat[k]))

# dialogue: is the ASCII period gone?
half = full = 0
for e in (x for x in c.files if x['dir'] == 'psp/txt/event/pck'):
    raw = c.read(e)
    n = int.from_bytes(raw[:4], 'little')
    for bi in range(n):
        off, sz = int.from_bytes(raw[8 + bi * 12:12 + bi * 12], 'little'), \
                  int.from_bytes(raw[12 + bi * 12:16 + bi * 12], 'little')
        b = raw[off:off + sz]
        if len(b) < 20:
            continue
        g = B.split_strings(b)
        if not g:
            continue
        for s in g[2]:
            half += s.count(b'.')
            full += s.count('．'.encode('cp932'))
print()
print('dialogue periods in the ISO: half-width %d, full-width %d' % (half, full))
