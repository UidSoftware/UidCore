# Especificação UI Hotfix — UidCore (Manutenção #58, Fase 2)

**Módulo novo:** `compras` — `frontend/src/pages/Compras.jsx` (arquivo novo)
**Base:** `Especificacao_Hotfix.md` (Manutenção #58, Fase 2) — RF-01 a RF-11, RN-01 a RN-08

---

## Design System do Projeto (referência)

Mesma fonte de verdade já usada na Fase 1 (`Especificacao_UI_Hotfix.md` anterior
foi substituído por este arquivo — conteúdo da Fase 1 preservado no histórico
de commits, não neste documento): `tailwind.config.js` + páginas já
implementadas (`Financeiro.jsx`, `Vendas.jsx`, `Produtos.jsx`, `pdv/*`). Esta
tela **não introduz nenhum token novo** — é composição do que já existe em 3
telas diferentes do projeto.

- **Cores primárias (light):** `primary-600` — botão primário (`Nova Compra`,
  `Confirmar`), links de ação, foco de input/select.
- **Cores de ação (dark):** `violet-400`/`violet-500` — equivalente dark.
- **Cores de fundo:**
  - App/modal: `bg-white` / `dark:bg-navy-800` (corpo do `Modal`, `rounded-2xl`,
    `shadow-xl`).
  - Card de listagem (linha mobile) e seções agrupadoras do formulário
    (cabeçalho da compra, seção "Itens"): `bg-gray-50 dark:bg-navy-900/50`,
    borda `border-gray-200 dark:border-navy-700`, `rounded-lg p-4`.
  - Sub-card (linha de item dentro do carrinho): `bg-white dark:bg-navy-800`,
    borda `border-gray-200 dark:border-navy-600`, `rounded-lg p-3`.
  - Campo "Total" read-only (subtotal do item, total geral): `bg-gray-50
    dark:bg-navy-900`, borda `border-gray-200 dark:border-navy-700` — mesmo
    tom "desabilitado" já usado no `Total (R$)` de `SecaoItens` em
    `Vendas.jsx`.
- **Texto:**
  - Título de página: `text-lg font-semibold text-gray-800 dark:text-slate-200`
    (padrão `<h2>` de todas as listagens — `Orcamentos`, `Pedidos`, etc.).
  - Título de seção interna do modal: `text-sm font-semibold text-gray-700
    dark:text-slate-200`.
  - Label de campo: `text-sm font-medium text-gray-700 dark:text-slate-300`
    (padrão `Input`/`Select`).
  - Muted/caption: `text-xs text-gray-400 dark:text-slate-500`.
  - Erro inline (por item/campo): `text-xs text-red-600 dark:text-red-400`.
- **Fonte:** Plus Jakarta Sans (headings) + DM Sans (body) — já carregadas
  globalmente, nenhuma ação aqui.
- **BorderRadius:** `rounded-lg` (cards, inputs, sub-cards) / `rounded-2xl`
  (moldura do `Modal`, já no componente) / `rounded-full` (badges de status)
  — mesmos valores já em uso, não introduzir `rounded-md`/`rounded-xl`.
- **Componentes a reutilizar (não recriar):** `Card`, `Input`, `Select`,
  `Button`, `Modal`, `Pagination` (`frontend/src/components/ui/`). A listagem
  **não** usa `ResourceCrud` genérico — RN-05 (Compra imutável, sem
  PUT/PATCH de itens) e o formato "carrinho" da criação não cabem no
  contrato de formulário plano do `ResourceCrud` (mesmo motivo por que
  `Vendas.jsx` — Orçamento/Pedido — já não usa `ResourceCrud` e implementa
  listagem + modal próprios). `Compras.jsx` segue o mesmo molde de
  `Vendas.jsx`: estado próprio de listagem (busca, paginação, filtro) +
  modal de criação com `SecaoItens`-like embutida.
- **Ícones:** `lucide-react`. Reaproveitar exatamente o que `Vendas.jsx` já
  importa (`Plus`, `Trash2`) e adicionar os novos desta tela (ver seção
  Ícones).
- **Item de menu (Sidebar):** emoji, **não** ícone Lucide — convenção já
  documentada como decisão de projeto (DIV-UI03, Manutenção #10/#38): todo
  item de `frontend/src/components/layout/Sidebar.jsx` usa emoji, nunca
  `lucide-react`. Não trocar o padrão da Sidebar inteira só por causa desta
  tela nova.

---

## Tela 1 — Lista de Compras (`/compras`)

Mesmo esqueleto de página das listagens com modal próprio (`Vendas.jsx` —
Orçamentos/Pedidos): `<h2>` + botão `+ Nova Compra` no cabeçalho, `Card` com
campo de busca, tabela desktop / cards mobile, paginação.

### Cabeçalho

```jsx
<div className="flex items-center justify-between gap-3">
  <h2 className="text-lg font-semibold text-gray-800 dark:text-slate-200">Compras</h2>
  <Button onClick={openNovaCompra}>+ Nova Compra</Button>
</div>
```

### Filtros (`Card`)

Linha única, `flex flex-wrap gap-3` (colapsa em coluna via wrap natural em
mobile, sem precisar de `flex-col` explícito — mesmo comportamento já usado
no filtro de contas do Financeiro):

- `Input` busca livre (`placeholder="Buscar por NF ou fornecedor..."`) →
  `search` do backend (`numero_nota_fiscal`, `fornecedor__nome_razao_social`).
- `Select` Status: `[Todos, Pendente, Pago, Cancelado]` → `status` do backend.
- Sem filtro de fornecedor dedicado nesta fase (busca livre já cobre nome do
  fornecedor via `search_fields` do backend) — evita um segundo campo
  redundante com a busca.

### Tabela desktop (`hidden md:table` — mesmo breakpoint de todas as
listagens do projeto)

| Coluna | Conteúdo | Alinhamento |
|---|---|---|
| Fornecedor | `item.fornecedor_nome` | esquerda |
| Nota Fiscal | `item.numero_nota_fiscal \|\| '—'` | esquerda |
| Data Emissão | `dd/mm/aaaa` (mesma função de formatação de data já usada no projeto) | esquerda |
| Valor Total | `BRL(item.valor_total)`, `font-medium` | direita |
| Status | `<Badge status={item.status} />` (ver abaixo) | centro |
| Ações | ícone `Eye` (ver detalhe) + ícone `Ban` (cancelar, só se `status !== 'CANCELADO'`) | direita |

```jsx
<td className="px-4 py-3 text-right">
  <div className="flex justify-end gap-3">
    <button onClick={() => abrirDetalhe(item)} title="Ver detalhes"
      className="text-gray-400 hover:text-primary-600 transition-colors dark:text-slate-500 dark:hover:text-violet-400">
      <Eye size={16} />
    </button>
    {item.status !== 'CANCELADO' && (
      <button onClick={() => confirmarCancelamento(item)} title="Cancelar compra"
        className="text-gray-400 hover:text-red-600 transition-colors dark:text-slate-500 dark:hover:text-red-400">
        <Ban size={16} />
      </button>
    )}
  </div>
</td>
```

### Cards mobile (`flex flex-col gap-3 md:hidden` — mesmo padrão de
`Vendas.jsx`)

