from rest_framework import serializers


class AuditFieldsMixin(serializers.Serializer):
    """
    Mixin para serializers de model que herda common.models.BaseModel.
    Expõe apenas o nome de quem criou/alterou — nunca o FK cru
    (created_by/updated_by), que não é gravável via payload (RN-03).
    """

    created_by_nome = serializers.CharField(
        source='created_by.nome_completo', read_only=True, default=''
    )
    updated_by_nome = serializers.CharField(
        source='updated_by.nome_completo', read_only=True, default=''
    )
