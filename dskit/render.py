"""Render the library page: tokens, component variants and live content."""

from html import escape

from .lint import slug
from .tokens import css_name, flatten, resolve

# Component styles. Every value comes from a token variable, so the page
# changes when tokens.json changes and nothing is hard-coded here.
BASE_CSS = """
body { margin: 0; font-family: var(--font-family-base); font-size: var(--font-size-md);
       color: var(--text-default); background: var(--surface-subtle); }
main { max-width: 960px; margin: 0 auto; padding: var(--space-6) var(--space-4); }
h1 { font-size: var(--font-size-xl); margin: 0 0 var(--space-2); }
h2 { font-size: var(--font-size-lg); margin: var(--space-6) 0 var(--space-3);
     padding-bottom: var(--space-2); border-bottom: 1px solid var(--border-default); }
p.lead { color: var(--text-muted); margin: 0; }
.grid { display: grid; gap: var(--space-4); grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); }
.swatches { display: grid; gap: var(--space-2); grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); }
.swatch { background: var(--surface-default); border: 1px solid var(--border-default);
          border-radius: var(--radius-md); overflow: hidden; font-size: var(--font-size-sm); }
.swatch .chip { height: 48px; border-bottom: 1px solid var(--border-default); }
.swatch div.label { padding: var(--space-2); overflow-wrap: anywhere; }
.swatch code { display: block; color: var(--text-muted); }
.topic-card { border: 1px solid var(--border-default); border-radius: var(--radius-md);
              padding: var(--space-4); display: flex; flex-direction: column; gap: var(--space-2); }
.topic-card h3 { margin: 0; font-size: var(--font-size-lg); }
.topic-card p { margin: 0; }
.topic-card .meta { font-size: var(--font-size-sm); }
.specialty-badge { align-self: flex-start; border-radius: var(--radius-sm); font-size: var(--font-size-sm);
                   font-weight: var(--font-weight-bold); padding: var(--space-1) var(--space-2); }
.related-list { font-size: var(--font-size-sm); margin: 0; padding: 0; list-style: none; }
.related-list a { color: inherit; }
.tag { font-size: var(--font-size-sm); color: var(--text-muted); }
.report { background: var(--surface-default); border: 1px solid var(--border-default);
          border-radius: var(--radius-md); padding: var(--space-4); }
.type-row { display: flex; gap: var(--space-4); align-items: baseline; padding: var(--space-2) 0; }
.type-row code { width: 160px; color: var(--text-muted); font-size: var(--font-size-sm); }
"""


def colours(variant):
    """Inline style for a variant's background and foreground tokens."""
    return (f"background: var({css_name(variant['background'])}); "
            f"color: var({css_name(variant['foreground'])});")


def badge(components, specialty):
    variant = components["specialty-badge"]["variants"].get(slug(specialty))
    style = colours(variant) if variant else ""
    return f'<span class="specialty-badge" style="{style}">{escape(specialty)}</span>'


def card(components, entry, titles, variant_name="default"):
    """One topic card. Each slot reads the schema property it is bound to."""
    variant = components["topic-card"]["variants"][variant_name]
    related = "".join(
        f'<li><a href="#{escape(t)}">{escape(titles[t])}</a></li>'
        for t in entry.get("Related topics", []) if t in titles
    )
    related_html = f'<ul class="related-list"><li>Related:</li>{related}</ul>' if related else ""
    return (
        f'<article class="topic-card" id="{escape(entry["id"])}" style="{colours(variant)}">'
        f'{badge(components, entry["Specialty"])}'
        f'<h3>{escape(entry["Title"])}</h3>'
        f'<p>{escape(entry["Summary"])}</p>'
        f'<span class="meta">Last reviewed {escape(entry.get("Last reviewed", "n/a"))}</span>'
        f'{related_html}</article>'
    )


def visible(components, entries):
    """Apply the topic card's show-when rule (only Published entries)."""
    rule = components["topic-card"].get("show-when", {})
    return [e for e in entries if all(e.get(k) == v for k, v in rule.items())]


def page(tokens, components, schema, entries, problems):
    flat = flatten(tokens)
    titles = {e["id"]: e["Title"] for e in entries}
    shown = visible(components, entries)

    swatches = "".join(
        f'<div class="swatch"><div class="chip" style="background: var({css_name(p)})"></div>'
        f'<div class="label">{escape(p)}<code>{escape(str(resolve(flat, p)))}</code></div></div>'
        for p, t in flat.items() if t["$type"] == "color"
    )
    type_scale = "".join(
        f'<div class="type-row"><code>{escape(p)}</code>'
        f'<span style="font-size: var({css_name(p)})">Patient education topic</span></div>'
        for p in flat if p.startswith("font.size.")
    )
    sample = shown[0] if shown else entries[0]
    variants = "".join(
        f'<div><p class="tag">topic-card / {escape(v)}</p>{card(components, sample, titles, v)}</div>'
        for v in components["topic-card"]["variants"]
    )
    badges = " ".join(badge(components, o) for o in schema["properties"]["Specialty"]["options"])
    content = "".join(card(components, e, titles) for e in shown)
    hidden = len(entries) - len(shown)
    report = (
        "<p>All checks pass: token names, aliases, contrast, slot bindings and content rows.</p>"
        if not problems else
        "<ul>" + "".join(f"<li>{escape(p)}</li>" for p in problems) + "</ul>"
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Content design system</title>
<link rel="stylesheet" href="tokens.css">
<style>{BASE_CSS}</style>
</head>
<body>
<main>
<h1>Content design system</h1>
<p class="lead">Generated from system/tokens.json, system/components.json and the
{escape(schema["database"])} content database. Sample content only, not medical advice.</p>

<h2>Colour tokens</h2>
<div class="swatches">{swatches}</div>

<h2>Type scale</h2>
{type_scale}

<h2>Components</h2>
<div class="grid">{variants}</div>
<p class="tag">specialty-badge: one variant per Specialty option</p>
<p>{badges}</p>

<h2>Content preview</h2>
<p class="tag">{len(shown)} published topic(s). {hidden} hidden by the show-when rule (not Published).</p>
<div class="grid">{content}</div>

<h2>Lint report</h2>
<div class="report">{report}</div>
</main>
</body>
</html>
"""