```jsx
<Card key={item.id}>
  <div className="flex items-start justify-between gap-2">
    <div className="min-w-0">
      <p className="font-medium text-gray-800 dark:text-slate-200 truncate">{item.fornecedor_nome}</p>
      <p className="text-xs text-gray-400 dark:text-slate-500">
        NF {item.numero_nota_fiscal || '—'} · {formatData(item.data_emissao)}
      </p>
    </div>
    <Badge status={item.status} />
  </div>
  <div className="flex items-center justify-between mt-2">
    <span className="font-semibold text-gray-800 dark:text-slate-200">{BRL(item.valor_total)}</span>
    <div className="flex gap-3">
      <button onClick={() => abrirDetalhe(item)} className="text-gray-400 dark:text-slate-500"><Eye size={16} /></button>
      {item.status !== 'CANCELADO' && (
        <button onClick={() => confirmarCancelamento(item)} className="text-gray-400 dark:text-slate-500"><Ban size={16} /></button>
      )}
    </div>
  </div>
</Card>
```

### Badge de Status — reaproveita 100% o padrão já em produção

`financeiro/Financeiro.jsx` já define `STATUS_BADGES`/`Badge` com as
**mesmas três chaves** que `Compra.status` usa (`PENDENTE`, `PAGO`,
`CANCELADO`) — não inventar cores novas, copiar exatamente:

