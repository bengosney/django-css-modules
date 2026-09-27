"""Root URLconf for the test suite."""

from django.urls import include, path

urlpatterns = [
    path("cssmodules/", include("django_css_modules.urls")),
]
