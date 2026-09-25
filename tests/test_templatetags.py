"""Tests for the cssmodules template tags (production / manifest mode)."""

import pytest
from django.template import Context, Template

from lightningcss_django.compiler import compile_all
from lightningcss_django.exceptions import CssModuleNotFoundError


def render(source: str, **context) -> str:
    return Template(source).render(Context(context))


def test_cssmodule_assignment_and_class_access(project):
    manifest = compile_all()
    out = render('{% load cssmodules %}{% cssmodule "card.module.css" as card %}{{ card.title }}|{{ card.container }}')
    exports = manifest["modules"]["card.module.css"]["exports"]
    assert out == f"{exports['title']}|{exports['container']}"
    # composes carried through to the rendered class attribute
    assert exports["container"] in out.split("|")[0].split()


def test_multiple_modules_in_one_template(project):
    manifest = compile_all()
    out = render(
        "{% load cssmodules %}"
        '{% cssmodule "card.module.css" as card %}'
        '{% cssmodule "components/button.module.css" as button %}'
        "{{ card.title }} {{ button.primary }}"
    )
    card = manifest["modules"]["card.module.css"]["exports"]
    button = manifest["modules"]["components/button.module.css"]["exports"]
    assert card["title"] in out
    assert button["primary"] in out


def test_unknown_local_name_is_empty(project):
    compile_all()
    out = render('{% load cssmodules %}{% cssmodule "card.module.css" as card %}[{{ card.nope }}]')
    assert out == "[]"


def test_cssmodule_url_tag(project):
    compile_all()
    out = render('{% load cssmodules %}{% cssmodule_url "card.module.css" %}')
    assert out == "/static/cssmodules/card.module.css"


def test_bundle_url_tag(project):
    compile_all()
    out = render("{% load cssmodules %}{% cssmodules_bundle_url %}")
    assert out == "/static/cssmodules/bundle.css"


def test_missing_module_raises(project):
    compile_all()
    with pytest.raises(CssModuleNotFoundError):
        render('{% load cssmodules %}{% cssmodule "nope.module.css" as x %}{{ x.a }}')
