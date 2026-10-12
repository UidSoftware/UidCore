from django.contrib import admin


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
