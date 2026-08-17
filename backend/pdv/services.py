"""
pdv/services.py — orquestração de operações do PDV.

Todas as operações com efeito financeiro rodam em transaction.atomic() +
pg_advisory_xact_lock (ADR-020 + ADR-021):

  - abrir_sessao    : lock por conta (RN-01 — evita race condition)
  - fechar_sessao   : sem lock extra (apenas leitura + update na sessão)
  - finalizar_venda : lock por conta da sessão + lock por produto (ordem crescente)
  - cancelar_venda  : mesmos locks de finalizar (estoque volta + receitas estornadas)
  - devolver_item   : lock por conta do pagamento (estoque parcial volta + estorno receita)

Baixa/reversão de estoque é a operação INVERSA exata de EntradaEstoque.save()
(achado A7 do Analista): mesma resolução de ConversaoUnidade, F() atômico.
"""
from datetime import date, timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import connection, transaction
from django.db.models import F
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from financeiro.models import Conta, Receita, TipoConta
from financeiro.services import estornar_receita
from pagamentos.models import MetodoPagamento, NomeMetodoPagamento
from produtos.models import Produto
from produtos.services import fator_para_base

from .models import (
    MovimentoCaixa,
    PagamentoVenda,
    RecebivelCartao,
    SessaoCaixa,
    StatusSessaoCaixa,
    Venda,
)


# ---------------------------------------------------------------------------
# Conversão de unidade (espelho de EntradaEstoque.save())
# ---------------------------------------------------------------------------

def _fator_conversao(item):
    """
    Fator de conversão de item.unidade para a unidade_base do produto,
    delegando para produtos.services.fator_para_base (Manutenção #37) —
    resolve cadeia (RN-01) e NUNCA cai em fallback 1:1 silencioso: unidade
    sem conversão cadastrada levanta rest_framework.exceptions.ValidationError
    (RN-05), convertida aqui a partir do django.core.exceptions.ValidationError
    levantado pela função compartilhada.
    """
    if item.unidade == item.produto.unidade_base:
        return Decimal('1')
    try:
        return fator_para_base(item.produto, item.unidade)
    except DjangoValidationError as exc:
        raise ValidationError({
            'unidade': exc.messages if hasattr(exc, 'messages') else [str(exc)],
        })


def _quantidade_base(item):
    """Converte item.quantidade para unidade base do produto (RN-05)."""
    return item.quantidade * _fator_conversao(item)


def _debitar_estoque(item):
    """Debita estoque do produto (operação inversa de EntradaEstoque)."""
    qtd_base = _quantidade_base(item)
    Produto.objects.filter(pk=item.produto_id).update(
        quantidade_estoque=F('quantidade_estoque') - qtd_base,
    )


def _reverter_estoque(item, quantidade_devolvida):
    """Reverte estoque para devolução parcial (RF-13)."""
    qtd_base = quantidade_devolvida * _fator_conversao(item)
    Produto.objects.filter(pk=item.produto_id).update(
        quantidade_estoque=F('quantidade_estoque') + qtd_base,
    )


# ---------------------------------------------------------------------------
# Resolução de conta por forma de pagamento (RF-14 / ADR-018)
# ---------------------------------------------------------------------------

def _resolver_conta(dados_pagamento, metodo):
    """
    Resolve a Conta de destino do pagamento:
    1. payload['conta'] se presente
    2. metodo.conta_padrao se configurado (ADR-018)
    3. erro 400 legível
    """
    conta_id = dados_pagamento.get('conta')
    if conta_id:
        try:
            return Conta.objects.get(pk=conta_id, is_active=True)
        except Conta.DoesNotExist:
            raise ValidationError({'conta': f'Conta {conta_id} nao encontrada ou inativa.'})
    if metodo.conta_padrao_id:
        return metodo.conta_padrao
    raise ValidationError({
        'conta': (
            f'Nenhuma conta informada e {metodo.get_nome_display()} '
            f'nao tem conta_padrao configurada.'
        ),
    })


