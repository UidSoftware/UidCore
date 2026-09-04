# Especificação Hotfix — Manutenção #57

**Sistema:** UidCore (OS #7)
**Tipo:** feature_pequena
**Data:** 2026-09-04
**Solicitação original (cliente):** "No SystemD tem um sistema de gráfico em pizza com porcentagem de gastos, analisar e replicar no UidCore"

---

## 1. Contexto

### 1.1 O que existe no SystemD (referência a replicar)

Investigado em `/root/SystemD`. O gráfico de pizza "Gastos por Categoria" vive na
tela **Visão Geral** do módulo Financeiro:

- **Frontend:** `frontend/src/pages/sistema/financeiro/VisaoGeralPage.jsx`
  - Componente `GraficoPizzaCategorias({ dados })`, renderizado dentro de um
    `Card` ao lado do gráfico de barras "Receita x Despesa (6 meses)", em
    grid de 2 colunas.
  - **Não usa nenhuma biblioteca de gráfico** (`recharts`, `chart.js`, `d3` —
    nenhuma está instalada no `package.json` do SystemD). É um SVG desenhado
    manualmente: funções `polarToCartesian()` e `fatiaPath()` calculam os
    arcos de cada fatia a partir do `percentual` de cada categoria, com
    `viewBox="0 0 100 100"`, círculo único quando só existe 1 categoria.
  - Paleta fixa de 8 cores em hex (`CORES_PIZZA`), aplicada ciclicamente
    (`CORES_PIZZA[i % CORES_PIZZA.length]`).
  - Ao lado do SVG, uma legenda vertical: bolinha colorida + nome da
    categoria + percentual + valor em R$ (formatado via `formatMoeda`).
  - Estado vazio: "Nenhuma despesa registrada." quando `dados` vier vazio/nulo.
  - Tooltip nativo via `<title>` dentro de cada `<path>`/`<circle>` (nome +
    valor ao passar o mouse).

- **Backend:** `backend/financeiro/views.py`, dentro da view `dashboard()`
  (linhas ~1139-1161). Query:
  ```python
  despesas_categoria_qs = (
      Despesa.objects.filter(
          is_active=True, estornado=False, status='PAGO',
          referencia_mes__gte=primeiro_dia, referencia_mes__lte=ultimo_dia,
      )
      .values('categoria__nome')
      .annotate(total=Sum('valor_liquido'))
      .order_by('-total')
  )
  ```
  Para cada linha: `nome` (ou `'Sem categoria'` se `categoria` for nulo),
  `total` (Decimal) e `percentual` (`total / despesa_mes * 100`, arredondado
  a 1 casa decimal). Resultado exposto na chave `despesas_por_categoria` do
  payload de `dashboard()`.

- **Dados exibidos:** apenas **Despesas** (não Receitas), pagas
  (`status='PAGO'`), não estornadas (`estornado=False`), agrupadas por
  `categoria.nome`, do **mês corrente** (competência via `referencia_mes`,
  mesma base usada para o KPI "Despesa (mês)" — por isso a soma das fatias
  bate exatamente com esse KPI no SystemD).
- **Período:** fixo, mês corrente. Sem seletor de mês/ano — decisão do
  próprio SystemD, mantida aqui por paridade (ver RN-04).

### 1.2 O que existe no UidCore (ponto de partida)

Investigado em `/var/www/uidcore`.

- **Backend:** `backend/financeiro/views.py`, view `dashboard_financeiro()`
  (linha 541), já devolve `grafico_6_meses`, `despesas_pagas_por_mes`,
  `receitas_recebidas_por_mes`, `indicadores`, `balanco_resumo` — **não
  possui `despesas_por_categoria`**. É o endpoint a estender (não é preciso
  criar endpoint novo).
- **Models:** `Categoria` (`nome`, `tipo` = `ENTRADA`/`SAIDA`) e `Despesa`
  (`categoria` FK para `Categoria` com `limit_choices_to={'tipo': 'SAIDA'}`,
  `valor_liquido`, `status`, `estornado`, `pagamento`, `is_active`) já
  existem em `backend/financeiro/models.py` com a mesma semântica do
  SystemD — nenhuma migration é necessária.
- **Divergência de base de cálculo a resolver:** no UidCore,
  `despesa_mes` (o KPI "Despesa (mês)") é calculado via `LivroCaixa` (fluxo
  de caixa, campo `data`), enquanto `despesas_pagas_por_mes` (os cards
  colapsáveis logo abaixo) já usa `Despesa` filtrado por `pagamento` dentro
  do mês — duas bases diferentes que já convivem hoje na mesma tela. Para o
  gráfico de pizza, replicar a base de `despesas_pagas_por_mes` (não a de
  `despesa_mes`/LivroCaixa) — mesmo padrão de filtro (`is_active=True,
  status='PAGO', estornado=False, pagamento` dentro do mês corrente) já
  usado nessa mesma view para os cards por mês. Isso garante que a soma das
  fatias do gráfico bata com o total do mês corrente já exibido no card
  "Despesas Pagas". Ver RN-01.
- **Frontend:** `frontend/src/pages/Financeiro.jsx`, componente
  `ResumoTab()` (linha 205). Já renderiza o card "Receita x Despesa (6
  meses)" (linha 294) do mesmo jeito hand-rolled em SVG/CSS que o SystemD
  usa para barras — não há `recharts`/`chart.js`/`d3` no
  `frontend/package.json` do UidCore (confirmado). **Local natural para o
  gráfico de pizza:** logo depois do card "Receita x Despesa (6 meses)",
  dentro do mesmo `ResumoTab`, no mesmo padrão de grid 2 colunas usado no
  SystemD (`grid grid-cols-1 md:grid-cols-2 gap-4` — mesma classe já usada
  linha 256 do próprio arquivo para o par "Receitas/Despesas a Vencer").
