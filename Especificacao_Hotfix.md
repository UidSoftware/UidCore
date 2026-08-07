# Especificacao Hotfix — Manutencao #14 UidCore

Data: 2026-08-07
Sistema: UidCore
Modulo: Financeiro — Balanco Patrimonial (relatorios.py)
Tipo: bug (contabil)
Complexidade: baixa
Status do codigo: FIX JA DEPLOYADO (aplicado em commit 95e30b1, Manutencao #15, deploy 2026-08-05)

---

## Contexto

Complemento a Manutencao #13 (mesmo modulo, achado depois de #13 ja ter sido disparada).
O fix do codigo foi incluido no commit 95e30b1 (Manutencao #15 PDV), que aplicou os filtros
`referencia_mes__lte=mes_ref` em `calcular_balanco()`.

Esta Especificacao documenta formalmente o bug e registra os 6 testes (CA-M14-01 a CA-M14-06)
que cobrem os criterios de aceite da correcao.

---

## Descricao do Bug

`calcular_balanco()` em `backend/financeiro/relatorios.py` reconhecia Despesas e Receitas
com status PENDENTE/ATRASADO sem verificar se o compromisso ja era do mes corrente ou era
um compromisso futuro.

Consequencia: uma despesa recorrente cadastrada hoje com parcelas ate dezembro inflava
artificialmente o Passivo Circulante E reduzia lucros_acumulados do balanco de hoje —
assustandoo cliente com Runway/patrimonio liquido piores do que a realidade. Regime de
competencia de verdade so reconhece a obrigacao no mes em que o servico e prestado/consumido.

Exemplo concreto: assinar um contrato de aluguel ate dezembro com 5 parcelas futuras
cadastradas hoje mostrava R$15.000 em Contas a Pagar mesmo sendo agosto.

---

## Fix Aplicado (commit 95e30b1)

Em `calcular_balanco(data_ref)`:

```python
mes_ref = date(data_ref.year, data_ref.month, 1)

# Antes: sem filtro de mes
contas_a_receber = Receita.objects.filter(
    is_active=True, status__in=['PENDENTE', 'ATRASADO'],
).aggregate(...)

# Depois: so reconhece ate o mes de referencia
contas_a_receber = Receita.objects.filter(
    is_active=True, status__in=['PENDENTE', 'ATRASADO'],
    referencia_mes__lte=mes_ref,
).aggregate(...)
```

Mesmo filtro aplicado em:
- `contas_a_pagar` (Despesa PENDENTE/ATRASADO)
- `total_receitas` (lucros_acumulados — lado receita)
- `total_despesas` (lucros_acumulados — lado despesa)

`calcular_fluxo_projetado()` NAO foi alterado — usa vencimento dentro de janelas
de dias (0-30/31-60/61-90), pergunta diferente (quando o caixa sai/entra, nao
quando a obrigacao foi incorrida).

---

## Criterios de Aceite

| ID | Descricao | Resultado |
|----|-----------|-----------|
| CA-M14-01 | Despesa PENDENTE com referencia_mes 3 meses no futuro NAO aparece em contas_a_pagar do balanco atual | PASS |
| CA-M14-02 | Despesa PENDENTE com referencia_mes futuro NAO reduz lucros_acumulados do balanco atual | PASS |
| CA-M14-03 | A mesma Despesa PENDENTE aparece em contas_a_pagar quando calcular_balanco() e chamado com data_ref no mes de referencia dela | PASS |
| CA-M14-04 | Despesa PENDENTE com referencia_mes no mes atual AINDA aparece em contas_a_pagar (corte nao remove o presente) | PASS |
| CA-M14-05 | Receita PENDENTE com referencia_mes futuro NAO aparece em contas_a_receber do balanco atual | PASS |
| CA-M14-06 | equacao_ok permanece True com Despesa futura registrada (nao entra nem no passivo nem nos lucros_acumulados) | PASS |

---

## Testes

Classe: `BalancoReferenciaMesFuturoTest` em `backend/financeiro/tests.py`
Testes: 6 (CA-M14-01 a CA-M14-06)
Suite completa: 188/188 passando (0 falhas, 0 regressao)
