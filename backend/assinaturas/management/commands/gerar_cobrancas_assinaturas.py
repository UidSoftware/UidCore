"""Management command: gerar_cobrancas_assinaturas -- Manutencao #64 [NUCLEO 3/5]."""
from datetime import date, datetime

from django.core.management.base import BaseCommand, CommandError

from assinaturas.services import gerar_cobrancas_mes


class Command(BaseCommand):
    help = 'Gera as cobrancas (financeiro.Receita PENDENTE) do mes para assinaturas ATIVA elegiveis.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--mes', default=None,
            help='Mes de competencia AAAA-MM (default: mes corrente).',
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Nao grava nenhuma Receita no banco, apenas simula.',
        )

    def handle(self, *args, **options):
        mes_str = options['mes']
        dry_run = options['dry_run']

        if mes_str:
            try:
                mes = datetime.strptime(mes_str + '-01', '%Y-%m-%d').date()
            except ValueError:
                raise CommandError('Formato invalido para --mes: use AAAA-MM.')
        else:
            mes = date.today().replace(day=1)

        self.stdout.write(f'\nGerando cobrancas de assinaturas - competencia {mes.strftime("%m/%Y")}')
        if dry_run:
            self.stdout.write('   Modo --dry-run: nenhuma Receita sera gravada.\n')

        resumo = gerar_cobrancas_mes(mes, dry_run=dry_run)

        self.stdout.write(f"   Criadas             : {resumo['criadas']}")
        self.stdout.write(f"   Puladas (idempot.)  : {resumo['puladas_idempotencia']}")
        self.stdout.write(f"   Puladas (elegibil.) : {resumo['puladas_elegibilidade']}")
        self.stdout.write(f"   Erros               : {len(resumo['erros'])}")

        for erro in resumo['erros']:
            self.stdout.write(self.style.WARNING(
                f"   -> Assinatura #{erro['assinatura_id']}: {erro['erro']}"
            ))

        # RF-06: erro parcial nao derruba o comando inteiro (exit code 0,
        # cron nao deve re-tentar o mes inteiro por causa de 1 assinatura
        # com dado inconsistente) -- CommandError so e levantado se TODAS
        # as assinaturas efetivamente tentadas (criadas + idempotencia +
        # erros, excluindo as puladas por elegibilidade de periodicidade,
        # que nunca chegaram a ser tentadas) tiverem falhado.
        tentativas = resumo['criadas'] + resumo['puladas_idempotencia'] + len(resumo['erros'])
        if resumo['erros'] and len(resumo['erros']) == tentativas:
            raise CommandError('Todas as assinaturas processadas falharam. Veja o resumo acima.')

        self.stdout.write(self.style.SUCCESS('\nConcluido.'))
