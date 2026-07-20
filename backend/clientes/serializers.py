import re
from rest_framework import serializers
from .models import Cliente, HistoricoCliente


class HistoricoClienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = HistoricoCliente
        fields = ['id', 'descricao', 'data']
        read_only_fields = ['id', 'data']


class ClienteSerializer(serializers.ModelSerializer):
    historico = HistoricoClienteSerializer(many=True, read_only=True)
    segmento_display = serializers.CharField(source='get_segmento_display', read_only=True)
    tipo_pessoa_display = serializers.CharField(source='get_tipo_pessoa_display', read_only=True)

    class Meta:
        model = Cliente
        fields = [
            'id', 'tipo_pessoa', 'tipo_pessoa_display',
            'documento', 'nome_razao_social',
            'telefone', 'email', 'endereco', 'cidade', 'estado', 'cep',
            'segmento', 'segmento_display', 'data_nascimento',
            'origem', 'limite_credito', 'observacoes',
            'is_active', 'created_at', 'updated_at',
            'historico',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_documento(self, value):
        if value == '':
            return None
        if value:
            value = re.sub(r'\D', '', value)
        return value
