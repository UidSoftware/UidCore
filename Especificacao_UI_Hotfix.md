# Especificação UI Hotfix — UidCore — Manutenção #15 (Módulo PDV)

**Base:** Especificacao_Hotfix.md (Analista, 492 linhas) + design_system.md (Brush, Manutenção #8)
**Modo:** MODO HOTFIX — camada visual sobre spec já aprovada. Nenhuma decisão de model/endpoint/arquitetura de app é tomada aqui (isso é do Blueprint). Este documento assume que o Blueprint resolveu os dois pontos [CONFIRMAR COM BLUEPRINT] da Seção 15 da spec (app `pdv` vs `vendas`; mês de abatimento do estorno no DRE) — nenhum dos dois afeta a UI.

> Nota: este arquivo é regravado a cada manutenção — o conteúdo anterior (relativo
> à Manutenção #14, puramente backend, sem UI) já cumpriu seu papel e está
> preservado no histórico de execuções do `CLAUDE.md` do projeto. Este documento
> passa a refletir apenas a Manutenção #15, em curso.

---

## Design System do Projeto (referência — não redefinido aqui)

- **Tema:** claro (light mode) — `bg-gray-50` app, `bg-gray-900` sidebar. **Não** usar o padrão escuro Uid (#0a0014) — divergência já documentada e aprovada em `design_system.md`.
- **Cor primária:** `primary-600` (#2563eb) / hover `primary-700` (#1d4ed8) — todo botão de ação principal, tab ativa, foco de input.
- **Cor de sucesso:** `accent-600` (#059669) — toast de sucesso, valores de entrada.
- **Cor de erro/perigo:** `red-600` (#dc2626) — toast de erro, botão danger, valores de saída.
- **Fonte:** Plus Jakarta Sans (headings) + DM Sans (body) — **ainda não configurada no projeto** (divergência #1 do design_system.md). Não é bloqueante para o PDV; usar as classes Tailwind de tamanho/peso normalmente, a fonte é herdada do que estiver configurado no `index.html`/`tailwind.config.js` no momento em que o Loom implementar. **Não** importar Inter/Roboto/Arial manualmente em nenhuma tela nova.
- **BorderRadius:** `rounded-lg` (8px) inputs/botões, `rounded-xl` (12px) cards, `rounded-full` badges/pills.
- **Padrão de card:** `bg-white rounded-xl border border-gray-200 shadow-sm`, header `px-6 py-4 border-b border-gray-100`, body `px-6 py-4`.
- **Padrão dual mobile/desktop:** `md:hidden` (cards empilhados) / `hidden md:block` (tabela), breakpoint crítico 768px — usado em Financeiro e Conciliação, replicar 1:1 no PDV.
- ⚠️ **NUNCA** `overflow-hidden` em elemento raiz de tela nova (regra global Uid — o `AppLayout` root já tem essa divergência documentada, não repetir o padrão em telas novas).

---

## Componentes existentes a reutilizar (sem criar nada novo em `components/ui/`)

| Componente | Uso no PDV |
|---|---|
| `Card.jsx` | Container de toda seção: carrinho, resumo de sessão, listas |
| `Button.jsx` (`variant`: primary/secondary/danger) | Todas as ações — ver mapeamento por tela abaixo |
| `Input.jsx` | Busca de produto, campos numéricos (valor, quantidade, contagem física) |
| `Select.jsx` | Seleção de conta, cliente (se não usar autocomplete), forma de pagamento |
| `Modal.jsx` | Sangria/Suprimento, confirmação de cancelamento, devolução parcial, split de pagamento (se não couber inline) |
| `Pagination.jsx` | Histórico de Vendas, Relatório de Sessões |
| `Loading.jsx` | Carregamento inicial de cada tela |
| Toast pattern (inline, `fixed top-4 right-4 z-50`) | Sucesso venda finalizada / erro de API — replicar exatamente o padrão de Financeiro.jsx/Conciliacao.jsx |
| Badge pattern (`<span className="px-2 py-0.5 rounded-full text-xs font-semibold ...">`) | Status de Venda, SessaoCaixa, RecebivelCartao — mapas novos definidos abaixo |
| Padrão `MesColapsavel` (Financeiro.jsx) — card com header clicável + lista expansível | Inspiração para agrupamento por sessão no Relatório de Sessões, se fizer sentido agrupar por dia |

**Nenhum componente novo em `components/ui/` é necessário.** Os padrões visuais específicos de PDV (linha de item de carrinho, chip de forma de pagamento, teclado numérico de contagem) são compostos localmente dentro de cada page, seguindo o mesmo estilo de composição inline já usado em `Financeiro.jsx`/`Conciliacao.jsx` (sub-componentes de função dentro do próprio arquivo de página, não componentes globais).

---

## Mapas de Badge novos (seguir a mesma estrutura de `STATUS_BADGES` de Financeiro.jsx)

```js
// Venda.status
const STATUS_VENDA_BADGES = {
  ABERTA: 'bg-yellow-100 text-yellow-800',
  FINALIZADA: 'bg-green-100 text-green-800',
  CANCELADA: 'bg-gray-100 text-gray-600',
}

// SessaoCaixa.status
const STATUS_SESSAO_BADGES = {
  ABERTA: 'bg-yellow-100 text-yellow-800',
  FECHADA: 'bg-blue-100 text-blue-800',
}

// RecebivelCartao.status
const STATUS_RECEBIVEL_BADGES = {
  PREVISTO: 'bg-yellow-100 text-yellow-800',
  LIQUIDADO: 'bg-green-100 text-green-800',
  CANCELADO: 'bg-gray-100 text-gray-600',
}

// MovimentoCaixa.tipo (chip, não badge de status)
const TIPO_MOVIMENTO_STYLE = {
  SANGRIA: 'bg-red-50 text-red-700',
  SUPRIMENTO: 'bg-green-50 text-green-700',
}
```
Mesma estrutura de `<Badge status={...} />` já usada — não criar componente `Badge.jsx` novo, replicar a função inline como em `Financeiro.jsx`/`Conciliacao.jsx`.

---

## Ícones (Lucide React) — mapeamento completo do módulo PDV

| Ação/Contexto | Ícone | Tamanho | Cor |
|---|---|---|---|
| Abrir caixa | `Unlock` | 20px (botão principal) | branco (dentro de botão primary) |
| Fechar caixa | `Lock` | 16px | — |
| Nova venda / carrinho | `ShoppingCart` | 20px (header), 16px (menu) | — |
| Buscar produto | `Search` | 16px (dentro do Input, `icon` prop se existir, senão posicionado absolute) | text-gray-400 |
| Código de barras | `ScanLine` | 16px (botão/toggle ao lado da busca) | text-gray-500 |
| Adicionar item ao carrinho / incrementar qtd | `Plus` | 14px | — |
| Remover 1 unidade | `Minus` | 14px | — |
| Remover item do carrinho | `Trash2` | 14px | text-red-600 no hover |
| Cliente vinculado | `User` | 16px | — |
| Consumidor final (sem cliente) | `UserX` | 16px | text-gray-400 |
| Sangria (saída de gaveta) | `ArrowDownCircle` | 16px | text-red-600 |
| Suprimento (entrada na gaveta) | `ArrowUpCircle` | 16px | text-green-600 |
| Dinheiro (forma pagamento) | `Banknote` | 20px | text-green-700 |
| PIX | `Zap` | 20px | text-green-600 |
| Cartão débito | `CreditCard` | 20px | text-blue-600 |
| Cartão crédito | `CreditCard` | 20px | text-purple-600 (diferenciar do débito só pela cor, mesmo ícone — já é o padrão do design_system.md para "Cartão") |
| Boleto | `FileText` | 20px | text-blue-600 |
| Outro método | `MoreHorizontal` | 20px | text-gray-500 |
| Finalizar venda | `CheckCircle2` | 16px (dentro do Button) | branco |
| Cancelar venda | `XCircle` | 14px | text-red-600 |
| Devolver item (parcial) | `RotateCcw` | 14px | text-yellow-700 |
| Ver detalhe de venda | `Eye` | 14px | text-gray-500 |
| Diferença de caixa (alerta) | `AlertTriangle` | 16px | text-yellow-600 (diferença) / text-red-600 (diferença negativa alta, a critério do Loom) |
| Contagem física confere | `CheckCircle` | 16px | text-green-600 |
| Filtro de período | `Calendar` | 14px | text-gray-400 |
| Relatório de sessões | `ClipboardList` | 16px (menu) | — |
| Estado vazio (carrinho/histórico) | `PackageSearch` | 32px | text-gray-300 |
| Recebível pendente (Conciliação, RF-17) | `Link2` | 14px | text-primary-600 |

---

## Tela 1 — Abertura de Caixa

**Rota:** `/pdv/abertura` (redireciona para cá automaticamente sempre que o operador tenta acessar `/pdv` sem `SessaoCaixa ABERTA` na conta — RN-02).

**Layout:** tela full-width, sem tabs, foco único — não é um CRUD, é um gate. Card único centralizado, `max-w-md mx-auto` (mesmo espírito do Card de Login: `bg-white rounded-2xl shadow-sm border border-gray-200 p-8`).

```
┌─────────────────────────────────┐
│      🔓 Abrir Caixa              │  ← ícone Unlock 32px text-primary-600, centralizado
│  Selecione a conta e informe o   │  ← subtítulo text-sm text-gray-500
│  valor de abertura               │
│                                   │
│  Conta (Select, tipo=CAIXA)      │
│  [ Selecione...            ▾]    │
│                                   │
│  Valor de abertura (Input)       │
│  [ R$ 0,00                  ]    │  ← input numérico, mesmo padrão de Input.jsx, alinhado à direita, font-mono
│                                   │
│  [    Abrir Caixa (primary)  ]   │  ← full width, ícone Unlock
└─────────────────────────────────┘
```

- Select de conta: popular via `GET /financeiro/contas/?tipo=CAIXA` (reaproveita endpoint já existente, filtrado).
- Se a conta escolhida já tiver `SessaoCaixa ABERTA` (RF-02/RN-01), erro inline abaixo do Select (mesmo padrão de erro de Input: `border-red-500` + mensagem `text-red-600 text-xs`), **não** toast — é erro de validação de formulário, não de rede.
- Se o operador já tem uma `SessaoCaixa ABERTA` própria em outra conta, mostrar aviso informativo (não bloqueante) acima do form: `bg-blue-50 border border-blue-200 text-blue-700 text-sm rounded-lg px-4 py-3` — "Você já tem uma sessão aberta na conta X. Deseja continuar nela?" com botão secundário "Ir para o caixa aberto".
- Botão "Abrir Caixa": `loading` state via `Button.jsx` prop já existente enquanto o POST não retorna.
- Mobile: mesmo layout, card ocupa `w-full` com padding lateral da tela (`px-4`), sem `max-w-md`.

---

## Tela 2 — Frente de Caixa / Nova Venda

**Rota:** `/pdv/venda`

**Layout geral:** duas colunas em desktop (busca+carrinho à esquerda 65%, resumo+pagamento à direita 35%, sticky), empilhado em mobile com **barra de total fixa no rodapé** (padrão comum de PDV/apps de venda — não existe ainda no UidCore, é o único padrão genuinamente novo desta especificação).

### Header da tela
- Título: "Nova Venda" (`text-2xl font-bold text-gray-900`) + badge da sessão ativa ao lado: `Sessão #{id} · {conta.nome} · Aberta às {hora}` em `text-xs text-gray-500`.
- Botão secundário no topo direito (desktop) / ícone no header mobile: `ArrowDownCircle`/`ArrowUpCircle` combinados em um botão "Sangria/Suprimento" que abre o Modal da Tela 3.

### Coluna esquerda — Busca + Carrinho

**Busca de produto:**
- Input com ícone `Search` à esquerda (posicionamento absolute dentro do wrapper, `pl-9` no input), placeholder "Buscar por nome ou código de barras...".
- Botão/ícone `ScanLine` ao lado direito do input — foco automático no input ao clicar, para leitor de código de barras USB (que simula teclado) funcionar sem campo dedicado. Não é um scanner de câmera nesta entrega (fora de escopo, spec não menciona).
- Resultado da busca: dropdown/lista abaixo do input (`absolute z-10 bg-white rounded-lg shadow-lg border border-gray-200 mt-1 max-h-64 overflow-y-auto`), cada linha: nome do produto + `text-xs text-gray-400` com código de barras + preço à direita (`font-mono text-sm`). Clique adiciona ao carrinho.
- Se `quantidade_estoque <= 0`: linha do resultado com opacidade reduzida (`opacity-50`) e badge `bg-red-100 text-red-800` "Sem estoque" — ainda clicável mas o backend vai bloquear (RF-07); mostrar erro extraído da API via toast se acontecer.

**Carrinho (lista de `ItemVenda`):**
- Dentro de `Card` sem título, cada linha (`border-b border-gray-100 last:border-0 py-3`):
  ```
  [Nome do produto]                    [Trash2]
  {qtd} {unidade} × {valor_unitario}    R$ {valor_total}
  [Minus] [qtd editável] [Plus]         (desconto_item, se >0, em text-xs text-gray-400 "- R$ X desconto")
  ```
- Stepper de quantidade: três elementos inline — botão `Minus` (rounded-full w-6 h-6 border border-gray-300), input numérico central (`w-12 text-center text-sm`), botão `Plus` (mesmo estilo do Minus, mas `bg-primary-50 text-primary-600` para diferenciar visualmente incremento de decremento). Editar quantidade direto no input também é permitido (respeitar `max_digits=12, decimal_places=3` do model — usar `step` compatível com a unidade do produto).
- Estado vazio do carrinho: `PackageSearch` 32px + "Carrinho vazio — busque um produto acima" (`text-center py-12 text-gray-400`, mesmo padrão de empty state do design_system.md).

### Coluna direita — Cliente + Resumo + Pagamento (sticky no desktop: `sticky top-4`)

**Cliente (opcional):**
- Chip/linha no topo do Card de resumo: se nenhum cliente selecionado, mostra `UserX` + "Consumidor Final" + botão texto "Vincular cliente" (`text-primary-600 text-sm`). Ao clicar, abre autocomplete inline (reaproveitar o mesmo padrão de busca de `Select` remoto já usado em outras telas, ou um Input com dropdown de resultados igual ao de produto). Cliente vinculado: `User` + nome do cliente + `X` pequeno para desvincular.

**Resumo de valores:**
```
Subtotal            R$ 120,00
Desconto            R$   0,00
─────────────────────────────
Total                R$ 120,00   ← text-lg font-bold, mesmo peso visual do "Valor de KPI" do design system
```

**Split de pagamento (`PagamentoVenda`, RF-09):**
- Grid de "chips" de forma de pagamento (reaproveitar exatamente o grid já documentado no design_system.md: `grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3`, cada chip com ícone 20px + label, igual ao já usado em Pagamentos.jsx) — clicar em uma forma adiciona uma linha de pagamento abaixo.
- Cada linha de pagamento adicionada:
  ```
  [ícone do método] {label}     [Input valor R$]   [X remover]
  ```
- Quando o método selecionado é **Cartão de Crédito**, a linha expande (mesmo padrão de expansão condicional já usado em Conciliação/Padrões Seguros — campo aparece/some conforme tipo) mostrando dois campos extras inline, menores (`text-xs`, `w-24`):
  ```
  Taxa (%) [Input]     Prazo (dias) [Input]
  ```
  Se RF-18 (Could) não estiver implementado ainda, esses campos vêm vazios/zerados por padrão — sem pré-preenchimento, o operador digita manualmente (RF-14 Must = seleção manual).
- Soma das linhas de pagamento deve bater com o Total — mostrar diferença em tempo real abaixo do split: `Falta alocar: R$ X` (`text-yellow-700 text-xs`) ou `Troco: R$ X` (`text-green-700 text-xs`, quando forma = Dinheiro e valor pago > total) ou nada quando bate exato. **Não bloquear** visualmente o botão Finalizar por isso — deixar a validação de "soma = total" para a resposta de erro da API, mesmo padrão de erro tratado por toast já usado no resto do sistema.

**Botão Finalizar Venda:**
- `Button variant="primary" size="lg"` full width, ícone `CheckCircle2`, texto "Finalizar Venda — R$ {total}".
- Desktop: fixo dentro da coluna direita (sticky).
- **Mobile: barra fixa no rodapé da tela** (`fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 p-4 z-40`, safe-area considerada) mostrando total + botão — padrão necessário porque em telas pequenas o resumo/split fica scrollado para baixo do carrinho; sem essa barra fixa o operador perde o botão de ação principal fora da viewport (viola o princípio "Ação principal sempre visível" do CLAUDE.md/manual do Brush). Isso não é `overflow-hidden` no root, é um elemento `fixed` — não conflita com a regra de overflow.

**Após finalizar com sucesso:** toast de sucesso (padrão `bg-accent-600`) + limpar carrinho + manter o operador na mesma tela pronta para a próxima venda (não navegar embora — fluxo de PDV é venda após venda na mesma sessão).

---

## Tela 3 — Sangria / Suprimento (Modal)

**Componente:** `Modal.jsx` (`maxW="max-w-md"`, o menor tamanho já catalogado — é um form rápido, RF-10).

```
┌───────────────────────────────┐
│  Sangria / Suprimento      [X] │
│                                 │
│  Tipo                          │
│  ( ) Sangria  ( ) Suprimento    │  ← toggle de dois botões pill, não Select — reduz 1 clique num fluxo que precisa ser rápido no balcão
│                                 │
│  Valor (Input, obrigatório)    │
│  [ R$ 0,00               ]     │
│                                 │
│  Motivo (obrigatório)          │
│  [ textarea rows=2         ]   │
│                                 │
│  [Cancelar]      [Confirmar]   │
└───────────────────────────────┘
```
- Toggle Tipo: dois botões lado a lado (`grid grid-cols-2 gap-2`), estilo pill igual ao das Tabs principais, cor por tipo quando selecionado: Sangria selecionada = `bg-red-50 border-red-300 text-red-700` + ícone `ArrowDownCircle`; Suprimento selecionada = `bg-green-50 border-green-300 text-green-700` + ícone `ArrowUpCircle`. Não selecionado = `bg-white border-gray-300 text-gray-600`.
- Motivo obrigatório — usar a mesma validação visual de campo obrigatório do `Input.jsx` (border vermelho + mensagem) se o operador tentar confirmar vazio.
- Botão "Confirmar": `variant="primary"` mas cor do texto/ícone acompanha o tipo escolhido — se quiser simplificar, manter sempre `primary-600` e deixar a cor semântica só no toggle (recomendado, evita um terceiro estado de botão custom).
- Acesso: ícone no header da Tela 2 (Frente de Caixa) e, opcionalmente, atalho na Tela 4 (Fechamento) antes de fechar — mas o fluxo principal é durante a sessão aberta, a partir da Frente de Caixa.

---

## Tela 4 — Fechamento de Caixa

**Rota:** `/pdv/fechamento`

**Layout:** Card único (`max-w-2xl mx-auto` desktop, full width mobile), sem tabs — fluxo linear de conferência antes de confirmar (RF-11).

```
┌──────────────────────────────────────────┐
│  Fechar Caixa — Sessão #{id}              │
│  {conta.nome} · aberta em {data/hora}     │
│                                            │
│  Resumo da sessão                         │
│  ┌──────────┬──────────┬──────────┬─────┐ │
│  │ Abertura │ Vendas   │ Sangrias │ Supr│ │  ← 4 KPI Cards, grid grid-cols-2 md:grid-cols-4 gap-3
│  │ R$ X     │ R$ X     │ -R$ X    │+R$X │ │     (mesmo componente KpiCard já documentado no design_system.md)
│  └──────────┴──────────┴──────────┴─────┘ │
│                                            │
│  Vendas por forma de pagamento            │
│  Dinheiro   R$ X                          │  ← lista simples, label + valor à direita font-mono
│  PIX        R$ X                          │
│  Cartão Déb R$ X                          │
│  Cartão Créd R$ X (pendente de liquidação)│  ← nota text-xs text-gray-400, pois cartão crédito não entra no "dinheiro em caixa"
│                                            │
│  Valor calculado em caixa    R$ X         │  ← text-lg font-bold (só considera dinheiro físico: abertura + vendas dinheiro - sangrias + suprimentos)
│                                            │
│  Contagem física (Input, obrigatório)     │
│  [ R$ 0,00                          ]     │
│                                            │
│  Diferença: R$ X   [AlertTriangle se ≠ 0] │  ← calculada em tempo real no frontend conforme o operador digita, cor: text-gray-600 se =0, text-yellow-700 se diferença pequena, text-red-700 se diferença grande (limiar a critério do Loom, ex. >5% do calculado — não é regra de negócio da spec, é só destaque visual)
│                                            │
│  Observações (textarea opcional)          │
│                                            │
│  [Cancelar]           [Fechar Caixa]      │
└──────────────────────────────────────────┘
```
- **RN-07 é explícito na UI:** o botão "Fechar Caixa" **nunca** fica desabilitado por causa da diferença — nenhuma validação de frontend bloqueia o submit por `diferenca != 0`. Mostrar o alerta visual (`AlertTriangle` + cor) é só informativo, reforçando a regra "fechamento nunca trava" já determinada pelo Analista.
- Após confirmar: toast de sucesso + redireciona para Tela 1 (Abertura) ou Dashboard, já que a sessão foi encerrada e não há mais o que fazer no PDV até abrir outra.
- Mobile: mesmo conteúdo em coluna única, KPI cards em `grid-cols-2` (padrão já existente).

---

## Tela 5 — Histórico de Vendas

**Rota:** `/pdv/vendas`

**Layout:** segue **exatamente** o padrão de `Conciliacao.jsx`/`Financeiro.jsx` — filtros no topo, lista dual mobile/desktop, paginação.

### Barra de filtros
```
flex flex-wrap gap-3 items-end
[Período: De    ] [Período: Até   ] [Operador ▾] [Status ▾]   [Limpar filtros]
```
- Cada filtro: label acima (`text-xs text-gray-500 mb-1`) + Input/Select abaixo — mesmo padrão descrito no manual do Brush.
- Botão "Limpar filtros" só aparece quando algum filtro está ativo (`bg-white border border-gray-300 text-gray-600 hover:bg-gray-50`, tradução do padrão do manual para o vocabulário Tailwind já usado no projeto).
- Status options: `[Todas, Aberta, Finalizada, Cancelada]` usando `STATUS_VENDA_BADGES`.

### Lista (desktop = tabela dentro de Card, mobile = cards empilhados — padrão dual já catalogado)

**Colunas da tabela:**
| Número | Data/Hora | Operador | Cliente | Formas de Pgto | Total | Status | Ações |
|---|---|---|---|---|---|---|---|
- Formas de Pgto: mini-ícones inline (não texto) — ex. `Banknote` + `Zap` lado a lado se a venda teve split dinheiro+PIX, `title` tooltip com o valor de cada.
- Total: `font-mono`, riscado (`line-through opacity-50`, mesmo padrão já usado para linha estornada no design_system.md) se `status=CANCELADA`.
- Ações: ícone `Eye` (ver detalhe) sempre; ícone `XCircle` (cancelar) só se `status=FINALIZADA` e usuário tiver permissão; nenhuma ação de devolução na linha da tabela — devolução por item fica dentro do **detalhe** (modal ou tela expandida), não faz sentido na linha resumida.

### Modal/painel de Detalhe de Venda
Abrir em `Modal.jsx` `maxW="max-w-2xl"` (ou navegação para `/pdv/vendas/{id}`, a critério do Loom — recomendo Modal para não sair do contexto de lista):
```
Venda #{numero} — {status badge}
{cliente || 'Consumidor Final'} · {operador} · {data/hora}

Itens
┌─────────────────────────────────────────────┐
│ Produto A   3un × R$10,00   R$30,00  [RotateCcw]│  ← ícone devolver por item, some se quantidade_estornada == quantidade
│ Produto B   1un × R$50,00   R$50,00  [RotateCcw]│
└─────────────────────────────────────────────┘

Pagamentos
Dinheiro  R$ 40,00
PIX       R$ 40,00

Total: R$ 80,00

[Cancelar Venda]  (só se ABERTA/FINALIZADA — RF-12, confirma via window.confirm() como já é padrão no projeto)
```
- Clicar `RotateCcw` num item abre um segundo modal pequeno (ou expande inline) com: quantidade a devolver (`Input` numérico, `max` = `quantidade - quantidade_estornada`, pré-preenchido com o restante) + motivo (obrigatório) + botão "Confirmar Devolução". Mesmo padrão de confirmação de ações sensíveis: `window.confirm()` antes de submeter, igual ao resto do projeto (não criar um Modal de confirmação novo, seguir o padrão existente documentado em "Padrões consolidados" do design_system.md).
- Item com `quantidade_estornada > 0` mas não totalmente devolvido: mostrar badge pequena `bg-yellow-50 text-yellow-700` "Parcialmente devolvido ({quantidade_estornada}un)" abaixo do nome do produto.
- Cancelamento de venda inteira: usar `window.confirm('Cancelar esta venda? Todo o estoque será revertido e os pagamentos estornados.')` — mesmo padrão já catalogado ("window.confirm() para ações destrutivas — simples e funcional").

---

## Tela 6 — Relatório de Sessões de Caixa (IsAdmin only)

**Rota:** `/pdv/sessoes` — item de menu só visível se `user.is_staff` (mesmo padrão de proteção de rota já usado no projeto para telas admin-only — reaproveitar o mecanismo existente de guard de rota/menu condicional, não criar um novo).

**Layout:** mesma estrutura dual tabela/cards.

**Filtros:** período + operador + conta.

**Colunas:**
| Sessão | Conta | Operador | Abertura | Fechamento | Valor Abertura | Valor Calculado | Contagem Física | Diferença | Status |
|---|---|---|---|---|---|---|---|---|---|

- Coluna Diferença: `text-green-700` se `= 0`, `text-red-700` com ícone `AlertTriangle` 14px inline se `≠ 0` — é a coluna de auditoria, deve saltar aos olhos visualmente (RF-16 existe justamente para achar diferença recorrente por operador).
- Ordenação padrão: mais recente primeiro (`-data_abertura`), mesmo padrão de `ordering` já usado nos outros módulos.
- Clique na linha abre detalhe (Modal) com o mesmo resumo por forma de pagamento já usado na Tela 4 (Fechamento) — reaproveitar o mesmo sub-componente de resumo entre as duas telas, se o Loom organizar como função compartilhada dentro do módulo PDV (`ResumoSessao({ sessao })`, por exemplo) em vez de duplicar o JSX.

---

## Tela 7 (Should — RF-14/RF-18) — Configuração Método de Pagamento → Conta / Taxa padrão

Fora do escopo Must desta especificação visual detalhada — se o Blueprint/Forge decidir implementar já (RF-14 parte Should), a tela é um CRUD simples e **deve reutilizar `ResourceCrud.jsx` diretamente**, sem tela custom: schema com colunas `metodo` (Select), `conta_padrao` (Select remoto de Contas), `taxa_percentual` (number, só relevante para Cartão Crédito). Mesmo padrão já usado em outros cadastros simples do sistema (ex. Metodos de pagamento em Pagamentos.jsx). Não desenhar layout novo para isso — é o caso de uso exato para o qual `ResourceCrud` existe.

---

## Menu / Navegação

- Adicionar item "PDV" na Sidebar, entre "Vendas" e "Financeiro" (agrupa proximidade de domínio — venda de balcão é irmã de Orçamento/Pedido, e alimenta o Financeiro).
- Ícone: `ShoppingCart` — **se o Loom migrar a Sidebar para Lucide nesta manutenção** (divergência #4 do design_system.md, não obrigatória aqui); caso a Sidebar continue em emoji por ora, usar 🛍️ ou 💵 seguindo o mesmo padrão emoji dos demais itens, **não misturar emoji e Lucide dentro do mesmo componente Sidebar** — decisão binária, não parcial.
- Submenu (se a Sidebar suportar submenu — senão, rotas internas por tab dentro da própria página `/pdv`): Nova Venda, Histórico, Sessões (admin only), Abertura/Fechamento acessíveis contextualmente (não precisam de item de menu próprio — Abertura aparece como redirect automático, Fechamento como botão dentro da tela de venda).

---

## Mobile-first — resumo transversal

- Breakpoint crítico: 768px (`md:`), igual ao resto do sistema.
- Frente de Caixa é a única tela com necessidade genuinamente nova de mobile (barra de total fixa no rodapé) — todas as outras seguem o padrão dual já estabelecido sem novidade.
- Testar sempre em 375px (iPhone SE) antes de considerar pronto — regra padrão do Brush.
- Grid de formas de pagamento: `grid-cols-2` em mobile (cabe 2 chips por linha confortavelmente), `sm:grid-cols-3 lg:grid-cols-4` conforme cresce a tela — mesmo grid já catalogado no design_system.md para "Metodos de pagamento".

---

## O que NÃO foi definido aqui (propositalmente)

- Nome final do app Django/estrutura de pastas do frontend (`pages/Pdv.jsx` único com tabs internas, ou pasta `pages/pdv/` com múltiplos arquivos) — decisão de organização de código, não de UI, fica com Loom seguindo o padrão que achar mais consistente com o resto do projeto (os módulos maiores como Financeiro/Conciliação usam um arquivo por página com tabs internas — recomendo o mesmo aqui, mas não é uma regra visual).
- Payload exato dos endpoints, nomes de campos JSON — contrato de API é do Blueprint/Forge.
- Regra de negócio de UX da devolução com split rateado entre formas de pagamento (Seção 5.6 da spec, item 4, marcado "UX a decidir com Loom/Blueprint") — **recomendação do Brush:** UI simples, deixa o operador escolher de qual `PagamentoVenda` da venda a devolução deve sair (dropdown das formas de pagamento daquela venda específica, pré-selecionado o primeiro), API valida se o valor cabe; não implementar rateio automático complexo na v1 — reduz a superfície de erro e é consistente com o princípio "menos é mais" do Brush.

---

## Passagem de bastão

```
✅ Especificação UI concluída — UidCore (Manutenção #15 — Módulo PDV)
   Telas analisadas: 6 Must + 1 Should (config)
   Componentes reutilizados: Card, Button, Input, Select, Modal, Pagination,
     Loading, padrão de Toast, padrão de Badge, padrão dual mobile/desktop,
     ResourceCrud (tela 7)
   Novos padrões: barra de total fixa no rodapé mobile (Frente de Caixa),
     grid de chips de forma de pagamento com expansão condicional (cartão
     crédito), toggle pill de 2 opções (Sangria/Suprimento)

📁 Arquivo: Especificacao_UI_Hotfix.md (em /var/www/uidcore/)

➡️ Loom lê Especificacao_Hotfix.md + Especificacao_UI_Hotfix.md
   antes de implementar o frontend do módulo PDV
```
