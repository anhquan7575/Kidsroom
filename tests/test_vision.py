import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

from kidsroom.vision import CompletionGate, load_template, match_score


class VisionTests(unittest.TestCase):
    def test_requires_fresh_completion_and_three_consecutive_matches(self):
        gate = CompletionGate(0.9)
        for _ in range(5):
            self.assertFalse(gate.observe(1.0))
        self.assertFalse(gate.observe(0.1))
        self.assertFalse(gate.observe(0.95))
        self.assertFalse(gate.observe(0.95))
        self.assertTrue(gate.observe(0.95))

    def test_other_foreground_window_resets_stability_not_baseline(self):
        gate = CompletionGate(0.9)
        for score in (None, 0.1, 0.95, 0.95, None, 0.95, 0.95):
            self.assertFalse(gate.observe(score))
        self.assertTrue(gate.observe(0.95))

    def test_actual_template_matching_and_size_guard(self):
        rng = np.random.default_rng(42)
        frame = rng.integers(0, 256, (150, 200), dtype=np.uint8)
        template = frame[20:50, 30:70].copy()
        self.assertGreater(match_score(frame, template), 0.99)
        self.assertLess(match_score(np.zeros_like(frame), template), 0.9)
        self.assertEqual(match_score(frame[:10, :10], template), 0)

    def test_template_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "template.png"
            path.write_bytes(b"not an image")
            with self.assertRaises(ValueError):
                load_template(str(path))
            for image in (np.zeros((20, 20), dtype=np.uint8),
                          np.arange(100, dtype=np.uint8).reshape(10, 10)):
                path.write_bytes(cv2.imencode(".png", image)[1].tobytes())
                with self.assertRaises(ValueError):
                    load_template(str(path))
            image = np.random.default_rng(5).integers(0, 256, (30, 30), dtype=np.uint8)
            path.write_bytes(cv2.imencode(".png", image)[1].tobytes())
            np.testing.assert_array_equal(load_template(str(path)), image)


if __name__ == "__main__":
    unittest.main()
