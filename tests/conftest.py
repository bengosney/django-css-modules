"""Shared fixtures for the test suite."""

import pytest

CARD = ".container { padding: 1rem; }\n.title { composes: container; font-weight: bold; }\n"
BUTTON = ".primary { color: rebeccapurple; }\n"


@pytest.fixture
def project(settings, tmp_path):
    """A configured source tree with two modules; returns the temp root."""
    src = tmp_path / "src"
    (src / "components").mkdir(parents=True)
    (src / "card.module.css").write_text(CARD)
    (src / "components" / "button.module.css").write_text(BUTTON)
    settings.STATIC_URL = "/static/"
    settings.CSS_MODULES = {
        "dirs": [src],
        "output_root": tmp_path / "static",
        "minify": False,
    }
    return tmp_path