```jsx
const STATUS_BADGES = {
  PENDENTE: 'bg-yellow-100 text-yellow-800 dark:bg-amber-900/30 dark:text-amber-300',
  PAGO: 'bg-green-100 text-green-800 dark:bg-emerald-900/30 dark:text-emerald-300',
  CANCELADO: 'bg-gray-100 text-gray-600 dark:bg-navy-700 dark:text-slate-400',
}

function Badge({ status }) {
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${STATUS_BADGES[status] || 'bg-gray-100 text-gray-600 dark:bg-navy-700 dark:text-slate-400'}`}>
      {status}
    </span>
  )
}
```

- Copiar o objeto/função dentro de `Compras.jsx` (mesmo padrão de
  duplicação já aceito no projeto — `Vendas.jsx` também tem seu próprio
  `STATUS_BADGES` local em vez de importar de `Financeiro.jsx`, evita
  acoplamento entre páginas). **Não** extrair para componente compartilhado
  nesta fase — fora de escopo, três páginas já duplicam o mesmo padrão.

### Ação Cancelar (RF-10)

`window.confirm` + prompt de motivo — mesma técnica nativa já usada em
`Produtos.jsx` (Fase 1, fluxo de estoque negativo) e consistente com
"sem `ConfirmDialog` customizado" documentado nas Armadilhas do Brush:

```jsx
async function confirmarCancelamento(item) {
  if (!window.confirm(`Cancelar a compra de ${item.fornecedor_nome} no valor de ${BRL(item.valor_total)}?`)) return
  try {
    await api.post(`/compras/${item.id}/cancelar/`)
    showToast('Compra cancelada. Estoque revertido.', 'success')
    fetch()
  } catch (err) {
    showToast(extractErrorMessage(err, 'Erro ao cancelar compra.'), 'error')
  }
}
```

- Sem campo de "motivo" digitável nesta ação — `Especificacao_Hotfix.md`
  (RF-10) não pede motivo no cancelamento de Compra (diferente do estorno de
  Despesa avulsa, que já pede motivo em `DespesaViewSet.estornar_despesa`); o
  `window.confirm` já é a barreira de segurança suficiente para esta ação,
  não duplicar um segundo prompt de texto sem exigência no backend.
- Após sucesso: toast mencionando "Estoque revertido" — reforça
  visualmente o efeito colateral (RF-10.2) que não é óbvio só pela mudança
  de badge.

### Estado vazio / carregando

Mesmo padrão de `Vendas.jsx`:
- Carregando: `"Carregando..."`, `text-center py-12 text-gray-400 dark:text-slate-500 text-sm`.
- Vazio: ícone `📦` (emoji, consistente com o emoji já usado no item de menu
  Produtos — Compra é originada de estoque/mercadoria) + `"Nenhuma compra
  registrada."`.

---

## Tela 2 — Modal "Nova Compra" (carrinho)

`Modal` com `maxW="max-w-2xl"` (mesma largura maior já usada em modais com
seção de itens — `Vendas.jsx` Orçamento/Pedido, `Produtos.jsx` edição).

### Cabeçalho do formulário (fora da seção de itens)

Grid `grid grid-cols-1 sm:grid-cols-2 gap-4` (2 colunas em desktop, empilha
em mobile — mesmo breakpoint de todos os formulários do projeto):

```jsx
<div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
  <Select label="Fornecedor" name="fornecedor" required
    options={[{ value: '', label: 'Selecione...' }, ...fornecedoresOptions]}
    value={form.fornecedor} onChange={handleChange} />
  <Select label="Conta" name="conta" required
    options={[{ value: '', label: 'Selecione...' }, ...contasOptions]}
    value={form.conta} onChange={handleChange} />
  <Input label="Número da Nota Fiscal" name="numero_nota_fiscal"
    value={form.numero_nota_fiscal} onChange={handleChange} placeholder="NF-e 00001..." />
  <Input label="Data de Emissão" name="data_emissao" type="date" required
    value={form.data_emissao} onChange={handleChange} />
  <Select label="Forma de Pagamento" name="forma_pagamento"
    options={FORMA_PAGAMENTO} value={form.forma_pagamento} onChange={handleChange} />
  <Select label="Status Inicial" name="status" required
    options={[{ value: 'PENDENTE', label: 'Pendente' }, { value: 'PAGO', label: 'Pago' }]}
    value={form.status} onChange={handleChange} />
</div>
```

