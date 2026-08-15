# Especificação UI Hotfix — UidCore (Manutenção #32, revisão 2)

**Elaborado por:** Brush (MODO HOTFIX)
**Data:** 2026-08-15
**Baseado em:** `Especificacao_Hotfix.md` (Analista, revisão 2) + leitura de
`frontend/src/pages/pdv/FrenteDeCaixa.jsx` (referência visual) e
`frontend/src/pages/Vendas.jsx` (arquivo a alterar)

> Nota: este arquivo é regravado a cada manutenção (padrão já estabelecido nas
> Manutenções #21 e #14 "Dark Mode") — o conteúdo anterior (dark mode) está
> preservado no histórico do `CLAUDE.md` do projeto e no git history. Este
> documento passa a refletir apenas a entrega desta manutenção (busca rápida de
> produto em Orçamento/Pedido, igual ao PDV).

```
❌ NÃO criar design system novo
❌ NÃO mudar paleta/tipografia — usa exatamente navy-*/violet-*/red-* já em produção
❌ NÃO implementar código — isso é do Loom
✅ Apenas especifica a camada visual do BuscaProdutoRapida por cima do que já existe
```

---

## Design System do Projeto (referência)

- **Cores primárias (light):** `primary-500`/`primary-600` — usadas em foco de input,
  links, botão principal.
- **Cores primárias (dark):** paleta `navy-*` (superfícies: `navy-900`, `navy-800`,
  `navy-700`, `navy-600`, `navy-500`) + `violet-*` (interação: `violet-400`,
  `violet-500`, `violet-600`) — confirmado em uso real em `Vendas.jsx` e
  `FrenteDeCaixa.jsx`, manter exatamente os mesmos tokens, não introduzir cor nova.
- **Feedback:** vermelho (`red-100`/`red-800`/`red-900/30`/`red-300`) para "sem
  estoque"; não usar verde/âmbar aqui (reservados aos badges de status de
  Orçamento/Pedido, componente diferente).
- **Fonte:** Plus Jakarta Sans (headings) + DM Sans (corpo) — já importadas
  globalmente, nenhuma ação necessária no componente novo.
- **BorderRadius padrão:** `rounded-lg` (8px) em inputs/dropdowns/cards internos de
  formulário, `rounded-xl` (12px) reservado a blocos de página cheia (ex: bloco de
  busca do PDV, que vive fora de modal). Dentro do modal (`SecaoItens`), usar
  `rounded-lg`, igual ao restante do formulário de item.
- **Padrão de card:** `bg-white border border-gray-200 shadow-sm dark:bg-navy-800
  dark:border-navy-600 dark:shadow-none` para blocos elevados; `bg-gray-50
  dark:bg-navy-900/50` para contêineres de agrupamento (é o que `SecaoItens` já usa e
  continua usando, sem alteração).

---

## Contexto: por que este componente existe

