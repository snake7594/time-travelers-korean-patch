# -*- coding: utf-8 -*-
"""Make the secondary fonts able to draw Korean.

telop_main and staffroll only carry ~450 kanji each, so most of the code
points the translation borrows are simply absent and the engine paints its
missing-glyph box -- that is the ????? in the guide window. Their own kanji
are dead weight now that the text is Korean, so each kanji slot is re-pointed
at a code point we actually use and redrawn as that syllable.

The char table is binary-searched, so it is re-sorted after the codes change.
"""
import struct, collections
import imgp, l5enc


def remap(F, wanted, render, redraw, band=None, must=()):
    """wanted: [code point] in priority order. Returns (new FNT.bin, new .xi).

    `must` is taken first and never dropped: these fonts hold only a few
    hundred glyphs, far fewer than the translation uses, so the text they
    actually draw -- the chapter cards and the menus -- has to be reserved
    before the merely-frequent syllables get a look in.
    """
    data = F['files']['FNT.bin']['data']
    m = F['meta']
    h = struct.unpack('<6H', data[0x1C:0x28])
    lg_off, lg_cnt, sm_off = h[2] * 4, h[3], h[4] * 4
    blk = data[lg_off:sm_off]
    raw = imgp.l5_decompress(blk)[:lg_cnt * 8]

    have = {c['code'] for c in m['large']}
    # A slot whose code point the translation already borrows must keep it.
    # Handing it to another syllable removed the one that was there -- which
    # is how the chapter cards lost 나, 경 and 교 and came out as ?????.
    keep = set(wanted) | set(must)
    # Kana count as slots too. The two telop fonts that draw the chapter card
    # carry nothing but the kanji and kana of those few titles -- barely two
    # dozen glyphs each -- so restricting slots to kanji left nowhere to put
    # the Korean and the card came out as ?????.
    slots = [i for i, c in enumerate(m['large'])
             if c['code'] >= 0x3000
             and c['code'] not in keep
             and m['sizes'][c['size']][2] >= 10
             and m['sizes'][c['size']][3] >= 10]
    # The block re-encodes with the tree already in the file, whose alphabet
    # is only the bytes the original table used. Restricting candidates to it
    # dropped syllables the chapter cards need for a couple of slots' worth of
    # compression, so let everything through and leave _fit to pick between
    # that tree and LZ10.
    symbols = None
    # Sorted by value, not by how often the syllable is used: the slots are
    # walked in code order too, so near-in-value targets barely disturb the
    # bytes and many more of them fit. Picking the most frequent instead
    # scatters the values and only a handful survive the size limit.
    def encodable(cp):
        return cp not in have and (
            symbols is None
            or ((cp & 0xFF) in symbols and (cp >> 8) in symbols))

    # The text this font actually draws comes first and is followed by the
    # busiest syllables overall. How many of the list survives is decided by
    # how well the char table still compresses, so a font that can only take
    # a couple of hundred still gets the ones that matter.
    seen = set()
    todo = []
    for cp in list(must) + list(wanted):
        if cp in seen or not encodable(cp):
            continue
        seen.add(cp)
        todo.append(cp)
    todo = todo[:600]

    # Both the slots and the code points we want are sorted kanji ranges, so
    # pairing them in order keeps the table sorted for the binary search and
    # keeps the byte changes small enough to still compress into the block.
    slots.sort(key=lambda i: m['large'][i]['code'])
    room = sm_off - lg_off

    def build(n):
        ents = [bytearray(raw[i * 8:i * 8 + 8]) for i in range(lg_cnt)]
        picked = sorted(todo[:n])
        got = {}
        for i, cp in zip(slots, picked):
            ents[i][0:2] = struct.pack('<H', cp)
            got[cp] = m['large'][i]
        codes = [struct.unpack('<H', bytes(e[0:2]))[0] for e in ents]
        if codes != sorted(codes):
            ents.sort(key=lambda b: struct.unpack('<H', bytes(b[0:2]))[0])
        return _fit(b''.join(bytes(e) for e in ents), blk, room), got

    # Rewriting every slot overflows the block by a couple of hundred bytes;
    # fewer changes compress better, so take the most that still fits.
    lo, hi, best = 0, min(len(slots), len(todo)), None
    while lo <= hi:
        mid = (lo + hi) // 2
        new, got = build(mid)
        if new is None:
            hi = mid - 1
        else:
            best = (new, got)
            lo = mid + 1
    if best is None:
        return None, 0
    new, assigned = best
    print('      re-pointed %d of %d free slots' % (len(assigned), len(slots)))
    out = bytearray(data)
    out[lg_off:sm_off] = new + bytes(sm_off - lg_off - len(new))

    # Draw every code point the translation uses that this font can now
    # reach -- not just the slots we re-pointed. The ones it already carried
    # would otherwise keep their original kanji and show up as garbage in the
    # middle of Korean text.
    for cp in wanted:
        if cp in have and cp not in assigned:
            for c in m['large']:
                if c['code'] == cp:
                    assigned[cp] = c
                    break

    boxes = collections.defaultdict(list)
    for cp, g in assigned.items():
        _, oy, w, hgt = m['sizes'][g['size']]
        b = None
        if band:
            # draw at this font's own size, not the dialogue font's
            b = (max(0, band[0] - oy), min(band[1] - band[0], hgt), w)
        boxes[g['tex']].append((g['x'], g['y'], w, hgt, render[cp], b))
    tex = {}
    for t, bs in boxes.items():
        tex[t] = redraw(F['files']['%03d.xi' % t]['data'], bs)
    return (bytes(out), tex), len(assigned)


