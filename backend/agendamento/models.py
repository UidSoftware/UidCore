from django.conf import settings
from django.db import models

from common.models import BaseModel


class Agenda(BaseModel):
    nome      = models.CharField(max_length=100)
    descricao = models.TextField(blank=True)
    cor       = models.CharField(max_length=7, default='#3B82F6')
    ativo     = models.BooleanField(default=True)

    class Meta:
        db_table = 'age_agenda'
        ordering = ['nome']

    def __str__(self):
        return self.nome


class StatusCompromisso(models.TextChoices):
    AGENDADO   = 'AGENDADO',   'Agendado'
    CONFIRMADO = 'CONFIRMADO', 'Confirmado'
    CANCELADO  = 'CANCELADO',  'Cancelado'
    CONCLUIDO  = 'CONCLUIDO',  'Concluido'


class Compromisso(BaseModel):
    agenda      = models.ForeignKey(Agenda, on_delete=models.PROTECT, related_name='compromissos')
    titulo      = models.CharField(max_length=255)
    descricao   = models.TextField(blank=True)
    inicio      = models.DateTimeField()
    fim         = models.DateTimeField()
    local       = models.CharField(max_length=255, blank=True)
    cliente     = models.ForeignKey(
        'clientes.Cliente', null=True, blank=True,
        on_delete=models.PROTECT, related_name='compromissos',
    )
    status      = models.CharField(
        max_length=10, choices=StatusCompromisso.choices, default='AGENDADO',
    )
    observacoes = models.TextField(blank=True)
    criado_por  = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='+',
    )

    class Meta:
        db_table = 'age_compromisso'
        ordering = ['inicio']

    def __str__(self):
        return f'{self.titulo} — {self.inicio.strftime("%d/%m/%Y %H:%M")}'
