---
name: portrait-gaze
description: Create an interactive portrait whose eyes follow a mouse or touch drag, from an AI-generated blank-eye portrait through measured sclera masks to a local HTML page. Use for 肖像眼神跟随、眼珠跟随鼠标、会看人的画像.
---

# Portrait Gaze · 肖像眼神跟随

Produce a blank-eye portrait, visually checked eye contours, and a working self-contained HTML. Work in a new output folder; preserve the user's original image and existing site. The helpers run locally with Python 3.10+ and Pillow; image generation uses the host's available image tool, not a bundled model or API key.

## Make or accept the portrait

Use the user's style and subject. If a suitable blank-eye image exists, use it directly. Otherwise use an available image-generation/editing tool to make a front-facing portrait with **two pale, completely empty sclera regions enclosed by dark eyelids**. No pupils, iris, glasses, hair crossing eyes, or highlights inside the white regions. Read [references/portrait-input.md](references/portrait-input.md) for a starting prompt and input limitations.

For a real person, preserve facial features using the supplied reference. Choose iris color and size from visible evidence. If the reference does not show them clearly, ask for a usable reference or label a user-approved choice as illustrative; never claim the software recovered the person's actual eye color. Do not include private reference photos in delivered public assets. For fictional characters, choose eye appearance to match the design.

If no image tool is available, ask for a prepared blank-eye portrait. Do not pretend to generate an image or silently introduce a paid service.

## Measure and inspect

Let `SKILL_DIR` be this skill folder and `OUT` the new output folder. Install once in an isolated environment:

```sh
python3 -m venv "$OUT/.venv"
"$OUT/.venv/bin/python" -m pip install -r "$SKILL_DIR/requirements.txt"
```

Read the image at its actual pixel dimensions. Using image inspection, select a seed inside each white region and a generous enclosing box around each eye. Write `regions.json` with two `eyes`, each containing `seed: [x,y]`, inclusive `box: [left,top,right,bottom]`, `iris_color: "#RRGGBB"`, and optionally `iris_radius` in source pixels and `pupil_ratio` (default 0.34). Coordinates refer to the original image, not a resized preview. The AI locates the rough regions; the script measures the pixel boundary.

```sh
"$OUT/.venv/bin/python" "$SKILL_DIR/scripts/measure.py" "$OUT/portrait.png" "$OUT/regions.json" --out "$OUT/eyes.json" --preview "$OUT/outline-check.png"
```

Open `outline-check.png` and verify both green outlines sit inside the eyelids and do not include skin or omit a large white area. The script refuses leaking regions, holes, overlapping eyes, or implausible shapes; treat these as input problems. Correct seeds/boxes first. Only adjust `min_luminance` and `max_chroma` if the actual image supports it. If the eyelids are open or whites contain pupils, regenerate/edit the image instead of fabricating a mask. Use a new output name or `--force` only for your own intermediate outputs.

## Build and test

After you have visually checked the contour, build:

```sh
"$OUT/.venv/bin/python" "$SKILL_DIR/scripts/build.py" "$OUT/portrait.png" "$OUT/eyes.json" --out "$OUT/portrait.html" --approve-outline
```

`--approve-outline` records your visual review decision for this build; do not use it to bypass inspection. The image hash prevents accidentally applying contours to a different image. Iris color and radius can be adjusted in `regions.json` and then remeasured. The program draws each iris and pupil under an SVG clipping mask. Both eyes share one movement vector.

Open the HTML in a browser. Check left and right movement, clipping at the eyelids, touch dragging on the portrait, resizing, pause, and reduced-motion behavior. Show the user the result inline when the host supports it. Deliver the HTML, source portrait, regions, measured JSON and contour-check image; explain any unverified behavior. Generating these files does not authorize modifying or deploying an existing site.

For integration, read [references/integration.md](references/integration.md). Copy only the portrait SVG, runtime and measured configuration into the intended component; keep the component's other behavior intact.
