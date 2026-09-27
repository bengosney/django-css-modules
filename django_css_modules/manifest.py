"""Build-time manifest: where compiled CSS lands and the exports map.

The manifest is written into the output dir alongside the compiled CSS, so it is
collected and deployed by ``collectstatic`` like any other static file. At render
time it is read from the filesystem (the collected ``STATIC_ROOT`` copy if present,
otherwise the build dir), never over HTTP.
"""

import json
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from .conf import ModuleSettings

MANIFEST_VERSION = 1
MANIFEST_NAME = "manifest.json"

# Parsed manifests cached by path, invalidated on file mtime change.
_cache: dict[str, tuple[float, dict]] = {}


def _first_staticfiles_dir() -> Path | None:
    dirs = getattr(settings, "STATICFILES_DIRS", None) or []
    if not dirs:
        return None
    entry = dirs[0]
    if isinstance(entry, (tuple, list)):  # ("prefix", "/path") form
        return Path(entry[1])
    return Path(entry)


def resolve_output_root(cfg: ModuleSettings) -> Path:
    """Filesystem directory that compiled CSS is written under."""
    if cfg.output_root:
        return Path(cfg.output_root)
    root = _first_staticfiles_dir()
    if root is None:
        raise ImproperlyConfigured(
            "django-css-modules needs somewhere to write compiled CSS. Set "
            "CSS_MODULES['output_root'] or configure STATICFILES_DIRS."
        )
    return root


def resolve_output_dir(cfg: ModuleSettings) -> Path:
    """The ``output`` subdirectory inside the output root."""
    return resolve_output_root(cfg) / cfg.output


def resolve_manifest_path(cfg: ModuleSettings) -> Path:
    """Where the manifest is written (inside the output dir, so it gets collected)."""
    if cfg.manifest_path:
        return Path(cfg.manifest_path)
    return resolve_output_dir(cfg) / MANIFEST_NAME


def _read_candidates(cfg: ModuleSettings) -> list[Path]:
    """Filesystem locations to look for the manifest at render time, best first."""
    if cfg.manifest_path:
        return [Path(cfg.manifest_path)]
    candidates = []
    static_root = getattr(settings, "STATIC_ROOT", None)
    if static_root:  # the copy collectstatic produced (production)
        candidates.append(Path(static_root) / cfg.output / MANIFEST_NAME)
    candidates.append(resolve_output_dir(cfg) / MANIFEST_NAME)  # build dir (pre-collect / dev)
    return candidates


def save_manifest(cfg: ModuleSettings, data: dict) -> Path:
    path = resolve_manifest_path(cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    _cache[str(path)] = (path.stat().st_mtime, data)
    return path


def load_manifest(cfg: ModuleSettings) -> dict:
    for path in _read_candidates(cfg):
        try:
            mtime = path.stat().st_mtime
        except FileNotFoundError:
            continue

        key = str(path)
        hit = _cache.get(key)
        if hit is not None and hit[0] == mtime:
            return hit[1]
        with path.open(encoding="utf-8") as fh:
            data = json.load(fh)
        _cache[key] = (mtime, data)
        return data

    raise ImproperlyConfigured(
        "CSS modules manifest not found. Run `manage.py compilecssmodules` (or "
        "`collectstatic` with CssModulesFinder) before serving, or enable DEBUG "
        "for on-demand compilation."
    )


def clear_cache(**kwargs) -> None:
    _cache.clear()
