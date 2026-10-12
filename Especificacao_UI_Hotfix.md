# Especificação UI Hotfix — UidCore (Manutenção #64 [NUCLEO 3/5])
## Assinaturas: mensalidade recorrente com contrato ativo

**Autor:** Brush (MODO HOTFIX)
**Base:** `Especificacao_Hotfix.md` (Manutenção #64) + design system existente do
projeto (inferido de `pages/Compras.jsx`, `pages/Clientes.jsx`, `pages/Vendas.jsx`,
`components/ui/*`, `tailwind.config.js`). Este documento **sobrescreve** o
`Especificacao_UI_Hotfix.md` da Manutenção #63 (fase anterior do pacote NUCLEO,
já encerrada — este arquivo é sempre o retrato da fase em execução).

---

## 0. Design System do Projeto (referência — nada disto é novo)

- **Modo:** dark mode por padrão (toggle ☀️/🌙 no Header, `useTheme.js`,
  localStorage `uidcore-theme`) — ver Manutenção #31.
- **Paleta:** tokens Tailwind `navy-*` (950/900/800/700/600/500 — superfícies)
  e `violet-*` (700/600/500/400 — interação/foco), com `primary-*`/`accent-*`
  mapeados no light mode. Vermelho só para erro/destrutivo (`red-*`).
- **Fonte:** Plus Jakarta Sans (títulos) + DM Sans (corpo), via Google Fonts
  em `index.css`. **Nunca** Inter/Roboto/Arial.
- **BorderRadius padrão:** `rounded-lg` (8px) em inputs/botões, `rounded-2xl`
  (16px) em `Modal`/`Card`, `rounded-full` em badges.
- **Componentes genéricos reutilizáveis** (`components/ui/`): `Button.jsx`,
  `Card.jsx`, `Input.jsx`, `Select.jsx`, `Modal.jsx`, `Pagination.jsx`,
  `Loading.jsx`, `ResourceCrud.jsx`, `AuditFooter.jsx`.
- **Não existe** componente `Badge`/`StatusBadge` compartilhado nem
  `Autocomplete`/`FinanceiroTable` genéricos — cada página **duplica** um
  `function Badge({ status })` local com mapa de classes Tailwind (ver
  `Compras.jsx` linha ~58, citando explicitamente que copia o padrão de
  `Financeiro.jsx` em vez de importar) e uma função local de busca
  debounced tipo `ProdutoAutocomplete`/`BuscaProdutoRapida` (`Vendas.jsx`
  linha ~45/193). **Assinaturas.jsx segue exatamente essa convenção** — não
  é o momento de extrair componentes compartilhados (fora de escopo desta
  fase, é módulo isolado).
- **Padrão de página de listagem** (visto identicamente em `Compras.jsx`,
  `Clientes.jsx`, `Vendas.jsx`): toast local fixo (`fixed top-4 right-4`),
  header `flex items-center justify-between` com título h1 + subtítulo +
  botão de ação à direita, `Card` com barra de filtros (`Input` busca +
  `Select` status), depois **split mobile/desktop**: `div.md:hidden` com
  `Card` por item (mobile) e `table` tradicional (`hidden md:table`/
  `md:block`) para desktop, com estado vazio (emoji grande + texto
  cinza) e estado de loading (texto centralizado).
- **Modal de formulário:** `Modal.jsx` — props `title`, `onClose`, `maxW`
  (default `max-w-lg`), conteúdo via `children`, sem tabs nativas — qualquer
  tab dentro de modal é implementada na página (estado local `activeTab`),
  não vem de um componente `Tabs` genérico (não existe).

---

## 1. Tela: Sidebar + Rota — item de menu "Assinaturas"

RF-08/RF-09 do Analista já fixam o essencial — Brush confirma consistência
visual, sem inventar nada novo:

