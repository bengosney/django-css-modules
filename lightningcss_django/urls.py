"""URLs for the development on-demand CSS views.

Include under any prefix, e.g.::

    path("cssmodules/", include("lightningcss_django.urls")),

Only needed when serving compiled CSS on demand (typically ``DEBUG``); production
serves the prebuilt files from ``compilecssmodules`` as static assets.
"""

from django.urls import path

from . import views

app_name = "lightningcss_django"

urlpatterns = [
    # bundle.css must precede the catch-all so it isn't swallowed by <path:key>.
    path("bundle.css", views.bundle_css, name="bundle"),
    path("<path:key>", views.module_css, name="module"),
]
