# Especificacao_Hotfix — Manutencao #13 — UidCore
**Data:** 2026-08-03
**Sistema:** UidCore (OS #7) — Template Financeiro Multi-Nicho
**Origem:** Diagnostico interno — 3 bugs contabeis em backend/financeiro/relatorios.py e views.py
**Agente produtor:** Analista (Modo Hotfix)
**Tipo:** `bug` — correcao contabil pura, sem alteracao de modelos, sem migration
**Requer aprovacao comercial:** nao

---

## 1. Contexto

O modulo financeiro do UidCore possui funcoes de relatorio em
`backend/financeiro/relatorios.py` e uma view de dashboard em
`backend/financeiro/views.py`. Foram identificados 3 bugs contabeis
independentes, todos relacionados ao tratamento de contas do tipo
`CARTEIRA` (cartao de credito) no calculo de saldo e balanco patrimonial.

Os tres bugs existem no codigo atual em producao. Nenhum deles exige
alteracao de model nem de migration — a correcao e puramente em logica
de calculo Python/ORM.

Referencia de modelo: `TipoConta.CARTEIRA = 'CARTEIRA'` em
`backend/financeiro/models.py` linha 13.

---

## 2. Diagnostico tecnico — os 3 bugs

### BUG 1 — `_saldo_total_contas()` inclui contas CARTEIRA

**Arquivo:** `backend/financeiro/relatorios.py`, linhas 9-19

**Codigo atual:**
```python
def _saldo_total_contas():
    saldo_inicial = Conta.objects.filter(is_active=True).aggregate(
        v=Sum('saldo_inicial')
    )['v'] or Decimal('0')
    agg = LivroCaixa.objects.filter(
        conta__is_active=True, estornado=False,
    ).aggregate(
        e=Sum('valor', filter=Q(tipo='ENTRADA')),
        s=Sum('valor', filter=Q(tipo='SAIDA')),
    )
    return saldo_inicial + (agg['e'] or Decimal('0')) - (agg['s'] or Decimal('0'))
```

**Problema:** a funcao soma TODAS as contas ativas sem excluir `tipo=CARTEIRA`.
Quando o cartao tem fatura em aberto, o saldo da conta CARTEIRA e negativo
(ex: -R$1.500). Esse valor negativo reduz o caixa disponivel reportado, como
se o dinheiro ja tivesse saido do banco — o que e errado. A divida do cartao
e um **Passivo Circulante**, nao uma reducao de Ativo disponivel. O dinheiro
no banco continua disponivel; o que existe e uma obrigacao futura de pagar a
fatura.

**Impacto:** afeta `calcular_indicadores_cfo()` (que chama `_saldo_total_contas()`
para calcular o runway) e `calcular_balanco()` (que tambem chama
`_saldo_total_contas()` para preencher `caixa_equivalentes`). Ambos reportam
caixa menor do que o real sempre que houver cartao com fatura pendente.

---

### BUG 2 — `calcular_balanco()` sem linha de Passivo para divida de cartao

**Arquivo:** `backend/financeiro/relatorios.py`, linhas 83-160

**Problema:** mesmo apos corrigir o BUG 1 (excluir CARTEIRA de
`_saldo_total_contas()`), a divida do cartao desaparece completamente do
balanco. Ela nao aparece como Ativo (correto apos BUG 1) e tambem nao
aparece como Passivo — simplesmente some.

Isso quebra a equacao contabil fundamental:

```
Ativo = Passivo + Patrimonio Liquido
```

Exemplo concreto com os tres bugs:
- Banco: R$5.000 (conta CORRENTE)
- Cartao: -R$1.500 (conta CARTEIRA, fatura em aberto)
- Despesas PENDENTE: R$800
- Aportes: R$10.000
- Lucros acumulados: R$3.700

**Balanco ERRADO (codigo atual):**
```
Ativo Circulante:
  Caixa e equivalentes: R$3.500  <- banco + cartao (-1.500) somados
  Contas a receber:     R$0
  Total Ativo:          R$3.500

Passivo Circulante:
  Contas a pagar:       R$800
  Total Passivo:        R$800

PL:
  Aportes:              R$10.000
  Lucros acumulados:    R$3.700
  Total PL:             R$13.700

Total Passivo + PL:     R$14.500
equacao_ok: FALSE  <- 3.500 != 14.500
```

**Balanco CORRETO (apos correcao de BUG 1 + BUG 2):**
```
Ativo Circulante:
  Caixa e equivalentes: R$5.000  <- so banco, sem cartao
  Contas a receber:     R$0
  Total Ativo:          R$5.000

Passivo Circulante:
  Contas a pagar:       R$800
  Cartao a pagar:       R$1.500  <- divida do cartao como passivo
  Total Passivo:        R$2.300

PL:
  Aportes:              R$10.000
  Lucros acumulados:    R$2.700  <- resultado reflete despesas reais
  Total PL:             R$12.700

Total Passivo + PL:     R$15.000
equacao_ok: FALSE  <- ainda nao fecha porque PL usa regime de competencia
```

Nota: a equacao `Ativo = Passivo + PL` pode nao fechar perfeitamente
dependendo do regime contabil de cada elemento. O que importa e que o
cartao nao desapareca — ele deve aparecer em Passivo Circulante como
`cartao_credito_a_pagar`.

---

### BUG 3 — `dashboard_financeiro()` calcula saldo_total inline duplicado

**Arquivo:** `backend/financeiro/views.py`, linhas 550-559

**Codigo atual:**
```python
saldo_total = Conta.objects.filter(is_active=True).aggregate(
    v=Sum('saldo_inicial')
)['v'] or Decimal('0')
agg_saldo = LivroCaixa.objects.filter(
    conta__is_active=True, estornado=False,
).aggregate(
    e=Sum('valor', filter=Q(tipo='ENTRADA')),
    s=Sum('valor', filter=Q(tipo='SAIDA')),
)
saldo_total += (agg_saldo['e'] or Decimal('0')) - (agg_saldo['s'] or Decimal('0'))
```

**Problema duplo:**
1. Replica manualmente a logica de `_saldo_total_contas()`, criando
   divergencia potencial de manutencao (se alguem corrigir `_saldo_total_contas()`
   sem lembrar de corrigir esse bloco, o dashboard mostra valor diferente).
2. Inclui o BUG 1: nao exclui `tipo=CARTEIRA`, entao o saldo_total do
   dashboard e errado quando ha cartao com fatura em aberto.

Alem disso, o `saldo_total` calculado inline nunca e retornado na resposta da
view (a view retorna `indicadores['saldo_total']` via `calcular_indicadores_cfo()`).
O bloco e codigo morto com bug embutido.

---

## 3. Requisitos Funcionais

**RF01 — Excluir CARTEIRA de `_saldo_total_contas()`**
A funcao deve filtrar apenas contas cujo `tipo != 'CARTEIRA'` ao calcular
caixa e equivalentes. Contas CARTEIRA representam passivo, nao ativo disponivel.

**RF02 — Criar funcao auxiliar `_divida_cartao_credito()`**
Nova funcao em `relatorios.py` que soma o saldo negativo das contas CARTEIRA
ativas e retorna como valor positivo (= valor da divida). Retorna `Decimal('0')`
quando nao ha conta CARTEIRA ativa ou quando todas tem saldo zero ou positivo.

**RF03 — Adicionar linha de Passivo Circulante em `calcular_balanco()`**
`calcular_balanco()` deve chamar `_divida_cartao_credito()` e incluir o
resultado em `passivo.circulante` como `cartao_credito_a_pagar`. O
`passivo_total` deve incluir esse valor.

**RF04 — Remover bloco inline de saldo em `dashboard_financeiro()`**
O bloco manual de calculo de saldo (linhas 550-559 de views.py) deve ser
removido. O `saldo_total` do dashboard ja vem de `calcular_indicadores_cfo()`
via `indicadores['saldo_total']`, que por sua vez usa `_saldo_total_contas()`.
Nao ha nada para substituir — o bloco e removido sem substituicao (e codigo morto).

---

## 4. Requisitos Nao Funcionais

**RNF01 — Zero migrations**
Os 3 bugs sao de logica de calculo. Nenhuma alteracao de model e necessaria.
O Forge nao deve gerar nem aplicar nenhuma migration.

**RNF02 — Backward compatibility**
A assinatura e o retorno de `_saldo_total_contas()` e `calcular_balanco()`
devem permanecer compatíveis com todos os callers existentes. Apenas os
VALORES retornados mudam (correcao dos numeros errados).

**RNF03 — `calcular_balanco()` deve incluir `cartao_credito_a_pagar` no dict retornado**
O campo deve aparecer em `passivo.circulante` mesmo quando seu valor for zero
(para o frontend nao quebrar ao tentar acessar a chave).

**RNF04 — Nao alterar frontend**
Essa manutencao e puramente de backend. O frontend nao deve ser alterado.
Se o Loom for invocado, deve confirmar que nenhuma alteracao e necessaria e
encerrar.

---

## 5. Spec backend detalhada — o que Forge deve implementar

### 5.1 `_saldo_total_contas()` — adicionar `.exclude(tipo='CARTEIRA')`

```python
# ANTES (bugado)
def _saldo_total_contas():
    saldo_inicial = Conta.objects.filter(is_active=True).aggregate(
        v=Sum('saldo_inicial')
    )['v'] or Decimal('0')
    agg = LivroCaixa.objects.filter(
        conta__is_active=True, estornado=False,
    ).aggregate(
        e=Sum('valor', filter=Q(tipo='ENTRADA')),
        s=Sum('valor', filter=Q(tipo='SAIDA')),
    )
    return saldo_inicial + (agg['e'] or Decimal('0')) - (agg['s'] or Decimal('0'))

# DEPOIS (correto)
def _saldo_total_contas():
    saldo_inicial = Conta.objects.filter(
        is_active=True,
    ).exclude(tipo='CARTEIRA').aggregate(
        v=Sum('saldo_inicial')
    )['v'] or Decimal('0')
    agg = LivroCaixa.objects.filter(
        conta__is_active=True, estornado=False,
    ).exclude(conta__tipo='CARTEIRA').aggregate(
        e=Sum('valor', filter=Q(tipo='ENTRADA')),
        s=Sum('valor', filter=Q(tipo='SAIDA')),
    )
    return saldo_inicial + (agg['e'] or Decimal('0')) - (agg['s'] or Decimal('0'))
```

### 5.2 Nova funcao `_divida_cartao_credito()` — inserir logo apos `_saldo_total_contas()`

A divida e calculada diretamente pelo saldo calculado: `saldo_inicial` da conta
CARTEIRA mais os movimentos de LivroCaixa dela. Se esse valor for negativo,
retorna o modulo como positivo (= valor da divida). Se for zero ou positivo
(cartao quitado ou sem fatura), retorna `Decimal('0')`.

```python
def _divida_cartao_credito():
    """
    Soma o saldo liquido de todas as contas CARTEIRA ativas.
    Se o saldo for negativo (fatura em aberto), retorna o valor
    absoluto como positivo (= valor da divida, Passivo Circulante).
    Retorna Decimal('0') se nao ha cartao ativo ou o saldo e >= 0.
    """
    saldo_inicial = Conta.objects.filter(
        is_active=True, tipo='CARTEIRA',
    ).aggregate(v=Sum('saldo_inicial'))['v'] or Decimal('0')

    agg = LivroCaixa.objects.filter(
        conta__is_active=True, conta__tipo='CARTEIRA', estornado=False,
    ).aggregate(
        e=Sum('valor', filter=Q(tipo='ENTRADA')),
        s=Sum('valor', filter=Q(tipo='SAIDA')),
    )
    saldo_cartao = saldo_inicial + (agg['e'] or Decimal('0')) - (agg['s'] or Decimal('0'))

    # Divida = saldo negativo convertido em positivo
    return abs(saldo_cartao) if saldo_cartao < Decimal('0') else Decimal('0')
```

### 5.3 `calcular_balanco()` — adicionar `cartao_credito_a_pagar` em passivo.circulante

Localizar o bloco de `passivo_circulante` em `calcular_balanco()` e inserir
a chamada a `_divida_cartao_credito()`:

```python
# ANTES
passivo_circulante = contas_a_pagar
passivo_exigivel_lp = emprestimos
passivo_total = passivo_circulante + passivo_exigivel_lp

# DEPOIS
divida_cartao = _divida_cartao_credito()
passivo_circulante = contas_a_pagar + divida_cartao
passivo_exigivel_lp = emprestimos
passivo_total = passivo_circulante + passivo_exigivel_lp
```

E no dict retornado, dentro de `'passivo': {'circulante': {...}}`:

```python
# ANTES
'circulante': {
    'contas_a_pagar': contas_a_pagar,
    'total': passivo_circulante,
},

# DEPOIS
'circulante': {
    'contas_a_pagar': contas_a_pagar,
    'cartao_credito_a_pagar': divida_cartao,
    'total': passivo_circulante,
},
```

### 5.4 `dashboard_financeiro()` — remover bloco de saldo inline (linhas 550-559)

Remover inteiramente as 10 linhas do bloco manual de calculo de saldo:

```python
# REMOVER este bloco inteiro (codigo morto com bug):
saldo_total = Conta.objects.filter(is_active=True).aggregate(
    v=Sum('saldo_inicial')
)['v'] or Decimal('0')
agg_saldo = LivroCaixa.objects.filter(
    conta__is_active=True, estornado=False,
).aggregate(
    e=Sum('valor', filter=Q(tipo='ENTRADA')),
    s=Sum('valor', filter=Q(tipo='SAIDA')),
)
saldo_total += (agg_saldo['e'] or Decimal('0')) - (agg_saldo['s'] or Decimal('0'))
```

O saldo que o dashboard retorna vem de `indicadores['saldo_total']`
(calculado por `calcular_indicadores_cfo()` → `_saldo_total_contas()`),
que ja estara correto apos a correcao do BUG 1. Nao ha substituicao necessaria.

---

## 6. Arquivos a alterar

| Arquivo | Mudanca |
|---|---|
| `backend/financeiro/relatorios.py` | BUG 1: exclude CARTEIRA em `_saldo_total_contas()` |
| `backend/financeiro/relatorios.py` | BUG 2: nova funcao `_divida_cartao_credito()` |
| `backend/financeiro/relatorios.py` | BUG 2: `calcular_balanco()` usa `_divida_cartao_credito()` |
| `backend/financeiro/views.py` | BUG 3: remover bloco saldo inline linhas 550-559 |

**Nao alterar:** models.py, serializers.py, urls.py, migrations/, frontend/

---

## 7. Testes existentes a verificar

Antes de escrever testes novos, o Forge deve confirmar se ja existem testes
para `_saldo_total_contas()`, `calcular_balanco()` e `dashboard_financeiro()`
no suite atual. Localizar em:

```
backend/financeiro/tests/
```

Se existirem testes que criam contas e verificam saldo/balanco, eles podem
estar passando com o comportamento errado (afinal, o bug esta em producao).
Esses testes devem ser **atualizados** para refletir o comportamento correto
apos a correcao.

---

## 8. Criterios de Aceite (para o Sentinel)

### CA-01 — `_saldo_total_contas()` exclui CARTEIRA

Cenario: criar uma conta CORRENTE com saldo_inicial=R$5.000 e uma conta
CARTEIRA com saldo_inicial=R$0 mais lancamentos de SAIDA=R$1.500 no LivroCaixa
(fatura em aberto, saldo efetivo = -R$1.500).

Resultado esperado de `_saldo_total_contas()`: `Decimal('5000.00')`
Resultado errado (codigo atual): `Decimal('3500.00')`

### CA-02 — `_divida_cartao_credito()` retorna valor absoluto da divida

Mesmo cenario do CA-01.

Resultado esperado de `_divida_cartao_credito()`: `Decimal('1500.00')`
Resultado quando cartao quitado (saldo=0): `Decimal('0')`
Resultado quando cartao sem fatura (saldo positivo): `Decimal('0')`

### CA-03 — `calcular_balanco()` inclui `cartao_credito_a_pagar` em passivo.circulante

Mesmo cenario do CA-01.

```python
balanco = calcular_balanco()
assert balanco['passivo']['circulante']['cartao_credito_a_pagar'] == Decimal('1500.00')
assert balanco['passivo']['circulante']['total'] >= Decimal('1500.00')
assert balanco['ativo']['circulante']['caixa_equivalentes'] == Decimal('5000.00')
```

### CA-04 — `calcular_balanco()` com cartao zerado retorna `cartao_credito_a_pagar` = 0

Cenario: nenhuma conta CARTEIRA, ou conta CARTEIRA com saldo zero.

```python
balanco = calcular_balanco()
# Chave deve existir mesmo com valor zero (frontend nao quebra)
assert 'cartao_credito_a_pagar' in balanco['passivo']['circulante']
assert balanco['passivo']['circulante']['cartao_credito_a_pagar'] == Decimal('0')
```

### CA-05 — `calcular_indicadores_cfo()` retorna `saldo_total` sem cartao

Mesmo cenario do CA-01.

```python
indicadores = calcular_indicadores_cfo()
assert indicadores['saldo_total'] == Decimal('5000.00')  # so banco, sem cartao
```

### CA-06 — `dashboard_financeiro()` nao tem bloco de saldo duplicado

Verificacao estatica: ler `backend/financeiro/views.py` e confirmar que
**nao existe** nenhum bloco do tipo:

```python
saldo_total = Conta.objects.filter(is_active=True).aggregate(...)
```

dentro da funcao `dashboard_financeiro()`.

### CA-07 — Endpoint `/api/v1/financeiro/dashboard/` retorna HTTP 200

Cenario: container de teste rodando, usuario autenticado.
O endpoint deve retornar HTTP 200 e o campo `indicadores.saldo_total` deve
ser igual ao valor de `_saldo_total_contas()` (sem cartao).

### CA-08 — Suite completa de testes Django passa sem falhas

```bash
# No container de teste isolado (docker compose -p uidcore-test)
docker exec uidcore-test-backend-1 python manage.py test --verbosity=2
```

Resultado esperado: 0 falhas, 0 erros.

---

## 9. Instrucoes para o Sentinel — como testar com conta CARTEIRA real

O Sentinel deve criar dados de teste via shell do Django ou via fixtures
para validar os CAs acima com valores reais. Roteiro sugerido:

```bash
# Abrir shell no container de teste
docker exec -it uidcore-test-backend-1 python manage.py shell

# Criar conta bancaria e conta cartao
from financeiro.models import Conta, LivroCaixa
from decimal import Decimal
from datetime import date

banco = Conta.objects.create(
    nome='Banco Teste',
    tipo='CORRENTE',
    saldo_inicial=Decimal('5000.00'),
)
cartao = Conta.objects.create(
    nome='Cartao Teste',
    tipo='CARTEIRA',
    saldo_inicial=Decimal('0'),
)

# Simular fatura em aberto: compra de R$1.500 no cartao
LivroCaixa.objects.create(
    conta=cartao,
    tipo='SAIDA',
    valor=Decimal('1500.00'),
    descricao='Compra no cartao',
    data=date.today(),
    estornado=False,
)

# Verificar resultado correto
from financeiro.relatorios import _saldo_total_contas, _divida_cartao_credito, calcular_balanco

saldo = _saldo_total_contas()
divida = _divida_cartao_credito()
balanco = calcular_balanco()

print('saldo_total_contas:', saldo)          # esperado: 5000.00
print('divida_cartao:', divida)              # esperado: 1500.00
print('cartao_a_pagar:', balanco['passivo']['circulante']['cartao_credito_a_pagar'])  # esperado: 1500.00
print('caixa_equivalentes:', balanco['ativo']['circulante']['caixa_equivalentes'])   # esperado: 5000.00
```

O Sentinel deve executar esse roteiro no container de teste e registrar
os valores reais obtidos no relatorio de aprovacao/reprovacao.

---

## 10. Observacoes tecnicas

**Por que CARTEIRA e Passivo e nao Ativo:**
O modelo de cartao de credito como conta CARTEIRA foi documentado no CLAUDE.md
do projeto (secao "Padroes financeiros herdados do SystemD"). O cartao e um
instrumento de pagamento diferido — o dinheiro de verdade continua no banco
ate o dia do pagamento da fatura. Antes disso, existe uma obrigacao (Passivo),
nao uma reducao de disponivel (Ativo).

**Por que o BUG 3 e codigo morto:**
A variavel `saldo_total` calculada inline em `dashboard_financeiro()` nao e
usada em nenhum lugar apos o calculo — a view retorna `indicadores['saldo_total']`
que vem de `calcular_indicadores_cfo()`. O bloco e vestigio de uma versao
anterior do dashboard e pode ser removido sem consequencia alguma para a
resposta da API.

**Quanto a `equacao_ok` em `calcular_balanco()`:**
Apos a correcao, `equacao_ok` pode continuar nao fechando em alguns cenarios
(ex: quando `lucros_acumulados` usa regime de competencia e os demais elementos
usam regime misto). Esse e um limitador contabil preexistente, nao introduzido
por esta manutencao. O campo `equacao_ok` deve ser mantido como esta — o
objetivo desta manutencao e somente garantir que o cartao aparece nos lugares
certos (excluido do Ativo, incluido no Passivo), nao reescrever a logica de
fechamento de balanco.

---

## 11. Scope e o que nao fazer

**Fora do escopo desta manutencao:**
- Alteracao de models ou migrations
- Correcao do calculo de `lucros_acumulados` em `calcular_balanco()`
- Alteracao de qualquer endpoint alem de `dashboard_financeiro`
- Alteracao do frontend
- Alteracao de `calcular_dre_mes()` ou `calcular_fluxo_projetado()`
- Refatoracao geral do modulo financeiro

**Forge deve encerrar apos alterar exatamente 2 arquivos:**
1. `backend/financeiro/relatorios.py` (BUG 1 + BUG 2)
2. `backend/financeiro/views.py` (BUG 3)

---

## 12. Resumo executivo para o Planner

| Item | Detalhe |
|---|---|
| Tipo | bug — 3 bugs contabeis independentes |
| Arquivos alterados | 2 (relatorios.py + views.py) |
| Migrations | nenhuma |
| Frontend | nenhuma alteracao |
| Risco | baixo — correcao de calculo, sem mudanca de interface |
| Bloqueante em producao | nao — os valores estao errados, mas o sistema funciona |
| Prioridade sugerida | alta — dados financeiros errados impactam decisoes do cliente |
