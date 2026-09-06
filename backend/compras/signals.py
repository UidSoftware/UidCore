"""
compras/signals.py — RF-07 (Manutencao #58, Fase 2).

Gera/sincroniza a financeiro.Despesa a partir do ciclo de vida da Compra.
NUNCA escreve em LivroCaixa diretamente — quem cria o LivroCaixa e sempre
o signal ja existente `financeiro.signals.despesa_para_livro_caixa`,
disparado indiretamente quando este signal chama `despesa.save()`.
"""
from datetime import date

from django.db.models.signals import post_save
from django.dispatch import receiver

from financeiro.models import Categoria, Despesa

from .models import Compra


@receiver(post_save, sender=Compra)
def compra_sincroniza_despesa(sender, instance, created, **kwargs):
    if created:
        # RF-09: get_or_create idempotente — se a data migration de seed
        # ainda nao tiver rodado num ambiente, cai em categoria=None sem
        # erro (limit_choices_to e so validacao de formulario, nao bloqueia
        # create() direto via ORM).
        categoria = Categoria.objects.filter(
            nome='Compra de Mercadoria', tipo='SAIDA', is_active=True,
        ).first()

        despesa = Despesa.objects.create(
            tipo='VARIAVEL',
            descricao=(
                f'Compra #{instance.pk} — NF {instance.numero_nota_fiscal or "s/n"} — '
                f'{instance.fornecedor.nome_razao_social}'
            ),
            fornecedor=instance.fornecedor.nome_razao_social,  # RN-04: continua CharField
            valor_bruto=instance.valor_total,
            conta=instance.conta,
            categoria=categoria,
            forma_pagamento=instance.forma_pagamento,
            status=instance.status,
            vencimento=instance.data_emissao,
            pagamento=instance.data_emissao if instance.status == 'PAGO' else None,
            observacoes=instance.observacoes,
            criado_por=instance.criado_por,
        )
        # update() de queryset nao dispara post_save de novo (evita loop) —
        # mesmo truque ja usado em ProdutoSerializer.create() da Fase 1.
        Compra.objects.filter(pk=instance.pk).update(despesa=despesa)
        instance.despesa = despesa
        return

    if instance.despesa_id and instance.despesa.status != instance.status:
        despesa = instance.despesa
        despesa.status = instance.status
        if instance.status == 'PAGO' and not despesa.pagamento:
            despesa.pagamento = date.today()
        despesa.save()  # re-dispara financeiro.signals.despesa_para_livro_caixa
