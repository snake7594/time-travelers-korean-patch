# -*- coding: utf-8 -*-
"""Work out a punctuation substitution every dialogue font can render.

The translation uses half-width , ( ) ! ' where the Japanese script used the
full-width forms. Some of the three fonts only carry the full-width ones, so
those characters come out as the engine's missing-glyph box.
"""
import json, glob, os, re, collections
import dnsfile, pack_korean as P

CANDIDATES = {
    ',': '，、',   '.': '．。',   '!': '！',    '?': '？',
    '(': '（',    ')': '）',    "'": '’‘',   '"': '”“',
    '‘': '『「',  '’': '』」',  '“': '『「',  '”': '』」',
    ':': '：',    ';': '；',    '~': '～〜',  '-': '－ー',
    '%': '％',    '/': '／',    '&': '＆',    '+': '＋',
    '＜': '〈＜', '＞': '〉＞', '【': '［（', '】': '］）',
    '☆': '★○',  '★': '☆○',  '￡': '＄￥', '·': '・',
    '…': '…・',  '—': '―－',  '–': '―－',
}


def main():
    d = dnsfile.DNSFile()
    fonts = P.load_fonts(d)
    have = [{c['code'] for c in F['meta']['large']} for F in fonts.values()]
    everywhere = set.intersection(*have)
    gm = json.load(open(P.GLYPH_MAP, encoding='utf-8'))
    TAG = re.compile(r'<[^>]{0,20}>')

    used = collections.Counter()
    in_source = set()
    for dd in (r'D:\psp\타임트레블러즈\ui_json', r'D:\psp\타임트레블러즈\script_fix'):
        for p in sorted(glob.glob(os.path.join(dd, '*.json'))):
            b = os.path.basename(p)
            if b == 'manifest.json' or b.startswith('_'):
                continue
            for e in json.load(open(p, encoding='utf-8'))['entries']:
                ko = TAG.sub('', e.get('ko', '')).replace('\\n', '')
                for ch in ko:
                    if ch not in gm:
                        used[ch] += 1

    table, unresolved = {}, []
    for ch, n in used.most_common():
        if ord(ch) in everywhere:
            continue
        for alt in CANDIDATES.get(ch, ''):
            if ord(alt) in everywhere:
                try:
                    alt.encode('cp932')
                except UnicodeEncodeError:
                    continue
                table[ch] = alt
                break
        else:
            # If the Japanese used it too, the original had the same gap; only
            # characters the translation introduced are ours to fix.
            if ch not in in_source:
                unresolved.append((ch, n))

    print('replacements (%d):' % len(table))
    for ch, alt in sorted(table.items(), key=lambda kv: -used[kv[0]]):
        print('   %r U+%04X -> %r U+%04X   %d uses' % (ch, ord(ch), alt, ord(alt), used[ch]))
    if unresolved:
        print()
        print('introduced by the translation, no substitute (%d):' % len(unresolved))
        for ch, n in unresolved[:20]:
            print('   %r U+%04X  %d uses' % (ch, ord(ch), n))
    json.dump({k: v for k, v in table.items()},
              open(r'D:\psp\타임트레블러즈\script_json\_punct_map.json', 'w',
                   encoding='utf-8'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
