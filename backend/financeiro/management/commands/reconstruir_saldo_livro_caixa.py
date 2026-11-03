from django.core.management.base import BaseCommand
from django.db import transaction

from financeiro.models import Conta, LivroCaixa


class Command(BaseCommand):
    help = 'Reconstroi saldo_anterior/saldo_atual do LivroCaixa em ordem cronologica por conta'

    def handle(self, *args, **options):
        for conta in Conta.objects.all():
            self.stdout.write(f'Reconstruindo conta: {conta.nome}')
            with transaction.atomic():
                lancamentos = list(
                    LivroCaixa.objects.filter(conta=conta)
                    .order_by('data', 'criado_em', 'pk')
                    .select_for_update()
                )
                if not lancamentos:
                    self.stdout.write('  Sem lancamentos - ignorando')
                    continue

                saldo = conta.saldo_inicial
                for lc in lancamentos:
                    lc.saldo_anterior = saldo
                    saldo = saldo + lc.valor if lc.tipo == 'ENTRADA' else saldo - lc.valor
                    lc.saldo_atual = saldo

                LivroCaixa.objects.bulk_update(lancamentos, ['saldo_anterior', 'saldo_atual'])
                self.stdout.write(self.style.SUCCESS(
                    f'  {len(lancamentos)} lancamentos corrigidos - saldo final: R${saldo}'
                ))

        self.stdout.write(self.style.SUCCESS('Concluido.'))
