from django.apps import AppConfig


class HealthConfig(AppConfig):
    name = 'health'

    def ready(self):
        import health.signals
