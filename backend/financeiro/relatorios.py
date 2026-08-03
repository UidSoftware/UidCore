from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Sum, Q, Count

from .models import Aporte, Categoria, Conta, Despesa, LivroCaixa, Receita


def _saldo_total_contas():
    saldo_inicial = Conta.objects.filter(
        is_active=True,
    ).exclude(tipo='CARTEIRA').aggregate(
        v=Sum('saldo_inicial')
    )['v'] or Decimal('0')
    agg = LivroCaixa.objects.filter(
        conta__is_active=True, estornado=False,
    ).exclude(conta__tipo='CARTEIRA').aggregate(
        e=Sum('valor', filter=Q(tipo='ENTRADA')),
        s=Sum('valor', filter=Q(tipo='SAIDA')),
    )
    return saldo_inicial + (agg['e'] or Decimal('0')) - (agg['s'] or Decimal('0'))


def _divida_cartao_credito():
    """
    Soma o saldo liquido de todas as contas CARTEIRA ativas.
    Se o saldo for negativo (fatura em aberto), retorna o valor
    absoluto como positivo (= valor da divida, Passivo Circulante).
    Retorna Decimal('0') se nao ha cartao ativo ou o saldo e >= 0.
    """
    saldo_inicial = Conta.objects.filter(
        is_active=True, tipo='CARTEIRA',
    ).aggregate(v=Sum('saldo_inicial'))['v'] or Decimal('0')

    agg = LivroCaixa.objects.filter(
        conta__is_active=True, conta__tipo='CARTEIRA', estornado=False,
    ).aggregate(
        e=Sum('valor', filter=Q(tipo='ENTRADA')),
        s=Sum('valor', filter=Q(tipo='SAIDA')),
    )
    saldo_cartao = saldo_inicial + (agg['e'] or Decimal('0')) - (agg['s'] or Decimal('0'))

    # Divida = saldo negativo convertido em positivo
    return abs(saldo_cartao) if saldo_cartao < Decimal('0') else Decimal('0')


def calcular_dre_mes(ano, mes):
    rec_qs = Receita.objects.filter(
        recebimento__year=ano, recebimento__month=mes,
        status='RECEBIDO', is_active=True,
    )
    desp_qs = Despesa.objects.filter(
        pagamento__year=ano, pagamento__month=mes,
        status='PAGO', is_active=True, estornado=False,
    )

    receita_operacional = rec_qs.exclude(tipo='RECEITA_FINANCEIRA').aggregate(
        v=Sum('valor_bruto'))['v'] or Decimal('0')
    receita_financeira = rec_qs.filter(tipo='RECEITA_FINANCEIRA').aggregate(
        v=Sum('valor_bruto'))['v'] or Decimal('0')
    receita_bruta = receita_operacional + receita_financeira
    descontos = rec_qs.aggregate(v=Sum('desconto'))['v'] or Decimal('0')
    receita_liquida = receita_bruta - descontos

    fixas = desp_qs.filter(tipo='FIXA').aggregate(v=Sum('valor_liquido'))['v'] or Decimal('0')
    variaveis = desp_qs.filter(tipo='VARIAVEL').aggregate(v=Sum('valor_liquido'))['v'] or Decimal('0')
    prolabore = desp_qs.filter(tipo='PROLABORE').aggregate(v=Sum('valor_liquido'))['v'] or Decimal('0')
    impostos = desp_qs.filter(tipo='IMPOSTO').aggregate(v=Sum('valor_liquido'))['v'] or Decimal('0')
    outros = desp_qs.filter(tipo='OUTRO').aggregate(v=Sum('valor_liquido'))['v'] or Decimal('0')
    total_despesas = fixas + variaveis + prolabore + impostos + outros
    resultado = receita_liquida - total_despesas

    # EBITDA = resultado + impostos + prolabore (sem D&A modelado)
    ebitda = resultado + impostos + prolabore

    receitas_por_cat = list(
        rec_qs.filter(categoria__isnull=False)
        .values('categoria__nome')
        .annotate(total=Sum('valor_liquido'))
        .order_by('-total')
    )
    despesas_por_cat = list(
        desp_qs.filter(categoria__isnull=False)
        .values('categoria__nome')
        .annotate(total=Sum('valor_liquido'))
        .order_by('-total')
    )

    return {
        'receita_operacional': receita_operacional,
        'receita_financeira': receita_financeira,
        'receita_bruta': receita_bruta,
        'descontos': descontos,
        'receita_liquida': receita_liquida,
        'despesas_fixas': fixas,
        'despesas_variaveis': variaveis,
        'prolabore': prolabore,
        'impostos': impostos,
        'outros': outros,
        'total_despesas': total_despesas,
        'resultado': resultado,
        'ebitda': ebitda,
        'receitas_por_categoria': {r['categoria__nome']: r['total'] for r in receitas_por_cat},
        'despesas_por_categoria': {d['categoria__nome']: d['total'] for d in despesas_por_cat},
    }


