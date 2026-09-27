"""A staticfiles finder that compiles CSS modules as part of collectstatic.

Add it to ``STATICFILES_FINDERS`` and ``collectstatic`` will compile the modules
and hand the results over — no separate ``compilecssmodules`` step needed::

    STATICFILES_FINDERS = [
        "django.contrib.staticfiles.finders.FileSystemFinder",
        "django.contrib.staticfiles.finders.AppDirectoriesFinder",
        "django_css_modules.finders.CssModulesFinder",
    ]

The compiled output must live OUTSIDE ``STATICFILES_DIRS`` (set
``CSS_MODULES['output_root']`` to a build dir), otherwise both
``FileSystemFinder`` and this finder report the files and they get collected twice.
"""

from pathlib import Path

from django.conf import settings
from django.contrib.staticfiles.finders import BaseFinder
from django.core.checks import Warning as CheckWarning
from django.core.exceptions import ImproperlyConfigured
from django.core.files.storage import FileSystemStorage

from .compiler import compile_all
from .conf import get_settings
from .manifest import resolve_output_dir, resolve_output_root


class CssModulesFinder(BaseFinder):
    """Compile CSS modules and expose the output to ``collectstatic`` / ``static()``."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._found_compiled = False

    def _output(self) -> tuple[str, Path]:
        cfg = get_settings()
        return cfg.output, resolve_output_dir(cfg)

    def list(self, ignore_patterns):
        """Compile, then yield ``(path, storage)`` for every produced file."""
        compile_all()
        prefix, out_dir = self._output()
        storage = FileSystemStorage(location=str(out_dir))
        storage.prefix = prefix
        for path in sorted(out_dir.rglob("*")):
            if path.is_file():
                yield path.relative_to(out_dir).as_posix(), storage

    def find(self, path, all=False, **kwargs):
        """Locate a compiled file by its static path (e.g. ``cssmodules/card.module.css``)."""
        find_all = kwargs.get("find_all", all)
        if not self._found_compiled:
            compile_all()
            self._found_compiled = True

        prefix, out_dir = self._output()
        norm = path.replace("\\", "/")
        matches: list[str] = []
        if norm.startswith(f"{prefix}/"):
            candidate = out_dir / norm[len(prefix) + 1 :]
            if candidate.is_file():
                matches.append(str(candidate))
        if find_all:
            return matches
        return matches[0] if matches else None

    def check(self, **kwargs):
        try:
            out_root = resolve_output_root(get_settings())
        except ImproperlyConfigured:
            return []

        errors = []
        for entry in getattr(settings, "STATICFILES_DIRS", None) or []:
            base = Path(entry[1] if isinstance(entry, (tuple, list)) else entry)
            if out_root == base or base in out_root.parents:
                errors.append(
                    CheckWarning(
                        "CSS_MODULES['output_root'] is inside STATICFILES_DIRS, so "
                        "compiled files will be collected twice. Point output_root at a build "
                        "directory outside STATICFILES_DIRS when using CssModulesFinder.",
                        id="django_css_modules.W001",
                    )
                )
        return errors
