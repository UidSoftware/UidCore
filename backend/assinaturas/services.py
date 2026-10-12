"""
assinaturas/services.py — Manutencao #64 [NUCLEO 3/5].

Geração de cobrança mensal (financeiro.Receita PENDENTE) a partir de
Assinatura ativa. Idempotente via get_or_create (lookup por
assinatura+referencia_mes) + UniqueConstraint em financeiro.Receita como
segunda camada de defesa contra race condition
(financeiro/migrations — uniq_assinatura_referencia_mes).

RN-03/RN-04 (lição real do NosFluir/Studio Fluir): a elegibilidade de
status e data_fim é parte da QUERY base (queryset), não um filtro
aplicado depois de já ter decidido gerar — evita exatamente o bug que lá
gerou cobrança indevida 2 meses depois do contrato encerrado.

RN-09: nunca escreve LivroCaixa diretamente — cria Receita PENDENTE; o
signal já existente (financeiro/signals.py::receita_para_livro_caixa) só
dispara quando a Receita for de fato marcada RECEBIDO, exatamente como
qualquer outra Receita manual.
"""
import calendar

from django.db import transaction
from django.db.models import Q

from financeiro.models import Receita, StatusReceita, TipoReceita

from .models import Assinatura, INTERVALO_MESES_POR_PERIODICIDADE, StatusAssinatura


def _elegivel_por_periodicidade(assinatura, mes):
    """RN-05 — periodicidade não-mensal só gera no mês de competência exato."""
    diferenca_meses = (
        (mes.year - assinatura.data_inicio.year) * 12
        + (mes.month - assinatura.data_inicio.month)
    )
    intervalo = INTERVALO_MESES_POR_PERIODICIDADE[assinatura.plano.periodicidade]
    return diferenca_meses >= 0 and diferenca_meses % intervalo == 0


def _vencimento_do_mes(mes, dia_vencimento):
    # dia_vencimento já é limitado a 1-28 no model (RN-02 do RF-03),
    # então sempre existe em qualquer mês — min() aqui é defesa extra.
    ultimo_dia = calendar.monthrange(mes.year, mes.month)[1]
    return mes.replace(day=min(dia_vencimento, ultimo_dia))


def _primeiro_dia_mes_seguinte(mes):
    if mes.month == 12:
        return mes.replace(year=mes.year + 1, month=1)
    return mes.replace(month=mes.month + 1)


def gerar_cobrancas_mes(mes, dry_run=False):
    """
    mes: date representando o 1º dia do mês de competência.
    Retorna resumo: {criadas, puladas_idempotencia, puladas_elegibilidade, erros: [...]}.
    """
    resumo = {
        'criadas': 0,
        'puladas_idempotencia': 0,
        'puladas_elegibilidade': 0,
        'erros': [],
    }

    # RN-01 + RN-02 + RN-03: status=ATIVA, data_inicio dentro do mês de
    # competência (ou antes) e (data_fim nula OU >= mes) fazem parte da
    # query base — uma Assinatura ENCERRADA com data_fim no passado
    # simplesmente não entra neste queryset, nunca é avaliada como "seria
    # elegível se não fosse o status". A comparação de data_inicio usa o
    # 1º dia do mês SEGUINTE (não `mes` direto) porque `data_inicio` pode
    # cair em qualquer dia dentro do próprio mês de competência (ex:
    # data_inicio=2026-01-15 ainda é elegível no mês 2026-01 — ver seção
    # 5 "Fora de Escopo" da Especificacao_Hotfix.md) — um `data_inicio__lte=mes`
    # literal excluiria incorretamente qualquer início depois do dia 1.
    assinaturas = (
        Assinatura.objects.filter(is_active=True, status=StatusAssinatura.ATIVA)
        .filter(data_inicio__lt=_primeiro_dia_mes_seguinte(mes))
        .filter(Q(data_fim__isnull=True) | Q(data_fim__gte=mes))
        .select_related('plano', 'plano__categoria', 'cliente', 'conta')
    )

    for assinatura in assinaturas:
        if not _elegivel_por_periodicidade(assinatura, mes):
            resumo['puladas_elegibilidade'] += 1
            continue

        try:
            # RN-06: transaction.atomic() própria por assinatura — erro em
            # uma não impede o processamento das demais no mesmo lote.
            with transaction.atomic():
                receita, criada = Receita.objects.get_or_create(
                    assinatura=assinatura,
                    referencia_mes=mes,
                    defaults={
                        'tipo': TipoReceita.MENSALIDADE,
                        'descricao': (
                            f'Assinatura #{assinatura.pk} — {assinatura.plano.nome} '
                            f'({mes.strftime("%m/%Y")})'
                        ),
                        'cliente': assinatura.cliente,
                        'categoria': assinatura.plano.categoria,
                        'valor_bruto': assinatura.valor,
                        'conta': assinatura.conta,
                        'vencimento': _vencimento_do_mes(mes, assinatura.dia_vencimento),
                        'status': StatusReceita.PENDENTE,
                    },
                )

                if criada:
                    resumo['criadas'] += 1
                else:
                    resumo['puladas_idempotencia'] += 1

                if dry_run:
                    # RN-08: dry-run nunca grava nada no banco — desfaz a
                    # transação (savepoint) depois de calcular o que seria
                    # criado/pulado, sem precisar duplicar a lógica acima.
                    transaction.set_rollback(True)
        except Exception as exc:  # noqa: BLE001 — erro de 1 assinatura não derruba o lote (RN-06)
            resumo['erros'].append({'assinatura_id': assinatura.pk, 'erro': str(exc)})

    return resumo