def calcular_balanco(data_ref=None):
    if data_ref is None:
        data_ref = date.today()

    saldo_caixa = _saldo_total_contas()

    # Contas a receber/pagar precisam incluir PENDENTE e ATRASADO — um
    # recebível/pagável em atraso continua sendo um recebível/pagável,
    # só que vencido; excluir ATRASADO subestimava o balanço.
    contas_a_receber = Receita.objects.filter(
        is_active=True, status__in=['PENDENTE', 'ATRASADO'],
    ).aggregate(v=Sum('valor_liquido'))['v'] or Decimal('0')

    ativo_circulante = saldo_caixa + contas_a_receber
    ativo_total = ativo_circulante

    contas_a_pagar = Despesa.objects.filter(
        is_active=True, status__in=['PENDENTE', 'ATRASADO'], estornado=False,
    ).aggregate(v=Sum('valor_liquido'))['v'] or Decimal('0')

    emprestimos = Aporte.objects.filter(
        is_active=True, tipo='EMPRESTIMO',
    ).aggregate(v=Sum('valor'))['v'] or Decimal('0')

    divida_cartao = _divida_cartao_credito()
    passivo_circulante = contas_a_pagar + divida_cartao
    passivo_exigivel_lp = emprestimos
    passivo_total = passivo_circulante + passivo_exigivel_lp

    capital_aportes = Aporte.objects.filter(
        is_active=True,
    ).exclude(tipo='EMPRESTIMO').aggregate(v=Sum('valor'))['v'] or Decimal('0')

    # Lucros acumulados em regime de competência (não de caixa), pra bater
    # com contas_a_receber/contas_a_pagar acima (também competência) — regime
    # de caixa aqui deixava a equação Ativo = Passivo + PL sem fechar sempre
    # que existisse qualquer receita/despesa pendente ou atrasada.
    total_receitas = Receita.objects.filter(
        is_active=True,
    ).exclude(status='CANCELADO').aggregate(v=Sum('valor_liquido'))['v'] or Decimal('0')
    total_despesas = Despesa.objects.filter(
        is_active=True, estornado=False,
    ).exclude(status='CANCELADO').aggregate(v=Sum('valor_liquido'))['v'] or Decimal('0')
    lucros_acumulados = total_receitas - total_despesas

    patrimonio_liquido = capital_aportes + lucros_acumulados

    equacao_ok = ativo_total == (passivo_total + patrimonio_liquido)

    return {
        'data_referencia': data_ref.isoformat(),
        'ativo': {
            'circulante': {
                'caixa_equivalentes': saldo_caixa,
                'contas_a_receber': contas_a_receber,
                'total': ativo_circulante,
            },
            'total': ativo_total,
        },
        'passivo': {
            'circulante': {
                'contas_a_pagar': contas_a_pagar,
                'cartao_credito_a_pagar': divida_cartao,
                'total': passivo_circulante,
            },
            'exigivel_lp': {
                'emprestimos': emprestimos,
                'total': passivo_exigivel_lp,
            },
            'total': passivo_total,
        },
        'patrimonio_liquido': {
            'capital_aportes': capital_aportes,
            'lucros_acumulados': lucros_acumulados,
            'total': patrimonio_liquido,
        },
        'equacao_ok': equacao_ok,
        'total_ativo': ativo_total,
        'total_passivo_pl': passivo_total + patrimonio_liquido,
    }


