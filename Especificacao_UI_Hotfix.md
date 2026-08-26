# Especificação UI Hotfix — UidCore (OS #7)

**Manutenção #54 — Módulo Marketing (Campanhas + Leads + ROI/CAC)**

Data: 2026-08-25
Baseado em: `Especificacao_Hotfix.md` (Analista, Manutenção #54)

---

## Design System do Projeto (referência)

- **Modo:** Padrão Uid — dark mode como default (Manutenção #31), sem marca própria de cliente
- **Cores primárias:** `violet-500`/`violet-600` (ação, botões primários, foco de input), `navy-950/900/800/700/600` (superfícies, do fundo ao elemento mais elevado)
- **Cores de fundo:** `bg-white` / `dark:bg-navy-800` (cards), `dark:bg-navy-900` (fundo de página/footer de card)
- **Bordas:** `border-gray-200` / `dark:border-navy-600` (cards), `dark:border-navy-700` (divisores internos)
- **Fonte:** Plus Jakarta Sans (títulos) + DM Sans (corpo) — já globais, nenhuma ação nova
- **BorderRadius padrão:** `rounded-xl` (cards), `rounded-full` (badges de status)
- **Padrão de card:** `Card.jsx` existente — título opcional no header (`border-b`), conteúdo em `px-6 py-4`, footer opcional com fundo levemente distinto
- **Padrão de badge de status:** `span` inline com `text-xs rounded-full px-2 py-0.5 font-semibold` + par de classes `bg-*-100 text-*-700` (light) / `dark:bg-*-900/30 dark:text-*-300` (dark), mapeado por um objeto `STATUS_BADGES` local ao componente — **não existe** componente `Badge.jsx` dedicado no projeto, o padrão é esse span inline (ver `Vendas.jsx` linhas 645-651, 680-682). Seguir o mesmo padrão em Marketing, não criar `Badge.jsx` novo.
- **Ícones:** Lucide React em toda a aplicação, **exceto Sidebar**, que usa emojis — padrão de fábrica documentado (DIV-UI03) e reforçado no RF06 desta manutenção (ícone `📣`)
- **Mobile-first:** grid responsivo (`grid-cols-1 md:grid-cols-2 lg:grid-cols-3` etc.), padrão já usado em Vendas.jsx/Produtos.jsx

---

## Especificação Visual por Tela

### 1. Campanhas (`/marketing/campanhas`)

**Layout geral:**
- Full-page list, mesmo padrão estrutural de `Vendas.jsx` (Orçamentos/Pedidos): header com título + botão de ação à direita, barra de filtros, grid de cards (não tabela — cards carregam mais informação por item: canal, status, datas, orçamento, botão ROI)
- Padding da página: `space-y-4` no container raiz, mesmo padrão das demais páginas — **nunca** `overflow-hidden` na raiz (regra global do projeto)
- Mobile (375px): grid colapsa para `grid-cols-1`; filtros em `flex flex-col` (stack vertical)

**Cabeçalho da página:**
```jsx
<div className="flex items-center justify-between gap-3">
  <h1 className="text-xl font-bold text-gray-900 dark:text-slate-100">Campanhas</h1>
  <Button onClick={openNewCampanhaModal}>
    <Plus size={16} className="mr-1" /> Nova Campanha
  </Button>
</div>
```
- Título: `text-xl font-bold` (Plus Jakarta Sans herdado do global), `text-gray-900 dark:text-slate-100`
- Sem subtítulo — não há dado dinâmico de contexto pra mostrar aqui (diferente do Dashboard)
- Botão de ação: `<Plus />` 16px, variante primary (`Button.jsx` default), label "Nova Campanha"

**Barra de filtros:**
- Layout: `flex flex-row flex-wrap gap-3 items-end`
- Filtro Status: `Select` com options `['Todos', 'Planejada', 'Ativa', 'Encerrada']`, width `w-40`
- Filtro Canal: `Select` com options `['Todos', 'Ads', 'Redes Sociais', 'E-mail', 'Orgânico', 'Outro']`, width `w-44`
- Ambos sem label acima (usar `placeholder`/primeira option como label implícito), consistente com o padrão enxuto já usado nos filtros de Vendas.jsx
- Botão "Limpar filtros": aparece só quando status ou canal ≠ "Todos" — `variant="ghost"`, `text-xs`, `text-gray-500 dark:text-slate-400`

**Card de Campanha (grid item):**
```
┌─────────────────────────────────────┐
│ Nome da Campanha         [ATIVA]     │  ← header: nome (font-semibold) + STATUS_BADGES
│ 📣 Ads                                │  ← canal, text-xs text-gray-400 dark:text-slate-500
│ 01/08/2026 — 31/08/2026               │  ← datas, text-xs
│ Orçamento: R$ 2.500,00                │  ← text-lg font-bold, mesmo peso usado em valor_total (Vendas.jsx)
│                                        │
│ [Editar] [Excluir]      [Ver ROI →]  │  ← footer do Card, ações à esquerda, ROI destacado à direita
└─────────────────────────────────────┘
```
- Usar `Card.jsx` como wrapper — sem `title` prop (nome vai no corpo, junto do badge, para poder alinhar `justify-between` com o status)
- `STATUS_BADGES` (Campanha):
  ```js
  const STATUS_BADGES_CAMPANHA = {
    planejada: 'bg-gray-100 text-gray-600 dark:bg-navy-700 dark:text-slate-400',
    ativa:     'bg-green-100 text-green-700 dark:bg-emerald-900/30 dark:text-emerald-300',
    encerrada: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300',
  }
  ```
  (planejada=gray, ativa=green, encerrada=red — exatamente como pedido; segue a mesma paridade de classes light/dark já usada em `STATUS_BADGES` de Vendas.jsx)
- Botão "Ver ROI": `variant="ghost"`, cor de destaque `text-violet-600 dark:text-violet-400`, ícone `<TrendingUp size={14} />` à esquerda do label, abre o Modal de ROI (seção 5) — chama `GET /marketing/campanhas/{id}/roi/` no clique (lazy, não pré-carregado na listagem)
- Botões Editar/Excluir: ícones `<Pencil size={14} />` e `<Trash2 size={14} />`, mesmo padrão de ação inline já usado nos demais módulos (ghost, sem texto em mobile — só ícone; label visível em desktop `md:inline`)
- Estado vazio (nenhuma campanha após filtro): ícone `<Megaphone size={32} className="text-gray-300 dark:text-navy-600" />` centralizado + texto "Nenhuma campanha encontrada" `text-sm text-gray-400 dark:text-slate-500`

**Modal Campanha (criar/editar) — ver seção 3**

**Paginação:** `Pagination.jsx` no rodapé, mesmo padrão de Fornecedores/Clientes

**Mobile-first:**
- Breakpoint 375px: cards `w-full`, grid `grid-cols-1`
- Filtros em coluna, `Select`s `w-full`
- Botões do footer do Card: Editar/Excluir colapsam para ícone-only, "Ver ROI" mantém o texto (ação principal do card, precisa ficar legível)

---

### 2. Leads (`/marketing/leads`)

**Layout geral:**
- Full-page list — aqui sim **tabela**, não cards (lead é um registro mais tabular: nome, email, telefone, campanha, status, ação — cabe bem em linha, e o volume de leads tende a ser maior que campanhas)
- Estrutura de tabela: reaproveitar o padrão de tabela já usado no projeto — `<table>` semântica com `thead` fixo (`bg-gray-50 dark:bg-navy-900 border-b border-gray-200 dark:border-navy-600`) e `tbody` com `divide-y divide-gray-100 dark:divide-navy-700`, mesma estrutura implícita nas listagens tabulares do projeto
- Mobile (375px): tabela em scroll horizontal (`overflow-x-auto` no wrapper — nunca no root da página)

**Cabeçalho da página:**
```jsx
<div className="flex items-center justify-between gap-3">
  <h1 className="text-xl font-bold text-gray-900 dark:text-slate-100">Leads</h1>
  <Button onClick={openNewLeadModal}>
    <Plus size={16} className="mr-1" /> Novo Lead
  </Button>
</div>
```

**Barra de filtros:**
- Filtro Status: `Select` options `['Todos', 'Novo', 'Qualificado', 'Convertido', 'Descartado']`, `w-40`
- Filtro Campanha: `Select` populado via `GET /marketing/campanhas/` (apenas `is_active=True`), option adicional "Sem campanha" para leads com `campanha=null`, `w-52`
- Mesmo padrão de "Limpar filtros" da tela de Campanhas

**Tabela — colunas:**
| Coluna | Largura sugerida | Conteúdo |
|---|---|---|
| Nome | flex-1 (min 160px) | `font-medium text-gray-900 dark:text-slate-100` |
| E-mail | 200px | `text-gray-500 dark:text-slate-400`, "—" se vazio |
| Telefone | 140px | `text-gray-500 dark:text-slate-400`, "—" se vazio |
| Campanha | 160px | nome da campanha ou "Sem campanha" em `text-gray-400 dark:text-slate-500 italic` quando null |
| Status | 120px | badge (ver `STATUS_BADGES_LEAD` abaixo) |
| Ações | 160px | ícones Editar/Excluir + botão "Converter em Cliente" |

- `STATUS_BADGES_LEAD`:
  ```js
  const STATUS_BADGES_LEAD = {
    novo:        'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
    qualificado: 'bg-yellow-100 text-yellow-700 dark:bg-amber-900/30 dark:text-amber-300',
    convertido:  'bg-green-100 text-green-700 dark:bg-emerald-900/30 dark:text-emerald-300',
    descartado:  'bg-gray-100 text-gray-500 dark:bg-navy-700 dark:text-slate-500',
  }
  ```
  (novo=blue, qualificado=yellow, convertido=green, descartado=gray — exatamente como pedido)

**Botão "Converter em Cliente":**
- Visível **apenas** quando `lead.status !== 'convertido'` (RN06 — irreversível, então some/desabilita depois, nunca mostra desabilitado com tooltip — simplesmente não renderiza, é mais claro que um botão morto)
- Ícone `<UserCheck size={14} />`, `variant="secondary"` (contorno `violet-500`, não preenchido — ação importante mas não é a ação primária da tela, que é "Novo Lead")
- Ao clicar: `POST /marketing/leads/{id}/converter/` → toast de sucesso ("Lead convertido em cliente com sucesso") → refresh da linha (status vira `convertido`, badge atualiza, botão some) — **sem confirmação modal prévia** (ação não é destrutiva, é aditiva; se falhar, `extractErrorMessage` no catch mostra o motivo, ex. "Lead já convertido")

**Estado vazio:** ícone `<Users size={32} className="text-gray-300 dark:text-navy-600" />` + "Nenhum lead encontrado"

**Paginação:** `Pagination.jsx`, mesmo padrão

---

### 3. Modal Campanha (criar/editar)

**Layout:** `Modal.jsx` existente, título dinâmico "Nova Campanha" / "Editar Campanha"

**Campos (ordem):**
1. Nome — `Input` full width, `required`
2. Canal — `Select`, options `[Ads, Redes Sociais, E-mail, Orgânico, Outro]`, `required`
3. Linha dupla (`grid grid-cols-1 md:grid-cols-2 gap-3`):
   - Data Início — `Input type="date"`, `required`
   - Data Fim — `Input type="date"`, opcional, placeholder "Opcional"
4. Orçamento — `Input type="number"` com prefixo visual "R$" (mesmo padrão de campo monetário já usado em Vendas.jsx/Financeiro.jsx), `step="0.01"`, `min="0"`
5. Status — `Select`, options `[Planejada, Ativa, Encerrada]`, default "Planejada" na criação

**Rodapé do modal:** `Button variant="ghost"` "Cancelar" + `Button` primary "Salvar" (padrão de todos os modais do projeto)

**Validação client-side mínima:** nome e canal obrigatórios, data_fim (se preenchida) não pode ser anterior a data_inicio — mensagem inline abaixo do campo, mesmo padrão de erro dos demais formulários

---

### 4. Modal Lead (criar/editar)

**Layout:** `Modal.jsx`, título "Novo Lead" / "Editar Lead"

**Campos (ordem):**
1. Nome — `Input` full width, `required`
2. Linha dupla (`grid grid-cols-1 md:grid-cols-2 gap-3`):
   - E-mail — `Input type="email"`, opcional
   - Telefone — `Input`, opcional, máscara de telefone já existente no projeto (mesma usada em Clientes.jsx)
3. Campanha — `Select` (autocomplete simples via busca client-side na lista já carregada, sem necessidade de endpoint de busca dedicado — volume de campanhas é baixo), populado via `GET /marketing/campanhas/?is_active=true`, opção "Sem campanha" no topo
4. Status — `Select`, options `[Novo, Qualificado, Convertido, Descartado]`
   - **Regra de UI (RN06):** se `lead.status === 'convertido'` (edição), o `Select` de status fica **desabilitado** com texto auxiliar `text-xs text-gray-400` abaixo: "Conversão é irreversível — use a ação Converter em Cliente na listagem para leads não convertidos." Isso é reforço visual da regra de negócio já bloqueada no backend (RN06), evita o usuário tentar mudar e levar 400 sem entender por quê.
5. Observações — `Input` multilinha (`textarea`, mesmo estilo visual do `Input.jsx` adaptado, ou reaproveitar o campo `observacoes` já existente em Vendas.jsx como referência de estilo), opcional

**Rodapé:** mesmo padrão de Cancelar/Salvar

---

### 5. Modal ROI

**Decisão de layout:** **Modal** (não Drawer lateral) — consistente com o resto do projeto, que não tem nenhum padrão de Drawer implementado ainda (`Modal.jsx` é o único padrão de overlay existente no projeto). Introduzir um Drawer novo só para esta tela seria inconsistência sem ganho real — o conteúdo do ROI (6 métricas + gráfico simples) cabe bem em um Modal de tamanho médio.

**Título:** "ROI — {nome da campanha}"

**Conteúdo — grid de métricas (RF04):**
```
┌──────────────────┬──────────────────┬──────────────────┐
│ Leads Totais      │ Leads Convertidos│ Orçamento         │
│ 42                │ 8                │ R$ 2.500,00       │
├──────────────────┼──────────────────┼──────────────────┤
│ Receita Fechada   │ CAC              │ ROI               │
│ R$ 12.000,00      │ R$ 312,50        │ +380%             │
└──────────────────┴──────────────────┴──────────────────┘
```
- Grid `grid-cols-2 md:grid-cols-3 gap-3`, cada métrica em um mini-card: `bg-gray-50 dark:bg-navy-900/50 rounded-lg p-3`
  - Label: `text-xs text-gray-400 dark:text-slate-500 uppercase tracking-wide`
  - Valor: `text-lg font-bold text-gray-900 dark:text-slate-100`
- **CAC e ROI nulos (RF04 — divisor zero):** exibir `"—"` em vez de "R$ NaN", "0" ou "R$ 0,00" — regra explícita já definida na Especificacao_Hotfix (seção 8), reforçada aqui como requisito visual obrigatório
- **ROI negativo:** valor em `text-red-600 dark:text-red-400` em vez da cor padrão (campanha deu prejuízo — mesma lógica de feedback por cor+texto já usada no projeto, nunca cor isolada); ROI positivo em `text-green-600 dark:text-emerald-400` com prefixo "+"; ROI neutro/null mantém `text-gray-900 dark:text-slate-100`

**Gráfico simples (sem lib extra — pedido explícito):**
- Barra de progresso horizontal simples com CSS puro (`div` com `width: {pct}%`, sem SVG/canvas/lib) representando `leads_convertidos / leads_total` — funil de conversão visual abaixo do grid de métricas:
  ```jsx
  <div className="mt-4">
    <div className="flex justify-between text-xs text-gray-400 dark:text-slate-500 mb-1">
      <span>Taxa de conversão</span>
      <span>{leads_total > 0 ? Math.round((leads_convertidos / leads_total) * 100) : 0}%</span>
    </div>
    <div className="w-full h-2 rounded-full bg-gray-100 dark:bg-navy-700 overflow-hidden">
      <div
        className="h-full rounded-full bg-violet-500 transition-all"
        style={{ width: `${leads_total > 0 ? (leads_convertidos / leads_total) * 100 : 0}%` }}
      />
    </div>
  </div>
  ```
- Isso satisfaz "gráfico simples se possível" sem introduzir dependência nova (Chart.js/Recharts etc. — fora do escopo; evita inflar o bundle por causa de uma métrica única)

**Rodapé:** apenas botão "Fechar" (`variant="ghost"`) — ROI é somente leitura, sem ação de edição neste modal

**Loading state:** enquanto `GET .../roi/` não retorna, `Loading.jsx` (spinner já existente) no lugar do grid

**Mobile-first:** grid de métricas colapsa para `grid-cols-2` (mantém 2 colunas mesmo em 375px — 6 métricas em 1 coluna só fica muito longo; 2 colunas é o mínimo legível testado nas demais telas do projeto)

---

## Ícones Lucide (mapa completo desta manutenção)

| Ação/Elemento | Ícone | Tamanho |
|---|---|---|
| Nova Campanha / Novo Lead | `<Plus />` | 16px |
| Ver ROI | `<TrendingUp />` | 14px |
| Editar | `<Pencil />` | 14px |
| Excluir | `<Trash2 />` | 14px |
| Converter em Cliente | `<UserCheck />` | 14px |
| Estado vazio — Campanhas | `<Megaphone />` | 32px |
| Estado vazio — Leads | `<Users />` | 32px |
| Canal Ads (opcional, decorativo em card) | `<Target />` | 14px |

**Sidebar (RF06) — exceção confirmada:** item "Marketing" usa emoji `📣`, **não** Lucide — consistente com a regra de fábrica (DIV-UI03) de que a Sidebar nunca usa ícone de lib, só emoji.

---

## Componentes existentes reutilizados

```
Button.jsx     → todos os CTAs (primary/ghost/secondary já suportados)
Card.jsx       → grid de Campanhas
Input.jsx      → todos os campos de texto/número/data dos modais
Select.jsx     → filtros + campos de choice dos modais
Modal.jsx      → Modal Campanha, Modal Lead, Modal ROI (nenhum Drawer novo)
Loading.jsx    → loading state do Modal ROI
Pagination.jsx → rodapé de Campanhas e Leads
```

**Nenhum componente novo de UI genérico precisa ser criado** — só as duas páginas (`Campanhas.jsx`, `Leads.jsx`) e os 3 modais, todos montados com o kit existente.

---

## Passagem de bastão

```
✅ Especificação UI concluída — UidCore (Manutenção #54)
   Telas analisadas: 5 (Campanhas, Leads, Modal Campanha, Modal Lead, Modal ROI)
   Componentes reutilizados: 7 existentes (Button, Card, Input, Select,
     Modal, Loading, Pagination)
   Novos padrões: 0 componentes de UI novos — apenas 2 mapas de
     STATUS_BADGES locais (Campanha e Lead) seguindo o padrão inline já
     estabelecido em Vendas.jsx, e uma barra de progresso CSS pura para
     o funil de conversão no Modal ROI (sem lib de gráfico nova)

📁 Arquivo: Especificacao_UI_Hotfix.md (em /var/www/uidcore/)

➡️ Loom lê Especificacao_Hotfix.md + Especificacao_UI_Hotfix.md
   antes de implementar Campanhas.jsx, Leads.jsx, os 3 modais,
   Sidebar.jsx (RF06) e o Select de perfil em Usuarios.jsx
```
