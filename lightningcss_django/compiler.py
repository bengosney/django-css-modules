"""Compile ``*.module.css`` files and build the manifest.

Flow: compile each file for CSS modules (per-file, scoped by its stable key), then
bundle the *compiled* files together with Lightning CSS's bundler (css-modules off,
so the already-hashed class names are preserved).
"""

import tempfile
from pathlib import Path

from . import _lightningcss_rs as rust
from .conf import ModuleSettings, get_settings
from .discovery import discover_modules
from .exceptions import CompileError
from .manifest import MANIFEST_VERSION, resolve_output_dir, save_manifest

BUNDLE_NAME = "bundle.css"
_ENTRY_NAME = "_bundle_entry.css"


def flatten_exports(exports: dict) -> dict[str, str]:
    """Turn ``{local: {"name", "composes": [...]}}`` into ``{local: "class composed..."}``."""
    return {local: " ".join([data["name"], *data["composes"]]) for local, data in exports.items()}


def compile_source(key: str, path: Path, cfg: ModuleSettings) -> tuple[str, dict[str, str]]:
    """Compile one module -> ``(css, flattened class map)``.

    ``key`` is the stable identifier used for hashing (reproducible across machines).
    """
    css = path.read_text(encoding="utf-8")
    try:
        code, exports = rust.compile(
            css,
            key,
            minify=cfg.minify,
            browsers_list=list(cfg.targets) if cfg.targets else None,
            pattern=cfg.pattern,
            dashed_idents=cfg.dashed_idents,
        )
    except ValueError as exc:
        raise CompileError(f"Failed to compile {path}: {exc}") from exc
    return code, flatten_exports(exports)


def _bundle_dir(directory: Path, keys: list[str], cfg: ModuleSettings) -> str:
    """Bundle already-compiled files in ``directory`` (imported by ``keys``) into one sheet.

    The ``@import`` entry is written to a system temp dir (with absolute paths to the
    compiled files), so the build never writes a transient file into ``directory``.
    """
    with tempfile.TemporaryDirectory() as tmp:
        entry = Path(tmp) / _ENTRY_NAME
        entry.write_text(
            "".join(f'@import "{(directory / key).resolve()}";\n' for key in keys),
            encoding="utf-8",
        )
        try:
            return rust.bundle_entry(
                str(entry),
                minify=cfg.minify,
                browsers_list=list(cfg.targets) if cfg.targets else None,
            )
        except ValueError as exc:
            raise CompileError(f"Failed to bundle CSS modules: {exc}") from exc


def build_bundle(cfg: ModuleSettings | None = None) -> str:
    """Compile every module and return the bundled CSS (no persistent files written)."""
    cfg = cfg or get_settings()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        keys = []
        for key, path in discover_modules(cfg).items():
            code, _ = compile_source(key, path, cfg)
            dest = tmp_dir / key
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(code, encoding="utf-8")
            keys.append(key)
        return _bundle_dir(tmp_dir, keys, cfg)


def compile_all(cfg: ModuleSettings | None = None) -> dict:
    """Compile every module, write per-file CSS + a real bundle + manifest; return the manifest."""
    cfg = cfg or get_settings()
    out_dir = resolve_output_dir(cfg)

    manifest_modules: dict[str, dict] = {}
    keys: list[str] = []
    for key, path in discover_modules(cfg).items():
        code, exports = compile_source(key, path, cfg)
        dest = out_dir / key
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(code, encoding="utf-8")
        manifest_modules[key] = {"css": f"{cfg.output}/{key}", "exports": exports}
        keys.append(key)

    bundle_code = _bundle_dir(out_dir, keys, cfg)
    (out_dir / BUNDLE_NAME).write_text(bundle_code, encoding="utf-8")

    manifest = {
        "version": MANIFEST_VERSION,
        "output": cfg.output,
        "bundle": f"{cfg.output}/{BUNDLE_NAME}",
        "modules": manifest_modules,
    }
    save_manifest(cfg, manifest)
    return manifest
