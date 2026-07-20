from django.db import connection, transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Aporte, Despesa, LivroCaixa, Receita


def _ultimo_saldo(conta):
    ultimo = (
        LivroCaixa.objects.select_for_update()
        .filter(conta=conta)
        .order_by('data', 'criado_em')
        .last()
    )
    if ultimo:
        return ultimo.saldo_atual
    return conta.saldo_inicial


def _reconstruir_cadeia(conta):
    lancamentos = list(
        LivroCaixa.objects.filter(conta=conta)
        .order_by('data', 'criado_em')
        .select_for_update()
    )
    saldo = conta.saldo_inicial
    for lc in lancamentos:
        lc.saldo_anterior = saldo
        saldo = saldo + lc.valor if lc.tipo == 'ENTRADA' else saldo - lc.valor
        lc.saldo_atual = saldo
    LivroCaixa.objects.bulk_update(lancamentos, ['saldo_anterior', 'saldo_atual'])


def _gerar_lancamento(conta, tipo, origem, origem_id, descricao, valor, data, criado_por=None):
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute('SELECT pg_advisory_xact_lock(%s)', [conta.id])

        existente = LivroCaixa.objects.filter(origem=origem, origem_id=origem_id).first()
        if existente:
            mudou = existente.data != data or existente.valor != valor or existente.descricao != descricao
            if mudou:
                existente.data = data
                existente.valor = valor
                existente.descricao = descricao
                existente.save(update_fields=['data', 'valor', 'descricao'])
                _reconstruir_cadeia(conta)
            return

        saldo_anterior = _ultimo_saldo(conta)
        if tipo == 'ENTRADA':
            saldo_atual = saldo_anterior + valor
        else:
            saldo_atual = saldo_anterior - valor

        LivroCaixa.objects.create(
            conta=conta,
            tipo=tipo,
            origem=origem,
            origem_id=origem_id,
            descricao=descricao,
            valor=valor,
            data=data,
            saldo_anterior=saldo_anterior,
            saldo_atual=saldo_atual,
            criado_por=criado_por,
        )

        _reconstruir_cadeia(conta)


@receiver(post_save, sender=Aporte)
def aporte_para_livro_caixa(sender, instance, created, **kwargs):
    if not created:
        return
    _gerar_lancamento(
        conta=instance.conta,
        tipo='ENTRADA',
        origem='APORTE',
        origem_id=instance.id,
        descricao=f'Aporte: {instance.descricao}',
        valor=instance.valor,
        data=instance.data,
        criado_por=instance.criado_por,
    )


@receiver(post_save, sender=Receita)
def receita_para_livro_caixa(sender, instance, **kwargs):
    if instance.status != 'RECEBIDO' or not instance.recebimento:
        return
    _gerar_lancamento(
        conta=instance.conta,
        tipo='ENTRADA',
        origem='RECEITA',
        origem_id=instance.id,
        descricao=instance.descricao,
        valor=instance.valor_liquido,
        data=instance.recebimento,
        criado_por=instance.criado_por,
    )


@receiver(post_save, sender=Despesa)
def despesa_para_livro_caixa(sender, instance, **kwargs):
    if instance.status != 'PAGO' or not instance.pagamento:
        return
    _gerar_lancamento(
        conta=instance.conta,
        tipo='SAIDA',
        origem='DESPESA',
        origem_id=instance.id,
        descricao=instance.descricao,
        valor=instance.valor_liquido,
        data=instance.pagamento,
        criado_por=instance.criado_por,
    )
