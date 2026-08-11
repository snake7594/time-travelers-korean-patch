# -*- coding: utf-8 -*-
"""Can the chapter-card font actually draw the chapter cards?"""
import json, re, sys, collections
import cpk, dnsfile, xpck, fnt, pack_korean as P

ISO = sys.argv[1] if len(sys.argv) > 1 else P.DST
TAG = re.compile(r'<[^>]{0,24}>')
gm = json.load(open(P.GLYPH_MAP, encoding='utf-8'))

c = cpk.CPK(dnsfile.DNSFile(iso=ISO))
have = {}
for name in ('telop_main.xf', 'staffroll.xf'):
    e = [x for x in c.files if x['name'] == name][0]
    files = {f['name']: f for f in xpck.parse(c.read(e))}
    have[name] = {ch['code'] for ch in fnt.parse(files['FNT.bin']['data'])['large']}
    print('%s: %d glyphs' % (name, len(have[name])))

SOURCES = {'telop_main.xf': ['eboot.json', 'lua.json'],
           'staffroll.xf': ['staffroll.json']}
for font, files in SOURCES.items():
    miss = collections.Counter()
    total = ok = 0
    worst = []
    for f in files:
        for e in json.load(open(r'D:\psp\타임트레블러즈\ui_json\%s' % f,
                                encoding='utf-8'))['entries']:
            ko = TAG.sub('', e.get('ko', ''))
            if not ko.strip():
                continue
            bad = [ch for ch in ko
                   if ch in gm and gm[ch] not in have[font]]
            total += 1
            if bad:
                miss.update(bad)
                worst.append((e['id'], ''.join(sorted(set(bad)))))
            else:
                ok += 1
    print()
    print('%s: %d of %d strings fully drawable' % (font, ok, total))
    if miss:
        print('   missing syllables: %s' % ''.join(sorted(miss)))
        for i, b in worst[:5]:
            print('   %-28s missing %s' % (i, b))

print()
card = '캐스터 편후시미 히나의 경우형사 편루상치 편사기꾼 편고교생 편타임 트래블러 편'
bad = [ch for ch in card if ch != ' ' and gm.get(ch) not in have['telop_main.xf']]
print('chapter cards: %s' % ('all present' if not bad else 'missing ' + ''.join(bad)))
