"""Management command: carregar_categorias_padrao -- Manutencao #88.

Carga inicial idempotente de Categoria para qualquer ambiente novo (fork/
cliente) que ainda nao tenha nenhuma -- sem isso, o cadastro de Plano
(FK obrigatoria para Categoria tipo=ENTRADA) fica travado em banco vazio.

Idempotente via get_or_create por (nome, tipo, pai) -- RN-04: a unique_together
real do model e so [nome, tipo] (sem pai), entao duas chamadas desta rotina
nunca duplicam (nomes do seed sao unicos por tipo). Rodar 2x nao altera
is_active/pai de categoria ja existente que o usuario tenha editado na mao
(get_or_create nunca sobrescreve registro ja existente).
"""
from django.core.management.base import BaseCommand

from financeiro.models import Categoria

CATEGORIAS_ENTRADA_SEM_PAI = [
    'Venda de serviços',
    'Venda de produtos',
    'Mensalidades',
    'Outras receitas',
]

CATEGORIAS_SAIDA_SEM_PAI = [
    'Aluguel',
    'Água/Luz/Internet',
    'Salários',
    'Pró-labore',
    'Impostos e taxas',
    'Marketing',
    'Manutenção',
    'Combustível',
    'Outras despesas',
]

# RF-07: subcategorias de Combustivel (SAIDA), 1 nivel, pai resolvido em
# tempo de execucao (depende do get_or_create de 'Combustível' acima).
SUBCATEGORIAS_SAIDA = {
    'Combustível': ['Carro', 'Moto'],
}


class Command(BaseCommand):
    help = (
        'Carga inicial idempotente de Categoria (ENTRADA/SAIDA + subcategorias '
        'de Combustivel). Seguro rodar mais de uma vez -- nunca duplica nem '
        'sobrescreve categoria ja existente.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Nao grava nada no banco, apenas mostra o que seria criado.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        criadas = 0
        existentes = 0

        self.stdout.write('\nCarregando categorias padrao...')
        if dry_run:
            self.stdout.write('   Modo --dry-run: nenhuma Categoria sera gravada.\n')

        pais_por_nome = {}

        for nome in CATEGORIAS_ENTRADA_SEM_PAI:
            criada = self._get_or_create(nome, 'ENTRADA', pai=None, dry_run=dry_run)
            criadas += int(criada)
            existentes += int(not criada)

        for nome in CATEGORIAS_SAIDA_SEM_PAI:
            criada = self._get_or_create(nome, 'SAIDA', pai=None, dry_run=dry_run)
            criadas += int(criada)
            existentes += int(not criada)
            if nome in SUBCATEGORIAS_SAIDA:
                pais_por_nome[nome] = self._buscar_pai(nome, 'SAIDA', dry_run=dry_run)

        for nome_pai, subnomes in SUBCATEGORIAS_SAIDA.items():
            pai = pais_por_nome.get(nome_pai)
            for subnome in subnomes:
                criada = self._get_or_create(subnome, 'SAIDA', pai=pai, dry_run=dry_run)
                criadas += int(criada)
                existentes += int(not criada)

        self.stdout.write(f'   Criadas    : {criadas}')
        self.stdout.write(f'   Ja existiam: {existentes}')
        self.stdout.write(self.style.SUCCESS('\nConcluido.'))

    def _buscar_pai(self, nome, tipo, dry_run):
        if dry_run:
            return Categoria.objects.filter(nome=nome, tipo=tipo, pai__isnull=True).first()
        return Categoria.objects.get(nome=nome, tipo=tipo, pai__isnull=True)

    def _get_or_create(self, nome, tipo, pai, dry_run):
        """Retorna True se a categoria foi (ou seria, em --dry-run) criada agora."""
        ja_existe = Categoria.objects.filter(nome=nome, tipo=tipo).exists()
        if ja_existe:
            self.stdout.write(f'   = ja existe: {nome} ({tipo})' + (f' pai={pai.nome}' if pai else ''))
            return False

        if dry_run:
            self.stdout.write(f'   + criaria  : {nome} ({tipo})' + (f' pai={pai.nome}' if pai else ''))
            return True

        Categoria.objects.get_or_create(
            nome=nome, tipo=tipo, pai=pai, defaults={'is_active': True},
        )
        self.stdout.write(f'   + criada   : {nome} ({tipo})' + (f' pai={pai.nome}' if pai else ''))
        return True
