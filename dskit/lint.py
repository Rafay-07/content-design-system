"""Consistency checks across tokens, components and the content schema.

Each check returns a list of plain-English problems. An empty list means
that part of the system is clean.
"""

import re

from .tokens import contrast, flatten, resolve

# Lowercase words joined by hyphens: "primary-dark", "on-brand", "900"
SEGMENT = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MIN_CONTRAST = 4.5  # WCAG 2.x level AA for normal-size text


def slug(text):
    """"Plain language" -> "plain-language", used to match option names to variants."""
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def check_token_names(tokens):
    """Every group and token name must follow the naming convention."""
    problems = []
    for path in flatten(tokens):
        for part in path.split("."):
            if not SEGMENT.match(part):
                problems.append(f"token '{path}': '{part}' should be lowercase words joined by hyphens")
    return problems


def check_token_aliases(tokens):
    """Every alias must point at a token that exists, with no loops."""
    flat = flatten(tokens)
    problems = []
    for path in flat:
        try:
            resolve(flat, path)
        except KeyError as missing:
            problems.append(f"token '{path}' points at '{missing.args[0]}', which does not exist")
        except ValueError as loop:
            problems.append(f"token '{path}': {loop}")
    return problems


def check_components(components, tokens, schema):
    """Components must use real tokens, readable colours and real schema fields."""
    flat = flatten(tokens)
    props = schema["properties"]
    problems = []

    for name, comp in components.items():
        if not SEGMENT.match(name):
            problems.append(f"component '{name}' should be lowercase words joined by hyphens")

        for variant, colours in comp.get("variants", {}).items():
            where = f"{name}/{variant}"
            if not SEGMENT.match(variant):
                problems.append(f"variant '{where}' should be lowercase words joined by hyphens")
            try:
                fg = resolve(flat, colours["foreground"])
                bg = resolve(flat, colours["background"])
            except (KeyError, ValueError) as err:
                problems.append(f"variant '{where}' uses a token that does not resolve: {err}")
                continue
            ratio = contrast(fg, bg)
            if ratio < MIN_CONTRAST:
                problems.append(f"variant '{where}' text contrast is {ratio:.2f}:1, below {MIN_CONTRAST}:1")

        for slot, binding in comp.get("slots", {}).items():
            where = f"{name}.{slot}"
            prop = props.get(binding["property"])
            if prop is None:
                problems.append(f"slot '{where}' is bound to '{binding['property']}', which is not in the schema")
                continue
            if prop["type"] not in binding["accepts"]:
                problems.append(f"slot '{where}' accepts {binding['accepts']} but '{binding['property']}' is {prop['type']}")
            nested = binding.get("component")
            if nested and nested not in components:
                problems.append(f"slot '{where}' uses component '{nested}', which is not defined")

        # A badge-style component needs one variant per option in the schema,
        # otherwise a new option added in the content database would render
        # with no styling.
        source = comp.get("variant-source")
        if source:
            options = {slug(o) for o in props[source].get("options", [])}
            variants = set(comp.get("variants", {}))
            for missing in sorted(options - variants):
                problems.append(f"component '{name}' has no variant for {source} option '{missing}'")
            for extra in sorted(variants - options):
                problems.append(f"component '{name}' variant '{extra}' matches no {source} option")
    return problems


def check_entries(entries, schema):
    """Content rows must match the schema the components were built for."""
    props = schema["properties"]
    ids = {e.get("id") for e in entries}
    problems = []

    for entry in entries:
        eid = entry.get("id", "?")
        for key in entry:
            if key != "id" and key not in props:
                problems.append(f"entry '{eid}' has '{key}', which is not in the schema")
        for key, rule in props.items():
            value = entry.get(key)
            if value in (None, "", []):
                if rule.get("required"):
                    problems.append(f"entry '{eid}' is missing required '{key}'")
                continue
            kind = rule["type"]
            if kind in ("select", "status") and value not in rule["options"]:
                problems.append(f"entry '{eid}' {key} '{value}' is not one of {rule['options']}")
            if kind in ("title", "rich_text") and len(value) > rule.get("max_length", 10**6):
                problems.append(f"entry '{eid}' {key} is {len(value)} characters, limit {rule['max_length']}")
            if kind == "date" and not DATE.match(value):
                problems.append(f"entry '{eid}' {key} '{value}' should be YYYY-MM-DD")
            if kind == "relation":
                for target in value:
                    if target not in ids:
                        problems.append(f"entry '{eid}' {key} points at '{target}', which does not exist")
    return problems


def lint_all(tokens, components, schema, entries):
    """Run every check and return one combined list."""
    return (
        check_token_names(tokens)
        + check_token_aliases(tokens)
        + check_components(components, tokens, schema)
        + check_entries(entries, schema)
    )
