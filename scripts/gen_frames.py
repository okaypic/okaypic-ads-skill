"""Keyframes: one still per shot that has a "frame" in shots.json, for the user to review.

    python gen_frames.py <ad_dir> [shot ids]          # render the current try of each frame
    python gen_frames.py <ad_dir> --review            # rebuild frames/review.jpg from the latest tries
    python gen_frames.py <ad_dir> --approve 03 05     # lock the latest try as the shot's first frame
    python gen_frames.py <ad_dir> --approve 03=2      # ... or a given try

A shot's "frame" is {"prompt": ..., "take": 1, "model": "gpt-image-2", "note": ...}. The shot's
"refs" (product sheet, actor sheet, ...) go along as <Picture 1>, <Picture 2>... in that order,
the same order the clip uses. To iterate, change the frame and run again for that shot:
  - another seed of the same idea:  bump "take"
  - a correction ("the screen should face her"):  set "note" (appended to the prompt) and bump "take"
  - another model:  "model": "gpt-image-2" (default) | "nano-banana-2.1" | "gpt-image-2.5"
  - the user's own image:  copy it to frames/<id>_t<n>.png and approve that try
Every try is kept (frames/<id>_t<take>.png) and costs one image (about US$0.03).

Approved frames are set as the shot's "first_frame": the clip then starts exactly on it
(ref_mode "okay", 5-15 s clips).
"""
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ad_project import find_fonts, load, project_id, ref_path, save  # noqa: E402
from okaypic_api import data_uri, download, poll, submit_image  # noqa: E402


def rules(brief):
    """Product-agnostic rules appended to every keyframe prompt."""
    p = brief.get("product", {})
    size = f" Its real size is {p['size']}; keep that scale against hands, faces and furniture." if p.get("size") else ""
    return (f"The product must match its reference picture exactly: shape, proportions, colours, materials, controls, "
            f"labels and logos.{size} Show the side of the product that faces the camera in this moment of the action, "
            "as it looks in the matching view of the reference. Any text in the image appears only where it physically "
            "exists on the product or in the scene.")


def frame_file(ad, sid, take):
    return os.path.join(ad, "frames", f"{sid}_t{take}.png")


def latest_take(ad, sid):
    takes = [int(m.group(1)) for f in os.listdir(os.path.join(ad, "frames"))
             if (m := re.fullmatch(rf"{re.escape(sid)}_t(\d+)\.png", f))]
    return max(takes) if takes else None


def review(ad, spec):
    """frames/review.jpg: the latest try of every frame side by side, labelled "<shot> try <n>"."""
    tiles = []
    for s in spec["shots"]:
        if "frame" in s and (t := latest_take(ad, s["id"])):
            tiles.append((s["id"], t, frame_file(ad, s["id"], t)))
    if not tiles:
        return
    try:
        font = os.path.relpath(os.path.join(find_fonts(ad), "NotoSans-Bold.ttf"), ad).replace("\\", "/")
    except SystemExit:
        font = None
    inputs, chains = [], []
    for k, (sid, t, f) in enumerate(tiles):
        inputs += ["-i", os.path.relpath(f, ad)]
        label = (f",drawtext=fontfile={font}:text='{sid} try {t}':fontsize=40:fontcolor=white:box=1:boxcolor=black@0.6:"
                 "boxborderw=12:x=16:y=16") if font else ""
        chains.append(f"[{k}:v]scale=-2:900{label}[t{k}]")
    chains.append("".join(f"[t{k}]" for k in range(len(tiles))) + f"hstack=inputs={len(tiles)}[o]" if len(tiles) > 1
                  else "[t0]null[o]")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", ";".join(chains), "-map", "[o]",
                    "-frames:v", "1", os.path.join("frames", "review.jpg")], cwd=ad, check=True)
    print("review", os.path.join(ad, "frames", "review.jpg"), "-", ", ".join(f"{s} try {t}" for s, t, _ in tiles))


def main():
    args = [x for x in sys.argv[1:] if not x.startswith("--")]
    ad, ids = args[0], args[1:]
    spec = load(ad, "shots.json")
    os.makedirs(os.path.join(ad, "frames"), exist_ok=True)

    if "--approve" in sys.argv:
        for item in ids:
            sid, _, t = item.partition("=")
            take = int(t) if t else latest_take(ad, sid)
            f = frame_file(ad, sid, take) if take else None
            if not f or not os.path.exists(f):
                raise SystemExit(f"shot {sid}: no frame try {t or ''} in frames/")
            shot = next(s for s in spec["shots"] if s["id"] == sid)
            shot["first_frame"] = os.path.relpath(f, ad).replace("\\", "/")
            print(f"shot {sid}: first_frame = {shot['first_frame']}")
        save(ad, "shots.json", spec)
        return
    if "--review" in sys.argv:
        review(ad, spec)
        return

    brief = load(ad, "ad.json")
    pid = project_id(ad)
    jobs = {}
    for s in spec["shots"]:
        f = s.get("frame")
        if not f or (ids and s["id"] not in ids):
            continue
        take = f.get("take", 1)
        out = frame_file(ad, s["id"], take)
        if os.path.exists(out):
            print(f"have {s['id']} try {take} (bump frame.take for a new try)")
            continue
        prompt = " ".join(x for x in (spec.get("style", ""), f["prompt"], f.get("note", ""), rules(brief)) if x)
        body = {"model": f.get("model", "gpt-image-2"), "prompt": prompt, "ratio": spec.get("ratio", "9:16"),
                "images": [data_uri(ref_path(ad, r)) for r in s.get("refs", [])]}
        if body["model"] == "gpt-image-2.5":
            body["resolution"] = "2k"
        jobs[s["id"]] = (submit_image(body, f"{pid}-frame-{s['id']}-{take}"), out)
        print(f"submitted {s['id']} try {take} ({body['model']})", flush=True)

    for sid, (tid, out) in jobs.items():
        r = poll("image", tid)
        if r.get("status") == "completed":
            download(r["resultUrls"][0], out)
            print("done", sid, out, flush=True)
        else:
            print("FAILED", sid, r.get("errorCode"), r.get("errorMessage"), flush=True)
    review(ad, spec)


if __name__ == "__main__":
    main()
