# -*- coding: utf-8 -*-
"""Full audit of every font against every string the game shows.

A code point being present in the char table is not enough: if its slot was
never redrawn the original kanji is still there, which is how 合 and 山 turned
up in the middle of a chapter card. The test here is differential -- a slot
counts as Korean only when its bitmap differs from the untouched disc.

  python audit_fonts.py [iso]
"""
import json, glob, os, re, struct, sys, collections
import numpy as np
import cpk, dnsfile, xpck, fnt, imgp, pack_korean as P, build_expand2 as B

ISO = sys.argv[1] if len(sys.argv) > 1 else P.DST
ORIG = P.SRC
TAG = re.compile(r'<[^>]{0,24}>')
UI = r'D:\psp\타임트레블러즈\ui_json'
FIX = r'D:\psp\타임트레블러즈\script_fix'
gm = json.load(open(P.GLYPH_MAP, encoding='utf-8'))
back = {v: k for k, v in gm.items()}

# which font draws what, as far as the screens have shown
ROUTE = [('eboot.json', 'telop_main.xf'), ('lua.json', 'telop_main.xf'),
         ('staffroll.json', 'staffroll.xf'),
         ('tip.json', 'ttp_main.xf'), ('tutorial.json', 'ttp_main.xf'),
         ('help.json', 'ttp_main.xf'), ('outline.json', 'ttp_main.xf'),
         ('choice.json', 'nrm_sub.xf'), ('dialogue', 'nrm_sub.xf')]


def nibbles(xi):
    w, _ = struct.unpack('<HH', xi[0x10:0x14])
    a1, s1, a2, s2 = struct.unpack('<IIII', xi[0x40:0x50])
    tiles = imgp.l5_decompress(xi[0x58 + a1:0x58 + a1 + s1])
    pix = imgp.l5_decompress(xi[0x58 + a2:0x58 + a2 + s2])
    idx = struct.unpack('<%dH' % (len(tiles) // 2), tiles)
    sw = bytearray()
    for i in idx:
        sw += bytes(32) if i == 0xFFFF else pix[i * 32:i * 32 + 32]
    wb = w // 2
    H = len(sw) // wb
    lin = bytearray(len(sw))
    si = 0
    for by in range(H // 8):
        for bx in range(wb // 16):
            for y in range(8):
                d = (by * 8 + y) * wb + bx * 16
                lin[d:d + 16] = sw[si:si + 16]
                si += 16
    a = np.frombuffer(bytes(lin), np.uint8)
    n = np.empty(a.size * 2, np.uint8)
    n[0::2] = a & 0xF
    n[1::2] = a >> 4
    return n.reshape(H, w)


def font_files(iso):
    out = {}
    for src in (cpk.CPK(dnsfile.DNSFile(iso=iso)),
                cpk.CPK(iso, base=P.CPK_LBA * P.SEC)):
        for e in (x for x in src.files if x['name'].endswith('.xf')):
            if e['name'] in out or e['name'] == 'dbg.xf':
                continue
            try:
                files = {f['name']: f for f in xpck.parse(src.read(e))}
                out[e['name']] = (files, fnt.parse(files['FNT.bin']['data']))
            except Exception:
                pass
    return out


def korean_glyphs(new, old):
    """Syllables whose slot really changed, per font."""
    out = {}
    for name, (nf, nm) in new.items():
        if name not in old:
            continue
        of, om = old[name]
        a = {i: nibbles(nf['%03d.xi' % i]['data']) for i in range(nm['textures'])}
        b = {i: nibbles(of['%03d.xi' % i]['data']) for i in range(om['textures'])}
        got = set()
        for c in nm['large']:
            syl = back.get(c['code'])
            if syl is None:
                continue
            _, _, w, h = nm['sizes'][c['size']]
            if not w or not h:
                continue
            na = a[c['tex']][c['y']:c['y'] + h, c['x']:c['x'] + w]
            # the same place on the untouched disc, whatever glyph sat there
            ob = b[c['tex']][c['y']:c['y'] + h, c['x']:c['x'] + w]
            if na.any() and not np.array_equal(na, ob):
                got.add(syl)
        out[name] = got
    return out


def texts():
    """(source, id, korean) for everything the player can read."""
    for p in sorted(glob.glob(os.path.join(UI, '*.json'))):
        b = os.path.basename(p)
        if b == 'manifest.json' or b.startswith('_'):
            continue
        for e in json.load(open(p, encoding='utf-8'))['entries']:
            if e.get('ko', '').strip():
                yield b, e['id'], e['ko']
    for p in sorted(glob.glob(os.path.join(FIX, '*.json'))):
        b = os.path.basename(p)
        if b == 'manifest.json' or b.startswith('_'):
            continue
        for e in json.load(open(p, encoding='utf-8'))['entries']:
            if e.get('ko', '').strip():
                yield 'dialogue', e['id'], e['ko']


def main():
    new, old = font_files(ISO), font_files(ORIG)
    drawn = korean_glyphs(new, old)
    print('Korean glyphs per font:')
    for n in sorted(drawn):
        print('   %-16s %4d' % (n, len(drawn[n])))

    route = dict(ROUTE)
    per = collections.defaultdict(lambda: [0, 0, collections.Counter()])
    bad = collections.defaultdict(list)
    for src, i, ko in texts():
        font = route.get(src)
        if font is None or font not in drawn:
            continue
        need = {ch for ch in TAG.sub('', ko) if ch in gm}
        miss = need - drawn[font]
        per[src][0] += 1
        if miss:
            per[src][1] += 1
            per[src][2].update(miss)
            if len(bad[src]) < 4:
                bad[src].append((i, ''.join(sorted(miss))))
    print()
    print('%-16s %-16s %8s %8s' % ('source', 'font', 'strings', 'broken'))
    total = 0
    for src, font in ROUTE:
        if src not in per:
            continue
        n, b, miss = per[src]
        total += b
        print('  %-16s %-16s %6d %8d %s'
              % (src, font, n, b, ''.join(sorted(miss))[:40]))
        for i, m in bad[src]:
            print('      %-28s %s' % (i, m))
    print()
    print('strings that would show a missing-glyph box: %d' % total)


if __name__ == '__main__':
    main()
