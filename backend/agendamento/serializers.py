import re
from datetime import date, datetime, timedelta

from django.utils.text import slugify
from rest_framework import serializers

from common.serializers import AuditFieldsMixin

from .models import (
    Agenda, Compromisso, DiaSemana, HorarioDisponivel,
    OrigemCompromisso, StatusCompromisso,
)


class AgendaSerializer(AuditFieldsMixin, serializers.ModelSerializer):
    id = serializers.IntegerField(source='pk', read_only=True)
    profissional_nome = serializers.CharField(
        source='profissional.nome_completo', read_only=True, allow_null=True,
    )

    class Meta:
        model = Agenda
        fields = [
            'id', 'nome', 'descricao', 'cor', 'profissional', 'profissional_nome',
            'slug', 'permite_agendamento_publico',
            'is_active', 'created_at', 'created_by_nome', 'updated_by_nome',
        ]
        read_only_fields = ['id', 'created_at']

    def validate_slug(self, value):
        if not value:
            return value
        qs = Agenda.objects.filter(slug=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('Este slug já está em uso por outra agenda.')
        return value

    def validate(self, attrs):
        # Gera slug automaticamente no POST se nao enviado
        if not self.instance and not attrs.get('slug'):
            nome = attrs.get('nome', '')
            if nome:
                base_slug = slugify(nome)
                slug = base_slug
                n = 1
                while Agenda.objects.filter(slug=slug).exists():
                    slug = f'{base_slug}-{n}'
                    n += 1
                attrs['slug'] = slug
        return attrs


class HorarioDisponivelSerializer(AuditFieldsMixin, serializers.ModelSerializer):
    id = serializers.IntegerField(source='pk', read_only=True)
    agenda_nome = serializers.CharField(source='agenda.nome', read_only=True)
    dia_semana_label = serializers.CharField(
        source='get_dia_semana_display', read_only=True,
    )

    class Meta:
        model = HorarioDisponivel
        fields = [
            'id', 'agenda', 'agenda_nome', 'dia_semana', 'dia_semana_label',
            'hora_inicio', 'duracao_minutos', 'vagas', 'servico', 'publico',
            'ativo', 'is_active', 'created_at', 'created_by_nome', 'updated_by_nome',
        ]
        read_only_fields = ['id', 'agenda_nome', 'dia_semana_label', 'created_at']

    def validate(self, attrs):
        duracao = attrs.get('duracao_minutos', getattr(self.instance, 'duracao_minutos', None))
        vagas = attrs.get('vagas', getattr(self.instance, 'vagas', None))
        if duracao is not None and duracao < 5:
            raise serializers.ValidationError({'duracao_minutos': 'Duração mínima é 5 minutos.'})
        if vagas is not None and vagas < 1:
            raise serializers.ValidationError({'vagas': 'Mínimo de 1 vaga.'})
        return attrs


class CompromissoSerializer(AuditFieldsMixin, serializers.ModelSerializer):
    id           = serializers.IntegerField(source='pk', read_only=True)
    agenda_nome  = serializers.CharField(source='agenda.nome', read_only=True)
    cliente_nome = serializers.CharField(
        source='cliente.nome_razao_social', read_only=True, allow_null=True,
    )
    status_label = serializers.CharField(source='get_status_display', read_only=True)
    origem_label = serializers.CharField(source='get_origem_display', read_only=True)
    vagas_restantes = serializers.SerializerMethodField(read_only=True)
    horario_servico = serializers.CharField(
        source='horario.servico', read_only=True, allow_null=True,
    )

    class Meta:
        model = Compromisso
        fields = [
            'id', 'agenda', 'agenda_nome', 'titulo', 'descricao',
            'inicio', 'fim', 'local', 'cliente', 'cliente_nome',
            'status', 'status_label', 'observacoes',
            'horario', 'horario_servico', 'data_horario',
            'origem', 'origem_label',
            'nome_contato', 'telefone_contato', 'email_contato',
            'vagas_restantes',
            'is_active', 'created_at', 'created_by_nome', 'updated_by_nome',
        ]
        read_only_fields = [
            'id', 'agenda_nome', 'cliente_nome', 'status_label', 'origem_label',
            'horario_servico', 'vagas_restantes', 'created_at',
        ]

    def get_vagas_restantes(self, obj):
        if not obj.horario_id or not obj.data_horario:
            return None
        ocupados = Compromisso.objects.filter(
            horario_id=obj.horario_id,
            data_horario=obj.data_horario,
            is_active=True,
        ).exclude(status=StatusCompromisso.CANCELADO).count()
        return max(0, obj.horario.vagas - ocupados)

    def validate(self, attrs):
        fim = attrs.get('fim')
        inicio = attrs.get('inicio')
        if fim and inicio and fim < inicio:
            raise serializers.ValidationError({'fim': 'Fim deve ser maior ou igual ao inicio.'})

        horario = attrs.get('horario', getattr(self.instance, 'horario', None))
        data_horario = attrs.get('data_horario', getattr(self.instance, 'data_horario', None))
        if horario and not data_horario:
            raise serializers.ValidationError(
                {'data_horario': 'data_horario é obrigatório quando horario for informado.'}
            )
        if horario and data_horario:
            _validar_dia_semana(horario, data_horario)
        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Aviso de conflito para o mesmo cliente (RN-09 — só quando cliente for informado)
        request = self.context.get('request')
        if (
            request and request.method in ('POST',)
            and instance.cliente_id
            and instance.inicio
            and instance.fim
        ):
            conflito = Compromisso.objects.filter(
                cliente_id=instance.cliente_id,
                is_active=True,
                inicio__lt=instance.fim,
                fim__gt=instance.inicio,
            ).exclude(status=StatusCompromisso.CANCELADO).exclude(pk=instance.pk).exists()
            if conflito:
                data['aviso'] = 'Cliente já possui compromisso no mesmo período.'
        return data


def _validar_dia_semana(horario, data_horario):
    """Valida que data_horario bate com o dia_semana do HorarioDisponivel."""
    if isinstance(data_horario, str):
        data_horario = date.fromisoformat(data_horario)
    dia_da_semana_da_data = data_horario.weekday()  # 0=Seg, 6=Dom
    if dia_da_semana_da_data != horario.dia_semana:
        nomes = dict(DiaSemana.choices)
        esperado = nomes.get(horario.dia_semana, str(horario.dia_semana))
        raise serializers.ValidationError({
            'data_horario': (
                f'A data informada ({data_horario.strftime("%d/%m/%Y")}) '
                f'não é {esperado}. O horário selecionado é para {esperado}s.'
            )
        })


# ---------------------------------------------------------------------------
# Serializer para agendamento público (AllowAny)
# ---------------------------------------------------------------------------

class AgendamentoPublicoSerializer(serializers.Serializer):
    horario_id       = serializers.IntegerField()
    data_horario     = serializers.DateField()
    nome_contato     = serializers.CharField(max_length=255)
    telefone_contato = serializers.CharField(max_length=20)
    email_contato    = serializers.EmailField(required=False, allow_blank=True, default='')

    # Guardado pelo validate() para reuso na view sem novo lookup
    _horario_obj = None

    def validate_telefone_contato(self, value):
        apenas_digitos = re.sub(r'\D', '', value)
        if len(apenas_digitos) < 8:
            raise serializers.ValidationError(
                'Telefone deve conter no mínimo 8 dígitos.'
            )
        return value

    def validate(self, attrs):
        slug = self.context.get('slug')
        horario_id = attrs['horario_id']
        data_horario = attrs['data_horario']

        try:
            horario = HorarioDisponivel.objects.select_related('agenda').get(pk=horario_id)
        except HorarioDisponivel.DoesNotExist:
            raise serializers.ValidationError({'horario_id': 'Horário não encontrado.'})

        if horario.agenda.slug != slug:
            raise serializers.ValidationError({'horario_id': 'Horário não pertence a esta agenda.'})

        if not horario.publico:
            raise serializers.ValidationError({'horario_id': 'Este horário não está disponível para agendamento público.'})

        if not horario.ativo:
            raise serializers.ValidationError({'horario_id': 'Este horário não está ativo.'})

        _validar_dia_semana(horario, data_horario)

        attrs['_horario_obj'] = horario
        return attrs
