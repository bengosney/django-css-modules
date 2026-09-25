# lightningcss-django

CSS Modules for Django templates, powered by [Lightning CSS](https://lightningcss.dev/).

Scope your CSS class names per file and reference the hashed names directly from Django
templates — no JavaScript bundler required. Class names are transformed at build time
(with a dev fallback that compiles on demand).

> Status: early development. See the build plan in the project notes.

## How it works

`*.module.css` files are compiled with Lightning CSS's CSS Modules support. A single
compile pass produces both the transformed CSS (hashed class names) and an `exports` map
(original name → hashed name), so the stylesheet and your templates always agree.

```django
{% load cssmodules %}
{% cssmodule "card.module.css" as card %}

<link rel="stylesheet" href="{% cssmodule_url "card.module.css" %}">
{# ...or ship one bundled file: #}
<link rel="stylesheet" href="{% cssmodules_bundle_url %}">

<div class="{{ card.container }}">{{ card.title }}</div>
```

## Development

Requires [uv](https://github.com/astral-sh/uv) and a Rust toolchain.

```bash
make init        # set up .venv, install deps, git hooks
make develop     # build the Rust extension into the venv
make test
```
