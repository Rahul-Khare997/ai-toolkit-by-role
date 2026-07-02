"""Validate the data and render the README + the site's data.json.

One source of truth (data/*.json) → two outputs:
  * README.md        — categorized, beginner-friendly, generated from a template
  * docs/data.json   — the exact data the filterable website reads

Live GitHub star counts come from data/stars.json (produced by fetch_stars.py);
they are merged in at build time, so the build works offline and stars stay
optional.

Run:  python build.py          (build everything)
      python build.py --check  (validate only; used by tests/CI)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
DOCS = ROOT / "docs"
TEMPLATES = ROOT / "templates"

REQUIRED_FIELDS = {
    "id", "name", "type", "surface", "tools", "roles",
    "what", "why", "install", "docs", "official", "difficulty", "tags",
    "last_verified", "cost",
}
DIFFICULTIES = {"beginner", "intermediate", "advanced"}
REPO_RE = re.compile(r"^[\w.-]+/[\w.-]+$")


def load(name: str):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def load_stars() -> dict:
    p = DATA / "stars.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def kfmt(n) -> str:
    """Format a star count like 243820 -> '243.8k'."""
    if n is None:
        return ""
    n = int(n)
    if n >= 1000:
        return f"{n/1000:.1f}k".replace(".0k", "k")
    return str(n)


def validate(items, roles, tools, types, surfaces, costs) -> list[str]:
    errors: list[str] = []
    role_ids = {r["id"] for r in roles}
    tool_ids = {t["id"] for t in tools}
    type_ids = {t["id"] for t in types}
    surface_ids = {s["id"] for s in surfaces}
    cost_ids = {c["id"] for c in costs}
    seen_ids: set[str] = set()

    for i, it in enumerate(items):
        label = it.get("id") or it.get("name") or f"index {i}"
        missing = REQUIRED_FIELDS - it.keys()
        if missing:
            errors.append(f"[{label}] missing fields: {sorted(missing)}")
            continue
        if it["id"] in seen_ids:
            errors.append(f"[{label}] duplicate id")
        seen_ids.add(it["id"])
        if it["type"] not in type_ids:
            errors.append(f"[{label}] unknown type '{it['type']}'")
        if it["surface"] not in surface_ids:
            errors.append(f"[{label}] unknown surface '{it['surface']}'")
        if it["difficulty"] not in DIFFICULTIES:
            errors.append(f"[{label}] bad difficulty '{it['difficulty']}'")
        if not it["tools"]:
            errors.append(f"[{label}] has no tools")
        for t in it["tools"]:
            if t not in tool_ids:
                errors.append(f"[{label}] unknown tool '{t}'")
        if not it["roles"]:
            errors.append(f"[{label}] has no roles")
        for r in it["roles"]:
            if r not in role_ids:
                errors.append(f"[{label}] unknown role '{r}'")
        for k in it["install"]:
            if k not in tool_ids:
                errors.append(f"[{label}] install references unknown tool '{k}'")
            elif k not in it["tools"]:
                errors.append(f"[{label}] install mentions '{k}' but it's not in tools")
        if not str(it["docs"]).startswith("http"):
            errors.append(f"[{label}] docs is not a URL")
        for field in ("what", "why"):
            if not str(it[field]).strip():
                errors.append(f"[{label}] empty {field}")
        if "repo" in it and not REPO_RE.match(it["repo"]):
            errors.append(f"[{label}] repo '{it['repo']}' is not owner/repo")
        if "built_in" in it and not isinstance(it["built_in"], bool):
            errors.append(f"[{label}] built_in must be true/false")
        if it.get("cost") not in cost_ids:
            errors.append(f"[{label}] bad/missing cost '{it.get('cost')}'")
    return errors


def validate_collections(collections) -> list[str]:
    errors: list[str] = []
    for c in collections:
        label = c.get("id") or c.get("name") or "?"
        for f in ("id", "name", "kind", "url", "what"):
            if not c.get(f):
                errors.append(f"[collection {label}] missing {f}")
        if c.get("kind") not in {"collection", "marketplace"}:
            errors.append(f"[collection {label}] bad kind '{c.get('kind')}'")
        if "repo" in c and not REPO_RE.match(c["repo"]):
            errors.append(f"[collection {label}] repo not owner/repo")
    return errors


def compute_stats(items, roles, types, surfaces, costs):
    by_type = {t["id"]: 0 for t in types}
    by_surface = {s["id"]: 0 for s in surfaces}
    by_role = {r["id"]: 0 for r in roles}
    by_cost = {c["id"]: 0 for c in costs}
    for it in items:
        by_type[it["type"]] += 1
        by_surface[it["surface"]] += 1
        by_cost[it.get("cost", "free")] = by_cost.get(it.get("cost", "free"), 0) + 1
        for r in it["roles"]:
            by_role[r] += 1
    return {
        "total": len(items),
        "by_type": by_type, "by_surface": by_surface, "by_role": by_role, "by_cost": by_cost,
        "with_stars": sum(1 for it in items if it.get("stars")),
        "built_in": sum(1 for it in items if it.get("built_in")),
        "apps": by_type.get("app", 0),
    }


def merge_stars(rows, stars):
    for r in rows:
        if r.get("repo"):
            r["stars"] = stars.get(r["repo"])


def render(items, roles, tools, types, surfaces, costs, collections, stars, generated_at, stars_asof):
    merge_stars(items, stars)
    merge_stars(collections, stars)

    tool_by_id = {t["id"]: t for t in tools}
    type_by_id = {t["id"]: t for t in types}
    surface_by_id = {s["id"]: s for s in surfaces}
    cost_by_id = {c["id"]: c for c in costs}
    stats = compute_stats(items, roles, types, surfaces, costs)

    grouped = []
    for role in roles:
        role_items = sorted(
            [it for it in items if role["id"] in it["roles"]],
            key=lambda x: (-(x.get("stars") or 0), x["difficulty"] != "beginner", x["name"].lower()),
        )
        if role_items:
            grouped.append((role, role_items))

    coll_sorted = sorted(collections, key=lambda c: (c["kind"] != "collection", -(c.get("stars") or 0), c["name"].lower()))

    env = Environment(loader=FileSystemLoader(str(TEMPLATES)), trim_blocks=True, lstrip_blocks=True)
    env.filters["tool_label"] = lambda tid: tool_by_id.get(tid, {}).get("label", tid)
    env.filters["kfmt"] = kfmt
    template = env.get_template("README.md.j2")
    readme = template.render(
        grouped=grouped, roles=roles, tools=tools, types=types, surfaces=surfaces, costs=costs,
        collections=coll_sorted, type_by_id=type_by_id, surface_by_id=surface_by_id,
        cost_by_id=cost_by_id, tool_by_id=tool_by_id, stats=stats,
        generated_at=generated_at, stars_asof=stars_asof,
    )
    (ROOT / "README.md").write_text(readme, encoding="utf-8")

    DOCS.mkdir(exist_ok=True)
    export = {
        "generated_at": generated_at, "stars_asof": stars_asof,
        "items": items, "roles": roles, "tools": tools,
        "types": types, "surfaces": surfaces, "costs": costs,
        "collections": coll_sorted, "stats": stats,
    }
    (DOCS / "data.json").write_text(json.dumps(export, indent=2), encoding="utf-8")
    return stats


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="validate only")
    ap.add_argument("--date", default="2026-07", help="generated-on stamp")
    args = ap.parse_args(argv)

    items = load("items.json")
    roles = load("roles.json")
    tools = load("tools.json")
    types = load("types.json")
    surfaces = load("surfaces.json")
    costs = load("costs.json")
    collections = load("collections.json")
    stars = load_stars()
    stars_asof = stars.get("_generated_at", "not yet fetched")

    errors = validate(items, roles, tools, types, surfaces, costs) + validate_collections(collections)
    if errors:
        print(f"❌ {len(errors)} validation error(s):", file=sys.stderr)
        for e in errors:
            print("  -", e, file=sys.stderr)
        return 1
    print(f"✅ {len(items)} items + {len(collections)} collections valid", file=sys.stderr)
    if args.check:
        return 0

    stats = render(items, roles, tools, types, surfaces, costs, collections, stars, args.date, stars_asof)
    print(
        f"📝 README + docs/data.json written | {stats['total']} items "
        f"({stats['with_stars']} with live stars, {stats['built_in']} built-in) "
        f"across {sum(1 for v in stats['by_role'].values() if v)} roles",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
