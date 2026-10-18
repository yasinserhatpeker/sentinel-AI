from django.apps import AppConfig


class DemoConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "demo"

    def ready(self) -> None:
        from .telemetry import configure_telemetry

        configure_telemetry()