def _fit(raw, orig_blk, room):
    out = [struct.pack('<I', len(raw) << 3) + raw]      # method 0, stored
    try:
        out.append(l5enc.block(raw, l5enc.tree_of(orig_blk)))
    except Exception:
        pass
    out.append(l5enc.lz10_block(raw))
    out = [b for b in out if len(b) <= room]
    return min(out, key=len) if out else None


def remap_small(F, must, render, redraw, band=None, protect=()):
    """For a font that carries one screen's worth of glyphs and nothing else.

    telop_player and telop_sp hold only the kanji and kana of the chapter
    card -- 刑事編, 伏見雛の場合 and the rest -- two dozen glyphs each, in a
    char table with no slack at all. Re-pointing a few entries and keeping
    the others therefore never fits. The table is rewritten instead with
    just the syllables this font has to draw; dropping the Japanese it no
    longer needs is what makes room.
    """
    data = F['files']['FNT.bin']['data']
    m = F['meta']
    h = struct.unpack('<6H', data[0x1C:0x28])
    lg_off, lg_cnt, sm_off = h[2] * 4, h[3], h[4] * 4
    blk = data[lg_off:sm_off]
    raw = imgp.l5_decompress(blk)[:lg_cnt * 8]
    room = sm_off - lg_off

    # `protect` are the code points the Korean itself still spells out --
    # full-width digits, ．（）！？ and the like. Handing those slots to a
    # syllable took the font's own digits away and '폭발 ３０초 전' lost its
    # number.
    slots = [i for i, c in enumerate(m['large'])
             if c['code'] >= 0x3000
             and c['code'] not in protect
             and m['sizes'][c['size']][2] >= 10
             and m['sizes'][c['size']][3] >= 10]
    # Japanese needs no word space and these fonts carry none, so one slot
    # becomes it -- otherwise every gap in the Korean drew the missing-glyph
    # box: '형사?편'.
    SPACE = 0x20
    picked = [SPACE] + [cp for cp in dict.fromkeys(must) if cp != SPACE]
    picked = picked[:len(slots)]          # priority order; the tail is cut
    use = dict(zip(slots, picked))

    def table(keep_ascii):
        ents, assigned, blanks = [], {}, []
        for i, c in enumerate(m['large']):
            if i in use:
                e = bytearray(raw[i * 8:i * 8 + 8])
                struct.pack_into('<H', e, 0, use[i])
                if use[i] == SPACE:
                    half = max(4, c['advance'] // 2)
                    struct.pack_into('<H', e, 2,
                                     (c['size'] & 0x3FF) | (half << 10))
                    blanks.append(c)
                else:
                    assigned[use[i]] = c
                ents.append(bytes(e))
            elif c['code'] in protect or (keep_ascii and c['code'] < 0x3000):
                ents.append(raw[i * 8:i * 8 + 8])   # digits, ？, the ? box
        ents.sort(key=lambda b: struct.unpack('<H', b[:2])[0])
        return ents, assigned, blanks

    # The ASCII entries stay, always: dropping them cost the font its digits
    # and its missing-glyph box, and '폭발 30초 전' came out as '폭발 //초 전'.
    # What gives instead is the tail of the syllable list, which is ordered
    # least-important last.
    new = None
    for keep_ascii in (True, False):
        use = dict(zip(slots, picked))
        ents, assigned, blanks = table(keep_ascii)
        new = _fit(b''.join(ents), blk, room)
        if new is not None:
            break
    while new is None and picked:
        # Neither fits, so give up syllables rather than the ASCII: the tail
        # of the list is the least important of them.
        picked = picked[:-8]
        use = dict(zip(slots, picked))
        ents, assigned, blanks = table(True)
        new = _fit(b''.join(ents), blk, room)
    if new is None:
        return None, 0

    out = bytearray(data)
    out[lg_off:sm_off] = new + bytes(room - len(new))
    struct.pack_into('<H', out, 0x22, len(ents))       # the table is shorter
    boxes = collections.defaultdict(list)
    for cp, g in assigned.items():
        _, oy, w, hgt = m['sizes'][g['size']]
        b = None
        if band:
            b = (max(0, band[0] - oy), min(band[1] - band[0], hgt), w)
        boxes[g['tex']].append((g['x'], g['y'], w, hgt, render[cp], b))
    for g in blanks:
        _, _, w, hgt = m['sizes'][g['size']]
        boxes[g['tex']].append((g['x'], g['y'], w, hgt, None, None))
    tex = {t: redraw(F['files']['%03d.xi' % t]['data'], bs)
           for t, bs in boxes.items()}
    return (bytes(out), tex), len(assigned)