# ---------------------------------------------------------------------------
# Geração de Receita por PagamentoVenda (RF-08)
# ---------------------------------------------------------------------------

def _criar_receita_a_vista(venda, pagamento, usuario):
    """
    Receita status=RECEBIDO para pagamento à vista (dinheiro, pix, débito).
    O signal receita_para_livro_caixa (financeiro/signals.py) dispara
    automaticamente no save() e cria o LivroCaixa ENTRADA — zero código novo.
    """
    return Receita.objects.create(
        tipo='PRODUTO',
        descricao=f'Venda {venda.numero} — {pagamento.metodo.get_nome_display()}',
        cliente=venda.cliente,
        valor_bruto=pagamento.valor,
        conta=pagamento.conta,
        status='RECEBIDO',
        recebimento=date.today(),
        criado_por=usuario,
    )


def _criar_receita_cartao(venda, pagamento, dados, usuario):
    """
    Receita status=PENDENTE + RecebivelCartao para pagamento em cartão de
    crédito (Ponto 3 / ADR-019).

    Nenhum LivroCaixa nasce aqui — o signal só dispara com status=RECEBIDO,
    que só acontece na liquidação via ConciliacaoViewSet.confirmar_item.
    Reutiliza Receita.desconto para a taxa da maquininha (ADR-019 + Seção 6.1).
    """
    taxa = Decimal(str(dados['taxa_percentual']))
    prazo_dias = int(dados.get('prazo_dias', 0))
    valor_bruto = pagamento.valor
    desconto = (valor_bruto * taxa / Decimal('100')).quantize(Decimal('0.01'))
    data_prevista = date.today() + timedelta(days=prazo_dias)

    receita = Receita.objects.create(
        tipo='PRODUTO',
        descricao=f'Venda {venda.numero} — Cartao de Credito',
        cliente=venda.cliente,
        valor_bruto=valor_bruto,
        desconto=desconto,
        conta=pagamento.conta,
        status='PENDENTE',
        vencimento=data_prevista,
        criado_por=usuario,
    )
    RecebivelCartao.objects.create(
        pagamento=pagamento,
        receita=receita,
        taxa_percentual=taxa,
        valor_bruto=valor_bruto,
        valor_liquido_previsto=receita.valor_liquido,
        data_prevista_liquidacao=data_prevista,
        criado_por=usuario,
    )
    return receita


# ---------------------------------------------------------------------------
# abrir_sessao (RF-01 / RF-02)
# ---------------------------------------------------------------------------

def abrir_sessao(conta_id, valor_abertura, usuario):
    """
    Abre uma SessaoCaixa.

    RN-01: select_for_update() + lock por conta para retornar 400 legível em
    vez de IntegrityError 500 na UniqueConstraint condicional.
    RN-02 (Manutenção #36): mesma proteção, agora também por operador — um
    operador não pode ter mais de uma sessão ABERTA simultânea, mesmo em
    contas diferentes. Lock advisory dedicado com namespace de 2 argumentos
    (classid=2, objid=operador.id) para não colidir com o lock de 1
    argumento já usado para conta.id.
    """
    try:
        conta = Conta.objects.get(pk=conta_id, is_active=True)
    except Conta.DoesNotExist:
        raise ValidationError({'conta': 'Conta nao encontrada ou inativa.'})

    if conta.tipo != TipoConta.CAIXA:
        # RF-01/RN-01 (Manutenção #36): o dropdown do frontend ja filtra por
        # tipo=CAIXA, mas isso e so UI — a garantia real tem que estar aqui.
        raise ValidationError({'conta': 'Conta informada nao e do tipo CAIXA.'})

    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute('SELECT pg_advisory_xact_lock(%s)', [conta.id])
            cursor.execute('SELECT pg_advisory_xact_lock(2, %s)', [usuario.id])

        if SessaoCaixa.objects.filter(conta=conta, status='ABERTA').select_for_update().exists():
            raise ValidationError({'conta': 'Ja existe sessao aberta nesta conta.'})

        if SessaoCaixa.objects.filter(
            operador=usuario, status='ABERTA',
        ).select_for_update().exists():
            raise ValidationError({
                'operador': 'Voce ja tem uma sessao de caixa aberta em outra conta.',
            })

        sessao = SessaoCaixa.objects.create(
            conta=conta,
            operador=usuario,
            valor_abertura=valor_abertura or Decimal('0'),
            status=StatusSessaoCaixa.ABERTA,
        )

    return sessao


