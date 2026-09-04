# Especificação UI Hotfix — UidCore (Manutenção #57)

## Design System do Projeto (referência)

`design_system.md` na raiz do projeto é anterior à Manutenção #31 (dark
mode) e não documenta os tokens `navy-*`/`violet-*` — a fonte de verdade
atual é `frontend/tailwind.config.js` + o padrão já em uso em
`frontend/src/pages/Financeiro.jsx`. Resumo aplicável a esta tarefa:

- **Cores de superfície (dark):** `navy-950` (fundo app), `navy-900`,
  `navy-800` (cards — `dark:bg-navy-800`), `navy-700`/`navy-600` (bordas —
  `dark:border-navy-600`, `dark:border-navy-700`).
- **Cores de superfície (light):** `bg-white`, `border-gray-200`,
  `border-gray-100`.
- **Cor de ação/destaque:** `violet-*` (não usada diretamente neste
  componente — o gráfico usa a paleta categórica do RF-05, não `violet`
  como cor única).
- **Fonte:** Plus Jakarta Sans (headings/UI) + DM Sans (`font-body`) — já
  carregadas globalmente, nenhuma ação necessária aqui.
- **BorderRadius padrão:** `rounded-xl` (cards, via componente `Card`),
  `rounded-full` (badges/bolinhas de legenda).
- **Padrão de card:** componente `Card` (`frontend/src/components/ui/
  Card.jsx`) — `bg-white dark:bg-navy-800`, borda `border-gray-200
  dark:border-navy-600`, `rounded-xl`, header opcional com `title` em
  `text-sm font-semibold text-gray-700 dark:text-slate-200`, corpo com
  `px-6 py-4`. **Reutilizar tal como está — não criar wrapper novo.**
- **Texto secundário/muted:** `text-gray-400 dark:text-slate-500` (estado
  vazio, captions) e `text-gray-500 dark:text-slate-500` (legendas
  auxiliares, ex. eixo do gráfico de barras existente).
- **Texto principal:** `text-gray-800 dark:text-slate-200`.

## Especificação Visual — Card "Gastos por Categoria"

### Layout geral (integração no ResumoTab)

O card novo entra no **mesmo grid** do card "Receita x Despesa (6 meses)"
existente (`frontend/src/pages/Financeiro.jsx`, linha ~294), não depois
dele solto. Hoje esse card está fora de qualquer grid; passa a ficar
lado a lado com o novo:

```jsx
<div className="grid grid-cols-1 md:grid-cols-2 gap-4">
  {data.grafico_6_meses && (
    <Card title="Receita x Despesa (6 meses)">
      {/* conteúdo existente do gráfico de barras — inalterado */}
    </Card>
  )}

  <Card title="Gastos por Categoria">
    <GraficoPizzaCategorias dados={data.despesas_por_categoria} />
  </Card>
</div>
```

- Mesma classe de grid já usada linha 256 do arquivo para o par
  "Receitas a Vencer" / "Despesas a Vencer" (`grid grid-cols-1
  md:grid-cols-2 gap-4`) — reutilizar exatamente, não inventar variação.
- Posição no fluxo da página: onde hoje está o card "Receita x Despesa (6
  meses)" (depois do par Receitas/Despesas a Vencer, antes dos cards
  colapsáveis Despesas Pagas/Receitas Recebidas).
- O card "Receita x Despesa (6 meses)" mantém seu `{data.grafico_6_meses
  && (...)}` de renderização condicional já existente; o card novo
  renderiza sempre (o estado vazio é tratado dentro do componente, ver
  seção "Estado vazio" abaixo) — não usar `data.despesas_por_categoria &&
  (...)` no nível do `<Card>`, senão o card some da tela inteira em vez
  de mostrar a mensagem de vazio (RF-07/CA-10 exigem que o card continue
  visível com a mensagem).

### SVG manual — paleta de cores

Fill de `<path>`/`<circle>` do SVG não aceita classe Tailwind dinâmica —
usar array de hex fixo conforme já definido no RF-05 da
`Especificacao_Hotfix.md` (não inventar paleta nova, não copiar os hex do
SystemD):

