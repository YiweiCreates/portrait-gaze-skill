# Preparing a portrait

A useful starting prompt (adapt style, appearance and aspect ratio to the user):

> A front-facing illustrated portrait of [subject], head upright, both complete eyes visible. Preserve the subject's facial proportions and expression. Each almond-shaped eye has a pale ivory white region completely enclosed by a continuous dark eyelid. Leave both white regions entirely empty: no irises, no pupils, no dots, no internal highlights. These empty eye whites will receive software-drawn irises later. No text or watermark.

This workflow is most reliable with clean illustrations. A head width of 600–1000 pixels usually leaves enough eye detail. The two white regions must be opaque and visibly separated from skin. Inspect the actual delivered image dimensions; generation tools may not return the requested size.

## What measurement does

The agent or user supplies rough boxes and interior seeds. A local flood fill selects pale, low-chroma pixels connected to each seed; the script traces their exposed pixel edges. It preserves concavities rather than replacing the eyelid with a convex hull. It does not discover faces, infer missing anatomy, or identify a person.

Optional per-eye parameters:

| Field | Meaning | Default |
| --- | --- | --- |
| `min_luminance` | Minimum pixel luminance, 0–255 | 90 |
| `max_chroma` | Maximum RGB channel spread, 0–255 | Seed patch median + 22, capped at 90 |
| `iris_color` | Chosen iris hex color | `#594330` |
| `iris_radius` | Radius in source-image pixels | 0.68 × measured eye height |
| `pupil_ratio` | Pupil radius / iris radius | 0.34 |

Strong head turns, realistic photographic texture, tinted shadows, eyelashes crossing the sclera, tiny eyes, existing pupils, and broken eyelid borders can fail. A threshold is not proof of a correct outline: always inspect the green overlay. This version supports one face with two eyes per image. It draws stylized irises and pupils; it does not reconstruct a photorealistic eye texture.
