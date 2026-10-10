"""Cut the ad: takes + still inserts + supers + captions + end card, then the export ratios.

    python cut_ad.py <ad_dir>           -> <ad_dir>/out/<output>_9x16.mp4 (+ _16x9, _1x1)

Reads <ad_dir>/cut.json (see docs/cut-format.md) and the takes in takes/leveled/ (or takes/).
The cut is laid out in the ratio of shots.json; every other ratio in "exports" is derived from it
by centring the frame over a blurred, darkened copy of itself (no re-render, nothing cropped).
Supers sit in the top band, captions near the bottom (ads autoplay muted), the programme is
normalised to -14 LUFS (H.264 CRF 20, AAC, +faststart). Fonts: assets/fonts from fetch_fonts.py.
"""
import json
import os
import subprocess
import sys
import textwrap

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ad_project import find_fonts, load  # noqa: E402

SIZES = {"9:16": (1080, 1920), "16:9": (1920, 1080), "1:1": (1080, 1080), "4:5": (1080, 1350)}
FPS = 30

ad = sys.argv[1]
cfg = load(ad, "cut.json")
ratio = load(ad, "shots.json", {}).get("ratio", "9:16")
W, H = SIZES[ratio]
K = min(W, H) / 1080  # text scale
work = os.path.join(ad, "cut")
os.makedirs(work, exist_ok=True)
os.makedirs(os.path.join(ad, "out"), exist_ok=True)
fonts = os.path.relpath(find_fonts(ad), work).replace("\\", "/")
BOLD, REG, CJK = f"{fonts}/NotoSans-Bold.ttf", f"{fonts}/NotoSans-Regular.ttf", f"{fonts}/NotoSansSC-Bold.otf"
if not os.path.exists(os.path.join(work, REG)):
    REG = BOLD
colors = cfg.get("colors", {})
BG = colors.get("bg", "0x111214")
ACCENT = colors.get("accent", "0xf5c542")
TEXT = colors.get("text", "white")


def run(cmd):
    r = subprocess.run(cmd, cwd=work, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"ffmpeg failed:\n{' '.join(cmd)}\n{r.stderr[-2000:]}")


def is_cjk(ch):
    return ord(ch) > 0x2E80


def width_em(s):
    """Approximate rendered width in em: Latin ~0.52 (Noto Sans Bold), CJK 1."""
    return sum(1.0 if is_cjk(c) else 0.52 for c in s)


n_text = 0


def textfile(s):
    global n_text
    n_text += 1
    name = f"t{n_text}.txt"
    # plain LF line ends: drawtext draws a CR (Windows text mode) as an extra blank line
    with open(os.path.join(work, name), "w", encoding="utf-8", newline=chr(10)) as f:
        f.write(s)
    return name


def font_for(s):
    return CJK if any(is_cjk(c) for c in s) else BOLD


def fit(s, size, max_w):
    """Largest font size <= size at which s fits on one line in max_w px."""
    return int(min(size, max_w / max(1.0, width_em(s))))


def wrap(s, size, max_w):
    if width_em(s) * size <= max_w:
        return s
    per_line = max(8, int(max_w / (size * (1.0 if any(is_cjk(c) for c in s) else 0.52))))
    if any(is_cjk(c) for c in s):
        return "\n".join(s[i:i + per_line] for i in range(0, len(s), per_line))
    return "\n".join(textwrap.wrap(s, per_line))


# centre each line of a wrapped caption (ffmpeg >= 7.1); older builds keep them left-aligned
ALIGN = ":text_align=C" if "text_align" in subprocess.run(
    ["ffmpeg", "-hide_banner", "-h", "filter=drawtext"], capture_output=True, text=True).stdout else ""


def fade(seg, delay=0.0):
    return f"alpha='min(1,max(0,(t-{delay})/0.25))'" if seg.get("fade", True) else "alpha=1"


