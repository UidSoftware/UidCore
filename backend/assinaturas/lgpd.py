"""
assinaturas/lgpd.py — Manutencao #66 [NUCLEO 5/5].

Seção do relatório LGPD referente aos planos/assinaturas do cliente.
Registro financeiro/fiscal — exportado para o titular, mas NUNCA alterado
pela anonimização (RN-03: guarda legal, LGPD art. 16, I).
"""


def exportar_titular(cliente):
    from .models import Assinatura

    assinaturas = Assinatura.objects.filter(cliente=cliente).order_by('-created_at')
    if not assinaturas.exists():
        return None

    return {
        'assinaturas': [
            {
                'plano': a.plano.nome,
                'valor': str(a.valor),
                'periodicidade': a.plano.get_periodicidade_display(),
                'status': a.get_status_display(),
                'data_inicio': a.data_inicio.isoformat() if a.data_inicio else None,
                'data_fim': a.data_fim.isoformat() if a.data_fim else None,
            }
            for a in assinaturas
        ]
    }
