"""Compile ``*.module.css`` files and build the manifest."""

from pathlib import Path

from . import _lightningcss_rs as rust
from .conf import ModuleSettings, get_settings
from .discovery import discover_modules
from .exceptions import CompileError
from .manifest import MANIFEST_VERSION, resolve_output_dir, save_manifest

BUNDLE_NAME = "bundle.css"


def flatten_exports(exports: dict) -> dict[str, str]:
    """Turn ``{local: {"name", "composes": [...]}}`` into ``{local: "class composed..."}``.

    Same-file ``composes`` references are already resolved to hashed names by the
    native layer, so a class simply becomes its own hashed name followed by any
    composed ones, space-joined for use in a ``class="..."`` attribute.
    """
    return {local: " ".join([data["name"], *data["composes"]]) for local, data in exports.items()}


def compile_source(path: Path, cfg: ModuleSettings) -> tuple[str, dict[str, str]]:
    """Compile a single module file -> ``(css, flattened class map)``."""
    css = path.read_text(encoding="utf-8")
    try:
        code, exports = rust.compile(
            css,
            str(path),
            minify=cfg.minify,
            browsers_list=list(cfg.targets) if cfg.targets else None,
            pattern=cfg.pattern,
            dashed_idents=cfg.dashed_idents,
        )
    except ValueError as exc:
        raise CompileError(f"Failed to compile {path}: {exc}") from exc
    return code, flatten_exports(exports)


def compile_all(cfg: ModuleSettings | None = None) -> dict:
    """Compile every discovered module, write CSS + bundle + manifest, return the manifest."""
    cfg = cfg or get_settings()
    modules = discover_modules(cfg)
    out_dir = resolve_output_dir(cfg)

    manifest_modules: dict[str, dict] = {}
    bundle_parts: list[str] = []

    for key, path in modules.items():
        code, classes = compile_source(path, cfg)
        dest = out_dir / key
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(code, encoding="utf-8")
        manifest_modules[key] = {"css": f"{cfg.output}/{key}", "exports": classes}
        bundle_parts.append(f"/* {key} */\n{code}")

    bundle_code = "\n".join(bundle_parts)
    bundle_dest = out_dir / BUNDLE_NAME
    bundle_dest.parent.mkdir(parents=True, exist_ok=True)
    bundle_dest.write_text(bundle_code, encoding="utf-8")

    manifest = {
        "version": MANIFEST_VERSION,
        "output": cfg.output,
        "bundle": f"{cfg.output}/{BUNDLE_NAME}",
        "modules": manifest_modules,
    }
    save_manifest(cfg, manifest)
    return manifest
