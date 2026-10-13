from django.apps import AppConfig


class PortalConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'portal'
    verbose_name = 'Portal do Cliente'

    def ready(self):
        from common.lgpd import registrar_exportador
        from .lgpd import exportar_titular
        registrar_exportador('portal', 'Acessos ao Portal do Cliente', exportar_titular)