# ---------------------------------------------------------------------------
# calcular_resumo_sessao (RF-03) — extraída de fechar_sessao() para ser
# reutilizada ao vivo (sessão ABERTA, sem persistir nada) e no fechamento
# (sessão FECHADA), sem duplicar a fórmula.
# ---------------------------------------------------------------------------

def calcular_resumo_sessao(sessao):
    """
    Resumo ao vivo (não persistido) de uma SessaoCaixa: vendas por forma de
    pagamento, sangrias, suprimentos e o valor calculado de caixa físico.

    Usado por:
      - SessaoCaixaSerializer.resumo (RF-03) — sessão ABERTA ou FECHADA.
      - fechar_sessao() — mesma fórmula, agora extraída daqui (RN-07).

    valor_calculado_dinheiro = valor_abertura
                               + vendas finalizadas à vista (dinheiro/pix/débito)
                               + suprimentos
                               - sangrias
    (Apenas métodos à vista entram no cálculo físico do caixa — cartão de
    crédito não entra na gaveta física, mas continua listado em por_metodo
    para a conferência de "vendas por forma de pagamento".)
    """
    from django.db.models import Sum

    pagamentos_qs = PagamentoVenda.objects.filter(
        venda__sessao_caixa=sessao,
        venda__status='FINALIZADA',
    ).select_related('metodo')

    labels = dict(NomeMetodoPagamento.choices)
    por_metodo = [
        {
            'metodo_nome': labels.get(row['metodo__nome'], row['metodo__nome']),
            'total': row['total'] or Decimal('0'),
        }
        for row in (
            pagamentos_qs.values('metodo__nome')
            .annotate(total=Sum('valor'))
            .order_by('metodo__nome')
        )
    ]

    vendas_dinheiro = pagamentos_qs.filter(
        metodo__nome__in=[
            NomeMetodoPagamento.DINHEIRO,
            NomeMetodoPagamento.PIX,
            NomeMetodoPagamento.CARTAO_DEBITO,
        ],
    ).aggregate(v=Sum('valor'))['v'] or Decimal('0')

    suprimentos = sessao.movimentos.filter(
        tipo='SUPRIMENTO', is_active=True,
    ).aggregate(v=Sum('valor'))['v'] or Decimal('0')

    sangrias = sessao.movimentos.filter(
        tipo='SANGRIA', is_active=True,
    ).aggregate(v=Sum('valor'))['v'] or Decimal('0')

    valor_calculado_dinheiro = sessao.valor_abertura + vendas_dinheiro + suprimentos - sangrias

    return {
        'por_metodo': por_metodo,
        'vendas_dinheiro': vendas_dinheiro,
        'sangrias': sangrias,
        'suprimentos': suprimentos,
        'valor_calculado_dinheiro': valor_calculado_dinheiro,
    }


# ---------------------------------------------------------------------------
# fechar_sessao (RF-11 / RN-07)
# ---------------------------------------------------------------------------

def fechar_sessao(sessao, valor_fechamento_informado, observacoes=''):
    """
    Fecha uma SessaoCaixa.

    RN-07: nunca bloqueia por diferença — registra e segue.
    Reaproveita calcular_resumo_sessao() para o valor calculado — mesma
    fórmula usada ao vivo antes do fechamento (RF-03), sem duplicação.
    """
    if sessao.status != 'ABERTA':
        raise ValidationError({'status': 'Sessao ja esta fechada.'})

    resumo = calcular_resumo_sessao(sessao)
    calculado = resumo['valor_calculado_dinheiro']
    informado = Decimal(str(valor_fechamento_informado))

    sessao.valor_fechamento_calculado = calculado
    sessao.valor_fechamento_informado = informado
    sessao.diferenca = calculado - informado
    sessao.status = StatusSessaoCaixa.FECHADA
    sessao.data_fechamento = timezone.now()
    sessao.observacoes = observacoes or ''
    sessao.save(update_fields=[
        'valor_fechamento_calculado', 'valor_fechamento_informado',
        'diferenca', 'status', 'data_fechamento', 'observacoes',
    ])

    return sessao


