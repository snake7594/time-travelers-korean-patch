# -*- coding: utf-8 -*-
"""Check the Lua patch in the built ISO."""
import json, re
import cpk, dnsfile, extract_lua as X, pack_korean as P

gm = json.load(open(P.GLYPH_MAP, encoding='utf-8'))
P.SYLLABLES[:] = sorted(gm)
back = {chr(v): k for k, v in gm.items()}
ko = {e['id']: e['ko'] for e in
      json.load(open(r'D:\psp\타임트레블러즈\ui_json\lua.json',
                     encoding='utf-8'))['entries'] if e.get('ko', '').strip()}

src = cpk.CPK(dnsfile.DNSFile())
dst = cpk.CPK(dnsfile.DNSFile(iso=P.DST))
by_name = {e['name']: e for e in dst.files}

exact = diff = 0
asset_changed = []
for e in sorted((x for x in src.files if x['name'].endswith('.lua')),
                key=lambda x: x['name']):
    want = {}
    for form, a, b, t in X.strings(src.read(e)):
        k = '%s@%d' % (e['name'], a)
        if k in ko:
            want[k] = ko[k]
    if not want:
        continue
    got = dst.read(by_name[e['name']])
    # every literal in the patched file, decoded back through the glyph map
    seen = {}
    for form, a, b, t in X.strings(got):
        seen.setdefault(''.join(back.get(c, c) for c in t), 0)
        seen[''.join(back.get(c, c) for c in t)] += 1
    for k, v in want.items():
        target = P.full_stops(v)
        for a, bch in P.PUNCT.items():
            target = target.replace(a, bch)
        if target in seen:
            exact += 1
        else:
            diff += 1
            if diff <= 6:
                print('  missing: %-28s %s' % (k, v[:40]))
    # asset names must be byte-identical
    for pat in (b'Chr_SetMotion', b'Chr_SetImgMotion', b'Anm_SetByName'):
        if src.read(e).count(pat) != got.count(pat):
            asset_changed.append(e['name'])

print('%d Korean literals found in the ISO, %d not found' % (exact, diff))
print('files whose asset-name calls changed: %s' % (asset_changed or 'none'))

# the source must still parse as far as balanced string.char( ... ) goes
bad = []
for e in sorted((x for x in dst.files if x['name'].endswith('.lua')),
                key=lambda x: x['name']):
    d = dst.read(e)
    if d.count(b'string.char(') != d.count(b'0x') and False:
        pass
    for m in re.finditer(rb'string\.char\(([^)]*)\)', d):
        body = m.group(1)
        if body and not re.fullmatch(rb'\s*(?:0x[0-9A-Fa-f]{1,2}\s*,\s*)*'
                                     rb'0x[0-9A-Fa-f]{1,2}\s*', body):
            bad.append((e['name'], body[:40]))
            break
print('malformed string.char() calls: %s' % (bad[:5] or 'none'))
