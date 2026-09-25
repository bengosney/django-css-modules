"""Reading and validating the ``LIGHTNINGCSS_MODULES`` Django setting."""

from dataclasses import dataclass
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

SETTING_NAME = "LIGHTNINGCSS_MODULES"

DEFAULT_SUFFIX = ".module.css"

_DEFAULTS = {
    "suffix": DEFAULT_SUFFIX,
    "output": "cssmodules",
    "output_root": None,
    "minify": None,  # None = auto: minify unless DEBUG
    "targets": None,
    "pattern": None,
    "dashed_idents": False,
    "manifest_path": None,
}

_KNOWN_KEYS = {"dirs", *_DEFAULTS}


@dataclass(frozen=True)
class ModuleSettings:
    """Validated configuration for the CSS Modules pipeline."""

    dirs: tuple[Path, ...]
    suffix: str = DEFAULT_SUFFIX
    output: str = "cssmodules"
    output_root: Path | None = None
    minify: bool = True
    targets: tuple[str, ...] | None = None
    pattern: str | None = None
    dashed_idents: bool = False
    manifest_path: Path | None = None


def get_settings() -> ModuleSettings:
    """Build a :class:`ModuleSettings` from Django settings, validating as we go.

    Not cached: callers may rely on ``override_settings`` (tests) and per-request
    changes. Discovery/compile layers add their own mtime-aware caching.
    """
    raw = getattr(settings, SETTING_NAME, None)
    if not raw:
        raise ImproperlyConfigured(f"The {SETTING_NAME} setting is required.")
    if not isinstance(raw, dict):
        raise ImproperlyConfigured(f"{SETTING_NAME} must be a dict, got {type(raw).__name__}.")

    unknown = set(raw) - _KNOWN_KEYS
    if unknown:
        raise ImproperlyConfigured(
            f"Unknown {SETTING_NAME} keys: {', '.join(sorted(unknown))}. Valid keys: {', '.join(sorted(_KNOWN_KEYS))}."
        )

    dirs = raw.get("dirs")
    if not dirs:
        raise ImproperlyConfigured(f"{SETTING_NAME}['dirs'] must list at least one directory.")
    if isinstance(dirs, (str, Path)):
        raise ImproperlyConfigured(f"{SETTING_NAME}['dirs'] must be a list of directories, not a single path.")

    targets = raw.get("targets", _DEFAULTS["targets"])
    if isinstance(targets, str):
        targets = [targets]

    manifest_path = raw.get("manifest_path", _DEFAULTS["manifest_path"])
    output_root = raw.get("output_root", _DEFAULTS["output_root"])

    suffix = raw.get("suffix", _DEFAULTS["suffix"])
    if not suffix or not isinstance(suffix, str):
        raise ImproperlyConfigured(f"{SETTING_NAME}['suffix'] must be a non-empty string.")

    # Default: minify in production, skip it in DEBUG for readable output.
    minify = raw.get("minify", _DEFAULTS["minify"])
    minify = (not getattr(settings, "DEBUG", False)) if minify is None else bool(minify)

    return ModuleSettings(
        dirs=tuple(Path(d) for d in dirs),
        suffix=suffix,
        output=raw.get("output", _DEFAULTS["output"]),
        output_root=Path(output_root) if output_root else None,
        minify=minify,
        targets=tuple(targets) if targets else None,
        pattern=raw.get("pattern", _DEFAULTS["pattern"]),
        dashed_idents=bool(raw.get("dashed_idents", _DEFAULTS["dashed_idents"])),
        manifest_path=Path(manifest_path) if manifest_path else None,
    )
