#!/usr/bin/env python3
"""Measure two blank sclera regions from local image + rough boxes/seeds. Offline."""

import argparse
import hashlib
import json
import math
import statistics
from collections import deque
from pathlib import Path

from PIL import Image, ImageDraw


def finite(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def outline(pixels):
    """Trace exposed pixel edges, preserving the actual non-convex component boundary."""
    edges = {}
    for x, y in pixels:
        for neighbour, a, b in [
            ((x, y - 1), (x, y), (x + 1, y)),
            ((x + 1, y), (x + 1, y), (x + 1, y + 1)),
            ((x, y + 1), (x + 1, y + 1), (x, y + 1)),
            ((x - 1, y), (x, y + 1), (x, y)),
        ]:
            if neighbour not in pixels:
                if a in edges:
                    raise ValueError(
                        "Ambiguous boundary; use a cleaner blank eye image."
                    )
                edges[a] = b
    loops = []
    while edges:
        start = next(iter(edges))
        p = start
        loop = []
        while True:
            loop.append(p)
            if p not in edges:
                raise ValueError("Eye boundary is not closed.")
            p = edges.pop(p)
            if p == start:
                break
        # Remove collinear points only: never expand a concave eyelid with a convex hull.
        clean = []
        for i, q in enumerate(loop):
            a, b = loop[i - 1], loop[(i + 1) % len(loop)]
            if (q[0] - a[0]) * (b[1] - q[1]) != (q[1] - a[1]) * (b[0] - q[0]):
                clean.append(q)
        loops.append(clean)
    if len(loops) != 1:
        raise ValueError(
            "Eye contains holes or disconnected boundaries; check for existing pupils, highlights, or noise."
        )
    return [list(point) for point in loops[0]]


def measure(image_path, regions):
    with Image.open(image_path) as src:
        if src.format not in ("PNG", "JPEG", "WEBP"):
            raise ValueError("Use PNG, JPEG or WebP, not SVG or animated input.")
        if getattr(src, "n_frames", 1) != 1:
            raise ValueError("Animated images are not supported.")
        if src.width * src.height > 20_000_000:
            raise ValueError("Image too large; use at most 20 megapixels.")
        im = src.convert("RGBA")
    w, h = im.size
    px = im.load()
    if (
        not isinstance(regions, dict)
        or not isinstance(regions.get("eyes"), list)
        or len(regions["eyes"]) != 2
    ):
        raise ValueError(
            "Provide exactly two eyes with a seed and an enclosing box each."
        )
    result = []
    for spec in regions["eyes"]:
        box = spec.get("box", [])
        seed = spec.get("seed", [])
        if (
            len(box) != 4
            or len(seed) != 2
            or not all(finite(v) and int(v) == v for v in box + seed)
        ):
            raise ValueError("Box and seed must use integer source-image pixels.")
        x0, y0, x1, y1 = map(int, box)
        sx, sy = map(int, seed)
        if not (0 <= x0 < sx < x1 < w and 0 <= y0 < sy < y1 < h):
            raise ValueError("Box/seed outside image or seed not inside box.")

        def values(x, y):
            r, g, b, alpha = px[x, y]
            return 0.299 * r + 0.587 * g + 0.114 * b, max(r, g, b) - min(r, g, b), alpha

        patch = [
            values(x, y)
            for y in range(max(y0, sy - 2), min(y1, sy + 3) + 1)
            for x in range(max(x0, sx - 2), min(x1, sx + 3) + 1)
        ]
        chroma = statistics.median(v[1] for v in patch)
        lum_min = spec.get("min_luminance", 90)
        chroma_max = spec.get("max_chroma", min(90, chroma + 22))
        if not all(finite(v) and 0 <= v <= 255 for v in (lum_min, chroma_max)):
            raise ValueError("Thresholds must be between 0 and 255.")

        def ok(x, y, lum_min=lum_min, chroma_max=chroma_max):
            lum, ch, a = values(x, y)
            return a >= 240 and lum >= lum_min and ch <= chroma_max

        if not ok(sx, sy):
            raise ValueError(
                "Seed is not in a pale, opaque eye white. Move it inside the eye."
            )
        seen = {(sx, sy)}
        todo = deque([(sx, sy)])
        while todo:
            x, y = todo.popleft()
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if (
                    x0 <= nx <= x1
                    and y0 <= ny <= y1
                    and (nx, ny) not in seen
                    and ok(nx, ny)
                ):
                    seen.add((nx, ny))
                    todo.append((nx, ny))
        if any(x in (x0, x1) or y in (y0, y1) for x, y in seen):
            raise ValueError(
                "Eye white reaches the box boundary. Check the box, eyelid closure, skin leakage, and thresholds."
            )
        xs = [x for x, y in seen]
        ys = [y for x, y in seen]
        ew = max(xs) + 1 - min(xs)
        eh = max(ys) + 1 - min(ys)
        if len(seen) < 20 or not (1.2 <= ew / eh <= 8):
            raise ValueError(
                "Implausible eye component; inspect the image, seed and box."
            )
        poly = outline(seen)
        color = spec.get("iris_color", "#594330")
        radius = spec.get("iris_radius", round(eh * 0.68, 3))
        pupil = spec.get("pupil_ratio", 0.34)
        if not finite(radius) or not 0 < radius <= ew / 2:
            raise ValueError(
                "Iris radius must be positive and no larger than half the eye width."
            )
        if not finite(pupil) or not 0.1 <= pupil <= 0.7:
            raise ValueError("Pupil ratio must be 0.1–0.7.")
        import re

        if not isinstance(color, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
            raise ValueError("Iris color must be #RRGGBB.")
        result.append(
            {
                "polygon": poly,
                "center": [(min(xs) + max(xs) + 1) / 2, (min(ys) + max(ys) + 1) / 2],
                "width": ew,
                "height": eh,
                "iris_radius": radius,
                "iris_color": color,
                "pupil_ratio": pupil,
                "max_offset": [
                    min(ew * 0.15, radius * 0.50),
                    min(eh * 0.12, radius * 0.20),
                ],
                "measurement": {
                    "pixels": len(seen),
                    "box": box,
                    "seed": seed,
                    "min_luminance": lum_min,
                    "max_chroma": chroma_max,
                },
            }
        )
    if set(map(tuple, result[0]["polygon"])) & set(map(tuple, result[1]["polygon"])):
        raise ValueError("Eye regions overlap.")
    result.sort(key=lambda e: e["center"][0])
    if math.dist(result[0]["center"], result[1]["center"]) < max(
        e["width"] for e in result
    ):
        raise ValueError(
            "The two eye measurements overlap or are too close; check seeds."
        )
    return {
        "schema": "portrait-gaze/1",
        "image": {
            "width": w,
            "height": h,
            "sha256": hashlib.sha256(Path(image_path).read_bytes()).hexdigest(),
        },
        "eyes": result,
        "review": {
            "outline_verified": False,
            "likeness_verified": False,
            "note": "Review green outlines visually before approving; eye color/radius are selected parameters, not measured identity evidence.",
        },
    }


def save_preview(image_path, data, destination):
    im = Image.open(image_path).convert("RGB")
    d = ImageDraw.Draw(im)
    for e in data["eyes"]:
        d.line(
            [tuple(v) for v in e["polygon"]] + [tuple(e["polygon"][0])],
            fill=(0, 230, 110),
            width=max(2, im.width // 500),
        )
    im.save(destination)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("image", type=Path)
    p.add_argument("regions", type=Path)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--preview", type=Path, required=True)
    p.add_argument("--force", action="store_true")
    a = p.parse_args()
    if a.out.resolve() == a.preview.resolve() or any(
        x.resolve() in (a.image.resolve(), a.regions.resolve())
        for x in [a.out, a.preview]
    ):
        p.error("Outputs must be distinct from each other and from inputs.")
    if not a.force and any(x.exists() for x in [a.out, a.preview]):
        p.error("Output exists; select new filenames or use --force.")
    try:
        data = measure(a.image, json.loads(a.regions.read_text(encoding="utf-8")))
    except (ValueError, OSError, KeyError, TypeError) as e:
        p.error(str(e))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.preview.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    save_preview(a.image, data, a.preview)
    print("Measured both eyes. Inspect the green outlines before building.")


if __name__ == "__main__":
    main()
