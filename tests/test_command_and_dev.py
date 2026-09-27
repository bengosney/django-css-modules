"""End-to-end tests: the management command and dev on-demand serving."""

from io import StringIO

import pytest
from django.core.management import call_command
from django.template import Context, Template

from django_css_modules.manifest import resolve_manifest_path, resolve_output_dir
from django_css_modules.resolver import DevResolver, get_resolver


# --- management command -------------------------------------------------


def test_compilecssmodules_command(project):
    out = StringIO()
    call_command("compilecssmodules", stdout=out)

    cfg = get_resolver().cfg
    assert resolve_manifest_path(cfg).is_file()
    assert (resolve_output_dir(cfg) / "card.module.css").is_file()
    assert (resolve_output_dir(cfg) / "bundle.css").is_file()
    assert "Compiled 2 CSS module(s)" in out.getvalue()


def test_command_reports_compile_error(project, settings):
    # A pattern the native layer rejects surfaces as a CommandError.
    from django.core.management.base import CommandError

    cfg = dict(settings.CSS_MODULES)
    cfg["pattern"] = "[not_a_real_segment]"
    settings.CSS_MODULES = cfg
    with pytest.raises(CommandError):
        call_command("compilecssmodules")


# --- dev views (DEBUG on-demand serving) --------------------------------


@pytest.fixture
def dev(project, settings):
    settings.DEBUG = True
    return project


def test_module_css_view_serves_compiled_css(dev, client):
    resp = client.get("/cssmodules/card.module.css")
    assert resp.status_code == 200
    assert resp["Content-Type"] == "text/css"
    body = resp.content.decode()
    assert "_title" in body and "_container" in body


def test_nested_module_css_view(dev, client):
    resp = client.get("/cssmodules/components/button.module.css")
    assert resp.status_code == 200
    assert "_primary" in resp.content.decode()


def test_bundle_css_view(dev, client):
    resp = client.get("/cssmodules/bundle.css")
    assert resp.status_code == 200
    body = resp.content.decode()
    # the real bundler merges every module's scoped classes into one sheet
    assert "_title" in body and "_container" in body and "_primary" in body


def test_missing_module_view_404(dev, client):
    assert client.get("/cssmodules/nope.module.css").status_code == 404


# --- dev resolver URLs reverse to the views -----------------------------


def test_dev_resolver_urls(dev):
    resolver = get_resolver()
    assert isinstance(resolver, DevResolver)
    assert resolver.css_url("card.module.css") == "/cssmodules/card.module.css"
    assert resolver.css_url("components/button.module.css") == "/cssmodules/components/button.module.css"
    assert resolver.bundle_url() == "/cssmodules/bundle.css"


def test_dev_url_tags_render(dev):
    out = Template('{% load cssmodules %}{% cssmodule_url "card.module.css" %}|{% cssmodules_bundle_url %}').render(
        Context()
    )
    assert out == "/cssmodules/card.module.css|/cssmodules/bundle.css"
