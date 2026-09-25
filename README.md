# lightningcss-django

CSS Modules for Django templates, powered by [Lightning CSS](https://lightningcss.dev/).

Scope your CSS class names per file and reference the hashed names directly from Django
templates — no JavaScript bundler required. Class names are transformed at build time
(with a dev fallback that compiles on demand).

> Status: early development. See the build plan in the project notes.

## How it works

Each `*.module.css` file is compiled with Lightning CSS's CSS Modules support, scoped by
its own stable key so hashes are reproducible. A compile pass produces both the transformed
CSS (hashed class names) and an `exports` map (original name → hashed name), so the stylesheet
and your templates always agree. `composes` within a file is supported.

The bundle (`{% cssmodules_bundle_url %}`) is built by Lightning CSS's real bundler over the
already-compiled files (with CSS Modules off, so the hashed names are preserved): it resolves
`@import`, dedupes, rebases `url()`, and minifies — not a naive concatenation.

```django
{% load cssmodules %}
{% cssmodule "card.module.css" as card %}

<link rel="stylesheet" href="{% cssmodule_url "card.module.css" %}">
{# ...or ship one bundled file: #}
<link rel="stylesheet" href="{% cssmodules_bundle_url %}">

<div class="{{ card.container }}">{{ card.title }}</div>
```

## Known limitations

- **External `@import` inside a module isn't bundled yet.** If a `*.module.css` file itself
  `@import`s a non-module stylesheet (e.g. `@import "shared.css";`), that reference is left in
  the compiled output and the bundle step can't resolve it from the output directory. Modules
  that don't `@import` external files bundle fine.
- **Cross-file `composes ... from "./other.module.css"` is not supported.** Only `composes`
  within a single file is resolved.

## Development

Requires [uv](https://github.com/astral-sh/uv) and a Rust toolchain.

```bash
make init        # set up .venv, install deps, git hooks
make develop     # build the Rust extension into the venv
make test
```
