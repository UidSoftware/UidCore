from django.apps import AppConfig


class FinanceiroConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'financeiro'
    verbose_name = 'Financeiro'

    def ready(self):
        import financeiro.signals  # noqa: F401
        from common.lgpd import registrar_exportador
        from .lgpd import exportar_titular
        registrar_exportador('financeiro', 'Financeiro', exportar_titular)
