"""Helpers shared by the ad scripts: the project folder, its id, references and fonts.

An ad project is one folder:

    myad/
      ad.json          the brief: product, labelled images, features, tagline, story, actor, format
      product/         the user's product images (copied in, never edited)
      refs/            product.png (product sheet), actor_<id>.png, voice_<id>.mp3
      shots.json       style + shots (keyframe prompts, clip prompts, refs, voices, timing)
      frames/          keyframe tries  <shot>_t<n>.png  + review.jpg
      takes/           rendered clips  <shot>_<take>.mp4 (+ .jpg contact sheet, leveled/ copies)
      cut.json         the edit: segments, supers, captions, end card
      out/             <name>_9x16.mp4, _16x9.mp4, _1x1.mp4
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))


def load(ad, name, default=None):
    p = os.path.join(ad, name)
    if not os.path.exists(p):
        if default is not None:
            return default
        raise SystemExit(f"{p} is missing")
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def save(ad, name, data):
    with open(os.path.join(ad, name), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def project_id(ad):
    """A random id kept in ad.json and put into every client_request_id.

    Idempotency keys are per account and permanent: two projects whose ids collide would get the
    first project's old results back instead of new renders. The id is created once and never
    changes, so resuming a project (even after moving its folder) reuses the same request ids."""
    brief = load(ad, "ad.json", {})
    if not brief.get("id"):
        slug = "".join(c if c.isalnum() else "-" for c in os.path.basename(os.path.abspath(ad)).lower())[:24]
        brief["id"] = f"{slug.strip('-') or 'ad'}-{os.urandom(3).hex()}"
        save(ad, "ad.json", brief)
    return brief["id"]


def ref_path(ad, name):
    """A reference by name: refs/<name>.png (or .jpg), or a path relative to the project."""
    for cand in (os.path.join(ad, "refs", f"{name}.png"), os.path.join(ad, "refs", f"{name}.jpg"), os.path.join(ad, name)):
        if os.path.exists(cand):
            return cand
    raise SystemExit(f"reference {name!r} not found (looked for refs/{name}.png and {name})")


def voice_path(ad, name):
    for cand in (os.path.join(ad, "refs", f"voice_{name}.mp3"), os.path.join(ad, name)):
        if os.path.exists(cand):
            return cand
    raise SystemExit(f"voice {name!r} not found (looked for refs/voice_{name}.mp3)")


def find_fonts(ad):
    """The assets/fonts folder: the project's own, or the first one found walking up."""
    d = os.path.abspath(ad)
    for _ in range(5):
        cand = os.path.join(d, "assets", "fonts")
        if os.path.isdir(cand):
            return cand
        d = os.path.dirname(d)
    raise SystemExit("no assets/fonts folder found; run: python scripts/fetch_fonts.py <project>/assets")
