from django.db import models

from common.models import BaseModel


class CanalCampanha(models.TextChoices):
    ADS = 'ads', 'Ads'
    REDES_SOCIAIS = 'redes_sociais', 'Redes Sociais'
    EMAIL = 'email', 'E-mail'
    ORGANICO = 'organico', 'Orgânico'
    OUTRO = 'outro', 'Outro'


class StatusCampanha(models.TextChoices):
    PLANEJADA = 'planejada', 'Planejada'
    ATIVA = 'ativa', 'Ativa'
    ENCERRADA = 'encerrada', 'Encerrada'


class Campanha(BaseModel):
    nome = models.CharField('nome', max_length=255)
    canal = models.CharField('canal', max_length=20, choices=CanalCampanha.choices)
    data_inicio = models.DateField('data de início')
    data_fim = models.DateField('data de fim', null=True, blank=True)
    orcamento = models.DecimalField('orçamento', max_digits=12, decimal_places=2, default=0)
    status = models.CharField(
        'status', max_length=10, choices=StatusCampanha.choices, default=StatusCampanha.PLANEJADA,
    )

    class Meta:
        db_table = 'marketing_campanha'
        verbose_name = 'Campanha'
        verbose_name_plural = 'Campanhas'
        ordering = ['-created_at']

    def __str__(self):
        return self.nome


class StatusLead(models.TextChoices):
    NOVO = 'novo', 'Novo'
    QUALIFICADO = 'qualificado', 'Qualificado'
    CONVERTIDO = 'convertido', 'Convertido'
    DESCARTADO = 'descartado', 'Descartado'


class Lead(BaseModel):
    nome = models.CharField('nome', max_length=200)
    email = models.EmailField('e-mail', blank=True)
    telefone = models.CharField('telefone', max_length=20, blank=True)
    campanha = models.ForeignKey(
        Campanha, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='leads',
    )
    observacoes = models.TextField('observações', blank=True)
    status = models.CharField(
        'status', max_length=12, choices=StatusLead.choices, default=StatusLead.NOVO,
    )
    cliente_convertido = models.ForeignKey(
        'clientes.Cliente', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='leads_origem',
    )

    class Meta:
        db_table = 'marketing_lead'
        verbose_name = 'Lead'
        verbose_name_plural = 'Leads'
        ordering = ['-created_at']

    def __str__(self):
        return self.nome