def overlays(seg):
    """drawtext filters: super + sub in the top band (or "super_at": "lower", just above the
    captions, when a face is in the top of the frame), captions in a box near the bottom."""
    f = []
    lower = seg.get("super_at") == "lower"
    top = int(H * (0.60 if lower else 0.12))
    if seg.get("super") and "clip" in seg:
        y0 = int(H * 0.56) if lower else 0
        f.append(f"drawbox=x=0:y={y0}:w=iw:h={int(H * 0.17 if lower else H * 0.25)}:color=black@0.40:t=fill")
    if seg.get("super"):
        size = fit(seg["super"], 118 * K, W * 0.9)
        f.append(f"drawtext=fontfile={font_for(seg['super'])}:textfile={textfile(seg['super'])}:fontsize={size}:"
                 f"fontcolor={TEXT}:shadowcolor=black@0.6:shadowx=0:shadowy=4:x=(w-text_w)/2:y={top}:{fade(seg)}")
        top += int(size * 1.25)
    if seg.get("sub"):
        size = fit(seg["sub"], 52 * K, W * 0.9)
        f.append(f"drawtext=fontfile={font_for(seg['sub'])}:textfile={textfile(seg['sub'])}:fontsize={size}:"
                 f"fontcolor={ACCENT}:shadowcolor=black@0.7:shadowx=0:shadowy=3:x=(w-text_w)/2:y={top}:{fade(seg, 0.2)}")
    t0 = seg.get("in", 0)
    size = int(54 * K)
    for c in seg.get("captions", []):
        a, b = c["start"] - t0, c["end"] - t0
        text = wrap(c["text"], size, W * 0.86)
        f.append(f"drawtext=fontfile={font_for(c['text'])}:textfile={textfile(text)}:fontsize={size}:fontcolor=white:"
                 f"line_spacing={int(size * 0.25)}{ALIGN}:box=1:boxcolor=black@0.55:boxborderw={int(22 * K)}:"
                 f"x=(w-text_w)/2:y={int(H * 0.80)}-text_h/2:enable='between(t,{a:.2f},{b:.2f})'")
    return f


def rel(path):
    return os.path.relpath(os.path.join(ad, path), work).replace("\\", "/")


ENC = ["-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000"]
SILENCE = ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]


def seg_clip(i, seg):
    src = os.path.join("takes", "leveled", seg["clip"] + ".mp4")
    if not os.path.exists(os.path.join(ad, src)):
        src = os.path.join("takes", seg["clip"] + ".mp4")
    tin, tout = seg.get("in", 0), seg.get("out")
    vf = [f"scale={W}:{H}:force_original_aspect_ratio=increase", f"crop={W}:{H}", "setsar=1", f"fps={FPS}"] + overlays(seg)
    cmd = ["ffmpeg", "-y", "-ss", f"{tin}", "-i", rel(src)] + (["-t", f"{tout - tin}"] if tout else [])
    run(cmd + ["-vf", ",".join(vf), "-af", "aresample=48000,aformat=channel_layouts=stereo", *ENC, f"s{i:02d}.mp4"])


def seg_still(i, seg):
    """An image (UI screenshot, product photo) as a floating card with a soft glow and a slow push-in."""
    d = seg.get("seconds", 2.5)
    frames = int(d * FPS)
    crop = f"crop={seg['crop']}," if seg.get("crop") else ""
    box_w, box_h = int(W * 0.78), int(H * (0.55 if H > W else 0.62))
    y_off = int(H * 0.08) if H > W else int(H * 0.1)
    fc = (f"color=c={BG}:s={W}x{H}:d={d}:r={FPS}[bg];"
          f"[0:v]{crop}scale={box_w}:{box_h}:force_original_aspect_ratio=decrease:flags=lanczos,split[card][g];"
          f"[g]format=rgba,boxblur=40:2,colorchannelmixer=aa=0.5[glow];"
          f"[bg][glow]overlay=(W-w)/2:(H-h)/2+{y_off}[b1];[b1][card]overlay=(W-w)/2:(H-h)/2+{y_off},"
          f"zoompan=z='1+0.06*on/{frames}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={W}x{H}:fps={FPS},"
          + ",".join(["setsar=1"] + overlays(seg)) + ",format=yuv420p[v]")
    run(["ffmpeg", "-y", "-loop", "1", "-i", rel(seg["still"]), *SILENCE, "-filter_complex", fc,
         "-map", "[v]", "-map", "1:a", "-t", f"{d}", *ENC, f"s{i:02d}.mp4"])


