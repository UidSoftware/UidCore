"""
vendas/lgpd.py — Manutencao #66 [NUCLEO 5/5].

Seção do relatório LGPD referente a orçamentos e pedidos do cliente.
Registro financeiro/fiscal — exportado para o titular, mas NUNCA alterado
pela anonimização (RN-03: guarda legal, LGPD art. 16, I).
"""


def exportar_titular(cliente):
    from .models import Orcamento, Pedido

    orcamentos = Orcamento.objects.filter(cliente=cliente).order_by('-created_at')
    pedidos = Pedido.objects.filter(cliente=cliente).order_by('-created_at')

    if not orcamentos.exists() and not pedidos.exists():
        return None

    dados = {}

    if orcamentos.exists():
        dados['orcamentos'] = [
            {
                'numero': o.numero,
                'status': o.get_status_display(),
                'valor_total': str(o.valor_total),
                'validade': o.validade.isoformat() if o.validade else None,
                'itens': [
                    {
                        'descricao': i.descricao,
                        'quantidade': str(i.quantidade),
                        'valor_unitario': str(i.valor_unitario),
                        'valor_total': str(i.valor_total),
                    }
                    for i in o.itens.all()
                ],
            }
            for o in orcamentos
        ]

    if pedidos.exists():
        dados['pedidos'] = [
            {
                'numero': p.numero,
                'status': p.get_status_display(),
                'valor_total': str(p.valor_total),
                'data_pedido': p.data_pedido.isoformat() if p.data_pedido else None,
                'data_entrega_prevista': (
                    p.data_entrega_prevista.isoformat() if p.data_entrega_prevista else None
                ),
                'itens': [
                    {
                        'descricao': i.descricao,
                        'quantidade': str(i.quantidade),
                        'valor_unitario': str(i.valor_unitario),
                        'valor_total': str(i.valor_total),
                    }
                    for i in p.itens.all()
                ],
            }
            for p in pedidos
        ]

    return dados