- Ícone: `🔁` (emoji, **não** Lucide) — Sidebar do projeto usa emojis em
  todos os itens (`📊 Dashboard`, `🧾 Compras`, `💰 Financeiro`, `🔄
  Conciliação`...), divergência já documentada e aceita como decisão de
  projeto (DIV-UI03, Manutenção #8/#9 — **não** reabrir essa discussão
  nesta fase).
- Posição no array `navItems` de `Sidebar.jsx`: logo depois de
  `{ to: '/conciliacao', ... }` e antes de `{ to: '/administrativo', ... }`
  — agrupa com os demais itens `requer: 'financeiro'` (Compras, Financeiro,
  Conciliação), mantendo a vizinhança semântica do menu.
- Gate de visibilidade: `requer: 'financeiro'` → já resolvido por
  `selectPodeAcessarFinanceiro(authStore)` — **nenhuma lógica de ícone
  condicional por perfil**, é o mesmo seletor que já oculta Compras/
  Financeiro/Conciliação para OPERACIONAL/MARKETING/PROFISSIONAL (fecha
  CA-09 na ponta visual).
- Rota: `/assinaturas` envolta em `FinanceiroRoute` (mesmo wrapper de
  `/compras`), sem layout especial — usa o `AppLayout` padrão (sidebar
  desktop fixa + bottom/collapse mobile já existente, **nunca**
  `overflow-hidden` no root).

---

## 2. Tela: `Assinaturas.jsx` (listagem principal)

### Layout geral
- Estrutura idêntica a `Compras.jsx`: toast fixo → header (título +
  subtítulo + botão) → `Card` de filtros → lista (mobile cards / desktop
  table) → `Modal` de criação/edição → `Modal` menor de confirmação de
  encerramento.
- Container raiz: `<div className="space-y-4">` (padrão de todas as
  páginas de listagem do projeto — não inventar novo espaçamento vertical).
- Padding da página: nenhum padding próprio — herdado do `AppLayout`
  (conteúdo já tem padding lateral padrão do shell).

### Cabeçalho
```jsx
<div className="flex items-center justify-between gap-3">
  <div>
    <h1 className="text-2xl font-bold text-gray-900 dark:text-slate-100">Assinaturas</h1>
    <p className="text-sm text-gray-500 dark:text-slate-400 mt-0.5">
      Mensalidades recorrentes — planos, contratos ativos e cobrança automática
    </p>
  </div>
  <Button onClick={openNovaAssinatura}>+ Nova Assinatura</Button>
</div>
```
- Título: `text-2xl font-bold` (Plus Jakarta Sans herdado do `h1` global).
- Subtítulo: `text-sm text-gray-500 dark:text-slate-400`.
- Botão: `Button` padrão (`variant` default/primary), texto `+ Nova
  Assinatura` — mesma convenção textual de `+ Nova Compra` em
  `Compras.jsx` (não usar ícone `Plus` dentro do próprio `Button` aqui,
  já que nenhuma outra listagem do projeto faz isso no botão de header —
  só o texto com `+`).

### Barra de filtros (dentro de `Card`)
```jsx
<Card>
  <div className="flex flex-wrap gap-3">
    <div className="flex-1 min-w-[200px]">
      <Input placeholder="Buscar por cliente..." value={search} onChange={...} />
    </div>
    <div className="w-48">
      <Select options={STATUS_FILTRO_OPTIONS} value={statusFiltro} onChange={...} />
    </div>
  </div>
</Card>
```
- `STATUS_FILTRO_OPTIONS`: `[{value:'', label:'Todos'}, {value:'ATIVA',
  label:'Ativa'}, {value:'PAUSADA', label:'Pausada'}, {value:'ENCERRADA',
  label:'Encerrada'}]` — mesmo shape de `STATUS_FILTRO_OPTIONS` em
  `Compras.jsx`.
- Busca por cliente: `search` dispara `GET
  /api/v1/assinaturas/assinaturas/?search=<termo>` (ou `?cliente__nome=`
  conforme o Forge exponha — Brush não define contrato de API, só o
  campo de UI) com `setPage(1)` ao digitar, igual padrão de `Compras.jsx`.

