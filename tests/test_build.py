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
        cls.collections = build.load("collections.json")
        cls.stars = build.load_stars()

    def test_real_items_valid(self):
        errors = build.validate(self.items, self.roles, self.tools, self.types, self.surfaces)
        self.assertEqual(errors, [], "\n".join(errors))

    def test_real_collections_valid(self):
        errors = build.validate_collections(self.collections)
        self.assertEqual(errors, [], "\n".join(errors))

    def test_every_role_has_items(self):
        covered = set()
        for it in self.items:
            covered.update(it["roles"])
        for r in self.roles:
            self.assertIn(r["id"], covered, f"role '{r['id']}' has no items")

    def test_repos_are_owner_slash_repo(self):
        for it in self.items + self.collections:
            if it.get("repo"):
                self.assertRegex(it["repo"], r"^[\w.-]+/[\w.-]+$", it.get("id"))

    def test_validator_catches_bad_repo(self):
        bad = json.loads(json.dumps(self.items[0]))
        bad["repo"] = "not-a-valid-repo-string"
        errors = build.validate([bad], self.roles, self.tools, self.types, self.surfaces)
        self.assertTrue(any("owner/repo" in e for e in errors))

    def test_validator_catches_bad_role(self):
        bad = json.loads(json.dumps(self.items[0]))
        bad["roles"] = ["not-a-real-role"]
        errors = build.validate([bad], self.roles, self.tools, self.types, self.surfaces)
        self.assertTrue(any("unknown role" in e for e in errors))

    def test_builtin_must_be_bool(self):
        bad = json.loads(json.dumps(self.items[0]))
        bad["built_in"] = "yes"
        errors = build.validate([bad], self.roles, self.tools, self.types, self.surfaces)
        self.assertTrue(any("built_in" in e for e in errors))

    def test_kfmt(self):
        self.assertEqual(build.kfmt(243820), "243.8k")
        self.assertEqual(build.kfmt(999), "999")
        self.assertEqual(build.kfmt(None), "")

    def test_build_writes_readme_and_site_data(self):
        build.render(self.items, self.roles, self.tools, self.types, self.surfaces,
                     self.collections, self.stars, "2026-07", self.stars.get("_generated_at", "x"))
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("AI Toolkit by Role", readme)
        self.assertIn("Where to find more", readme)
        data = json.loads((ROOT / "docs" / "data.json").read_text(encoding="utf-8"))
        self.assertEqual(len(data["items"]), len(self.items))
        self.assertIn("collections", data)
        self.assertGreater(len(data["collections"]), 5)


if __name__ == "__main__":
    unittest.main()
