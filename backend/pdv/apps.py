from django.apps import AppConfig


class PdvConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'pdv'
    verbose_name = 'PDV — Ponto de Venda'

    def ready(self):
        from common.lgpd import registrar_exportador
        from .lgpd import exportar_titular
        registrar_exportador('pdv', 'Vendas de Balcão (PDV)', exportar_titular)
