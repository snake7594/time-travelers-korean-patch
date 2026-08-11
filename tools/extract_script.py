# -*- coding: utf-8 -*-
"""Extract the event script to JSON for external translation, and re-insert it.

  python extract_script.py dump   <outdir>
  python extract_script.py check  <outdir>

Layout produced:
  <outdir>/manifest.json      global info, rules, per-chapter counts
  <outdir>/<CHAPTER>.json     one file per chapter, entries in story order

Entry ids are "<CHAPTER>:<blob>:<index>" and address a string by position, so
they stay valid as long as the source ISO is unchanged (guarded by "sha1").

Only strings #3.. of a blob are content; #0-#2 are always the script's date,
author and id and are left alone.
"""
import hashlib, json, os, re, sys

import cpk, dnsfile, build_expand2 as B

ENC = 'cp932'
RUBY = re.compile(r'\[([^/\]]*)/([^\]]*)\]')
TAG = re.compile(r'</?[A-Za-z][A-Za-z0-9]*>')

RULES = {
    "encoding": "The game stores text as CP932. Write ko as ordinary Korean; "
                "the packer assigns each Hangul syllable to a spare glyph slot.",
    "line_break": "\\n (backslash + n, two literal characters) starts a new "
                  "line. The engine does NOT wrap: anything past the right "
                  "edge is clipped, so insert \\n yourself.",
    "max_chars_per_line": 30,
    "max_lines_per_entry": 2,
    "tags": "Keep every <...> tag (e.g. <B>, <W15>, <TIP>, </TIP>) verbatim "
            "and in the same relative order. They control pacing, not text.",
    "ruby": "[base/reading] is furigana. Korean needs none: translate the base "
            "word and drop the brackets and the reading.",
    "leading_marker": "A leading ＊ (U+FF0A) marks a narration line. Keep it as "
                      "the first character if the source has it.",
    "empty": "If a source entry is an empty string, leave ko empty too.",
    "glyph_budget": 2300,
    "glyph_budget_note": "Total distinct Hangul syllables across the whole "
                         "translation must stay under this; the font has that "
                         "many glyph slots to repurpose.",
}


def readable(s):
    """Collapse ruby to its base word so the line reads naturally."""
    return RUBY.sub(lambda m: m.group(1), s)


def iter_entries(c):
    for e in sorted((x for x in c.files if x['dir'] == 'psp/txt/event/pck'),
                    key=lambda x: x['name']):
        chapter = e['name'][:-4]
        raw = c.read(e)
        n, recs = B.blobs_of(raw)
        out = []
        for bi, (h, off, sz) in enumerate(recs):
            b = raw[off:off + sz]
            if len(b) < 20:
                continue
            g = B.split_strings(b)
            if not g:
                continue
            for si, s in enumerate(g[2]):
                if si < 3:                      # date / author / script id
                    continue
                try:
                    t = s.decode(ENC)
                except UnicodeDecodeError:
                    continue
                out.append((bi, si, t))
        yield chapter, e, raw, out


def dump(outdir):
    os.makedirs(outdir, exist_ok=True)
    c = cpk.CPK(dnsfile.DNSFile())
    files, total, chars = [], 0, 0
    for chapter, e, raw, rows in iter_entries(c):
        entries = []
        for bi, si, t in rows:
            item = {"id": "%s:%d:%d" % (chapter, bi, si), "ja": t, "ko": ""}
            r = readable(t)
            if r != t:
                item["ja_read"] = r
            if '\n' in t.replace('\\n', '\n'):
                pass
            item["lines"] = t.count('\\n') + 1
            entries.append(item)
        doc = {"schema": "tt1-script/1", "chapter": chapter,
               "source": e['name'], "count": len(entries), "entries": entries}
        with open(os.path.join(outdir, chapter + '.json'), 'w', encoding='utf-8') as f:
            json.dump(doc, f, ensure_ascii=False, indent=1)
        n = sum(len(x['ja']) for x in entries)
        files.append({"chapter": chapter, "source": e['name'],
                      "entries": len(entries), "chars": n,
                      "sha1": hashlib.sha1(raw).hexdigest()})
        total += len(entries)
        chars += n
        print('  %-6s %5d entries %7d chars' % (chapter, len(entries), n))

    man = {"schema": "tt1-script/1",
           "game": "Time Travelers (NPJH50597)",
           "encoding": ENC,
           "totals": {"chapters": len(files), "entries": total, "chars": chars},
           "rules": RULES,
           "files": files}
    with open(os.path.join(outdir, 'manifest.json'), 'w', encoding='utf-8') as f:
        json.dump(man, f, ensure_ascii=False, indent=1)
    print('\n%d chapters, %d entries, %d chars -> %s' % (len(files), total, chars, outdir))


def check(outdir):
    """Validate a translated set: markup kept, lines short enough, budget."""
    man = json.load(open(os.path.join(outdir, 'manifest.json'), encoding='utf-8'))
    limit = man['rules']['max_chars_per_line']
    syll, problems, done = set(), [], 0
    for fi in man['files']:
        p = os.path.join(outdir, fi['chapter'] + '.json')
        doc = json.load(open(p, encoding='utf-8'))
        for it in doc['entries']:
            ko = it.get('ko', '')
            if not ko:
                continue
            done += 1
            if sorted(TAG.findall(ko)) != sorted(TAG.findall(it['ja'])):
                problems.append((it['id'], 'tag mismatch'))
            if it['ja'].startswith('＊') and not ko.startswith('＊'):
                problems.append((it['id'], 'missing leading ＊'))
            if '[' in ko or ']' in ko:
                problems.append((it['id'], 'ruby brackets left in ko'))
            for ln in ko.split('\\n'):
                body = TAG.sub('', ln)
                if len(body) > limit:
                    problems.append((it['id'], 'line %d chars > %d' % (len(body), limit)))
            syll.update(ch for ch in ko if 0xAC00 <= ord(ch) <= 0xD7A3)
    print('translated %d entries; distinct Hangul syllables %d (budget %d)'
          % (done, len(syll), man['rules']['glyph_budget']))
    if len(syll) > man['rules']['glyph_budget']:
        print('  OVER BUDGET')
    print('problems: %d' % len(problems))
    for i, (k, m) in enumerate(problems[:20]):
        print('   %-16s %s' % (k, m))


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'dump'
    out = sys.argv[2] if len(sys.argv) > 2 else r'D:\psp\타임트레블러즈\script_json'
    (dump if cmd == 'dump' else check)(out)