- **Diferença de tema a resolver:** o SystemD é single-theme (fundo roxo
  escuro fixo, cores em `style` inline hardcoded, ex. `#1a0a2e`). O UidCore
  tem dark mode com toggle (Manutenção #31 — paleta `navy`/`violet` via
  Tailwind, `darkMode: 'class'`). O componente não pode copiar os hex fixos
  do SystemD — precisa usar Tailwind + tokens `navy-*`/`violet-*` como o
  resto do `ResumoTab()` já faz (`dark:bg-navy-800 dark:border-navy-600`),
  e a paleta de cores das fatias precisa ler bem tanto em fundo claro
  quanto em `navy-800`. Ver RF-05 e Spec Frontend.
- **Componente `Card`:** `frontend/src/components/ui/Card.jsx`, já
  importado e usado no `ResumoTab()` — reutilizar (`<Card title="...">`),
  não criar um novo wrapper.

---

## 2. Requisitos Funcionais (RF)

**RF-01 — Novo dado no endpoint de dashboard**
`GET /api/v1/financeiro/dashboard/` passa a devolver a chave
`despesas_por_categoria`: lista de objetos
`{ categoria_id, nome, total, percentual }`, ordenada por `total`
decrescente, agrupando as despesas do mês corrente por `categoria__nome`.
Despesa sem categoria (`categoria_id is NULL`) entra agrupada sob o nome
`"Sem categoria"` com `categoria_id: null`.

**RF-02 — Gráfico de pizza SVG (sem biblioteca nova)**
Novo componente frontend que renderiza um gráfico de pizza em SVG puro
(mesma técnica do SystemD — `polarToCartesian`/`fatiaPath`, sem adicionar
`recharts`/`chart.js`/`d3` ao `package.json`), consumindo
`data.despesas_por_categoria` do payload já buscado pelo `ResumoTab()`
(nenhuma chamada de API adicional).

**RF-03 — Legenda com percentual e valor**
Ao lado (ou abaixo, em telas estreitas) do SVG, lista com: bolinha colorida
da fatia, nome da categoria, percentual (`XX.X%`) e valor formatado em BRL
— mesmo padrão de legenda do SystemD.

**RF-04 — Tooltip nativo por fatia**
Cada fatia (`<path>`/`<circle>`) expõe `<title>{nome}: {valor BRL}</title>`
para tooltip nativo do navegador ao passar o mouse — paridade com o
SystemD.

