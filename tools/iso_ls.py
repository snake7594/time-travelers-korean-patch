import struct, sys, io

ISO = r"D:\psp\타임트레블러즈\Time Travelers.iso"
SEC = 2048

f = open(ISO, "rb")

def read_sector(lba, count=1):
    f.seek(lba * SEC)
    return f.read(SEC * count)

# --- Primary Volume Descriptor at LBA 16 ---
pvd = read_sector(16)
assert pvd[1:6] == b"CD001", pvd[:16]
vol_id = pvd[40:72].decode("latin-1").strip()
vol_size = struct.unpack("<I", pvd[80:84])[0]
print("Volume ID   :", vol_id)
print("Volume size : %d sectors (%.1f MB)" % (vol_size, vol_size * SEC / 1048576))

root_dr = pvd[156:156+34]
root_lba = struct.unpack("<I", root_dr[2:6])[0]
root_len = struct.unpack("<I", root_dr[10:14])[0]
print("Root dir    : LBA %d, %d bytes" % (root_lba, root_len))
print()

entries = []

def parse_dir(lba, length, path):
    data = read_sector(lba, (length + SEC - 1) // SEC)
    off = 0
    while off < length:
        rl = data[off]
        if rl == 0:
            # advance to next sector boundary
            off = (off // SEC + 1) * SEC
            if off >= length:
                break
            continue
        rec = data[off:off+rl]
        ext_lba = struct.unpack("<I", rec[2:6])[0]
        ext_len = struct.unpack("<I", rec[10:14])[0]
        flags = rec[25]
        nlen = rec[32]
        name = rec[33:33+nlen]
        off += rl
        if nlen == 1 and name in (b"\x00", b"\x01"):
            continue
        nm = name.decode("latin-1")
        if ";" in nm:
            nm = nm.split(";")[0]
        full = path + "/" + nm
        isdir = bool(flags & 0x02)
        entries.append((full, ext_lba, ext_len, isdir))
        if isdir:
            parse_dir(ext_lba, ext_len, full)

parse_dir(root_lba, root_len, "")

for full, lba, ln, isdir in entries:
    if isdir:
        print("  <DIR>            %-60s" % full)
    else:
        print("  %10d bytes  %-60s  (LBA %d)" % (ln, full, lba))
