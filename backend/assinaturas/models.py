"""
assinaturas/models.py — Manutencao #64 [NUCLEO 3/5].

Mensalidade recorrente com contrato ativo. Origem: lição real do NosFluir
(Studio Fluir) — cron de mensalidade continuou gerando cobrança 2 meses
depois do contrato do aluno ter sido encerrado porque a rotina de geração
não consultava fim/status do contrato antes de criar a cobrança do mês
(RN-03/RN-04 em assinaturas/services.py fecham essa lacuna de vez).

Plano/Assinatura herdam common.models.BaseModel — soft delete via
AuditMixin nos ViewSets, nunca .delete() físico.
"""
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from common.models import BaseModel


class Periodicidade(models.TextChoices):
    MENSAL = 'MENSAL', 'Mensal'
    TRIMESTRAL = 'TRIMESTRAL', 'Trimestral'
    SEMESTRAL = 'SEMESTRAL', 'Semestral'
    ANUAL = 'ANUAL', 'Anual'


# Usado por assinaturas/services.py (RN-05) para calcular o intervalo de
# meses de competência a partir de data_inicio.
INTERVALO_MESES_POR_PERIODICIDADE = {
    Periodicidade.MENSAL: 1,
    Periodicidade.TRIMESTRAL: 3,
    Periodicidade.SEMESTRAL: 6,
    Periodicidade.ANUAL: 12,
}


class Plano(BaseModel):
    nome = models.CharField('nome', max_length=150)
    descricao = models.TextField('descrição', blank=True, default='')
    valor = models.DecimalField('valor', max_digits=12, decimal_places=2)
    periodicidade = models.CharField(
        'periodicidade', max_length=20, choices=Periodicidade.choices,
    )
    categoria = models.ForeignKey(
        'financeiro.Categoria', verbose_name='categoria',
        on_delete=models.PROTECT, related_name='planos',
        limit_choices_to={'tipo': 'ENTRADA', 'is_active': True},
    )
    # RF-02: campo de negócio distinto de is_active (soft delete, herdado
    # do BaseModel). Um Plano pode continuar is_active=True (não excluído)
    # e ativo=False (descontinuado para NOVAS assinaturas, sem afetar as
    # assinaturas já vinculadas a ele). Mesmo precedente de Categoria.
    ativo = models.BooleanField(
        'disponível para novas assinaturas', default=True,
    )

    class Meta:
        db_table = 'ass_plano'
        ordering = ['nome']
        verbose_name = 'Plano'
        verbose_name_plural = 'Planos'

    def __str__(self):
        return f'{self.nome} — R$ {self.valor} ({self.get_periodicidade_display()})'


class StatusAssinatura(models.TextChoices):
    ATIVA = 'ATIVA', 'Ativa'
    PAUSADA = 'PAUSADA', 'Pausada'
    ENCERRADA = 'ENCERRADA', 'Encerrada'


class Assinatura(BaseModel):
    cliente = models.ForeignKey(
        'clientes.Cliente', verbose_name='cliente',
        on_delete=models.PROTECT, related_name='assinaturas',
    )
    plano = models.ForeignKey(
        Plano, verbose_name='plano',
        on_delete=models.PROTECT, related_name='assinaturas',
    )
    # RF-03: snapshot editável do Plano.valor no momento da criação — não
    # recalcula sozinho se o Plano mudar depois (mesmo padrão de
    # Receita.valor_bruto/Despesa.valor_bruto, que também não seguem
    # nenhuma tabela de preço "ao vivo").
    valor = models.DecimalField('valor', max_digits=12, decimal_places=2)
    dia_vencimento = models.PositiveSmallIntegerField(
        'dia de vencimento',
        validators=[MinValueValidator(1), MaxValueValidator(28)],
        help_text='Limitado a 1-28 (RN-02) — evita vencimento em dia '
                   'inexistente em fevereiro.',
    )
    data_inicio = models.DateField('data de início')
    data_fim = models.DateField(
        'data de fim', null=True, blank=True,
        help_text='Nulo = indeterminado.',
    )
    status = models.CharField(
        'status', max_length=20, choices=StatusAssinatura.choices,
        default=StatusAssinatura.ATIVA,
    )
    conta = models.ForeignKey(
        'financeiro.Conta', verbose_name='conta',
        on_delete=models.PROTECT, related_name='assinaturas',
        help_text='Conta de destino das Receitas geradas pela assinatura.',
    )
    motivo_encerramento = models.TextField('motivo de encerramento', blank=True, default='')
    encerrada_em = models.DateTimeField('encerrada em', null=True, blank=True)

    class Meta:
        db_table = 'ass_assinatura'
        ordering = ['-data_inicio']
        verbose_name = 'Assinatura'
        verbose_name_plural = 'Assinaturas'

    def __str__(self):
        return f'Assinatura #{self.pk} — {self.cliente_id} — {self.plano_id}'