### Lista — Mobile (`<768px`, `div.flex.flex-col.gap-3.md:hidden`)
Cada item em `Card`:
```jsx
<Card key={item.id}>
  <div className="flex items-start justify-between gap-2">
    <div className="min-w-0">
      <p className="font-medium text-gray-800 dark:text-slate-200 truncate">{item.cliente_nome}</p>
      <p className="text-xs text-gray-400 dark:text-slate-500">
        {item.plano_nome} · vence dia {item.dia_vencimento}
      </p>
    </div>
    <Badge status={item.status} />
  </div>
  <div className="flex items-center justify-between mt-2">
    <span className="font-semibold text-gray-800 dark:text-slate-200">{BRL(item.valor)}</span>
    <div className="flex gap-3">
      <button onClick={() => openEditar(item)} className="text-gray-400 dark:text-slate-500">
        <Pencil size={16} />
      </button>
      {item.status !== 'ENCERRADA' && (
        <button onClick={() => togglePausarRetomar(item)} className="text-gray-400 dark:text-slate-500">
          {item.status === 'ATIVA' ? <PauseCircle size={16} /> : <PlayCircle size={16} />}
        </button>
      )}
      {item.status !== 'ENCERRADA' && (
        <button onClick={() => abrirModalEncerrar(item)} className="text-gray-400 dark:text-slate-500">
          <XCircle size={16} />
        </button>
      )}
    </div>
  </div>
</Card>
```

### Lista — Desktop (`table` padrão `hidden md:block`, igual `Compras.jsx`)
Colunas sugeridas (larguras relativas):
| Coluna | Conteúdo | Largura |
|---|---|---|
| Cliente | `item.cliente_nome` | flex |
| Plano | `item.plano_nome` | 18% |
| Valor | `BRL(item.valor)` | 12%, alinhado à direita |
| Vencimento | `dia {item.dia_vencimento}` | 10% |
| Status | `<Badge status={item.status} />` | 12%, centralizado |
| Ações | ícones (ver abaixo) | 14%, centralizado |

Cada linha: `<tr className="border-b border-gray-100 dark:border-navy-700 hover:bg-gray-50 dark:hover:bg-navy-700/30">`
(hover sutil, mesmo padrão de todas as tabelas do projeto).

### Ícones (Lucide React — padrão já em uso no projeto, nunca emoji em ação de linha)
| Ação | Ícone | Tamanho | Observação |
|---|---|---|---|
| Nova Assinatura | — (texto `+ Nova Assinatura` no `Button`, sem ícone) | — | consistente com `+ Nova Compra` |
| Editar | `<Pencil />` | 16px | mesmo ícone de ação de edição já usado no projeto |
| Pausar (quando `status=ATIVA`) | `<PauseCircle />` | 16px | novo no projeto — `lucide-react` já é dependência, ícone existe no pacote |
| Retomar (quando `status=PAUSADA`) | `<PlayCircle />` | 16px | contraponto visual direto do Pausar — fica óbvio o toggle |
| Encerrar | `<XCircle />` | 16px | ação terminal — cor neutra na listagem (não vermelha na linha, só confirma gravidade dentro do modal, RN-07) |
| Estado vazio | `<span className="text-4xl">🔁</span>` (emoji grande, igual padrão `📦`/`🏭` já usado) | — | consistência com `Compras.jsx`/`Clientes.jsx` |

> Nota: `Pencil`, `Trash2`, `Search`, `Plus`, `Eye`, `Ban`, `User`,
> `Building2`, `ArrowRight`, `Gift`, `Package`, `Store`, `ClipboardList`
> já são os únicos ícones Lucide importados hoje no projeto (grep
> confirmado em `Clientes.jsx`, `Compras.jsx`, `Produtos.jsx`,
> `Vendas.jsx`). `PauseCircle`/`PlayCircle`/`XCircle` são novos nesta
> fase — **confirmar no `package.json` que `lucide-react` já contém esses
> ícones** (faz parte do pacote padrão da lib, não precisa de upgrade de
> versão) antes do Loom importar.

