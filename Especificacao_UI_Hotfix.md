# Especificação UI Hotfix — UidCore (Manutenção #91)

## Modo

**MODO HOTFIX.** Extensão de tela já existente (`frontend/src/pages/
Produtos.jsx`) para suportar um novo `tipo` (`SERVICO`) dentro do mesmo
model `Produto`, com reflexo em 3 telas que já consomem produto:
`Produtos.jsx` (cadastro + listagem), PDV (`pages/pdv/FrenteDeCaixa.jsx`)
e Vendas (`pages/Vendas.jsx` — `BuscaProdutoRapida`/`ProdutoAutocomplete`).
Nenhum app/rota/tela nova, nenhuma mudança de identidade visual, paleta ou
tipografia — tudo reaproveita o design system e os componentes já em
produção.

Lido antes de escrever esta especificação: `Especificacao_Hotfix.md`
(Manutenção #91, seções 1-9 + Spec Frontend completas), `frontend/src/
pages/Produtos.jsx` (completo, 1302 linhas — form/modal de Produto linhas
804-1000+, listagem mobile/desktop linhas 596-690, seção Combos
693-800+), `frontend/src/pages/Vendas.jsx` (padrão de abas `TABS`/`tab`
linhas 16-19 e 1045-1060; `BuscaProdutoRapida` com badge "Sem estoque"
linha ~354), `frontend/src/pages/pdv/FrenteDeCaixa.jsx` (dropdown de
busca com o mesmo badge "Sem estoque" linha ~483), `components/ui/{Button,
Select, Input, Modal, Card}.jsx`.

**Achado relevante:** o briefing do Planner cita "Produtos.jsx tem abas
(Produtos/Combos)" — não é exato. Hoje `Produtos.jsx` **não tem abas**:
é uma lista única de Produtos seguida de uma seção "Combos" separada,
sempre visível, abaixo (linha 693+). O padrão de abas de verdade (`TABS`
+ botões toggle + estado `tab`) já existe no projeto, mas em
`Vendas.jsx` (Orçamentos/Pedidos), não em Produtos. Esta especificação
usa exatamente esse padrão existente — não inventa um novo — aplicado
pela primeira vez em `Produtos.jsx`, só para a lista de Produtos/
Serviços (a seção Combos abaixo continua como está, fora do escopo).

## Design System do Projeto (referência — não alterado)

- **Cores primárias:** `primary-600` (light) / `violet-600` (dark) —
  botão de ação, aba ativa, foco de input/select. Hover:
  `primary-700`/`violet-700` (light), `violet-700` (dark).
- **Cores de fundo:** `white` (light) / `navy-800` (dark) — cards,
  modal, dropdown; `gray-50`/`navy-900` para header de tabela e fundo de
  página; `navy-500` para borda de input/select, `navy-600`/`navy-700`
  para borda de card/divisor.
- **Texto:** `text-gray-900`/`text-gray-700`/`text-gray-500`/
  `text-gray-400` (light), `text-slate-100`/`text-slate-300`/
  `text-slate-400`/`text-slate-500` (dark).
- **Feedback:**
  - Verde (`green-100`/`green-700` light, `emerald-900/30`/
    `emerald-300` dark) — já usado para badge "Ativo" em Produtos.
  - Cinza (`gray-100`/`gray-500` light, `navy-700`/`slate-400` dark) —
    já usado para badge "Inativo".
  - Vermelho (`red-100`/`red-800` light, `red-900/30`/`red-300` dark) —
    já usado para badge "Sem estoque" no PDV/Vendas; **nunca** reaplicar
    esse vermelho ao badge novo de "Serviço" (ver abaixo) para não
    sugerir alerta onde não há.
- **Cor nova desta manutenção — badge "Serviço":** usar o mesmo par
  primário já usado para ações/destaque neutro no projeto —
  `bg-primary-100 text-primary-700` (light) / `bg-violet-900/30
  text-violet-300` (dark). É a mesma família de cor do botão primário e
  da aba ativa, então comunica "categoria/tipo", não "status" nem
  "alerta" — evita colidir visualmente com os badges de Ativo/Inativo
  (verde/cinza) e Sem estoque (vermelho) já existentes na mesma tela.
- **Fonte:** Plus Jakarta Sans (display) + DM Sans (body) — já
  carregadas globalmente, não tocar.
- **BorderRadius:** `rounded-lg` (inputs, selects, botões, badges,
  abas), `rounded-2xl` (`Modal.jsx`, não tocar), `rounded-full` (pill
  dos badges de status — manter, é o padrão já usado em Ativo/Inativo/
  Sem estoque).
- **Dark mode:** classe `dark` no `<html>`, toggle já existente — não
  tocar; todo elemento novo nesta manutenção precisa das duas variantes
  (light + `dark:`), igual ao resto do arquivo.
- **Ícones:** biblioteca `lucide-react`, já importada em `Produtos.jsx`
  (`Plus, Trash2, ArrowRight, Gift, Pencil, Package`). Padrão do
  projeto: emoji só na Sidebar (regra global do CLAUDE.md) — dentro de
  telas/formulários, ícone é sempre Lucide.

## Especificação Visual por Tela

### `Produtos.jsx` — Header e botão de ação

**Mudança:** label do botão `+ Novo Produto` → `+ Novo Item`
(linha 583). Mesmo componente `Button` (`variant` padrão = primary),
mesmo ícone implícito de texto (sem ícone hoje — manter sem ícone, não
introduzir `<Plus>` onde não existia, para não alterar mais do que o
texto pedido).

```jsx
<Button onClick={openNew}>+ Novo Item</Button>
```

Subtítulo do header ("Gestão de estoque e catálogo de produtos",
linha 581) **não muda** — continua válido, catálogo agora inclui
serviço, mas a frase já é genérica o suficiente.

---

### `Produtos.jsx` — Abas Todos | Produtos | Serviços

**Posição:** entre o `Card` de busca (linha 585-591) e o bloco de
conteúdo (`loading`/lista vazia/cards/tabela, linha 594+). Mesma posição
relativa que as abas de `Vendas.jsx` ocupam em relação ao conteúdo
daquela tela.

**Componente:** clonar o padrão exato de `TABS`/botões-toggle de
`Vendas.jsx` (linhas 16-19 e 1045-1060) — não é um componente `ui/`
reutilizável hoje (é inline em cada página), então replicar o mesmo
JSX/classes, não importar de `Vendas.jsx`.

```jsx
const TIPO_TABS = [
  { key: '', label: 'Todos' },
  { key: 'PRODUTO', label: 'Produtos' },
  { key: 'SERVICO', label: 'Serviços' },
]
```

```jsx
<div className="flex gap-1 overflow-x-auto pb-1">
  {TIPO_TABS.map((t) => (
    <button
      key={t.key || 'todos'}
      onClick={() => setFiltroTipo(t.key)}
      className={`px-4 py-2 text-sm font-medium rounded-lg whitespace-nowrap transition-colors ${
        filtroTipo === t.key
          ? 'bg-primary-600 text-white dark:bg-violet-600'
          : 'bg-white text-gray-600 hover:bg-gray-100 border border-gray-200 dark:bg-navy-800 dark:text-slate-400 dark:hover:bg-navy-700 dark:border-navy-600'
      }`}
    >
      {t.label}
    </button>
  ))}
</div>
```

- "Todos" é o padrão (`filtroTipo === ''`) — bate com RF-10 (comportamento
  atual preservado ao abrir a tela).
- Trocar de aba reseta `page` para 1 e refaz o fetch com `?tipo=...`
  (ou sem o param para "Todos") — mesmo padrão de `useEffect` que já
  reage a `search`/`page` hoje.
- **Mobile-first:** `overflow-x-auto` já cobre 375px (3 abas cabem sem
  quebrar, mas a classe garante scroll horizontal se a label aumentar
  por tradução/zoom futuro — mesma garantia que `Vendas.jsx` já tem com
  2 abas).
- Esta aba filtra **só a lista de Produtos/Serviços** — a seção Combos
  abaixo (linha 693+) não tem filtro e não é afetada.

---

### `Produtos.jsx` — Listagem (cards mobile + tabela desktop)

**Badge de tipo** — novo span ao lado do nome, nos dois layouts (mobile
card linha ~607 e tabela desktop linha ~649), mesmo estilo pill dos
badges de Ativo/Inativo já existentes:

```jsx
<span className={`shrink-0 text-xs rounded-full px-2 py-0.5 font-medium ${
  p.tipo === 'SERVICO'
    ? 'bg-primary-100 text-primary-700 dark:bg-violet-900/30 dark:text-violet-300'
    : 'bg-gray-100 text-gray-500 dark:bg-navy-700 dark:text-slate-400'
}`}>
  {p.tipo === 'SERVICO' ? 'Serviço' : 'Produto'}
</span>
```

- **Mobile card:** vai ao lado do badge Ativo/Inativo já existente, no
  mesmo `flex items-start justify-between` do topo do card — os dois
  badges ficam lado a lado (gap-1.5/2), sem empilhar, card não cresce
  de altura.
- **Tabela desktop:** inserir como um `<span>` extra dentro da própria
  célula "Nome" (ao lado/abaixo do nome, truncate preservado) — **não**
  criar coluna nova na tabela para não desalinhar a largura das colunas
  já existentes em telas estreitas (ex.: notebook 1280px); badge de tipo
  é metadado leve, não precisa de coluna dedicada, igual ao que já se
  faz hoje com o badge de status dentro da própria célula.
- **Coluna/campo "Estoque"** (mobile: bloco "Estoque" linha ~621-624;
  desktop: coluna "Estoque" linha ~649): quando `p.tipo === 'SERVICO'`,
  renderizar `—` no lugar de `{p.quantidade_estoque || 0} {p.unidade_base}`
  (RF-10). Mesma célula/posição, só o conteúdo muda — não oculta a
  célula por completo (manteria o grid/tabela desalinhado entre linhas
  de tipos diferentes).

```jsx
{p.tipo === 'SERVICO' ? '—' : `${p.quantidade_estoque || 0} ${p.unidade_base}`}
```

---

### `Produtos.jsx` — Modal "Novo Item" / "Editar Item"

**Título do modal** (linha 805): `Editar Produto`/`Novo Produto` →
`Editar Item`/`Novo Item`.

**Seletor de tipo** — novo bloco logo abaixo do título, antes do
primeiro `Input` de nome (antes da linha 811). Usar o mesmo padrão
visual de toggle de duas opções (não o `Select` dropdown — a escolha é
binária e estrutural, toggle deixa mais evidente que ela reconfigura o
form inteiro, igual ao padrão já visto nas abas de `Vendas.jsx`/aba de
Produtos acima, reaproveitando a mesma classe):

```jsx
<div className="flex gap-2">
  {[
    { value: 'PRODUTO', label: 'Produto' },
    { value: 'SERVICO', label: 'Serviço' },
  ].map((opt) => (
    <button
      key={opt.value}
      type="button"
      disabled={!!editingId}
      onClick={() => setForm((f) => ({ ...f, tipo: opt.value }))}
      className={`flex-1 px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
        form.tipo === opt.value
          ? 'bg-primary-600 text-white dark:bg-violet-600'
          : 'bg-white text-gray-600 border border-gray-300 hover:bg-gray-50 dark:bg-navy-800 dark:text-slate-400 dark:border-navy-500 dark:hover:bg-navy-700'
      } disabled:opacity-50 disabled:cursor-not-allowed`}
    >
      {opt.label}
    </button>
  ))}
</div>
```

- `disabled` + `disabled:opacity-50 disabled:cursor-not-allowed` cobre
  RN-06 (não dá para trocar o tipo na edição) — sem precisar de tooltip
  explicando por quê (o cursor `not-allowed` + opacidade já é o sinal
  visual padrão do projeto para campo bloqueado, mesma linguagem usada
  em botões `disabled` existentes).
- Toggle de 2 botões (não `Select`) porque é usado uma única vez, no
  topo do form, e o estado visual "qual está selecionado" precisa ser
  óbvio sem abrir dropdown — consistente com a razão de ser de um
  toggle vs. select.

**Campos condicionais — bloco `PRODUTO` (sem mudança nenhuma):**
todo o form atual (linhas 811-1000+: nome, código de barras, unidade
base, estoque inicial/mínimo, custo, preço de venda, observações, seção
conversões, seção "Movimentar Estoque") permanece **idêntico, pixel por
pixel**, dentro de `{form.tipo === 'PRODUTO' && (...)}`. Zero alteração
visual no fluxo de cadastro de Produto já em produção.

**Campos condicionais — bloco `SERVICO` (novo):**

```jsx
{form.tipo === 'SERVICO' && (
  <>
    <Input label="Nome" name="nome" value={form.nome} onChange={handleChange} required />

    <Input
      label="Descrição"
      name="observacoes"
      value={form.observacoes}
      onChange={handleChange}
      placeholder="Ex.: sessão de 50 minutos, inclui avaliação inicial"
    />

    <div className="grid grid-cols-2 gap-3">
      <Input
        label="Preço de Venda"
        name="preco_venda"
        type="number"
        step="0.01"
        value={form.preco_venda}
        onChange={handleChange}
        required
      />
      <Input
        label="Duração (minutos)"
        name="duracao_minutos"
        type="number"
        min="0"
        value={form.duracao_minutos}
        onChange={handleChange}
        placeholder="Opcional"
      />
    </div>

    <Select
      label="Categoria financeira de entrada"
      name="categoria_financeira_entrada"
      value={form.categoria_financeira_entrada}
      onChange={handleChange}
      options={[{ value: '', label: 'Sem categoria sugerida' }, ...categoriasEntrada]}
    />
  </>
)}
```

- **Reuso explícito:** `Input`, `Select` — mesmos componentes `ui/` já
  importados no arquivo, nenhum componente novo.
- `observacoes` é o **mesmo campo** do model (RF-09 do Analista já
  decide isso) — só muda o `label` exibido ("Descrição" em vez de
  "Observações"), sem duplicar estado nem criar input novo.
- `categoriasEntrada`: novo `useState([])`, carregado 1x ao abrir o
  modal (ou 1x ao montar a página — decisão do Loom, ambas aceitáveis)
  via `GET /api/v1/financeiro/categorias/?tipo=ENTRADA`, mapeado para
  `{value: c.id, label: c.nome}`. Opcional de verdade — opção
  "Sem categoria sugerida" sempre disponível e selecionada por padrão.
- **Não reaproveitar `CriarCategoriaRapidaModal.jsx`** (usado em
  Financeiro/Assinaturas para criar categoria on-the-fly) — fora de
  escopo nesta manutenção (RN-07: campo é só metadado informativo, sem
  fluxo de criação rápida associado). Se o usuário precisar de uma
  categoria nova, cadastra em Financeiro → Categorias primeiro.
- **Nada de:** código de barras, unidade base, estoque inicial/mínimo,
  custo, seção de conversões, seção "Movimentar Estoque" — nenhum desses
  blocos renderiza quando `form.tipo === 'SERVICO'` (ficam dentro do
  `{form.tipo === 'PRODUTO' && (...)}` acima, nunca duplicados).

**Grid responsivo:** o `grid grid-cols-2 gap-3` do bloco Serviço (Preço
+ Duração) segue o mesmo padrão mobile-first já usado no bloco Produto
do mesmo modal (ex.: estoque inicial + estoque mínimo também em
`grid-cols-2` hoje) — em 375px o grid de 2 colunas com `Input` numérico
curto continua legível (já validado no bloco Produto existente, mesmo
breakpoint, sem `md:` necessário).

---

### PDV (`pages/pdv/FrenteDeCaixa.jsx`) — Dropdown de busca

**Badge "Serviço"** no resultado de busca (bloco `resultadosBusca.map`,
~linha 469-490), ao lado de onde hoje só aparece preço + estoque/badge
"Sem estoque":

```jsx
<div className="text-right shrink-0 ml-3">
  <p className="text-sm font-mono font-medium text-gray-900 dark:text-slate-100">{BRL(p.preco_venda)}</p>
  {p.tipo === 'SERVICO' ? (
    <span className="px-1.5 py-0.5 rounded-full text-xs font-semibold bg-primary-100 text-primary-700 dark:bg-violet-900/30 dark:text-violet-300">
      Serviço
    </span>
  ) : parseFloat(p.quantidade_estoque || 0) <= 0 ? (
    <span className="px-1.5 py-0.5 rounded-full text-xs font-semibold bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300">
      Sem estoque
    </span>
  ) : (
    <p className="text-xs text-gray-400 dark:text-slate-500">{p.quantidade_estoque} {p.unidade_base}</p>
  )}
</div>
```

- Mesma posição, mesma classe de badge (`rounded-full text-xs
  font-semibold px-1.5 py-0.5`) já usada para "Sem estoque" — só troca
  a cor (vermelho de alerta → primary/violet neutro, ver seção Design
  System acima) e o texto.
- A linha inteira do resultado perde o `opacity-50` que hoje marca
  "sem estoque" (`className={parseFloat(p.quantidade_estoque || 0) <=
  0 ? 'opacity-50' : ''}`) quando o item é Serviço — serviço nunca está
  "indisponível por estoque", então nunca deve parecer desabilitado na
  busca:

```jsx
<div className={p.tipo !== 'SERVICO' && parseFloat(p.quantidade_estoque || 0) <= 0 ? 'opacity-50' : ''}>
```

**Carrinho** — linha do item no carrinho que hoje mostra unidade:
quando o item adicionado é de Serviço, omitir o seletor/texto de
unidade (renderizar vazio ou nada na posição onde a unidade apareceria)
— sem remover a coluna/alinhamento do carrinho, só o conteúdo textual
daquela posição específica.

---

### Vendas (`pages/Vendas.jsx`) — `BuscaProdutoRapida` e autocomplete por linha

Mesmo tratamento do PDV, no mesmo componente `BuscaProdutoRapida`
(~linha 320-360) — é **o mesmo bloco de código visual** (badge "Sem
estoque", `opacity-50`) duplicado do PDV, então a mudança é idêntica:

```jsx
{p.tipo === 'SERVICO' ? (
  <span className="px-1.5 py-0.5 rounded-full text-xs font-semibold bg-primary-100 text-primary-700 dark:bg-violet-900/30 dark:text-violet-300">
    Serviço
  </span>
) : parseFloat(p.quantidade_estoque || 0) <= 0 ? (
  <span className="px-1.5 py-0.5 rounded-full text-xs font-semibold bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300">
    Sem estoque
  </span>
) : (
  <p className="text-xs text-gray-400 dark:text-slate-500">{p.quantidade_estoque} {p.unidade_base}</p>
)}
```

- Item de Serviço adicionado à lista de itens do Orçamento/Pedido
  (`SecaoItens`) não exibe campo de unidade — o model `ItemOrcamento`/
  `ItemPedido` já não tem esse campo (RF-11/Spec Frontend do Analista já
  confirma: "não há mudança de payload aqui, é só visual"), então não
  há nada a esconder na linha do item em si, só no dropdown de busca
  acima.

---

### Combos (`ComboForm`, dentro de `Produtos.jsx`)

Sem mudança visual — autocomplete de produto do Combo continua listando
Produto e Serviço juntos, sem badge nem tratamento especial (confirma a
decisão "Fora do Escopo" do Analista — RN explicitamente não vedada).

## Componentes reutilizados (resumo)

- `Button`, `Input`, `Select`, `Modal`, `Card`, `Pagination` — todos já
  existentes em `components/ui/`, nenhum componente novo criado.
- Padrão de abas (`TABS`/toggle de botões) — clonado de `Vendas.jsx`,
  primeira vez aplicado em `Produtos.jsx`.
- Padrão de badge pill (`rounded-full text-xs font-semibold px-1.5/2
  py-0.5`) — já usado para Ativo/Inativo/Sem estoque, estendido com uma
  variante de cor nova (primary/violet) para "Serviço"/"Produto".
- Padrão de toggle de 2 botões para escolha binária — análogo às abas,
  reaproveitando a mesma classe condicional (ativo = `bg-primary-600`/
  `dark:bg-violet-600`, inativo = `bg-white border`/`dark:bg-navy-800`).

## Novo padrão desta manutenção

- **Cor "Serviço"** (`primary-100`/`primary-700` light,
  `violet-900/30`/`violet-300` dark) — único token de cor novo,
  documentado acima; não é uma cor nova do design system, é uma
  combinação já usada em outros contextos (é o mesmo par de
  primary/violet do botão de ação) aplicada por extensão a um badge de
  categoria/tipo.

## Mobile-first — checagem em 375px

- Toggle Produto/Serviço no modal: 2 botões `flex-1` cabem lado a lado
  em 375px sem quebrar linha (mesma largura mínima já validada nas abas
  de 2 itens de `Vendas.jsx`).
- Abas Todos/Produtos/Serviços na listagem: 3 abas cabem em 375px sem
  overflow na prática (labels curtas), `overflow-x-auto` garante scroll
  se não couber em telas ainda menores ou com zoom de acessibilidade.
- Grid Preço de Venda + Duração (bloco Serviço): 2 colunas já validadas
  em 375px no bloco Produto existente (mesmo componente `Input`, mesmo
  breakpoint).
- Badge "Serviço"/"Produto" no card mobile: `shrink-0` já usado no badge
  de status existente evita que o badge quebre linha ou comprima o
  nome truncado ao lado.

## Armadilhas evitadas

- ❌ Não criar coluna nova na tabela desktop só para o badge de tipo —
  quebraria alinhamento entre Produto/Serviço e quebraria em telas
  estreitas; badge vai dentro da célula "Nome", mesmo padrão do badge de
  status.
- ❌ Não reaplicar o vermelho de "Sem estoque" ao badge "Serviço" — são
  semânticas diferentes (alerta vs. categoria); usar o par primary/
  violet já documentado.
- ❌ Não remover a célula "Estoque" da tabela/card quando o item é
  Serviço (desalinha linhas entre tipos diferentes) — substituir o
  conteúdo por `—`, manter a célula.
- ❌ Não esconder o toggle Produto/Serviço na edição (ficaria menos claro
  qual é o tipo do item já salvo) — mostrar sempre, só desabilitar
  (`disabled` + estilo de "bloqueado").
- ❌ Não introduzir `CriarCategoriaRapidaModal` no campo de categoria
  financeira — fora de escopo (RN-07), campo é só metadado informativo
  nesta manutenção.

---

## Passagem de bastão

```
✅ Especificação UI concluída — UidCore (Manutenção #91)
   Telas analisadas: 3 (Produtos.jsx — modal + listagem + abas novas;
     PDV FrenteDeCaixa.jsx — dropdown de busca + carrinho; Vendas.jsx —
     BuscaProdutoRapida)
   Componentes reutilizados: 6 existentes (Button, Input, Select, Modal,
     Card, Pagination) + 2 padrões de referência direta (abas de
     Vendas.jsx clonadas para Produtos.jsx; badge pill de status
     estendido com variante "Serviço")
   Novos padrões: 1 token de cor (primary/violet aplicado a badge de
     tipo "Serviço"/"Produto") — nenhum componente novo, nenhuma
     mudança de paleta/tipografia/identidade
   Modo: Padrão Uid (sistema interno já em produção, dark mode
     navy/violet — sem alteração de identidade)

📁 Arquivo: Especificacao_UI_Hotfix.md (em /var/www/uidcore/)

➡️ Loom lê Especificacao_Hotfix.md (Analista) + este arquivo antes de
   implementar o frontend. Nenhum código foi escrito por este agente.
```
