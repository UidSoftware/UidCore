# Design System — UidCore
**Modo:** Padrão Uid (cliente interno — Uid Software)
**Data do levantamento:** 2026-07-28
**Elaborado por:** Brush (MODO HOTFIX — documentação do sistema real em produção)

---

## a) Identidade Visual

- **Logo/Brand:** Ícone quadrado (border-radius 16px) com letra "U" em branco sobre fundo primary-600, exibido na tela de Login. No header, texto "UidCore" em primary-600.
- **Tom de voz:** Técnico-neutro. Termos contábeis reais (DRE, EBITDA, Livro Caixa, Balanço Patrimonial). Interface para usuário de negócio, não para leigo.
- **Fundo da aplicação:** `bg-gray-50` (#f9fafb) — fundo claro, não escuro.
- **Sidebar:** `bg-gray-900` (#111827) — escuro, contrasta com o conteúdo claro.

> DIVERGÊNCIA CRÍTICA: O UidCore usa tema claro (light mode), o oposto do padrão Uid escuro (bg-dark #0a0014). Isso é uma decisão arquitetural do projeto — não alterar sem ADR.

---

## b) Paleta de Cores

Extraída de `tailwind.config.js` (tokens customizados) + uso real nas páginas.

### Tokens customizados no tailwind.config.js

| Token | Hex | Uso |
|---|---|---|
| primary-500 | #3b82f6 | Referência intermediária |
| primary-600 | #2563eb | Botão primário, tab ativa, link, ícones de destaque |
| primary-700 | #1d4ed8 | Hover do botão primário |
| primary-800 | #1e40af | Uso raro |
| primary-50 | #eff6ff | Background de badge primário, fundo de hover em file input |
| primary-100 | #dbeafe | Avatar do usuário no header |
| accent-500 | #10b981 | Referência |
| accent-600 | #059669 | Toast de sucesso |
| accent-400 | #34d399 | Barras de gráfico (receita) |

### Cores Tailwind nativas usadas nas páginas

| Cor | Hex aproximado | Uso |
|---|---|---|
| gray-900 | #111827 | Sidebar background, títulos h1, texto de tabela primário |
| gray-800 | #1f2937 | Títulos h2 de seção |
| gray-700 | #374151 | Labels de formulário, texto secundário |
| gray-600 | #4b5563 | Cabeçalho de tabela, texto de célula |
| gray-500 | #6b7280 | Subtítulos, meta-informação |
| gray-400 | #9ca3af | Placeholders, texto vazio, ícones inativos |
| gray-300 | #d1d5db | Bordas de input e select |
| gray-200 | #e5e7eb | Bordas de tabela, divisores |
| gray-100 | #f3f4f6 | Thead background, badge neutro |
| gray-50 | #f9fafb | Fundo da aplicação, hover de linha de tabela |
| green-700 | #15803d | Valores de receita, campos financeiros positivos |
| green-400 | #4ade80 | Barras do gráfico de receita |
| red-700 | #b91c1c | Valores de despesa, campos financeiros negativos |
| red-600 | #dc2626 | Botão danger, toast de erro |
| red-400 | #f87171 | Barras do gráfico de despesa |
| blue-700 | #1d4ed8 | Valor de cobrança em Pagamentos |
| yellow-700 | #a16207 | Runway em situação de alerta |
| purple-800 | #6b21a8 | Badge EM_PRODUCAO, badge CONCLUIDO em Agendamento |

### Paleta completa de badges de status

| Status | Background | Texto | Módulo |
|---|---|---|---|
| RECEBIDO / PAGO | bg-green-100 | text-green-800 | Financeiro |
| PENDENTE | bg-yellow-100 | text-yellow-800 | Financeiro, Pagamentos, RH |
| ATRASADO / CANCELADO (crítico) | bg-red-100 | text-red-800 | Financeiro |
| CANCELADO (neutro) | bg-gray-100 | text-gray-400 | Vendas, Pagamentos |
| RASCUNHO | bg-gray-100 | text-gray-600 | Vendas, Administrativo |
| ENVIADO / CONFIRMADO / AGENDADO | bg-blue-100 | text-blue-800 | Vendas, Agendamento |
| APROVADO / VIGENTE / CONCLUIDO / ATIVO | bg-green-100 | text-green-800 | Vendas, Administrativo |
| REJEITADO | bg-red-100 | text-red-800 | Vendas |
| EM_PRODUCAO | bg-purple-100 | text-purple-800 | Vendas |
| EXPIRADO | bg-yellow-100 | text-yellow-800 | Administrativo |
| ABERTA | bg-yellow-100 | text-yellow-800 | RH (Folha) |
| FECHADA | bg-blue-100 | text-blue-800 | RH (Folha) |
| PAGA | bg-green-100 | text-green-800 | RH (Folha) |
| EM_ANDAMENTO | bg-yellow-100 | text-yellow-800 | RH (Férias) |
| PROCESSADO / CONCILIADO | bg-green-100 | text-green-800 | Conciliação |
| COM_DIVERGENCIAS / FALTANDO_SISTEMA | bg-yellow-100 | text-yellow-800 | Conciliação |
| FALTANDO_BANCO | bg-gray-100 | text-gray-600 | Conciliação |
| Ativo (booleano) | bg-green-100 | text-green-800 | Portal, Agendamento |
| Inativo (booleano) | bg-gray-100 | text-gray-400 | Portal, Agendamento |
| Sim (booleano) | bg-green-50 | text-green-700 | ResourceCrud |
| Não (booleano) | bg-gray-100 | text-gray-500 | ResourceCrud |

---

## c) Tipografia

### Fontes em uso

**Nenhuma fonte personalizada está configurada.** O `index.html` não tem nenhum `<link>` para Google Fonts. O `index.css` só contém as diretivas Tailwind. O projeto usa exclusivamente a **font-family padrão do sistema** herdada do Tailwind CSS.

> DIVERGÊNCIA CRÍTICA: O padrão Uid exige Plus Jakarta Sans (headings) + DM Sans (body) e proíbe Inter, Roboto e Arial. O UidCore ainda não configurou nenhuma fonte Uid.
>
> Na próxima iteração, adicionar em `tailwind.config.js`:
> ```js
> fontFamily: {
>   sans: ['"DM Sans"', 'sans-serif'],
>   display: ['"Plus Jakarta Sans"', 'sans-serif'],
> }
> ```
>
> E no `index.html`:
> ```html
> <link rel="preconnect" href="https://fonts.googleapis.com">
> <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
> <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600&family=Plus+Jakarta+Sans:wght@700;800&display=swap" rel="stylesheet">
> ```

### Hierarquia tipográfica atual (classes Tailwind)

| Uso | Classe | Tamanho / Peso |
|---|---|---|
| Título de página (h1) | text-2xl font-bold text-gray-900 | 24px, 700 |
| Título de seção (h2) | text-lg font-semibold text-gray-800 | 18px, 600 |
| Subtítulo de página | text-sm text-gray-500 | 14px, 400 |
| Título de card | text-sm font-semibold text-gray-700 | 14px, 600 |
| Corpo de tabela (coluna principal) | text-sm font-medium text-gray-900 | 14px, 500 |
| Corpo de tabela (colunas secundárias) | text-sm text-gray-600 | 14px, 400 |
| Labels de formulário | text-sm font-medium text-gray-700 | 14px, 500 |
| Cabeçalho de tabela | text-sm font-semibold text-gray-600 | 14px, 600 |
| Texto meta / caption | text-xs text-gray-500 | 12px, 400 |
| Valores monetários em tabela | font-mono | monospace |
| Badge | text-xs font-semibold | 12px, 600 |
| Label de KPI | text-xs font-medium opacity-70 | 12px, 500 |
| Valor de KPI | text-lg font-bold | 18px, 700 |
| Branding (header) | text-sm font-semibold text-primary-600 tracking-wide | 14px, 600 |
| Branding (sidebar) | text-lg font-bold text-white tracking-tight | 18px, 700 |

---

## d) Espaçamento e Layout

### Estrutura geral

```
Sidebar (bg-gray-900)          | Header (bg-white, h-16, border-b)
240px expandida / 64px colaps. | logo + avatar + logout
flex-col, py-4 no nav          |
                               |-------------------------------
NavLinks: px-3 py-2.5          | <main> p-6 overflow-y-auto
Ativo: bg-primary-600 white    | space-y-4 ou space-y-6
Inativo: text-gray-400         |
```

### AppLayout

- Root: `flex h-screen bg-gray-50 overflow-hidden`
- Sidebar desktop: `hidden md:flex shrink-0`
- Sidebar mobile: `fixed inset-y-0 left-0 z-30` com translate animado
- Overlay mobile: `fixed inset-0 z-20 bg-black/50`
- Header: `h-16 bg-white border-b border-gray-200 shrink-0`
- Main: `flex-1 overflow-y-auto p-6`

> ALERTA: `overflow-hidden` está presente no root do AppLayout. A regra Uid proíbe overflow-hidden no SistemaLayout root pois clipa selects nativos no Linux Chrome/Opera. Avaliar na próxima iteração se está causando problemas em produção.

### Breakpoints responsivos

| Prefix | Valor | Comportamento |
|---|---|---|
| (padrão) | < 768px | Cards empilhados, sidebar oculta |
| md: | >= 768px | Tabelas, sidebar visível |
| lg: | >= 1024px | Grids de 3 colunas |
| xl: | >= 1280px | Dashboard 4 colunas de métricas |
| sm: | >= 640px | Grid de 2 colunas em modais |

Breakpoint crítico de layout: **md (768px)** — divide cards mobile vs. tabela desktop.

### Padrões de grid

| Contexto | Classes |
|---|---|
| Métricas do Dashboard | grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4 |
| KPI Cards (Financeiro) | grid grid-cols-2 md:grid-cols-4 gap-3 |
| Cards de conta | grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 |
| Formulário em modal | grid grid-cols-1 sm:grid-cols-2 gap-4 |
| Formulário 3 colunas | grid grid-cols-1 sm:grid-cols-3 gap-4 |
| Metodos de pagamento | grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3 |
| Cargos/Agendas | grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 |

### Espaçamento interno

- Entre seções de página: `space-y-4` (padrão) / `space-y-6` (Dashboard)
- Padding do main: `p-6`
- Padding de card: `px-6 py-4`
- Padding de célula de tabela: `px-4 py-3` (primeira coluna: `px-6`)
- Gap entre botões de ação: `gap-2` (ações de linha) / `gap-3` (rodapé de modal)

---

## e) Componentes UI Existentes

### Localização: `/frontend/src/components/`

#### Layout
- `AppLayout.jsx` — wrapper principal: sidebar + header + main outlet
- `Sidebar.jsx` — navegação lateral colapsável, ícones emoji por módulo
- `Header.jsx` — barra superior com logo, avatar do usuário e botão de logout

#### UI (componentes reutilizáveis)
- `Button.jsx` — botão com 3 variantes e 3 tamanhos
- `Card.jsx` — container com título opcional, corpo e footer
- `Input.jsx` — input com label e mensagem de erro
- `Select.jsx` — select nativo com label e mensagem de erro
- `Modal.jsx` — overlay modal com título, conteúdo e largura configurável
- `Pagination.jsx` — paginação numérica simples
- `Loading.jsx` — spinner centralizado com mensagem
- `ResourceCrud.jsx` — CRUD genérico completo (tabela + modal + toast + paginação)

### Button

```jsx
<Button variant="primary" size="md" loading={false} disabled={false}>Texto</Button>
```

| Prop | Valores | Default |
|---|---|---|
| variant | primary, secondary, danger | primary |
| size | sm, md, lg | md |
| loading | bool | false |
| type | button, submit | button |

| Variante | Background | Texto | Hover |
|---|---|---|---|
| primary | bg-primary-600 | white | bg-primary-700 |
| secondary | bg-white + border-gray-300 | text-gray-700 | bg-gray-50 |
| danger | bg-red-600 | white | bg-red-700 |

| Tamanho | Padding | Font |
|---|---|---|
| sm | px-3 py-1.5 | text-sm |
| md | px-4 py-2 | text-sm |
| lg | px-6 py-3 | text-base |

Base: `rounded-lg font-medium focus:ring-2 focus:ring-offset-2 transition-colors`

### Card

```jsx
<Card title="Título opcional" footer={<div />} className="">conteúdo</Card>
```

- Container: `bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden`
- Header: `px-6 py-4 border-b border-gray-100` / `text-sm font-semibold text-gray-700`
- Body: `px-6 py-4`
- Footer: `px-6 py-3 bg-gray-50 border-t border-gray-100`

### Input

- Default: `border-gray-300 bg-white`
- Error: `border-red-500 bg-red-50`
- Focus: `focus:ring-2 focus:ring-primary-500 focus:border-transparent`
- Disabled: `bg-gray-50 cursor-not-allowed`
- Classe base: `w-full rounded-lg border px-3 py-2 text-sm text-gray-900 placeholder-gray-400`

### Select

Mesmas classes do Input. Usar opção vazia `{ value: '', label: 'Selecione...' }` como placeholder.

### Modal

- Overlay: `fixed inset-0 z-50 flex items-center justify-center px-4 bg-black/50`
- Container: `bg-white rounded-2xl shadow-xl p-6 max-h-[90vh] overflow-y-auto`
- maxW: `max-w-lg` (formulários simples) / `max-w-2xl` (formulários com grid 2 colunas)

### Pagination

- Botão ativo: `bg-primary-600 text-white`
- Botão inativo: `bg-gray-100 text-gray-600 hover:bg-gray-200`
- Tamanho: `w-8 h-8 rounded-lg text-sm font-medium`
- Oculto quando `totalPages <= 1`

### ResourceCrud

CRUD genérico parametrizado por schema. Aceita campo `columns` com modificadores:

| Modificador | Comportamento |
|---|---|
| `money: true` | `Number(v).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })` |
| `date: true` | `new Date(v).toLocaleDateString('pt-BR')` |
| `datetime: true` | `new Date(v).toLocaleString('pt-BR')` |
| `boolean: true` | Badge "Sim" (green-50/green-700) ou "Não" (gray-100/gray-500) |
| `badge: true` | Badge primary-50/primary-700 rounded-full |

PAGE_SIZE: 10. Detecta campos `file` e usa FormData automaticamente.

---

## f) Ícones

### Biblioteca: Lucide React

Usado exclusivamente nas páginas de Fase E. Verificar presença em `package.json` antes de usar.

Importação: `import { Plus, Pencil, Trash2, ... } from 'lucide-react'`

### Mapeamento por contexto

| Contexto | Ícone | Tamanho |
|---|---|---|
| Adicionar / Novo | Plus | size={16} no header, size={14} em sm |
| Editar | Pencil | size={14} |
| Excluir | Trash2 | size={14} |
| Download | Download | size={14} |
| Ver detalhe | Eye | size={14} |
| Confirmar | CheckCircle | size={14} |
| Upload | Upload | size={16} |
| Voltar | ArrowLeft | size={16} |
| Estado vazio conciliação | FileSearch | size={32} className="text-gray-300" |
| Novo funcionário | UserPlus | size={16} |
| Desativar usuário | UserX | size={14} |
| Novo agendamento | CalendarPlus | size={16} |
| Cargo | Briefcase | size={20} em cards, size={16} no header |
| PIX | Zap | size={20} className="text-green-600" |
| Boleto | FileText | size={20} className="text-blue-600" |
| Cartão | CreditCard | size={20} className="text-purple-600" |
| Dinheiro | Banknote | size={20} className="text-green-700" |
| Outro método | MoreHorizontal | size={20} className="text-gray-500" |

### Ícones de navegação na Sidebar

A Sidebar atual usa **emojis** (não Lucide): 📊👥🏭🛒💳💰📁👔📅🌐

> Recomendação: migrar para ícones Lucide na próxima iteração.

---

## g) Formulários

### Padrão de formulário em modal

```jsx
<form onSubmit={handleSubmit} className="space-y-4">
  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
    <Input label="Nome" name="nome" value={form.nome} onChange={handleChange} required />
    <Select label="Tipo" name="tipo" options={OPCOES} value={form.tipo} onChange={handleChange} />
  </div>
  <div className="flex flex-col gap-1">
    <label className="text-sm font-medium text-gray-700">Observações</label>
    <textarea
      name="obs"
      rows={3}
      className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-colors duration-150"
    />
  </div>
  <div className="flex justify-end gap-3 pt-2">
    <Button type="button" variant="secondary" onClick={closeModal}>Cancelar</Button>
    <Button type="submit" loading={saving}>Salvar</Button>
  </div>
</form>
```

### Tipos de campo (ResourceCrud e páginas)

| Type | Renderização |
|---|---|
| text / email / number / date / datetime-local / month | Input |
| select | Select com options estáticas |
| select-remote | Select com options via API no mount |
| textarea | textarea inline com classes padrão |
| file | input[type=file] com estilo customizado no botão |
| checkbox | input[type=checkbox] com label ao lado |

### Gerenciamento de estado

- `useState` + `useCallback` + `useEffect` (padrão em todas as páginas)
- `react-hook-form`, `@tanstack/react-query` e `zustand` estão instalados mas **não usados nas páginas existentes**
- Erros de API: via `extractErrorMessage()` + toast

---

## h) Tabelas e Listas

### Padrão de tabela desktop (dentro de Card)

```jsx
<Card>
  <div className="overflow-x-auto -mx-6 -my-4">
    <table className="w-full text-sm">
      <thead>
        <tr className="bg-gray-50 border-b border-gray-200">
          <th className="text-left px-4 py-3 font-semibold text-gray-600 whitespace-nowrap first:px-6">
            Coluna
          </th>
          <th className="text-right px-6 py-3 font-semibold text-gray-600">Ações</th>
        </tr>
      </thead>
      <tbody className="divide-y divide-gray-100">
        {items.map((item) => (
          <tr key={item.id} className="hover:bg-gray-50 transition-colors">
            <td className="px-4 py-3 text-gray-600 whitespace-nowrap first:px-6 first:font-medium first:text-gray-900">
              {item.campo}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  </div>
</Card>
```

- `overflow-x-auto -mx-6 -my-4`: expansão além do padding do Card
- Linha estornada: `opacity-50 line-through`

### Padrão mobile/desktop

```jsx
{/* Mobile: visível abaixo de md */}
<div className="flex flex-col gap-3 md:hidden">
  {items.map((item) => <Card key={item.id}>...</Card>)}
</div>

{/* Desktop: visível em md+ */}
<div className="hidden md:block">
  <Card><table>...</table></Card>
</div>
```

### Paginação

- PAGE_SIZE: 10 (ResourceCrud) / 20 (Financeiro)
- Parâmetros: `?page=N&page_size=N`
- Resposta: `{ count: N, results: [...] }` — nunca `.data` direto

### Formatação de valores

| Tipo | Padrão |
|---|---|
| Monetário | `Number(v).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })` |
| Data | `new Date(v).toLocaleDateString('pt-BR')` |
| Datetime | `new Date(v).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })` |
| Nulo | `<span className="text-gray-400">—</span>` |
| Número monospace | `font-mono` |

---

## i) Feedback

### Toast

```jsx
{toast && (
  <div className={`fixed top-4 right-4 z-50 max-w-sm px-4 py-3 rounded-lg shadow-lg text-sm font-medium text-white whitespace-pre-line break-words ${
    toast.type === 'error' ? 'bg-red-600' : 'bg-accent-600'
  }`}>
    {toast.msg}
  </div>
)}
```

- Sucesso: `bg-accent-600` (#059669), auto-dismiss 3500ms
- Erro: `bg-red-600` (#dc2626), auto-dismiss 7000ms

### Loading states

```jsx
{/* Componente Loading.jsx (carregamento inicial de página) */}
<Loading message="Carregando..." />

{/* Loading inline em tabs */}
<div className="text-center py-12 text-gray-400 text-sm">Carregando...</div>

{/* Loading em botão de submit */}
<Button type="submit" loading={saving}>Salvar</Button>
```

### Empty states

```jsx
{/* Com emoji */}
<div className="flex flex-col items-center justify-center py-12 gap-2 text-gray-400">
  <span className="text-4xl">{emptyIcon}</span>
  <p className="text-sm">{emptyText}</p>
</div>

{/* Com ícone Lucide */}
<div className="text-center py-12 text-gray-400">
  <FileSearch size={32} className="mx-auto text-gray-300 mb-2" />
  <p className="text-sm">Nenhum item encontrado.</p>
</div>
```

---

## j) Paleta de Status — Badges

Estrutura padrão (componente inline, não existe Badge.jsx no /components/ui/):

```jsx
<span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${MAP[status] || 'bg-gray-100 text-gray-600'}`}>
  {status}
</span>
```

- Base: `rounded-full px-2 py-0.5 text-xs font-semibold`
- Fallback: `bg-gray-100 text-gray-600`
- Tag retangular (regime RH): `rounded px-2 py-0.5 text-xs bg-gray-100 text-gray-700` (não pill)

---

## k) Padrões específicos do módulo Financeiro

### Tabs principais (pill style)

```jsx
<div className="flex gap-1 overflow-x-auto pb-1">
  <button className={tab === t.key
    ? 'px-4 py-2 text-sm font-medium rounded-lg bg-primary-600 text-white'
    : 'px-4 py-2 text-sm font-medium rounded-lg bg-white text-gray-600 hover:bg-gray-100 border border-gray-200'
  }>
    {t.label}
  </button>
</div>
```

### Sub-abas (underline style)

```jsx
<div className="flex gap-1 border-b border-gray-200 mb-4">
  <button className={subTab === t.key
    ? 'px-4 py-2 text-sm font-medium border-b-2 border-primary-600 text-primary-600'
    : 'px-4 py-2 text-sm font-medium border-b-2 border-transparent text-gray-500 hover:text-gray-700'
  }>
    {t.label}
  </button>
</div>
```

### KPI Card

```jsx
function KpiCard({ label, value, color }) {
  // color: 'blue' | 'green' | 'red'
  const colors = {
    blue:  'bg-blue-50 text-blue-700',
    green: 'bg-green-50 text-green-700',
    red:   'bg-red-50 text-red-700',
  }
  return (
    <div className={`rounded-xl p-4 ${colors[color]}`}>
      <p className="text-xs font-medium opacity-70">{label}</p>
      <p className="text-lg font-bold mt-1">{value}</p>
    </div>
  )
}
```

### Indicadores financeiros

- Receita/Entrada: `text-green-700` + prefix `+`
- Despesa/Saída: `text-red-700` + prefix `-`
- Delta positivo: `▲ X%` em `text-green-600`
- Delta negativo: `▼ X%` em `text-red-600`
- Runway >= 6 meses: `text-green-700` / 3-5 meses: `text-yellow-700` / < 3 meses: `text-red-700`

### Gráfico de barras (CSS puro, sem biblioteca)

Barras verticais com largura `w-3`, `rounded-t`, altura calculada por percentual do max via `style={{ height: \`\${pct}%\` }}`. Verde para receita, vermelho para despesa.

---

## l) Login Page

- Fundo: `min-h-screen bg-gradient-to-br from-primary-50 to-primary-100`
- Formulário centralizado: `w-full max-w-sm`
- Card do form: `bg-white rounded-2xl shadow-sm border border-gray-200 p-8`
- Ícone logo: `w-16 h-16 rounded-2xl bg-primary-600` com "U" em branco
- Erro inline (não toast): `rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700`

---

## m) Divergências e Recomendações

### Divergências críticas (corrigir na próxima iteração)

| # | Divergência | Impacto | Recomendação |
|---|---|---|---|
| 1 | Nenhuma fonte configurada | Alto — usa fonte do SO, varia por plataforma | Configurar Plus Jakarta Sans + DM Sans (ver seção b) |
| 2 | Tema claro vs. padrão Uid escuro | Decisão arquitetural | Documentar como ADR: "UidCore usa tema claro para gestão financeira" |
| 3 | overflow-hidden no root do AppLayout | Pode clipar selects no Linux Chrome/Opera | Testar em produção no Linux; substituir se confirmar bug |
| 4 | Emojis na Sidebar em vez de ícones Lucide | Inconsistente com o restante da UI | Migrar para Lucide na Sidebar |
| 5 | react-query e zustand instalados mas não usados | Bundle desnecessário | Remover ou adotar nos fetches existentes |
| 6 | lucide-react ausente no package.json original | Pode causar erro em builds limpos | Confirmar que lucide-react está em package.json |

### Padrões consolidados (manter)

```
✅ primary-600 (#2563eb) como cor de ação — consistente em 100% dos componentes
✅ rounded-lg (8px) em inputs/botões — visualmente confortável
✅ rounded-xl (12px) em cards — hierarquia clara
✅ rounded-full em badges — pill bem estabelecido
✅ Padrão dual md:hidden / hidden md:block — implementado em todo Financeiro e Fase E
✅ Toast fixo top-4 right-4 z-50 — não interfere com modais
✅ overflow-x-auto -mx-6 -my-4 em tabelas dentro de Card — solução elegante
✅ BRL() helper para formatação monetária — reutilizado em todo projeto
✅ stripEmptyStrings() no payload — evita strings vazias para a API
✅ window.confirm() para ações destrutivas — simples e funcional
```

---

## Referência rápida — classes mais usadas

```
Fundo app:         bg-gray-50
Sidebar:           bg-gray-900 text-white
Header:            bg-white border-b border-gray-200 h-16
Card:              bg-white rounded-xl border border-gray-200 shadow-sm
Botão primário:    bg-primary-600 text-white hover:bg-primary-700 rounded-lg font-medium
Input:             w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900
Input focus:       focus:ring-2 focus:ring-primary-500 focus:border-transparent
Badge pill:        px-2 py-0.5 rounded-full text-xs font-semibold
Título h1:         text-2xl font-bold text-gray-900
Subtítulo:         text-sm text-gray-500
Tabela header:     bg-gray-50 border-b border-gray-200 px-4 py-3 font-semibold text-gray-600
Tabela hover:      hover:bg-gray-50 divide-y divide-gray-100
Toast sucesso:     fixed top-4 right-4 z-50 bg-accent-600 text-white px-4 py-3 rounded-lg
Toast erro:        fixed top-4 right-4 z-50 bg-red-600 text-white px-4 py-3 rounded-lg
Empty state:       text-center py-12 text-gray-400 text-sm
Modal overlay:     fixed inset-0 z-50 flex items-center justify-center px-4 bg-black/50
```
