from django.apps import AppConfig


class VendasConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'vendas'
    verbose_name = 'Vendas'

    def ready(self):
        from common.lgpd import registrar_exportador
        from .lgpd import exportar_titular
        registrar_exportador('vendas', 'Orçamentos e Pedidos', exportar_titular)
