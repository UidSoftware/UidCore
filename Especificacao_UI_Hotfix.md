# Especificação UI Hotfix — UidCore (Manutenção #39)
**Elaborado por:** Brush (MODO HOTFIX)
**Data:** 2026-08-17
**Base:** Especificacao_Hotfix.md (Analista, Manutenção #39 — fix `sessao_atual` + navegação PDV/Caixas)

---

## Escopo desta especificação

Manutenção majoritariamente **sem** peso visual — 2 dos 3 itens são
correção de lógica, sem UI nova:

1. `FrenteDeCaixa.jsx` + `AberturaCaixa.jsx` (+ `FechamentoCaixa.jsx`,
   achado adicional do Analista) — **fora do escopo do Brush**. RF-02,
   RF-03, RF-04 são correção de parsing de resposta HTTP
   (`res.data.sessao` em vez de `res.data`). Zero mudança de layout, zero
   componente novo, zero token novo. Loom implementa direto a partir da
   Especificação técnica — Frontend já detalhada pelo Analista.
2. `Sidebar.jsx` — remoção pura de item de menu (RF-06). Sem substituição
   visual, sem reposicionamento dos itens restantes.
3. `Vendas.jsx` — **único ponto com peso de UI real** (RF-07): dois
   botões novos, "PDV" e "Caixas", visíveis lado a lado. Esta seção é o
   foco do restante deste documento.

---

## Design System do Projeto (referência — lido em tailwind.config.js + Button.jsx + código real)

- Cores primárias: `primary-600` (light) / `violet-600` (dark) — botão
  variant `primary`; `accent-600` usado em toasts de sucesso.
- Cores de fundo: `white`/`gray-50` (light) / `navy-900`/`navy-800`
  (dark, dark mode já configurado via classe `dark`).
- Fonte: Plus Jakarta Sans (headings) + DM Sans (body) — já carregadas
  globalmente, nenhuma ação necessária.
- BorderRadius padrão: `rounded-lg` (botões, cards, inputs).
- Padrão de botão (`components/ui/Button.jsx`): só 3 variantes existem —
  `primary`, `secondary`, `danger`. **Não existe variante `outline` ou
  `ghost`** — não inventar uma nova, usar `secondary` (já é
  outline-like: fundo branco/navy-800 + borda, texto neutro) para não
  competir visualmente com o `primary` já usado no "+ Novo Orcamento" da
  tab Orçamentos.
- Ícones: Lucide React em todo o módulo PDV (`Search`, `Lock`, `Unlock`,
  `ClipboardList`, `AlertTriangle`, `CheckCircle`, etc. — ver
  `pages/pdv/*.jsx`). `Vendas.jsx` já importa `Trash2, Search` de
  `lucide-react` — só adicionar aos imports existentes, não criar novo
  import block.
- Padrão de reaproveitamento de ícone entre botão de entrada e header da
  tela de destino já existe no projeto: `RelatorioSessoesCaixa.jsx`
  usa `ClipboardList` no próprio `<h1>` (linha 311). Reaproveitar o
  mesmo ícone no botão "Caixas" de `Vendas.jsx` mantém a associação
  visual botão → destino.

---

## Especificação Visual por Tela

### `Vendas.jsx` — botões "PDV" e "Caixas"

**Layout geral:**
- Não é uma tela nova nem uma tab nova — dois botões adicionados ao
  header existente do componente principal `Vendas()` (linhas 1017–1050
  do arquivo atual), entre o bloco de título (`<h1>Vendas</h1>` +
  subtítulo) e a linha de tabs Orçamentos/Pedidos.
- Motivo de ficar no header do componente principal (não dentro de
  `OrcamentosTab`/`PedidosTab`, onde vive o botão "+ Novo Orcamento"):
  os botões navegam para fora do módulo Vendas (para `/pdv` e
  `/pdv/sessoes`) e devem estar visíveis **independente da tab ativa**
  — colocar dentro de uma tab violaria a instrução explícita do
  Analista ("não dentro de uma tab específica").
- Novo bloco `<div className="flex items-center gap-2">` inserido logo
  abaixo do bloco de título, acima da linha de tabs:
  ```jsx
  <div className="flex items-center gap-2">
    <Button variant="secondary" size="sm" onClick={() => navigate('/pdv')}>
      <Store size={16} />
      PDV
    </Button>
    <Button variant="secondary" size="sm" onClick={() => navigate('/pdv/sessoes')}>
      <ClipboardList size={16} />
      Caixas
    </Button>
  </div>
  ```
- Padding/espaçamento: `gap-2` entre os dois botões (8px, padrão do
  projeto para grupos de botão — ver `SplitPagamento.jsx`); `mt-2`
  (ou o `space-y-4` já existente no container raiz do componente cobre
  o espaçamento vertical entre este bloco e o título acima / tabs
  abaixo — não é necessário CSS adicional).
- `size="sm"` (não `md`, o padrão do `Button`) — estes são botões de
  navegação secundária, não a ação principal da tela; `size="sm"` os
  diferencia hierarquicamente do "+ Novo Orcamento" (`size` padrão,
  dentro da tab) sem disputar atenção visual com ele.

**Ícones (Lucide React):**
- "PDV" → `<Store size={16} />` — ícone novo neste arquivo, adicionar
  ao import existente: `import { Trash2, Search, Store, ClipboardList } from 'lucide-react'`.
  `Store` não é usado em nenhum outro lugar do projeto ainda — está
  livre e é semanticamente direto (ponto de venda / balcão).
- "Caixas" → `<ClipboardList size={16} />` — reaproveitado do mesmo
  ícone já usado no `<h1>` de `RelatorioSessoesCaixa.jsx` (a tela para a
  qual o botão navega), reforçando a associação visual.
- Tamanho `16px`, consistente com o padrão de ícone-dentro-de-botão já
  usado em `SplitPagamento.jsx`/`CarrinhoItem.jsx` (ícones pequenos
  acompanhando label curto).

**Variante e cor:**
- Ambos os botões usam `variant="secondary"` do `Button.jsx` existente
  — fundo branco/borda cinza no light mode, `navy-800`/borda `navy-500`
  no dark mode (classes já definidas no componente, nenhum token novo).
- Não usar `variant="danger"` nem `variant="primary"` — nenhum dos dois
  é ação destrutiva nem a ação primária da tela (essa continua sendo
  "+ Novo Orcamento"/"+ Novo Pedido" dentro de cada tab).

**Dark mode:**
- 100% herdado do `Button.jsx` (`dark:bg-navy-800 dark:border-navy-500
  dark:text-slate-200 dark:hover:bg-navy-700`) — nenhum ajuste manual
  necessário, os ícones Lucide herdam `currentColor` automaticamente.

**Mobile-first (375px):**
- `flex items-center gap-2` quebra naturalmente se necessário — mas com
  apenas 2 botões `size="sm"` + label curta ("PDV", "Caixas"), cabem
  lado a lado mesmo em 375px sem overflow. Não usar `flex-wrap`
  forçado nem empilhar verticalmente — manter lado a lado em todas as
  larguras, como pedido explicitamente pelo Analista ("dois botões
  distintos e lado a lado").
- Testar visualmente que o bloco de título + botões não ultrapassa a
  largura da viewport em 375px (label + ícone + padding `size="sm"` =
  ~70-80px por botão, folga suficiente).

**Estado/comportamento:**
- Nenhum estado de loading, disabled ou feedback visual adicional —
  `onClick` dispara `navigate()` direto (RN-03: mesma guarda de rota
  `ProtectedRoute` já existente, nenhuma permissão nova).
- Sem tooltip, sem badge, sem contador — apenas navegação direta.

---

### `Sidebar.jsx` — remoção do item "PDV / Caixa"

- Ação puramente de remoção (RF-06): apagar a linha
  `{ to: '/pdv', label: 'PDV / Caixa', icon: '🏪' },` do array
  `navItems`.
- Sem reposicionamento dos itens restantes, sem novo espaçamento — o
  array simplesmente perde um item, o layout do menu se ajusta
  automaticamente (mesmo padrão de lista vertical já existente).
- Nenhuma outra alteração visual no Sidebar.

---

### `FrenteDeCaixa.jsx` / `AberturaCaixa.jsx` / `FechamentoCaixa.jsx`

- **Fora do escopo do Brush** — confirmado pelo Analista: "Sem mudança
  de layout/UX — é puramente correção do parsing da resposta" e
  "Fora do escopo: Qualquer mudança em FrenteDeCaixa.jsx,
  AberturaCaixa.jsx ou FechamentoCaixa.jsx além do parsing de
  res.data.sessao".
- Loom implementa RF-02/RF-03/RF-04 direto da Especificação técnica —
  Frontend do `Especificacao_Hotfix.md`, sem necessidade de spec visual
  adicional.

---

## Componentes reutilizados (nenhum novo)

| Componente | Origem | Uso nesta manutenção |
|---|---|---|
| `Button` (`variant="secondary"`, `size="sm"`) | `components/ui/Button.jsx` | Botões "PDV" e "Caixas" em `Vendas.jsx` |
| `Store` (ícone) | `lucide-react` | Botão "PDV" — primeiro uso no projeto, ícone livre |
| `ClipboardList` (ícone) | `lucide-react`, já usado em `RelatorioSessoesCaixa.jsx` | Botão "Caixas" — reaproveitado do header da tela de destino |

Nenhum componente novo criado. Nenhum token de cor/espaçamento novo
adicionado ao `tailwind.config.js`.

---

## Passagem de bastão

```
✅ Especificação UI concluída — UidCore (Manutenção #39)
   Telas analisadas: 4 (Vendas.jsx com UI real; FrenteDeCaixa.jsx,
   AberturaCaixa.jsx, FechamentoCaixa.jsx confirmadas fora de escopo;
   Sidebar.jsx remoção pura sem UI nova)
   Componentes reutilizados: 1 (Button variant="secondary")
   Ícones novos no projeto: 1 (Store — ClipboardList já existia)
   Novos padrões visuais: 0 — 100% reaproveitamento do design system
   existente

📁 Arquivo: Especificacao_UI_Hotfix.md (neste diretório)

➡️ Loom lê Especificacao_Hotfix.md + Especificacao_UI_Hotfix.md antes
   de implementar o frontend. Forge segue direto pela Especificação
   técnica — Backend do Analista (RF-01/RF-05), sem dependência deste
   documento.
```
