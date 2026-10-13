from django.apps import AppConfig


class AssinaturasConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'assinaturas'
    verbose_name = 'Assinaturas'

    def ready(self):
        from common.lgpd import registrar_exportador
        from .lgpd import exportar_titular
        registrar_exportador('assinaturas', 'Planos e Assinaturas', exportar_titular)
