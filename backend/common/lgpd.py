"""
common/lgpd.py — Manutencao #66 [NUCLEO 5/5].

Registry genérico de exportação de dados do titular (LGPD, art. 18 — acesso
e portabilidade). O núcleo nunca conhece os app_labels de negócio: cada app
se registra sozinho, uma linha, dentro do próprio `AppConfig.ready()` (mesmo
padrão já usado por `signals.py` nos apps existentes). Um app novo que queira
aparecer na exportação só precisa chamar `registrar_exportador()` — este
arquivo não é alterado para isso (RN-04 da Especificacao_Hotfix).
"""

_REGISTRY = {}


def registrar_exportador(app_label, titulo, funcao):
    """
    Registra a função de exportação de um app.

    funcao(cliente) -> dict | None.
    None ou {} = o app não tem dado para esse cliente — a seção é omitida
    do relatório (nunca aparece "vazia" no PDF/JSON).
    """
    _REGISTRY[app_label] = {'titulo': titulo, 'funcao': funcao}


def exportar_tudo(cliente):
    """
    Agrega a seção de cada app registrado para o cliente informado.

    Retorna [{"app": app_label, "titulo": ..., "dados": {...}}] — apenas
    para os apps cuja função devolveu dado real para este cliente.
    """
    secoes = []
    for app_label, info in _REGISTRY.items():
        dados = info['funcao'](cliente)
        if dados:
            secoes.append({'app': app_label, 'titulo': info['titulo'], 'dados': dados})
    return secoes


def apps_registrados():
    """Usado pelos testes do registry — lista os app_labels registrados neste processo."""
    return list(_REGISTRY.keys())


def resumir_secoes(secoes):
    """
    Resumo curto (contagem por seção) para `ExportacaoTitular.conteudo_resumo`
    — auditoria sem precisar guardar o PDF/JSON inteiro (RF-03).
    """
    partes = []
    for secao in secoes:
        dados = secao['dados']
        if isinstance(dados, dict):
            total = sum(len(v) if isinstance(v, list) else 1 for v in dados.values())
        elif isinstance(dados, list):
            total = len(dados)
        else:
            total = 1
        partes.append(f"{secao['app']}:{total}")
    return '; '.join(partes) if partes else 'sem dados em outros módulos'


def formatar_em_linhas(dados, nivel=0):
    """
    Achata um dict/list de uma seção em linhas de texto simples, para o
    template do PDF (sem depender de filtro de template nenhum para
    estrutura arbitrária).
    """
    linhas = []
    indent = '  ' * nivel
    if isinstance(dados, dict):
        for chave, valor in dados.items():
            if isinstance(valor, (dict, list)):
                linhas.append(f'{indent}{chave}:')
                linhas.extend(formatar_em_linhas(valor, nivel + 1))
            else:
                linhas.append(f'{indent}{chave}: {valor}')
    elif isinstance(dados, list):
        for i, item in enumerate(dados, start=1):
            linhas.append(f'{indent}#{i}')
            linhas.extend(formatar_em_linhas(item, nivel + 1))
    else:
        linhas.append(f'{indent}{dados}')
    return linhas