def calcular_fluxo_projetado():
    hoje = date.today()
    saldo_atual = _saldo_total_contas()

    limites = [
        ('0-30', hoje, hoje + timedelta(days=30)),
        ('31-60', hoje + timedelta(days=31), hoje + timedelta(days=60)),
        ('61-90', hoje + timedelta(days=61), hoje + timedelta(days=90)),
    ]

    janelas = []
    saldo_projetado = saldo_atual

    for periodo, inicio, fim in limites:
        entradas = Receita.objects.filter(
            is_active=True, status='PENDENTE',
            vencimento__gte=inicio, vencimento__lte=fim,
        ).aggregate(v=Sum('valor_liquido'))['v'] or Decimal('0')

        saidas = Despesa.objects.filter(
            is_active=True, status='PENDENTE', estornado=False,
            vencimento__gte=inicio, vencimento__lte=fim,
        ).aggregate(v=Sum('valor_liquido'))['v'] or Decimal('0')

        resultado = entradas - saidas
        saldo_projetado += resultado

        janelas.append({
            'periodo': periodo,
            'entradas_previstas': entradas,
            'saidas_previstas': saidas,
            'resultado_previsto': resultado,
        })

    receitas_pendentes = list(
        Receita.objects.filter(
            is_active=True, status='PENDENTE',
            vencimento__gte=hoje, vencimento__lte=hoje + timedelta(days=90),
        ).order_by('vencimento').values(
            'id', 'descricao', 'valor_liquido', 'vencimento',
        )[:20]
    )
    despesas_pendentes = list(
        Despesa.objects.filter(
            is_active=True, status='PENDENTE', estornado=False,
            vencimento__gte=hoje, vencimento__lte=hoje + timedelta(days=90),
        ).order_by('vencimento').values(
            'id', 'descricao', 'valor_liquido', 'vencimento', 'fornecedor',
        )[:20]
    )

    return {
        'saldo_atual': saldo_atual,
        'data_referencia': hoje.isoformat(),
        'janelas': janelas,
        'saldo_projetado_90_dias': saldo_projetado,
        'receitas_pendentes': receitas_pendentes,
        'despesas_pendentes': despesas_pendentes,
    }


