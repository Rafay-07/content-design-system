"""Design token loading, alias resolution and colour contrast.

Tokens follow the W3C Design Tokens Community Group format: every token is
an object with "$value" and "$type". A value written as "{color.neutral.0}"
is an alias that points at another token.
"""

import json
import re
from pathlib import Path

ALIAS = re.compile(r"^\{([^}]+)\}$")


def load_json(path):
    """Read a JSON file and return the parsed data."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def flatten(tree, prefix=""):
    """Turn the nested token tree into {"color.brand.primary": {...}}.

    A node counts as a token when it has a "$value" key. Anything else is a
    group, so we keep walking down into it.
    """
    flat = {}
    for name, node in tree.items():
        path = f"{prefix}.{name}" if prefix else name
        if isinstance(node, dict) and "$value" in node:
            flat[path] = node
        elif isinstance(node, dict):
            flat.update(flatten(node, path))
    return flat


def resolve(flat, path, seen=None):
    """Follow aliases until we reach a real value.

    Raises KeyError for an alias that points nowhere and ValueError for a
    loop such as a -> b -> a, so the linter can report both.
    """
    seen = seen or []
    if path in seen:
        raise ValueError("alias loop: " + " -> ".join(seen + [path]))
    if path not in flat:
        raise KeyError(path)
    value = flat[path]["$value"]
    match = ALIAS.match(str(value))
    if match:
        return resolve(flat, match.group(1), seen + [path])
    return value


def css_name(path):
    """color.brand.primary -> --color-brand-primary"""
    return "--" + path.replace(".", "-")


def to_css(flat):
    """Write every token as a CSS custom property.

    Aliases stay as var() references so a change to a base colour flows
    through to every semantic token that uses it.
    """
    lines = [":root {"]
    for path, token in flat.items():
        match = ALIAS.match(str(token["$value"]))
        value = f"var({css_name(match.group(1))})" if match else token["$value"]
        lines.append(f"  {css_name(path)}: {value};")
    lines.append("}")
    return "\n".join(lines) + "\n"


def _channel(c):
    # sRGB channel to linear light, per the WCAG 2.x relative luminance formula
    c = c / 255
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def luminance(hex_colour):
    """Relative luminance of a #rrggbb colour (0 is black, 1 is white)."""
    h = hex_colour.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * _channel(r) + 0.7152 * _channel(g) + 0.0722 * _channel(b)


def contrast(fg, bg):
    """WCAG contrast ratio between two colours, from 1.0 up to 21.0."""
    light, dark = sorted((luminance(fg), luminance(bg)), reverse=True)
    return (light + 0.05) / (dark + 0.05)
