# content-design-system

A small design system where the design tokens, the component library and the content database are checked against each other, so they stay consistent as any one of them changes.

The sample content is a set of patient education topics. It is placeholder text, not medical advice.

Live library page: https://rafay-07.github.io/content-design-system/

## The problem it solves

In a product team, three things drift apart:

1. **Design tokens** (colours, type sizes, spacing) get renamed or added without a naming rule.
2. **Components** get bound to content fields that were later renamed, or get a colour pair nobody checked for contrast.
3. **Content** in a database (Notion, a CMS) gains a new option, such as a new specialty, that no component variant knows how to show.

This repo keeps all three in plain JSON files and runs one linter across them.

## How it is organised

| File | What it holds |
|---|---|
| `system/tokens.json` | Tokens in the W3C Design Tokens format (`$value`, `$type`). Base colours plus semantic aliases such as `text.default` and `surface.brand` |
| `system/components.json` | Components, their variants (which background and text tokens each uses) and their slots (which content property each slot shows) |
| `content/schema.json` | The content database schema, modelled on Notion property types: title, rich_text, select, status, relation, date |
| `content/entries.json` | Rows in that database |
| `dskit/` | Python code: token resolution, the linter and the page renderer |
| `docs/` | Generated `tokens.css` and `index.html` (the library page) |

## What the linter checks

- **Naming:** every token, component and variant name is lowercase words joined by hyphens (`primary-dark`, `on-brand`).
- **Aliases:** every alias such as `{color.neutral.0}` points at a real token, with no loops.
- **Contrast:** every variant's text and background pair meets WCAG 2.x AA (4.5:1).
- **Slot bindings:** every component slot points at a schema property that exists and has a type the slot accepts.
- **Option coverage:** `specialty-badge` must have exactly one variant per `Specialty` option. Adding "Mental Health" to the schema fails the build until a badge variant exists for it.
- **Content rows:** required fields present, select and status values valid, relations point at real rows, dates in `YYYY-MM-DD`, text within length limits.

## Run it

Python 3.10 or newer, no dependencies for the build. pytest for the tests.

```bash
python build.py          # lint, then write docs/tokens.css and docs/index.html
python build.py --check  # lint only, exit code 1 on any problem
pip install pytest
pytest -q                # 12 tests, each breaks one rule on purpose
```

GitHub Actions runs the lint and the tests on every push.

## Design decisions

- Semantic tokens (`text.muted`, `surface.brand`) are aliases of base tokens. `tokens.css` keeps them as `var()` references, so changing one base colour updates every component that uses it.
- Components never hard-code a colour. Each variant names two tokens, which is what makes the contrast check possible.
- The `topic-card` has a `show-when` rule (`Status = Published`), so draft content in the database never reaches the page.
