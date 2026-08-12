# -*- coding: utf-8 -*-
"""Re-encrypt the PGD install stream with pgdecrypt.exe.

The stream is decrypted once, the edits are written into the plain bytes, and
the whole thing is handed back to the tool to encrypt. Rewriting the blocks in
place -- decrypt, patch, encrypt again, header untouched -- is what a build did
before, and the console refused those discs (`C1-2858-3`) even though PPSSPP
played them. The tool writes a fresh header and key with the data, and the
encrypted result is the same length as the original, so it drops straight back
into the image.
"""
import os
import shutil
import subprocess

TOOL = r'D:\psp\디크립트 툴\pgdecrypt\pgdecrypt.exe'
WORK = r'C:\tt_pgd'
PLAIN = 'DATA.BIN.decrypt'       # what the tool calls its decrypted output
FEED = 'data.cpk'                # what it reads back in to encrypt
OUT = 'DATA.cpk.encrypt'


def _run():
    r = subprocess.run([os.path.join(WORK, 'pgdecrypt.exe')], cwd=WORK,
                       capture_output=True, text=True)
    if 'Save DATA.cpk.encrypt' not in (r.stdout or ''):
        raise SystemExit('PGD 재암호화 실패: %s' % (r.stdout or r.stderr)[-300:])


def prepare(iso, lba, size, sector=2048):
    """Pull the stream out of the ISO and decrypt it, once."""
    os.makedirs(WORK, exist_ok=True)
    if not os.path.exists(os.path.join(WORK, 'pgdecrypt.exe')):
        shutil.copy(TOOL, WORK)
    plain = os.path.join(WORK, PLAIN)
    if os.path.exists(plain):
        return plain                      # already decrypted from an earlier run
    with open(iso, 'rb') as src, open(os.path.join(WORK, 'DATA.BIN'), 'wb') as dst:
        src.seek(lba * sector)
        left = size
        while left > 0:
            chunk = src.read(min(1 << 22, left))
            if not chunk:
                break
            dst.write(chunk)
            left -= len(chunk)
    for junk in (FEED, OUT):
        p = os.path.join(WORK, junk)
        if os.path.exists(p):
            os.remove(p)
    _run()
    return plain


def rewrite(edits, iso, lba, size, sector=2048):
    """The stream with `edits` applied, encrypted, as bytes."""
    plain = prepare(iso, lba, size, sector)
    feed = os.path.join(WORK, FEED)
    shutil.copyfile(plain, feed)
    with open(feed, 'r+b') as fh:
        for off, blob in edits:
            fh.seek(off)
            fh.write(blob)
    out = os.path.join(WORK, OUT)
    if os.path.exists(out):
        os.remove(out)
    _run()
    data = open(out, 'rb').read()
    if len(data) != size:
        raise SystemExit('재암호화 결과 %d 바이트, 원본 슬롯 %d' % (len(data), size))
    print('  PGD re-encrypted by pgdecrypt.exe: %d bytes, %d edits'
          % (len(data), len(edits)))
    return data