# ---------------------------------------------------------------------------
# finalizar_venda (RF-06 / RF-07 / RF-08 / RF-09 / ADR-020 / ADR-021)
# ---------------------------------------------------------------------------

def finalizar_venda(venda, pagamentos_payload, usuario):
    """
    Finaliza uma Venda:
    1. Valida status e sessão aberta.
    2. Valida soma dos pagamentos == valor_total.
    3. Adquire locks: conta da sessão + produto (ordem crescente id, ADR-020).
    4. Valida estoque de TODOS os itens (RF-07) — aborta antes de debitar qualquer um.
    5. Debita estoque de cada item.
    6. Para cada pagamento: cria PagamentoVenda + Receita (à vista ou cartão).
    7. Marca Venda como FINALIZADA.
    """
    if venda.status != 'ABERTA':
        raise ValidationError({'status': 'Venda nao esta aberta.'})
    if venda.sessao_caixa.status != 'ABERTA':
        raise ValidationError({'sessao_caixa': 'Sessao de caixa nao esta aberta.'})

    itens = list(venda.itens.filter(is_active=True).select_related('produto'))
    if not itens:
        raise ValidationError({'itens': 'Venda sem itens.'})

    soma_pagamentos = sum(Decimal(str(p['valor'])) for p in pagamentos_payload)
    if soma_pagamentos != venda.valor_total:
        raise ValidationError({
            'pagamentos': (
                f'Soma dos pagamentos (R$ {soma_pagamentos}) difere '
                f'do total da venda (R$ {venda.valor_total}).'
            ),
        })

    with transaction.atomic():
        # ADR-020: lock conta + produtos em ordem crescente de id
        produto_ids = sorted({item.produto_id for item in itens})
        with connection.cursor() as cursor:
            cursor.execute(
                'SELECT pg_advisory_xact_lock(%s)', [venda.sessao_caixa.conta_id],
            )
            for pid in produto_ids:
                cursor.execute('SELECT pg_advisory_xact_lock(%s)', [pid])

        # RF-07: valida estoque de TODOS antes de debitar qualquer um
        itens_sem_estoque = []
        for item in itens:
            produto = Produto.objects.select_for_update().get(pk=item.produto_id)
            qtd_base = _quantidade_base(item)
            if produto.quantidade_estoque < qtd_base:
                itens_sem_estoque.append({
                    'item_id': item.id,
                    'produto': produto.nome,
                    'disponivel': str(produto.quantidade_estoque),
                    'solicitado': str(qtd_base),
                })
        if itens_sem_estoque:
            raise ValidationError({'itens_sem_estoque': itens_sem_estoque})

        # Debitar estoque de todos os itens
        for item in itens:
            _debitar_estoque(item)

        # Criar PagamentoVenda + Receita para cada parcela do split
        for dados in pagamentos_payload:
            metodo = MetodoPagamento.objects.get(pk=dados['metodo'])
            conta = _resolver_conta(dados, metodo)

            pagamento = PagamentoVenda.objects.create(
                venda=venda,
                metodo=metodo,
                valor=Decimal(str(dados['valor'])),
                conta=conta,
            )

            if metodo.nome == NomeMetodoPagamento.CARTAO_CREDITO:
                receita = _criar_receita_cartao(venda, pagamento, dados, usuario)
            else:
                receita = _criar_receita_a_vista(venda, pagamento, usuario)

            pagamento.receita = receita
            pagamento.save(update_fields=['receita'])

        venda.status = 'FINALIZADA'
        venda.save(update_fields=['status'])

    return venda


