from django.utils import timezone


class AuditMixin:
    """
    Aplicar em todo ViewSet cujo model herda common.models.BaseModel.
    perform_create/perform_update/perform_destroy gravam quem fez o quê.
    NUNCA remove o registro do banco (instance.delete()) — regra absoluta
    da fábrica (soft delete em todos os models).
    """

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    def perform_destroy(self, instance):
        instance.deleted_at = timezone.now()
        instance.deleted_by = self.request.user
        instance.is_active = False
        instance.save(update_fields=['deleted_at', 'deleted_by', 'is_active', 'updated_at'])
