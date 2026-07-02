"""Fetch live GitHub star counts for every repo referenced in the data.

Writes data/stars.json:  { "owner/repo": 12345, ..., "_generated_at": "2026-07-02" }

Reads GITHUB_TOKEN from the environment if present (higher rate limit). Failures
are non-fatal: a repo that can't be fetched keeps its previously-cached value, so
a transient API hiccup never wipes the numbers.

Run:  python fetch_stars.py [--date YYYY-MM-DD]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
STARS = DATA / "stars.json"


def referenced_repos() -> set[str]:
    repos: set[str] = set()
    for fname in ("items.json", "collections.json"):
        for row in json.loads((DATA / fname).read_text(encoding="utf-8")):
            if row.get("repo"):
                repos.add(row["repo"])
    return repos


def fetch_one(repo: str, token: str | None) -> int | None:
    req = urllib.request.Request(f"https://api.github.com/repos/{repo}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "ai-toolkit-by-role-star-fetcher")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return int(json.load(resp)["stargazers_count"])
    except (urllib.error.URLError, KeyError, ValueError) as e:
        sys.stderr.write(f"  !! {repo}: {e}\n")
        return None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default="2026-07", help="stamp for _generated_at")
    args = ap.parse_args(argv)

    token = os.environ.get("GITHUB_TOKEN")
    previous = {}
    if STARS.exists():
        previous = json.loads(STARS.read_text(encoding="utf-8"))

    stars: dict[str, int] = {}
    for repo in sorted(referenced_repos()):
        n = fetch_one(repo, token)
        if n is None and repo in previous:
            n = previous[repo]  # keep last known value on failure
        if n is not None:
            stars[repo] = n
            sys.stderr.write(f"  {repo}: {n:,}\n")

    stars["_generated_at"] = args.date
    STARS.write_text(json.dumps(stars, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"[stars] wrote {len(stars) - 1} repos to {STARS.relative_to(ROOT)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
