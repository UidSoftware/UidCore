# Especificação UI Hotfix — UidCore (Manutenção #10)
**Tela:** Conciliação Bancária
**Baseado em:** `Especificacao_Hotfix.md` (Analista, Manutenção #10)
**Modo:** Hotfix — sistema existente, design system já definido (`design_system.md` +
padrão vivo em `Financeiro.jsx`). Nenhuma cor, fonte ou token novo é criado aqui.

---

## Design System do Projeto (referência)

- **Fonte:** Plus Jakarta Sans (títulos) + DM Sans (corpo) — já configuradas globalmente
  desde a Manutenção #9. Não repetir configuração, só não usar classe que quebre.
- **Cores primárias:** `primary-600`/`primary-700` (Tailwind custom, ver `tailwind.config.js`)
  para ações principais e abas ativas; `accent-600` reservado para toast de sucesso
  (mesmo padrão de `Financeiro.jsx`).
- **Cores de fundo:** branco (`bg-white`) para cards/tabelas, `bg-gray-50`/`bg-gray-100`
  para hover e cabeçalho de tabela, `bg-gray-900` fixo na Sidebar.
- **BorderRadius padrão:** `rounded-lg` (8px) em inputs/botões/badges de pílula,
  `rounded-xl` (12px) em `Card`, `rounded-2xl` em `Modal`, `rounded-full` em badges de status.
- **Padrão de card:** componente `Card.jsx` existente — `bg-white rounded-xl border
  border-gray-200 shadow-sm`, `title` opcional com borda inferior.
- **Ícones:** `lucide-react` já está no `package.json` e deve ser usado **dentro da página**
  (botões, ações, estados vazios). **Exceção confirmada pela Analista (RF-F07):** o item
  de menu da Sidebar mantém emoji `🔄`, por consistência com o padrão atual da Sidebar
  (divergência DIV-UI03 já suspensa na Manutenção #9 — não migrar só este item).

---

## Observação sobre cores de badge (reconciliação de fontes)

O prompt desta manutenção sugeriu "verde=PROCESSADO/CONCILIADO, amarelo=COM_DIVERGENCIAS/
FALTANDO_BANCO, vermelho=FALTANDO_SISTEMA". A `Especificacao_Hotfix.md` (§3.2, artefato
canônico do Analista, já validado) é mais específica e separa dois enums distintos —
sigo ela como fonte de verdade para o **status da conciliação** e uso a orientação do
prompt (mais granular) para o **status do item**, que a Especificação só descreve em
prosa (§4, RF-F03):

| Enum | Valor | Cor | Classe Tailwind |
|---|---|---|---|
| **Status da Conciliação** (`StatusConciliacao`) | `PROCESSADO` | verde | `bg-green-100 text-green-800` |
| | `COM_DIVERGENCIAS` | vermelho | `bg-red-100 text-red-800` |
| | `PENDENTE` | amarelo | `bg-yellow-100 text-yellow-800` |
| **Status do Item** (`StatusItemConciliacao`) | `CONCILIADO` | verde | `bg-green-100 text-green-800` |
| | `FALTANDO_BANCO` | amarelo/laranja | `bg-yellow-100 text-yellow-800` |
| | `FALTANDO_SISTEMA` | vermelho | `bg-red-100 text-red-800` |

Reaproveitar o padrão `STATUS_BADGES` + componente `Badge` já existentes em
`Financeiro.jsx` (linhas 73-90) — copiar a mesma estrutura de objeto/lookup, apenas
com as chaves acima, em vez de recriar um componente de badge do zero.

---

## Especificação Visual por Tela

### `Conciliacao.jsx` — Layout geral da página

Segue **exatamente** a estrutura de `Financeiro.jsx` (mesmo componente pai controlando
abas via `useState` + array `TABS`, sem sub-rotas):

```jsx
const TABS = [
  { key: 'historico', label: 'Histórico' },
  { key: 'padroes', label: 'Padrões Seguros' },
]
```

- Header da página (fora das abas, sempre visível):
  - `<h1 className="text-2xl font-bold text-gray-900">Conciliação Bancária</h1>`
  - `<p className="text-sm text-gray-500 mt-0.5">Envie extratos e concilie com o Livro Caixa</p>`
- Barra de abas: `flex gap-1 overflow-x-auto pb-1`, botão ativo
  `bg-primary-600 text-white`, inativo `bg-white text-gray-600 hover:bg-gray-100
  border border-gray-200` — idêntico ao `TABS.map` de `Financeiro.jsx` (linhas 124-138).
- Toast local: mesmo padrão (`fixed top-4 right-4 z-50 ...`, verde `bg-accent-600` /
  vermelho `bg-red-600`), reaproveitar tal qual.
- Padding externo da página: nenhum adicional — o layout autenticado (`AppLayout`) já
  define o padding do conteúdo; a página só usa `space-y-4` no container raiz.
- **Mobile (375px):** abas com `overflow-x-auto` já cobre o caso de label não caber;
  título quebra para `text-xl` se necessário, mas `text-2xl` já é o padrão usado em
  outras páginas em mobile sem overflow, então manter.

---

### Aba "Histórico" (RF-F01) — Listagem de conciliações

**Cabeçalho da aba:**
```jsx
<div className="flex items-center justify-between gap-3">
  <h2 className="text-lg font-semibold text-gray-800">Histórico de Conciliações</h2>
  <Button onClick={openNovaConciliacao}>
    <Plus size={16} className="mr-1" /> Nova Conciliação
  </Button>
</div>
```
(ícone Lucide `Plus`, 16px, mesmo padrão de "+ Nova Receita" em `Financeiro.jsx` mas
com ícone real em vez de `+` literal — primeira página do UidCore a usar Lucide dentro
do corpo, conforme já habilitado pelo design system)

**Estado vazio:** `text-center py-12 text-gray-400`, ícone `<Inbox size={40}
className="mx-auto mb-2 opacity-50" />` + `<p className="text-sm">Nenhuma conciliação
enviada ainda.</p>`.

**Estado loading:** `text-center py-12 text-gray-400 text-sm` com texto "Carregando...".

**Desktop (`hidden md:block`) — Tabela dentro de `Card`:**

Reaproveitar exatamente a estrutura de tabela de `LivroCaixaTab` (`overflow-x-auto -mx-6
-my-4`, `<table className="w-full text-sm">`, `thead` com `bg-gray-50 border-b
border-gray-200`, `tbody` com `divide-y divide-gray-100`, linha `hover:bg-gray-50
cursor-pointer` porque a linha inteira é clicável).

| Coluna | Classe | Formatação |
|---|---|---|
| Período | `px-4 py-3 text-gray-600` | `MM/YYYY` (ex: `periodo` já vem `YYYY-MM` do backend — formatar no front) |
| Conta | `px-4 py-3 text-gray-600` | `conta_nome` |
| Status | `px-4 py-3` | `<Badge status={item.status} map={STATUS_CONCILIACAO_BADGES} />` |
| Total Banco | `px-4 py-3 text-right font-mono text-gray-700` | `BRL(item.total_banco)` |
| Total Sistema | `px-4 py-3 text-right font-mono text-gray-700` | `BRL(item.total_sistema)` |
| Divergências | `px-4 py-3 text-right` | `item.divergencias` — se `> 0`: `font-semibold text-red-600`; se `0`: `text-gray-400` |
| Processado em | `px-4 py-3 text-gray-500 text-xs` | `processado_em` formatado `dd/MM/yyyy HH:mm` |
| Ações | `px-4 py-3 text-right` | `<ChevronRight size={16} className="text-gray-400" />` (indica "clicável", sem botão) |

Linha inteira com `onClick={() => abrirDetalhe(item)}`.

**Mobile (`flex flex-col gap-3 md:hidden`) — Cards:**

Mesmo padrão de `ReceitasTab`/`DespesasTab` mobile — `Card` clicável (`onClick` no
`Card` ou `div` interno):

```jsx
<Card key={item.id} className="cursor-pointer" onClick={() => abrirDetalhe(item)}>
  <div className="flex justify-between items-start gap-2">
    <div className="min-w-0">
      <p className="font-semibold text-gray-900 truncate">{item.conta_nome}</p>
      <p className="text-xs text-gray-500 mt-0.5">{formatarPeriodo(item.periodo)}</p>
    </div>
    <Badge status={item.status} map={STATUS_CONCILIACAO_BADGES} />
  </div>
  <div className="mt-2 flex justify-between items-center text-sm">
    <span className="text-gray-500">Banco: <span className="font-mono text-gray-700">{BRL(item.total_banco)}</span></span>
    <span className="text-gray-500">Sistema: <span className="font-mono text-gray-700">{BRL(item.total_sistema)}</span></span>
  </div>
  {item.divergencias > 0 && (
    <p className="text-xs text-red-600 font-medium mt-1">{item.divergencias} divergência(s)</p>
  )}
</Card>
```

`Pagination` component embaixo, igual ao resto — usar `PAGE_SIZE = 20` (mesma constante
de `Financeiro.jsx`), `response.data.results`/`response.data.count`.

---

### Modal "Nova Conciliação" (RF-F02)

`<Modal title="Nova Conciliação" onClose={...} maxW="max-w-lg">` (tamanho padrão, não
precisa de `max-w-2xl` — poucos campos).

Ordem dos campos (`space-y-4` dentro do `<form>`, igual padrão de `Financeiro.jsx`):

1. **Arquivo (obrigatório):**
   ```jsx
   <div className="flex flex-col gap-1">
     <label className="text-sm font-medium text-gray-700">Extrato Bancário (PDF)</label>
     <input type="file" accept="application/pdf" required
       className="w-full text-sm text-gray-600 file:mr-3 file:py-2 file:px-3
         file:rounded-lg file:border-0 file:bg-primary-50 file:text-primary-700
         file:text-sm file:font-medium hover:file:bg-primary-100" />
   </div>
   ```
   (mesmo estilo de input de arquivo já usado em `ResourceCrud.jsx` linha 208-221 —
   reaproveitar o padrão de classe, não recriar)
2. **Conta (obrigatório):** `<Select label="Conta" options={[{value:'',label:'Selecione...'}, ...contasOptions]} required />` — `contasOptions` via `GET /financeiro/contas/`, mesmo `useEffect` de `Financeiro.jsx` (linhas 102-109).
3. **Período (obrigatório):** `<input type="month" required>` estilizado com a mesma classe de `Input.jsx` (borda, radius, focus ring) — como não existe `type="month"` no componente `Input` genérico, usar `<input>` nativo com as classes do padrão de input do projeto (copiar classe de `Input.jsx`).
4. **Senha do PDF (opcional):** `<Input label="Senha do PDF (se protegido)" type="password" name="senha" />`
5. **Checkbox "Conciliar automaticamente":**
   ```jsx
   <div className="flex items-center gap-2">
     <input type="checkbox" id="auto" className="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500" />
     <label htmlFor="auto" className="text-sm font-medium text-gray-700">Conciliar automaticamente por padrões seguros</label>
   </div>
   ```
   (mesmo padrão de checkbox de `ResourceCrud.jsx` linhas 193-206)

Rodapé do form: `<Button type="button" variant="secondary">Cancelar</Button>` +
`<Button type="submit" loading={uploading}>Enviar</Button>` — durante upload, `Button`
já tem spinner embutido (`loading` prop existente), atende RNF-01 (não precisa criar
spinner novo).

**Ícone no botão de trigger do modal:** `Upload` (Lucide) é uma alternativa a `Plus`
para reforçar "envio de arquivo" — usar `Plus` no botão da listagem (ação genérica de
criar) e `Upload` só dentro do modal se quiser reforçar visualmente a área de arquivo
(opcional, não obrigatório).

---

### Detalhe da Conciliação (RF-F03) — decisão de UI: `Modal maxW="max-w-4xl"`

A Especificação deixou a escolha entre aba interna ou Modal a critério do Loom. Brush
recomenda **Modal `max-w-4xl`**, por consistência com o único outro modal grande já
existente no padrão do projeto (`Modal` com `maxW` customizável já suporta isso nativamente,
sem componente novo) e porque preserva o estado da listagem por trás (não perde
filtro/página ao fechar).

**Header do detalhe (dentro do modal, acima da tabela de itens):**

```jsx
<div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
  <div>
    <p className="text-xs text-gray-500">Conta</p>
    <p className="text-sm font-semibold text-gray-900">{conciliacao.conta_nome}</p>
  </div>
  <div>
    <p className="text-xs text-gray-500">Período</p>
    <p className="text-sm font-semibold text-gray-900">{formatarPeriodo(conciliacao.periodo)}</p>
  </div>
  <div>
    <p className="text-xs text-gray-500">Status</p>
    <Badge status={conciliacao.status} map={STATUS_CONCILIACAO_BADGES} />
  </div>
  <div>
    <p className="text-xs text-gray-500">Divergências</p>
    <p className={`text-sm font-bold ${conciliacao.divergencias > 0 ? 'text-red-600' : 'text-green-600'}`}>
      {conciliacao.divergencias}
    </p>
  </div>
</div>
<div className="grid grid-cols-2 gap-3 mb-4 pb-4 border-b border-gray-100">
  <div className="rounded-xl p-3 bg-blue-50 text-blue-700">
    <p className="text-xs font-medium opacity-70">Total Banco</p>
    <p className="text-base font-bold mt-0.5">{BRL(conciliacao.total_banco)}</p>
  </div>
  <div className="rounded-xl p-3 bg-blue-50 text-blue-700">
    <p className="text-xs font-medium opacity-70">Total Sistema</p>
    <p className="text-base font-bold mt-0.5">{BRL(conciliacao.total_sistema)}</p>
  </div>
</div>
```
(reaproveita o mesmo estilo de mini-KPI de `KpiCard` em `Financeiro.jsx`, sem precisar
importar o componente — inline, já que é local a este modal)

**Tabela de itens** (`GET /conciliacoes/{id}/itens/`), mesmo padrão desktop/mobile de
`LivroCaixaTab`:

| Coluna | Formatação |
|---|---|
| Data | `data_banco`, `dd/MM/yyyy` |
| Descrição | `descricao_banco`, `truncate max-w-[220px]` |
| Valor | `BRL(valor)`, cor por `tipo`: `ENTRADA` → `text-green-700` com prefixo `+`, `SAIDA` → `text-red-700` com prefixo `-` (idêntico a `LivroCaixaTab`) |
| Tipo | ícone Lucide inline: `ArrowUpCircle` (verde) para `ENTRADA`, `ArrowDownCircle` (vermelho) para `SAIDA`, 14px, ao lado do label |
| Status | `<Badge status={item.status} map={STATUS_ITEM_BADGES} />` |
| Ação | condicional (ver regras abaixo) |

**Regras de linha (RN-02, já detalhadas na Especificação — tradução visual):**

- `CONCILIADO` → linha com opacidade normal, sem badge de alerta extra, sem botão.
- `FALTANDO_BANCO` → fundo da linha `bg-yellow-50` (leve, só para destacar visualmente
  sem gritar), ícone `AlertTriangle` 14px amarelo ao lado do status, sem botão de ação
  (é só informativo, fora do escopo resolver na tela).
- `FALTANDO_SISTEMA && confirmado === false` → fundo da linha `bg-red-50`, botão de ação:
  ```jsx
  <Button size="sm" onClick={() => confirmarItem(item)}>
    <CheckCircle2 size={14} className="mr-1" /> Confirmar
  </Button>
  ```
- `FALTANDO_SISTEMA && confirmado === true` → volta ao visual neutro (igual `CONCILIADO`),
  sem botão — já foi resolvido.

**Estado vazio de itens:** mesma linguagem visual do resto do sistema — `<Inbox
size={32} className="mx-auto mb-2 opacity-40" />` + "Nenhum item nesta conciliação."

---

### Confirmar item (RF-F04)

Sem modal de confirmação adicional (ação de baixo risco, reversível pelo backend em
teoria via re-consulta) — clique direto no botão "Confirmar" chama a API. Feedback:

- Toast de sucesso: "Item confirmado. {divergencias_restantes} divergência(s) restante(s)."
- Atualizar localmente: `item.confirmado = true` no state (sem re-fetch completo — UX
  mais rápida) + atualizar `conciliacao.divergencias` no header do modal com o valor
  `divergencias_restantes` retornado pela API.
- Erro: toast vermelho com `extractErrorMessage()`, igual ao resto do sistema.

---

### Aba "Padrões Seguros" (RF-F05)

**Avaliação do `ResourceCrud.jsx`:** o componente cobre bem o caso — CRUD com tabela +
modal + paginação genéricos. **Recomendação: usar `ResourceCrud`** em vez de recriar
`ContasTab`-style do zero, com uma ressalva importante:

> `ResourceCrud` não tem suporte nativo a **campo condicional** (RN-01: esconder/desabilitar
> `natureza` quando `tipo=SAIDA`). O componente atual (`renderField`) não recebe
> `form` como contexto para decidir visibilidade condicional de outro campo. Duas opções
> para o Loom:
> 1. **Estender `ResourceCrud`** com um campo `dependsOn`/`showIf: (form) => form.tipo === 'ENTRADA'`
>    no schema de `fields` (mudança pequena e reaproveitável por outros CRUDs futuros).
> 2. **Não usar `ResourceCrud`** para este caso específico e implementar a aba com
>    form próprio (como `ContasTab`), copiando a estrutura de tabela genérica.
>
> Brush recomenda a opção 1 (estender `ResourceCrud`) — é a única tela do projeto até
> agora com campo condicional, e a extensão é pequena o suficiente para não justificar
> duplicar toda a lógica de CRUD só por isso.

**Colunas da tabela** (via `ResourceCrud columns` prop ou tabela custom, se optar pela
opção 2):

| Coluna | Config |
|---|---|
| Descrição | `descricao_padrao`, texto |
| Tipo | badge: `ENTRADA` → `bg-green-100 text-green-700`, `SAIDA` → `bg-red-100 text-red-700` (mesmo padrão de badge de pílula do projeto) |
| Natureza | `natureza_label` — **só exibe valor quando `tipo=ENTRADA`**; quando `tipo=SAIDA`, célula mostra `—` (`text-gray-400`) |

**Modal criar/editar** — campos:

1. `Input label="Descrição" name="descricao_padrao" required` (largura completa, `sm:col-span-2`)
2. `Select label="Tipo" name="tipo" options={[{value:'ENTRADA',label:'Entrada'},{value:'SAIDA',label:'Saída'}]}`
3. `Select label="Natureza" name="natureza" options={[{value:'APORTE',label:'Aporte'},{value:'RECEITA_FINANCEIRA',label:'Receita Financeira'}]}` —
   **RN-01 aplicado:** quando `form.tipo === 'SAIDA'`, o campo fica `disabled` e
   visualmente esmaecido (`opacity-50 cursor-not-allowed` no wrapper), **não escondido
   por completo** — esconder completamente pode confundir o usuário sobre por que um
   campo "sumiu"; desabilitar com indicação visual é mais claro. Adicionar texto de apoio:
   `<p className="text-xs text-gray-400 mt-1">Aplicável apenas para Tipo = Entrada</p>`
   quando desabilitado.

Botão de ação no header da aba: `<Button onClick={openNovoPadrao}><Plus size={16}
className="mr-1" /> Novo Padrão</Button>` — mesmo padrão visual de "Nova Conciliação".

Excluir: `window.confirm` + `DELETE` (soft delete no backend), mesmo padrão de
`ContasTab.handleDelete` — toast de sucesso/erro igual ao resto.

---

### Ícones Lucide — resumo de uso nesta tela

| Ação/Elemento | Ícone | Tamanho |
|---|---|---|
| Nova Conciliação / Novo Padrão | `<Plus />` | 16px |
| Upload de arquivo (reforço visual, opcional) | `<Upload />` | 16-18px |
| Linha clicável (histórico → detalhe) | `<ChevronRight />` | 16px |
| Estado vazio (listas) | `<Inbox />` | 32-40px, `opacity-40/50` |
| Confirmar item | `<CheckCircle2 />` | 14px |
| Alerta (`FALTANDO_BANCO`) | `<AlertTriangle />` | 14px |
| Entrada (tipo do item) | `<ArrowUpCircle />` (verde) | 14px |
| Saída (tipo do item) | `<ArrowDownCircle />` (vermelho) | 14px |
| Editar padrão | `<Pencil />` | 14px (dentro do `Button size="sm"` de editar, se não usar `ResourceCrud` padrão que já usa texto "Editar") |
| Excluir padrão | `<Trash2 />` | 14px (idem) |

Todos importados de `lucide-react`, já presente no `package.json` (confirmado na
Manutenção #9, DIV-UI04).

---

## Mobile-first (RNF-03)

- Breakpoint de referência: 375px (iPhone SE), mesmo padrão usado no resto do sistema.
- Listagem de histórico: cards empilhados (`flex flex-col gap-3 md:hidden`), tabela some
  em mobile (`hidden md:block`) — padrão já validado em todas as outras páginas.
- Modal "Nova Conciliação": `maxW="max-w-lg"` já é responsivo por padrão (`Modal.jsx`
  usa `w-full` + `px-4` no overlay) — sem ajuste extra necessário.
- Modal de Detalhe (`max-w-4xl`): em telas pequenas, a tabela de itens deve ter
  `overflow-x-auto` dentro do modal (mesmo padrão `-mx-6 -my-4` das outras tabelas) para
  não estourar a largura do modal em 375px; o grid de header (4 colunas) deve colapsar
  para `grid-cols-2` em mobile (já especificado acima com `grid-cols-2 sm:grid-cols-4`).
- Aba "Padrões Seguros": se usar `ResourceCrud`, o componente já não tem view mobile em
  cards (usa só tabela com `overflow-x-auto`) — aceitável para este CRUD simples (poucos
  campos, tabela cabe rolando horizontal), consistente com o padrão que `ResourceCrud`
  já estabelece nos outros módulos (Vendas, RH, Administrativo etc.).

---

## Componentes existentes reutilizados (nenhum componente novo de UI é criado)

| Componente | Uso nesta tela |
|---|---|
| `Card.jsx` | Container de tabela desktop, cards mobile de histórico |
| `Button.jsx` | Todas as ações (primary/secondary/danger, com `loading`) |
| `Input.jsx` | Senha do PDF, descrição do padrão |
| `Select.jsx` | Conta, Tipo, Natureza |
| `Modal.jsx` | Nova Conciliação, Detalhe da Conciliação, criar/editar Padrão |
| `Pagination.jsx` | Listagem de histórico |
| `ResourceCrud.jsx` | Aba Padrões Seguros (com extensão sugerida para campo condicional — ver seção acima) |

Nenhum ícone de emoji é introduzido dentro da página (diferente da Sidebar, que mantém
`🔄` por decisão já documentada) — esta é a primeira página do UidCore a demonstrar o
uso de `lucide-react` no corpo da tela, o que é coerente com o design system (que já
lista `lucide-react` como disponível desde a Manutenção #9) mas ainda não tinha sido
adotado em nenhuma página existente.

---

## Passagem de bastão

```
✅ Especificação UI concluída — UidCore (Manutenção #10)
   Telas analisadas: 1 página (Conciliacao.jsx, 2 abas: Histórico + Padrões Seguros)
     + 3 estados de modal (Nova Conciliação, Detalhe, Criar/Editar Padrão)
   Componentes reutilizados: 6 existentes (Card, Button, Input, Select, Modal, Pagination)
     + ResourceCrud (com extensão sugerida — showIf/dependsOn condicional)
   Novos padrões: uso de lucide-react no corpo da página (primeira vez no UidCore)

📁 Arquivo: Especificacao_UI_Hotfix.md (em /var/www/uidcore/)

➡️ Loom lê Especificacao_Hotfix.md + Especificacao_UI_Hotfix.md
   antes de implementar Conciliacao.jsx, routes/index.jsx e Sidebar.jsx
```
