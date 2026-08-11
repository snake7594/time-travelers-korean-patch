# -*- coding: utf-8 -*-
"""Build the Korean-subtitled movies with Sony's official PSMF tools.

The previous x264 builds decode in PPSSPP but do not match the AVC syntax used
by the disc (notably log2_max_frame_num=6), which can stop the PSP Media Engine.
This follows the proven Valkyria Chronicles 2 pipeline instead:

    subtitled UYVY AVI -> psmfenc -> psmfmux -> PsmfComposerCMD

Sony's old tools are given ASCII-only paths.  Each composed PMF is verified and
then padded at EOF to the original CPK slot size before it replaces movie/*.pmf.
"""
import gc
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import time

import cv2
import numpy as np

import cpk
import op_mux
import op_render
import op_subs
import pack_korean as P


RATE = '30000/1001'
FPS = 30000.0 / 1001.0
FFMPEG = r'C:\vc2work\tools\ffmpeg\ffmpeg.exe'
FFPROBE = r'C:\vc2work\tools\ffmpeg\ffprobe.exe'
SUITE = r'C:\vc2work\usc\psmfsuite\PSMF Stream Composer Suite'
ENCODER = os.path.join(SUITE, 'psmfenc.exe')
MUXER = os.path.join(SUITE, 'psmfmux.exe')
COMPOSER = os.path.join(SUITE, 'PsmfComposerCMD.exe')
DUMPER = r'C:\vc2work\usc\plus\tools\psmfdump.exe'
WORK_ROOT = r'C:\vc2work\usc\tt_sony'
# Match the known-good Valkyria Chronicles 2 Sony build.  64 kbps is legal,
# but the real-device reference used Sony's 96 kbps ATRAC target throughout.
AUDIO_KBPS = 96
MIN_VIDEO_KBPS = 80
MAX_ATTEMPTS = 10


def say(message):
    print(message, flush=True)


def run(cmd, cwd=None, label=None):
    """Run a tool and retain enough diagnostics to make failures actionable."""
    started = time.time()
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                          errors='replace')
    if proc.returncode:
        tail = (proc.stdout + '\n' + proc.stderr).strip()[-1200:]
        raise RuntimeError('%s failed (exit %d):\n%s' %
                           (label or os.path.basename(cmd[0]),
                            proc.returncode, tail))
    if label:
        say('  %s: %.1fs' % (label, time.time() - started))
    return proc


def require_tools():
    missing = [p for p in (FFMPEG, FFPROBE, ENCODER, MUXER, COMPOSER,
                            DUMPER, op_render.TTF) if not os.path.isfile(p)]
    if missing:
        raise RuntimeError('required file not found:\n' + '\n'.join(missing))


def load_original(name):
    archive = cpk.CPK(P.SRC, base=P.CPK_LBA * P.SEC)
    entry = next(x for x in archive.files
                 if x['dir'] == 'psp/mov' and x['name'] == name)
    return archive.read(entry)


def decode_to_bgr(es, raw_path, expected):
    """Decode the original elementary stream to a writable BGR memmap."""
    es_path = os.path.join(os.path.dirname(raw_path), 'original.264')
    with open(es_path, 'wb') as fh:
        fh.write(es)
    cap = cv2.VideoCapture(es_path)
    ok, first = cap.read()
    if not ok:
        cap.release()
        raise RuntimeError('OpenCV could not decode the first frame')
    h, w = first.shape[:2]
    frames = np.memmap(raw_path, mode='w+', dtype=np.uint8,
                       shape=(expected, h, w, 3))
    frames[0] = first
    count = 1
    while count < expected:
        ok, frame = cap.read()
        if not ok:
            break
        frames[count] = frame
        count += 1
        if count % 1000 == 0:
            say('  decode: %d/%d frames' % (count, expected))
    extra, _ = cap.read()
    cap.release()
    if count != expected or extra:
        del frames
        raise RuntimeError('decoded frame count %d does not match %d'
                           % (count + (1 if extra else 0), expected))
    frames.flush()
    return frames, w, h


