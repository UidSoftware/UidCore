from rest_framework import serializers

from common.serializers import AuditFieldsMixin

from .models import Documento, TipoDocumento


class TipoDocumentoSerializer(AuditFieldsMixin, serializers.ModelSerializer):
    id = serializers.IntegerField(source='pk', read_only=True)

    class Meta:
        model = TipoDocumento
        fields = ['id', 'nome', 'descricao', 'is_active', 'created_at', 'created_by_nome', 'updated_by_nome']
        read_only_fields = ['id', 'created_at']


class DocumentoSerializer(AuditFieldsMixin, serializers.ModelSerializer):
    id           = serializers.IntegerField(source='pk', read_only=True)
    tipo_nome    = serializers.CharField(source='tipo.nome', read_only=True)
    cliente_nome = serializers.CharField(
        source='cliente.nome_razao_social', read_only=True, allow_null=True,
    )
    status_label = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Documento
        fields = [
            'id', 'titulo', 'tipo', 'tipo_nome', 'arquivo',
            'cliente', 'cliente_nome', 'descricao', 'status', 'status_label',
            'validade', 'is_active', 'created_at',
            'created_by_nome', 'updated_by_nome',
        ]
        read_only_fields = ['id', 'tipo_nome', 'cliente_nome', 'status_label', 'is_active', 'created_at']
