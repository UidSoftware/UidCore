from django.apps import AppConfig


class AgendamentoConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'agendamento'
    verbose_name = 'Agendamento'

    def ready(self):
        from common.lgpd import registrar_exportador
        from .lgpd import exportar_titular
        registrar_exportador('agendamento', 'Agendamento', exportar_titular)
