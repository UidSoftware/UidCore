"""
Services do app agendamento (Manutencao 92, RF-09).

Centraliza a contagem de ocupacao de um HorarioDisponivel numa data
especifica -- antes da Manutencao 92 essa logica estava duplicada em 4
lugares (perform_create, action ocupacao, view publica de disponibilidade
e CompromissoSerializer.get_vagas_restantes), o que e exatamente o tipo
de duplicacao que o CLAUDE.md global proibe pra calculo compartilhado
(mesmo principio do "_saldo_total_contas" do modulo financeiro: uma unica
funcao, reaproveitada por todo mundo que precisa do mesmo numero).
"""
from .models import StatusCompromisso


def contar_ocupacao(horario, data_horario, excluir_pk=None):
    """
    Retorna (ocupados, disponiveis) para um HorarioDisponivel numa data
    especifica. Nao usa select_for_update aqui (leitura) -- quem precisa
    de trava contra corrida (perform_create/perform_update) faz o
    select_for_update no HorarioDisponivel ANTES de chamar esta funcao,
    dentro do proprio transaction.atomic().

    excluir_pk: pk do Compromisso a excluir da contagem (RN-04) -- usado
    na edicao, para o proprio compromisso nao contar como ocupante do
    slot que ele mesmo ja ocupa.
    """
    from .models import Compromisso  # import local -- evita ciclo no modulo

    qs = Compromisso.objects.filter(
        horario=horario,
        data_horario=data_horario,
        is_active=True,
    ).exclude(status=StatusCompromisso.CANCELADO)
    if excluir_pk:
        qs = qs.exclude(pk=excluir_pk)
    ocupados = qs.count()
    disponiveis = max(0, horario.vagas - ocupados)
    return ocupados, disponiveis
