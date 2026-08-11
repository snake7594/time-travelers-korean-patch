# -*- coding: utf-8 -*-
"""Every Japanese string still in the game data, and whether it will now be
drawn as garbage.

Any kanji the translation borrowed as a Hangul slot draws Hangul wherever it
appears -- so Japanese left untranslated does not stay Japanese, it turns
into nonsense syllables. This lists what is left and how bad each one is.
"""
import collections, json, re, struct, sys
import cpk, dnsfile, pack_korean as P, build_expand2 as B

ISO = sys.argv[1] if len(sys.argv) > 1 else P.DST
gm = json.load(open(P.GLYPH_MAP, encoding='utf-8'))
borrowed = {v for v in gm.values()}
# Korean rides on kanji code points, so a patched line still reads as kanji.
# Kana is what tells real Japanese apart from it.
JP = re.compile(r'[぀-ヿ]')
CLEAN = re.compile(r'^[　-ヿ一-鿿！-｠'
                   r'‐-‟… -~\r\n\t\[\]/]+$')


def strings_of(d, name):
    """Best-effort string extraction for whatever kind of file this is."""
    if name.endswith('.pck'):
        n = struct.unpack('<I', d[:4])[0]
        for bi in range(n):
            off, sz = struct.unpack('<II', d[8 + bi * 12:16 + bi * 12])
            b = d[off:off + sz]
            if len(b) < 20:
                continue
            g = B.split_strings(b)
            if g:
                for s in g[2]:
                    yield s
        return
    if name.endswith('.cfg.bin'):
        g = P.split_cfg(d)
        if g:
            for s in g[2]:
                yield s
        return
    for s in d.split(b'\x00'):
        if 3 <= len(s) <= 400:
            yield s


def main():
    c = cpk.CPK(dnsfile.DNSFile(iso=ISO))
    per = collections.Counter()
    sample = collections.defaultdict(list)
    for e in c.files:
        if e['extract'] > 4 << 20:
            continue
        try:
            d = c.read(e)
        except Exception:
            continue
        for s in strings_of(d, e['name']):
            try:
                t = s.decode('cp932')
            except UnicodeDecodeError:
                continue
            if not JP.search(t) or not CLEAN.match(t):
                continue
            hit = [ch for ch in t if ord(ch) in borrowed]
            key = '%s/%s' % (e['dir'], e['name'])
            per[key] += 1
            if hit and len(sample[key]) < 3:
                sample[key].append((t[:60], ''.join(hit[:12])))
    print('files still holding Japanese, worst first:')
    for k, n in per.most_common(30):
        mark = ' <- draws as Hangul' if sample[k] else ''
        print('  %-46s %5d%s' % (k, n, mark))
        for t, h in sample[k][:2]:
            print('        %s' % t.replace('\n', ' '))
            print('        borrowed kanji in it: %s' % h)


if __name__ == '__main__':
    main()
