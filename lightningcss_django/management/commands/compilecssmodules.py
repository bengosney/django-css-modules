"""``manage.py compilecssmodules`` — build scoped CSS + the manifest.

Run this before ``collectstatic`` in your deploy pipeline.
"""

from django.core.management.base import BaseCommand, CommandError

from ...compiler import compile_all
from ...conf import get_settings
from ...exceptions import CssModuleError
from ...manifest import resolve_manifest_path, resolve_output_dir


class Command(BaseCommand):
    help = "Compile *.module.css files into scoped CSS plus a manifest."

    def handle(self, *args, **options):
        cfg = get_settings()
        try:
            manifest = compile_all(cfg)
        except CssModuleError as exc:
            raise CommandError(str(exc)) from exc

        count = len(manifest["modules"])
        out_dir = resolve_output_dir(cfg)
        self.stdout.write(f"Compiled {count} CSS module(s) to {out_dir}")
        self.stdout.write(f"Bundle: {out_dir / 'bundle.css'}")
        self.stdout.write(self.style.SUCCESS(f"Wrote manifest to {resolve_manifest_path(cfg)}"))
