"""Locate ``*.module.css`` files across the configured source directories."""

from pathlib import Path

from django.apps import apps
from django.core.exceptions import ImproperlyConfigured

from .conf import ModuleSettings, get_settings
from .exceptions import CssModuleNotFoundError


def source_dirs(cfg: ModuleSettings) -> list[Path]:
    """All directories to scan: explicit ``dirs`` plus each ``app_dirs`` sub-dir per app."""
    dirs = list(cfg.dirs)
    if cfg.app_dirs:
        for config in apps.get_app_configs():
            for subdir in cfg.app_dirs:
                candidate = Path(config.path) / subdir
                if candidate.is_dir():
                    dirs.append(candidate)
    return dirs


def discover_modules(cfg: ModuleSettings | None = None) -> dict[str, Path]:
    """Return a mapping of ``relative key -> absolute path`` for every module.

    A "module" is any file whose name ends with the configured ``suffix``
    (default ``.module.css``). Directories come from ``dirs`` and, if enabled,
    the ``app_dirs`` sub-directory of each installed app. The key is the path
    relative to whichever directory contains it (POSIX separators), so
    ``{% cssmodule "components/card.module.css" %}`` maps straight onto it.
    Missing directories are skipped; the same key appearing in two directories
    is a configuration error.
    """
    cfg = cfg or get_settings()
    found: dict[str, Path] = {}
    origins: dict[str, Path] = {}

    for source_dir in source_dirs(cfg):
        if not source_dir.is_dir():
            continue
        for path in sorted(source_dir.rglob(f"*{cfg.suffix}")):
            if not path.is_file():
                continue
            key = path.relative_to(source_dir).as_posix()
            if key in found:
                raise ImproperlyConfigured(
                    f"Duplicate CSS module {key!r} found in both "
                    f"{origins[key]} and {source_dir}. Module keys must be unique across dirs."
                )
            found[key] = path
            origins[key] = source_dir

    return found


def resolve_module(key: str, cfg: ModuleSettings | None = None) -> Path:
    """Return the absolute path for a single module key, or raise ``CssModuleNotFoundError``."""
    cfg = cfg or get_settings()
    normalized = key.replace("\\", "/").lstrip("/")
    modules = discover_modules(cfg)
    try:
        return modules[normalized]
    except KeyError:
        raise CssModuleNotFoundError(
            f"No CSS module {key!r} found in: {', '.join(str(d) for d in source_dirs(cfg))}."
        ) from None