def preview_for(name):
    """A ready-made subtitled cut of this film, if one was prepared.

    `movie/subtitles/<film>.ko.preview.mp4` is the rendered result of the full
    subtitle pass -- 125 lines for avant_title, against the 35 that reached
    op_subs. Re-rendering from op_subs would silently ship the shorter set, so
    when the preview is there and lines up frame for frame with the original,
    its pictures are used as they are.
    """
    path = os.path.join(P.MOVIE_DIR, 'subtitles',
                        os.path.splitext(name)[0] + '.ko.preview.mp4')
    return path if os.path.exists(path) else None


def make_avi(name, original, work):
    es = op_mux.video_es(original)
    expected = len(op_mux.frames(es))
    raw = os.path.join(work, 'subtitled.bgr')
    avi = os.path.join(work, 'subtitled.avi')

    ready = preview_for(name)
    if ready:
        probe = cv2.VideoCapture(ready)
        count = int(probe.get(cv2.CAP_PROP_FRAME_COUNT))
        pw = int(probe.get(cv2.CAP_PROP_FRAME_WIDTH))
        ph = int(probe.get(cv2.CAP_PROP_FRAME_HEIGHT))
        probe.release()
        if count == expected:
            say('  using prepared subtitles: %s (%d frames, %dx%d)'
                % (os.path.basename(ready), count, pw, ph))
            run([FFMPEG, '-y', '-hide_banner', '-loglevel', 'error',
                 '-i', ready, '-an', '-frames:v', str(expected),
                 '-c:v', 'rawvideo', '-pix_fmt', 'uyvy422', '-r', RATE, avi],
                label='UYVY AVI')
            return avi, expected, len(es), pw, ph
        say('  prepared subtitles skipped: %d frames, expected %d'
            % (count, expected))

    say('  decode: %d frames' % expected)
    frames, w, h = decode_to_bgr(es, raw, expected)
    op_render.render(name, frames, lambda _, i, n: say(
        '  subtitles: %d/%d cues' % (i + 1, n)))
    frames.flush()
    del frames
    gc.collect()
    run([FFMPEG, '-y', '-hide_banner', '-loglevel', 'error',
         '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', '%dx%d' % (w, h),
         '-r', RATE, '-i', raw, '-an', '-frames:v', str(expected),
         '-c:v', 'rawvideo', '-pix_fmt', 'uyvy422', '-r', RATE, avi],
        label='UYVY AVI')
    os.remove(raw)
    return avi, expected, len(es), w, h


def has_audio(original):
    off = struct.unpack('>I', original[8:12])[0]
    p = off
    while p + 6 <= len(original):
        if original[p:p + 3] != b'\x00\x00\x01':
            p += 1
            continue
        sid = original[p + 3]
        if sid == 0xBD:
            return True
        if sid == 0xBA:
            p += 14 + (original[p + 13] & 7)
            continue
        if sid == 0xB9:
            break
        p += 6 + struct.unpack('>H', original[p + 4:p + 6])[0]
    return False


def make_audio(original_path, avi, work):
    """Decode the original ATRAC3+ and let Sony encode a length-adjusted ATX."""
    audio_base = os.path.join(work, 'original_audio.oma')
    dump_video = os.path.join(work, 'dump.264')
    run([DUMPER, original_path, '-a', audio_base, '-v', dump_video],
        label='ATRAC extract')
    oma = os.path.join(work, 'original_audio.0.oma')
    wav = os.path.join(work, 'original_audio.wav')
    if not os.path.isfile(oma):
        raise RuntimeError('psmfdump did not create the ATRAC stream')
    run([FFMPEG, '-y', '-hide_banner', '-loglevel', 'error', '-i', oma,
         '-c:a', 'pcm_s16le', '-ar', '44100', '-ac', '2', wav],
        label='ATRAC decode')
    atx = os.path.join(work, 'audio.atx')
    run([ENCODER, '-audio', '-avgb', str(AUDIO_KBPS), '-adjust_v',
         avi, wav, atx], cwd=SUITE, label='Sony audio encode')
    if not os.path.isfile(atx):
        raise RuntimeError('Sony audio encoder did not create audio.atx')
    return atx


def remove_encode_outputs(work):
    for name in ('video.bsf', 'video.eui', 'video.esia', 'movie.mps',
                 'composed.pmf'):
        try:
            os.remove(os.path.join(work, name))
        except FileNotFoundError:
            pass


