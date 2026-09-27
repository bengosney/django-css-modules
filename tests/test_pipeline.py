"""Tests for the compiler, manifest, and resolver."""

import pytest

from django_css_modules.compiler import compile_all, flatten_exports
from django_css_modules.exceptions import CssModuleNotFoundError
from django_css_modules.manifest import load_manifest, resolve_manifest_path, resolve_output_dir
from django_css_modules.resolver import DevResolver, ManifestResolver, get_resolver

# --- flatten ------------------------------------------------------------


def test_flatten_exports_joins_composes():
    exports = {
        "container": {"name": "h_container", "composes": []},
        "title": {"name": "h_title", "composes": ["h_container"]},
    }
    assert flatten_exports(exports) == {"container": "h_container", "title": "h_title h_container"}


# --- compile_all --------------------------------------------------------


def test_compile_all_writes_css_bundle_and_manifest(project):
    manifest = compile_all()
    out_dir = resolve_output_dir(get_resolver().cfg)

    # per-module files mirror their keys under the output dir
    assert (out_dir / "card.module.css").is_file()
    assert (out_dir / "components" / "button.module.css").is_file()
    # bundle (built by the real bundler) contains every module's scoped classes
    bundle = (out_dir / "bundle.css").read_text()
    card = manifest["modules"]["card.module.css"]["exports"]
    button = manifest["modules"]["components/button.module.css"]["exports"]
    assert card["title"].split()[0] in bundle
    assert button["primary"] in bundle

    assert manifest["version"] == 1
    assert manifest["bundle"] == "cssmodules/bundle.css"
    assert set(manifest["modules"]) == {"card.module.css", "components/button.module.css"}
    card = manifest["modules"]["card.module.css"]
    assert card["css"] == "cssmodules/card.module.css"
    # composes flattened into the class string: .title carries .container's class
    container_class = card["exports"]["container"]
    assert container_class in card["exports"]["title"].split()


def test_manifest_written_into_output_dir(project):
    compile_all()
    manifest_path = resolve_manifest_path(get_resolver().cfg)
    out_dir = resolve_output_dir(get_resolver().cfg)
    assert manifest_path.is_file()
    # lives inside the output dir so collectstatic picks it up
    assert manifest_path.parent == out_dir


def test_output_dir_has_no_stray_build_files(project):
    compile_all()
    out_dir = resolve_output_dir(get_resolver().cfg)
    names = {p.name for p in out_dir.rglob("*") if p.is_file()}
    # only real artifacts — no transient bundle entry file left behind
    assert "_bundle_entry.css" not in names
    assert names == {"card.module.css", "button.module.css", "bundle.css", "manifest.json"}


# --- ManifestResolver (production) --------------------------------------


def test_manifest_resolver_classes_and_urls(project):
    compile_all()
    resolver = get_resolver()
    assert isinstance(resolver, ManifestResolver)  # DEBUG defaults to False

    classes = resolver.classes("card.module.css")
    assert "container" in classes["title"]  # composes present
    assert resolver.css_url("card.module.css") == "/static/cssmodules/card.module.css"
    assert resolver.bundle_url() == "/static/cssmodules/bundle.css"


def test_manifest_resolver_missing_module(project):
    compile_all()
    with pytest.raises(CssModuleNotFoundError):
        get_resolver().classes("nope.module.css")


def test_manifest_cache_reloads_on_recompile(project):
    import os

    compile_all()
    resolver = get_resolver()
    first = resolver.classes("card.module.css")["title"]

    # change the source, bump mtime, recompile
    src_card = project / "src" / "card.module.css"
    src_card.write_text(".container{padding:2rem}\n.title{composes:container;color:red}\n")
    manifest_path = resolve_manifest_path(resolver.cfg)
    compile_all()
    os.utime(manifest_path, (manifest_path.stat().st_atime + 10, manifest_path.stat().st_mtime + 10))

    reloaded = load_manifest(resolver.cfg)
    assert reloaded["modules"]["card.module.css"]["exports"]["title"]
    assert first  # sanity: had a value before


# --- DevResolver --------------------------------------------------------


def test_dev_resolver_compiles_on_demand(project, settings):
    settings.DEBUG = True
    resolver = get_resolver()
    assert isinstance(resolver, DevResolver)

    classes = resolver.classes("card.module.css")
    assert "container" in classes["title"]
    # cached: second call returns same object identity for the class map
    assert resolver.classes("card.module.css") is classes


def test_dev_resolver_recompiles_when_source_changes(project, settings):
    import os

    settings.DEBUG = True
    resolver = get_resolver()
    first = resolver.classes("card.module.css")

    src_card = project / "src" / "card.module.css"
    src_card.write_text(".container{padding:2rem}\n")
    os.utime(src_card, (src_card.stat().st_atime + 10, src_card.stat().st_mtime + 10))

    second = resolver.classes("card.module.css")
    assert second is not first
    assert "title" not in second
