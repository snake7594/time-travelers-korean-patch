# -*- coding: utf-8 -*-
"""Let the text windows do their own wrapping.

The windows wrap by themselves, so the forced breaks the translation
inherited from the Japanese only push text past the last line. They are
removed here. Closing a break needs a decision -- 행동\n을 joins up, 게임
진행\n방법을 does not -- and that is made from the translation itself: if the
piece after the break never stands as a word anywhere in the script but the
joined form does, it belongs to the word before it.

  python unwrap_ui.py [--write]
"""
import json, os, glob, re, sys, collections
import dnsfile, pack_korean as P
from shorter_ui import SHORTER

UI = r'D:\psp\타임트레블러즈\ui_json'
FIX = r'D:\psp\타임트레블러즈\script_fix'
FILES = ['tip.json', 'tutorial.json', 'help.json', 'outline.json']
TAG = re.compile(r'<[^>]{0,24}>')
RUBY = re.compile(r'\[([^/\]]*)/[^\]]*\]')
EDGE = '.,!?)]}』」”’…・、。＿ 　\'"([{『「“‘'

PARTICLES = set("""
은 는 이 가 을 를 와 과 의 에 에서 에게 에겐 에는 에도 에서는 에서도 께 께서
한테 한테서 로 으로 로써 으로써 로서 으로서 로부터 부터 까지 도 만 밖에 조차
마저 처럼 같이 보다 대로 뿐 씩 째 이나 나 이란 란 라는 이라는 라고 이라고
이며 며 이고 고 이자 자 인 든 이든 이라도 라도 이야 야 요 이라 라
""".split())


# Breaks that fell inside a word where the corpus test cannot tell: either
# the joined form is rarer than the piece on its own, or it never occurs
# anywhere else. Matched at the break site only, so ordinary text is safe.
JOIN_PAIRS = {
    ('그', '때'), ('움직이', '지'), ('일어', '나는'), ('사용', '할'),
    ('진행', '해'), ('협력', '해'), ('다뤄', '진'), ('도쿄', '만에'),
    ('전환', '됩니다'), ('도착', '한'), ('반성', '문을'), ('시간', '대'),
    ('같', '지'), ('성공', '한다'), ('촬영', '할'), ('재개', '할'),
    ('이탈', '한'), ('골', '대가'), ('카', '운트'), ('지시', '였다고'),
    ('트레이', '너'), ('그리워', '하며'), ('성립했', '다는'),
}


def strip(t):
    return TAG.sub('', RUBY.sub(r'\1', t))


def corpus():
    """Every Korean word the translation uses, however it is spelled."""
    c = collections.Counter()
    for d in (FIX, UI):
        for p in sorted(glob.glob(os.path.join(d, '*.json'))):
            b = os.path.basename(p)
            if b == 'manifest.json' or b.startswith('_'):
                continue
            for e in json.load(open(p, encoding='utf-8'))['entries']:
                for w in strip(e.get('ko', '')).replace('\\n', ' ').split():
                    w = w.strip(EDGE)
                    if w:
                        c[w] += 1
    return c


def width(text, adv, default):
    return sum(adv.get(ord(c), default) for c in text)


def lines_needed(text, adv, default, box):
    n, cur = 1, 0
    for word in re.split(r'(\s+)', text):
        if not word:
            continue
        w = width(word, adv, default)
        if word.isspace():
            cur += w
            continue
        if cur and cur + w > box:
            n += 1
            cur = 0
        while w > box:
            n += 1
            word = word[1:]
            w = width(word, adv, default)
        cur += w
    return n


def unwrap(ko, vocab, unknown):
    out, i = [], 0
    while True:
        j = ko.find('\\n', i)
        if j < 0:
            out.append(ko[i:])
            break
        out.append(ko[i:j])
        rest = ko[j + 2:]
        left = (''.join(out).split() or [''])[-1].strip(EDGE)
        right = (rest.split() or [''])[0]
        right = TAG.split(right)[0].strip(EDGE)
        if not rest.strip():
            pass                                  # break at the very end
        elif out[-1].endswith(' ') or rest.startswith(' '):
            pass                                  # a space is already there
        elif right in PARTICLES or (left, right) in JOIN_PAIRS:
            pass                                  # 행동 + 을  ->  행동을
        elif vocab[left + right] and vocab[left + right] >= vocab[right]:
            # 누르 + 세요 -> 누르세요, 파 + 이브 -> 파이브. The joined form
            # being at least as common as the piece on its own is what tells
            # a split word apart from two real ones.
            pass
        else:
            if not vocab[right] and not vocab[left + right]:
                unknown.append('%s | %s' % (left, right))
            out.append(' ')
        i = j + 2
    return re.sub(r' +', ' ', ''.join(out)).strip()


def main(write=False):
    F = P.load_fonts(dnsfile.DNSFile())['nrm_sub.xf']
    adv = {c['code']: c['advance'] for c in F['meta']['large']}
    default = collections.Counter(adv.values()).most_common(1)[0][0]
    kadv = collections.defaultdict(lambda: P.UNIFORM_ADV, adv)
    vocab = corpus()
    print('vocabulary: %d distinct words' % len(vocab))

    unknown = []
    for name in FILES:
        path = os.path.join(UI, name)
        doc = json.load(open(path, encoding='utf-8'))
        segs = sorted(width(s, adv, default)
                      for e in doc['entries']
                      for s in strip(e['ja']).split('\\n')[:-1] if s.strip())
        if not segs:
            print('%-14s no forced breaks' % name)
            continue
        box = segs[int(len(segs) * .95)]

        def count(t, a, dflt):
            # the build turns the ASCII period full-width, so measure that
            return sum(lines_needed(s, a, dflt, box)
                       for s in P.full_stops(strip(t)).split('\\n'))

        before = after = changed = 0
        over = []
        for e in doc['entries']:
            ko = e.get('ko', '')
            if not ko.strip():
                continue
            nja = sum(lines_needed(s, adv, default, box)
                      for s in strip(e['ja']).split('\\n'))
            if count(ko, kadv, P.UNIFORM_ADV) > nja:
                before += 1
            new = SHORTER.get(e['id']) or unwrap(ko, vocab, unknown)
            if new != ko:
                changed += 1
            e['ko'] = new
            nko = count(new, kadv, P.UNIFORM_ADV)
            if nko > nja:
                after += 1
                over.append((e['id'], nja, nko, strip(new)))
        print('%-14s box %3dpx (%2d chars)  %3d rewritten  over: %3d -> %d'
              % (name, box, box // default, changed, before, after))
        for i, a, b, t in over[:6]:
            print('      %-24s %d -> %d  %s' % (i, a, b, t[:52]))
        if write:
            json.dump(doc, open(path, 'w', encoding='utf-8'),
                      ensure_ascii=False, indent=1)
    if unknown:
        print()
        print('spaced but neither form is a known word (%d):' % len(unknown))
        for s in unknown[:30]:
            print('   %s' % s)


if __name__ == '__main__':
    main('--write' in sys.argv)
