# -*- coding: utf-8 -*-
"""Check the .scn patch: every table still starts where the header says,
every string still sits at its own offset, and the text is Korean."""
import json, struct, sys
import cpk, dnsfile, pack_korean as P

ISO = sys.argv[1] if len(sys.argv) > 1 else P.DST
gm = json.load(open(P.GLYPH_MAP, encoding='utf-8'))
back = {chr(v): k for k, v in gm.items()}

src = cpk.CPK(dnsfile.DNSFile())
dst = cpk.CPK(dnsfile.DNSFile(iso=ISO))
name = 'tt1.scn'
a = src.read([x for x in src.files if x['name'] == name][0])
b = dst.read([x for x in dst.files if x['name'] == name][0])
ta = [struct.unpack('<I', a[o:o + 4])[0] for o in P.SCN_TABLES] + [len(a)]
tb = [struct.unpack('<I', b[o:o + 4])[0] for o in P.SCN_TABLES] + [len(b)]
print('table starts  original %s  patched %s' % (ta[:3], tb[:3]))
print('file size     original %d  patched %d' % (len(a), len(b)))

def slots(d, lo, hi):
    out, p = [], lo
    for s in d[lo:hi].split(b'\x00')[:-1]:
        out.append((p, s))
        p += len(s) + 1
    return out

def dec(x):
    t = x.decode('cp932', 'replace')
    return ''.join(back.get(c, c) for c in t)

moved = ko = jp = 0
for k in range(3):
    sa = slots(a, ta[k], ta[k + 1])
    sb = slots(b, tb[k], tb[k + 1])
    print('  table %d: %d -> %d strings' % (k + 1, len(sa), len(sb)))
    for (oa, xa), (ob, xb) in zip(sa, sb):
        if oa != ob or len(xa) != len(xb):
            moved += 1
        t = dec(xb)
        if any('가' <= c <= '힣' for c in t):
            ko += 1
        elif any('぀' <= c <= 'ヿ' for c in t):
            jp += 1
print('strings that moved or changed length: %d' % moved)
print('Korean %d, still Japanese %d' % (ko, jp))

print()
print('first table, around the choice that was wrong:')
for o, s in slots(b, tb[0], tb[1])[122:127]:
    print('   @%d  %s' % (o, dec(s)))
print('table 2 starts with: %s' % dec(slots(b, tb[1], tb[2])[0][1]))
print('table 3 starts with: %s' % dec(slots(b, tb[2], tb[3])[0][1])[:60])
