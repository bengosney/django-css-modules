"""Tests for settings validation and module discovery."""

import pytest
from django.core.exceptions import ImproperlyConfigured

from lightningcss_django.conf import get_settings
from lightningcss_django.discovery import discover_modules, resolve_module
from lightningcss_django.exceptions import CssModuleNotFoundError


def write(path, text=".a { color: red; }"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


# --- conf ---------------------------------------------------------------


def test_missing_setting_raises(settings):
    del settings.LIGHTNINGCSS_MODULES
    with pytest.raises(ImproperlyConfigured):
        get_settings()


def test_dirs_required(settings):
    settings.LIGHTNINGCSS_MODULES = {"minify": True}
    with pytest.raises(ImproperlyConfigured):
        get_settings()


def test_single_path_dirs_rejected(settings, tmp_path):
    settings.LIGHTNINGCSS_MODULES = {"dirs": str(tmp_path)}
    with pytest.raises(ImproperlyConfigured):
        get_settings()


def test_unknown_key_rejected(settings, tmp_path):
    settings.LIGHTNINGCSS_MODULES = {"dirs": [tmp_path], "minfy": True}
    with pytest.raises(ImproperlyConfigured):
        get_settings()


def test_defaults_and_targets_coercion(settings, tmp_path):
    settings.LIGHTNINGCSS_MODULES = {"dirs": [tmp_path], "targets": "last 2 versions"}
    cfg = get_settings()
    assert cfg.output == "cssmodules"
    assert cfg.dashed_idents is False
    assert cfg.targets == ("last 2 versions",)


def test_minify_defaults_off_in_debug(settings, tmp_path):
    settings.DEBUG = True
    settings.LIGHTNINGCSS_MODULES = {"dirs": [tmp_path]}
    assert get_settings().minify is False


def test_minify_defaults_on_without_debug(settings, tmp_path):
    settings.DEBUG = False
    settings.LIGHTNINGCSS_MODULES = {"dirs": [tmp_path]}
    assert get_settings().minify is True


def test_minify_explicit_overrides_debug(settings, tmp_path):
    settings.DEBUG = True
    settings.LIGHTNINGCSS_MODULES = {"dirs": [tmp_path], "minify": True}
    assert get_settings().minify is True

    settings.DEBUG = False
    settings.LIGHTNINGCSS_MODULES = {"dirs": [tmp_path], "minify": False}
    assert get_settings().minify is False


# --- discovery ----------------------------------------------------------


def test_discovers_across_dirs_with_relative_keys(settings, tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    write(a / "card.module.css")
    write(a / "components" / "nav.module.css")
    write(b / "button.module.css")
    write(a / "plain.css")  # not a module -> ignored
    settings.LIGHTNINGCSS_MODULES = {"dirs": [a, b]}

    modules = discover_modules()
    assert set(modules) == {"card.module.css", "components/nav.module.css", "button.module.css"}
    assert modules["card.module.css"] == a / "card.module.css"


def test_custom_suffix(settings, tmp_path):
    a = tmp_path / "a"
    write(a / "card.scoped.css")
    write(a / "other.module.css")  # default suffix -> ignored now
    settings.LIGHTNINGCSS_MODULES = {"dirs": [a], "suffix": ".scoped.css"}

    modules = discover_modules()
    assert set(modules) == {"card.scoped.css"}


def test_empty_suffix_rejected(settings, tmp_path):
    settings.LIGHTNINGCSS_MODULES = {"dirs": [tmp_path], "suffix": ""}
    with pytest.raises(ImproperlyConfigured):
        get_settings()


def test_missing_dir_is_skipped(settings, tmp_path):
    a = tmp_path / "a"
    write(a / "card.module.css")
    settings.LIGHTNINGCSS_MODULES = {"dirs": [a, tmp_path / "does-not-exist"]}
    assert set(discover_modules()) == {"card.module.css"}


def test_collision_across_dirs_raises(settings, tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    write(a / "card.module.css")
    write(b / "card.module.css")
    settings.LIGHTNINGCSS_MODULES = {"dirs": [a, b]}
    with pytest.raises(ImproperlyConfigured):
        discover_modules()


def test_resolve_module(settings, tmp_path):
    a = tmp_path / "a"
    write(a / "components" / "card.module.css")
    settings.LIGHTNINGCSS_MODULES = {"dirs": [a]}

    assert resolve_module("components/card.module.css") == a / "components" / "card.module.css"
    # leading slash / backslashes are normalized
    assert resolve_module("/components\\card.module.css") == a / "components" / "card.module.css"

    with pytest.raises(CssModuleNotFoundError):
        resolve_module("nope.module.css")
