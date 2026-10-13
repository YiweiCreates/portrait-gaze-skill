#!/usr/bin/env python3
"""Build a self-contained gaze portrait HTML from measured, visually reviewed eyes."""

import argparse
import base64
import hashlib
import html
import io
import json
import math
import re
from pathlib import Path

from PIL import Image

ASSETS = Path(__file__).resolve().parents[1] / "assets"


def number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def validate(data, image):
    if data.get("schema") != "portrait-gaze/1":
        raise ValueError("Unsupported eye data schema.")
    info = data["image"]
    w, h = image.size
    if (w, h) != (info["width"], info["height"]):
        raise ValueError("Image dimensions differ from measurement; measure again.")
    eyes = data["eyes"]
    if len(eyes) != 2:
        raise ValueError("Exactly two eyes are required.")
    for e in eyes:
        poly = e["polygon"]
        c = e["center"]
        off = e["max_offset"]
        if not isinstance(poly, list) or not 3 <= len(poly) <= 20000:
            raise ValueError("Invalid polygon length.")
        if any(
            not isinstance(p, list)
            or len(p) != 2
            or not all(number(v) for v in p)
            or not (0 <= p[0] <= w and 0 <= p[1] <= h)
            for p in poly
        ):
            raise ValueError("Polygon outside image or invalid coordinates.")
        if (
            len(c) != 2
            or not all(number(v) for v in c)
            or not (0 <= c[0] <= w and 0 <= c[1] <= h)
        ):
            raise ValueError("Invalid eye center.")
        if len(off) != 2 or not all(
            number(v) and 0 <= v <= min(w, h) * 0.1 for v in off
        ):
            raise ValueError("Invalid eye offset.")
        if not isinstance(e["iris_color"], str) or not re.fullmatch(
            "#[0-9A-Fa-f]{6}", e["iris_color"]
        ):
            raise ValueError("Invalid iris color.")
        if not number(e["iris_radius"]) or not 0 < e["iris_radius"] <= min(w, h) * 0.2:
            raise ValueError("Invalid iris radius.")
        if not number(e["pupil_ratio"]) or not 0.1 <= e["pupil_ratio"] <= 0.7:
            raise ValueError("Invalid pupil ratio.")
    if math.dist(eyes[0]["center"], eyes[1]["center"]) < 1:
        raise ValueError("Eye centers must differ.")


def build(image_path, data, title, credit, approved=False):
    raw = Path(image_path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != data["image"]["sha256"]:
        raise ValueError(
            "Portrait changed since measurement; measure the current file again."
        )
    with Image.open(io.BytesIO(raw)) as src:
        if (
            src.format not in ("PNG", "JPEG", "WEBP")
            or getattr(src, "n_frames", 1) != 1
        ):
            raise ValueError("Use a static PNG, JPEG or WebP.")
        if src.width * src.height > 20_000_000:
            raise ValueError("Image too large.")
        validate(data, src)
        im = src.convert("RGBA")
        w, h = im.size
    if not approved and data.get("review", {}).get("outline_verified") is not True:
        raise ValueError(
            "Inspect the green outline image, then pass --approve-outline or mark outline_verified true."
        )
    # Re-encode to strip EXIF/location metadata; no external URLs or SVG uploads are embedded.
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    uri = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")
    prefix = (
        "pg-"
        + hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()[:12]
    )
    defs = []
    groups = []
    for i, e in enumerate(data["eyes"]):
        d = "M" + " L".join(f"{x} {y}" for x, y in e["polygon"]) + " Z"
        cid = f"{prefix}-{i}"
        defs.append(f'<clipPath id="{cid}"><path d="{d}"/></clipPath>')
        r = e["iris_radius"]
        c = e["iris_color"]
        p = r * e["pupil_ratio"]
        x, y = e["center"]
        groups.append(
            f'<g clip-path="url(#{cid})"><g data-iris transform="translate({x} {y})"><circle r="{r}" fill="{c}" stroke="#292820" stroke-width="{r * 0.06}"/><circle r="{p}" fill="#171b19"/><circle cx="{-r * 0.26}" cy="{-r * 0.3}" r="{r * 0.09}" fill="#fff9e4" opacity=".65"/></g></g><path class="outline" d="{d}"/>'
        )
    svg = f'<svg data-gaze-portrait role="img" aria-label="{html.escape(title, quote=True)}" viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg"><defs>{"".join(defs)}</defs><image width="{w}" height="{h}" href="{uri}"/>{"".join(groups)}</svg>'
    config = {
        "eyes": [{k: e[k] for k in ["center", "max_offset"]} for e in data["eyes"]]
    }
    values = {
        "TITLE": html.escape(title),
        "CREDIT": html.escape(credit),
        "SVG": svg,
        "RUNTIME": (ASSETS / "gaze.js").read_text(encoding="utf-8"),
        "CONFIG": json.dumps(config, allow_nan=False).replace("<", "\\u003c"),
    }
    page = (ASSETS / "page.html").read_text(encoding="utf-8")
    return re.sub(
        r"__(TITLE|CREDIT|SVG|RUNTIME|CONFIG)__", lambda m: values[m[1]], page
    )


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("image", type=Path)
    p.add_argument("eyes", type=Path)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--title", default="让肖像的眼睛\n跟着你转")
    p.add_argument("--credit", default="本地交互示例 · 不上传图片，不使用摄像头")
    p.add_argument("--approve-outline", action="store_true")
    p.add_argument("--force", action="store_true")
    a = p.parse_args()
    if a.out.resolve() in (a.image.resolve(), a.eyes.resolve()):
        p.error("Output must not overwrite an input.")
    if a.out.exists() and not a.force:
        p.error("Output exists; choose a new filename or use --force.")
    try:
        page = build(
            a.image,
            json.loads(a.eyes.read_text(encoding="utf-8")),
            a.title,
            a.credit,
            a.approve_outline,
        )
    except (ValueError, OSError, KeyError, TypeError) as e:
        p.error(str(e))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(page, encoding="utf-8")
    print(f"Built {a.out}. Open locally and test left/right gaze plus touch input.")


if __name__ == "__main__":
    main()
