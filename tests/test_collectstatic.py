"""Verify the compiled output is picked up by collectstatic."""

from io import StringIO

from django.core.management import call_command

from lightningcss_django.manifest import resolve_manifest_path
from lightningcss_django.resolver import get_resolver

CARD = ".container { padding: 1rem; }\n.title { composes: container; font-weight: bold; }\n"

FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
    "lightningcss_django.finders.CssModulesFinder",
]


def test_compilecssmodules_then_collectstatic(settings, tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "card.module.css").write_text(CARD)

    static_src = tmp_path / "assets"  # a STATICFILES_DIRS entry (output lands here)
    static_root = tmp_path / "collected"

    settings.STATIC_URL = "/static/"
    settings.STATIC_ROOT = str(static_root)
    settings.STATICFILES_DIRS = [str(static_src)]
    settings.LIGHTNINGCSS_MODULES = {"dirs": [src]}  # output_root defaults to STATICFILES_DIRS[0]

    # 1. build
    call_command("compilecssmodules", stdout=StringIO())
    # written into the staticfiles source dir
    assert (static_src / "cssmodules" / "card.module.css").is_file()
    assert (static_src / "cssmodules" / "bundle.css").is_file()
    # the temporary bundle entry is cleaned up (won't be collected)
    assert not (static_src / "cssmodules" / "_bundle_entry.css").exists()

    # 2. collectstatic
    call_command("collectstatic", interactive=False, verbosity=0)
    assert (static_root / "cssmodules" / "card.module.css").is_file()
    assert (static_root / "cssmodules" / "bundle.css").is_file()

    # the manifest lives outside the static tree, so it is NOT collected/served
    manifest_path = resolve_manifest_path(get_resolver().cfg)
    assert manifest_path.is_file()
    assert static_root not in manifest_path.parents
    assert not (static_root / "cssmodules.manifest.json").exists()


def test_works_with_manifest_static_files_storage(settings, tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "card.module.css").write_text(CARD)

    settings.STATIC_URL = "/static/"
    settings.STATIC_ROOT = str(tmp_path / "collected")
    settings.STATICFILES_DIRS = [str(tmp_path / "assets")]
    settings.STORAGES = {
        **settings.STORAGES,
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"},
    }
    settings.LIGHTNINGCSS_MODULES = {"dirs": [src]}

    call_command("compilecssmodules", stdout=StringIO())
    call_command("collectstatic", interactive=False, verbosity=0)

    # URL tags resolve through hashed static storage (cache-busting) and the
    # hashed files actually exist on disk.
    resolver = get_resolver()
    url = resolver.css_url("card.module.css")
    bundle_url = resolver.bundle_url()
    assert url != "/static/cssmodules/card.module.css"  # a content hash was inserted
    assert url.startswith("/static/cssmodules/card.") and url.endswith(".css")

    collected = tmp_path / "collected"
    assert (collected / url.removeprefix("/static/")).is_file()
    assert (collected / bundle_url.removeprefix("/static/")).is_file()


def test_finder_makes_collectstatic_compile(settings, tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "card.module.css").write_text(CARD)

    settings.STATIC_URL = "/static/"
    settings.STATIC_ROOT = str(tmp_path / "collected")
    settings.STATICFILES_DIRS = []
    settings.STATICFILES_FINDERS = FINDERS
    settings.LIGHTNINGCSS_MODULES = {
        "dirs": [src],
        "output_root": str(tmp_path / "build"),  # outside STATICFILES_DIRS
    }

    # NOTE: no compilecssmodules call — the finder compiles during collectstatic.
    call_command("collectstatic", interactive=False, verbosity=0)

    collected = tmp_path / "collected"
    assert (collected / "cssmodules" / "card.module.css").is_file()
    assert (collected / "cssmodules" / "bundle.css").is_file()


def test_finder_find_locates_compiled_file(settings, tmp_path):
    from django.contrib.staticfiles import finders

    src = tmp_path / "src"
    src.mkdir()
    (src / "card.module.css").write_text(CARD)

    settings.STATICFILES_DIRS = []
    settings.STATICFILES_FINDERS = FINDERS
    settings.LIGHTNINGCSS_MODULES = {"dirs": [src], "output_root": str(tmp_path / "build")}

    found = finders.find("cssmodules/card.module.css")
    assert found is not None
    assert found.endswith("cssmodules/card.module.css")
