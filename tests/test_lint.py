"""Tests for the linter. Each test breaks one rule on purpose and checks it is caught."""

import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from build import load  # noqa: E402
from dskit.lint import (  # noqa: E402
    check_components, check_entries, check_token_aliases, check_token_names, lint_all,
)
from dskit.tokens import contrast, flatten, resolve, to_css  # noqa: E402


@pytest.fixture
def system():
    # Deep copy so each test can break things without affecting the others
    return copy.deepcopy(load())


def test_shipped_system_is_clean(system):
    assert lint_all(*system) == []


def test_alias_resolves_to_base_colour(system):
    flat = flatten(system[0])
    assert resolve(flat, "surface.brand") == "#1f5fad"


def test_css_keeps_aliases_as_var_references(system):
    css = to_css(flatten(system[0]))
    assert "--surface-brand: var(--color-brand-primary);" in css


def test_contrast_matches_known_values():
    assert round(contrast("#000000", "#ffffff"), 1) == 21.0
    assert round(contrast("#777777", "#ffffff"), 2) == 4.48


def test_bad_token_name_is_caught(system):
    tokens = system[0]
    tokens["color"]["brand"]["PrimaryLight"] = {"$type": "color", "$value": "#5b8fd6"}
    assert any("PrimaryLight" in p for p in check_token_names(tokens))


def test_broken_alias_is_caught(system):
    tokens = system[0]
    tokens["text"]["muted"]["$value"] = "{color.neutral.650}"
    assert any("does not exist" in p for p in check_token_aliases(tokens))


def test_alias_loop_is_caught(system):
    tokens = system[0]
    tokens["text"]["default"]["$value"] = "{text.muted}"
    tokens["text"]["muted"]["$value"] = "{text.default}"
    assert any("alias loop" in p for p in check_token_aliases(tokens))


def test_low_contrast_variant_is_caught(system):
    tokens, components, schema, _ = system
    components["topic-card"]["variants"]["subtle"]["foreground"] = "border.default"
    assert any("contrast" in p for p in check_components(components, tokens, schema))


def test_slot_bound_to_missing_property_is_caught(system):
    tokens, components, schema, _ = system
    components["topic-card"]["slots"]["body"]["property"] = "Description"
    assert any("not in the schema" in p for p in check_components(components, tokens, schema))


def test_slot_type_mismatch_is_caught(system):
    tokens, components, schema, _ = system
    components["topic-card"]["slots"]["meta"]["property"] = "Summary"
    assert any("accepts" in p for p in check_components(components, tokens, schema))


def test_new_select_option_without_badge_variant_is_caught(system):
    tokens, components, schema, _ = system
    schema["properties"]["Specialty"]["options"].append("Mental Health")
    problems = check_components(components, tokens, schema)
    assert any("no variant" in p and "mental-health" in p for p in problems)


def test_bad_entries_are_caught(system):
    _, _, schema, entries = system
    entries[0]["Specialty"] = "Dermatology"
    entries[1]["Related topics"] = ["missing-topic"]
    entries[2]["Last reviewed"] = "30/08/2026"
    del entries[3]["Summary"]
    problems = check_entries(entries, schema)
    assert len(problems) == 4
