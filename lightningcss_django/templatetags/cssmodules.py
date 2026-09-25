"""Template tags for using CSS Modules in Django templates.

Usage::

    {% load cssmodules %}
    {% cssmodule "card.module.css" as card %}

    <link rel="stylesheet" href="{% cssmodule_url "card.module.css" %}">
    {# ...or one bundled file: #}
    <link rel="stylesheet" href="{% cssmodules_bundle_url %}">

    <div class="{{ card.container }}">{{ card.title }}</div>
"""

from django import template

from ..resolver import get_resolver

register = template.Library()


@register.simple_tag
def cssmodule(key):
    """Return the ``{local: "hashed classes"}`` map for a module.

    Intended for use with ``as``: ``{% cssmodule "x.module.css" as x %}`` then
    ``{{ x.title }}``. Unknown local names resolve to Django's ``string_if_invalid``
    (empty by default), matching normal template variable behaviour.
    """
    return get_resolver().classes(key)


@register.simple_tag
def cssmodule_url(key):
    """Return the served URL of a single module's compiled CSS."""
    return get_resolver().css_url(key)


@register.simple_tag
def cssmodules_bundle_url():
    """Return the served URL of the bundle containing every module's CSS."""
    return get_resolver().bundle_url()
