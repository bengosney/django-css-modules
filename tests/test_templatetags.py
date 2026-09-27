"""Tests for the cssmodules template tags (production / manifest mode)."""

import pytest
from django.template import Context, Template

from django_css_modules.compiler import compile_all
from django_css_modules.exceptions import CssModuleNotFoundError


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


def test_cssdump_filter_from_resolved_map(project):
    manifest = compile_all()
    out = render('{% load cssmodules %}{% cssmodule "card.module.css" as card %}{{ card|cssdump }}')
    exports = manifest["modules"]["card.module.css"]["exports"]
    assert out.startswith('<pre class="cssdump">') and out.endswith("</pre>")
    for name in exports:
        assert name in out


def test_cssdump_filter_from_key(project):
    manifest = compile_all()
    out = render('{% load cssmodules %}{{ "card.module.css"|cssdump }}')
    exports = manifest["modules"]["card.module.css"]["exports"]
    for name in exports:
        assert name in out


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


# --- {% class %} helper -------------------------------------------------


def test_class_tag_joins_module_and_literal(project):
    manifest = compile_all()
    out = render(
        "{% load cssmodules %}"
        '{% cssmodule "card.module.css" as card %}'
        '{% cssmodule "components/button.module.css" as button %}'
        '<div {% class card.container button.primary "static-extra" %}></div>'
    )
    card = manifest["modules"]["card.module.css"]["exports"]
    button = manifest["modules"]["components/button.module.css"]["exports"]
    assert out == f'<div class="{card["container"]} {button["primary"]} static-extra"></div>'


def test_class_tag_expands_composes_and_dedupes(project):
    compile_all()
    # card.title composes container, so it resolves to "title container"; passing
    # card.container too would duplicate the container class -> deduped.
    out = render('{% load cssmodules %}{% cssmodule "card.module.css" as card %}{% class card.title card.container %}')
    classes = out.removeprefix('class="').removesuffix('"').split()
    assert len(classes) == len(set(classes))  # no duplicates
    assert classes[0].endswith("_title")


def test_class_tag_drops_blanks(project):
    compile_all()
    out = render(
        '{% load cssmodules %}{% cssmodule "card.module.css" as card %}{% class card.missing card.container %}'
    )
    # only the container class survives; the unknown local resolves to ""
    assert out.count(" ") == 0
    assert out.startswith('class="') and out.endswith('"')