**RF-05 — Paleta compatível com dark mode**
Paleta de cores das fatias definida em hex fixo (não pode usar classes
Tailwind dinâmicas em `fill` de SVG), mas escolhida para ter contraste
legível tanto sobre fundo claro (`bg-white`, tema claro do `Card`) quanto
sobre `navy-800` (tema escuro) — reutilizar tons já usados no restante do
projeto (`blue-500 #3b82f6`, `violet-500 #8b5cf6`, `emerald-500 #10b981`,
`amber-500 #f59e0b`, `red-500 #ef4444`, `cyan-500 #06b6d4`,
`pink-500 #ec4899`, `lime-500 #84cc16` — 8 cores, aplicadas ciclicamente
como no SystemD).

**RF-06 — Card posicionado no Resumo**
O card "Gastos por Categoria" aparece dentro de `ResumoTab()`
(`frontend/src/pages/Financeiro.jsx`), logo após o card "Receita x Despesa
(6 meses)", em grid de 2 colunas (`grid grid-cols-1 md:grid-cols-2 gap-4`),
reutilizando o componente `Card` já importado no arquivo.

**RF-07 — Estado vazio**
Quando `despesas_por_categoria` vier vazio (nenhuma despesa paga no mês),
exibir mensagem "Nenhuma despesa registrada neste mês." no lugar do SVG —
mesmo padrão textual das outras mensagens de estado vazio já existentes no
`ResumoTab()` (ex.: "Nenhuma receita pendente.").

---

## 3. Regras de Negócio (RN)

**RN-01 — Base de cálculo: Despesa paga por competência do mês, não
LivroCaixa**
`despesas_por_categoria` usa a mesma base de filtro já aplicada em
`despesas_pagas_por_mes` na própria `dashboard_financeiro()`:
`Despesa.objects.filter(is_active=True, status='PAGO', estornado=False,
pagamento__gte=primeiro_dia, pagamento__lte=ultimo_dia)` (mês corrente).
**Não** usar `LivroCaixa` (base do KPI `despesa_mes`) — evita reabrir a
divergência de bases já documentada na Manutenção #9/#13 para
patrimônio/DRE.

**RN-02 — Percentual soma 100% (não usa `despesa_mes` como denominador)**
`percentual` de cada categoria é calculado como
`total_categoria / soma_de_todos_os_totais_de_categoria * 100`, arredondado
a 1 casa decimal — **não** contra `despesa_mes` (que vem do `LivroCaixa` e
pode divergir da soma das categorias, conforme RN-01). Isso garante que a
soma dos percentuais exibidos feche em 100% (± arredondamento).

**RN-03 — Despesa sem categoria não é descartada**
Despesas com `categoria_id NULL` entram no agrupamento sob a categoria
sintética `"Sem categoria"` (`categoria_id: null` no payload) — mesmo
comportamento do SystemD (`nome = row['categoria__nome'] or 'Sem
categoria'`). Não excluir essas despesas do gráfico.

**RN-04 — Período fixo: mês corrente**
Sem seletor de mês/ano nesta manutenção — paridade com o SystemD, que
também não tem seletor no gráfico de pizza. Fora de escopo (ver seção 7).

**RN-05 — Estorno exclui a despesa do agrupamento**
Despesa com `estornado=True` não entra na soma nem aparece na legenda —
mesmo filtro (`estornado=False`) já usado em `despesas_pagas_por_mes` e no
SystemD.

**RN-06 — Apenas Despesas, não Receitas**
Gráfico mostra somente gastos (Despesas), não Receitas — paridade exata
com o nome "Gastos por Categoria" do SystemD. Gráfico de receitas por
categoria está fora de escopo desta manutenção.

---

## 4. Spec Backend

**Arquivo:** `backend/financeiro/views.py`
**Função:** `dashboard_financeiro()` (view existente, GET
`/api/v1/financeiro/dashboard/`)

Adicionar bloco de agregação por categoria, usando `primeiro_dia`/
`ultimo_dia` já calculados no início da função (linhas 542-547), seguindo
o mesmo formato de `desp_por_mes_qs` (linha 614) mas agrupando por
`categoria` em vez de por mês:

```python
# Despesas pagas do mes corrente agrupadas por categoria — alimenta o
# card "Gastos por Categoria" (pizza SVG) no Resumo. Mesma base de
# despesas_pagas_por_mes (pagamento dentro do mes corrente), NAO a
# mesma base de despesa_mes (LivroCaixa) — ver RN-01/RN-02.
despesas_categoria_qs = (
    Despesa.objects.filter(
        is_active=True, status='PAGO', estornado=False,
        pagamento__gte=primeiro_dia, pagamento__lte=ultimo_dia,
    )
    .values('categoria_id', 'categoria__nome')
    .annotate(total=Sum('valor_liquido'))
    .order_by('-total')
)
soma_categorias = sum((row['total'] or Decimal('0')) for row in despesas_categoria_qs)
despesas_por_categoria = []
for row in despesas_categoria_qs:
    total = row['total'] or Decimal('0')
    percentual = float((total / soma_categorias) * 100) if soma_categorias else 0.0
    despesas_por_categoria.append({
        'categoria_id': row['categoria_id'],
        'nome': row['categoria__nome'] or 'Sem categoria',
        'total': total,
        'percentual': round(percentual, 1),
    })
```

E incluir a chave no `Response(...)` final (perto de
`'despesas_pagas_por_mes'`, linha ~714):

```python
'despesas_por_categoria': despesas_por_categoria,
```

Nenhuma migration, nenhum model novo, nenhum endpoint novo — `Decimal` e
`Sum` já estão importados no topo do arquivo (mesmo padrão usado
logo acima em `desp_por_mes_qs`).

**Serializer:** não aplicável — `dashboard_financeiro()` monta `Response()`
com dict puro, sem serializer, mesmo padrão do restante da view.

---

## 5. Spec Frontend

**Arquivo:** `frontend/src/pages/Financeiro.jsx` (mesmo arquivo do
`ResumoTab()` — não criar página nova).

1. Novo componente `GraficoPizzaCategorias({ dados })` no mesmo arquivo
   (ou extraído para `frontend/src/components/financeiro/
   GraficoPizzaCategorias.jsx`, se o Loom preferir manter `Financeiro.jsx`
   enxuto — decisão de implementação, não de requisito), adaptando o do
   SystemD:
   - `polarToCartesian`/`fatiaPath` idênticos (matemática pura, não tem
     acoplamento com tema).
   - Paleta `CORES_PIZZA` em hex conforme RF-05 (não os hex do SystemD,
     que foram calibrados pro roxo escuro fixo).
   - Container e legenda em Tailwind (`flex flex-col sm:flex-row items-
     center gap-4`), texto com `text-gray-800 dark:text-slate-200` /
     `text-gray-400 dark:text-slate-500` — mesmo padrão de classes já
     usado no restante do `ResumoTab()` (nada de `style={{ color:
     '#e2d9f3' }}` fixo como no SystemD).
   - Formatação de valor: reaproveitar o helper `BRL()` já usado em todo
     o `ResumoTab()` (não recriar `formatMoeda`).

2. Envolver o card novo e o card "Receita x Despesa (6 meses)" (linha 294)
   num grid 2 colunas:
   ```jsx
   <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
     <Card title="Receita x Despesa (6 meses)">
       {/* conteúdo existente, inalterado */}
     </Card>
     <Card title="Gastos por Categoria">
       <GraficoPizzaCategorias dados={data.despesas_por_categoria} />
     </Card>
   </div>
   ```
   (hoje o card de barras está solto, fora de um grid — envolver os dois
   sem alterar o conteúdo interno do card de barras existente.)

3. Estado vazio: se `!dados || dados.length === 0`, renderizar
   `<p className="text-sm text-gray-400 dark:text-slate-500">Nenhuma
   despesa registrada neste mês.</p>` (RF-07).

Nenhuma dependência nova em `package.json` (confirma RF-02 — sem
`recharts`/`chart.js`/`d3`).

---

## 6. Critérios de Aceite

