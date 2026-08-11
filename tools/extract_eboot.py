# -*- coding: utf-8 -*-
"""Build ui_json/eboot.json from the decrypted executable.

PPSSPP dumps the decrypted EBOOT when "Dump decrypted EBOOT.BIN on game
boot" is on; that dump is a plain ELF of exactly the same length as the
encrypted file on the disc, so the strings can be edited in place and the
whole thing dropped back over EBOOT.BIN.

  python extract_eboot.py
"""
import json, sys
import eboot_strings as E
from eboot_ko import KO, UTILITY, SKIP

OUT = r'D:\psp\타임트레블러즈\ui_json\eboot.json'
LO, HI = 2880000, 2960000


def targets(d):
    """[(offset, room, ja)] for every string the game itself draws."""
    out = []
    for o, t in E.scan(d):
        if not LO <= o <= HI:
            continue
        if any(a <= o < b for a, b in UTILITY):
            continue
        if any(s in t for s in SKIP):
            continue
        out.append((o, len(t.encode('cp932')), t))
    return out


def main():
    d = open(E.DUMP, 'rb').read()
    entries, miss = [], []
    for o, room, ja in targets(d):
        ko = KO.get(ja, '')
        if not ko:
            miss.append((o, ja))
        entries.append({'id': 'eboot@%d' % o, 'room': room,
                        'ja': ja, 'ko': ko})
    json.dump({'schema': 'tt1-ui/1', 'source': 'PSP_GAME/SYSDIR/EBOOT.BIN',
               'note': 'engine-drawn system messages; edited in the decrypted ELF',
               'count': len(entries), 'entries': entries},
              open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    done = len(entries) - len(miss)
    print('%d engine strings, %d translated -> %s' % (len(entries), done, OUT))
    for o, t in miss:
        print('   no Korean: %8d  %s' % (o, t.replace('\n', ' | ')[:80]))


if __name__ == '__main__':
    main()
