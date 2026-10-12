"""
assinaturas/serializers.py — Manutencao #64 [NUCLEO 3/5].
"""
from rest_framework import serializers

from common.serializers import AuditFieldsMixin

from .models import Assinatura, Plano


class PlanoSerializer(AuditFieldsMixin, serializers.ModelSerializer):
    id = serializers.IntegerField(source='pk', read_only=True)
    categoria_nome = serializers.CharField(source='categoria.nome', read_only=True)

    class Meta:
        model = Plano
        fields = [
            'id', 'nome', 'descricao', 'valor', 'periodicidade',
            'categoria', 'categoria_nome', 'ativo',
            'is_active', 'created_at', 'updated_at',
            'created_by_nome', 'updated_by_nome',
        ]
        read_only_fields = ['is_active', 'created_at', 'updated_at']


class AssinaturaSerializer(AuditFieldsMixin, serializers.ModelSerializer):
    id = serializers.IntegerField(source='pk', read_only=True)
    cliente_nome = serializers.CharField(source='cliente.nome_razao_social', read_only=True)
    plano_nome = serializers.CharField(source='plano.nome', read_only=True)
    conta_nome = serializers.CharField(source='conta.nome', read_only=True)
    # RF-03: valor é snapshot do Plano, não obrigatório no payload — se
    # omitido, create() abaixo copia de plano.valor. Editável quando
    # enviado explicitamente (desconto negociado).
    valor = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)

    class Meta:
        model = Assinatura
        fields = [
            'id', 'cliente', 'cliente_nome', 'plano', 'plano_nome',
            'valor', 'dia_vencimento', 'data_inicio', 'data_fim',
            'status', 'conta', 'conta_nome',
            'motivo_encerramento', 'encerrada_em',
            'is_active', 'created_at', 'updated_at',
            'created_by_nome', 'updated_by_nome',
        ]
        # RN-10: status/motivo_encerramento/encerrada_em só mudam via
        # actions dedicadas (encerrar/pausar/retomar, em views.py) — nunca
        # por create/update genérico deste serializer, mesmo que o campo
        # venha no payload (DRF simplesmente ignora campo read_only).
        read_only_fields = [
            'status', 'motivo_encerramento', 'encerrada_em',
            'is_active', 'created_at', 'updated_at',
        ]

    def validate(self, data):
        data_inicio = data.get('data_inicio', getattr(self.instance, 'data_inicio', None))
        data_fim = data.get('data_fim', getattr(self.instance, 'data_fim', None))
        if data_fim and data_inicio and data_fim < data_inicio:
            raise serializers.ValidationError(
                {'data_fim': 'Não pode ser anterior à data de início.'}
            )
        return data

    def create(self, validated_data):
        if not validated_data.get('valor'):
            validated_data['valor'] = validated_data['plano'].valor
        return super().create(validated_data)