- `fornecedoresOptions` e `contasOptions`: **`Select` simples com lista
  pré-carregada** (`api.get('/fornecedores/').then(...)` e
  `api.get('/financeiro/contas/').then(...)` no `useEffect` de montagem da
  página, mesmo padrão de `clientesOptions` em `Vendas.jsx` e `contasOptions`
  em `Financeiro.jsx`) — **não** usar um componente de autocomplete com
  busca por digitação aqui. Decisão: cadastro de Fornecedor (como Cliente)
  tende a ser uma lista pequena/média que cabe inteira num `<select>` nativo
  sem paginação — diferente de Produto, cujo catálogo pode ser grande e por
  isso usa busca (`ProdutoAutocomplete`/`BuscaProdutoRapida`). Reaproveita
  exatamente o padrão já validado em produção para Cliente/Conta, sem
  introduzir um terceiro padrão de seleção nesta tela.
- `FORMA_PAGAMENTO`: mesmo array já definido em `Financeiro.jsx` (`PIX`,
  `TED/DOC`, `Boleto`, `Cartão Débito`, `Cartão Crédito`, `Dinheiro`,
  `Outro`) — copiar o array local em `Compras.jsx`, não importar entre
  páginas (mesmo padrão de duplicação aceito no projeto, ver nota do Badge
  acima).
- `Status Inicial` **não** lista `Cancelado` — só o usuário pode escolher
  `Pendente`/`Pago` na criação (RN-06, cancelamento é sempre via ação
  dedicada depois de já criada).
