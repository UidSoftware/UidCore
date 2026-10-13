from django.apps import AppConfig


class ClientesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'clientes'
    verbose_name = 'Clientes'

    def ready(self):
        from common.lgpd import registrar_exportador
        from .lgpd import exportar_titular
        registrar_exportador('clientes', 'Cadastro do Cliente', exportar_titular)
