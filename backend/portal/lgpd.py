"""
portal/lgpd.py — Manutencao #66 [NUCLEO 5/5].

Seção do relatório LGPD referente aos acessos do cliente ao Portal.
Expõe apenas e-mail do usuário vinculado (não o PK/FK cru do User —
RNF-04 da Especificacao_Hotfix).
"""


def exportar_titular(cliente):
    from .models import AcessoPortalCliente

    acessos = AcessoPortalCliente.objects.filter(cliente=cliente)
    if not acessos.exists():
        return None

    return {
        'acessos': [
            {
                'usuario_email': a.usuario.email if a.usuario else None,
                'ultimo_acesso': a.ultimo_acesso.isoformat() if a.ultimo_acesso else None,
            }
            for a in acessos
        ]
    }
