from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tools.quotation_manager.core import (
    build_prompt,
    next_version,
    parse_ai_response,
    preview_import,
    repo_root_from,
    slugify,
)


class CoreTests(unittest.TestCase):
    def test_slugify(self):
        self.assertEqual(slugify("Personal Growth"), "personal-growth")
        self.assertEqual(slugify(" Self_control  "), "self-control")

    def test_versions(self):
        self.assertEqual(next_version("1.2.3", "patch"), "1.2.4")
        self.assertEqual(next_version("1.2.3", "minor"), "1.3.0")
        self.assertEqual(next_version("1.2.3", "major"), "2.0.0")
        self.assertEqual(next_version("1.2.3", "none"), "1.2.3")

    def test_parse_fenced_json(self):
        raw = """```json
        [{"text":"One","author":"","language":"English"}]
        ```"""
        parsed = parse_ai_response(raw)
        self.assertEqual(parsed[0]["text"], "One")

    def test_prompt_requires_output_shape(self):
        prompt = build_prompt(
            category="Wisdom",
            count=10,
            language="English",
            tone="Thoughtful",
            max_words=20,
        )
        self.assertIn('"text"', prompt)
        self.assertIn('"author"', prompt)
        self.assertIn('"language"', prompt)
        self.assertIn("Return exactly 10 items", prompt)

    def test_preview_skips_existing_and_batch_duplicates(self):
        repo_root = repo_root_from(Path(__file__))
        raw = json.dumps([
            {"text": "Silence is the sleep that nourishes wisdom.", "author": ""},
            {"text": "A totally new unit test quotation.", "author": ""},
            {"text": "A totally new unit test quotation.", "author": ""},
        ])
        preview = preview_import(repo_root, raw, "Wisdom")
        self.assertEqual(len(preview.accepted), 1)
        self.assertEqual(len(preview.duplicate_existing), 1)
        self.assertEqual(len(preview.duplicate_batch), 1)


if __name__ == "__main__":
    unittest.main()
