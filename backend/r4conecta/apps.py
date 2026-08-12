from django.apps import AppConfig


class R4ConectaConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "r4conecta"
    verbose_name = "R4 Conecta (Mibanco)"

    def ready(self):
        # Los cobros que el banco deja "en proceso" se confirman solos desde
        # aquí: sin cron y sin comandos. Ver r4conecta/vigilante.py.
        from . import vigilante
        vigilante.iniciar()