```js
const CORES_PIZZA = [
  '#3b82f6', // blue-500
  '#8b5cf6', // violet-500
  '#10b981', // emerald-500
  '#f59e0b', // amber-500
  '#ef4444', // red-500
  '#06b6d4', // cyan-500
  '#ec4899', // pink-500
  '#84cc16', // lime-500
]
```

- Aplicação cíclica: `CORES_PIZZA[i % CORES_PIZZA.length]`, `i` = índice
  do item em `despesas_por_categoria` (mesma ordem retornada pela API,
  já ordenada por `total` decrescente — não reordenar no frontend).
- `viewBox="0 0 100 100"`, `polarToCartesian`/`fatiaPath` — mesma
  matemática do SystemD (matemática pura, sem acoplamento de tema).
- **Caso 1 categoria:** renderizar `<circle>` único preenchido com
  `CORES_PIZZA[0]` (evita arco degenerado de 360° em `fatiaPath` — CA-11).
- Essas 8 cores foram escolhidas para manter contraste mínimo 4.5:1 tanto
  sobre `bg-white` (tema claro) quanto sobre `navy-800` (`#1a2540`, tema
  escuro) — todas são tons "500" de saturação média-alta, não precisam de
  ajuste por tema. Não usar tons "300"/"400" (contraste insuficiente em
  fundo claro) nem "700"/"800" (somem em `navy-800`).

### Legenda

- Layout: `flex flex-col sm:flex-row items-start sm:items-center gap-4`
  dentro do corpo do `Card` — SVG à esquerda (ou acima, mobile), lista de
  legenda à direita (ou abaixo, mobile).
- Tamanho do SVG: `w-32 h-32` (128px) fixo — proporcional ao espaço do
  card ao lado do gráfico de barras (`h-40`/`h-32` já usados no card
  vizinho), sem crescer além disso.
- Cada item da legenda em `flex items-center gap-2 text-sm` com:
  - Bolinha colorida: `<span className="w-2.5 h-2.5 rounded-full
    flex-shrink-0" style={{ backgroundColor: CORES_PIZZA[i %
    CORES_PIZZA.length] }} />` — mesmo padrão de bolinha já usado na
    legenda do gráfico de barras (`w-2 h-2 bg-green-400 rounded-full`),
    só que com cor dinâmica via `style` (inevitável — cor vem de array,
    não de classe estática) em vez de `bg-*` fixo.
  - Nome da categoria: `text-gray-700 dark:text-slate-200 truncate`
    (categorias podem ter nome longo — truncar, não quebrar layout).
  - Percentual: `text-gray-400 dark:text-slate-500 text-xs` logo após o
    nome, formato `XX.X%` (valor já vem pronto do backend, só
    concatenar `%`).
  - Valor BRL: `font-semibold text-gray-800 dark:text-slate-200
    whitespace-nowrap ml-auto` alinhado à direita do item — reaproveitar
    `BRL()` (helper já definido no topo de `Financeiro.jsx`, linha 82),
    não recriar formatação de moeda.
  - Espaçamento entre itens da legenda: `space-y-1.5` no container da
    lista.
  - Lista com `max-h-32 overflow-y-auto` se houver muitas categorias
    (evita empurrar o card e desalinhar o grid — mesmo cuidado de scroll
    interno já aplicado nos cards colapsáveis Despesas Pagas/Receitas
    Recebidas).

### Estado vazio

Quando `!dados || dados.length === 0`, renderizar **no lugar do SVG +
legenda** (não junto):

```jsx
<p className="text-sm text-gray-400 dark:text-slate-500">
  Nenhuma despesa registrada neste mês.
</p>
```

