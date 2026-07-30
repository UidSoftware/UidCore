"""Servico central de conciliacao bancaria.

Reaproveitado tanto pelo management command `conciliar_extrato` quanto pelo
endpoint `ConciliacaoViewSet.upload` (financeiro/views.py) -- fonte unica de
verdade para o matching e para o processamento automatico, evitando a
duplicacao de logica entre CLI e API.

Regra de ouro (RF-D06): ambiguidade NUNCA e decidida automaticamente.
Se mais de um candidato bate os criterios (Passo 1) ou mais de um
PadraoSeguroConciliacao ativo bate a descricao (Passo 2), o item NAO e
assentado/criado -- permanece FALTANDO_SISTEMA aguardando revisao humana.
"""
from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction

from .models import (
    Aporte, Categoria, ConciliacaoExtrato, Despesa,
    ItemConciliacao, LivroCaixa, PadraoSeguroConciliacao, Receita,
)


def _noop(_mensagem):
    return None


def executar_matching(conta, transacoes_banco, periodo):
    """Camada 1: bate LivroCaixa por data (+-1 dia) + valor + tipo.

    Args:
        conta: instancia de Conta.
        transacoes_banco: lista de dicts (data, descricao, valor, tipo) -- saida dos parsers.
        periodo: date do primeiro dia do mes de referencia.

    Returns:
        tuple: (itens: list[dict], lancamentos_sistema: list[LivroCaixa])
        Cada item em `itens` tem as chaves: data_banco, descricao_banco, valor,
        tipo, status (CONCILIADO|FALTANDO_SISTEMA|FALTANDO_BANCO), lancamento_lc.
    """
    primeiro_dia = periodo
    if periodo.month == 12:
        ultimo_dia = date(periodo.year + 1, 1, 1)
    else:
        ultimo_dia = date(periodo.year, periodo.month + 1, 1)

    lancamentos_sistema = list(
        LivroCaixa.objects.filter(
            conta=conta,
            data__gte=primeiro_dia,
            data__lt=ultimo_dia,
            estornado=False,
        ).exclude(
            # RN-D01: um LivroCaixa ja conciliado (CONCILIADO) em uma execucao
            # anterior nunca pode ser vinculado a um novo ItemConciliacao.
            conciliacoes__status='CONCILIADO',
        ).order_by('data', 'criado_em')
    )

    usados_sistema = set()
    itens = []

    for t in transacoes_banco:
        match = None
        for i, lc in enumerate(lancamentos_sistema):
            if i in usados_sistema:
                continue
            diff_dias = abs((lc.data - t['data']).days)
            if diff_dias <= 1 and lc.valor == t['valor'] and lc.tipo == t['tipo']:
                match = lc
                usados_sistema.add(i)
                break

        if match:
            itens.append({
                'data_banco': t['data'],
                'descricao_banco': t['descricao'],
                'valor': t['valor'],
                'tipo': t['tipo'],
                'status': 'CONCILIADO',
                'lancamento_lc': match,
            })
        else:
            itens.append({
                'data_banco': t['data'],
                'descricao_banco': t['descricao'],
                'valor': t['valor'],
                'tipo': t['tipo'],
                'status': 'FALTANDO_SISTEMA',
                'lancamento_lc': None,
            })

    for i, lc in enumerate(lancamentos_sistema):
        if i not in usados_sistema:
            itens.append({
                'data_banco': lc.data,
                'descricao_banco': lc.descricao,
                'valor': lc.valor,
                'tipo': lc.tipo,
                'status': 'FALTANDO_BANCO',
                'lancamento_lc': lc,
            })

    return itens, lancamentos_sistema


def calcular_totais(transacoes_banco, lancamentos_sistema):
    """Calcula total_banco e total_sistema (entradas - saidas)."""
    total_banco = (
        sum((t['valor'] for t in transacoes_banco if t['tipo'] == 'ENTRADA'), Decimal('0'))
        - sum((t['valor'] for t in transacoes_banco if t['tipo'] == 'SAIDA'), Decimal('0'))
    )
    total_sistema = (
        sum((lc.valor for lc in lancamentos_sistema if lc.tipo == 'ENTRADA'), Decimal('0'))
        - sum((lc.valor for lc in lancamentos_sistema if lc.tipo == 'SAIDA'), Decimal('0'))
    )
    return total_banco, total_sistema


