from datetime import date, timedelta
from decimal import Decimal

from django.db import connection, transaction
from django.db.models import Sum, Q
from rest_framework import status
from rest_framework.decorators import action, api_view
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.mixins import CreateModelMixin, ListModelMixin, RetrieveModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ModelViewSet
from django_filters.rest_framework import DjangoFilterBackend

from common.permissions import IsAdmin

from .signals import _reconstruir_cadeia
from .models import (
    Aporte, Categoria, Conta, Despesa, FormaPagamento,
    LivroCaixa, Receita,
)
from .serializers import (
    AporteSerializer, CategoriaSerializer, ContaSerializer,
    DespesaSerializer, LivroCaixaSerializer, ReceitaSerializer,
)


class ReadCreateViewSet(CreateModelMixin, ListModelMixin, RetrieveModelMixin, GenericViewSet):
    pass


class CategoriaViewSet(ModelViewSet):
    queryset = Categoria.objects.filter(is_active=True).order_by('nome')
    serializer_class = CategoriaSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['tipo']

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = False
        instance.save(update_fields=['is_active', 'updated_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)


class ContaViewSet(ModelViewSet):
    queryset = Conta.objects.filter(is_active=True).order_by('nome')
    serializer_class = ContaSerializer
    filter_backends = [SearchFilter]
    search_fields = ['nome']

    def perform_create(self, serializer):
        serializer.save(criado_por=self.request.user)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = False
        instance.save(update_fields=['is_active', 'updated_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'], url_path='transferir')
    def transferir(self, request, pk=None):
        conta_origem = self.get_object()
        conta_destino_id = request.data.get('conta_destino')
        valor_str = request.data.get('valor')
        descricao = request.data.get('descricao') or 'Transferência entre contas'
        data_str = request.data.get('data') or date.today().isoformat()

        if not conta_destino_id or not valor_str:
            return Response({'erro': 'conta_destino e valor são obrigatórios.'}, status=400)

        try:
            valor = Decimal(str(valor_str))
        except Exception:
            return Response({'erro': 'Valor inválido.'}, status=400)

        if valor <= 0:
            return Response({'erro': 'Valor deve ser maior que zero.'}, status=400)

        try:
            conta_destino = Conta.objects.get(id=conta_destino_id, is_active=True)
        except Conta.DoesNotExist:
            return Response({'erro': 'Conta destino não encontrada.'}, status=400)

        if conta_origem.id == conta_destino.id:
            return Response({'erro': 'Conta origem e destino devem ser diferentes.'}, status=400)

        try:
            data = date.fromisoformat(data_str)
        except ValueError:
            return Response({'erro': 'Data inválida.'}, status=400)

        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute('SELECT pg_advisory_xact_lock(%s)', [conta_origem.id])
                cursor.execute('SELECT pg_advisory_xact_lock(%s)', [conta_destino.id])

            saldo_ant_origem = _saldo_real(conta_origem)
            LivroCaixa.objects.create(
                conta=conta_origem,
                tipo='SAIDA',
                origem='TRANSFER',
                descricao=f'Transferência para {conta_destino.nome}: {descricao}',
                valor=valor,
                data=data,
                saldo_anterior=saldo_ant_origem,
                saldo_atual=saldo_ant_origem - valor,
                criado_por=request.user,
            )
            _reconstruir_cadeia(conta_origem)

            saldo_ant_destino = _saldo_real(conta_destino)
            LivroCaixa.objects.create(
                conta=conta_destino,
                tipo='ENTRADA',
                origem='TRANSFER',
                descricao=f'Transferência de {conta_origem.nome}: {descricao}',
                valor=valor,
                data=data,
                saldo_anterior=saldo_ant_destino,
                saldo_atual=saldo_ant_destino + valor,
                criado_por=request.user,
            )
            _reconstruir_cadeia(conta_destino)

        return Response({'ok': True, 'mensagem': f'Transferência de R$ {valor} realizada.'})


class AporteViewSet(ModelViewSet):
    queryset = Aporte.objects.filter(is_active=True).select_related('conta').order_by('-data')
    serializer_class = AporteSerializer
    permission_classes = [IsAdmin]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['tipo', 'conta']
    ordering_fields = ['data', 'valor']

    def perform_create(self, serializer):
        serializer.save(criado_por=self.request.user)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = False
        instance.save(update_fields=['is_active', 'updated_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)


class ReceitaViewSet(ModelViewSet):
    queryset = (
        Receita.objects.filter(is_active=True)
        .select_related('cliente', 'conta', 'categoria')
        .order_by('vencimento')
    )
    serializer_class = ReceitaSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['tipo', 'status', 'cliente', 'conta']
    search_fields = ['descricao']
    ordering_fields = ['vencimento', 'valor_liquido', 'status']

    def perform_create(self, serializer):
        serializer.save(criado_por=self.request.user)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = False
        instance.save(update_fields=['is_active', 'updated_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['patch'], url_path='receber')
    def marcar_recebido(self, request, pk=None):
        receita = self.get_object()
        recebimento = request.data.get('recebimento') or date.today().isoformat()
        conta_id = request.data.get('conta')
        if conta_id:
            try:
                receita.conta = Conta.objects.get(id=conta_id)
            except Conta.DoesNotExist:
                return Response({'conta': 'Conta não encontrada.'}, status=400)
        receita.recebimento = recebimento
        receita.status = 'RECEBIDO'
        receita.save()
        return Response(ReceitaSerializer(receita).data)


class DespesaViewSet(ModelViewSet):
    queryset = (
        Despesa.objects.filter(is_active=True)
        .select_related('conta', 'categoria')
        .order_by('vencimento')
    )
    serializer_class = DespesaSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['tipo', 'status', 'conta', 'estornado']
    search_fields = ['descricao', 'fornecedor']
    ordering_fields = ['vencimento', 'valor_liquido', 'status']

    def perform_create(self, serializer):
        serializer.save(criado_por=self.request.user)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = False
        instance.save(update_fields=['is_active', 'updated_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['patch'], url_path='pagar')
    def marcar_pago(self, request, pk=None):
        despesa = self.get_object()
        pagamento = request.data.get('pagamento') or date.today().isoformat()
        conta_id = request.data.get('conta')
        forma_pagamento = request.data.get('forma_pagamento', '')
        if conta_id:
            try:
                despesa.conta = Conta.objects.get(id=conta_id)
            except Conta.DoesNotExist:
                return Response({'conta': 'Conta não encontrada.'}, status=400)
        if forma_pagamento and forma_pagamento not in FormaPagamento.values:
            return Response({'forma_pagamento': 'Forma de pagamento inválida.'}, status=400)
        despesa.pagamento = pagamento
        despesa.forma_pagamento = forma_pagamento
        despesa.status = 'PAGO'
        despesa.save()
        return Response(DespesaSerializer(despesa).data)

    @action(detail=True, methods=['post'], url_path='estornar', permission_classes=[IsAdmin])
    def estornar_despesa(self, request, pk=None):
        despesa = self.get_object()

        if despesa.status != 'PAGO':
            return Response({'detail': 'Somente despesas com status PAGO podem ser estornadas.'}, status=400)

        if despesa.estornado:
            return Response({'detail': 'Despesa já foi estornada.'}, status=400)

        data_estorno_str = request.data.get('data_estorno') or date.today().isoformat()
        motivo = request.data.get('motivo', '')

        if not motivo.strip():
            return Response({'motivo': 'Motivo do estorno é obrigatório.'}, status=400)

        try:
            data_estorno = date.fromisoformat(data_estorno_str)
        except ValueError:
            return Response({'data_estorno': 'Data inválida.'}, status=400)

        conta = despesa.conta

        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute('SELECT pg_advisory_xact_lock(%s)', [conta.id])

            lancamento_original = (
                LivroCaixa.objects.select_for_update()
                .filter(origem='DESPESA', origem_id=despesa.id, estornado=False)
                .first()
            )

            lancamento = LivroCaixa.objects.create(
                conta=conta,
                tipo='ENTRADA',
                origem='ESTORNO',
                origem_id=despesa.id,
                descricao=f'Estorno despesa: {despesa.descricao} — {motivo}',
                valor=despesa.valor_liquido,
                data=data_estorno,
                saldo_anterior=Decimal('0'),
                saldo_atual=Decimal('0'),
                criado_por=request.user,
                estorno_de=lancamento_original,
                estornado=True,
            )

            if lancamento_original:
                lancamento_original.estornado = True
                lancamento_original.save(update_fields=['estornado'])

            despesa.estornado = True
            despesa.data_estorno = data_estorno
            despesa.motivo_estorno = motivo
            despesa.save(update_fields=['estornado', 'data_estorno', 'motivo_estorno'])

            _reconstruir_cadeia(conta)
            lancamento.refresh_from_db()

        return Response(LivroCaixaSerializer(lancamento).data, status=201)


class LivroCaixaViewSet(ReadCreateViewSet):
    queryset = (
        LivroCaixa.objects.select_related('conta')
        .order_by('-data', '-criado_em')
    )
    serializer_class = LivroCaixaSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['conta', 'tipo', 'origem', 'estornado']
    ordering_fields = ['data', 'valor']

    def perform_create(self, serializer):
        serializer.save(criado_por=self.request.user)

    @action(detail=True, methods=['post'], permission_classes=[IsAdmin])
    def estornar(self, request, pk=None):
        lancamento = self.get_object()
        if lancamento.estornado:
            return Response({'detail': 'Lançamento já estornado.'}, status=400)

        motivo = request.data.get('motivo', '')
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute('SELECT pg_advisory_xact_lock(%s)', [lancamento.conta_id])

            tipo_estorno = 'ENTRADA' if lancamento.tipo == 'SAIDA' else 'SAIDA'

            estorno = LivroCaixa.objects.create(
                conta=lancamento.conta,
                tipo=tipo_estorno,
                origem='MANUAL',
                descricao=f'Estorno: {lancamento.descricao}' + (f' — {motivo}' if motivo else ''),
                valor=lancamento.valor,
                data=date.today(),
                saldo_anterior=Decimal('0'),
                saldo_atual=Decimal('0'),
                criado_por=request.user,
                estorno_de=lancamento,
                estornado=True,
            )
            lancamento.estornado = True
            lancamento.save(update_fields=['estornado'])

            _reconstruir_cadeia(lancamento.conta)
            estorno.refresh_from_db()

        return Response(LivroCaixaSerializer(estorno).data, status=201)

    @action(detail=False, methods=['get'])
    def totais(self, request):
        conta_id = request.query_params.get('conta')
        qs = LivroCaixa.objects.filter(estornado=False)
        if conta_id:
            qs = qs.filter(conta_id=conta_id)
        agg = qs.aggregate(
            total_entradas=Sum('valor', filter=Q(tipo='ENTRADA')),
            total_saidas=Sum('valor', filter=Q(tipo='SAIDA')),
        )
        total_entradas = agg['total_entradas'] or Decimal('0')
        total_saidas = agg['total_saidas'] or Decimal('0')

        if conta_id:
            try:
                conta = Conta.objects.get(id=conta_id)
                saldo_atual = conta.saldo_inicial + total_entradas - total_saidas
            except Conta.DoesNotExist:
                saldo_atual = total_entradas - total_saidas
        else:
            saldo_inicial_total = Conta.objects.filter(is_active=True).aggregate(
                v=Sum('saldo_inicial')
            )['v'] or Decimal('0')
            saldo_atual = saldo_inicial_total + total_entradas - total_saidas

        return Response({
            'total_entradas': total_entradas,
            'total_saidas': total_saidas,
            'saldo_atual': saldo_atual,
        })


def _saldo_real(conta):
    agg = LivroCaixa.objects.filter(
        conta=conta, estornado=False,
    ).aggregate(
        e=Sum('valor', filter=Q(tipo='ENTRADA')),
        s=Sum('valor', filter=Q(tipo='SAIDA')),
    )
    return conta.saldo_inicial + (agg['e'] or Decimal('0')) - (agg['s'] or Decimal('0'))


@api_view(['GET'])
def fluxo_caixa(request):
    mes_str = request.query_params.get('mes')
    conta_id = request.query_params.get('conta')

    try:
        if mes_str:
            ano, mes = int(mes_str[:4]), int(mes_str[5:7])
        else:
            hoje = date.today()
            ano, mes = hoje.year, hoje.month
    except (ValueError, IndexError):
        return Response({'detail': 'Formato inválido. Use mes=YYYY-MM.'}, status=400)

    qs = LivroCaixa.objects.filter(
        data__year=ano, data__month=mes, estornado=False,
    )
    conta = None
    if conta_id:
        try:
            conta = Conta.objects.get(id=conta_id)
            qs = qs.filter(conta=conta)
        except Conta.DoesNotExist:
            pass

    agg = qs.aggregate(
        total_entradas=Sum('valor', filter=Q(tipo='ENTRADA')),
        total_saidas=Sum('valor', filter=Q(tipo='SAIDA')),
    )

    primeiro_dia = date(ano, mes, 1)

    def _saldo_antes(conta_obj):
        agg_prev = LivroCaixa.objects.filter(
            conta=conta_obj, data__lt=primeiro_dia, estornado=False,
        ).aggregate(
            e=Sum('valor', filter=Q(tipo='ENTRADA')),
            s=Sum('valor', filter=Q(tipo='SAIDA')),
        )
        return conta_obj.saldo_inicial + (agg_prev['e'] or Decimal('0')) - (agg_prev['s'] or Decimal('0'))

    if conta_id and conta:
        saldo_inicial = _saldo_antes(conta)
    else:
        saldo_inicial = Decimal('0')
        for _c in Conta.objects.filter(is_active=True):
            saldo_inicial += _saldo_antes(_c)

    total_entradas = agg['total_entradas'] or Decimal('0')
    total_saidas = agg['total_saidas'] or Decimal('0')
    saldo_final = saldo_inicial + total_entradas - total_saidas

    lancamentos = LivroCaixaSerializer(qs.order_by('data', 'criado_em'), many=True).data

    return Response({
        'periodo': f'{mes:02d}/{ano}',
        'conta': conta.nome if conta else 'Todas',
        'saldo_inicial': saldo_inicial,
        'total_entradas': total_entradas,
        'total_saidas': total_saidas,
        'saldo_final': saldo_final,
        'lancamentos': lancamentos,
    })


@api_view(['GET'])
def dre(request):
    try:
        ano = int(request.query_params.get('ano', date.today().year))
    except ValueError:
        return Response({'detail': 'Ano inválido.'}, status=400)

    meses = []
    totais = {
        'receita_operacional': Decimal('0'), 'receita_financeira': Decimal('0'),
        'receita_bruta': Decimal('0'), 'descontos': Decimal('0'),
        'receita_liquida': Decimal('0'), 'despesas_fixas': Decimal('0'),
        'despesas_variaveis': Decimal('0'), 'prolabore': Decimal('0'),
        'impostos': Decimal('0'), 'total_despesas': Decimal('0'),
        'resultado': Decimal('0'),
    }

    for mes in range(1, 13):
        rec_qs = Receita.objects.filter(
            recebimento__year=ano, recebimento__month=mes, status='RECEBIDO', is_active=True,
        )
        desp_qs = Despesa.objects.filter(
            pagamento__year=ano, pagamento__month=mes, status='PAGO', is_active=True, estornado=False,
        )

        receita_operacional = rec_qs.exclude(tipo='RECEITA_FINANCEIRA').aggregate(v=Sum('valor_bruto'))['v'] or Decimal('0')
        receita_financeira = rec_qs.filter(tipo='RECEITA_FINANCEIRA').aggregate(v=Sum('valor_bruto'))['v'] or Decimal('0')
        receita_bruta = receita_operacional + receita_financeira
        descontos = rec_qs.aggregate(v=Sum('desconto'))['v'] or Decimal('0')
        receita_liq = receita_bruta - descontos

        fixas = desp_qs.filter(tipo='FIXA').aggregate(v=Sum('valor_liquido'))['v'] or Decimal('0')
        variaveis = desp_qs.filter(tipo='VARIAVEL').aggregate(v=Sum('valor_liquido'))['v'] or Decimal('0')
        prolabore = desp_qs.filter(tipo='PROLABORE').aggregate(v=Sum('valor_liquido'))['v'] or Decimal('0')
        impostos = desp_qs.filter(tipo='IMPOSTO').aggregate(v=Sum('valor_liquido'))['v'] or Decimal('0')
        outros = desp_qs.filter(tipo='OUTRO').aggregate(v=Sum('valor_liquido'))['v'] or Decimal('0')
        total_desp = fixas + variaveis + prolabore + impostos + outros
        resultado = receita_liq - total_desp

        dados_mes = {
            'mes': f'{mes:02d}/{ano}',
            'receita_operacional': receita_operacional,
            'receita_financeira': receita_financeira,
            'receita_bruta': receita_bruta,
            'descontos': descontos,
            'receita_liquida': receita_liq,
            'despesas_fixas': fixas,
            'despesas_variaveis': variaveis,
            'prolabore': prolabore,
            'impostos': impostos,
            'outros': outros,
            'total_despesas': total_desp,
            'resultado': resultado,
        }
        meses.append(dados_mes)

        for k in totais:
            totais[k] += dados_mes.get(k, Decimal('0'))

    return Response({'ano': ano, 'meses': meses, 'totais_ano': totais})


@api_view(['GET'])
def dashboard_financeiro(request):
    hoje = date.today()
    primeiro_dia = hoje.replace(day=1)
    if hoje.month == 12:
        ultimo_dia = date(hoje.year + 1, 1, 1) - timedelta(days=1)
    else:
        ultimo_dia = date(hoje.year, hoje.month + 1, 1) - timedelta(days=1)

    agg_mes = LivroCaixa.objects.filter(
        estornado=False, data__gte=primeiro_dia, data__lte=ultimo_dia,
    ).aggregate(
        rec=Sum('valor', filter=Q(tipo='ENTRADA')),
        des=Sum('valor', filter=Q(tipo='SAIDA')),
    )
    receita_mes = agg_mes['rec'] or Decimal('0')
    despesa_mes = agg_mes['des'] or Decimal('0')

    mrr = Receita.objects.filter(
        is_active=True, tipo='MENSALIDADE', status='RECEBIDO',
        recebimento__gte=primeiro_dia, recebimento__lte=ultimo_dia,
    ).aggregate(v=Sum('valor_liquido'))['v'] or Decimal('0')

    prox_30 = hoje + timedelta(days=30)
    receitas_vencer = list(
        Receita.objects.filter(is_active=True, status='PENDENTE', vencimento__gte=hoje, vencimento__lte=prox_30)
        .select_related('cliente').order_by('vencimento')[:8]
        .values('id', 'descricao', 'valor_liquido', 'vencimento', 'cliente__nome_razao_social')
    )

    despesas_vencer = list(
        Despesa.objects.filter(is_active=True, status='PENDENTE', vencimento__gte=hoje, vencimento__lte=prox_30)
        .order_by('vencimento')[:8]
        .values('id', 'descricao', 'valor_liquido', 'vencimento', 'fornecedor')
    )

    saldo_total = Conta.objects.filter(is_active=True).aggregate(
        v=Sum('saldo_inicial')
    )['v'] or Decimal('0')
    agg_saldo = LivroCaixa.objects.filter(
        conta__is_active=True, estornado=False,
    ).aggregate(
        e=Sum('valor', filter=Q(tipo='ENTRADA')),
        s=Sum('valor', filter=Q(tipo='SAIDA')),
    )
    saldo_total += (agg_saldo['e'] or Decimal('0')) - (agg_saldo['s'] or Decimal('0'))

    MESES_PT = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
    grafico = []
    for i in range(5, -1, -1):
        m = hoje.month - i
        y = hoje.year
        if m <= 0:
            m += 12
            y -= 1
        p = date(y, m, 1)
        u = date(y + 1, 1, 1) - timedelta(days=1) if m == 12 else date(y, m + 1, 1) - timedelta(days=1)
        agg = LivroCaixa.objects.filter(estornado=False, data__gte=p, data__lte=u).aggregate(
            rec=Sum('valor', filter=Q(tipo='ENTRADA')),
            des=Sum('valor', filter=Q(tipo='SAIDA')),
        )
        rec = agg['rec'] or Decimal('0')
        des = agg['des'] or Decimal('0')
        grafico.append({
            'mes': f'{y}-{m:02d}', 'label': MESES_PT[m - 1],
            'receita': rec, 'despesa': des, 'resultado': rec - des,
        })

    return Response({
        'receita_mes': receita_mes,
        'despesa_mes': despesa_mes,
        'resultado_mes': receita_mes - despesa_mes,
        'saldo_total_contas': saldo_total,
        'mrr': mrr,
        'receitas_vencer': receitas_vencer,
        'despesas_vencer': despesas_vencer,
        'grafico_6_meses': grafico,
        'receitas_atrasadas': Receita.objects.filter(is_active=True, status='ATRASADO').count(),
        'despesas_atrasadas': Despesa.objects.filter(is_active=True, status='ATRASADO').count(),
    })
