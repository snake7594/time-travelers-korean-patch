# -*- coding: utf-8 -*-
"""Produce a proof-reading pass over the existing translation.

The first manifest told the translator the engine does not wrap and that it
should insert \\n itself within 30 characters a line. That was wrong -- the
engine wraps at spaces -- and the pressure it created is what dropped spaces
and glued words together. This rebuilds the JSON with the rule corrected,
mechanically undoing the unambiguous cases first.

  python make_fixjson.py <outdir>
"""
import json, glob, os, re, sys, collections

SRC = r'D:\psp\타임트레블러즈\script_json'
NL = '\\n'
TAG = re.compile(r'</?[A-Za-z][A-Za-z0-9]*>')

RULES = {
    "task": "Fix Korean spacing (띄어쓰기) in ko. Do not retranslate: keep the "
            "wording, only repair spacing and line breaks.",
    "wrapping": "The engine wraps automatically at spaces. Line breaks are NOT "
                "needed to fit the box.",
    "line_break": "\\n (backslash + n) is a hard break. Keep only the ones the "
                  "ja source has, in the same places. Do not add new ones.",
    "spacing": "Never drop a space to make a line shorter. Natural Korean "
               "spacing takes priority over line length.",
    "line_length": "About 30 full-width characters fit on a line; treat it as "
                   "advisory, not a limit.",
    "keep": "Leave tags (<B>, <W15>, <TIP...>, </TIP>), the [base/key] "
            "brackets inside TIP tags, a leading ＊, and 「」『』 speech "
            "brackets exactly as they are.",
    "flags": {
        "added_break": "ko had a line break the source does not have; it was "
                       "replaced with a space automatically -- check the result "
                       "reads naturally.",
        "extra_break": "ko has more breaks than the source; decide which to drop.",
        "glued_break": "a break sits between two words with no space either "
                       "side -- likely a swallowed space.",
        "long_run": "12+ Hangul syllables with no space; almost certainly a "
                    "missing space.",
    },
}


def main(out):
    os.makedirs(out, exist_ok=True)
    stats = collections.Counter()
    files, total = [], 0

    for p in sorted(glob.glob(os.path.join(SRC, '*.json'))):
        b = os.path.basename(p)
        if b == 'manifest.json' or b.startswith('_'):
            continue
        doc = json.load(open(p, encoding='utf-8'))
        entries = []
        for e in doc['entries']:
            ja, ko = e['ja'], e.get('ko', '')
            if not ko:
                continue
            flags = []
            a, k = ja.count(NL), ko.count(NL)

            if a == 0 and k > 0:
                # unambiguous: every break here was invented, put the space back
                ko = re.sub(r' *' + re.escape(NL) + r' *', ' ', ko).strip()
                flags.append('added_break')
                stats['auto-fixed breaks'] += 1
            elif k > a:
                flags.append('extra_break')
                stats['needs manual break decision'] += 1

            if NL in ko:
                for m in re.finditer(re.escape(NL), ko):
                    i, j = m.start(), m.end()
                    if (i and ko[i-1] not in ' 　') and (j < len(ko) and ko[j] not in ' 　'):
                        flags.append('glued_break')
                        stats['glued break'] += 1
                        break

            plain = TAG.sub('', ko).replace(NL, ' ')
            if max((len(x) for x in re.findall(r'[가-힣]+', plain)), default=0) >= 12:
                flags.append('long_run')
                stats['long unbroken run'] += 1

            item = {"id": e['id'], "ja": ja, "ko": ko}
            if flags:
                item["flags"] = flags
                stats['entries flagged'] += 1
            entries.append(item)
            total += 1

        json.dump({"schema": "tt1-fix/1", "chapter": doc['chapter'],
                   "count": len(entries), "entries": entries},
                  open(os.path.join(out, doc['chapter'] + '.json'), 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)
        files.append({"chapter": doc['chapter'], "entries": len(entries)})

    json.dump({"schema": "tt1-fix/1",
               "game": "Time Travelers (NPJH50597)",
               "totals": {"chapters": len(files), "entries": total},
               "rules": RULES, "files": files},
              open(os.path.join(out, 'manifest.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)

    print('%d chapters, %d entries -> %s' % (len(files), total, out))
    for k, v in stats.most_common():
        print('   %-32s %d' % (k, v))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else r'D:\psp\타임트레블러즈\script_fix')
