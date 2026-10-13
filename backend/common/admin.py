from django.contrib import admin

from .models import ExportacaoTitular


class AuditModelAdmin(admin.ModelAdmin):
    """
    ModelAdmin base para models que herdam common.models.BaseModel.
    Usa all_objects (manager sem filtro de deleted_at) para que o
    Django Admin continue vendo registros excluídos via soft delete —
    diferente da API, que usa o manager padrão (objects) e nunca
    retorna registros com deleted_at preenchido.
    """

    def get_queryset(self, request):
        return self.model.all_objects.all()


@admin.register(ExportacaoTitular)
class ExportacaoTitularAdmin(AuditModelAdmin):
    list_display = ['cliente', 'formato', 'created_by', 'created_at']
    list_filter = ['formato', 'created_at']
    search_fields = ['cliente__nome_razao_social', 'cliente__documento']
    readonly_fields = ['cliente', 'formato', 'conteudo_resumo', 'created_by', 'created_at']

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
