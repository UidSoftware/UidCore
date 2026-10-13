from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.text import slugify

from common.models import BaseModel


class Agenda(BaseModel):
    nome      = models.CharField(max_length=100, blank=True)
    descricao = models.TextField(blank=True)
    cor       = models.CharField(max_length=7, default='#3B82F6')
    profissional = models.ForeignKey(            # Manutencao 63 (RF-05)
        settings.AUTH_USER_MODEL, verbose_name='profissional responsável',
        null=True, blank=True, on_delete=models.SET_NULL, related_name='agendas_vinculadas',
    )
    # Manutencao 65 [NUCLEO 4/5] — agendamento publico
    slug = models.SlugField(
        max_length=100, unique=True, blank=True,
        help_text='Identificador unico para URL publica. Gerado automaticamente a partir do nome.',
    )
    permite_agendamento_publico = models.BooleanField(
        default=False,
        verbose_name='permite agendamento público',
    )

    class Meta:
        db_table = 'age_agenda'
        ordering = ['nome']

    def save(self, *args, **kwargs):
        if not self.slug and self.nome:
            base_slug = slugify(self.nome)
            slug = base_slug
            n = 1
            while Agenda.all_objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f'{base_slug}-{n}'
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nome


class DiaSemana(models.IntegerChoices):
    SEG = 0, 'Segunda'
    TER = 1, 'Terça'
    QUA = 2, 'Quarta'
    QUI = 3, 'Quinta'
    SEX = 4, 'Sexta'
    SAB = 5, 'Sábado'
    DOM = 6, 'Domingo'


class HorarioDisponivel(BaseModel):
    """Grade de horários recorrentes por agenda (Manutencao 65 [NUCLEO 4/5])."""
    agenda          = models.ForeignKey(
        Agenda, on_delete=models.PROTECT, related_name='horarios',
    )
    dia_semana      = models.IntegerField(choices=DiaSemana.choices)
    hora_inicio     = models.TimeField()
    duracao_minutos = models.PositiveIntegerField(validators=[MinValueValidator(5)])
    vagas           = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    servico         = models.CharField(max_length=255, blank=True)
    publico         = models.BooleanField(default=True)
    ativo           = models.BooleanField(
        default=True,
        help_text='Indica se este horário está sendo ofertado. Distinto do is_active (soft delete).',
    )

    class Meta:
        db_table = 'age_horario_disponivel'
        ordering = ['dia_semana', 'hora_inicio']

    def __str__(self):
        dia = DiaSemana(self.dia_semana).label
        return f'{self.agenda.nome} — {dia} {self.hora_inicio} ({self.servico})'


class StatusCompromisso(models.TextChoices):
    AGENDADO   = 'AGENDADO',   'Agendado'
    CONFIRMADO = 'CONFIRMADO', 'Confirmado'
    CANCELADO  = 'CANCELADO',  'Cancelado'
    CONCLUIDO  = 'CONCLUIDO',  'Concluido'


class OrigemCompromisso(models.TextChoices):
    INTERNO = 'INTERNO', 'Interno'
    PUBLICO = 'PUBLICO', 'Público'


class Compromisso(BaseModel):
    agenda      = models.ForeignKey(
        Agenda, null=True, blank=True, on_delete=models.PROTECT, related_name='compromissos',
    )
    titulo      = models.CharField(max_length=255, blank=True)
    descricao   = models.TextField(blank=True)
    inicio      = models.DateTimeField(null=True, blank=True)
    fim         = models.DateTimeField(null=True, blank=True)
    local       = models.CharField(max_length=255, blank=True)
    cliente     = models.ForeignKey(
        'clientes.Cliente', null=True, blank=True,
        on_delete=models.PROTECT, related_name='compromissos',
    )
    status      = models.CharField(
        max_length=10, choices=StatusCompromisso.choices, default='AGENDADO',
    )
    observacoes = models.TextField(blank=True)
    # Manutencao 65 [NUCLEO 4/5] — campos de horario e agendamento publico
    horario     = models.ForeignKey(
        HorarioDisponivel, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='compromissos',
    )
    data_horario = models.DateField(
        null=True, blank=True,
        help_text='Data concreta do slot (necessaria pois HorarioDisponivel define dia da semana, nao data absoluta).',
    )
    origem      = models.CharField(
        max_length=10, choices=OrigemCompromisso.choices, default=OrigemCompromisso.INTERNO,
    )
    nome_contato     = models.CharField(max_length=255, blank=True)
    telefone_contato = models.CharField(max_length=20, blank=True)
    email_contato    = models.EmailField(blank=True)

    class Meta:
        db_table = 'age_compromisso'
        ordering = ['inicio']

    def __str__(self):
        if self.inicio:
            return f'{self.titulo} — {self.inicio.strftime("%d/%m/%Y %H:%M")}'
        return self.titulo
