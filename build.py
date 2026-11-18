"""Lint the design system, then write docs/tokens.css and docs/index.html.

Usage:
    python build.py          lint and build
    python build.py --check  lint only; exit code 1 if anything is wrong
"""

import sys
from pathlib import Path

from dskit.lint import lint_all
from dskit.render import page
from dskit.tokens import flatten, load_json, to_css

ROOT = Path(__file__).parent


def load():
    return (
        load_json(ROOT / "system" / "tokens.json"),
        load_json(ROOT / "system" / "components.json"),
        load_json(ROOT / "content" / "schema.json"),
        load_json(ROOT / "content" / "entries.json"),
    )


def main(argv):
    tokens, components, schema, entries = load()
    problems = lint_all(tokens, components, schema, entries)

    for p in problems:
        print("x", p)
    print(f"{len(problems)} problem(s) found")

    if "--check" in argv:
        return 1 if problems else 0

    out = ROOT / "docs"
    out.mkdir(exist_ok=True)
    (out / "tokens.css").write_text(to_css(flatten(tokens)), encoding="utf-8")
    (out / "index.html").write_text(page(tokens, components, schema, entries, problems), encoding="utf-8")
    print("wrote docs/tokens.css and docs/index.html")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
