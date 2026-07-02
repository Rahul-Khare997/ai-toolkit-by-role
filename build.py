"""Validate the data and render the README + the site's data.json.

One source of truth (data/*.json) → two outputs:
  * README.md        — categorized, beginner-friendly, generated from a template
  * docs/data.json   — the exact data the filterable website reads

Run:  python build.py          (build everything)
      python build.py --check  (validate only; used by tests/CI)
"""
from __future__ import annotations

import argparse
import json
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
    "last_verified",
}
DIFFICULTIES = {"beginner", "intermediate", "advanced"}


def load(name: str):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def validate(items, roles, tools, types, surfaces) -> list[str]:
    """Return a list of human-readable problems (empty = valid)."""
    errors: list[str] = []
    role_ids = {r["id"] for r in roles}
    tool_ids = {t["id"] for t in tools}
    type_ids = {t["id"] for t in types}
    surface_ids = {s["id"] for s in surfaces}
    seen_ids: set[str] = set()

    for i, it in enumerate(items):
        label = it.get("id") or it.get("name") or f"index {i}"

        missing = REQUIRED_FIELDS - it.keys()
        if missing:
            errors.append(f"[{label}] missing fields: {sorted(missing)}")
            continue  # can't validate further without the fields

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

        # install keys must be tools that also appear in the item's tool list
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

    return errors


def compute_stats(items, roles, types, surfaces):
    by_type = {t["id"]: 0 for t in types}
    by_surface = {s["id"]: 0 for s in surfaces}
    by_role = {r["id"]: 0 for r in roles}
    for it in items:
        by_type[it["type"]] += 1
        by_surface[it["surface"]] += 1
        for r in it["roles"]:
            by_role[r] += 1
    return {"total": len(items), "by_type": by_type, "by_surface": by_surface, "by_role": by_role}


def render(items, roles, tools, types, surfaces, generated_at: str):
    tool_by_id = {t["id"]: t for t in tools}
    type_by_id = {t["id"]: t for t in types}
    surface_by_id = {s["id"]: s for s in surfaces}
    stats = compute_stats(items, roles, types, surfaces)

    # group items under each role, preserving role order
    grouped = []
    for role in roles:
        role_items = sorted(
            [it for it in items if role["id"] in it["roles"]],
            key=lambda x: (x["difficulty"] != "beginner", x["name"].lower()),
        )
        if role_items:
            grouped.append((role, role_items))

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES)), trim_blocks=True, lstrip_blocks=True
    )
    env.filters["tool_label"] = lambda tid: tool_by_id.get(tid, {}).get("label", tid)
    template = env.get_template("README.md.j2")
    readme = template.render(
        grouped=grouped, roles=roles, tools=tools, types=types, surfaces=surfaces,
        type_by_id=type_by_id, surface_by_id=surface_by_id, tool_by_id=tool_by_id,
        stats=stats, generated_at=generated_at,
    )
    (ROOT / "README.md").write_text(readme, encoding="utf-8")

    # site data
    DOCS.mkdir(exist_ok=True)
    export = {
        "generated_at": generated_at,
        "items": items, "roles": roles, "tools": tools,
        "types": types, "surfaces": surfaces, "stats": stats,
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

    errors = validate(items, roles, tools, types, surfaces)
    if errors:
        print(f"❌ {len(errors)} validation error(s):", file=sys.stderr)
        for e in errors:
            print("  -", e, file=sys.stderr)
        return 1
    print(f"✅ {len(items)} items valid", file=sys.stderr)

    if args.check:
        return 0

    stats = render(items, roles, tools, types, surfaces, args.date)
    print(
        f"📝 README + docs/data.json written | "
        f"{stats['total']} items across {sum(1 for v in stats['by_role'].values() if v)} roles",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
