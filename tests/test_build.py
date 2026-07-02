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
        cls.costs = build.load("costs.json")
        cls.collections = build.load("collections.json")
        cls.stars = build.load_stars()

    def _validate(self, items):
        return build.validate(items, self.roles, self.tools, self.types, self.surfaces, self.costs)

    def test_real_items_valid(self):
        self.assertEqual(self._validate(self.items), [])

    def test_real_collections_valid(self):
        self.assertEqual(build.validate_collections(self.collections), [])

    def test_every_role_has_items(self):
        covered = set()
        for it in self.items:
            covered.update(it["roles"])
        for r in self.roles:
            self.assertIn(r["id"], covered, f"role '{r['id']}' has no items")

    def test_thin_roles_are_deeper_now(self):
        by_role = {}
        for it in self.items:
            for r in it["roles"]:
                by_role[r] = by_role.get(r, 0) + 1
        for role in ("legal", "healthcare", "video-creator", "graphic-designer"):
            self.assertGreaterEqual(by_role.get(role, 0), 8, f"{role} still thin")

    def test_apps_exist_and_are_standalone(self):
        apps = [i for i in self.items if i["type"] == "app"]
        self.assertGreaterEqual(len(apps), 20)
        for a in apps:
            self.assertEqual(a["surface"], "standalone")
            self.assertEqual(a["tools"], ["standalone"])
            self.assertIn("standalone", a["install"])

    def test_every_item_has_valid_cost(self):
        cost_ids = {c["id"] for c in self.costs}
        for it in self.items:
            self.assertIn(it.get("cost"), cost_ids, it.get("id"))

    def test_repos_are_owner_slash_repo(self):
        for it in self.items + self.collections:
            if it.get("repo"):
                self.assertRegex(it["repo"], r"^[\w.-]+/[\w.-]+$", it.get("id"))

    def test_validator_catches_bad_cost(self):
        bad = json.loads(json.dumps(self.items[0])); bad["cost"] = "cheapish"
        self.assertTrue(any("cost" in e for e in self._validate([bad])))

    def test_validator_catches_bad_role(self):
        bad = json.loads(json.dumps(self.items[0])); bad["roles"] = ["nope"]
        self.assertTrue(any("unknown role" in e for e in self._validate([bad])))

    def test_kfmt(self):
        self.assertEqual(build.kfmt(243820), "243.8k")
        self.assertEqual(build.kfmt(999), "999")
        self.assertEqual(build.kfmt(None), "")

    def test_build_writes_readme_and_site_data(self):
        build.render(self.items, self.roles, self.tools, self.types, self.surfaces, self.costs,
                     self.collections, self.stars, "2026-07", self.stars.get("_generated_at", "x"))
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("AI Toolkit by Role", readme)
        self.assertIn("Cost", readme)
        data = json.loads((ROOT / "docs" / "data.json").read_text(encoding="utf-8"))
        self.assertEqual(len(data["items"]), len(self.items))
        self.assertIn("costs", data)
        self.assertIn("by_cost", data["stats"])


if __name__ == "__main__":
    unittest.main()
