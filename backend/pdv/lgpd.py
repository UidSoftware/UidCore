"""
pdv/lgpd.py — Manutencao #66 [NUCLEO 5/5].

Seção do relatório LGPD referente às vendas de balcão (PDV) do cliente.
Registro financeiro/fiscal — exportado para o titular, mas NUNCA alterado
pela anonimização (RN-03: guarda legal, LGPD art. 16, I).
"""


def exportar_titular(cliente):
    from .models import Venda

    vendas = Venda.objects.filter(cliente=cliente).order_by('-data_hora')
    if not vendas.exists():
        return None

    return {
        'vendas': [
            {
                'numero': v.numero,
                'status': v.get_status_display(),
                'valor_total': str(v.valor_total),
                'data_hora': v.data_hora.isoformat() if v.data_hora else None,
                'itens': [
                    {
                        'produto': i.produto.nome,
                        'quantidade': str(i.quantidade),
                        'valor_unitario': str(i.valor_unitario),
                        'valor_total': str(i.valor_total),
                    }
                    for i in v.itens.all()
                ],
                'pagamentos': [
                    {
                        'metodo': p.metodo.get_nome_display() if p.metodo else None,
                        'valor': str(p.valor),
                    }
                    for p in v.pagamentos.all()
                ],
            }
            for v in vendas
        ]
    }
