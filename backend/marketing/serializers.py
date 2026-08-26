from rest_framework import serializers

from .models import Campanha, Lead, StatusLead


class CampanhaSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='pk', read_only=True)
    canal_display = serializers.CharField(source='get_canal_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Campanha
        fields = [
            'id', 'nome', 'canal', 'canal_display', 'data_inicio', 'data_fim',
            'orcamento', 'status', 'status_display', 'is_active',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


class LeadSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='pk', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    campanha_nome = serializers.CharField(source='campanha.nome', read_only=True, default=None)
    cliente_convertido_nome = serializers.CharField(
        source='cliente_convertido.nome_razao_social', read_only=True, default=None,
    )

    class Meta:
        model = Lead
        fields = [
            'id', 'nome', 'email', 'telefone', 'campanha', 'campanha_nome',
            'observacoes', 'status', 'status_display',
            'cliente_convertido', 'cliente_convertido_nome',
            'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['cliente_convertido', 'created_at', 'updated_at']

    def validate_status(self, value):
        # RN06 — conversão é irreversível via API. A troca convertido -> outro
        # status só acontece pela action /converter/ (que nunca desfaz), nunca
        # por PATCH direto no serializer.
        if self.instance and self.instance.status == StatusLead.CONVERTIDO and value != StatusLead.CONVERTIDO:
            raise serializers.ValidationError('Lead já convertido não pode voltar para outro status.')
        return value