- Mesma classe exata (`text-sm text-gray-400 dark:text-slate-500`) já
  usada nos outros estados vazios do `ResumoTab()` ("Nenhuma receita
  pendente.", "Nenhuma despesa pendente.", "Nenhuma despesa paga
  registrada.") — não inventar variação de cor/tamanho para este caso.
- O `<Card title="Gastos por Categoria">` continua renderizado (só o
  conteúdo interno muda) — o header do card com o título permanece
  visível mesmo sem dados, mesmo padrão dos outros cards do
  `ResumoTab()`.

### Responsividade

- **Mobile (< `md`, < 768px):** grid do card colapsa para 1 coluna
  (`grid-cols-1`) — card "Gastos por Categoria" empilha abaixo de
  "Receita x Despesa (6 meses)", ocupando 100% da largura. Dentro do
  card, SVG + legenda também empilham (`flex-col`, breakpoint interno
  `sm:flex-row` — ou seja, entre 768px de largura de viewport o card
  ainda pode estar estreito o suficiente pra manter a legenda embaixo do
  SVG; usar a largura do container, não a do viewport, como já é a
  convenção Tailwind aqui).
- **Desktop (≥ `md`, ≥ 768px):** grid 2 colunas
  (`md:grid-cols-2`), SVG e legenda lado a lado dentro do card
  (`sm:flex-row`).
- Testar em 375px (iPhone SE, conforme princípio Uid de armadilhas
  conhecidas): SVG de 128px + legenda embaixo não deve estourar a
  largura do card nem exigir scroll horizontal.

### Dark mode — classes exatas

| Elemento | Light | Dark |
|---|---|---|
| Fundo do card | `bg-white` (herdado do `Card`) | `dark:bg-navy-800` (herdado do `Card`) |
| Borda do card | `border-gray-200` (herdado do `Card`) | `dark:border-navy-600` (herdado do `Card`) |
| Título do card | `text-gray-700` (herdado do `Card`) | `dark:text-slate-200` (herdado do `Card`) |
| Nome da categoria (legenda) | `text-gray-700` | `dark:text-slate-200` |
| Percentual (legenda) | `text-gray-400` | `dark:text-slate-500` |
| Valor BRL (legenda) | `text-gray-800` font-semibold | `dark:text-slate-200` |
| Mensagem estado vazio | `text-gray-400` | `dark:text-slate-500` |
| Fatias do SVG (`fill`) | hex fixo `CORES_PIZZA` (RF-05) | mesmo hex fixo — já calibrado pra ler em `navy-800` |

Nenhuma classe nova precisa ser adicionada ao `tailwind.config.js` — tudo
usa tokens/cores já existentes no projeto.

### Componentes existentes a reutilizar

- `Card` (`frontend/src/components/ui/Card.jsx`) — já importado em
  `Financeiro.jsx`, usar `<Card title="Gastos por Categoria">` sem
  wrapper adicional.
- `BRL()` (helper de formatação de moeda, `Financeiro.jsx` linha 82) —
  reutilizar para os valores da legenda e do `<title>` do tooltip; **não
  recriar `formatMoeda`** (nome usado no SystemD, não existe no UidCore).
- Classe de grid `grid grid-cols-1 md:grid-cols-2 gap-4` — já em uso
  linha 256, reaplicar aqui.
- Padrão de bolinha de legenda (`w-2 h-2 ... rounded-full`) do card
  "Receita x Despesa (6 meses)" — adaptar tamanho para `w-2.5 h-2.5` por
  ser lista mais longa (até 8+ categorias) e precisar de leitura rápida
  ao lado do nome.

### Novo componente (local sugerido)

`GraficoPizzaCategorias({ dados })` — pode ficar inline em
`Financeiro.jsx` (mesmo arquivo do `ResumoTab()`, junto de `KpiCard`) ou
extraído para `frontend/src/components/financeiro/
GraficoPizzaCategorias.jsx`, a critério do Loom. Nenhuma prop além de
`dados` (array de `{ categoria_id, nome, total, percentual }` vindo
direto de `data.despesas_por_categoria`) — sem chamada de API própria.

## Fora do escopo desta especificação de UI

- Cálculo/agregação de `despesas_por_categoria` — já especificado no
  backend pelo Analista em `Especificacao_Hotfix.md` (seção 4/RF-01),
  Loom só consome o payload.
- Seletor de mês/ano, drill-down por fatia, exportação — fora de escopo
  desta manutenção (ver seção 7 de `Especificacao_Hotfix.md`).
- Qualquer mudança em `tailwind.config.js` ou nos tokens `navy-*`/
  `violet-*` — não é necessária, tudo já existe.
