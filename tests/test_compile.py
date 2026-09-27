"""Tests for the native _lightningcss_rs.compile() contract."""

import pytest

from django_css_modules import _lightningcss_rs as rs

CSS = """
.container { padding: 1rem; }
.title { composes: container; font-weight: bold; }
#main { display: grid; }
"""


def test_version():
    assert rs.version() == "0.0.1"


def test_scopes_class_names():
    code, exports = rs.compile(CSS, "card.module.css", minify=False)
    # Original names are gone; hashed names are present.
    assert ".container " not in code
    assert exports["container"]["name"] in code
    assert exports["title"]["name"].endswith("_title")


def test_exports_shape():
    _, exports = rs.compile(CSS, "card.module.css")
    assert set(exports) == {"container", "title", "main"}
    for value in exports.values():
        assert set(value) == {"name", "composes"}
        assert isinstance(value["name"], str)
        assert isinstance(value["composes"], list)


def test_same_file_composes_resolves_to_hashed_name():
    _, exports = rs.compile(CSS, "card.module.css")
    # `.title { composes: container }` -> title carries container's hashed name.
    assert exports["title"]["composes"] == [exports["container"]["name"]]
    assert exports["container"]["composes"] == []


def test_custom_pattern():
    _, exports = rs.compile(CSS, "card.module.css", pattern="[name]_[local]")
    assert exports["container"]["name"] == "card-module_container"


def test_minify():
    code, _ = rs.compile(CSS, "card.module.css", minify=True)
    assert "\n" not in code.strip()
    assert "font-weight:700" in code


def test_hashing_is_deterministic():
    a, _ = rs.compile(CSS, "card.module.css")
    b, _ = rs.compile(CSS, "card.module.css")
    assert a == b


def test_browser_targeting_runs():
    # Just ensure a browserslist query is accepted and produces output.
    code, _ = rs.compile(".a { color: rebeccapurple; }", "a.module.css", browsers_list=["last 2 versions"])
    assert code


def test_invalid_pattern_raises():
    with pytest.raises(ValueError):
        rs.compile(CSS, "card.module.css", pattern="[unknown_segment]")
