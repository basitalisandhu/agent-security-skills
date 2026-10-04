#!/usr/bin/env python3
"""Tests for the frontmatter scalar check in validate_plugin.py (run by scripts/run_tests.py)."""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("validate_plugin_under_test", ROOT / "scripts" / "validate_plugin.py")
validator = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(validator)


def doc(*lines: str) -> str:
    return "---\n" + "\n".join(lines) + "\n---\n\nBody: text with a colon is fine.\n"


class ScalarProblemsTest(unittest.TestCase):
    def test_plain_scalar_with_colon_space_is_rejected(self):
        problems = validator.scalar_problems(doc("name: x", "description: Set up evaluations: benign and attack tasks"))
        self.assertEqual(len(problems), 1)
        self.assertIn("line 3", problems[0])
        self.assertIn("'description'", problems[0])

    def test_plain_scalar_with_space_hash_is_rejected(self):
        self.assertEqual(len(validator.scalar_problems(doc("description: Use for C # code"))), 1)

    def test_plain_scalar_with_trailing_colon_or_indicator_is_rejected(self):
        self.assertEqual(len(validator.scalar_problems(doc("description: Ends with:"))), 1)
        self.assertEqual(len(validator.scalar_problems(doc("description: *starts with an alias"))), 1)
        self.assertEqual(len(validator.scalar_problems(doc("description: @mention first"))), 1)

    def test_nested_metadata_values_are_checked(self):
        problems = validator.scalar_problems(doc("name: x", "metadata:", "  note: has: a colon"))
        self.assertEqual(len(problems), 1)
        self.assertIn("line 4", problems[0])

    def test_unclosed_quoted_scalar_is_rejected(self):
        self.assertEqual(len(validator.scalar_problems(doc('description: "never closed'))), 1)
        self.assertEqual(len(validator.scalar_problems(doc("description: 'never closed"))), 1)
        self.assertEqual(len(validator.scalar_problems(doc('description: "ends with an escaped quote\\"'))), 1)

    def test_accepted_forms(self):
        for line in (
            'description: "Quoted: with a colon # and a hash"',
            "description: 'Single: quoted'",
            "description: Plain text, a URL https://example.com/a:b and a#b",
            "description: C:\\path\\to",
            "description: >-",
            "allowed-tools: [Read, Grep]",
            "name: plain-name",
        ):
            self.assertEqual(validator.scalar_problems(doc(line)), [], line)

    def test_block_scalar_content_is_not_checked(self):
        self.assertEqual(validator.scalar_problems(doc("description: |", "  Text: with a colon", "name: x")), [])

    def test_text_without_frontmatter_is_ignored(self):
        self.assertEqual(validator.scalar_problems("description: a: b\n"), [])

    def test_every_skill_in_this_repository_parses_cleanly(self):
        skills = sorted((ROOT / "plugins").glob("*/skills/*/SKILL.md"))
        self.assertTrue(skills)
        for path in skills:
            with self.subTest(skill=str(path.relative_to(ROOT))):
                self.assertEqual(validator.scalar_problems(path.read_text(encoding="utf-8")), [])


if __name__ == "__main__":
    unittest.main()
