# -*- coding: utf-8 -*-
"""Extract the choice text from psp/script/*.scn.

The nine .scn files are byte-identical in their string tables, so one
translation covers all of them. Strings live at the offset in the header at
+0x30 and run to the end of the file, NUL separated.
"""
import json, os, struct, sys
import cpk, dnsfile

STR_OFF = 0x30


def strings(d):
    """(index, text) for every Japanese string, index counted over all slots."""
    off = struct.unpack('<I', d[STR_OFF:STR_OFF + 4])[0]
    out, i = [], 0
    for raw in d[off:].split(b'\x00'):
        if raw:
            try:
                t = raw.decode('cp932')
            except UnicodeDecodeError:
                t = None
            if t and any('\u3040' <= ch <= '\u9fff' for ch in t):
                out.append((i, t))
        i += 1
    return off, out


def main(out_path):
    c = cpk.CPK(dnsfile.DNSFile())
    names = sorted(x['name'] for x in c.files if x['name'].endswith('.scn'))
    d = c.read([x for x in c.files if x['name'] == names[0]][0])
    _, items = strings(d)

    seen, entries = {}, []
    for idx, t in items:
        if t in seen:
            continue
        seen[t] = idx
        entries.append({"id": "scn#%d" % idx, "ja": t, "ko": ""})

    doc = {"schema": "tt1-ui/1", "source": "psp/script/*.scn",
           "note": "the nine .scn files share one string table; this covers all",
           "count": len(entries), "entries": entries}
    json.dump(doc, open(out_path, 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print('%d strings, %d chars -> %s'
          % (len(entries), sum(len(e['ja']) for e in entries), out_path))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1
         else r'D:\psp\타임트레블러즈\ui_json\choice.json')
