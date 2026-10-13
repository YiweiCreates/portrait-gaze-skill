import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]


def module(name):
    spec = importlib.util.spec_from_file_location(
        name, ROOT / "portrait-gaze/scripts" / f"{name}.py"
    )
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


measure = module("measure")
build = module("build")


class Pipeline(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.p = Path(self.tmp.name) / "portrait.png"
        im = Image.new("RGB", (240, 120), "#c98652")
        d = ImageDraw.Draw(im)
        d.ellipse((35, 45, 85, 65), fill="#fff9ee", outline="#222222", width=2)
        d.ellipse((145, 45, 195, 65), fill="#fff9ee", outline="#222222", width=2)
        im.save(self.p)
        self.regions = {
            "eyes": [
                {"seed": [60, 55], "box": [25, 35, 95, 75]},
                {"seed": [170, 55], "box": [135, 35, 205, 75]},
            ]
        }

    def test_end_to_end_mask_inside_whites(self):
        data = measure.measure(self.p, self.regions)
        self.assertEqual(len(data["eyes"]), 2)
        for e in data["eyes"]:
            self.assertGreater(e["measurement"]["pixels"], 200)
            mask = Image.new("1", (240, 120))
            ImageDraw.Draw(mask).polygon([tuple(p) for p in e["polygon"]], fill=1)
            self.assertFalse(mask.getpixel((20, 20)))
        self.assertRaises(ValueError, build.build, self.p, data, "test", "credit")
        page = build.build(self.p, data, "<script>alert(1)</script>", "__SVG__", True)
        self.assertIn("&lt;script&gt;", page)
        self.assertNotIn("<script>alert(1)</script>", page)
        self.assertIn("data:image/png;base64", page)
        self.assertEqual(page.count("data-iris transform="), 2)
        self.assertIn("__SVG__", page)

    def test_concavity_retained(self):
        pixels = {(x, y) for x in range(8) for y in range(5) if not (x < 3 and y < 2)}
        poly = measure.outline(pixels)
        self.assertIn([3, 2], poly)
        area = (
            abs(
                sum(
                    a[0] * b[1] - a[1] * b[0] for a, b in zip(poly, poly[1:] + poly[:1])
                )
            )
            / 2
        )
        self.assertEqual(area, len(pixels))

    def test_existing_pupil_rejected(self):
        im = Image.open(self.p)
        ImageDraw.Draw(im).ellipse((57, 52, 63, 58), fill="black")
        im.save(self.p)
        self.regions["eyes"][0]["seed"] = [45, 55]
        self.assertRaises(ValueError, measure.measure, self.p, self.regions)

    def test_leaking_region_rejected(self):
        self.regions["eyes"][0]["box"] = [50, 50, 80, 63]
        self.assertRaises(ValueError, measure.measure, self.p, self.regions)

    def test_duplicate_eye_rejected(self):
        self.regions["eyes"][1] = copy.deepcopy(self.regions["eyes"][0])
        self.assertRaises(ValueError, measure.measure, self.p, self.regions)

    def test_image_hash_prevents_wrong_mask(self):
        data = measure.measure(self.p, self.regions)
        im = Image.open(self.p)
        im.putpixel((0, 0), (0, 0, 0))
        im.save(self.p)
        self.assertRaises(ValueError, build.build, self.p, data, "", "", True)

    def test_untrusted_numeric_and_color_data(self):
        data = measure.measure(self.p, self.regions)
        for key, value in [
            ("iris_color", 'red" onload="alert(1)'),
            ("center", [float("nan"), 2]),
            ("max_offset", [999, 2]),
            ("pupil_ratio", True),
        ]:
            bad = copy.deepcopy(data)
            bad["eyes"][0][key] = value
            self.assertRaises(ValueError, build.build, self.p, bad, "", "", True)

    def test_cli_cannot_overwrite_input_even_with_force(self):
        data = measure.measure(self.p, self.regions)
        j = self.p.with_suffix(".json")
        j.write_text(json.dumps(data))
        before = self.p.read_bytes()
        proc = subprocess.run(
            [
                sys.executable,
                str(ROOT / "portrait-gaze/scripts/build.py"),
                str(self.p),
                str(j),
                "--out",
                str(self.p),
                "--force",
                "--approve-outline",
            ],
            capture_output=True,
            check=False,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(before, self.p.read_bytes())

    def test_packaged_example_rebuilds(self):
        data = measure.measure(
            ROOT / "examples/portrait-blank.png",
            json.loads((ROOT / "examples/regions.json").read_text()),
        )
        page = build.build(ROOT / "examples/portrait-blank.png", data, "Demo", "", True)
        self.assertIn("PortraitGaze.mount", page)


if __name__ == "__main__":
    unittest.main()
