"""Compose the product reference sheet from the user's own images (nothing is generated).

    python product_sheet.py <ad_dir>

Reads ad.json product.images. Every image with "sheet": true goes into refs/product.png, in the
listed order, scaled to one height and set side by side (2 rows when there are more than 3) on
the background colour of the first image. Images with "sheet": "detail" go into
refs/product_detail.png the same way (close-ups of controls, labels, textures). Up to 4 per sheet:
the video model downsizes every reference to about 2048 px, so more panels means less detail each.

The sheet carries no labels or text; the views are described in words in the prompts instead
(ad.json product.images[].shows / notes).
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ad_project import load  # noqa: E402

PANEL_H = 1024
GAP = 32


def corner_colour(path):
    out = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", path, "-vf", "crop=4:4:0:0,scale=1:1,format=rgb24",
                          "-f", "rawvideo", "-"], capture_output=True).stdout
    return "0x%02x%02x%02x" % tuple(out[:3]) if len(out) >= 3 else "0xffffff"


def compose(ad, files, out):
    files = files[:4]
    bg = corner_colour(os.path.join(ad, files[0]))
    rows = [files] if len(files) <= 3 else [files[:2], files[2:]]
    inputs, chains, row_labels = [], [], []
    k = 0
    for r, row in enumerate(rows):
        labels = []
        for f in row:
            inputs += ["-i", os.path.join(ad, f)]
            # pad every panel with a gap so the views never touch
            chains.append(f"[{k}:v]scale=-2:{PANEL_H}:flags=lanczos,pad=iw+{2 * GAP}:ih+{2 * GAP}:{GAP}:{GAP}:color={bg}[p{k}]")
            labels.append(f"[p{k}]")
            k += 1
        if len(row) > 1:
            chains.append("".join(labels) + f"hstack=inputs={len(row)}[r{r}]")
        else:
            chains.append(f"{labels[0]}null[r{r}]")
        row_labels.append(f"[r{r}]")
    if len(rows) > 1:
        # rows may differ in width: pad both to the wider one
        chains.append(f"{row_labels[0]}{row_labels[1]}xstack=inputs=2:layout=0_0|0_h0:fill={bg}[s]")
    else:
        chains.append(f"{row_labels[0]}null[s]")
    chains.append(f"[s]scale='min(2048,iw)':-2:flags=lanczos[o]")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", ";".join(chains),
                    "-map", "[o]", "-frames:v", "1", out], check=True)
    print("wrote", out, f"({len(files)} views)")


def main():
    ad = sys.argv[1]
    images = load(ad, "ad.json").get("product", {}).get("images", [])
    main_views = [i["file"] for i in images if i.get("sheet") is True]
    details = [i["file"] for i in images if i.get("sheet") == "detail"]
    if not main_views:
        raise SystemExit('no image has "sheet": true in ad.json product.images')
    os.makedirs(os.path.join(ad, "refs"), exist_ok=True)
    compose(ad, main_views, os.path.join(ad, "refs", "product.png"))
    if details:
        compose(ad, details, os.path.join(ad, "refs", "product_detail.png"))


if __name__ == "__main__":
    main()
