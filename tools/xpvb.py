# -*- coding: utf-8 -*-
"""Read the sprite rectangles out of a Level-5 .xa menu archive.

  RES.bin   L5-compressed ANMP00, the animation definitions and their names
  NNN.pbi   index buffer: six indices per quad, always four consecutive
            vertices
  000.pvb   'XPVB' -- header, then one L5 block of `count` vertices

Vertex, 20 bytes, five float32:
  0,1  u, v   texture coordinates, in pixels
  2,3  x, y   screen position, y measured upwards
  4          unused here

So a quad's four vertices give one texture rectangle and one screen
rectangle -- which is what the labels have to be drawn into.
"""
import struct, sys
import cpk, dnsfile, xpck, imgp

HDR = 20        # XPVB header: magic, then five fields


def parts_of(name):
    c = cpk.CPK(dnsfile.DNSFile())
    d = c.read([x for x in c.files if x['name'] == name][0])
    return {p['name']: p for p in xpck.parse(d)}


def blob(part):
    try:
        u = imgp.l5_decompress(part)
        return u if u else part
    except Exception:
        return part


def vertices(pvb):
    _, _, off, stride = struct.unpack('<4H', pvb[4:12])
    count = struct.unpack('<I', pvb[12:16])[0]
    raw = imgp.l5_decompress(pvb[off:])
    out = []
    for i in range(count):
        out.append(struct.unpack('<5f', raw[i * stride:(i + 1) * stride]))
    return out


def quads(parts):
    """[(pbi, first vertex)] for every quad the index buffers name."""
    out = []
    for k in sorted(parts):
        if not k.endswith('.pbi'):
            continue
        u = blob(parts[k]['data'])
        n = struct.unpack('<H', u[4:6])[0]
        n = min(n, (len(u) - 12) // 2)
        idx = struct.unpack('<%dH' % n, u[12:12 + n * 2])
        for i in range(0, n - 5, 6):
            g = idx[i:i + 6]
            lo = min(g)
            if sorted(set(g)) == list(range(lo, lo + 4)):
                out.append((k, lo))
    return out


def rects(name='navi.xa'):
    """[(pbi, uv rect, screen rect)] -- uv in texture pixels."""
    parts = parts_of(name)
    vs = vertices(parts['000.pvb']['data'])
    out = []
    for k, v0 in quads(parts):
        q = vs[v0:v0 + 4]
        us = [p[0] for p in q]
        vv = [p[1] for p in q]
        xs = [p[2] for p in q]
        ys = [p[3] for p in q]
        out.append((k,
                    (min(us), min(vv), max(us), max(vv)),
                    (min(xs), min(ys), max(xs), max(ys))))
    return out


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else 'navi.xa'
    got = rects(name)
    print('%s: %d quads' % (name, len(got)))
    seen = set()
    for k, uv, sc in got:
        key = tuple(round(x) for x in uv)
        if key in seen:
            continue
        seen.add(key)
        print('  %-9s tex %4d,%-4d %3dx%-3d   screen %5d,%-5d %3dx%-3d'
              % (k, uv[0], uv[1], uv[2] - uv[0], uv[3] - uv[1],
                 sc[0], sc[1], sc[2] - sc[0], sc[3] - sc[1]))


if __name__ == '__main__':
    main()