def criar_conciliacao(conta, transacoes_banco, periodo, arquivo_nome, criado_por=None, auto=False, log=None):
    """Fluxo completo: matching (Camada 1) + persistencia + auto-processamento (Camadas 2/3).

    Usado pelo endpoint ConciliacaoViewSet.upload (financeiro/views.py) e pelo
    management command conciliar_extrato.

    Args:
        conta: instancia de Conta.
        transacoes_banco: lista de dicts vinda de um parser (financeiro/parsers.py).
        periodo: date do primeiro dia do mes de referencia.
        arquivo_nome: nome do arquivo (sem path completo -- RN-D03).
        criado_por: usuario que disparou a conciliacao (opcional).
        auto: se True, executa auto_processar (Camadas 2 e 3) apos persistir.
        log: callable(str) para relatorio (ex: self.stdout.write); default no-op.

    Returns:
        ConciliacaoExtrato criada (ja refletindo o resultado do auto-processamento,
        se auto=True).
    """
    log = log or _noop

    itens, lancamentos_sistema = executar_matching(conta, transacoes_banco, periodo)
    total_banco, total_sistema = calcular_totais(transacoes_banco, lancamentos_sistema)

    with transaction.atomic():
        faltando_sistema = [x for x in itens if x['status'] == 'FALTANDO_SISTEMA']
        faltando_banco = [x for x in itens if x['status'] == 'FALTANDO_BANCO']

        status_inicial = (
            'COM_DIVERGENCIAS' if (faltando_sistema or faltando_banco) else 'PROCESSADO'
        )
        conc = ConciliacaoExtrato.objects.create(
            conta=conta,
            arquivo_nome=arquivo_nome,
            periodo=periodo,
            status=status_inicial,
            total_banco=total_banco,
            total_sistema=total_sistema,
            divergencias=len(faltando_sistema) + len(faltando_banco),
            criado_por=criado_por,
        )

        for item in itens:
            ItemConciliacao.objects.create(
                conciliacao=conc,
                data_banco=item['data_banco'],
                descricao_banco=item['descricao_banco'],
                valor=item['valor'],
                tipo=item['tipo'],
                status=item['status'],
                lancamento_lc=item['lancamento_lc'],
            )

        if auto:
            auto_processar(faltando_sistema, conta, conc, log=log)

    conciliados = [x for x in itens if x['status'] == 'CONCILIADO']
    log(f'Conciliados      : {len(conciliados)}')
    log(f'Faltando sistema : {len(faltando_sistema)}')
    log(f'Faltando banco   : {len(faltando_banco)}')
    log(f'Total banco    : R$ {total_banco:,.2f}')
    log(f'Total sistema  : R$ {total_sistema:,.2f}')
    log(f'Diferenca      : R$ {(total_banco - total_sistema):,.2f}')

    return conc


