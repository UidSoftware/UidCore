"""Parsers de extrato bancario em PDF para o modulo de conciliacao."""
import re
import subprocess
from datetime import date
from decimal import Decimal, InvalidOperation

try:
    import pikepdf
except ImportError:  # pragma: no cover - dependencia sempre presente em runtime
    pikepdf = None


def _pdf_exige_senha(caminho_arquivo: str) -> bool:
    """Verifica via pikepdf se o PDF esta protegido por senha.

    RN-D07: PDFs com senha sem o campo senha informado devem ser rejeitados
    com uma mensagem clara, em vez de deixar o subprocess pdftotext falhar
    com uma mensagem generica de stderr.

    Retorna False se pikepdf nao estiver disponivel (falha aberta -- o
    proprio pdftotext ainda vai rejeitar o arquivo levantando RuntimeError).
    """
    if pikepdf is None:
        return False
    try:
        with pikepdf.open(caminho_arquivo):
            return False
    except pikepdf.PasswordError:
        return True
    except pikepdf.PdfError:
        return False


def extrair_texto_pdf(caminho_arquivo: str, senha: str | None = None) -> str:
    """Extrai texto de PDF usando pdftotext via subprocess.

    Args:
        caminho_arquivo: Caminho absoluto para o arquivo PDF.
        senha: Senha do PDF, ou None se nao tiver senha.

    Returns:
        Texto completo extraido do PDF.

    Raises:
        RuntimeError: Se o PDF exigir senha e nenhuma senha foi informada,
            ou se pdftotext retornar codigo diferente de 0.
    """
    if not senha and _pdf_exige_senha(caminho_arquivo):
        raise RuntimeError(
            'PDF protegido por senha. Informe o campo "senha" para continuar.'
        )

    cmd = ['pdftotext', '-layout']
    if senha:
        cmd += ['-upw', senha]
    cmd += [caminho_arquivo, '-']

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=30,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f'pdftotext falhou (codigo {result.returncode}): {result.stderr.strip()}'
        )

    return result.stdout


def _parse_valor_br(texto: str) -> Decimal:
    """Converte string de valor brasileiro para Decimal.

    Remove tudo exceto digitos e virgula, substitui virgula por ponto.

    Returns:
        Decimal do valor, ou Decimal('0') em caso de erro.
    """
    try:
        limpo = re.sub(r'[^\d,]', '', texto)
        limpo = limpo.replace(',', '.')
        return Decimal(limpo)
    except (InvalidOperation, ValueError):
        return Decimal('0')


def parse_c6(texto: str, ano: int) -> list[dict]:
    """Parseia extrato do banco C6.

    Formato esperado: DD/MM  DESCRICAO  +/-VALOR
    Sinal + = ENTRADA, sinal - = SAIDA.

    Returns:
        Lista de dicts com chaves: data (date), descricao (str),
        valor (Decimal), tipo ('ENTRADA'|'SAIDA').
    """
    padrao = re.compile(
        r'^(\d{2}/\d{2})\s+(.+?)\s+([-+]?\s*[\d.]+,\d{2})\s*$',
        re.MULTILINE,
    )

    resultado = []
    for m in padrao.finditer(texto):
        data_str, descricao, valor_str = m.group(1), m.group(2).strip(), m.group(3).strip()

        # Remove espacos internos do valor (ex: "- 1.234,56" -> "-1.234,56")
        valor_str_limpo = valor_str.replace(' ', '')

        eh_saida = valor_str_limpo.startswith('-')
        valor = _parse_valor_br(valor_str_limpo)

        if valor == Decimal('0'):
            continue

        dia, mes = int(data_str[:2]), int(data_str[3:])
        try:
            data = date(ano, mes, dia)
        except ValueError:
            continue

        resultado.append({
            'data': data,
            'descricao': descricao,
            'valor': valor,
            'tipo': 'SAIDA' if eh_saida else 'ENTRADA',
        })

    return resultado


def parse_btg(texto: str, ano: int) -> list[dict]:
    """Parseia extrato do banco BTG.

    Formato esperado: DD/MM/AAAA  DESCRICAO  D/C  VALOR
    D = debito = SAIDA; C = credito = ENTRADA.

    Returns:
        Lista de dicts com chaves: data (date), descricao (str),
        valor (Decimal), tipo ('ENTRADA'|'SAIDA').
    """
    padrao = re.compile(
        r'(\d{2}/\d{2}/\d{4})\s+(.+?)\s+([DC])\s+([\d.]+,\d{2})',
        re.MULTILINE,
    )

    resultado = []
    for m in padrao.finditer(texto):
        data_str, descricao, dc, valor_str = (
            m.group(1), m.group(2).strip(), m.group(3), m.group(4).strip()
        )

        valor = _parse_valor_br(valor_str)
        if valor == Decimal('0'):
            continue

        try:
            dia, mes, ano_doc = int(data_str[:2]), int(data_str[3:5]), int(data_str[6:10])
            data = date(ano_doc, mes, dia)
        except ValueError:
            continue

        resultado.append({
            'data': data,
            'descricao': descricao,
            'valor': valor,
            'tipo': 'SAIDA' if dc == 'D' else 'ENTRADA',
        })

    return resultado


def parse_nubank(texto: str, ano: int) -> list[dict]:
    """Stub — Nubank nao implementado. Retorna lista vazia."""
    return []


def parse_inter(texto: str, ano: int) -> list[dict]:
    """Stub — Inter nao implementado. Retorna lista vazia."""
    return []


def parse_caixa(texto: str, ano: int) -> list[dict]:
    """Stub — Caixa nao implementado. Retorna lista vazia."""
    return []


def parse_itau(texto: str, ano: int) -> list[dict]:
    """Stub — Itau nao implementado. Retorna lista vazia."""
    return []


_PARSERS = {
    'C6': parse_c6,
    'BTG': parse_btg,
    'NUBANK': parse_nubank,
    'INTER': parse_inter,
    'CAIXA': parse_caixa,
    'ITAU': parse_itau,
}


def get_parser(nome_conta: str):
    """Retorna a funcao parser correspondente ao nome da conta.

    A busca e feita por substring case-insensitive no nome da conta.

    Args:
        nome_conta: Nome da conta bancaria (ex: 'Conta C6 PJ').

    Returns:
        Funcao parser callable.

    Raises:
        ValueError: Se nenhum parser for encontrado para o nome da conta.
    """
    nome_upper = nome_conta.upper()
    for chave, parser in _PARSERS.items():
        if chave in nome_upper:
            return parser

    chaves_disponiveis = ', '.join(_PARSERS.keys())
    raise ValueError(
        f'Nenhum parser encontrado para a conta "{nome_conta}". '
        f'Bancos suportados: {chaves_disponiveis}.'
    )
