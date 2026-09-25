"""Root URLconf for the test suite."""

from django.urls import include, path

urlpatterns = [
    path("cssmodules/", include("lightningcss_django.urls")),
]
