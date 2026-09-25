"""Runtime resolution of class names and CSS URLs for template tags.

Two strategies behind one interface:

* production reads the prebuilt manifest (mtime-cached), URLs go through ``static()``;
* ``DEBUG`` compiles on demand (cached by file mtime) and serves CSS via a view.
"""

from django.conf import settings
from django.templatetags.static import static
from django.urls import reverse

from .compiler import compile_source
from .conf import ModuleSettings, get_settings
from .discovery import resolve_module
from .exceptions import CssModuleNotFoundError
from .manifest import load_manifest

URL_NAMESPACE = "lightningcss_django"


class BaseResolver:
    def __init__(self, cfg: ModuleSettings) -> None:
        self.cfg = cfg

    def classes(self, key: str) -> dict[str, str]:  # pragma: no cover - interface
        raise NotImplementedError

    def css_url(self, key: str) -> str:  # pragma: no cover - interface
        raise NotImplementedError

    def bundle_url(self) -> str:  # pragma: no cover - interface
        raise NotImplementedError


class ManifestResolver(BaseResolver):
    """Production: everything comes from the compiled manifest."""

    def _module(self, key: str) -> dict:
        modules = load_manifest(self.cfg)["modules"]
        try:
            return modules[key]
        except KeyError:
            raise CssModuleNotFoundError(f"CSS module {key!r} is not in the manifest.") from None

    def classes(self, key: str) -> dict[str, str]:
        return self._module(key)["exports"]

    def css_url(self, key: str) -> str:
        return static(self._module(key)["css"])

    def bundle_url(self) -> str:
        return static(load_manifest(self.cfg)["bundle"])


class DevResolver(BaseResolver):
    """DEBUG: compile on demand, cache by (key, mtime); CSS served by a view."""

    def __init__(self, cfg: ModuleSettings) -> None:
        super().__init__(cfg)
        self._cache: dict[str, tuple[float, dict[str, str]]] = {}

    def classes(self, key: str) -> dict[str, str]:
        path = resolve_module(key, self.cfg)
        mtime = path.stat().st_mtime
        hit = self._cache.get(key)
        if hit is None or hit[0] != mtime:
            _, classes = compile_source(path, self.cfg)
            self._cache[key] = (mtime, classes)
        return self._cache[key][1]

    def css_url(self, key: str) -> str:
        resolve_module(key, self.cfg)  # validate it exists (raises CssModuleNotFoundError)
        return reverse(f"{URL_NAMESPACE}:module", kwargs={"key": key})

    def bundle_url(self) -> str:
        return reverse(f"{URL_NAMESPACE}:bundle")


_resolver: BaseResolver | None = None


def get_resolver() -> BaseResolver:
    """Return the process-wide resolver for the current settings."""
    global _resolver
    if _resolver is None:
        cfg = get_settings()
        _resolver = DevResolver(cfg) if getattr(settings, "DEBUG", False) else ManifestResolver(cfg)
    return _resolver


def reset_resolver(**kwargs) -> None:
    """Drop the cached resolver (called on ``setting_changed``)."""
    global _resolver
    _resolver = None