def normalize_psmf(pmf_path, mps_path):
    """Normalize Composer output to the PSP game's 0x800-byte PSMF layout.

    PsmfComposerCMD sometimes emits a 0x1000-byte header for a long clip.  The
    Valkyria Chronicles 2 hardware build and this game's original movies both
    use a 0x800-byte header, and their stream-size field names only the MPS
    payload (not the PSMF header).  The MPS itself is already sector-aligned,
    so it is safe to retain it verbatim and replace only the generated header
    placement/length fields.
    """
    pmf = open(pmf_path, 'rb').read()
    mps = open(mps_path, 'rb').read()
    if pmf[:8] != b'PSMF0015':
        raise RuntimeError('Composer output is not PSMF0015')
    offset = struct.unpack('>I', pmf[8:12])[0]
    if offset + len(mps) > len(pmf) or pmf[offset:offset + len(mps)] != mps:
        raise RuntimeError(
            'Composer payload does not match MPS (offset 0x%x, MPS %d)' %
            (offset, len(mps)))
    header = bytearray(pmf[:0x800])
    struct.pack_into('>I', header, 0x08, 0x800)
    struct.pack_into('>I', header, 0x0c, len(mps))
    normalized = bytes(header) + mps
    with open(pmf_path, 'wb') as fh:
        fh.write(normalized)
    say('  normalized PSMF header: 0x%x -> 0x800, stream=%d bytes' %
        (offset, len(mps)))


def compose(avi, audio, work, kbps):
    remove_encode_outputs(work)
    video = os.path.join(work, 'video.bsf')
    mps = os.path.join(work, 'movie.mps')
    pmf = os.path.join(work, 'composed.pmf')
    run([ENCODER, '-video', '-2pass', '-wp_off', '-avgb', str(kbps),
         avi, video], cwd=SUITE, label='Sony video encode at %dk' % kbps)
    if not os.path.isfile(video):
        raise RuntimeError('Sony video encoder did not create video.bsf')
    mux_cmd = [MUXER, video]
    if audio:
        mux_cmd.append(audio)
    mux_cmd.append(mps)
    run(mux_cmd, cwd=SUITE, label='Sony PSMF mux')
    run([COMPOSER, '-ep_map', mps, pmf], cwd=SUITE,
        label='Sony PSMF compose')
    if not os.path.isfile(pmf):
        raise RuntimeError('Sony composer did not create composed.pmf')
    normalize_psmf(pmf, mps)
    return pmf


def first_sps_log2(pmf):
    """Read log2_max_frame_num_minus4 from FFmpeg's H.264 trace output."""
    proc = subprocess.run(
        [FFMPEG, '-v', 'verbose', '-i', pmf, '-map', '0:v:0', '-frames:v',
         '1', '-c', 'copy', '-bsf:v', 'trace_headers', '-f', 'null', os.devnull],
        capture_output=True, text=True, errors='replace')
    found = re.search(r'log2_max_frame_num_minus4\s+[^=]*=\s*(\d+)',
                      proc.stdout + proc.stderr)
    return int(found.group(1)) if found else None


def verify(pmf, original_size, expected_frames, width, height):
    data = open(pmf, 'rb').read()
    if len(data) != original_size:
        raise RuntimeError('PMF size %d != original %d'
                           % (len(data), original_size))
    if data[:8] != b'PSMF0015':
        raise RuntimeError('unexpected PSMF header %r' % data[:8])
    stream_offset = struct.unpack('>I', data[8:12])[0]
    stream_size = struct.unpack('>I', data[12:16])[0]
    if stream_offset != 0x800:
        raise RuntimeError('PSMF stream offset 0x%x != required 0x800'
                           % stream_offset)
    if stream_size <= 0 or stream_size > len(data) - stream_offset:
        raise RuntimeError('invalid PSMF stream size %d for %d-byte file'
                           % (stream_size, len(data)))
    if data[stream_offset:stream_offset + 4] != b'\x00\x00\x01\xba':
        raise RuntimeError('PSMF stream does not begin with an MPEG pack')
    es = op_mux.video_es(data)
    if b'x264 - core' in es:
        raise RuntimeError('x264 encoder signature remains in output')
    aud_frames = len(op_mux.frames(es))
    if aud_frames != expected_frames:
        raise RuntimeError('AUD frame count %d != original %d'
                           % (aud_frames, expected_frames))
    probe = run([FFPROBE, '-v', 'error', '-count_frames', '-select_streams',
                 'v:0', '-show_entries',
                 'stream=width,height,nb_read_frames', '-of', 'json', pmf],
                label='frame-count verification')
    stream = json.loads(probe.stdout)['streams'][0]
    counted = int(stream['nb_read_frames'])
    if (counted, int(stream['width']), int(stream['height'])) != \
            (expected_frames, width, height):
        raise RuntimeError('decoded stream is %s, expected %dx%d/%d frames'
                           % (stream, width, height, expected_frames))
    run([FFMPEG, '-v', 'error', '-i', pmf, '-map', '0:v:0', '-f', 'null',
         '-y', os.devnull], label='full video decode')
    log2_minus4 = first_sps_log2(pmf)
    if log2_minus4 != 2:
        raise RuntimeError('Sony-compatible SPS expected '
                           'log2_max_frame_num_minus4=2, got %r'
                           % log2_minus4)
    return len(es), log2_minus4


