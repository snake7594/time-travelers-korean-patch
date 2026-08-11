# -*- coding: utf-8 -*-
"""Count sentence-end marks as they actually sit in the built ISO."""
import collections, struct, sys
import cpk, dnsfile, pack_korean as P, build_expand2 as B

ISO = sys.argv[1] if len(sys.argv) > 1 else P.DST
MARKS = {'。': 'ideographic (Japanese)', '．': 'full-width (Korean)',
         '.': 'ASCII', '、': 'ideographic comma'}
PAT = {ch: ch.encode('cp932') for ch in MARKS}

c = cpk.CPK(dnsfile.DNSFile(iso=ISO))
n = collections.Counter()

for e in (x for x in c.files if x['dir'] == 'psp/txt/event/pck'):
    raw = c.read(e)
    cnt = struct.unpack('<I', raw[:4])[0]
    for bi in range(cnt):
        off, sz = struct.unpack('<II', raw[8 + bi * 12:16 + bi * 12])
        b = raw[off:off + sz]
        if len(b) < 20:
            continue
        g = B.split_strings(b)
        if not g:
            continue
        for s in g[2]:
            for ch, p in PAT.items():
                n['dialogue ' + ch] += s.count(p)

for e in (x for x in c.files if x['dir'] in P.CFG_DIRS):
    got = P.split_cfg(c.read(e))
    if not got:
        continue
    for s in got[2]:
        for ch, p in PAT.items():
            n['window ' + ch] += s.count(p)

for e in (x for x in c.files if x['name'] == 'tt1.scn'):
    d = c.read(e)
    base = struct.unpack('<I', d[0x30:0x34])[0]
    for ch, p in PAT.items():
        n['choice ' + ch] += d[base:].count(p)

for k in sorted(n):
    if n[k]:
        print('  %-14s %r  %s' % (k.rsplit(' ', 1)[0], k[-1], n[k]))
