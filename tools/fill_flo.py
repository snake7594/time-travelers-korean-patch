# -*- coding: utf-8 -*-
"""Attach the Korean to the extracted chart strings -> ui_json/flo.json."""
import json
import pack_korean as P
from flo_ko import KO

SRC = 'flo_new.json'
OUT = r'D:\psp\타임트레블러즈\ui_json\flo.json'

doc = json.load(open(SRC, encoding='utf-8'))
n = len(doc['entries'])
if len(KO) != n:
    raise SystemExit('%d translations for %d strings' % (len(KO), n))

over = []
for e, ko in zip(doc['entries'], KO):
    e['ko'] = ko
    # a Hangul syllable rides on a kanji, so it costs two bytes like one
    n_bytes = sum(2 if '가' <= ch <= '힣' else
                  len(ch.encode('cp932', 'replace')) for ch in P.full_stops(ko))
    if n_bytes > e['room']:
        over.append((e['id'], e['ja'][:20], ko, e['room']))
json.dump(doc, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('%d strings translated -> %s' % (n, OUT))
for i, ja, ko, room in over[:10]:
    print('   too long %s room %d: %s' % (i, room, ko))
