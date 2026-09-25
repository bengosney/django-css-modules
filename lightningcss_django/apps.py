from django.apps import AppConfig


class LightningCssConfig(AppConfig):
    name = "lightningcss_django"
    verbose_name = "Lightning CSS Modules"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self) -> None:
        from django.core.signals import setting_changed

        from .manifest import clear_cache
        from .resolver import reset_resolver

        setting_changed.connect(reset_resolver, weak=False)
        setting_changed.connect(clear_cache, weak=False)