### Badge de status (duplicar o padrão local, não importar)
```jsx
const STATUS_BADGES = {
  ATIVA: 'bg-green-100 text-green-800 dark:bg-emerald-900/30 dark:text-emerald-300',
  PAUSADA: 'bg-yellow-100 text-yellow-800 dark:bg-amber-900/30 dark:text-amber-300',
  ENCERRADA: 'bg-gray-100 text-gray-600 dark:bg-navy-700 dark:text-slate-400',
}
function Badge({ status }) {
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${STATUS_BADGES[status] || STATUS_BADGES.ENCERRADA}`}>
      {status}
    </span>
  )
}
```
Exatamente as mesmas classes/tons já usados para `PENDENTE`/`PAGO`/
`CANCELADO` em `Compras.jsx` — ATIVA reaproveita o verde de PAGO, PAUSADA
reaproveita o amarelo de PENDENTE, ENCERRADA reaproveita o cinza de
CANCELADO. Zero paleta nova.

### Estado vazio / loading
```jsx
{loading ? (
  <div className="text-center py-12 text-gray-400 dark:text-slate-500 text-sm">Carregando...</div>
) : items.length === 0 ? (
  <div className="flex flex-col items-center justify-center py-12 gap-2 text-gray-400 dark:text-slate-500">
    <span className="text-4xl">🔁</span>
    <p className="text-sm">Nenhuma assinatura cadastrada.</p>
  </div>
) : ( /* lista */ )}
```

---

## 3. Modal "Nova Assinatura" / Editar

- Componente: `Modal` (`maxW="max-w-lg"` — formulário médio, mesmo porte
  do modal de Compra/Cliente, não precisa de `max-w-2xl`).
- Título: `"Nova Assinatura"` (criação) / `"Editar Assinatura"` (edição) —
  mesmo padrão de título dinâmico condicional já usado em todo modal do
  projeto.
- Campos, em ordem, cada um com `Input`/`Select` padrão (label acima,
  mesma estrutura de `components/ui/Input.jsx`/`Select.jsx`):

1. **Cliente** — campo de busca/autocomplete local (reaproveitar o padrão
   de função debounced tipo `ProdutoAutocomplete` de `Vendas.jsx`, adaptado
   para `GET /api/v1/clientes/?search=`): input de texto com dropdown de
   resultados abaixo (`position: absolute`, **nunca** `position: fixed`
   dentro deste modal pequeno — ele não tem o problema de overflow-clip de
   modais grandes com scroll interno, mas ainda assim usar `z-10` no
   dropdown para garantir que fique acima do restante do form). Ao
   selecionar, grava `cliente_id` + mostra nome selecionado com botão "✕"
   para trocar.
2. **Plano** — `Select` populado via `GET /api/v1/assinaturas/planos/?ativo=true`
   (só planos `ativo=True`, RF-02). Ao mudar, **pré-preenche** o campo
   `valor` abaixo com `plano.valor` (editável depois — snapshot, RF-03).
3. **Valor** — `Input type="number" step="0.01"` com label "Valor (R$)",
   pré-preenchido pelo passo 2, editável (desconto negociado).
4. **Dia de vencimento** — `Input type="number" min={1} max={28}` label
   "Dia do vencimento" + texto de ajuda pequeno abaixo (`text-xs
   text-gray-400 dark:text-slate-500`): "Entre 1 e 28 — evita problema em
   meses com menos dias".
5. **Data início** — `Input type="date"` label "Início".
6. **Data fim (opcional)** — `Input type="date"` label "Fim (opcional)" +
   texto de ajuda: "Deixe em branco para contrato sem prazo definido".
7. **Conta** — `Select` populado via `GET /api/v1/financeiro/contas/?is_active=true`
   label "Conta de destino" (conta onde a Receita mensal vai cair).

- Rodapé do modal: `Button variant="secondary"` "Cancelar" + `Button`
  "Salvar" (mesmo par de botões de todo modal do projeto, alinhados à
  direita, `flex justify-end gap-2 mt-5`).
- Em modo edição, campo **Plano** e **Cliente** ficam bloqueados
  (`disabled`) — trocar cliente/plano de uma assinatura ativa não é um
  caso de uso coberto pelo backend (RF-03 trata valor como snapshot, não
  há endpoint de "migrar assinatura para outro plano"); se o usuário
  precisar trocar, o fluxo correto é Encerrar + criar nova (RN-07,
  coerente com o estado terminal documentado).

---

## 4. Modal "Encerrar Assinatura" (ação de linha, RF-10)

Modal pequeno e distinto do modal de edição — ação **sem volta** (RN-07),
precisa de fricção visual proposital:

- Componente: `Modal` (`maxW="max-w-sm"` — bem menor que o de formulário,
  reforça "isso é uma confirmação, não um cadastro").
- Título: `"Encerrar Assinatura"`.
- Corpo:
  - Texto de alerta: `"Encerrar a assinatura de {cliente_nome}? Essa ação
    não pode ser desfeita — a assinatura para de gerar cobrança a partir
    da data informada."` em `text-sm text-gray-600 dark:text-slate-300`.
  - Campo **Data de encerramento** — `Input type="date"`, label "A partir
    de" (vira `data_fim` no payload).
  - Campo **Motivo** — `<textarea>` com mesmas classes visuais do `Input`
    padrão (borda/foco idênticos — projeto não tem `Textarea.jsx` próprio,
    então replicar inline as classes de `Input.jsx`), label "Motivo do
    encerramento", `rows={3}`.
