"""
agendamento/lgpd.py — Manutencao #66 [NUCLEO 5/5].

Seção do relatório LGPD referente aos compromissos do cliente já
cadastrado como titular. Fora de escopo desta fase: compromissos de
contato avulso sem `cliente` vinculado (`nome_contato`/`telefone_contato`/
`email_contato` da Manutencao #65) — débito técnico conhecido, registrado
na Especificacao_Hotfix.
"""


def exportar_titular(cliente):
    from .models import Compromisso

    compromissos = Compromisso.objects.filter(cliente=cliente).order_by('-inicio')
    if not compromissos.exists():
        return None

    return {
        'compromissos': [
            {
                'titulo': c.titulo,
                'inicio': c.inicio.isoformat() if c.inicio else None,
                'fim': c.fim.isoformat() if c.fim else None,
                'local': c.local,
                'status': c.get_status_display(),
            }
            for c in compromissos
        ]
    }