- Nenhum destes 6 campos usa `grid-cols-3` — 2 colunas cabem melhor no
  `max-w-2xl` do modal sem espremer os labels mais longos ("Número da Nota
  Fiscal", "Forma de Pagamento").

### Seção "Itens" (carrinho) — reaproveita `SecaoItens`/`BuscaProdutoRapida`
de `Vendas.jsx` quase sem alteração

```jsx
<div className="bg-gray-50 rounded-lg border border-gray-200 p-4 mt-4 dark:bg-navy-900/50 dark:border-navy-700">
  <div className="flex items-center justify-between mb-3">
    <h3 className="text-sm font-semibold text-gray-700 dark:text-slate-200">Itens</h3>
  </div>

  <BuscaProdutoRapida onAdicionar={adicionarItemComProduto} />

  {itens.length === 0 && (
    <p className="text-xs text-gray-400 dark:text-slate-500">Nenhum item adicionado.</p>
  )}

  <div className="space-y-3">
    {itens.map((it, idx) => (
      <div key={idx} className="bg-white rounded-lg border border-gray-200 p-3 space-y-2 dark:bg-navy-800 dark:border-navy-600">
        <div className="flex items-center justify-between">
          <p className="text-sm font-medium text-gray-800 dark:text-slate-200 truncate">{it.produto_nome}</p>
          <button type="button" onClick={() => removeItem(idx)}
            className="text-red-400 hover:text-red-600 transition-colors dark:text-red-400/70 dark:hover:text-red-400 shrink-0">
            <Trash2 size={14} />
          </button>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          <Input label="Quantidade" type="number" min="0.001" step="0.001"
            value={it.quantidade} onChange={(e) => updateItem(idx, 'quantidade', e.target.value)} />
          <Select label="Unidade" options={unidadeOptionsDoProduto(it)}
            value={it.unidade} onChange={(e) => updateItem(idx, 'unidade', e.target.value)} />
          <Input label="Valor Unit. Custo (R$)" type="number" min="0.01" step="0.01"
            value={it.valor_unitario_custo} onChange={(e) => updateItem(idx, 'valor_unitario_custo', e.target.value)} />
          <div className="flex flex-col gap-1">
            <label className="text-sm font-medium text-gray-700 dark:text-slate-300">Subtotal</label>
            <div className="w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-700 dark:border-navy-700 dark:bg-navy-900 dark:text-slate-300">
              {BRL(it.quantidade * it.valor_unitario_custo)}
            </div>
          </div>
        </div>
        {it.erroUnidade && (
          <p className="text-xs text-red-600 dark:text-red-400">{it.erroUnidade}</p>
        )}
      </div>
    ))}
  </div>

  {itens.length > 0 && (
    <div className="mt-3 flex justify-end">
      <span className="text-sm font-bold text-gray-800 dark:text-slate-200">
        Total Geral: {BRL(totalGeral)}
      </span>
    </div>
  )}
</div>
```

- `BuscaProdutoRapida` (componente já existente em `Vendas.jsx`, linha
  ~192): copiar o componente **sem alteração de lógica** para
  `Compras.jsx` (mesmo padrão de reaproveitamento por cópia já usado entre
  Vendas/PDV — os dois arquivos já duplicam essa função hoje, não existe
  módulo compartilhado de componentes de página ainda; extrair para
  `components/` compartilhado é refinamento futuro, fora de escopo desta
  fase). Ao clicar num resultado, `adicionarItemComProduto` cria a linha já
  com `produto_nome`, `unidade` default = `unidade_base` do produto e
  `valor_unitario_custo` pré-preenchido com `produto.valor_unitario` (último
  custo conhecido — RF-05), que o usuário pode ajustar antes de confirmar.
- `Select Unidade`: opções = `unidade_base` do produto + suas `conversoes`
  cadastradas — **mesmo padrão de resolução de opções já usado no campo de
  conversão de `Produtos.jsx`** (`resolverFatorBase`/lista de conversões do
  produto). Requer que `BuscaProdutoRapida`/`adicionarItemComProduto` também
  busque `GET /produtos/{id}/conversoes/` no momento de adicionar o item
  (mesma chamada já feita em `Produtos.jsx` ao abrir o modal de edição) —
  guardar o resultado por item (`it.conversoes`) para popular o `Select`
  sem repetir requisição a cada render.
- `Subtotal` por linha: **somente exibição**, calculado no frontend
  (`quantidade × valor_unitario_custo`) — nunca enviado como campo separado
  no payload (o backend recalcula, RF-06). Mesmo tom "desabilitado" (`bg-gray-50
  dark:bg-navy-900`) do campo `Total (R$)` já usado em `SecaoItens` de
  `Vendas.jsx`.
- `it.erroUnidade`: preenchido a partir da resposta `400` de
  `itens[i].unidade` do backend (RN-01/CA-13) — exibido **na linha do item
  correspondente**, nunca como toast genérico solto no topo do modal
  (usuário precisa saber *qual* item tem o problema para corrigir sem
  perder os outros já preenchidos).
- `Total Geral`: soma de todos os subtotais, mesmo formato/posição
  (`flex justify-end`, `font-bold`) do "Total Geral" já usado em
  `Vendas.jsx`.

### Rodapé do modal

```jsx
<div className="flex justify-end gap-2 mt-5">
  <Button variant="secondary" onClick={onClose}>Cancelar</Button>
  <Button onClick={handleSubmit} disabled={saving || itens.length === 0}>
    {saving ? 'Salvando...' : 'Confirmar Compra'}
  </Button>
</div>
```

- Botão `Confirmar Compra` desabilitado enquanto `itens.length === 0` (RN-02,
  feedback antes mesmo de tentar submeter) — mesmo padrão de desabilitar
  botão de submit já usado em formulários do projeto quando falta campo
  obrigatório evidente.
- Após sucesso (`POST /api/v1/compras/`): fecha modal, `fetch()` da
  listagem, toast **mencionando o status da Despesa gerada** (RF-11 já
  pede isso explicitamente):
  ```js
  showToast(
    form.status === 'PAGO'
      ? 'Compra registrada. Despesa gerada como Paga.'
      : 'Compra registrada. Despesa gerada como Pendente.',
    'success',
  )
  ```

---

## Tela 3 — Detalhe/Visualização de Compra (read-only)

RN-05 proíbe edição de itens já criados — não existe modal de edição, só um
modal de **consulta**, aberto pelo ícone `Eye` da listagem. Reaproveita o
mesmo componente `Modal`, sem nenhum campo editável (todo `Input`/`Select`
vira texto simples — não usar componentes de formulário desabilitados aqui,
seria confuso sugerir que algo poderia ser editado):

```jsx
<Modal title={`Compra #${item.id}`} onClose={onClose}>
  <div className="grid grid-cols-2 gap-3 text-sm mb-4">
    <InfoField label="Fornecedor" value={item.fornecedor_nome} />
    <InfoField label="Conta" value={item.conta_nome} />
    <InfoField label="Nota Fiscal" value={item.numero_nota_fiscal || '—'} />
    <InfoField label="Data Emissão" value={formatData(item.data_emissao)} />
    <InfoField label="Forma de Pagamento" value={formaPagamentoLabel(item.forma_pagamento)} />
    <InfoField label="Status" value={<Badge status={item.status} />} />
  </div>

  {item.observacoes && (
    <p className="text-xs text-gray-500 dark:text-slate-400 mb-4">{item.observacoes}</p>
  )}

  <h3 className="text-sm font-semibold text-gray-700 dark:text-slate-200 mb-2">Itens</h3>
  <div className="space-y-2 mb-3">
    {item.itens.map((it) => (
      <div key={it.id} className="flex items-center justify-between text-sm bg-gray-50 dark:bg-navy-900/50 rounded-lg px-3 py-2">
        <span className="text-gray-700 dark:text-slate-300">{it.produto_nome} — {it.quantidade} {it.unidade}</span>
        <span className="font-medium text-gray-800 dark:text-slate-200">{BRL(it.subtotal)}</span>
      </div>
    ))}
  </div>

  <div className="flex justify-between items-center border-t border-gray-200 dark:border-navy-700 pt-3">
    <span className="text-sm font-semibold text-gray-700 dark:text-slate-200">Total</span>
    <span className="text-sm font-bold text-gray-800 dark:text-slate-200">{BRL(item.valor_total)}</span>
  </div>

  {item.despesa && (
    <p className="text-xs text-gray-400 dark:text-slate-500 mt-3">
      Despesa vinculada: #{item.despesa} — ver em Financeiro
    </p>
  )}
</Modal>
```

`InfoField` (helper local, não é componente novo em `components/ui/` — só
uma função auxiliar dentro de `Compras.jsx`):

```jsx
function InfoField({ label, value }) {
  return (
    <div>
      <p className="text-xs text-gray-400 dark:text-slate-500">{label}</p>
      <p className="text-gray-800 dark:text-slate-200">{value}</p>
    </div>
  )
}
```

- "Despesa vinculada: #{id} — ver em Financeiro" é **texto informativo, não
  link navegável** nesta fase — o módulo Financeiro não tem rota de detalhe
  de Despesa por ID (`/financeiro` abre em abas, sem deep-link para um
  registro específico). Adicionar navegação real é refinamento futuro, fora
  de escopo (a Especificação Hotfix não pede isso em nenhum RF).
- Este modal **não tem botão de ação** além de fechar — cancelar continua
  sendo feito a partir da listagem (ícone `Ban`), não duplicado aqui, para
  manter um único ponto de entrada para essa ação (mesmo racional já usado
  na Fase 1 para não duplicar "Movimentar Estoque" em dois lugares).

---

## Ícones (lucide-react)

```jsx
import { Plus, Trash2, Eye, Ban } from 'lucide-react'
```

| Uso | Ícone | Tamanho |
|---|---|---|
| Nova Compra (botão, texto já no `Button`, sem ícone dentro do botão — consistente com `+ Novo Orcamento`/`+ Novo Pedido`, que também são só texto) | — | — |
| Remover item do carrinho | `<Trash2 />` | 14px |
| Ver detalhe da compra (listagem) | `<Eye />` | 16px |
| Cancelar compra (listagem) | `<Ban />` | 16px |

- `Ban` (não `Trash2`/`X`) para cancelar compra — `Trash2` já significa
  "remover item da lista/exclusão" em outras telas do projeto (Produtos,
  Vendas); usar `Ban` reforça que é um **cancelamento com efeito colateral
  financeiro/estoque** (RF-10), não uma exclusão simples, evitando o usuário
  confundir com soft-delete comum.
- Nenhum ícone dentro do `<select>` de Unidade — mesma regra já documentada
  na Fase 1 (ícone dentro de `<option>` não renderiza de forma confiável
  entre browsers).

---

## Mobile-first (375px)

- Cabeçalho do formulário (Fornecedor/Conta/NF/Data/Forma/Status): grid
  `grid-cols-1 sm:grid-cols-2` já colapsa para 1 coluna em 375px — nenhuma
  regra adicional.
- Linha de item do carrinho: grid `grid-cols-2 sm:grid-cols-4` — em 375px
  vira 2×2 (Quantidade+Unidade na primeira linha, Valor Unit.+Subtotal na
  segunda), não empilha em 1 coluna só, porque `Quantidade`/`Unidade` são
  campos curtos o suficiente para caber lado a lado mesmo na tela menor
  (mesmo racional já usado no grid `Quantidade+Unidade` da Fase 1).
- `BuscaProdutoRapida`: campo de busca em largura total, dropdown
  `position: fixed` (técnica já herdada do fix M32/M53) — sem ajuste
  adicional necessário, o componente já resolve overflow do `Modal` em
  qualquer tamanho de tela.
- Tabela da listagem: `hidden md:table` + cards `flex flex-col md:hidden` —
  mesmo breakpoint/padrão de toda listagem do projeto, sem scroll
  horizontal de tabela em mobile.
- Modal de detalhe (Tela 3): grid `grid-cols-2` do cabeçalho informativo
  colapsa para 1 coluna abaixo de `sm:` — ajustar para
  `grid-cols-1 sm:grid-cols-2` (diferente do que está escrito acima em forma
  simplificada) para não espremer "Forma de Pagamento"/"Nota Fiscal" em
  375px.
- Rodapé do modal (`Cancelar`/`Confirmar Compra`): `flex justify-end gap-2`
  sem stack vertical — cabem lado a lado mesmo em 375px, mesmo padrão já
  usado nos outros modais do projeto.

---

## O que NÃO fazer

- Não usar `ResourceCrud` para esta tela — o formato carrinho + imutabilidade
  pós-criação (RN-05) não cabe no contrato genérico do componente.
- Não criar modal de edição de Compra — só visualização (Tela 3) e
  cancelamento (ação na listagem). RN-05 é regra de backend *e* de UX: não
  sugerir editável o que o backend rejeita.
- Não adicionar filtro de fornecedor dedicado (dropdown separado) na
  listagem — a busca livre já cobre por nome (RF-11 não pede filtro
  duplicado).
- Não trocar `Select` simples de Fornecedor/Conta por autocomplete de busca
  — cadastros pequenos/médios, mesmo padrão já usado para Cliente/Conta em
  outras telas.
- Não adicionar ícone Lucide no item de menu "Compras" da Sidebar — usar
  emoji, consistente com a Sidebar inteira (DIV-UI03).
- Não expor `Cancelado` como opção de "Status Inicial" no modal de criação
  (RN-06).
- Não estilizar o `window.confirm` de cancelamento — diálogo nativo, fora de
  escopo.
- Não alterar `border-radius`, paleta de cores ou tipografia do projeto —
  esta é uma tela nova que segue o design system existente, não introduz um
  novo.

---

## Resumo — componentes/padrões reaproveitados (mapa para o Loom)

| Padrão | Origem | Uso em Compras.jsx |
|---|---|---|
| `Card`, `Input`, `Select`, `Button`, `Modal`, `Pagination` | `components/ui/` | Toda a tela |
| Listagem tabela desktop + cards mobile + busca + paginação | `Vendas.jsx` (Orçamentos/Pedidos) | Tela 1 |
| `STATUS_BADGES`/`Badge` (PENDENTE/PAGO/CANCELADO) | `Financeiro.jsx` (copiar, não importar) | Tela 1, Tela 3 |
| `BuscaProdutoRapida` (busca→clicar→item na lista) | `Vendas.jsx` (Manutenção #32) | Tela 2 |
| `SecaoItens` (linha de item + subtotal + total geral) | `Vendas.jsx` | Tela 2, adaptado (quantidade/unidade/valor custo em vez de quantidade/valor único) |
| Resolução de opções de Unidade a partir de conversões do produto | `Produtos.jsx` (Fase 1) | Tela 2 |
| `window.confirm` para ação destrutiva/com efeito colateral | `Produtos.jsx` (Fase 1, estoque negativo) | Tela 1 (cancelar) |
| Emoji no item de menu da Sidebar | Convenção do projeto (DIV-UI03) | Sidebar (novo item "Compras") |

Nenhum token de cor, fonte, espaçamento ou border-radius novo é introduzido
por esta especificação.

---

## Passagem de bastão

```
✅ Especificação UI concluída — UidCore (Manutenção #58, Fase 2)
   Telas analisadas: 3 (Lista de Compras | Modal Nova Compra (carrinho) | Detalhe/Visualização)
   Componentes reutilizados: Card, Input, Select, Button, Modal, Pagination
   (6 existentes) + padrões copiados de Vendas.jsx/Financeiro.jsx/Produtos.jsx
   Novos padrões: nenhum — composição de 3 telas já em produção

📁 Arquivo: Especificacao_UI_Hotfix.md (raiz do projeto)

➡️ Loom lê Especificacao_Hotfix.md + Especificacao_UI_Hotfix.md
   antes de implementar o frontend
```
