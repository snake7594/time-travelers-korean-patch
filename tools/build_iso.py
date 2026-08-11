# -*- coding: utf-8 -*-
"""Build a diagnostic ISO: each font's kanji replaced by one Hangul letter.

nrm_main -> 가, nrm_sub -> 나, dbg -> 다.  Every size is preserved, so the
ISO is produced by copying the original and overwriting byte ranges.
"""
import os, shutil, struct, sys

import cpk, xpck, patch_font

SRC = r'D:\psp\타임트레블러즈\Time Travelers.iso'
DST = r'D:\psp\타임트레블러즈\Time Travelers (KR font test).iso'
CPK_LBA = 55248
SEC = 2048
MARK = {'nrm_main': u'\uac00', 'nrm_sub': u'\ub098', 'dbg': u'\ub2e4'}
XF_DIR = r'D:\psp\타임트레블러즈\extract\fnt'


def main():
    cpk_base = CPK_LBA * SEC
    c = cpk.CPK(SRC, base=cpk_base)
    entries = {e['name']: e for e in c.files if e['dir'] == 'psp/fnt'}

    patches = []                                   # (absolute ISO offset, bytes)
    for name, ch in MARK.items():
        xf_name = name + '.xf'
        ent = entries[xf_name]
        assert ent['size'] == ent['extract'], 'CPK entry is compressed'
        xf = open(os.path.join(XF_DIR, xf_name), 'rb').read()
        assert len(xf) == ent['size'], 'extracted .xf size mismatch'

        new_xi = patch_font.build(name, ch)
        inner = {f['name']: f for f in xpck.parse(xf)}
        xf_abs = cpk_base + ent['offset']
        for tex, blob in new_xi.items():
            fi = inner['%03d.xi' % tex]
            assert len(blob) == fi['size'], 'patched .xi changed size'
            patches.append((xf_abs + fi['offset'], blob))

    total = sum(len(b) for _, b in patches)
    print('\n%d byte ranges, %d bytes total' % (len(patches), total))

    if not os.path.exists(DST):
        print('copying ISO ...')
        shutil.copyfile(SRC, DST)
    with open(DST, 'r+b') as f:
        for off, blob in patches:
            f.seek(off)
            f.write(blob)
    print('wrote', DST)

    # verify by re-reading the patched fonts straight out of the new ISO
    c2 = cpk.CPK(DST, base=cpk_base)
    for e in c2.files:
        if e['dir'] != 'psp/fnt':
            continue
        files = {f['name']: f for f in xpck.parse(c2.read(e))}
        import imgp, numpy as np
        tex0 = files['000.xi']['data']
        w, h, rgba, rh = imgp.decode(tex0)
        ink = (np.frombuffer(rgba, np.uint8).reshape(h, w, 4)[:, :, 3] > 0).mean()
        print('  verified %-12s 000.xi decodes %dx%d, ink %.1f%%' % (e['name'], w, rh, ink * 100))


if __name__ == '__main__':
    main()
