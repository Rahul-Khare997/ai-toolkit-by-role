# Contributing

This directory is only useful if it's **accurate and beginner-friendly**. That's the bar.

## Add or update a tool

1. Edit [`data/items.json`](data/items.json) and add an entry:

```json
{
  "id": "unique-kebab-id",
  "name": "Human Name",
  "type": "connector",              // skill | connector | plugin | rule | extension
  "surface": "both",                // chat | code | both
  "tools": ["claude-code", "cursor"],
  "roles": ["software-developer"],  // one or more role ids from data/roles.json
  "what": "One plain-English sentence: what it does.",
  "why": "One sentence a beginner understands: why you'd want it.",
  "install": { "claude-code": "short step", "cursor": "short step" },
  "docs": "https://official-docs-url",
  "official": true,
  "difficulty": "beginner",         // beginner | intermediate | advanced
  "tags": ["a", "b"],
  "last_verified": "2026-07"
}
```

2. Rebuild and validate:

```bash
python build.py            # regenerates README.md + docs/data.json
python -m unittest discover -s tests -v
```

The build **fails** if anything is invalid (unknown role/tool/type, missing field, or an `install` step naming a tool that isn't in `tools`). Fix it until it's green.

## Rules that keep this trustworthy

- **Write for a beginner.** No unexplained jargon in `what`/`why`. Imagine someone who just installed their first AI app.
- **Accuracy over hype.** `official: true` only for first-party tools. Point `docs` at the real source. Set `surface` honestly — many connectors work in chat apps but not (yet) in a given coding agent, and vice-versa.
- **Least privilege.** If a connector touches sensitive data, say "read-only" in the install step.
- **Keep `last_verified` current** when you touch an entry.

## Add a new role or tool

Add it to `data/roles.json` or `data/tools.json` (follow the existing shape), then map items to it. Don't leave a role with zero items — the tests check for that.
