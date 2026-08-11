# -*- coding: utf-8 -*-
"""Check both translated sets before building.

Every failure the game has shown so far came from broken markup, so this
looks at exactly those invariants plus the glyph budget.
"""
import json, glob, os, re, collections

TAG = re.compile(r'</?[A-Za-z][A-Za-z0-9]*>')
ANYTAG = re.compile(r'<[^>]{0,16}>')
TIP = re.compile(r'(<TIP\d*>)(.*?)(</TIP>)', re.S)
RUBY = re.compile(r'^\[([^/\]]*)/([^\]]*)\]$')
NL = '\\n'
KANJI = re.compile(r'[\u4e00-\u9fff]')
KANA = re.compile(r'[\u3040-\u30ff]')
HANGUL = re.compile(r'[가-힣]')
BAD = set('·₩≤\u200b')


def check(entries, label, want_no_kanji):
    p = collections.Counter()
    syl = set()
    ex = collections.defaultdict(list)
    for e in entries:
        ja, ko = e['ja'], e.get('ko', '')
        if not ko.strip():
            p['empty'] += 1
            ex['empty'].append(e['id'])
            continue
        if sorted(TAG.findall(ko)) != sorted(TAG.findall(ja)):
            p['tag mismatch'] += 1
            ex['tag mismatch'].append(e['id'])
        for m in ANYTAG.findall(ko):
            if not re.fullmatch(r'</?[A-Za-z][A-Za-z0-9]*>', m):
                p['malformed tag'] += 1
                ex['malformed tag'].append((e['id'], m))
        jt, kt = TIP.findall(ja), TIP.findall(ko)
        if len(jt) != len(kt):
            p['TIP count'] += 1
            ex['TIP count'].append(e['id'])
        else:
            for a, b in zip(jt, kt):
                if RUBY.match(a[1]) and not RUBY.match(b[1]):
                    p['TIP ruby lost'] += 1
                    ex['TIP ruby lost'].append(e['id'])
        for op, cl in (('「', '」'), ('『', '』'), ('＜', '＞')):
            if ko.count(op) != ko.count(cl):
                p['unbalanced ' + op] += 1
                ex['unbalanced'].append(e['id'])
        if len(ja) - len(ja.lstrip('＊')) != len(ko) - len(ko.lstrip('＊')):
            p['star count'] += 1
            ex['star count'].append(e['id'])
        if ko.count(NL) > ja.count(NL):
            p['extra line break'] += 1
            ex['extra line break'].append(e['id'])
        bad = BAD & set(ko)
        if bad:
            p['unencodable char'] += 1
            ex['unencodable char'].append((e['id'], ''.join(bad)))
        body = TIP.sub('', ko)
        if want_no_kanji and KANJI.search(body):
            p['kanji left'] += 1
            ex['kanji left'].append(e['id'])
        if KANA.search(body):
            p['kana left'] += 1
            ex['kana left'].append(e['id'])
        syl.update(HANGUL.findall(ko))
    print('--- %s : %d entries' % (label, len(entries)))
    if p:
        for k, v in p.most_common():
            s = ex.get(k) or ex.get('unbalanced') or []
            print('   %-20s %5d   e.g. %s' % (k, v, s[:2]))
    else:
        print('   clean')
    return syl


def load(d):
    out = []
    for p in sorted(glob.glob(os.path.join(d, '*.json'))):
        b = os.path.basename(p)
        if b == 'manifest.json' or b.startswith('_'):
            continue
        out += json.load(open(p, encoding='utf-8'))['entries']
    return out


a = check(load(r'D:\psp\타임트레블러즈\script_fix'), 'dialogue (proofread)', False)
b = check(load(r'D:\psp\타임트레블러즈\ui_json'), 'UI / tips', True)
print()
print('distinct Hangul syllables: dialogue %d, UI %d, combined %d'
      % (len(a), len(b), len(a | b)))