def calcular_indicadores_cfo():
    hoje = date.today()
    primeiro_dia = hoje.replace(day=1)
    if hoje.month == 12:
        ultimo_dia = date(hoje.year + 1, 1, 1) - timedelta(days=1)
    else:
        ultimo_dia = date(hoje.year, hoje.month + 1, 1) - timedelta(days=1)

    dre_mes = calcular_dre_mes(hoje.year, hoje.month)
    receita_liq = dre_mes['receita_liquida']
    resultado = dre_mes['resultado']
    rec_operacional = dre_mes['receita_operacional']
    desp_fixas = dre_mes['despesas_fixas']
    desp_variaveis = dre_mes['despesas_variaveis']

    margem_liquida = (resultado / receita_liq * 100) if receita_liq else Decimal('0')

    if rec_operacional and rec_operacional != desp_variaveis:
        ponto_equilibrio = desp_fixas / (1 - (desp_variaveis / rec_operacional))
    else:
        ponto_equilibrio = Decimal('0')

    clientes_distintos = Receita.objects.filter(
        is_active=True, status='RECEBIDO',
        recebimento__gte=primeiro_dia, recebimento__lte=ultimo_dia,
        cliente__isnull=False,
    ).values('cliente').distinct().count()
    ticket_medio = (receita_liq / clientes_distintos) if clientes_distintos else Decimal('0')

    mrr = Receita.objects.filter(
        is_active=True, tipo='MENSALIDADE', status='RECEBIDO',
        recebimento__gte=primeiro_dia, recebimento__lte=ultimo_dia,
    ).aggregate(v=Sum('valor_liquido'))['v'] or Decimal('0')

    saldo_total = _saldo_total_contas()

    despesas_3m = []
    for i in range(1, 4):
        m = hoje.month - i
        y = hoje.year
        if m <= 0:
            m += 12
            y -= 1
        total_desp = Despesa.objects.filter(
            pagamento__year=y, pagamento__month=m,
            status='PAGO', is_active=True, estornado=False,
        ).aggregate(v=Sum('valor_liquido'))['v'] or Decimal('0')
        despesas_3m.append(total_desp)

    media_despesas = sum(despesas_3m) / 3 if despesas_3m else Decimal('0')
    runway_meses = (saldo_total / media_despesas) if media_despesas else Decimal('0')

    if hoje.month == 1:
        mes_ant_m, mes_ant_y = 12, hoje.year - 1
    else:
        mes_ant_m, mes_ant_y = hoje.month - 1, hoje.year
    dre_anterior = calcular_dre_mes(mes_ant_y, mes_ant_m)
    resultado_anterior = dre_anterior['resultado']
    if resultado_anterior:
        var_mes_anterior = ((resultado - resultado_anterior) / abs(resultado_anterior) * 100)
    else:
        var_mes_anterior = Decimal('0')

    dre_ano_ant = calcular_dre_mes(hoje.year - 1, hoje.month)
    resultado_ano_ant = dre_ano_ant['resultado']
    if resultado_ano_ant:
        var_ano_anterior = ((resultado - resultado_ano_ant) / abs(resultado_ano_ant) * 100)
    else:
        var_ano_anterior = Decimal('0')

    return {
        'margem_liquida': round(margem_liquida, 2),
        'ponto_equilibrio': round(ponto_equilibrio, 2),
        'ticket_medio': round(ticket_medio, 2),
        'mrr': mrr,
        'saldo_total': saldo_total,
        'runway_meses': round(runway_meses, 1),
        'resultado_mes': resultado,
        'receita_liquida_mes': receita_liq,
        'ebitda_mes': dre_mes['ebitda'],
        'var_mes_anterior': round(var_mes_anterior, 1),
        'var_ano_anterior': round(var_ano_anterior, 1),
    }


CATEGORIAS_KEYWORDS = {
    'Impostos/DAS': ['das', 'simples', 'cofins', 'pis', 'irrf', 'csll', 'inss', 'imposto', 'tributo'],
    'Pró-labore': ['prolabore', 'pró-labore', 'pro-labore', 'retirada', 'salário sócio', 'salario socio'],
    'Aluguel': ['aluguel', 'locação', 'locacao', 'coworking'],
    'Software/SaaS': ['aws', 'azure', 'google cloud', 'github', 'notion', 'slack', 'figma', 'vercel', 'heroku', 'digital ocean', 'hostinger'],
    'Marketing': ['tráfego', 'trafego', 'ads', 'google ads', 'meta ads', 'instagram', 'marketing', 'publicidade'],
    'Serviços Bancários': ['tarifa', 'ted', 'doc', 'iof', 'spread', 'taxa bancária', 'taxa bancaria'],
    'Utilidades': ['energia', 'água', 'agua', 'internet', 'telefone', 'celular', 'luz'],
    'Alimentação': ['alimentação', 'alimentacao', 'refeição', 'refeicao', 'restaurante', 'ifood'],
    'Transporte': ['uber', '99', 'combustível', 'combustivel', 'estacionamento', 'pedágio', 'pedagio'],
    'Escritório': ['papelaria', 'material de escritório', 'material de escritorio', 'toner', 'cartuchos'],
}


def inferir_categoria_descricao(descricao):
    if not descricao:
        return None
    desc_lower = descricao.lower()
    for categoria, keywords in CATEGORIAS_KEYWORDS.items():
        for kw in keywords:
            if kw in desc_lower:
                return categoria
    return None
