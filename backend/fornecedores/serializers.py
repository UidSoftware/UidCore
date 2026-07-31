import re
from rest_framework import serializers
from .models import AcionistaFornecedor, Fornecedor


class AcionistaFornecedorSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='pk', read_only=True)

    class Meta:
        model = AcionistaFornecedor
        fields = ['id', 'nome', 'email', 'cpf', 'telefone', 'whatsapp', 'principal', 'is_active', 'created_at']
        read_only_fields = ['created_at']


class FornecedorSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='pk', read_only=True)
    acionistas = AcionistaFornecedorSerializer(many=True, read_only=True)
    categoria_display = serializers.CharField(source='get_categoria_display', read_only=True)
    tipo_pessoa_display = serializers.CharField(source='get_tipo_pessoa_display', read_only=True)

    class Meta:
        model = Fornecedor
        fields = [
            'id', 'tipo_pessoa', 'tipo_pessoa_display',
            'documento', 'cpf', 'cnpj', 'nome_razao_social',
            'telefone', 'email', 'endereco', 'cidade', 'estado', 'cep',
            'categoria', 'categoria_display',
            'contato_nome', 'contato_telefone', 'website',
            'inscricao_estadual', 'observacoes',
            'is_active', 'created_at', 'updated_at',
            'acionistas',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def validate_documento(self, value):
        if value == '':
            return None
        if value:
            value = re.sub(r'\D', '', value)
        return value
