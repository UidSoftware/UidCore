"""
financeiro/lgpd.py — Manutencao #66 [NUCLEO 5/5].

Seção do relatório LGPD referente às receitas do cliente. Registro
financeiro/fiscal — exportado para o titular, mas NUNCA alterado pela
anonimização (RN-03: guarda legal, LGPD art. 16, I).
"""


def exportar_titular(cliente):
    from .models import Receita

    receitas = Receita.objects.filter(cliente=cliente).order_by('-created_at')
    if not receitas.exists():
        return None

    return {
        'receitas': [
            {
                'descricao': r.descricao,
                'valor_bruto': str(r.valor_bruto),
                'desconto': str(r.desconto),
                'valor_liquido': str(r.valor_liquido),
                'vencimento': r.vencimento.isoformat() if r.vencimento else None,
                'recebimento': r.recebimento.isoformat() if r.recebimento else None,
                'status': r.get_status_display(),
                'estornado': r.estornado,
            }
            for r in receitas
        ]
    }