- Botão de confirmação em destaque de risco: `Button` com classe adicional
  de cor de alerta (`bg-red-600 hover:bg-red-700 text-white` — **não**
  `variant="danger"` porque esse variant não existe em `Button.jsx` hoje;
  usar `className` extra sobre o `Button` padrão, mesmo truque usado em
  outros pontos do projeto para ação destrutiva pontual) + texto
  `"Confirmar encerramento"`.
- **Sem** `window.confirm()` nativo do browser — o próprio modal com
  texto de alerta já cumpre o papel de "guard antes de chamar a action"
  pedido no RF-10; `window.confirm` style (mencionado no texto do
  Analista) é satisfeito pela fricção do modal dedicado, não por um
  `window.confirm()` real (UX melhor, consistente com o resto do projeto
  que já evita `window.confirm` nativo em ações críticas — ver
  `Compras.jsx` que usa `window.confirm` só para cancelamento simples de
  1 linha, mas aqui o encerramento tem 2 campos obrigatórios, não cabe em
  um `confirm()` de texto único).

---

## 5. Aba "Assinaturas" na ficha do Cliente (RF-11)

`Clientes.jsx` hoje **não tem** uma "ficha" de detalhe com abas — só um
`Modal` único reaproveitado para criar/editar (confirmado lendo o arquivo:
um só `<Modal>` no fim do componente, sem sistema de tabs). RF-11 pede
"tela/modal de ficha" — a interpretação de menor atrito com o padrão
existente é **adicionar abas dentro do modal de edição já existente**,
visíveis só quando `editingId` está preenchido (cliente já existe — não
faz sentido mostrar assinaturas de um cliente que ainda não foi salvo):

