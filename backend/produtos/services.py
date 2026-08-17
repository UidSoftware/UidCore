"""
produtos/services.py — resolução de cadeia de conversão de unidade.

Manutenção #37 (UidCore): antes desta manutenção, cada `ConversaoUnidade`
tinha que carregar o fator já multiplicado até a unidade_base do produto
("1 CX = 300 UN" calculado de cabeça pelo usuário). Agora uma conversão
pode ser relativa a outra unidade já cadastrada (`converte_para`), formando
uma cadeia (ex.: 1 CX = 6 PT; 1 PT = 50 UN) — este módulo resolve essa
cadeia recursivamente até a unidade_base.

`fator_para_base()` substitui a lógica antes triplicada (e com fallback
1:1 silencioso — achado crítico RN-05) em:
  - produtos/models.py::EntradaEstoque.save()
  - pdv/services.py::_quantidade_base / _reverter_estoque
  - pdv/views.py::adicionar_item (cálculo de valor_unitario)

Erros são levantados como `django.core.exceptions.ValidationError` —
quem chama (view) é responsável por capturar e converter em HTTP 400
legível (RN-05/RN-01).
"""
from decimal import Decimal

from django.core.exceptions import ValidationError

PROFUNDIDADE_MAXIMA = 5  # RN-03


def _mapa_conversoes(produto, excluir_id=None):
    """Mapa {unidade: (quantidade_por_base, converte_para)} das conversões
    ativas do produto. `excluir_id` remove uma linha (usado ao validar uma
    edição — a versão em disco da linha editada não deve contar)."""
    from .models import ConversaoUnidade

    qs = ConversaoUnidade.objects.filter(produto=produto, is_active=True)
    if excluir_id is not None:
        qs = qs.exclude(pk=excluir_id)
    return {c.unidade: (c.quantidade_por_base, c.converte_para) for c in qs}


def _resolver_fator(unidade_base, mapa, unidade, _profundidade=0, _visitados=None):
    if unidade == unidade_base:
        return Decimal('1')

    if _visitados is None:
        _visitados = set()

    if unidade in _visitados:
        raise ValidationError(
            f'Conversão de unidade em ciclo detectada envolvendo "{unidade}".',
        )
    if _profundidade >= PROFUNDIDADE_MAXIMA:
        raise ValidationError(
            f'Cadeia de conversão de unidade excede o máximo de '
            f'{PROFUNDIDADE_MAXIMA} elos ao resolver "{unidade}".',
        )
    if unidade not in mapa:
        raise ValidationError(
            f'Conversão de unidade não cadastrada para "{unidade}".',
        )

    _visitados.add(unidade)
    quantidade_por_base, converte_para = mapa[unidade]
    proxima_unidade = converte_para or unidade_base
    fator_resto = _resolver_fator(
        unidade_base, mapa, proxima_unidade, _profundidade + 1, _visitados,
    )
    return quantidade_por_base * fator_resto


def fator_para_base(produto, unidade):
    """
    Resolve o fator de conversão de `unidade` para `produto.unidade_base`,
    percorrendo a cadeia de `ConversaoUnidade` cadastrada (RN-01), com
    limite de profundidade (RN-03) e detecção de ciclo.

    Levanta `ValidationError` (RN-05) se a unidade não tiver conversão
    cadastrada (direta ou em algum elo da cadeia) — nunca cai em fallback
    1:1 silencioso.
    """
    if unidade == produto.unidade_base:
        return Decimal('1')
    mapa = _mapa_conversoes(produto)
    return _resolver_fator(produto.unidade_base, mapa, unidade)


def validar_cadeia(produto, unidade, converte_para, quantidade_por_base, excluir_id=None):
    """
    Valida, ANTES de persistir, que uma ConversaoUnidade nova/editada
    resulta numa cadeia válida até a unidade_base (RN-01/RN-03) — usado no
    `validate()` do serializer. `excluir_id` é o pk da própria linha quando
    é uma edição (não deve contar a versão antiga dela no mapa).

    Retorna o fator composto até a base (útil para RF-04 se o backend
    quiser expor no futuro) ou levanta ValidationError.
    """
    mapa = _mapa_conversoes(produto, excluir_id=excluir_id)
    mapa[unidade] = (quantidade_por_base, converte_para or None)
    return _resolver_fator(produto.unidade_base, mapa, unidade)
