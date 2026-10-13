"""
clientes/lgpd.py — Manutencao #66 [NUCLEO 5/5].

Seção do relatório LGPD referente ao próprio cadastro do titular. Usa
apenas `objects` (nunca `all_objects`) — histórico/acionista soft-deletado
não entra na exportação (RF-02 da Especificacao_Hotfix).
"""


def exportar_titular(cliente):
    from .models import AcionistaCliente, HistoricoCliente

    historico = [
        {
            'descricao': h.descricao,
            'data': h.created_at.isoformat(),
        }
        for h in HistoricoCliente.objects.filter(cliente=cliente).order_by('-created_at')
    ]

    acionistas = [
        {
            'nome': a.nome,
            'email': a.email,
            'cpf': a.cpf,
            'telefone': a.telefone,
            'whatsapp': a.whatsapp,
            'principal': a.principal,
        }
        for a in AcionistaCliente.objects.filter(cliente=cliente).order_by('-principal', 'nome')
    ]

    dados = {
        'cadastro': {
            'tipo_pessoa': cliente.get_tipo_pessoa_display(),
            'documento': cliente.documento,
            'nome_razao_social': cliente.nome_razao_social,
            'telefone': cliente.telefone,
            'email': cliente.email,
            'endereco': cliente.endereco,
            'cidade': cliente.cidade,
            'estado': cliente.estado,
            'cep': cliente.cep,
            'segmento': cliente.get_segmento_display(),
            'data_nascimento': cliente.data_nascimento.isoformat() if cliente.data_nascimento else None,
            'origem': cliente.origem,
            'limite_credito': str(cliente.limite_credito),
            'observacoes': cliente.observacoes,
        },
    }
    if historico:
        dados['historico'] = historico
    if acionistas:
        dados['acionistas'] = acionistas
    return dados