RF-02/RF-03 da `Especificacao_Hotfix.md`: hoje, para vincular um produto a um
orçamento/pedido, o usuário precisa clicar em "+ Adicionar Item" primeiro para abrir
uma linha vazia, e só então buscar dentro dela. No PDV (`FrenteDeCaixa.jsx`), a busca é
o primeiro passo — um campo sempre visível no topo, e clicar num resultado já cria o
item. Esta especificação define o novo componente `BuscaProdutoRapida` dentro de
`SecaoItens`, espelhando o padrão visual e comportamental do PDV — sem duplicar seu
código-fonte (arquivo diferente), sem debitar estoque, sem os atalhos de câmera/scanner
físico exclusivos do PDV (fora de escopo, ver `Especificacao_Hotfix.md`, seção "Fora do
escopo").

**Diferença de contexto crítica vs PDV:** o campo de busca do PDV vive numa página
inteira, fora de qualquer ancestral com `overflow`. O `BuscaProdutoRapida` novo vive
**dentro do `<Modal>`** (`Novo Orçamento` / `Novo Pedido`), cujo conteúdo já é
`overflow-y-auto` — o mesmo tipo de clipping que motivou o fix `position: fixed` do
`ProdutoAutocomplete` (RF-01 desta manutenção, comentários `Fix M32` nas linhas 59-70 e
165 de `Vendas.jsx`). O dropdown do `BuscaProdutoRapida` **precisa do mesmo
tratamento** — detalhado abaixo.

---

## Especificação Visual do Componente

### `BuscaProdutoRapida` (novo, dentro de `SecaoItens`)

**Onde entra no JSX de `SecaoItens` (`Vendas.jsx`, função nas linhas 189-337 hoje):**
logo abaixo da linha do cabeçalho (`<h3>Itens</h3>` + botão `+ Adicionar Item`,
linhas 250-259), acima do bloco `itens.length === 0 && ...` / `itens.map(...)`
(linhas 261-328). Fica **dentro** do container `bg-gray-50 ... p-4` que `SecaoItens`
já renderiza — não é um wrapper de página nova, é um componente interno do formulário.

```
SecaoItens
├── header: "Itens" + "+ Adicionar Item"
├── BuscaProdutoRapida  ← NOVO, aqui
├── lista de itens (itens.map)
└── Total Geral
```

**Layout do campo:**
```jsx
<div className="relative mb-3">
  <div className="relative">
    <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 dark:text-slate-500 pointer-events-none" />
    <input
      ref={buscaRapidaRef}
      type="text"
      value={buscaRapida}
      onChange={(e) => setBuscaRapida(e.target.value)}
      placeholder="Buscar produto para adicionar..."
      className="w-full rounded-lg border border-gray-300 bg-white pl-9 pr-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent dark:border-navy-500 dark:bg-navy-800 dark:text-slate-100 dark:placeholder-slate-500 dark:focus:ring-violet-500"
      autoComplete="off"
    />
  </div>
  {/* dropdown — ver abaixo */}
</div>
```

- Reutilizar **exatamente** as classes de input já usadas em `ProdutoAutocomplete`
  (linha 159 de `Vendas.jsx`) e no campo de busca do PDV (linha 398 de
  `FrenteDeCaixa.jsx`) — mesmo `border-gray-300`/`dark:border-navy-500`,
  `focus:ring-primary-500`/`dark:focus:ring-violet-500`. Não criar variação nova.
- **Ícone:** `Search` (lucide-react), 16px, posicionado absolute à esquerda dentro do
  input (`left-3 top-1/2 -translate-y-1/2`), cor `text-gray-400 dark:text-slate-500`
  — mesmo padrão do PDV. **Não** incluir os botões `ScanLine`/`Camera` do PDV (fora de
  escopo — RF-06 é Could e cobre apenas Enter + `codigo_barras`, não UI de câmera).
- **Placeholder:** `"Buscar produto para adicionar..."` — distinto do placeholder do
  autocomplete de linha (`"Buscar produto..."`, mantido como está) para deixar claro
  que este campo novo adiciona a linha automaticamente.
- **Margem inferior:** `mb-3` no wrapper — mesmo respiro usado hoje entre o header de
  Itens e a lista.

### Dropdown de resultados

**Estrutura visual — espelha o dropdown do PDV (linhas 420-452 de
`FrenteDeCaixa.jsx`), com uma mudança obrigatória de posicionamento (ver seção
seguinte):**

```jsx
{(resultadosRapida.length > 0 || buscandoRapida) && (
  <div
    style={dropdownStyleRapida}   // position: fixed — ver "Posicionamento" abaixo
    className="bg-white rounded-lg shadow-lg border border-gray-200 max-h-64 overflow-y-auto dark:bg-navy-800 dark:border-navy-600 dark:shadow-none"
  >
    {buscandoRapida && (
      <div className="px-4 py-3 text-sm text-gray-400 dark:text-slate-500 text-center">Buscando...</div>
    )}
    {!buscandoRapida && resultadosRapida.map((p) => (
      <button
        key={p.id}
        type="button"
        onMouseDown={() => handleAdicionarRapido(p)}   // onMouseDown, não onClick — evita blur/close antes do clique registrar (mesmo padrão do ProdutoAutocomplete, linha 175)
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-gray-50 border-b border-gray-100 last:border-0 text-left transition-colors dark:hover:bg-navy-700 dark:border-navy-700"
      >
        <div className={parseFloat(p.quantidade_estoque || 0) <= 0 ? 'opacity-50' : ''}>
          <p className="text-sm font-medium text-gray-900 dark:text-slate-100">{p.nome}</p>
          {p.codigo_barras && (
            <p className="text-xs text-gray-400 dark:text-slate-500">{p.codigo_barras}</p>
          )}
        </div>
        <div className="text-right shrink-0 ml-3">
          <p className="text-sm font-mono font-medium text-gray-900 dark:text-slate-100">{BRL(p.preco_venda)}</p>
          {parseFloat(p.quantidade_estoque || 0) <= 0 ? (
            <span className="px-1.5 py-0.5 rounded-full text-xs font-semibold bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300">
              Sem estoque
            </span>
          ) : (
            <p className="text-xs text-gray-400 dark:text-slate-500">{p.quantidade_estoque} {p.unidade_base}</p>
          )}
        </div>
      </button>
    ))}
  </div>
)}
```

- **Campos exibidos por resultado:** nome (esquerda, `text-sm font-medium`),
  `codigo_barras` opcional abaixo em `text-xs text-gray-400`; preço via `BRL()` já
  existente no topo de `Vendas.jsx` (linha 35-36 — reaproveitar, não duplicar) à
  direita em `font-mono`; badge/texto de estoque abaixo do preço.
- **Badge "Sem estoque":** só aparece quando `quantidade_estoque <= 0`. Classes exatas
  (copiadas do PDV): `px-1.5 py-0.5 rounded-full text-xs font-semibold bg-red-100
  text-red-800 dark:bg-red-900/30 dark:text-red-300`. O bloco nome+código do produto
  ganha `opacity-50` quando sem estoque (mesmo efeito visual do PDV). **Importante:**
  diferente do PDV, aqui isso é só indicativo — **não bloqueia o clique** (RF-02 da
  Especificação: Orçamento/Pedido são documentos comerciais, não debitam estoque).
- **Quando há estoque:** mostrar `{quantidade_estoque} {unidade_base}` em
  `text-xs text-gray-400 dark:text-slate-500`, sem badge colorido — mesmo padrão PDV.
- **Estado "Buscando...":** texto centralizado `px-4 py-3 text-sm text-gray-400
  dark:text-slate-500 text-center`, mesmo do PDV.
- **Sem estado vazio explícito** ("nenhum resultado") especificado no PDV nem exigido
  pela Especificação — manter o mesmo comportamento (dropdown simplesmente não abre se
  `resultadosRapida.length === 0 && !buscandoRapida`).

### Posicionamento do dropdown — `position: fixed` obrigatório

O PDV usa `absolute` porque o campo de busca não está dentro de nenhum ancestral com
`overflow`. Aqui, `SecaoItens` renderiza **dentro de `<Modal>`**
(`frontend/src/components/ui/Modal.jsx`), cujo conteúdo é `overflow-y-auto` — um
dropdown `absolute` seria cortado do mesmo jeito que o `ProdutoAutocomplete` era antes
do RF-01. **Reaproveitar a técnica já validada em `ProdutoAutocomplete`** (linhas
59-86 e 165-169 de `Vendas.jsx`, comentários `Fix M32`):

- `inputRef` (`buscaRapidaRef`) no `<input>`; `calcularPosicaoRapida()` via
  `getBoundingClientRect()` → `{ position: 'fixed', top: rect.bottom + 4,
  left: rect.left, width: rect.width, zIndex: 9999 }`.
- Recalcular ao abrir o dropdown (resultado não vazio) e em `scroll`/`resize` da
  janela enquanto aberto (mesmos listeners do `ProdutoAutocomplete`, `{ capture: true
  }` no scroll).
- Fechar ao clicar fora (`mousedown` fora do wrapper) — mesmo padrão.

Isso não é uma escolha estética — é a mesma correção de bug que RF-01 já exigiu para o
autocomplete de linha, aplicada agora ao campo novo. Sem isso, `BuscaProdutoRapida`
nasce com o mesmo bug que esta manutenção já está corrigindo em outro lugar do mesmo
arquivo.

### Comportamento de busca (resumo do RF-02/RF-06 para o Loom implementar)

- Debounce 300ms.
- **Sem mínimo de caracteres** (dispara com 1+ caractere) — diferente do
  `ProdutoAutocomplete` de linha, que mantém 2+ (não alterar o de linha).
  `GET /api/v1/produtos/?search=<termo>&page_size=10`.
- Ao selecionar (`onMouseDown` no resultado): limpar o campo (`setBuscaRapida('')`),
  fechar o dropdown, e chamar `adicionarItemComProduto(produto)` em `SecaoItens` —
  objeto conforme RF-03 da Especificação (produto, produto_nome, descricao, quantidade
  1, valor_unitario, valor_total).
- RF-06 (Could): Enter com match exato de `codigo_barras` — mesmo padrão de
  `handleBuscaKeyDown` do PDV (linhas 184-214 de `FrenteDeCaixa.jsx`), sem UI
  adicional (é comportamento de teclado no mesmo input, não um elemento visual novo).

---

## Ícones (lucide-react)

| Uso | Ícone | Tamanho |
|---|---|---|
| Campo de busca novo (`BuscaProdutoRapida`) | `<Search />` | 16px |
| Remover item de linha (já existe, não alterar) | `<Trash2 />` | 14px |

Não introduzir `ScanLine`/`Camera`/`PackageSearch` neste componente — são específicos
do fluxo de PDV (leitor físico e câmera), fora do escopo desta manutenção.

---

## Layout Mobile-first

- Breakpoint de referência: 375px.
- O campo `BuscaProdutoRapida` já é `w-full` por padrão — nenhuma adaptação de largura
  necessária entre mobile e desktop, pois vive dentro do `Modal` que já é responsivo
  (`maxW="max-w-2xl"`, ocupa a largura disponível em telas pequenas).
- Dropdown: `max-h-64 overflow-y-auto` evita que a lista de resultados estoure a
  viewport em telas pequenas; como usa `position: fixed` calculado por
  `getBoundingClientRect()`, a largura (`width: rect.width`) acompanha a largura real
  do input em qualquer breakpoint — não precisa de classes responsivas adicionais.
- Cada item do dropdown mantém `flex items-center justify-between` (nome à esquerda,
  preço/estoque à direita) mesmo em mobile — padrão já validado no PDV, que é
  mobile-first por natureza (barra fixa inferior etc.).
- Não é necessário empilhar nome/preço verticalmente em telas pequenas — o padrão do
  PDV já cabe em 375px com truncamento natural do texto (nenhuma alteração adicional
  requerida).

---

## Componentes/tokens existentes a reutilizar (não recriar)

- `BRL()` — já definido no topo de `Vendas.jsx` (linha 35-36).
- Classes de input de busca — copiar de `ProdutoAutocomplete` (linha 159) /
  `FrenteDeCaixa.jsx` (linha 398), não inventar variação.
- Classes de dropdown/resultado — copiar de `FrenteDeCaixa.jsx` (linhas 420-452),
  ajustando apenas `onClick`→`onMouseDown` e o posicionamento (`fixed` calculado, não
  `absolute` fixo).
- Técnica de posicionamento `fixed` — copiar de `ProdutoAutocomplete` (`Fix M32`,
  linhas 59-86, 165-169), não reescrever do zero.
- `Modal`, `Card`, `Button`, `Input`, `Select` — nenhuma alteração necessária nesses
  componentes de UI base.

---

## O que NÃO fazer (reforço)

```
❌ Não criar paleta de cor nova — usar apenas navy-*/violet-*/red-* já em uso
❌ Não usar rounded-xl dentro do modal — é rounded-lg, igual ao resto do formulário
❌ Não copiar os botões ScanLine/Camera do PDV — fora de escopo
❌ Não usar position: absolute no dropdown novo — precisa de fixed (mesmo motivo do RF-01)
❌ Não bloquear o clique em produto sem estoque — é só indicativo aqui (ver "Fora do escopo" na Especificacao_Hotfix.md)
❌ Não alterar o placeholder/comportamento do ProdutoAutocomplete de linha existente (2+ caracteres, RF-05 preservado)
```

---

## Passagem de bastão

```
✅ Especificação UI concluída — UidCore (Manutenção #32)
   Telas analisadas: 1 (SecaoItens, dentro dos modais Novo Orçamento / Novo Pedido em Vendas.jsx)
   Componentes reutilizados: BRL(), classes de input/dropdown do PDV, técnica de
   position:fixed do ProdutoAutocomplete (Fix M32), Modal/Card/Button existentes
   Novos padrões: 1 (BuscaProdutoRapida — campo de busca rápida com dropdown fixed)

📁 Arquivo: Especificacao_UI_Hotfix.md (em /var/www/uidcore/)

➡️ Loom lê Especificacao_Hotfix.md + Especificacao_UI_Hotfix.md
   antes de implementar o frontend
```
