#!/usr/bin/env python3
"""Every skill README sample must match what its script prints today (run by scripts/run_tests.py).

The commands live in scripts/readme_samples.py; refresh the READMEs with `python3 scripts/readme_samples.py --write`.
"""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("readme_samples_under_test", ROOT / "scripts" / "readme_samples.py")
samples = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(samples)


class ReadmeSamplesTest(unittest.TestCase):
    def test_every_skill_has_a_readme(self):
        for skill in sorted(p.name for p in (ROOT / samples.SK).iterdir() if (p / "SKILL.md").is_file()):
            self.assertTrue((ROOT / samples.SK / skill / "README.md").is_file(), skill)

    def test_samples_match_the_scripts(self):
        for skill in samples.SAMPLES:
            with self.subTest(skill=skill):
                text = samples.readme(skill).read_text(encoding="utf-8")
                block = samples.BLOCK.search(text)
                self.assertIsNotNone(block, f"{skill}/README.md has no sample block")
                self.assertEqual(block.group(2), samples.render(skill),
                                 f"{skill}/README.md sample is stale: run python3 scripts/readme_samples.py --write")


if __name__ == "__main__":
    unittest.main()