- **CA-01:** `GET /api/v1/financeiro/dashboard/` (autenticado) retorna a
  chave `despesas_por_categoria` como lista (vazia ou populada).
- **CA-02:** Cada item da lista tem exatamente as chaves `categoria_id`,
  `nome`, `total`, `percentual`.
- **CA-03:** A soma de `total` de todos os itens de
  `despesas_por_categoria` é igual à soma de `valor_liquido` de todas as
  `Despesa` com `is_active=True, status='PAGO', estornado=False,
  pagamento` no mês corrente (bate com o `total` do mês corrente já
  presente em `despesas_pagas_por_mes`).
- **CA-04:** A soma de `percentual` de todos os itens fecha em
  100.0 (± 0.1 de arredondamento) quando `soma_categorias > 0`.
- **CA-05:** Despesa paga no mês corrente sem `categoria` aparece
  agrupada sob `nome: "Sem categoria"`, `categoria_id: null`.
- **CA-06:** Despesa com `estornado=True` no mês corrente **não** entra em
  nenhuma linha de `despesas_por_categoria`.
- **CA-07:** Despesa com `status != 'PAGO'` (ex. `PENDENTE`) no mês
  corrente **não** entra em `despesas_por_categoria`.
- **CA-08:** Quando não há nenhuma despesa paga no mês corrente,
  `despesas_por_categoria` retorna `[]` (lista vazia, não erro/null).
- **CA-09:** Tela Financeiro → aba Resumo (`ResumoTab`) renderiza o card
  "Gastos por Categoria" ao lado do card "Receita x Despesa (6 meses)",
  lado a lado em telas ≥ `md` e empilhados em telas menores.
- **CA-10:** Com `despesas_por_categoria` vazio, o card exibe "Nenhuma
  despesa registrada neste mês." em vez do SVG.
- **CA-11:** Com 1 categoria, o gráfico renderiza um círculo único
  (mesmo tratamento do SystemD para evitar arco degenerado de 360°).
- **CA-12:** Com 2+ categorias, cada fatia do SVG tem `<title>` com
  `{nome}: {valor em BRL}` — confirmar via inspeção do DOM renderizado.
- **CA-13:** Card e gráfico legíveis (contraste adequado) em tema claro e
  em tema escuro (toggle ☀️/🌙 do Header, Manutenção #31) — sem hex fixo
  incompatível com `navy-800`.
- **CA-14:** `npm run build` limpo, 0 erros, nenhuma dependência nova
  adicionada ao `package.json`.
- **CA-15:** Testes Django existentes (todos os módulos) continuam
  passando — 0 regressão (view estendida, não substituída).

---

## 7. Fora do Escopo

- Seletor de mês/ano para o gráfico de pizza (paridade com SystemD, que
  também não tem — RN-04).
- Gráfico de pizza para Receitas por categoria (RN-06 — só Despesas).
- Exportação do gráfico (PDF/imagem).
- Drill-down (clicar na fatia para ver lançamentos daquela categoria) —
  o SystemD também não tem essa interação.
- Migração de `despesa_mes` (KPI) de `LivroCaixa` para `Despesa` — fora de
  escopo desta manutenção; divergência de base pré-existente, documentada
  na seção 1.2, não é objeto deste hotfix.

---

## 8. Riscos e Dependências

- **Risco baixo:** view estendida (não reescrita) — `Response()` ganha uma
  chave nova, nenhum contrato de campo existente muda.
- **Dependência:** nenhuma — models `Categoria`/`Despesa` já existem com
  os campos necessários; nenhuma migration.
- **Atenção do Loom:** não copiar hex inline do SystemD (`#1a0a2e`,
  `#a78bca` etc.) — projeto tem dark mode com toggle, precisa de classes
  Tailwind (ver RF-05 e Spec Frontend item 1).
- **Atenção do Sentinel:** validar CA-03/CA-04 com dado real no banco
  (não só teste unitário isolado) — mesma recomendação já registrada nas
  manutenções anteriores de módulo financeiro (Manutenção #9/#13),
  divergência de base de cálculo é a categoria de bug mais recorrente
  nesse módulo.
