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

## Building the CSS

Two options:

- **Automatic (recommended): compile during `collectstatic`.** Register the finder and point
  the build output outside `STATICFILES_DIRS`:

  ```python
  STATICFILES_FINDERS = [
      "django.contrib.staticfiles.finders.FileSystemFinder",
      "django.contrib.staticfiles.finders.AppDirectoriesFinder",
      "lightningcss_django.finders.CssModulesFinder",
  ]
  LIGHTNINGCSS_MODULES = {"dirs": [...], "output_root": BASE_DIR / ".lightningcss_build"}
  ```

  Then `manage.py collectstatic` compiles the modules and collects them in one step.

- **Manual:** run `manage.py compilecssmodules` before `collectstatic` (writes into
  `output_root`, default `STATICFILES_DIRS[0]`).

The manifest (the class-name map) is written into the output dir alongside the compiled CSS,
so `collectstatic` collects and deploys it automatically — nothing extra to ship. At render
time it's read from the filesystem (the collected `STATIC_ROOT` copy, or the build dir). In
`DEBUG`, CSS is compiled on demand — no build step needed.

Minification defaults to on in production and off under `DEBUG` (readable output). Override it
explicitly with `LIGHTNINGCSS_MODULES = {..., "minify": True/False}`.

## Configuration

All settings live in the `LIGHTNINGCSS_MODULES` dict. At least one of `dirs` or `app_dirs`
is required.

```python
LIGHTNINGCSS_MODULES = {
    "dirs": [BASE_DIR / "assets"],  # at least one of dirs / app_dirs
    "app_dirs": ["static"],  # sub-dirs scanned inside every installed app
    "suffix": ".module.css",
    "output": "cssmodules",
    "output_root": BASE_DIR / ".lightningcss_build",
    "minify": None,  # None = on in prod, off under DEBUG
    "targets": [">= 0.25%"],
    "pattern": "[hash]_[local]",
    "dashed_idents": False,
    "manifest_path": None,
}
```

| Key | Default | Description |
| --- | --- | --- |
| `dirs` | `[]` | Explicit directories scanned for module source files. Multiple dirs share one key space; a duplicate relative key across dirs is an error. Required unless `app_dirs` is set. |
| `app_dirs` | `[]` | Like `dirs`, but resolved inside every installed app: a list of sub-directory names, each scanned as `<app>/<name>/` (e.g. `["static"]`). Namespace files (`static/<app>/…`) to avoid key clashes between apps. |
| `suffix` | `".module.css"` | Filename suffix that marks a file as a module. |
| `output` | `"cssmodules"` | Sub-directory (under `output_root`) for compiled CSS, the bundle, and the manifest. Also the URL prefix. |
| `output_root` | first `STATICFILES_DIRS` entry | Filesystem dir the compiled output is written under. Use a dir **outside** `STATICFILES_DIRS` when using the finder (or it's collected twice). |
| `minify` | `None` → on in prod, off under `DEBUG` | Minify output. Set `True`/`False` to force it. |
| `targets` | `None` | [browserslist](https://github.com/browserslist/browserslist) query (string or list), e.g. `[">= 0.25%"]`. Enables vendor prefixing and transpilation (nesting, `oklab()`, …) for those browsers. Unset = emit modern CSS untouched. |
| `pattern` | `"[hash]_[local]"` | CSS Modules class-name pattern. Segments: `[hash]`, `[content-hash]`, `[local]`, `[name]`. |
| `dashed_idents` | `False` | Also scope CSS custom properties (`--foo`). |
| `manifest_path` | inside the output dir | Override where the manifest JSON is written/read. |

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