### Layout
```jsx
{editingId && (
  <div className="flex gap-1 border-b border-gray-200 dark:border-navy-600 mb-4 -mt-1">
    <button
      onClick={() => setAbaFicha('dados')}
      className={`px-3 py-2 text-sm font-medium border-b-2 transition-colors ${
        abaFicha === 'dados'
          ? 'border-violet-500 text-violet-600 dark:text-violet-400'
          : 'border-transparent text-gray-400 dark:text-slate-500 hover:text-gray-600 dark:hover:text-slate-300'
      }`}
    >
      Dados
    </button>
    <button
      onClick={() => setAbaFicha('assinaturas')}
      className={/* mesma lógica, chave 'assinaturas' */}
    >
      Assinaturas
    </button>
  </div>
)}

{(!editingId || abaFicha === 'dados') && ( /* formulário atual, sem mudança */ )}
{editingId && abaFicha === 'assinaturas' && <AbaAssinaturasCliente clienteId={editingId} />}
```
- Estilo do seletor de aba: sublinhado (`border-b-2`), cor ativa
  `violet-500`/`violet-400` (dark) — é o primeiro uso de tabs dentro de
  `Clientes.jsx`, então Brush define aqui o padrão em vez de inferir de
  outro lugar; usa a cor de interação (`violet`) já estabelecida em todo
  o projeto para estado ativo/foco (mesma família de cor do anel de foco
  de `Select.jsx`/`Input.jsx`), não uma cor nova.
- Ao fechar o modal (`closeModal`), resetar `abaFicha` para `'dados'` —
  próxima abertura (de qualquer cliente) sempre começa na aba Dados.

### Conteúdo da aba "Assinaturas" (somente leitura, RF-11 explícito)
Sub-componente `AbaAssinaturasCliente`:
- Busca `GET /api/v1/assinaturas/assinaturas/?cliente=<id>` ao montar.
- **Sem** `Card` wrapper extra (já está dentro do `Modal`, que já tem
  padding) — lista direta.
- Cada assinatura do cliente, bloco compacto:
  ```jsx
  <div className="flex items-center justify-between py-2 border-b border-gray-100 dark:border-navy-700 last:border-0">
    <div>
      <p className="text-sm font-medium text-gray-800 dark:text-slate-200">{assinatura.plano_nome}</p>
      <p className="text-xs text-gray-400 dark:text-slate-500">
        {BRL(assinatura.valor)} · vence dia {assinatura.dia_vencimento}
      </p>
    </div>
    <Badge status={assinatura.status} />
  </div>
  ```
- Abaixo da lista de assinaturas, seção "Cobranças geradas" (título
  `text-xs font-semibold uppercase text-gray-400 dark:text-slate-500
  mt-4 mb-2`), listando as `Receita`s vinculadas
  (`?assinatura__cliente=<id>` conforme RF-11 do Analista), cada linha
  compacta: `referencia_mes` formatado (ex: "Nov/2026") + `BRL(valor_bruto)`
  + badge de status da Receita (reaproveitar o `Badge` de status já
  descrito, com as chaves de `Receita.status` — `PENDENTE`/`RECEBIDO`/
  etc., **não** as chaves de `Assinatura.status` — são badges visualmente
  idênticos mas semanticamente de domínios diferentes, não confundir ao
  implementar).
- Estado vazio desta aba (cliente sem nenhuma assinatura): texto simples
  centralizado `"Nenhuma assinatura para este cliente."`, sem emoji
  grande (é um bloco pequeno dentro de modal, não uma página — manter
  compacto, emoji grande ficaria desproporcional aqui).
- **Nenhum botão de ação** nesta aba (nem editar, nem pausar, nem
  encerrar) — RF-11 é explícito: ações de mutação continuam centralizadas
  em `Assinaturas.jsx`. Se o usuário quiser agir, sai do modal de Cliente
  e vai para a tela Assinaturas (nenhum deep-link automático nesta fase —
  fora de escopo, RF-11 não pede).

---

## 6. Mobile-first (breakpoint 375px)