def build_one(name):
    started = time.time()
    work = os.path.join(WORK_ROOT, os.path.splitext(name)[0])
    if os.path.isdir(work):
        shutil.rmtree(work)
    os.makedirs(work)
    original = load_original(name)
    original_path = os.path.join(work, 'original.pmf')
    with open(original_path, 'wb') as fh:
        fh.write(original)
    say('\n[%s] original=%d bytes' % (name, len(original)))
    avi, expected, original_es_size, width, height = make_avi(
        name, original, work)
    audio = make_audio(original_path, avi, work) if has_audio(original) else None
    duration = expected / FPS
    source_kbps = original_es_size * 8.0 / duration / 1000.0
    # The 2007 encoder silently produces no file for rates that are not a
    # multiple of 4 kbps (and still exits with status 0).
    kbps = max(MIN_VIDEO_KBPS, int(source_kbps * 0.98) // 4 * 4)
    selected = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        say('  compose attempt %d/%d: video=%dk audio=%s'
            % (attempt, MAX_ATTEMPTS, kbps,
               ('%dk' % AUDIO_KBPS) if audio else 'none'))
        pmf = compose(avi, audio, work, kbps)
        size = os.path.getsize(pmf)
        say('  composed size: %d / %d bytes (%.1f%%)'
            % (size, len(original), 100.0 * size / len(original)))
        if size <= len(original):
            selected = (pmf, size, kbps)
            break
        next_kbps = max(MIN_VIDEO_KBPS, int(kbps * 0.92) // 4 * 4)
        if next_kbps >= kbps:
            break
        kbps = next_kbps
    if selected is None:
        raise RuntimeError('%s cannot fit its %d-byte CPK slot'
                           % (name, len(original)))
    pmf, composed_size, kbps = selected
    padded = os.path.join(work, 'padded.pmf')
    with open(pmf, 'rb') as src, open(padded, 'wb') as dst:
        shutil.copyfileobj(src, dst)
        dst.write(b'\x00' * (len(original) - composed_size))
    es_size, log2 = verify(padded, len(original), expected, width, height)
    os.makedirs(P.MOVIE_DIR, exist_ok=True)
    destination = os.path.join(P.MOVIE_DIR, name)
    staged = destination + '.sony.tmp'
    shutil.copyfile(padded, staged)
    os.replace(staged, destination)
    say('  DONE: %s, %dk video, Sony SPS log2=%d, ES=%d bytes, %.1fs'
        % (destination, kbps, log2 + 4, es_size, time.time() - started))
    shutil.rmtree(work)


def main(argv):
    require_tools()
    names = argv or list(op_subs.MOVIES)
    unknown = [name for name in names if name not in op_subs.MOVIES]
    if unknown:
        raise SystemExit('unknown movie(s): ' + ', '.join(unknown))
    os.makedirs(WORK_ROOT, exist_ok=True)
    say('Sony PSMF build: %d movie(s)' % len(names))
    for index, name in enumerate(names, 1):
        say('\n=== %d/%d (%.0f%%) ===' %
            (index, len(names), 100.0 * (index - 1) / len(names)))
        build_one(name)
    say('\nALL SONY PMFs COMPLETE (100%)')


if __name__ == '__main__':
    main(sys.argv[1:])
