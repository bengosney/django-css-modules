"""Template tags for using CSS Modules in Django templates.

Usage::

    {% load cssmodules %}
    {% cssmodule "card.module.css" as card %}

    <link rel="stylesheet" href="{% cssmodule_url "card.module.css" %}">
    {# ...or one bundled file: #}
    <link rel="stylesheet" href="{% cssmodules_bundle_url %}">

    <div class="{{ card.container }}">{{ card.title }}</div>

    {# debug: dump a module's local -> compiled class map #}
    {{ card|cssdump }}
"""

from django import template
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe

from ..resolver import get_resolver

register = template.Library()


@register.simple_tag(name="class")
def class_attr(*values):
    """Build a ``class="..."`` attribute from any number of class references.

    ``{% cssmodule "page.module.css" as page %}``
    ``{% cssmodule "card.module.css" as card %}``
    ``<div {% class page.bla card.pop "static-extra" %}>``

    Each argument is whitespace-split, so composed classes (which resolve to
    several names) flow through; blanks are dropped and duplicates removed while
    preserving order.
    """
    seen: dict[str, None] = {}
    for value in values:
        if not value:
            continue
        for name in str(value).split():
            seen.setdefault(name, None)
    joined = " ".join(conditional_escape(name) for name in seen)
    return mark_safe(f'class="{joined}"')  # names are compiled identifiers, escaped above


@register.simple_tag
def cssmodule(key):
    """Return the ``{local: "hashed classes"}`` map for a module.

    Intended for use with ``as``: ``{% cssmodule "x.module.css" as x %}`` then
    ``{{ x.title }}``. Unknown local names resolve to Django's ``string_if_invalid``
    (empty by default), matching normal template variable behaviour.
    """
    return get_resolver().classes(key)


@register.filter
def cssdump(value):
    """Dump a module's ``local -> compiled`` class map for debugging.

    Accepts either a resolved map or a module key, so both of these work::

        {% cssmodule "card.module.css" as card %}{{ card|cssdump }}
        {{ "card.module.css"|cssdump }}

    Renders a ``<pre>`` block listing the local class names, one per line.
    """
    classes = value if isinstance(value, dict) else get_resolver().classes(value)
    if not classes:
        return mark_safe('<pre class="cssdump">(no classes)</pre>')
    lines = "\n".join(conditional_escape(name) for name in classes.keys())
    return mark_safe(f'<pre class="cssdump">{lines}</pre>')


@register.simple_tag
def cssmodule_url(key):
    """Return the served URL of a single module's compiled CSS."""
    return get_resolver().css_url(key)


@register.simple_tag
def cssmodules_bundle_url():
    """Return the served URL of the bundle containing every module's CSS."""
    return get_resolver().bundle_url()