def auto_processar(faltando, conta, conc, log=None):
    """Processamento automatico seguro em dois passos (Camadas 2 e 3).

    Passo 1 - Assentar pendentes existentes por valor + vencimento +-3 dias.
        RF-D06 / ambiguidade: se MAIS DE UM candidato (Receita ou Despesa) bate
        os criterios, NADA e assentado -- o item permanece FALTANDO_SISTEMA
        aguardando revisao humana. Decisao automatica so ocorre quando ha
        exatamente 1 candidato.

    Passo 2 - Criar por PadraoSeguroConciliacao aprovado.
        RF-D06 / ambiguidade: se MAIS DE UM padrao ativo bate a descricao,
        NADA e criado -- o item permanece FALTANDO_SISTEMA aguardando revisao
        humana. Decisao automatica so ocorre quando ha exatamente 1 padrao.

    Args:
        faltando: lista de itens (dict) com status FALTANDO_SISTEMA vindos do matching.
        conta: instancia de Conta.
        conc: instancia de ConciliacaoExtrato ja persistida (com ItemConciliacao criados).
        log: callable(str) para relatorio; default no-op.

    Returns:
        dict com contadores: assentados, criados_padrao, aguardando_revisao.
    """
    log = log or _noop

    pendentes_restantes = list(faltando)
    assentados = 0
    criados_padrao = 0
    aguardando_revisao = 0

    # Passo 1: Assentar pendentes existentes
    for item in list(pendentes_restantes):
        data_banco = item['data_banco']
        valor = item['valor']
        tipo = item['tipo']

        data_min = data_banco - timedelta(days=3)
        data_max = data_banco + timedelta(days=3)

        if tipo == 'ENTRADA':
            candidatos = list(Receita.objects.filter(
                conta=conta,
                status__in=['PENDENTE', 'ATRASADO'],
                valor_liquido=valor,
                vencimento__range=(data_min, data_max),
                is_active=True,
            ).order_by('vencimento'))

            if len(candidatos) == 1:
                receita = candidatos[0]
                receita.status = 'RECEBIDO'
                receita.recebimento = data_banco
                receita.save()  # signal cria LivroCaixa

                lc = LivroCaixa.objects.filter(
                    conta=conta, origem='RECEITA', origem_id=receita.id,
                ).order_by('-criado_em').first()

                ItemConciliacao.objects.filter(
                    conciliacao=conc, data_banco=data_banco, valor=valor,
                    tipo=tipo, confirmado=False,
                ).update(confirmado=True, status='CONCILIADO', lancamento_lc=lc)

                log(
                    f'  [AUTO-P1] Receita assentada: {receita.descricao[:50]} '
                    f'(R${valor:,.2f} em {data_banco})'
                )
                pendentes_restantes.remove(item)
                assentados += 1
            elif len(candidatos) > 1:
                log(
                    f'  [AUTO-P1] AMBIGUO -- {len(candidatos)} receitas candidatas para '
                    f'R${valor:,.2f} em {data_banco}: aguarda revisao humana'
                )
                pendentes_restantes.remove(item)
                aguardando_revisao += 1
            # 0 candidatos: mantem em pendentes_restantes para tentar Passo 2

        elif tipo == 'SAIDA':
            candidatos = list(Despesa.objects.filter(
                conta=conta,
                status__in=['PENDENTE', 'ATRASADO'],
                valor_liquido=valor,
                vencimento__range=(data_min, data_max),
                is_active=True,
                estornado=False,
            ).order_by('vencimento'))

            if len(candidatos) == 1:
                despesa = candidatos[0]
                despesa.status = 'PAGO'
                despesa.pagamento = data_banco
                despesa.save()  # signal cria LivroCaixa

                lc = LivroCaixa.objects.filter(
                    conta=conta, origem='DESPESA', origem_id=despesa.id,
                ).order_by('-criado_em').first()

                ItemConciliacao.objects.filter(
                    conciliacao=conc, data_banco=data_banco, valor=valor,
                    tipo=tipo, confirmado=False,
                ).update(confirmado=True, status='CONCILIADO', lancamento_lc=lc)

                log(
                    f'  [AUTO-P1] Despesa assentada: {despesa.descricao[:50]} '
                    f'(R${valor:,.2f} em {data_banco})'
                )
                pendentes_restantes.remove(item)
                assentados += 1
            elif len(candidatos) > 1:
                log(
                    f'  [AUTO-P1] AMBIGUO -- {len(candidatos)} despesas candidatas para '
                    f'R${valor:,.2f} em {data_banco}: aguarda revisao humana'
                )
                pendentes_restantes.remove(item)
                aguardando_revisao += 1
            # 0 candidatos: mantem em pendentes_restantes para tentar Passo 2

    # Passo 2: Criar por padrao seguro
    padroes_entrada = list(
        PadraoSeguroConciliacao.objects.filter(tipo='ENTRADA', is_active=True)
        .values_list('descricao_padrao', 'natureza')
    )
    padroes_saida = list(
        PadraoSeguroConciliacao.objects.filter(tipo='SAIDA', is_active=True)
        .values_list('descricao_padrao', flat=True)
    )
    categoria_investimento = Categoria.objects.filter(
        nome__iexact='Investimento', tipo='ENTRADA'
    ).first()

    for item in pendentes_restantes:
        descricao_lower = item['descricao_banco'].lower()
        tipo = item['tipo']

        if tipo == 'ENTRADA':
            matches = [
                (desc, nat) for desc, nat in padroes_entrada
                if desc.lower() in descricao_lower
            ]
        else:
            matches = [
                (desc, None) for desc in padroes_saida
                if desc.lower() in descricao_lower
            ]

        if len(matches) > 1:
            log(
                f"  [AUTO-P2] AMBIGUO -- {len(matches)} padroes batem para "
                f"'{item['descricao_banco'][:50]}': aguarda revisao humana"
            )
            aguardando_revisao += 1
            continue

        if not matches:
            log(
                f"  [AUTO-P2] Sem padrao -- aguarda revisao humana: "
                f"{item['descricao_banco'][:50]} (R${item['valor']:,.2f})"
            )
            aguardando_revisao += 1
            continue

        padrao_match, natureza_match = matches[0]

        try:
            if tipo == 'ENTRADA' and natureza_match == 'RECEITA_FINANCEIRA':
                Receita.objects.create(
                    conta=conta,
                    descricao=item['descricao_banco'][:255],
                    tipo='RECEITA_FINANCEIRA',
                    categoria=categoria_investimento,
                    valor_bruto=item['valor'],
                    vencimento=item['data_banco'],
                    recebimento=item['data_banco'],
                    status='RECEBIDO',
                )
            elif tipo == 'ENTRADA':
                Aporte.objects.create(
                    conta=conta,
                    descricao=item['descricao_banco'][:255],
                    valor=item['valor'],
                    data=item['data_banco'],
                    tipo='CAPITAL_SOCIAL',
                    responsavel='Conciliacao automatica',
                )
            else:
                Despesa.objects.create(
                    conta=conta,
                    descricao=item['descricao_banco'][:255],
                    valor_bruto=item['valor'],
                    vencimento=item['data_banco'],
                    pagamento=item['data_banco'],
                    status='PAGO',
                    tipo='VARIAVEL',
                    forma_pagamento='PIX',
                )

            ItemConciliacao.objects.filter(
                conciliacao=conc, data_banco=item['data_banco'], valor=item['valor'],
                tipo=tipo, confirmado=False,
            ).update(confirmado=True)

            log(
                f"  [AUTO-P2] Criado por padrao '{padrao_match[:30]}': "
                f"{item['descricao_banco'][:40]} (R${item['valor']:,.2f})"
            )
            criados_padrao += 1

        except Exception as e:
            log(f"  [AUTO-P2] Erro ao criar {item['descricao_banco'][:40]}: {e}")
            aguardando_revisao += 1

    # Atualiza status e divergencias da conciliacao
    restantes = conc.itens.filter(status='FALTANDO_SISTEMA', confirmado=False).count()
    faltando_banco_count = conc.itens.filter(status='FALTANDO_BANCO').count()

    conc.status = 'PROCESSADO' if (restantes == 0 and faltando_banco_count == 0) else 'COM_DIVERGENCIAS'
    conc.divergencias = restantes + faltando_banco_count
    conc.save(update_fields=['status', 'divergencias'])

    log('--- Resultado --auto ---')
    log(f'  Pendentes assentados : {assentados}')
    log(f'  Criados por padrao   : {criados_padrao}')
    log(f'  Aguardando revisao   : {aguardando_revisao}')

    return {
        'assentados': assentados,
        'criados_padrao': criados_padrao,
        'aguardando_revisao': aguardando_revisao,
    }
