"""
portal/lgpd.py — Manutencao #66 [NUCLEO 5/5] + #72 (RF-07).

Seção do relatório LGPD referente aos acessos do cliente ao Portal.
Expõe apenas e-mail do usuário vinculado (não o PK/FK cru do User —
RNF-04 da Especificacao_Hotfix) e, desde a Manutencao #72, a foto_url do
usuário vinculado (mesma URL que ele veria no próprio /accounts/me/ —
RN-09, não gera link novo nem copia arquivo).
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
                'foto_url': (a.usuario.foto.url if (a.usuario and a.usuario.foto) else None),
                'ultimo_acesso': a.ultimo_acesso.isoformat() if a.ultimo_acesso else None,
            }
            for a in acessos
        ]
    }