def seg_endcard(i, card):
    d = card.get("seconds", 3.5)
    tall = H > W
    img_h = int(H * (0.5 if tall else 0.42))
    f, y = [], int(H * (0.65 if tall else 0.55))
    title_size = fit(card.get("title", ""), 104 * K, W * 0.9)
    if card.get("title"):
        f.append(f"drawtext=fontfile={font_for(card['title'])}:textfile={textfile(card['title'])}:fontsize={title_size}:"
                 f"fontcolor={TEXT}:x=(w-text_w)/2:y={y}")
        y += int(title_size * 1.35)
    for k, line in enumerate(card.get("lines", [])):
        size = fit(line, 52 * K, W * 0.9)
        f.append(f"drawtext=fontfile={font_for(line)}:textfile={textfile(line)}:fontsize={size}:"
                 f"fontcolor={ACCENT if k == 0 else TEXT}:x=(w-text_w)/2:y={y}")
        y += int(size * 1.55)
    if card.get("small"):
        size = fit(card["small"], 34 * K, W * 0.92)
        f.append(f"drawtext=fontfile={REG}:textfile={textfile(card['small'])}:fontsize={size}:fontcolor=0x9aa0a8:"
                 f"x=(w-text_w)/2:y=h-{int(H * 0.07)}")
    top = int(H * (0.1 if tall else 0.07))
    # feather the image edges so a photo's own background melts into the card colour
    fc = (f"color=c={BG}:s={W}x{H}:d={d}:r={FPS}[bg];"
          f"[0:v]scale=-2:{img_h}:flags=lanczos,format=rgba,"
          f"geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='255*min(1,min(min(X,W-X),min(Y,H-Y))/({img_h}*0.09))'[p];"
          f"[bg][p]overlay=(W-w)/2:{top},vignette=PI/4," + ",".join(f + ["fade=t=in:st=0:d=0.35", "format=yuv420p"]) + "[v]")
    run(["ffmpeg", "-y", "-loop", "1", "-i", rel(card["image"]), *SILENCE, "-filter_complex", fc,
         "-map", "[v]", "-map", "1:a", "-t", f"{d}", *ENC, f"s{i:02d}.mp4"])


def main():
    parts = []
    for i, seg in enumerate(cfg["segments"]):
        if "clip" in seg:
            seg_clip(i, seg)
        elif "still" in seg:
            seg_still(i, seg)
        elif "endcard" in seg:
            seg_endcard(i, seg["endcard"])
        else:
            raise SystemExit(f"segment {i}: needs clip, still or endcard")
        parts.append(f"s{i:02d}.mp4")
        print("segment", i, flush=True)

    name = cfg.get("output", "ad")
    tag = ratio.replace(":", "x")
    main_out = f"../out/{name}_{tag}.mp4"
    ins = sum([["-i", p] for p in parts], [])
    chain = "".join(f"[{k}:v][{k}:a]" for k in range(len(parts))) + \
        f"concat=n={len(parts)}:v=1:a=1[v][a0];[a0]loudnorm=I=-14:TP=-1.5[a]"
    run(["ffmpeg", "-y", *ins, "-filter_complex", chain, "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-crf", "20",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", main_out])
    print("wrote", os.path.normpath(os.path.join(work, main_out)))

    for r in cfg.get("exports", ["9:16", "16:9", "1:1"]):
        if r == ratio:
            continue
        w, h = SIZES[r]
        out = f"../out/{name}_{r.replace(':', 'x')}.mp4"
        fc = (f"[0:v]split[a][b];[a]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},boxblur=30:3,"
              f"eq=brightness=-0.25[bg];[b]scale={w}:{h}:force_original_aspect_ratio=decrease[fg];"
              "[bg][fg]overlay=(W-w)/2:(H-h)/2,format=yuv420p[v]")
        run(["ffmpeg", "-y", "-i", main_out, "-filter_complex", fc, "-map", "[v]", "-map", "0:a", "-c:v", "libx264",
             "-crf", "20", "-c:a", "copy", "-movflags", "+faststart", out])
        print("wrote", os.path.normpath(os.path.join(work, out)))


if __name__ == "__main__":
    main()
