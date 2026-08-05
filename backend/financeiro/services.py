"""
financeiro/services.py — funções de serviço compartilhadas do módulo financeiro.

Segue o mesmo padrão de conciliacao_service.py: lógica procedural dentro de
transaction.atomic() + pg_advisory_xact_lock, chamada por ViewSets quando a
operação depende de dados do payload ou precisa abortar antes do commit
(ADR-021).

estornar_receita() é usada tanto por ReceitaViewSet.estornar quanto por
pdv.services.cancelar_venda/devolver_item (ADR-016).
"""
from datetime import date as _date
from decimal import Decimal

from django.db import connection, transaction
from rest_framework.exceptions import ValidationError

from .models import EstornoReceita, LivroCaixa
from .signals import _reconstruir_cadeia


def estornar_receita(receita, valor, motivo, data_estorno=None, item_venda=None, usuario=None):
    """
    Estorno parcial ou total de uma Receita (ADR-016).

    Regras:
      - Somente Receitas com status=RECEBIDO podem ser estornadas (RN-04).
      - Motivo não pode ser vazio (RN-05).
      - 0 < valor <= saldo_disponivel (nunca deixa saldo negativo, RN-04).
      - Só marca LivroCaixa original como estornado=True quando o estorno
        ESGOTA o saldo (estorno total) — estorno parcial não "anula" o
        lançamento original (ADR-007 adaptado para parcial).
      - DRE abate no mês da receita original (ADR-017) — feito em
        relatorios.calcular_dre_mes via EstornoReceita.receita.recebimento.

    Retorna o EstornoReceita criado.
    """
    if receita.status != 'RECEBIDO':
        raise ValidationError({'receita': 'Somente receitas RECEBIDO podem ser estornadas.'})

    if not motivo or not str(motivo).strip():
        raise ValidationError({'motivo': 'Motivo do estorno e obrigatorio.'})

    saldo = receita.saldo_disponivel
    if valor <= Decimal('0') or valor > saldo:
        raise ValidationError({
            'valor': f'Valor deve ser > 0 e <= saldo disponivel (R$ {saldo}).',
        })

    data_estorno = data_estorno or _date.today()
    conta = receita.conta

    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute('SELECT pg_advisory_xact_lock(%s)', [conta.id])

        estorno = EstornoReceita.objects.create(
            receita=receita,
            valor=valor,
            motivo=motivo,
            data_estorno=data_estorno,
            item_venda=item_venda,
            criado_por=usuario,
        )

        # Lançamento de SAIDA no LivroCaixa (o dinheiro sai de volta — ADR-007)
        lancamento_original = (
            LivroCaixa.objects.select_for_update()
            .filter(origem='RECEITA', origem_id=receita.id, estornado=False)
            .first()
        )

        esgota_saldo = (saldo - valor) <= Decimal('0')

        LivroCaixa.objects.create(
            conta=conta,
            tipo='SAIDA',
            origem='ESTORNO',
            origem_id=receita.id,
            descricao=f'Estorno receita: {receita.descricao} — {motivo}',
            valor=valor,
            data=data_estorno,
            saldo_anterior=Decimal('0'),
            saldo_atual=Decimal('0'),
            criado_por=usuario,
            estorno_de=lancamento_original if esgota_saldo else None,
            estornado=True,
        )

        # ADR-007: só marca o ORIGINAL como estornado=True quando o estorno
        # ESGOTA o saldo — estorno parcial reduz, não anula.
        if esgota_saldo and lancamento_original:
            lancamento_original.estornado = True
            lancamento_original.save(update_fields=['estornado'])

        receita.estornado = esgota_saldo
        receita.data_estorno = data_estorno
        receita.motivo_estorno = motivo
        receita.save(update_fields=['estornado', 'data_estorno', 'motivo_estorno'])

        _reconstruir_cadeia(conta)

    return estorno
