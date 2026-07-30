from rest_framework import serializers

from .models import Agenda, Compromisso


class AgendaSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='pk', read_only=True)

    class Meta:
        model = Agenda
        fields = ['id', 'nome', 'descricao', 'cor', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']


class CompromissoSerializer(serializers.ModelSerializer):
    id           = serializers.IntegerField(source='pk', read_only=True)
    agenda_nome  = serializers.CharField(source='agenda.nome', read_only=True)
    cliente_nome = serializers.CharField(
        source='cliente.nome_razao_social', read_only=True, allow_null=True,
    )
    status_label = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Compromisso
        fields = [
            'id', 'agenda', 'agenda_nome', 'titulo', 'descricao',
            'inicio', 'fim', 'local', 'cliente', 'cliente_nome',
            'status', 'status_label', 'observacoes', 'is_active', 'created_at',
        ]
        read_only_fields = ['id', 'agenda_nome', 'cliente_nome', 'status_label', 'created_at']

    def validate(self, attrs):
        fim = attrs.get('fim')
        inicio = attrs.get('inicio')
        if fim and inicio and fim < inicio:
            raise serializers.ValidationError({'fim': 'Fim deve ser maior ou igual ao inicio.'})
        return attrs
