"""On-camera actors: okaypic's preset AI actors, or the user's own photo / voice.

    python actors.py list                                   # presets: id, look, voices
    python actors.py use <ad_dir> <id> [--lang en]          # preset -> refs/actor_<id>.png + refs/voice_<id>.mp3
    python actors.py custom <ad_dir> <name> --photo me.jpg [--look "..."] [--voice me.mp3]
    python actors.py custom <ad_dir> <name> --look "a woman in her 40s ..."     # describe, no photo

Presets are purely AI-generated people (no likeness of anyone real), each with a reference sheet
(face close-ups + front/side/back full body) and one fixed voice per language (en / zh / ja), so
an actor looks and sounds the same in every ad. The list comes from GET /api/actors (free).

`custom` draws a reference sheet through the API (one image, about US$0.03) from a photo and/or a
description. A custom voice is the user's own recording (3-15 s of clean speech, MP3/WAV/M4A); it
is trimmed to 10 s and used as the voice-timbre reference, like the presets' voices.
Only use photos or voices of people who agreed to it.
"""
import argparse
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ad_project import project_id  # noqa: E402
from okaypic_api import data_uri, download, poll, request, submit_image  # noqa: E402


def presets():
    code, r = request("GET", "/api/actors")
    if code != 200:
        raise SystemExit(f"could not list actors: http {code} {r}")
    return r["actors"]


def sheet_prompt(look, with_ref):
    ref = (" The reference photo shows this exact person: keep the same face, skin, hair, outfit and accessories in every view."
           if with_ref else "")
    return re.sub(r"\s+", " ", (
        "A character reference sheet, 16:9 landscape, seamless pure white background, soft even studio lighting. "
        "Left column, two stacked panels: top, a front-facing head-and-shoulders close-up at eye level, calm neutral "
        "expression, lips closed, looking into the camera; bottom, a strict 90-degree side-profile close-up of the same face. "
        "Right side, three full-body views standing side by side: front, strict 90-degree side, and back, whole person "
        "from head to shoes, same scale and light, arms relaxed at the sides. "
        f"The person: {look}. Identical outfit, hairstyle and accessories in every view. One single person shown "
        f"from several angles, the only subject in the image.{ref} A photorealistic commercial look. "
        "Clean frame containing only the depicted subject."
    )).strip()


def trim_voice(src, dst):
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", src],
                               capture_output=True, text=True).stdout.strip() or 0)
    if not 3 <= dur <= 60:
        raise SystemExit(f"the voice sample is {dur:.1f} s; use 3-15 s of clean speech")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-t", "10", "-ac", "1", "-ar", "44100",
                    "-af", "loudnorm=I=-16:TP=-1.5", "-b:a", "128k", dst], check=True)
    print("voice", dst, f"({min(dur, 10):.1f} s)")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    u = sub.add_parser("use")
    u.add_argument("ad"); u.add_argument("id"); u.add_argument("--lang", default="en")
    c = sub.add_parser("custom")
    c.add_argument("ad"); c.add_argument("name")
    c.add_argument("--photo"); c.add_argument("--look", default=""); c.add_argument("--voice")
    c.add_argument("--model", default="gpt-image-2"); c.add_argument("--take", type=int, default=1)
    a = ap.parse_args()

    if a.cmd == "list":
        for p in presets():
            print(f"{p['id']:8} {p['name']:7} {p['gender']} {p['age']:10} {p['look']}")
            print(f"{'':8} sheet {p['sheet']}  voices: {', '.join(p['voices'])}")
        return

    refs = os.path.join(a.ad, "refs")
    os.makedirs(refs, exist_ok=True)
    if a.cmd == "use":
        p = next((x for x in presets() if x["id"] == a.id), None)
        if not p:
            raise SystemExit(f"no preset actor {a.id!r}; see: python actors.py list")
        download(p["sheet"], os.path.join(refs, f"actor_{a.id}.png"))
        v = p["voices"].get(a.lang)
        if v:
            download(v["cut"]["10"], os.path.join(refs, f"voice_{a.id}.mp3"))
        print(f"actor {a.id}: refs/actor_{a.id}.png" + (f", voice refs/voice_{a.id}.mp3 ({a.lang})" if v else
                                                         f" (no {a.lang} voice; H3 will pick one)"))
        return

    # custom actor
    if not a.photo and not a.look:
        raise SystemExit("give --photo and/or --look")
    body = {"model": a.model, "ratio": "16:9", "prompt": sheet_prompt(a.look or "the person in the reference photo", bool(a.photo))}
    if a.photo:
        body["images"] = [data_uri(a.photo)]
    tid = submit_image(body, f"{project_id(a.ad)}-actor-{a.name}-{a.take}")
    r = poll("image", tid)
    if r.get("status") != "completed":
        raise SystemExit(f"sheet failed: {r.get('errorCode')} {r.get('errorMessage')}")
    print("sheet", download(r["resultUrls"][0], os.path.join(refs, f"actor_{a.name}.png")))
    if a.voice:
        trim_voice(a.voice, os.path.join(refs, f"voice_{a.name}.mp3"))


if __name__ == "__main__":
    main()
