"""On-demand CSS views for development.

These compile modules per request so ``runserver`` needs no build step. In
production you run ``manage.py compilecssmodules`` and serve the output as static
files instead; there is no need to wire these URLs.
"""

from django.http import Http404, HttpResponse

from .compiler import build_bundle, compile_source
from .conf import get_settings
from .discovery import resolve_module
from .exceptions import CssModuleNotFoundError


def module_css(request, key):
    """Serve a single compiled module stylesheet."""
    cfg = get_settings()
    try:
        path = resolve_module(key, cfg)
    except CssModuleNotFoundError as exc:
        raise Http404(str(exc)) from exc
    code, _ = compile_source(path, cfg)
    return HttpResponse(code, content_type="text/css")


def bundle_css(request):
    """Serve every module concatenated into one stylesheet."""
    return HttpResponse(build_bundle(), content_type="text/css")
