"""Build-time manifest: where compiled CSS lands and the exports map.

The manifest is server-side data used at render time; it is deliberately written
outside the static tree (default: alongside ``output_root``) so it is not served.
"""

import json
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from .conf import ModuleSettings

MANIFEST_VERSION = 1
DEFAULT_MANIFEST_NAME = "cssmodules.manifest.json"

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
            "lightningcss-django needs somewhere to write compiled CSS. Set "
            "LIGHTNINGCSS_MODULES['output_root'] or configure STATICFILES_DIRS."
        )
    return root


def resolve_output_dir(cfg: ModuleSettings) -> Path:
    """The ``output`` subdirectory inside the output root."""
    return resolve_output_root(cfg) / cfg.output


def resolve_manifest_path(cfg: ModuleSettings) -> Path:
    """Where the manifest JSON is read from / written to."""
    if cfg.manifest_path:
        return Path(cfg.manifest_path)
    return resolve_output_root(cfg).parent / DEFAULT_MANIFEST_NAME


def save_manifest(cfg: ModuleSettings, data: dict) -> Path:
    path = resolve_manifest_path(cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    _cache[str(path)] = (path.stat().st_mtime, data)
    return path


def load_manifest(cfg: ModuleSettings) -> dict:
    path = resolve_manifest_path(cfg)
    try:
        mtime = path.stat().st_mtime
    except FileNotFoundError as exc:
        raise ImproperlyConfigured(
            f"CSS modules manifest not found at {path}. Run `manage.py compilecssmodules` "
            "before serving (or enable DEBUG for on-demand compilation)."
        ) from exc

    key = str(path)
    hit = _cache.get(key)
    if hit is not None and hit[0] == mtime:
        return hit[1]

    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    _cache[key] = (mtime, data)
    return data


def clear_cache(**kwargs) -> None:
    _cache.clear()
