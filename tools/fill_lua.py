# -*- coding: utf-8 -*-
"""Attach the Korean to the extracted Lua literals -> ui_json/lua.json."""
import json, sys
from lua_ko import KO, BR

SRC = 'lua_new.json'
OUT = r'D:\psp\타임트레블러즈\ui_json\lua.json'
MARKS = ('\\\\n', '\\n')          # 3-char and 2-char spellings in the source


def mark_of(t):
    for m in MARKS:
        if m in t:
            return m
    return None


def main():
    doc = json.load(open(SRC, encoding='utf-8'))
    hit = miss = 0
    seen_miss = []
    for e in doc['entries']:
        if not e['drawn']:
            e['ko'] = ''
            continue
        m = mark_of(e['ja'])
        key = e['ja'].replace(m, BR) if m else e['ja']
        ko = KO.get(key)
        if ko is None:
            miss += 1
            if key not in seen_miss:
                seen_miss.append(key)
            continue
        e['ko'] = ko.replace(BR, m) if m else ko
        hit += 1
    doc['count'] = len(doc['entries'])
    json.dump(doc, open(OUT, 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print('%d translated, %d left in Japanese -> %s' % (hit, miss, OUT))
    for k in seen_miss:
        print('   untranslated: %s' % k.replace(BR, ' / ')[:90])


if __name__ == '__main__':
    main()
