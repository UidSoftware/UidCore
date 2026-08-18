# Especificação — Manutenção #40
**Elaborado por:** Analista (MODO HOTFIX)
**Data:** 2026-08-18
**Sistema:** UidCore (OS #7)
**Solicitação original (verbatim, resumida):**
"BUG confirmado em `frontend/src/pages/Produtos.jsx` (~linha 540): o array
`converteParaOptions` de cada linha de `ConversaoUnidade` só oferece como destino
unidades que já existem em outra linha do estado local. Depende da ORDEM de criação
das linhas. Cenário que falha: 1 CX = 6 PT, 1 PT = 50 UN (base=UN). Usuário cria linha
CX primeiro, mas PT não aparece como opção de destino porque ainda não tem linha PT
criada — só aparece UN (base). Fix: `converteParaOptions` deve oferecer TODAS as
unidades de `UNIDADE_OPTIONS` exceto a própria unidade da linha." Escopo definido pelo
solicitante: Produtos.jsx (formulário de cadastro/edição) e backend `produtos/` se
tiver restrição similar. Não mexer em `FrenteDeCaixa.jsx`.

---

## Classificação

```
tipo: bug
sistema: UidCore
caminho_afetado: frontend/src/pages/Produtos.jsx
                 - converteParaOptions (linhas ~544-550)
                 - handleSubmit (linhas ~211-268)
                 backend/produtos/ (apenas leitura/confirmação — ver RN-04, sem alteração de código)
complexidade: baixa
requer_aprovacao_comercial: false
```

---

## Diagnóstico confirmado (leitura direta dos arquivos — não do pedido)

### Causa raiz relatada — dropdown depende da ordem local (confirmada)

`Produtos.jsx` linhas 544-550 hoje:

```js
const converteParaOptions = [
  { value: unidadeBase, label: `${unidadeLabel(unidadeBase)} (base)` },
  ...conversoes
    .filter((c, i) => i !== idx && c.unidade && c.unidade !== unidadeBase)
    .map((c) => ({ value: c.unidade, label: unidadeLabel(c.unidade) }))
    .filter((opt, i, arr) => arr.findIndex((o) => o.value === opt.value) === i),
]
```

Confirma exatamente o relatado: a lista de opções é montada a partir de `conversoes`
(estado local das OUTRAS linhas já criadas na tela), não a partir de `UNIDADE_OPTIONS`
(o catálogo fixo de 6 unidades definido no topo do arquivo, linha 14). Resultado: no
cenário do pedido (criar CX antes de PT), a linha CX só vê "UN (base)" como destino —
PT não aparece porque sua linha ainda não existe no array `conversoes` no momento em
que a linha CX é renderizada.

### Achado adicional do Analista — o mesmo problema de ORDEM existe no salvamento, não só no dropdown

Rastreando o fluxo completo (o pedido só mencionou o Select, mas pediu para verificar
"backend/produtos/ se tiver restrição similar" — havia, só que não é bug de backend,
é o handshake frontend↔backend):

`handleSubmit` (linhas 225-260) salva as conversões num loop sequencial, **na ordem em
que aparecem no array `conversoes`** (ordem de criação na tela):

```js
for (const conv of conversoes) {
  ...
  if (conv.id) {
    await api.patch(`/produtos/${produtoId}/conversoes/${conv.id}/`, payload)
  } else {
    await api.post(`/produtos/${produtoId}/conversoes/`, payload)
  }
}
```

Cada linha é um POST/PATCH HTTP **independente**. O backend (`produtos/serializers.py`
→ `ConversaoUnidadeSerializer.validate()` → `produtos/services.py::validar_cadeia`)
exige que a unidade apontada em `converte_para` **já exista como `ConversaoUnidade`
ativa persistida no banco no momento exato do POST** — ele não enxerga outras linhas
que ainda estão "no ar" na mesma leva de salvamento do formulário:

```python
# produtos/services.py::_resolver_fator
if unidade not in mapa:
    raise ValidationError(
        f'Conversão de unidade não cadastrada para "{unidade}".',
    )
```

Isso é **confirmado pelo próprio teste já existente** do backend,
`backend/produtos/tests.py::test_criar_conversao_cadeia_via_api` (linha 189): o teste
só passa porque cria **PT primeiro, depois CX** apontando pra PT. Se a ordem fosse
invertida (CX primeiro, como no cenário exato do pedido), o segundo POST falharia com
400 `{"unidade": ["Conversão de unidade não cadastrada para \"PT\"."]}`.

**Consequência prática:** corrigir só o Select (RF-01) resolve o sintoma visual
("PT não aparece como opção"), mas o cenário completo do pedido — usuário cria CX
primeiro, escolhe PT como destino, clica Salvar — **continuaria quebrando no submit**,
trocando um bug silencioso (opção não aparece) por um erro 400 confuso que o usuário
não tem como autodiagnosticar. Por isso este documento inclui RF-02, que não estava
no pedido original mas é necessário para o comportamento pedido funcionar de ponta a
ponta.

**Backend não tem bug.** `validar_cadeia`/`fator_para_base` leem corretamente o estado
já persistido no banco no momento da chamada (`_mapa_conversoes`), de forma agnóstica
à ordem histórica de criação — uma vez que PT e CX estejam ambas salvas, a resolução
da cadeia funciona em qualquer direção de consulta. A restrição existe (unidade
referenciada precisa existir no banco *no momento do POST*), é o comportamento correto
e intencional (RN-01/RN-03/RN-05 do backend, documentados em `produtos/services.py`) —
o ajuste necessário é inteiramente do lado do frontend, na ordem das chamadas HTTP que
ele dispara (RF-02). Ver RN-04.

---

## Requisitos Funcionais

**RF-01 (bug relatado no pedido).** `converteParaOptions` deve oferecer TODAS as
unidades de `UNIDADE_OPTIONS`, exceto a própria unidade da linha (`conv.unidade`) e a
unidade base do produto (que já entra separadamente como opção "(base)", primeira da
lista) — independente de já existir outra linha para aquela unidade no estado local
`conversoes`.
- Critério de exclusão passa a ser `unidade !== unidadeBase && unidade !== conv.unidade`
  sobre o catálogo fixo `UNIDADE_OPTIONS`, não mais um filtro sobre `conversoes`.
- Deduplicação por `value` deixa de ser necessária (o catálogo `UNIDADE_OPTIONS` já não
  tem duplicata).

**RF-02 (achado do Analista — necessário para o cenário do pedido não quebrar no
submit).** `handleSubmit` deve persistir as linhas de `conversoes` em **ordem de
dependência (topológica)**, não na ordem em que aparecem no array/tela: toda linha
cujo `converte_para` aponta para outra unidade que também é uma linha nova (sem `id`
ainda, ou seja, ainda não salva no banco) precisa ser salva **depois** da unidade
referenciada.
- Construir um grafo local `{unidade → converte_para}` a partir de `conversoes` e
  ordenar topologicamente antes do `for (const conv of conversoes)` atual.
- Se o grafo tiver ciclo (ex.: linha CX aponta para PT e linha PT aponta para CX) →
  **não iniciar nenhuma chamada POST/PATCH de conversões**; mostrar um toast de erro
  identificando o ciclo (ex.: `"Conversões em ciclo: CX → PT → CX. Corrija antes de
  salvar."`) e interromper apenas a seção de conversões do submit (ver RN-03 sobre o
  produto em si).
- Isso fecha, de fato, o cenário relatado no pedido: criar CX primeiro, apontar para
  PT (agora possível pelo RF-01), criar PT depois — ao salvar, PT é persistida antes de
  CX independentemente da ordem de criação na tela.

**RF-03 (preservação de comportamento existente).** O aviso por linha já existente
("⚠ conversao nao fecha na unidade base", renderizado quando `resolverFatorBase`
retorna `ok: false`, linha ~613) continua aparecendo durante a edição exatamente como
hoje — é só um preview client-side, não precisa mudar; só passa a fazer sentido em mais
casos porque agora dá pra escolher qualquer unidade como destino antes dela existir.

---

## Regras de Negócio (RN)

**RN-01.** A opção "(base)" (`unidadeBase` do produto) nunca é oferecida como destino
igual à própria linha — `conv.unidade` é sempre excluída da lista de opções, mesmo no
caso trivial em que `conv.unidade === unidadeBase` (não deveria ocorrer na prática, mas
a exclusão cobre o caso sem necessidade de tratamento especial).

**RN-02.** `converteParaOptions` não depende mais de quais linhas já foram criadas em
`conversoes` — depende só do catálogo fixo `UNIDADE_OPTIONS` menos a unidade da própria
linha. Isso é o que elimina a dependência de ordem descrita no pedido.

**RN-03.** Se a ordenação topológica (RF-02) detectar ciclo, os dados principais do
produto (nome, preço, estoque etc.) — já salvos pelo POST/PATCH que roda ANTES do loop
de conversões, linhas 217-224 — não são desfeitos. Mesmo comportamento de hoje quando
uma linha individual de conversão falha (linhas 249-257 do `handleSubmit` atual: erro
por-linha vira toast, sem reverter o produto). O toast de erro do ciclo deve deixar
claro que o produto foi salvo mas as conversões, não.

**RN-04 (confirmação — não gera mudança de código).** `backend/produtos/services.py`
(`validar_cadeia`, `fator_para_base`) e `backend/produtos/serializers.py`
(`ConversaoUnidadeSerializer.validate`) já funcionam corretamente e não têm bug —
exigem, corretamente, que a unidade referenciada em `converte_para` já esteja
persistida no banco no momento do POST/PATCH daquela linha. Essa é a "restrição
similar" mencionada no pedido: existe, mas do lado do backend ela é o comportamento
certo (é exatamente o que impede uma conversão referenciar algo que não existe).
Confirmado por `backend/produtos/tests.py::test_criar_conversao_cadeia_via_api`
(linha 189, cria PT antes de CX) e `test_criar_conversao_ciclo_rejeitada_400`
(linha 205). **Nenhuma alteração em `backend/produtos/` é necessária** — a correção
fica inteiramente em RF-02 (ordem das chamadas feitas pelo frontend).

---

## Telas afetadas

`Produtos.jsx` — Modal de cadastro/edição de produto, seção "Conversões de Unidade"
(linhas ~522-622) e função `handleSubmit` (linhas ~211-268). Nenhuma mudança visual
nova: o Select "Converte para" passa a listar mais opções (todas as unidades exceto a
própria), em vez de só as que já têm linha criada. Nenhuma mudança em
`FrenteDeCaixa.jsx`, conforme instrução explícita do pedido.

---

## Especificação técnica

### Frontend — RF-01 (linhas ~544-550 de `Produtos.jsx`)

Trocar:
```js
const converteParaOptions = [
  { value: unidadeBase, label: `${unidadeLabel(unidadeBase)} (base)` },
  ...conversoes
    .filter((c, i) => i !== idx && c.unidade && c.unidade !== unidadeBase)
    .map((c) => ({ value: c.unidade, label: unidadeLabel(c.unidade) }))
    .filter((opt, i, arr) => arr.findIndex((o) => o.value === opt.value) === i),
]
```
Por:
```js
const converteParaOptions = [
  { value: unidadeBase, label: `${unidadeLabel(unidadeBase)} (base)` },
  ...UNIDADE_OPTIONS
    .filter((u) => u.value !== unidadeBase && u.value !== conv.unidade)
    .map((u) => ({ value: u.value, label: u.label })),
]
```

### Frontend — RF-02 (`handleSubmit`, linhas ~225-260)

Adicionar uma função de ordenação topológica com detecção de ciclo (pode ficar junto
das outras funções utilitárias do topo do arquivo, perto de `resolverFatorBase`):

```js
function ordenarConversoesPorDependencia(lista) {
  const porUnidade = new Map(lista.map((c) => [c.unidade, c]))
  const estado = new Map() // unidade -> 'visitando' | 'pronto'
  const ordenado = []

  function visitar(unidade, caminho) {
    if (!porUnidade.has(unidade)) return // referencia unidade_base ou linha inexistente
    if (estado.get(unidade) === 'pronto') return
    if (estado.get(unidade) === 'visitando') {
      throw new Error(`Conversões em ciclo: ${[...caminho, unidade].join(' → ')}. Corrija antes de salvar.`)
    }
    estado.set(unidade, 'visitando')
    const conv = porUnidade.get(unidade)
    if (conv.converte_para) visitar(conv.converte_para, [...caminho, unidade])
    estado.set(unidade, 'pronto')
    ordenado.push(conv)
  }

  for (const conv of lista) {
    if (conv.unidade) visitar(conv.unidade, [])
  }
  return ordenado
}
```

No `handleSubmit`, envolver a montagem da lista a salvar:

```js
if (produtoId) {
  let conversoesOrdenadas
  try {
    conversoesOrdenadas = ordenarConversoesPorDependencia(
      conversoes.filter((c) => c.unidade && c.quantidade_por_base),
    )
  } catch (error) {
    showToast(error.message, 'error')
    closeModal()
    fetchProdutos()
    return
  }
  for (const conv of conversoesOrdenadas) {
    // ... corpo do loop igual ao atual (POST novas / PATCH alteradas)
  }
}
```

(Ajustar `closeModal()`/`fetchProdutos()` conforme RN-03 — produto já foi salvo antes
deste bloco, então a lista deve refletir isso mesmo se as conversões não salvarem.)

### Backend — RN-04

Nenhuma alteração de código em `backend/produtos/`. Rodar a suíte existente
(`backend/produtos/tests.py`) sem modificação para confirmar que nada regride.

---

## Fora do escopo

```
- FrenteDeCaixa.jsx — não tocar, conforme instrução explícita do pedido.
- backend/produtos/ — nenhuma alteração de código (RN-04); apenas confirmação via
  suíte de testes já existente de que o comportamento atual está correto.
- Qualquer reformulação visual do formulário de conversões além da lista de opções
  do Select "Converte para".
- Suporte a mais de 5 elos de cadeia (PROFUNDIDADE_MAXIMA já definida no backend,
  fora do escopo desta manutenção).
- Endpoint de criação em lote (bulk) de conversões — a correção ficou inteiramente
  no reordenamento do loop sequencial já existente no frontend, sem precisar de
  mudança de contrato de API.
```

---

## Critérios de Aceite (CA)

```
CA-01 - Produto com unidade_base=UN. Criar linha CX primeiro (sem PT ainda cadastrada)
        → Select "Converte para" da linha CX mostra UN (base), PT, KG, L, M — todas as
        unidades exceto a própria CX. PT aparece mesmo sem ter linha própria criada.
CA-02 - Selecionar CX → converte_para=PT, quantidade_por_base=6. Adicionar segunda
        linha PT → converte_para=UN (base), quantidade_por_base=50. Salvar o form.
CA-03 - Após CA-02, GET /produtos/{id}/conversoes/ retorna as duas conversões
        persistidas sem erro 400 — confirmando que PT foi salva antes de CX na
        sequência real de chamadas HTTP, mesmo com CX aparecendo primeiro na tela.
CA-04 - 1 CX resolve corretamente para 300 UN (6 PT/CX × 50 UN/PT) — conferir preview
        do formulário (resolverFatorBase) e, após salvar, uma EntradaEstoque de 1 CX
        soma 300 na quantidade_estoque do produto.
CA-05 - Cenário inverso (criar PT primeiro, depois CX apontando pra PT) continua
        funcionando exatamente como antes — sem regressão na ordem que já funcionava.
CA-06 - Tentar criar um ciclo (linha CX→PT e linha PT→CX) e salvar → toast de erro
        claro sobre o ciclo ANTES de qualquer POST/PATCH de conversão ser disparado;
        nenhuma das duas linhas fica salva parcialmente; produto principal
        (nome/preço/etc.) continua salvo normalmente (RN-03).
CA-07 - Editar produto já existente com conversões já salvas (linhas com id) sem
        mexer nelas → nenhuma chamada extra de PATCH desnecessária (comportamento de
        "só envia o que mudou" preservado, linhas 234-241 do handleSubmit atual).
CA-08 - Select "Converte para" nunca lista a própria unidade da linha como opção
        (ex.: linha CX nunca mostra "CX" como destino).
CA-09 - FrenteDeCaixa.jsx sem nenhuma alteração (diff vazio).
CA-10 - backend/produtos/ sem nenhuma alteração de código (diff vazio) — suíte
        backend/produtos/tests.py 100% passando sem modificação, confirmando RN-04.
CA-11 - npm run build limpo, 0 erros.
```

---

## Observações finais do Analista

- O pedido diagnosticou corretamente a causa do bug relatado
  (`converteParaOptions` dependente da ordem local do estado `conversoes`) e propôs o
  fix certo para o Select (RF-01). Fui além do texto literal, como manda o papel do
  Analista: rastreei `handleSubmit` (linhas 211-268) e o backend
  (`produtos/services.py` + `produtos/tests.py`) para verificar se o mesmo problema de
  ORDEM aparecia em outro ponto da cadeia — e aparece. Corrigir só o dropdown
  resolveria a reclamação visual ("PT não aparece como opção"), mas o cenário exato
  descrito no pedido (criar CX antes de PT, apontar CX para PT, salvar) continuaria
  quebrando no clique de Salvar, com um 400 `"Conversão de unidade não cadastrada para
  PT"` que o usuário não teria como entender sozinho — porque o loop de salvamento
  persiste as linhas na mesma ordem em que aparecem na tela (linha 227 do código
  atual), e o backend exige, corretamente, que a unidade referenciada já exista salva
  no banco no momento do POST daquela linha. Por isso RF-02 entra nesta especificação,
  mesmo não constando no pedido original — sem ele, o bug relatado não fica
  efetivamente resolvido para o cenário que o próprio pedido descreve como exemplo.
- Confirmado com o teste já existente
  `backend/produtos/tests.py::test_criar_conversao_cadeia_via_api` (linha 189): ele só
  passa porque cria PT antes de CX — prova de que a dependência de ordem no
  salvamento é real e não hipotética.
- Backend não tem bug (RN-04). `validar_cadeia`/`fator_para_base` leem o estado já
  persistido de forma correta e agnóstica à ordem histórica de criação; a "restrição
  similar" que o pedido pediu para verificar existe, mas é o comportamento certo do
  lado do backend — o ajuste necessário é inteiramente do lado do frontend (RF-02),
  respeitando o pedido de não mexer em `FrenteDeCaixa.jsx` e mantendo
  `backend/produtos/` sem alteração de código.
- Nenhuma lacuna bloqueante — pedido tinha localização exata do bug (arquivo, linha,
  cenário reproduzível com números concretos), suficiente para especificar sem
  precisar voltar ao solicitante.

---

➡️ **Planner: rotear para Pipeline B (bug sobre módulo existente) — Loom
(`frontend/src/pages/Produtos.jsx`, RF-01 + RF-02) apenas, sem Forge (RN-04: nenhuma
mudança de backend necessária) → Sentinel (validar CA-01 a CA-11, com atenção especial
a CA-02/CA-03/CA-06 por serem os que provam a correção do cenário real do pedido, não
só do sintoma visual do dropdown) → Pilot.**
