# Especificacao UI Hotfix — UidCore
**Data:** 2026-07-23
**Sistema:** UidCore — Template Financeiro Multi-Nicho
**Elaborado por:** Brush (MODO HOTFIX)

---

## Design System do Projeto (referencia)

Extraido de Financeiro.jsx, Clientes.jsx e tailwind.config.js existentes.

| Token | Valor | Uso |
|---|---|---|
| primary-600 | #2563eb | Botao primario, tab ativa, link |
| primary-700 | #1d4ed8 | Hover de botao primario |
| accent-600 | #059669 | Toast de sucesso |
| gray-900 | #111827 | Titulos h1, sidebar background |
| gray-800 | #1f2937 | Titulos h2 |
| gray-700 | #374151 | Labels, texto secundario |
| gray-600 | #4b5563 | Texto de tabela, badges neutros |
| gray-500 | #6b7280 | Subtitulos, meta |
| gray-400 | #9ca3af | Placeholders, icones inativos |
| gray-200 | #e5e7eb | Bordas de tabela, divisores |
| gray-100 | #f3f4f6 | Thead background, badge neutro |
| gray-50 | #f9fafb | Hover de linha, card background leve |
| green-100/800 | badge | Status positivos (RECEBIDO, PAGO, CONCILIADO, ATIVO) |
| yellow-100/800 | badge | Status atencao (PENDENTE, FALTANDO_SISTEMA) |
| red-100/800 | badge | Status critico (ATRASADO, SAIDA, FALTANDO_BANCO) |
| red-600 | #dc2626 | Botao danger, toast de erro |

**Fontes:** Plus Jakarta Sans (headings h1/h2) + DM Sans (body, labels, tabela)
Nota: o projeto usa classes Tailwind nativas; as fontes devem ser configuradas no
index.css/tailwind.config.js — NUNCA usar Inter, Roboto ou Arial.

**Border-radius padrao:** rounded-lg (8px) em inputs/botoes, rounded-xl (12px) em cards, rounded-full em badges
**Padding de card:** px-6 py-4 (extraido do Card.jsx)
**Padding de celula de tabela:** px-4 py-3

**Componentes reutilizaveis disponiveis:**
- Card — props: title, children, footer, className
- Button — props: variant (primary/secondary/danger), size (sm/md/lg), loading
- Input — props: label, name, type, placeholder, required
- Select — props: label, name, options [{value, label}]
- Modal — props: title, onClose, maxW (default max-w-lg)
- Pagination — props: page, totalPages, onPageChange

**Padrao de badge de status (Badge component existente em Financeiro.jsx):**

