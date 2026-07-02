"""Tests for the data model and build. Run: python -m unittest discover -s tests -v"""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import build  # noqa: E402


class TestData(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.items = build.load("items.json")
        cls.roles = build.load("roles.json")
        cls.tools = build.load("tools.json")
        cls.types = build.load("types.json")
        cls.surfaces = build.load("surfaces.json")

    def test_real_data_is_valid(self):
        errors = build.validate(self.items, self.roles, self.tools, self.types, self.surfaces)
        self.assertEqual(errors, [], "data/items.json has validation errors:\n" + "\n".join(errors))

    def test_every_role_has_at_least_one_item(self):
        covered = set()
        for it in self.items:
            covered.update(it["roles"])
        for r in self.roles:
            self.assertIn(r["id"], covered, f"role '{r['id']}' has no items")

    def test_must_have_role_populated(self):
        must = [it for it in self.items if "must-have" in it["roles"]]
        self.assertGreaterEqual(len(must), 3)

    def test_validator_catches_bad_role(self):
        bad = json.loads(json.dumps(self.items[0]))
        bad["roles"] = ["not-a-real-role"]
        errors = build.validate([bad], self.roles, self.tools, self.types, self.surfaces)
        self.assertTrue(any("unknown role" in e for e in errors))

    def test_validator_catches_missing_field(self):
        bad = json.loads(json.dumps(self.items[0]))
        del bad["why"]
        errors = build.validate([bad], self.roles, self.tools, self.types, self.surfaces)
        self.assertTrue(any("missing fields" in e for e in errors))

    def test_validator_catches_install_tool_mismatch(self):
        bad = json.loads(json.dumps(self.items[0]))
        bad["install"] = {"cursor": "x"}
        bad["tools"] = ["claude-code"]  # cursor not in tools
        errors = build.validate([bad], self.roles, self.tools, self.types, self.surfaces)
        self.assertTrue(any("install" in e for e in errors))

    def test_build_writes_readme_and_site_data(self):
        build.render(self.items, self.roles, self.tools, self.types, self.surfaces, "2026-07")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("AI Toolkit by Role", readme)
        self.assertIn("Must-have for everyone", readme)
        data = json.loads((ROOT / "docs" / "data.json").read_text(encoding="utf-8"))
        self.assertEqual(len(data["items"]), len(self.items))
        self.assertIn("stats", data)


if __name__ == "__main__":
    unittest.main()