- **Assinaturas.jsx:** filtros em `flex-wrap` já quebram naturalmente para
  coluna única em telas pequenas (mesma classe `flex flex-wrap gap-3` de
  `Compras.jsx`, testado e aprovado nas fases anteriores — não reinventar).
  Lista em `Card`s empilhados (`flex flex-col gap-3 md:hidden`), sem grid.
- **Modal de Nova/Editar Assinatura:** `Modal` já é responsivo por padrão
  (`w-full max-w-lg px-4` no overlay) — campos em coluna única, sem
  necessidade de grid 2 colunas (formulário tem 7 campos simples, cabe
  bem em coluna única mesmo no desktop; não forçar layout 2-colunas só
  porque há espaço — mantém consistência com o modal de Compra, que
  também é coluna única para o grupo de campos principais).
- **Aba Assinaturas no Cliente:** o seletor de abas (`Dados`/`Assinaturas`)
  usa `flex gap-1` — em 375px os dois botões cabem lado a lado sem quebrar
  (textos curtos), não precisa de `overflow-x-auto`.
- **Dropdown do autocomplete de Cliente** (dentro do modal de Assinatura):
  `w-full` dentro do container do campo, nunca `w-screen`/`fixed` — o modal
  já é pequeno (`max-w-lg`) e não tem scroll interno complexo o suficiente
  para justificar `position: fixed` com `getBoundingClientRect()` (esse
  truque, usado em `ProdutoAutocomplete`, resolve corte em modais grandes
  com `overflow-y-auto` agressivo — o modal de Assinatura é curto, 7
  campos, não deve ter esse problema; se o Loom notar corte na prática,
  aplicar o mesmo fix de `position: fixed`, mas não antecipar
  complexidade que pode não existir aqui).

---

## 7. O que NÃO fazer (reforço das armadilhas do projeto)

```
❌ NÃO criar componente Badge/StatusBadge compartilhado — duplicar local, como todo o resto do projeto já faz
❌ NÃO criar componente Autocomplete/Tabs genérico em components/ui/ — fora de escopo desta fase isolada
❌ NÃO usar ícone Lucide no item de Sidebar — é emoji (🔁), igual todos os outros itens
❌ NÃO usar window.confirm() nativo para o Encerrar — modal dedicado com 2 campos obrigatórios
❌ NÃO permitir trocar Plano/Cliente em assinatura já existente — não há endpoint para isso (RF-03 é snapshot)
❌ NÃO misturar Badge de status de Assinatura com Badge de status de Receita — mesma aparência, chaves de cor diferentes, não reaproveitar o mesmo objeto STATUS_BADGES
❌ NÃO adicionar overflow-hidden em nenhum container novo desta fase (regra global do SistemaLayout/AppLayout)
❌ NÃO esquecer Plus Jakarta Sans/DM Sans — são herdadas globalmente via index.css, nenhuma declaração de fonte nova necessária nesta fase
```

---

## 8. Passagem de bastão

```
✅ Especificação UI concluída — UidCore (Manutenção #64 [NUCLEO 3/5])
   Telas analisadas: 3 (Sidebar/rota, Assinaturas.jsx listagem+modais, aba Assinaturas na ficha do Cliente)
   Componentes reutilizados: Card, Button, Input, Select, Modal, AuditFooter (indireto via AuditMixin), padrão Badge-local, padrão autocomplete-local
   Novos padrões: tabs dentro de Modal (Dados/Assinaturas em Clientes.jsx) — primeira ocorrência no projeto, documentado acima; ícones PauseCircle/PlayCircle/XCircle (novos no projeto, já no pacote lucide-react)
   Modo: Padrão Uid (dark mode navy/violet já estabelecido, nenhuma identidade nova)

📁 Arquivo: Especificacao_UI_Hotfix.md (em /var/www/uidcore, sobrescreve a versão da Manutenção #63)

➡️ Loom lê Especificacao_Hotfix.md + Especificacao_UI_Hotfix.md antes de implementar
   Assinaturas.jsx, a aba na ficha do Cliente e o item de Sidebar/rota.
```
