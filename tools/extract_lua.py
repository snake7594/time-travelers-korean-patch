# -*- coding: utf-8 -*-
"""Pull the on-screen wording out of the Lua menu scripts.

The scripts are plain source, but every literal is written as
string.char(0x..,0x..,..) -- including the Japanese ones, which is why a
plain quote scan finds almost nothing. Both forms are collected here.

Offsets are byte offsets into the file so the text can be spliced back in.
Comments are skipped: their Japanese is never drawn.

  python extract_lua.py [out.json]
"""
import json, re, sys, collections
import cpk, dnsfile

CHARS = re.compile(rb'string\.char\(\s*((?:0x[0-9A-Fa-f]{1,2}\s*,\s*)*'
                   rb'0x[0-9A-Fa-f]{1,2})\s*\)')
QUOTED = re.compile(rb'"([^"\r\n]*)"')
BYTE = re.compile(rb'0x[0-9A-Fa-f]{1,2}')
JP = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff\uff66-\uff9f]')

# Only text that reaches the screen may be touched. The rest are asset and
# animation names -- Chr_SetMotion("立ち") looks up a clip inside a .xa, and
# translating it would stop the character drawing at all.
DRAWN = (b'Dialog_Start', b'Dialog', b'Text_CreateSet', b'Text_SetString',
         b'Text_Create', b'Msg_SetString', b'Utility_StartMsgDialog')
# Two files build their menu labels in plain tables, so the literal has no
# call around it. Everything Japanese in them is a label.
DRAWN_FILES = ('on_memory_tts.lua', 'menu_avantlist.lua')
CALLER = re.compile(rb'([A-Za-z_][A-Za-z0-9_]*)\s*\(\s*$')


def uncomment(src):
    """Blank -- comments, leaving every other byte where it was."""
    out = bytearray(src)
    i, n = 0, len(src)
    while i < n - 1:
        if src[i:i + 2] == b'--':
            j = src.find(b'\n', i)
            j = n if j < 0 else j
            out[i:j] = b' ' * (j - i)
            i = j
        else:
            i += 1
    return bytes(out)


def caller_of(src, start):
    """The function whose argument list this literal sits in."""
    depth, i = 0, start - 1
    while i >= 0 and start - i < 600:
        ch = src[i:i + 1]
        if ch == b')':
            depth += 1
        elif ch == b'(':
            if depth == 0:
                m = CALLER.search(src[max(0, i - 40):i + 1])
                return m.group(1) if m else b'?'
            depth -= 1
        i -= 1
    return b'?'


def strings(src):
    """[(form, start, end, text)] for every literal that carries Japanese."""
    body = uncomment(src)
    out = []
    for m in CHARS.finditer(body):
        try:
            t = bytes(int(x, 16) for x in BYTE.findall(m.group(1))).decode('cp932')
        except (ValueError, UnicodeDecodeError):
            continue
        if JP.search(t):
            out.append(('char', m.start(), m.end(), t))
    for m in QUOTED.finditer(body):
        try:
            t = m.group(1).decode('cp932')
        except UnicodeDecodeError:
            continue
        if JP.search(t):
            out.append(('quote', m.start(1), m.end(1), t))
    out.sort(key=lambda r: r[1])
    return out


def encode(form, raw):
    """Put CP932 bytes back in the shape the source used."""
    if form == 'char':
        return b'string.char(' + b','.join(b'0x%02X' % b for b in raw) + b')'
    return raw


def main(path):
    c = cpk.CPK(dnsfile.DNSFile())
    files = sorted((x for x in c.files if x['name'].endswith('.lua')),
                   key=lambda x: (x['dir'], x['name']))
    entries, per = [], collections.Counter()
    for e in files:
        src = c.read(e)
        body = uncomment(src)
        for form, a, b, t in strings(src):
            fn = caller_of(body, a).decode()
            entries.append({'id': '%s@%d' % (e['name'], a),
                            'file': '%s/%s' % (e['dir'], e['name']),
                            'form': form, 'caller': fn,
                            'drawn': fn.encode() in DRAWN
                                     or e['name'] in DRAWN_FILES,
                            'ja': t, 'ko': ''})
            per[fn] += 1
    doc = {'schema': 'tt1-ui/1', 'source': 'psp/script/lua/**/*.lua',
           'note': 'menu and system messages; literals are string.char()-encoded',
           'count': len(entries), 'entries': entries}
    json.dump(doc, open(path, 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    drawn = [e for e in entries if e['drawn']]
    print('%d literals; %d reach the screen (%d chars) -> %s'
          % (len(entries), len(drawn),
             sum(len(e['ja']) for e in drawn), path))
    for k, n in per.most_common(12):
        print('   %-22s %-4d %s'
              % (k, n, 'DRAWN' if k.encode() in DRAWN else ''))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1
         else r'D:\psp\타임트레블러즈\ui_json\lua.json')
