"""Management command: conciliar_extrato -- conciliacao bancaria em 3 camadas."""
import re
from datetime import date, datetime
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from financeiro.conciliacao_service import criar_conciliacao
from financeiro.models import Conta
from financeiro.parsers import extrair_texto_pdf, get_parser


class Command(BaseCommand):
    help = 'Concilia extrato bancario PDF com o LivroCaixa do UidCore.'

    def add_arguments(self, parser):
        parser.add_argument('--arquivo', required=True, help='Caminho para o PDF do extrato')
        parser.add_argument('--conta',   required=True, help='Nome da conta (C6, BTG, etc.)')
        parser.add_argument('--mes',     default=None,  help='Periodo YYYY-MM (inferido do nome do arquivo se omitido)')
        parser.add_argument('--auto',    action='store_true', help='Modo automatico: assenta pendentes e cria por padrao aprovado')
        parser.add_argument('--senha',   default='609393', help='Senha do PDF (deixar vazio se sem senha)')

    def handle(self, *args, **options):
        arquivo    = options['arquivo']
        nome_conta = options['conta']
        mes_str    = options['mes']
        auto       = options['auto']
        senha      = options['senha'] or None

        # Resolve conta
        try:
            conta = Conta.objects.get(nome__iexact=nome_conta, is_active=True)
        except Conta.DoesNotExist:
            raise CommandError(f'Conta "{nome_conta}" nao encontrada ou inativa.')

        # Infere periodo
        if mes_str:
            try:
                periodo = datetime.strptime(mes_str + '-01', '%Y-%m-%d').date()
            except ValueError:
                raise CommandError('Formato invalido para --mes: use YYYY-MM.')
        else:
            m = re.search(r'(\d{4})-(\d{2})', Path(arquivo).name)
            if m:
                periodo = date(int(m.group(1)), int(m.group(2)), 1)
            else:
                raise CommandError('Nao foi possivel inferir o mes. Use --mes YYYY-MM.')

        self.stdout.write(f'\nProcessando: {Path(arquivo).name}')
        self.stdout.write(f'   Conta  : {conta.nome}')
        self.stdout.write(f'   Periodo: {periodo.strftime("%m/%Y")}\n')

        # Extrai texto do PDF
        try:
            texto = extrair_texto_pdf(arquivo, senha=senha)
        except Exception as e:
            raise CommandError(f'Erro ao ler PDF: {e}')

        # Parseia de acordo com o banco
        try:
            parser = get_parser(conta.nome)
        except ValueError as e:
            raise CommandError(str(e))

        transacoes_banco = parser(texto, ano=periodo.year)

        # Filtra so o mes do periodo
        transacoes_banco = [
            t for t in transacoes_banco
            if t['data'].year == periodo.year and t['data'].month == periodo.month
        ]

        self.stdout.write(f'   Transacoes no extrato: {len(transacoes_banco)}\n')

        conc = criar_conciliacao(
            conta=conta,
            transacoes_banco=transacoes_banco,
            periodo=periodo,
            arquivo_nome=Path(arquivo).name,
            criado_por=None,
            auto=auto,
            log=self.stdout.write,
        )

        # Relatorio detalhado dos itens que ainda aguardam revisao humana
        faltando_sistema = list(conc.itens.filter(status='FALTANDO_SISTEMA'))
        faltando_banco = list(conc.itens.filter(status='FALTANDO_BANCO'))

        if faltando_sistema:
            self.stdout.write('\n--- Faltando no sistema (aguardando revisao) ---')
            for item in faltando_sistema:
                sinal = '+' if item.tipo == 'ENTRADA' else '-'
                self.stdout.write(
                    f'  {item.data_banco.strftime("%d/%m")}  '
                    f'{sinal}R${item.valor:,.2f}  '
                    f'{item.descricao_banco[:60]}'
                )

        if faltando_banco:
            self.stdout.write('\n--- Faltando no banco ---')
            for item in faltando_banco:
                sinal = '+' if item.tipo == 'ENTRADA' else '-'
                self.stdout.write(
                    f'  {item.data_banco.strftime("%d/%m")}  '
                    f'{sinal}R${item.valor:,.2f}  '
                    f'{item.descricao_banco[:60]}'
                )

        self.stdout.write(f'\nConciliacao ID: {conc.id}\n')