```jsx
function Badge({ status, label }) {
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${MAP[status] || 'bg-gray-100 text-gray-600'}`}>
      {label || status}
    </span>
  )
}
```

**Padrao de sub-abas internas (underline style — diferente das abas principais pill):**

```jsx
<div className="flex gap-1 border-b border-gray-200 mb-4">
  {SUB_TABS.map((t) => (
    <button
      key={t.key}
      onClick={() => setSubTab(t.key)}
      className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
        subTab === t.key
          ? 'border-primary-600 text-primary-600'
          : 'border-transparent text-gray-500 hover:text-gray-700'
      }`}
    >
      {t.label}
    </button>
  ))}
</div>
```

**Padrao mobile-first (extraido de Financeiro.jsx e Clientes.jsx):**
- Mobile cards: `<div className="flex flex-col gap-3 md:hidden">`
- Desktop table: `<div className="hidden md:block">`
- Breakpoint unico: md (768px) — abaixo = cards empilhados, acima = tabela
- Em 375px: formularios de modal em grid de 1 coluna (sm:grid-cols-2 so ativa em 640px+)

**Padrao de formulario em modal:**
- Campos simples: Input com label, required onde obrigatorio
- Textarea: className inline —
  `className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"`
- File input: `<input type="file" />` com estilo de file:button customizado
- Checkbox: `<input type="checkbox" />` com label ao lado (cursor-pointer)
- Botoes do modal: `<div className="flex justify-end gap-3 pt-2">` Cancelar (secondary) + Salvar (primary, loading={saving})

**Padrao de toast:**
```jsx
{toast && (
  <div className={`fixed top-4 right-4 z-50 px-4 py-3 rounded-lg shadow-lg text-sm font-medium text-white ${
    toast.type === 'error' ? 'bg-red-600' : 'bg-accent-600'
  }`}>
    {toast.msg}
  </div>
)}
```

**Padrao de estado vazio:**
```jsx
<div className="text-center py-12 text-gray-400">
  <p className="text-sm">Nenhum item encontrado.</p>
</div>
```

**Padrao de loading:**
```jsx
<div className="text-center py-12 text-gray-400 text-sm">Carregando...</div>
```

**Icones:** Lucide React exclusivamente.
Importacao: `import { Plus, Pencil, Trash2, CheckCircle, Upload, Eye, ... } from 'lucide-react'`
Tamanho padrao: size={14} em botoes sm / size={16} em botoes md e headers

---

## FASE D — ConciliacaoTab (adicionar ao Financeiro.jsx como 6a aba)

### Modificacao na lista TABS

Adicionar ao array TABS (linha ~19 do Financeiro.jsx):
```js
{ key: 'conciliacao', label: 'Conciliacao' }
```

Adicionar no return do componente Financeiro, apos `{tab === 'indicadores' && <IndicadoresTab />}`:
```jsx
{tab === 'conciliacao' && <ConciliacaoTab showToast={showToast} contasOptions={contasOptions} />}
```

---

### ConciliacaoTab — estrutura geral

**Layout:** space-y-4, mesmo padrao das outras tabs

**Header:**
```jsx
<div>
  <h2 className="text-lg font-semibold text-gray-800">Conciliacao Bancaria</h2>
  <p className="text-sm text-gray-500 mt-0.5">Upload e revisao de extratos bancarios</p>
</div>
```

**Sub-abas internas:**
```js
const CONC_SUB_TABS = [
  { key: 'upload',   label: 'Upload' },
  { key: 'lista',    label: 'Historico' },
  // 'detalhe' so aparece quando conciliacaoId != null
  { key: 'padroes',  label: 'Padroes Seguros' },
]
```

Regra de visibilidade da sub-aba "Detalhe": renderizar o botao somente se `conciliacaoId !== null`.
Ao clicar "Ver Itens" na lista: setar `conciliacaoId`, `conciliacaoSelecionada` e `setSubTab('detalhe')`.

**State do ConciliacaoTab (container):**
```js
const [subTab, setSubTab] = useState('upload')
const [conciliacaoId, setConciliacaoId] = useState(null)
const [conciliacaoSelecionada, setConciliacaoSelecionada] = useState(null)
```

---

### Sub-aba Upload

**Layout:** Card unico centralizado, space-y-4 interno

**Campos do formulario (em ordem):**

1. Select "Conta" (required)
   - options: [{ value: '', label: 'Selecione a conta...' }, ...contasOptions]
   - name="contaId"

2. Input type="month" "Mes/Ano de Referencia" (required)
   - name="periodo"
   - O valor nativo YYYY-MM e exatamente o que o backend espera

3. File input "Extrato PDF" (required)
   - accept=".pdf"
   - Estilo do botao file:
     ```jsx
     <label className="block text-sm font-medium text-gray-700 mb-1">
       Extrato PDF <span className="text-red-500">*</span>
     </label>
     <input
       type="file"
       accept=".pdf"
       onChange={(e) => setArquivo(e.target.files[0])}
       className="w-full text-sm text-gray-600 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-primary-50 file:text-primary-700 hover:file:bg-primary-100 cursor-pointer"
     />
     ```

4. Input type="text" "Senha do PDF" (opcional)
   - name="senha"
   - placeholder="Deixar vazio se o PDF nao tiver senha"

5. Checkbox "Modo automatico"
   ```jsx
   <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
     <input
       type="checkbox"
       checked={autoMode}
       onChange={(e) => setAutoMode(e.target.checked)}
       className="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
     />
     Modo automatico: assentar pendentes e criar lancamentos por Padroes Seguros
   </label>
   ```
   - Estado desmarcado por padrao

**Botao de envio:**
```jsx
<Button type="submit" loading={uploading} className="w-full">
  <Upload size={16} /> Enviar Extrato
</Button>
```

**Comportamento apos sucesso:** showToast + setSubTab('lista') + resetar form

**Mobile (375px):** coluna unica, botao 100% de largura

---

### Sub-aba Lista (Historico)

**Header:** "Historico de Conciliacoes" (text-base font-semibold text-gray-800)
Sem filtros — lista paginada simples.

**Colunas da tabela desktop:**

| Coluna | Largura | Alinhamento | Notas |
|---|---|---|---|
| Conta | auto | left | item.conta_nome |
| Periodo | 100px | left | item.periodo formatado como mm/aaaa |
| Status | 140px | left | Badge colorido |
| Total Banco | 120px | right | BRL(item.total_banco) |
| Total Sistema | 120px | right | BRL(item.total_sistema) |
| Divergencias | 80px | center | numero inteiro |
| Acoes | 80px | right | Botao "Ver" |

**Badge de status de conciliacao:**
```js
const BADGE_CONCILIACAO = {
  PENDENTE:         'bg-gray-100 text-gray-600',
  PROCESSADO:       'bg-green-100 text-green-800',
  COM_DIVERGENCIAS: 'bg-yellow-100 text-yellow-800',
}
```

**Divergencias:** `text-red-600 font-semibold` se > 0, `text-gray-600` se == 0

**Botao "Ver":**
```jsx
<Button size="sm" variant="secondary" onClick={() => {
  setConciliacaoId(item.id)
  setConciliacaoSelecionada(item)
  setSubTab('detalhe')
}}>
  <Eye size={14} /> Ver
</Button>
```

**Card mobile:**
```
Linha 1: conta_nome (font-semibold) + Badge status (direita)
Linha 2: Periodo formatado (text-xs text-gray-500)
Linha 3: "Banco: " BRL(total_banco) | "Sistema: " BRL(total_sistema) | divergencias (vermelho se > 0)
Linha 4: Botao "Ver Itens" (secondary, sm, w-full)
```

**Paginacao:** Pagination component, PAGE_SIZE=20
**Estado vazio:** "Nenhuma conciliacao processada ainda."

---

### Sub-aba Detalhe

**Condicao:** so renderizar se `conciliacaoId !== null`

**Header:**
```jsx
<div className="flex items-center justify-between gap-3 flex-wrap">
  <div className="flex items-center gap-3">
    <Button size="sm" variant="secondary" onClick={() => { setSubTab('lista'); setConciliacaoId(null) }}>
      <ArrowLeft size={16} /> Voltar
    </Button>
    <h3 className="text-base font-semibold text-gray-800">
      Conciliacao #{conciliacaoSelecionada?.id} — {conciliacaoSelecionada?.conta_nome} — {periodoFormatado}
    </h3>
  </div>
  <Badge status={conciliacaoSelecionada?.status} />
</div>
```

**3 KPI cards:**
```jsx
<div className="grid grid-cols-3 gap-3">
  <KpiCard label="Total Banco"   value={BRL(conciliacaoSelecionada?.total_banco)}   color="blue" />
  <KpiCard label="Total Sistema" value={BRL(conciliacaoSelecionada?.total_sistema)} color="green" />
  <KpiCard
    label="Divergencias"
    value={String(conciliacaoSelecionada?.divergencias || 0)}
    color={conciliacaoSelecionada?.divergencias > 0 ? 'red' : 'green'}
  />
</div>
```

**Fetch de itens:** `GET /api/v1/financeiro/conciliacoes/{conciliacaoId}/itens/`
Retorno e array direto (sem paginacao) — usar sem `.results`.

**Tabela de itens desktop:**

| Coluna | Notas |
|---|---|
| Data | item.data_banco |
| Descricao | item.descricao_banco, max-w-[200px] truncate |
| Valor | BRL(item.valor) right-aligned |
| Tipo | Badge por tipo |
| Status | Badge por status de item |
| Acao | Botao "Confirmar" condicional |

**Badge de tipo:**
```js
const BADGE_TIPO = {
  ENTRADA: 'bg-green-100 text-green-800',
  SAIDA:   'bg-red-100 text-red-800',
}
```

**Badge de status de item:**
```js
const BADGE_STATUS_ITEM = {
  CONCILIADO:       'bg-green-100 text-green-800',
  FALTANDO_SISTEMA: 'bg-yellow-100 text-yellow-800',
  FALTANDO_BANCO:   'bg-gray-100 text-gray-600',
}
```

**Botao "Confirmar":** exibir SOMENTE quando `item.status === 'FALTANDO_SISTEMA' && !item.confirmado`
```jsx
<Button size="sm" onClick={() => confirmarItem(item.id)}>
  <CheckCircle size={14} /> Confirmar
</Button>
```
Acao: `POST /api/v1/financeiro/conciliacoes/{conciliacaoId}/confirmar-item/` com body `{ item_id: item.id }`
Apos sucesso: refetch itens + refetch conciliacao pai (atualizar KPIs) + showToast

**Card mobile:**
```
Linha 1: descricao_banco (font-semibold truncate) + Badge tipo (direita)
Linha 2: data_banco (text-xs text-gray-500) + BRL(valor) (font-bold, direita, cor por tipo)
Linha 3: Badge status
Linha 4: Botao "Confirmar" (condicional, w-full)
```

**Estado vazio:**
```jsx
<div className="text-center py-12 text-gray-400">
  <FileSearch size={32} className="mx-auto text-gray-300 mb-2" />
  <p className="text-sm">Nenhum item nesta conciliacao.</p>
</div>
```

---

### Sub-aba Padroes Seguros

**Header:**
```jsx
<div className="flex items-center justify-between gap-3">
  <div>
    <h3 className="text-base font-semibold text-gray-800">Padroes Seguros de Conciliacao</h3>
    <p className="text-sm text-gray-500 mt-0.5">
      Substrings da descricao do extrato — usados pelo modo automatico para criar lancamentos.
    </p>
  </div>
  <Button onClick={openNew}><Plus size={16} /> Novo Padrao</Button>
</div>
```

**Tabela desktop:**

| Coluna | Notas |
|---|---|
| Descricao | item.descricao_padrao |
| Tipo | Badge ENTRADA=verde / SAIDA=vermelho (mesmos de BADGE_TIPO) |
| Natureza | item.natureza_label (text-sm text-gray-600) |
| Criado em | item.criado_em formatado como data curta |
| Acoes | Editar + Excluir (desativar) |

**Card mobile:**
```
Linha 1: descricao_padrao (font-semibold)
Linha 2: Badge tipo + natureza_label (text-xs text-gray-500)
Linha 3: Botoes Editar + Excluir
```

**Modal "Novo/Editar Padrao":**

Campos em ordem:
1. Input "Descricao do Padrao" (required)
   - placeholder="Substring que aparece no extrato (ex: PIX RECEBIDO, TARIFA)"
   - name="descricao_padrao"

2. Select "Tipo" (required)
   - options: [{ value: 'ENTRADA', label: 'Entrada' }, { value: 'SAIDA', label: 'Saida' }]
   - name="tipo"

3. Select "Natureza" — visivel SOMENTE quando `form.tipo === 'ENTRADA'`
   - options: [{ value: 'APORTE', label: 'Aporte (capital social)' }, { value: 'RECEITA_FINANCEIRA', label: 'Receita Financeira (rendimento)' }]
   - name="natureza"
   - Nota informativa abaixo do campo:
     ```jsx
     <p className="text-xs text-gray-400 mt-1">
       Aporte vai para Patrimonio Liquido. Receita Financeira entra no DRE.
     </p>
     ```

**Estado inicial do form:**
```js
const EMPTY_PADRAO = { descricao_padrao: '', tipo: 'ENTRADA', natureza: 'APORTE' }
```

**CRUD:**
- POST /api/v1/financeiro/padroes-conciliacao/ para criar
- PATCH /api/v1/financeiro/padroes-conciliacao/{id}/ para editar
- DELETE /api/v1/financeiro/padroes-conciliacao/{id}/ para desativar

**Confirmacao de exclusao:** `window.confirm('Desativar este padrao de conciliacao?')`

---

## FASE E.1 — Vendas.jsx

**Arquivo:** `frontend/src/pages/Vendas.jsx`
**Rota:** `/vendas` (ja registrada em routes/index.jsx como PlaceholderPage — substituir)

### Layout geral

**Header da pagina:**
```jsx
<div className="flex items-center justify-between gap-3">
  <div>
    <h1 className="text-2xl font-bold text-gray-900">Vendas</h1>
    <p className="text-sm text-gray-500 mt-0.5">Orcamentos e pedidos de venda</p>
  </div>
</div>
```

**Abas principais (pill style — mesmo padrao de Financeiro.jsx TABS):**
```js
const TABS = [
  { key: 'orcamentos', label: 'Orcamentos' },
  { key: 'pedidos',    label: 'Pedidos' },
]
```

**Toast:** proprio (showToast local, mesmo padrao de Clientes.jsx)

### Paleta de status

**Orcamentos:**
```js
const BADGE_ORC = {
  RASCUNHO:  'bg-gray-100 text-gray-600',
  ENVIADO:   'bg-blue-100 text-blue-800',
  APROVADO:  'bg-green-100 text-green-800',
  REJEITADO: 'bg-red-100 text-red-800',
  CANCELADO: 'bg-gray-100 text-gray-400',
}
```

**Pedidos:**
```js
const BADGE_PED = {
  PENDENTE:    'bg-yellow-100 text-yellow-800',
  CONFIRMADO:  'bg-blue-100 text-blue-800',
  EM_PRODUCAO: 'bg-purple-100 text-purple-800',
  ENTREGUE:    'bg-green-100 text-green-800',
  CANCELADO:   'bg-gray-100 text-gray-400',
}
```

### Aba Orcamentos

**Header da aba:**
```jsx
<div className="flex items-center justify-between gap-3">
  <h2 className="text-lg font-semibold text-gray-800">Orcamentos</h2>
  <Button onClick={openNew}><Plus size={16} /> Novo Orcamento</Button>
</div>
```

**Filtro:** Input de busca (por numero ou nome do cliente)

**Tabela desktop:**

| Coluna | Largura | Alinhamento | Notas |
|---|---|---|---|
| Numero | 140px | left | font-mono text-xs text-gray-500 |
| Cliente | auto | left | item.cliente_nome |
| Descricao | auto | left | max-w-[180px] truncate text-gray-600 |
| Valor Total | 110px | right | BRL(item.valor_total) text-green-700 font-semibold |
| Status | 110px | left | Badge BADGE_ORC |
| Validade | 100px | left | item.validade ou "—" |
| Acoes | 120px | right | Editar + Excluir |

**Card mobile:**
```
Linha 1: numero (font-mono text-xs text-gray-400) + Badge status (direita)
Linha 2: cliente_nome (font-semibold text-gray-900)
Linha 3: descricao (text-sm text-gray-600 truncate)
Linha 4: BRL(valor_total) (text-green-700 font-bold) | validade (text-xs text-gray-400 direita)
Linha 5: Botoes Editar (secondary sm) + Excluir (danger sm)
```

**Modal "Novo/Editar Orcamento" — maxW="max-w-2xl":**

Campos em ordem:
1. Select "Cliente" (required) — GET /api/v1/clientes/?page_size=200, carregado no mount
2. Textarea "Descricao" (required) — rows=3
3. `grid grid-cols-1 sm:grid-cols-2 gap-4`:
   - Input "Valor Total (R$)" type="number" step="0.01" min="0"
   - Select "Status" — RASCUNHO/ENVIADO/APROVADO/REJEITADO/CANCELADO (default: RASCUNHO)
4. Input "Validade" type="date" (opcional)
5. Textarea "Observacoes" rows=2 (opcional)

**Estado inicial:**
```js
const EMPTY_ORC = { cliente: '', descricao: '', valor_total: '', status: 'RASCUNHO', validade: '', observacoes: '' }
```

**Icones Lucide:**
- Novo orcamento: `<Plus size={16} />`
- Editar: `<Pencil size={14} />`
- Excluir: `<Trash2 size={14} />`

### Aba Pedidos

**Header da aba:**
```jsx
<div className="flex items-center justify-between gap-3">
  <h2 className="text-lg font-semibold text-gray-800">Pedidos</h2>
  <Button onClick={openNew}><Plus size={16} /> Novo Pedido</Button>
</div>
```

**Tabela desktop:**

| Coluna | Notas |
|---|---|
| Numero | font-mono text-xs text-gray-500 |
| Cliente | item.cliente_nome |
| Status | Badge BADGE_PED |
| Valor Total | BRL(item.valor_total) text-green-700 right |
| Data Pedido | item.data_pedido |
| Entrega Prevista | item.data_entrega_prevista ou "—" text-gray-400 |
| Acoes | Editar + Excluir |

**Card mobile:**
```
Linha 1: numero (font-mono text-xs) + Badge status (direita)
Linha 2: cliente_nome (font-semibold)
Linha 3: BRL(valor_total) (text-green-700 font-bold) | data_pedido (text-xs text-gray-400 direita)
Linha 4: "Entrega: " + data_entrega_prevista (text-xs text-gray-500) — condicional
Linha 5: Botoes Editar + Excluir
```

**Modal "Novo/Editar Pedido" — maxW="max-w-2xl":**

Campos:
1. Select "Cliente" (required)
2. Select "Orcamento" (opcional) — GET /api/v1/vendas/orcamentos/?page_size=200, opcao vazia "Nenhum"
3. Select "Status" — PENDENTE/CONFIRMADO/EM_PRODUCAO/ENTREGUE/CANCELADO (default: PENDENTE)
4. `grid grid-cols-1 sm:grid-cols-2 gap-4`:
   - Input "Valor Total (R$)" type="number" step="0.01" min="0"
   - Input "Data do Pedido" type="date" (required)
5. Input "Entrega Prevista" type="date" (opcional)
6. Textarea "Observacoes" rows=2 (opcional)

**Estado inicial:**
```js
const EMPTY_PED = { cliente: '', orcamento: '', status: 'PENDENTE', valor_total: '', data_pedido: '', data_entrega_prevista: '', observacoes: '' }
```

---

## FASE E.2 — Pagamentos.jsx

**Arquivo:** `frontend/src/pages/Pagamentos.jsx`

### Layout geral

Header: "Pagamentos" + "Cobrancas, parcelas e metodos de pagamento"
Abas: cobrancas | parcelas | metodos

### Paleta de status

```js
const BADGE_PAG = {
  PENDENTE:  'bg-yellow-100 text-yellow-800',
  PAGO:      'bg-green-100 text-green-800',
  CANCELADO: 'bg-gray-100 text-gray-400',
  ATRASADO:  'bg-red-100 text-red-800',
}
```

### Aba Cobrancas

**Header:** "Cobrancas" + botao "+ Nova Cobranca" com `<Plus size={16} />`

**Tabela desktop:**

| Coluna | Notas |
|---|---|
| Cliente | item.cliente_nome |
| Descricao | max-w-[160px] truncate |
| Valor | BRL(item.valor) right text-blue-700 font-semibold |
| Vencimento | item.vencimento |
| Status | Badge BADGE_PAG |
| Metodo | item.metodo_nome ou "—" text-gray-400 |
| Acoes | Editar + Excluir |

**Card mobile:**
```
Linha 1: cliente_nome (font-semibold) + Badge status (direita)
Linha 2: descricao (text-sm text-gray-600 truncate)
Linha 3: BRL(valor) (text-blue-700 font-bold) | vencimento (text-xs text-gray-400 direita)
Linha 4: metodo_nome (text-xs text-gray-400) — condicional
Linha 5: Botoes Editar + Excluir
```

**Modal "Nova/Editar Cobranca" — maxW="max-w-2xl":**

Campos:
1. Select "Cliente" (required) — GET /api/v1/clientes/?page_size=200
2. Input "Descricao" (required)
3. `grid grid-cols-1 sm:grid-cols-2 gap-4`:
   - Input "Valor (R$)" type="number" step="0.01" required
   - Input "Vencimento" type="date" required
4. `grid grid-cols-1 sm:grid-cols-2 gap-4`:
   - Select "Status" — PENDENTE/PAGO/CANCELADO/ATRASADO (default: PENDENTE)
   - Select "Metodo de Pagamento" (opcional) — GET /api/v1/pagamentos/metodos/
5. Input "Data de Pagamento" type="date" (opcional)
6. File input "Comprovante" (opcional) — mesmo estilo do file input da ConciliacaoTab, sem accept especifico
7. Textarea "Observacoes" rows=2 (opcional)

**Estado inicial:**
```js
const EMPTY_COB = { cliente: '', descricao: '', valor: '', vencimento: '', status: 'PENDENTE', metodo: '', data_pagamento: '', comprovante: null, observacoes: '' }
```

**IMPORTANTE para Loom:** formulario com comprovante usa FormData (nao JSON).

### Aba Parcelas

**Header:** "Parcelas" + botao "+ Nova Parcela" com `<Plus size={16} />`

**Tabela desktop:**

| Coluna | Notas |
|---|---|
| Cobranca | descricao da cobranca vinculada |
| Numero | item.numero (text-center) |
| Valor | BRL(item.valor) right |
| Vencimento | item.vencimento |
| Status | Badge BADGE_PAG (PENDENTE/PAGO/CANCELADO) |
| Acoes | Editar + Excluir |

**Modal "Nova/Editar Parcela":**

Campos:
1. Select "Cobranca" (required) — GET /api/v1/pagamentos/cobrancas/?page_size=200, label = descricao
2. Input "Numero da Parcela" type="number" min="1" (required)
3. `grid grid-cols-1 sm:grid-cols-2 gap-4`:
   - Input "Valor (R$)" type="number" step="0.01" required
   - Input "Vencimento" type="date" required
4. Select "Status" — PENDENTE/PAGO/CANCELADO (default: PENDENTE)
5. Input "Data de Pagamento" type="date" (opcional)

**Estado inicial:**
```js
const EMPTY_PARCELA = { cobranca: '', numero: '', valor: '', vencimento: '', status: 'PENDENTE', data_pagamento: '' }
```

### Aba Metodos

**Layout:** grid de cards (nao tabela)

**Header:** "Metodos de Pagamento" + botao "+ Adicionar" com `<Plus size={16} />`

**Grid:**
```jsx
<div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
```

**Card de metodo:**
```
Icone do metodo (ver mapa abaixo) — mb-2
Nome (nome_display, font-semibold text-gray-900)
Badge ativo/inativo
Botao "Desativar" (danger sm) — condicional: so se item.ativo
```

**Icones Lucide por metodo:**
- PIX: `<Zap size={20} className="text-green-600" />`
- BOLETO: `<FileText size={20} className="text-blue-600" />`
- CARTAO_CREDITO: `<CreditCard size={20} className="text-purple-600" />`
- CARTAO_DEBITO: `<CreditCard size={20} className="text-blue-600" />`
- DINHEIRO: `<Banknote size={20} className="text-green-700" />`
- OUTRO: `<MoreHorizontal size={20} className="text-gray-500" />`

**Badge ativo:**
```js
const BADGE_METODO = {
  true:  'bg-green-100 text-green-800',
  false: 'bg-gray-100 text-gray-400',
}
```
Uso: `BADGE_METODO[String(item.ativo)]`

**Modal "Adicionar Metodo":**

Campos:
1. Select "Metodo" (required):
   ```js
   [
     { value: 'PIX',            label: 'PIX' },
     { value: 'BOLETO',         label: 'Boleto' },
     { value: 'CARTAO_CREDITO', label: 'Cartao de Credito' },
     { value: 'CARTAO_DEBITO',  label: 'Cartao de Debito' },
     { value: 'DINHEIRO',       label: 'Dinheiro' },
     { value: 'OUTRO',          label: 'Outro' },
   ]
   ```
2. Checkbox "Ativo" (default marcado)

**Acao "Desativar":**
- DELETE /api/v1/pagamentos/metodos/{id}/ (backend faz is_active=False)
- Confirmacao: `window.confirm('Desativar este metodo de pagamento?')`

---

## FASE E.3 — Administrativo.jsx

**Arquivo:** `frontend/src/pages/Administrativo.jsx`

### Layout geral

Header: "Administrativo" + "Documentos e tipos de documento"
Abas: documentos | tipos

### Paleta de status de documento

```js
const BADGE_DOC = {
  RASCUNHO:  'bg-gray-100 text-gray-600',
  VIGENTE:   'bg-green-100 text-green-800',
  EXPIRADO:  'bg-yellow-100 text-yellow-800',
  CANCELADO: 'bg-red-100 text-red-600',
}
```

### Aba Documentos

**Header:** "Documentos" + botao "+ Novo Documento" com `<Plus size={16} />`

**Tabela desktop:**

| Coluna | Notas |
|---|---|
| Titulo | max-w-[180px] truncate font-medium text-gray-900 |
| Tipo | `<span className="text-xs bg-primary-50 text-primary-700 rounded-full px-2 py-0.5">` |
| Cliente | item.cliente_nome ou `<span className="text-gray-400 italic">Geral</span>` |
| Status | Badge BADGE_DOC |
| Validade | item.validade ou `<span className="text-xs text-gray-400">Sem validade</span>` |
| Acoes | Download (condicional) + Editar + Excluir |

**Botao Download:**
```jsx
{item.arquivo && (
  <Button size="sm" variant="secondary" onClick={() => window.open(item.arquivo, '_blank')}>
    <Download size={14} />
  </Button>
)}
```

**Card mobile:**
```
Linha 1: titulo (font-semibold) + Badge status (direita)
Linha 2: badge tipo (primary-50) | cliente_nome (text-xs text-gray-400)
Linha 3: validade (text-xs text-gray-500)
Linha 4: Botoes Download (condicional) + Editar + Excluir
```

**Modal "Novo/Editar Documento" — maxW="max-w-2xl":**

Campos:
1. Input "Titulo" (required)
2. Select "Tipo de Documento" (required) — GET /api/v1/administrativo/tipos/
3. File input "Arquivo" (required para criacao, opcional para edicao)
   - sem restrict de accept (qualquer tipo de arquivo)
   - nota: "(PDF, DOC, imagem ou qualquer formato)"
4. Select "Cliente" (opcional) — GET /api/v1/clientes/?page_size=200
   - opcao vazia: "Documento geral (sem cliente)"
5. Select "Status" — RASCUNHO/VIGENTE/EXPIRADO/CANCELADO (default: RASCUNHO)
6. Input "Validade" type="date" (opcional)
7. Textarea "Descricao" rows=2 (opcional)

**IMPORTANTE para Loom:** formulario com arquivo usa FormData (nao JSON).

**Estado inicial:**
```js
const EMPTY_DOC = { titulo: '', tipo: '', arquivo: null, cliente: '', descricao: '', status: 'RASCUNHO', validade: '' }
```

### Aba Tipos

**Header:** "Tipos de Documento" + botao "+ Novo Tipo" com `<Plus size={16} />`

**Tabela desktop:**

| Coluna | Notas |
|---|---|
| Nome | font-medium text-gray-900 |
| Descricao | text-sm text-gray-600 max-w-[300px] truncate |
| Acoes | Editar + Excluir |

**Modal "Novo/Editar Tipo":**

Campos:
1. Input "Nome" (required)
2. Textarea "Descricao" rows=2 (opcional)

**Estado inicial:**
```js
const EMPTY_TIPO = { nome: '', descricao: '' }
```

---

## FASE E.4 — RH.jsx

**Arquivo:** `frontend/src/pages/RH.jsx`

### Layout geral

Header: "RH" + "Funcionarios, folhas de pagamento e ferias"
Abas: funcionarios | folhas | ferias | cargos

### Paletas de status

**Folha de pagamento:**
```js
const BADGE_FOLHA = {
  ABERTA:  'bg-yellow-100 text-yellow-800',
  FECHADA: 'bg-blue-100 text-blue-800',
  PAGA:    'bg-green-100 text-green-800',
}
```

**Ferias:**
```js
const BADGE_FERIAS = {
  AGENDADO:     'bg-blue-100 text-blue-800',
  EM_ANDAMENTO: 'bg-yellow-100 text-yellow-800',
  CONCLUIDO:    'bg-green-100 text-green-800',
}
```

**Regime de funcionario (badge simples, sem cor especial):**
```js
// Exibir como tag neutra: bg-gray-100 text-gray-700 rounded px-2 py-0.5 text-xs
const REGIME_LABEL = { CLT: 'CLT', PJ: 'PJ', ESTAGIO: 'Estagio', SOCIO: 'Socio' }
```

### Aba Funcionarios

**Header:** "Funcionarios" + botao "+ Novo Funcionario" com `<UserPlus size={16} />`

**Filtro:** Input de busca (nome, CPF)

**Tabela desktop:**

| Coluna | Notas |
|---|---|
| Nome | font-medium text-gray-900 |
| CPF | font-mono text-xs text-gray-600 |
| Cargo | item.cargo_nome |
| Regime | tag neutra `bg-gray-100 text-gray-700 rounded px-2 py-0.5 text-xs` |
| Admissao | item.data_admissao |
| Salario Atual | BRL(item.salario_atual) right text-green-700 font-semibold |
| Acoes | Editar + Excluir |

**Card mobile:**
```
Linha 1: nome (font-semibold) + regime tag (direita)
Linha 2: CPF (font-mono text-xs text-gray-500) + cargo_nome (text-xs text-gray-500)
Linha 3: BRL(salario_atual) (text-green-700 font-bold) | data_admissao (text-xs text-gray-400 direita)
Linha 4: Botoes Editar + Excluir
```

**Modal "Novo/Editar Funcionario" — maxW="max-w-2xl":**

Campos:
1. Input "Nome" (required)
2. `grid grid-cols-1 sm:grid-cols-2 gap-4`:
   - Input "CPF" (required) — maxLength={11}, placeholder="Apenas digitos, sem mascara"
   - Input "E-mail" type="email" (opcional)
3. Select "Cargo" (required) — GET /api/v1/rh/cargos/
4. Select "Regime" — CLT/PJ/ESTAGIO/SOCIO (default: CLT)
5. `grid grid-cols-1 sm:grid-cols-2 gap-4`:
   - Input "Data de Admissao" type="date" (required)
   - Input "Data de Demissao" type="date" (opcional)
6. Input "Salario Atual (R$)" type="number" step="0.01" min="0" (required)
7. Textarea "Observacoes" rows=2 (opcional)

**Estado inicial:**
```js
const EMPTY_FUNC = { nome: '', cpf: '', email: '', cargo: '', data_admissao: '', data_demissao: '', salario_atual: '', regime: 'CLT', observacoes: '' }
```

### Aba Folhas

**Header:** "Folhas de Pagamento" + botao "+ Nova Folha" com `<Plus size={16} />`

**Tabela desktop:**

| Coluna | Notas |
|---|---|
| Funcionario | item.funcionario_nome |
| Mes Referencia | formatar item.mes_referencia como mm/aaaa |
| Bruto | BRL(item.salario_bruto) right |
| Descontos | BRL(item.descontos) right text-red-600 |
| Liquido | BRL(item.salario_liquido) right text-green-700 font-semibold |
| Status | Badge BADGE_FOLHA |
| Acoes | Editar + Excluir |

**Card mobile:**
```
Linha 1: funcionario_nome (font-semibold) + Badge status (direita)
Linha 2: mes referencia (text-sm text-gray-500)
Linha 3: "Bruto: " BRL(bruto) | "(-)" BRL(descontos, red) | "Liq: " BRL(liquido, green)
Linha 4: Botoes Editar + Excluir
```

**Modal "Nova/Editar Folha":**

Campos:
1. Select "Funcionario" (required) — GET /api/v1/rh/funcionarios/?page_size=200
2. Input "Mes de Referencia" type="month" (required)
   - IMPORTANTE: ao submeter converter para YYYY-MM-01: `mes_referencia: form.mes_referencia + '-01'`
3. `grid grid-cols-1 sm:grid-cols-3 gap-4`:
   - Input "Salario Bruto (R$)" type="number" step="0.01" required
   - Input "Descontos (R$)" type="number" step="0.01" (default 0)
   - Select "Status" — ABERTA/FECHADA/PAGA (default: ABERTA)
4. Textarea "Observacoes" rows=2 (opcional)
5. Nota informativa:
   ```jsx
   <p className="text-xs text-gray-400">Salario liquido = bruto - descontos (calculado automaticamente pelo backend).</p>
   ```

**Estado inicial:**
```js
const EMPTY_FOLHA = { funcionario: '', mes_referencia: '', salario_bruto: '', descontos: '0', status: 'ABERTA', observacoes: '' }
```

### Aba Ferias

**Header:** "Ferias" + botao "+ Registrar Ferias" com `<CalendarPlus size={16} />`

**Tabela desktop:**

| Coluna | Notas |
|---|---|
| Funcionario | item.funcionario_nome |
| Inicio | item.data_inicio |
| Fim | item.data_fim |
| Dias | item.dias (text-center) |
| Status | Badge BADGE_FERIAS |
| Acoes | Editar + Excluir |

**Card mobile:**
```
Linha 1: funcionario_nome (font-semibold) + Badge status (direita)
Linha 2: data_inicio + " ate " + data_fim (text-sm text-gray-600)
Linha 3: item.dias + " dias" (text-xs text-gray-400)
Linha 4: Botoes Editar + Excluir
```

**Modal "Registrar/Editar Ferias":**

Campos:
1. Select "Funcionario" (required) — GET /api/v1/rh/funcionarios/?page_size=200
2. `grid grid-cols-1 sm:grid-cols-2 gap-4`:
   - Input "Data de Inicio" type="date" (required)
   - Input "Data de Fim" type="date" (required)
3. Select "Status" — AGENDADO/EM_ANDAMENTO/CONCLUIDO (default: AGENDADO)
4. Nota informativa:
   ```jsx
   <p className="text-xs text-gray-400">Quantidade de dias calculada automaticamente pelo backend.</p>
   ```

**Estado inicial:**
```js
const EMPTY_FERIAS = { funcionario: '', data_inicio: '', data_fim: '', status: 'AGENDADO' }
```

### Aba Cargos

**Header:** "Cargos" + botao "+ Novo Cargo" com `<Briefcase size={16} />`

**Layout:** grid de cards
```jsx
<div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
```

**Card de cargo:**
```
Briefcase size={20} className="text-primary-600 mb-2"
Nome (font-semibold text-gray-900)
Descricao (text-sm text-gray-500 line-clamp-2) — condicional
"Salario base: " + BRL(salario_base) (text-sm font-medium text-green-700)
Botoes Editar (secondary sm) + Excluir (danger sm)
```

**Modal "Novo/Editar Cargo":**

Campos:
1. Input "Nome" (required)
2. Input "Salario Base (R$)" type="number" step="0.01" min="0" (required, default 0)
3. Textarea "Descricao" rows=2 (opcional)

**Estado inicial:**
```js
const EMPTY_CARGO = { nome: '', descricao: '', salario_base: '0' }
```

**Icones Lucide em RH.jsx:**
- `UserPlus` — novo funcionario
- `CalendarPlus` — registrar ferias
- `Briefcase` — cargo (header + icone no card)
- `Plus` — nova folha
- `Pencil` — editar
- `Trash2` — excluir

---

## FASE E.5 — Agendamento.jsx

**Arquivo:** `frontend/src/pages/Agendamento.jsx`

### Layout geral

Header: "Agendamento" + "Compromissos e agendas"
Abas: compromissos | agendas

### Paleta de status de compromisso

```js
const BADGE_COMP = {
  AGENDADO:  'bg-blue-100 text-blue-800',
  CONFIRMADO:'bg-green-100 text-green-800',
  CANCELADO: 'bg-gray-100 text-gray-400',
  CONCLUIDO: 'bg-purple-100 text-purple-800',
}
```

### Aba Compromissos

**Header:** "Compromissos" + botao "+ Novo Compromisso" com `<CalendarPlus size={16} />`

**Filtros (acima da tabela em Card):**
```jsx
<Card>
  <div className="flex flex-col sm:flex-row gap-3">
    <div className="w-full sm:w-48">
      <Select options={[{ value: '', label: 'Todas as agendas' }, ...agendasOptions]}
              value={agendaFilter} onChange={...} />
    </div>
    <div className="w-full sm:w-48">
      <Select options={STATUS_COMP_OPTS} value={statusFilter} onChange={...} />
    </div>
  </div>
</Card>
```

**Tabela desktop:**

| Coluna | Notas |
|---|---|
| Titulo | font-medium text-gray-900 |
| Agenda | bolinha colorida + nome — ver abaixo |
| Cliente | item.cliente_nome ou "—" |
| Inicio | fmtDatetime(item.inicio) |
| Fim | fmtDatetime(item.fim) |
| Status | Badge BADGE_COMP |
| Acoes | Editar + Excluir |

**Bolinha colorida de agenda:**
```jsx
<span className="inline-flex items-center gap-1.5">
  <span className="w-2.5 h-2.5 rounded-full shrink-0"
        style={{ backgroundColor: agendaCorMap[item.agenda] || '#3B82F6' }} />
  {item.agenda_nome}
</span>
```
`agendaCorMap` = objeto `{id: cor}` construido a partir da lista de agendas carregada no mount.
Se o serializer retornar `agenda_cor` diretamente, usar isso em vez do map.

**Formatacao de datetime:**
```js
const fmtDatetime = (s) => s
  ? new Date(s).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })
  : '—'
```

**Card mobile:**
```
Linha 1: titulo (font-semibold) + Badge status (direita)
Linha 2: bolinha colorida + agenda_nome (text-xs text-gray-500)
Linha 3: fmtDatetime(inicio) (text-sm text-gray-600) + " ate " + fmtDatetime(fim) (text-xs text-gray-400)
Linha 4: cliente_nome (text-xs text-gray-400) — condicional
Linha 5: Botoes Editar + Excluir
```

**Modal "Novo/Editar Compromisso" — maxW="max-w-2xl":**

Campos em ordem:
1. Input "Titulo" (required)
2. Select "Agenda" (required) — GET /api/v1/agendamento/agendas/
3. `grid grid-cols-1 sm:grid-cols-2 gap-4`:
   - Input "Inicio" type="datetime-local" (required)
   - Input "Fim" type="datetime-local" (required)
4. Se `form.fim && form.inicio && form.fim < form.inicio`:
   ```jsx
   <p className="text-xs text-red-500 -mt-2">A data/hora de fim deve ser apos o inicio.</p>
   ```
5. Input "Local" (opcional) — placeholder="Sala, endereco, link de reuniao..."
6. Select "Cliente" (opcional) — GET /api/v1/clientes/?page_size=200, opcao vazia "Nenhum"
7. Select "Status" — AGENDADO/CONFIRMADO/CANCELADO/CONCLUIDO (default: AGENDADO)
8. Textarea "Descricao" rows=2 (opcional)
9. Textarea "Observacoes" rows=2 (opcional)

**Estado inicial:**
```js
const EMPTY_COMP = { titulo: '', agenda: '', descricao: '', inicio: '', fim: '', local: '', cliente: '', status: 'AGENDADO', observacoes: '' }
```

### Aba Agendas

**Layout:** grid de cards (nao tabela)

**Header:** "Agendas" + botao "+ Nova Agenda" com `<Plus size={16} />`

**Grid:**
```jsx
<div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
```

**Card de agenda (com barra de cor no topo):**
```jsx
<div key={item.id} className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
  {/* Barra de cor no topo */}
  <div className="h-1.5" style={{ backgroundColor: item.cor || '#3B82F6' }} />
  <div className="px-6 py-4">
    <div className="flex items-center gap-2 mb-1">
      <span className="w-3 h-3 rounded-full shrink-0" style={{ backgroundColor: item.cor || '#3B82F6' }} />
      <p className="font-semibold text-gray-900">{item.nome}</p>
    </div>
    {item.descricao && <p className="text-sm text-gray-500 mb-3">{item.descricao}</p>}
    <div className="mb-3">
      <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${item.ativo ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-400'}`}>
        {item.ativo ? 'Ativa' : 'Inativa'}
      </span>
    </div>
    <div className="flex gap-2">
      <Button size="sm" variant="secondary" onClick={() => openEdit(item)}><Pencil size={14} /> Editar</Button>
      <Button size="sm" variant="danger" onClick={() => handleDelete(item)}><Trash2 size={14} /> Excluir</Button>
    </div>
  </div>
</div>
```

**Modal "Nova/Editar Agenda":**

Campos:
1. Input "Nome" (required)
2. Textarea "Descricao" rows=2 (opcional)
3. Campo de cor:
   ```jsx
   <div className="flex flex-col gap-1">
     <label className="text-sm font-medium text-gray-700">Cor da Agenda</label>
     <div className="flex items-center gap-3">
       <input
         type="color"
         name="cor"
         value={form.cor}
         onChange={handleChange}
         className="w-10 h-10 rounded-lg border border-gray-300 cursor-pointer p-0.5"
       />
       <span className="text-sm text-gray-500 font-mono">{form.cor}</span>
     </div>
   </div>
   ```
4. Checkbox "Ativa":
   ```jsx
   <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
     <input
       type="checkbox"
       checked={form.ativo}
       onChange={(e) => setForm(p => ({ ...p, ativo: e.target.checked }))}
       className="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
     />
     Agenda ativa
   </label>
   ```

**Estado inicial:**
```js
const EMPTY_AGENDA = { nome: '', descricao: '', cor: '#3B82F6', ativo: true }
```

**Icones Lucide em Agendamento.jsx:**
- `CalendarPlus` — novo compromisso
- `Plus` — nova agenda
- `Pencil` — editar
- `Trash2` — excluir

---

## FASE E.6 — Portal.jsx

**Arquivo:** `frontend/src/pages/Portal.jsx`

### Layout geral

Pagina unica (sem abas). Tabela de acessos ao portal do cliente.

**Header da pagina:**
```jsx
<div className="flex items-center justify-between gap-3">
  <div>
    <h1 className="text-2xl font-bold text-gray-900">Portal do Cliente</h1>
    <p className="text-sm text-gray-500 mt-0.5">Gerencie os acessos dos clientes ao portal</p>
  </div>
  <Button onClick={openNew}><Plus size={16} /> Novo Acesso</Button>
</div>
```

**Filtro:** Input de busca (por email ou nome do cliente)

**Tabela desktop:**

| Coluna | Largura | Notas |
|---|---|---|
| Usuario (E-mail) | auto | item.usuario_email, font-medium |
| Cliente | auto | item.cliente_nome |
| Ativo | 80px | Badge ativo/inativo |
| Ultimo Acesso | 140px | data formatada ou "Nunca" |
| Criado em | 120px | item.criado_em formatado |
| Acoes | 100px | Botao "Desativar" condicional |

**Badge ativo/inativo:**
```jsx
<span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${item.ativo ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-400'}`}>
  {item.ativo ? 'Ativo' : 'Inativo'}
</span>
```

**Botao "Desativar":**
- Exibir SOMENTE se `item.ativo === true`
```jsx
<Button size="sm" variant="danger" onClick={() => desativar(item)}>
  <UserX size={14} /> Desativar
</Button>
```
Acao: `PATCH /api/v1/portal/acessos/{id}/` com body `{ ativo: false }`
Confirmacao: `window.confirm('Desativar o acesso de "${item.usuario_email}" ao portal?')`
Apos sucesso: refetch + showToast('Acesso desativado.')

**Card mobile:**
```
Linha 1: usuario_email (font-semibold truncate) + Badge ativo/inativo (direita)
Linha 2: cliente_nome (text-sm text-gray-600)
Linha 3: "Ultimo acesso: " + data formatada ou "Nunca" (text-xs text-gray-400)
Linha 4: Botao "Desativar" (danger sm, condicional, w-full)
```

**Modal "+ Novo Acesso":**

Campos:
1. Select "Usuario" (required)
   - Endpoint: verificar `GET /api/v1/accounts/` ou similar em core/urls.py antes de implementar.
   - Se nao existir: o Loom deve escalar para o Forge criar endpoint minimo de listagem de usuarios.
   - Label: "Usuario (e-mail)"
2. Select "Cliente" (required) — GET /api/v1/clientes/?page_size=200
3. Checkbox "Ativo" (default marcado):
   ```jsx
   <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
     <input type="checkbox" checked={form.ativo}
            onChange={(e) => setForm(p => ({ ...p, ativo: e.target.checked }))}
            className="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500" />
     Acesso ativo imediatamente
   </label>
   ```

**Estado inicial:**
```js
const EMPTY_ACESSO = { usuario: '', cliente: '', ativo: true }
```

**Sem botao Editar:** acessos sao imutaveis apos criacao, exceto o campo `ativo` (via botao Desativar).

**Icones Lucide em Portal.jsx:**
- `Plus` — novo acesso
- `UserX` — desativar

---

## Atualizacoes de navegacao

### routes/index.jsx

Substituir as 6 PlaceholderPage por imports reais:
```jsx
import Vendas        from '../pages/Vendas.jsx'
import Pagamentos    from '../pages/Pagamentos.jsx'
import Administrativo from '../pages/Administrativo.jsx'
import RH            from '../pages/RH.jsx'
import Agendamento   from '../pages/Agendamento.jsx'
import Portal        from '../pages/Portal.jsx'
```

Substituir as routes:
```jsx
<Route path="/vendas"          element={<Vendas />} />
<Route path="/pagamentos"      element={<Pagamentos />} />
<Route path="/administrativo"  element={<Administrativo />} />
<Route path="/rh"              element={<RH />} />
<Route path="/agendamento"     element={<Agendamento />} />
<Route path="/portal"          element={<Portal />} />
```

### Sidebar.jsx

Os navItems ja existem com todos os paths corretos — nenhuma alteracao necessaria.

---

## Resumo de icones Lucide por arquivo

| Arquivo | Icones a importar |
|---|---|
| Financeiro.jsx (ConciliacaoTab) | Upload, Eye, CheckCircle, Plus, Pencil, Trash2, ArrowLeft, FileSearch, Building2 |
| Vendas.jsx | Plus, Pencil, Trash2 |
| Pagamentos.jsx | Plus, Pencil, Trash2, Zap, FileText, CreditCard, Banknote, MoreHorizontal |
| Administrativo.jsx | Plus, Pencil, Trash2, Download |
| RH.jsx | UserPlus, CalendarPlus, Briefcase, Plus, Pencil, Trash2 |
| Agendamento.jsx | CalendarPlus, Plus, Pencil, Trash2 |
| Portal.jsx | Plus, UserX |

Verificar se `lucide-react` esta em `frontend/package.json` antes de usar.
Se nao estiver: `npm install lucide-react` no diretorio frontend.

---

## Checklist de UI para o Loom

### FASE D — Financeiro.jsx
- [ ] Adicionar { key: 'conciliacao', label: 'Conciliacao' } ao array TABS
- [ ] Adicionar renderizacao da ConciliacaoTab no return do componente
- [ ] Implementar ConciliacaoTab com 4 sub-abas (upload, lista, detalhe, padroes)
- [ ] Sub-aba upload: FormData com arquivo PDF + campo type=month
- [ ] Sub-aba lista: tabela com badge PENDENTE/PROCESSADO/COM_DIVERGENCIAS + botao Ver
- [ ] Sub-aba detalhe: 3 KPI cards + tabela de itens + botao Confirmar condicional
- [ ] Sub-aba padroes: CRUD com campo Natureza visivel so quando tipo=ENTRADA
- [ ] Sub-aba detalhe: botao de sub-aba so renderizar se conciliacaoId != null
- [ ] Mobile: todos os cards mobile com padrao md:hidden / hidden md:block

### FASE E — Novas paginas
- [ ] Vendas.jsx: 2 abas, badges de orcamento e pedido, modais com select de cliente
- [ ] Pagamentos.jsx: 3 abas, metodos em grid de cards com icone Lucide por tipo
- [ ] Administrativo.jsx: 2 abas, botao download de arquivo, upload de arquivo no modal
- [ ] RH.jsx: 4 abas, cargos em grid de cards, mes_referencia como type=month com conversao +'-01'
- [ ] Agendamento.jsx: 2 abas, bolinha colorida de agenda, color picker no modal, validacao fim >= inicio
- [ ] Portal.jsx: pagina unica, badge ativo/inativo, sem botao Editar (so Desativar)
- [ ] routes/index.jsx: substituir 6 PlaceholderPage por imports reais
- [ ] Verificar lucide-react em package.json

---

## Notas criticas para o Loom

1. **type=month e conversao de data (mes_referencia em RH):**
   O input `type="month"` retorna `YYYY-MM`. Para folhas de pagamento, o backend espera DateField
   no formato `YYYY-MM-01`. Converter antes do POST/PATCH:
   ```js
   const payload = { ...form, mes_referencia: form.mes_referencia + '-01' }
   ```

2. **FormData para uploads:**
   Sempre usar `new FormData()` quando o form tem `<input type="file">`.
   Nao usar `Content-Type: application/json` nesses casos.
   Axios envia multipart automaticamente ao receber FormData como body.

3. **response.data.results obrigatorio:**
   Sempre usar `r.data.results || r.data || []` para endpoints paginados.
   Nunca usar `r.data` direto em listas.

4. **Select de Usuario no Portal:**
   O endpoint de listagem de usuarios pode nao existir. Verificar `core/urls.py`.
   Se ausente: escalar para o Forge, que deve criar um endpoint minimo em `accounts/views.py`.

5. **Cor da agenda (input type=color):**
   O campo `cor` e CharField max=7 no Django, armazena `#RRGGBB`.
   O `input[type=color]` retorna exatamente esse formato. Sem conversao necessaria.

6. **Checkbox ativo em Agendamento e Portal:**
   Usar `checked={form.ativo}` e `onChange={(e) => setForm(p => ({ ...p, ativo: e.target.checked }))}`.
   NUNCA usar `e.target.value` em checkbox — sempre `e.target.checked`.

7. **overflow-x-auto em tabelas:**
   Sempre envolver `<table>` em `<div className="overflow-x-auto -mx-6 -my-4">` dentro do Card.
   Isso garante scroll horizontal em mobile sem quebrar o layout do Card.

8. **Sub-aba Detalhe na ConciliacaoTab:**
   O botao de sub-aba "Detalhe" nao deve aparecer se `conciliacaoId === null`. Filtrar assim:
   ```jsx
   const visibleSubTabs = CONC_SUB_TABS.filter(t => t.key !== 'detalhe' || conciliacaoId !== null)
   // inserir 'detalhe' na posicao 2 (entre 'lista' e 'padroes') quando conciliacaoId != null
   ```

9. **Formato de datetime em Compromisso:**
   Input `type="datetime-local"` envia `YYYY-MM-DDTHH:MM`. O DRF aceita este formato diretamente.
   Para exibicao: usar `fmtDatetime` conforme definido nesta especificacao.

10. **Itens da conciliacao (sub-aba Detalhe):**
    O endpoint `/api/v1/financeiro/conciliacoes/{id}/itens/` retorna array direto (sem paginacao).
    Usar `r.data` (nao `.results`) para este endpoint especifico.

11. **Desativar metodo de pagamento:**
    Usar DELETE (nao PATCH), pois o ViewSet do Forge faz is_active=False no `perform_destroy`.
    Confirmar com o codigo real do Forge antes de implementar.

12. **Portal — sem edicao:**
    O botao Editar nao existe em Portal.jsx. O unico update e o Desativar (PATCH ativo=false).
    Nao implementar openEdit/modal de edicao para AcessoPortalCliente.
