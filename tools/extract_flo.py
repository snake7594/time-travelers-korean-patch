# -*- coding: utf-8 -*-
"""Pull the time-travel chart text out of psp/script/tt1.flo.

The strings sit inline in fixed-size records, NUL terminated and padded, so
they can be written back in place as long as each stays within the length it
had. Nothing addresses them by offset from outside.

  python extract_flo.py [out.json]
"""
import json, re, sys, collections
import cpk, dnsfile

NAME = 'tt1.flo'
JP = re.compile(r'[぀-ヿ]')
CLEAN = re.compile(r'^[　-ヿ一-鿿！-｠‐-‟… -~\r\n\[\]/]+$')


MARK = b'\xff\xff\xff\xff'


def spans(d, jp_only=True):
    """[(start, end, text)] for every text field in the file.

    A field is introduced by four 0xFF bytes and runs, CP932, to its NUL. It
    sits inline in a fixed-size record, so a replacement has to stay within
    the length it already has -- but nothing outside points at it.
    """
    out, i = [], 0
    while True:
        i = d.find(MARK, i)
        if i < 0:
            break
        a = i + 4
        b = d.find(b'\x00', a)
        i = a
        if b < 0 or not 1 <= b - a <= 300:
            continue
        try:
            t = d[a:b].decode('cp932')
        except UnicodeDecodeError:
            continue
        if not CLEAN.match(t):
            continue
        if jp_only and not JP.search(t):
            continue
        out.append((a, b, t))
    return out


def main(path):
    c = cpk.CPK(dnsfile.DNSFile())
    e = [x for x in c.files if x['name'] == NAME][0]
    d = c.read(e)
    got = spans(d)
    seen = collections.OrderedDict()
    room = {}
    for a, b, t in got:
        seen.setdefault(t, 0)
        seen[t] += 1
        room[t] = min(room.get(t, 10 ** 9), b - a)
    entries = [{'id': 'flo#%d' % i, 'uses': n, 'room': room[t],
                'ja': t, 'ko': ''}
               for i, (t, n) in enumerate(seen.items())]
    json.dump({'schema': 'tt1-ui/1', 'source': 'psp/script/tt1.flo',
               'note': 'time-travel chart nodes and telops; written back in place',
               'count': len(entries), 'entries': entries},
              open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('%d occurrences, %d distinct, %d chars -> %s'
          % (len(got), len(entries), sum(len(t) for t in seen), path))
    for e2 in entries[:12]:
        print('   x%-3d %3dB  %s' % (e2['uses'], e2['room'], e2['ja'][:60]))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1
         else r'D:\psp\타임트레블러즈\ui_json\flo.json')