# ---------------------------------------------------------------------------
# cancelar_venda (RF-12 / RN-08)
# ---------------------------------------------------------------------------

def cancelar_venda(venda, motivo, usuario):
    """
    Cancela uma Venda inteira.

    RN-08: reverte 100% do estoque (items não estornados) e estorna 100%
    das Receitas associadas (não as deleta). Devolução parcial é RF-13.
    """
    if venda.status == 'CANCELADA':
        raise ValidationError({'status': 'Venda ja foi cancelada.'})
    if venda.status not in ('ABERTA', 'FINALIZADA'):
        raise ValidationError({'status': 'Status invalido para cancelamento.'})

    with transaction.atomic():
        itens = list(venda.itens.filter(is_active=True).select_related('produto'))
        produto_ids = sorted({i.produto_id for i in itens})

        with connection.cursor() as cursor:
            cursor.execute(
                'SELECT pg_advisory_xact_lock(%s)', [venda.sessao_caixa.conta_id],
            )
            for pid in produto_ids:
                cursor.execute('SELECT pg_advisory_xact_lock(%s)', [pid])

        # Reverter estoque somente dos itens não totalmente estornados
        if venda.status == 'FINALIZADA':
            for item in itens:
                restante = item.quantidade - item.quantidade_estornada
                if restante > Decimal('0'):
                    _reverter_estoque(item, restante)

        # Estornar todas as Receitas com saldo disponível > 0
        for pagamento in venda.pagamentos.filter(is_active=True).select_related('receita', 'receita__conta'):
            if not pagamento.receita_id:
                continue
            receita = pagamento.receita
            if receita.status != 'RECEBIDO':
                continue
            saldo = receita.saldo_disponivel
            if saldo > Decimal('0'):
                estornar_receita(
                    receita=receita,
                    valor=saldo,
                    motivo=f'Cancelamento venda {venda.numero}: {motivo}',
                    usuario=usuario,
                )

        venda.status = 'CANCELADA'
        venda.cancelada_em = timezone.now()
        venda.motivo_cancelamento = motivo
        venda.save(update_fields=['status', 'cancelada_em', 'motivo_cancelamento'])

    return venda


# ---------------------------------------------------------------------------
# devolver_item (RF-13 / Ponto 2)
# ---------------------------------------------------------------------------

def devolver_item(item, quantidade, motivo, pagamento_id, usuario):
    """
    Devolução parcial de item de uma Venda finalizada.

    - Reverte o estoque da quantidade devolvida.
    - Cria EstornoReceita pelo valor proporcional na Receita do pagamento
      indicado por pagamento_id.
    - Incrementa item.quantidade_estornada.
    - Recalcula Venda.valor_total.
    """
    quantidade = Decimal(str(quantidade))

    if quantidade <= Decimal('0'):
        raise ValidationError({'quantidade': 'Quantidade deve ser maior que zero.'})

    restante = item.quantidade - item.quantidade_estornada
    if quantidade > restante:
        raise ValidationError({
            'quantidade': (
                f'Quantidade invalida. Disponivel para devolucao: {restante}.'
            ),
        })

    pagamento = get_object_or_404(
        PagamentoVenda, pk=pagamento_id, venda=item.venda, is_active=True,
    )
    if not pagamento.receita_id:
        raise ValidationError({'pagamento_id': 'Pagamento sem receita associada.'})

    valor_proporcional = (
        (quantidade / item.quantidade) * item.valor_total
    ).quantize(Decimal('0.01'))

    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute(
                'SELECT pg_advisory_xact_lock(%s)', [pagamento.conta_id],
            )

        _reverter_estoque(item, quantidade)

        estornar_receita(
            receita=pagamento.receita,
            valor=valor_proporcional,
            motivo=motivo,
            item_venda=item,
            usuario=usuario,
        )

        item.quantidade_estornada += quantidade
        item.save(update_fields=['quantidade_estornada'])

        # Recalcular valor_total da venda
        item.venda.recalcular_total()

    return item
