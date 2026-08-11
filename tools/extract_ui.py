# -*- coding: utf-8 -*-
"""Extract the non-dialogue text: tips, tutorials, help, outlines, menus.

Two sources:
  *.cfg.bin  -- same blob format as the dialogue (record area addressing
                strings by byte offset), just without the .pck wrapper
  *.lua      -- menu scripts; only quoted strings are UI text, the rest of
                the Japanese in them is developer comments

  python extract_ui.py <outdir>
"""
import json, os, re, struct, sys, collections

import cpk, dnsfile

JP = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff]')
QUOTED = re.compile(r'"([^"\n]*)"|\'([^\'\n]*)\'')
CFG_DIRS = ['psp/txt/tip', 'psp/txt/tutorial', 'psp/txt/help',
            'psp/txt/outline', 'psp/txt/staffroll']

RULES = {
    "task": "Translate the Japanese into Korean. These are tips, tutorial and "
            "help texts, story outlines and menu prompts -- not character "
            "dialogue, so use plain informative Korean.",
    "line_break": "\\n (backslash + n) is a hard line break. Keep the ones the "
                  "source has; do not add new ones. The engine wraps at spaces "
                  "on its own.",
    "spacing": "Use natural Korean spacing. Never drop a space to save room.",
    "ruby": "[base/reading] is furigana. Translate the base word and drop the "
            "brackets and the reading -- EXCEPT inside <TIP...>...</TIP>, "
            "where the brackets are structural and must stay as [text/key].",
    "keep": "Leave every <...> tag as it is, and keep a leading ＊ if present.",
    "charset": "Do not use · ₩ ≤ or zero-width spaces; the game's encoding has "
               "no room for them. Use ・ for a middle dot.",
    "format": "Edit ko in place. Do not change id or ja, and do not add or "
              "remove entries.",
}


def split_cfg(d):
    """Strings sit at the end; locate them from the count in the header."""
    if len(d) < 16:
        return None
    cnt = struct.unpack('<I', d[12:16])[0]
    if not 0 < cnt < 4096:
        return None
    end = len(d)
    while end > 0 and d[end - 1] == 0xFF:
        end -= 1
    for base in range(end - 1, 0, -1):
        seg = d[base:end]
        if not seg.endswith(b'\x00') or seg.count(b'\x00') != cnt:
            continue
        try:
            seg.decode('cp932')
        except UnicodeDecodeError:
            continue
        return base, seg.split(b'\x00')[:-1]
    return None


def main(out):
    os.makedirs(out, exist_ok=True)
    c = cpk.CPK(dnsfile.DNSFile())
    stats = collections.Counter()

    groups = collections.defaultdict(list)
    for e in sorted((x for x in c.files if x['dir'] in CFG_DIRS),
                    key=lambda x: (x['dir'], x['name'])):
        got = split_cfg(c.read(e))
        stats['cfg files'] += 1
        if not got:
            stats['cfg unparsed'] += 1
            continue
        _, strs = got
        for i, s in enumerate(strs):
            try:
                t = s.decode('cp932')
            except UnicodeDecodeError:
                continue
            if not t or not JP.search(t):
                continue                     # blank, author, script id, padding
            groups[e['dir']].append({"id": "%s#%d" % (e['name'], i),
                                     "ja": t, "ko": ""})
            stats['cfg strings'] += 1

    lua = []
    for e in sorted((x for x in c.files if x['name'].endswith('.lua')),
                    key=lambda x: x['name']):
        text = c.read(e).decode('cp932', 'ignore')
        for ln, line in enumerate(text.splitlines(), 1):
            code = line.split('--')[0]
            for m in QUOTED.finditer(code):
                s = m.group(1) or m.group(2) or ''
                if JP.search(s):
                    lua.append({"id": "%s#%d#%d" % (e['name'], ln, m.start()),
                                "ja": s, "ko": ""})
                    stats['lua strings'] += 1
    if lua:
        groups['psp/script/lua'] = lua

    files = []
    for d, items in sorted(groups.items()):
        name = d.split('/')[-1]
        json.dump({"schema": "tt1-ui/1", "source": d, "count": len(items),
                   "entries": items},
                  open(os.path.join(out, name + '.json'), 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)
        files.append({"name": name, "source": d, "entries": len(items),
                      "chars": sum(len(x['ja']) for x in items)})
        print('  %-14s %5d strings  %7d chars' % (name, len(items),
                                                 sum(len(x['ja']) for x in items)))

    json.dump({"schema": "tt1-ui/1", "game": "Time Travelers (NPJH50597)",
               "totals": {"entries": sum(f['entries'] for f in files),
                          "chars": sum(f['chars'] for f in files)},
               "rules": RULES, "files": files},
              open(os.path.join(out, 'manifest.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print()
    print('total %d strings -> %s' % (sum(f['entries'] for f in files), out))
    for k, v in stats.most_common():
        print('   %-16s %d' % (k, v))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else r'D:\psp\타임트레블러즈\ui_json')
