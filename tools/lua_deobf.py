# -*- coding: utf-8 -*-
"""Turn the string.char(0x..,0x..) name obfuscation back into readable text.

  python lua_deobf.py <name.lua> [grep-word]
"""
import re, sys
import cpk, dnsfile

CH = re.compile(r'string\.char\(\s*((?:0x[0-9A-Fa-f]+\s*,?\s*)+)\)')


def deobf(src):
    def sub(m):
        vals = [int(x, 16) for x in re.findall(r'0x[0-9A-Fa-f]+', m.group(1))]
        try:
            return '"%s"' % bytes(vals).decode('cp932')
        except UnicodeDecodeError:
            return m.group(0)
    return CH.sub(sub, src)


def main():
    c = cpk.CPK(dnsfile.DNSFile())
    e = [x for x in c.files if x['name'] == sys.argv[1]][0]
    src = deobf(c.read(e).decode('cp932'))
    if len(sys.argv) > 2:
        word = sys.argv[2]
        for i, l in enumerate(src.split('\n')):
            if word in l:
                print('%5d  %s' % (i + 1, l.strip()[:150]))
    else:
        print(src)


if __name__ == '__main__':
    main()
