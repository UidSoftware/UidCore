import re
from rest_framework import serializers
from common.serializers import AuditFieldsMixin
from .models import AcionistaCliente, Cliente, HistoricoCliente


class HistoricoClienteSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='pk', read_only=True)

    class Meta:
        model = HistoricoCliente
        fields = ['id', 'descricao', 'created_at']
        read_only_fields = ['created_at']


class AcionistaClienteSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='pk', read_only=True)

    class Meta:
        model = AcionistaCliente
        fields = ['id', 'nome', 'email', 'cpf', 'telefone', 'whatsapp', 'principal', 'is_active', 'created_at']
        read_only_fields = ['created_at']


class ClienteSerializer(AuditFieldsMixin, serializers.ModelSerializer):
    id = serializers.IntegerField(source='pk', read_only=True)
    historico = HistoricoClienteSerializer(many=True, read_only=True)
    acionistas = AcionistaClienteSerializer(many=True, read_only=True)
    segmento_display = serializers.CharField(source='get_segmento_display', read_only=True)
    tipo_pessoa_display = serializers.CharField(source='get_tipo_pessoa_display', read_only=True)
    anonimizado_por_nome = serializers.CharField(
        source='anonimizado_por.nome_completo', read_only=True, default=''
    )

    class Meta:
        model = Cliente
        fields = [
            'id', 'tipo_pessoa', 'tipo_pessoa_display',
            'documento', 'cpf', 'cnpj', 'nome_razao_social',
            'telefone', 'email', 'endereco', 'cidade', 'estado', 'cep',
            'segmento', 'segmento_display', 'data_nascimento',
            'origem', 'limite_credito', 'observacoes',
            'is_active', 'created_at', 'updated_at',
            'created_by_nome', 'updated_by_nome',
            'historico', 'acionistas',
            'anonimizado', 'anonimizado_em', 'anonimizado_por_nome',
        ]
        read_only_fields = [
            'created_at', 'updated_at',
            'anonimizado', 'anonimizado_em',
        ]

    def validate_documento(self, value):
        if value == '':
            return None
        if value:
            value = re.sub(r'\D', '', value)
        return value
