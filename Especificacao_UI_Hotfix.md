# Especificação UI Hotfix — UidCore (Manutenção #58, Fase 1)

**Módulo:** `produtos` (estoque) — `frontend/src/pages/Produtos.jsx`
**Base:** `Especificacao_Hotfix.md` (Manutenção #58, Fase 1) — RF-03, RF-04, RF-06, RN-01 a RN-07

---

## Design System do Projeto (referência)

`design_system.md` na raiz é anterior à Manutenção #31 (dark mode) e não
documenta `navy-*`/`violet-*`. Fonte de verdade real hoje: `tailwind.config.js`
+ o próprio `Produtos.jsx` (o modal de produto já usa o padrão abaixo de
ponta a ponta — esta tarefa só estende o que já existe, não introduz nada
novo).

- **Cores primárias (light):** `primary-600` (#2563eb) — botão primário, links de
  ação (`+ Adicionar Conversao`, `+ Registrar Entrada`), foco de input.
- **Cores de ação (dark):** `violet-400`/`violet-500` — equivalente dark dos
  links/foco `primary-*`.
- **Cores de fundo:**
  - App/modal: `bg-white` / `dark:bg-navy-800` (corpo do `Modal`).
  - Seções internas do formulário (cards agrupadores): `bg-gray-50
    dark:bg-navy-900/50`, borda `border-gray-200 dark:border-navy-700`,
    `rounded-lg p-4`.
  - Sub-card (formulário de novo item dentro da seção): `bg-white
    dark:bg-navy-800`, borda `border-gray-200 dark:border-navy-600`,
    `rounded-lg p-3`.
- **Texto:**
  - Título de seção: `text-sm font-semibold text-gray-700 dark:text-slate-200`.
  - Label de campo: `text-sm font-medium text-gray-700 dark:text-slate-300`
    (padrão `Input`/`Select`) ou `text-xs font-medium text-gray-600
    dark:text-slate-400` (label de campo dentro de sub-formulário, ex.
    "Observacoes" da entrada).
  - Muted/caption: `text-xs text-gray-400 dark:text-slate-500`.
  - Aviso (amarelo, já em uso p/ conversão que não fecha): `text-amber-700
    dark:text-amber-400`.
  - Erro: `text-red-600 dark:text-red-400` (mesma família já usada em toasts
    de erro do sistema).
- **Fonte:** Plus Jakarta Sans (headings) + DM Sans (body) — já carregadas
  globalmente, nenhuma ação aqui.
- **BorderRadius:** `rounded-lg` (cards de seção, sub-cards, inputs) —
  **não** usar `rounded-xl`/`rounded-md` nesta tela, manter consistente com o
  resto do modal de Produtos.
- **Componentes a reutilizar (não recriar):** `Input`, `Select`, `Button`,
  `Modal` (`frontend/src/components/ui/`). Textarea de observações usa
  `<textarea>` cru com a classe já padronizada no arquivo (ver Tela 2 abaixo)
  — não criar componente `Textarea` novo só para esta tarefa.
- **Ícones:** `lucide-react`, já importado no topo do arquivo
  (`Plus, Trash2, ArrowRight, Gift, Pencil`) — esta tarefa adiciona `Package`
  à importação existente (ver seção Ícones abaixo).

---

## Tela 1 — Modal de Produto: campo de estoque (RF-03, RF-04)

### Estado atual (a substituir)

Grid de 3 colunas (`grid grid-cols-1 sm:grid-cols-3 gap-4`, linha ~785) com
`Select Unidade Base` + `Input Qtd em Estoque` (editável, `name=
"quantidade_estoque"`) + `Input Estoque Minimo`. O input do meio some do fluxo
editável — vira dois comportamentos diferentes por modo (criação vs edição),
mantendo a mesma posição no grid para não quebrar o alinhamento visual.

### Modo Criação (`!editingId`)

Mantém o grid de 3 colunas. A coluna do meio passa a ser:

```jsx
<Input
  label="Estoque Inicial"
  name="estoque_inicial"
  type="number"
  step="0.001"
  min="0"
  value={form.estoque_inicial}
  onChange={handleChange}
  placeholder="0"
/>
```

- Mesmo componente `Input`, mesmas props de estilo do campo antigo — só troca
  `name`/`label`/`value`. Nenhuma mudança visual de layout.
- Sem asterisco de obrigatório (campo opcional, RF-04 — default `0` se vazio).
- Sem preview de conversão aqui — `estoque_inicial` é sempre lançado direto na
  `unidade_base` do produto (RF-04), não há seletor de unidade nesse campo.

### Modo Edição (`editingId`)

Coluna do meio vira **texto informativo, não input** — reaproveitar a
estrutura visual de "label acima + valor abaixo" do próprio `Input`, mas sem
campo editável:

```jsx
<div className="flex flex-col gap-1">
  <label className="text-sm font-medium text-gray-700 dark:text-slate-300">
    Estoque Atual
  </label>
  <div className="flex items-center gap-2 rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-700 dark:border-navy-700 dark:bg-navy-900/50 dark:text-slate-300">
    <Package size={14} className="text-gray-400 dark:text-slate-500 shrink-0" />
    <span className="font-medium">
      {form.quantidade_estoque} {unidadeLabel(form.unidade_base)}
    </span>
  </div>
</div>
```

- Visual "quase-input desabilitado": mesma altura/padding/border-radius de um
  `Input` normal (`rounded-lg`, `px-3 py-2`, `text-sm`), mas `bg-gray-50
  dark:bg-navy-900/50` (tom de "desabilitado", igual às seções agrupadoras) em
  vez de `bg-white` — sinaliza visualmente que não é clicável/editável, sem
  precisar de tooltip ou texto extra explicando.
- Ícone `Package` (14px, `lucide-react`) antes do valor — reforça "informação
  de estoque" sem precisar de mais texto.
- Fonte de dados: `form.quantidade_estoque` continua sendo populado a partir
  do produto carregado em `openEditModal` — só deixa de ser enviado no
  payload do submit (RF-03/RN-05 já garantem que o backend ignora o campo de
  qualquer forma; manter no `form` é só conveniência de exibição, não precisa
  de estado separado).
- **Não** incluir botão "Movimentar Estoque" dentro deste bloco — o botão de
  ação fica no cabeçalho da seção "Movimentar Estoque" (Tela 2), não
  duplicado aqui. Evita dois pontos de entrada para a mesma ação na mesma
  tela.

### Mobile (375px)

- Grid de 3 colunas já colapsa para 1 coluna via `grid-cols-1` (breakpoint
  `sm:`) — nenhuma mudança adicional necessária, o bloco de texto informativo
  empilha normalmente como os outros dois campos.

---

## Tela 2 — Seção "Movimentar Estoque" (RF-06, substitui "Entradas de Estoque")

Mantém a mesma estrutura de card agrupador já existente (linhas ~938-1042),
só renomeando "Entradas de Estoque" para "Movimentar Estoque" e estendendo o
formulário interno com o seletor de tipo + regras condicionais.

### Cabeçalho da seção

```jsx
<div className="flex items-center justify-between mb-3">
  <h3 className="text-sm font-semibold text-gray-700 dark:text-slate-200">
    Movimentar Estoque
  </h3>
  {!novoMovimento && (
    <button
      type="button"
      onClick={() => setNovoMovimento({ tipo: 'ENTRADA', quantidade: '', unidade: form.unidade_base, nota_fiscal: '', observacoes: '' })}
      className="flex items-center gap-1 text-xs text-primary-600 font-medium hover:text-primary-800 transition-colors dark:text-violet-400 dark:hover:text-violet-300"
    >
      <Plus size={14} />
      Registrar Movimento
    </button>
  )}
</div>
```

- Reaproveita 100% da classe do botão "+ Registrar Entrada" atual — só muda o
  label do botão e o estado inicial (`tipo: 'ENTRADA'` como default, é o caso
  mais comum, evita o usuário ter que selecionar toda vez).

### Formulário "novo movimento" (sub-card)

Mesmo container `bg-white dark:bg-navy-800 rounded-lg border ... p-3 mb-3
space-y-2` já usado. Ordem dos campos:

**1. Seletor de Tipo (novo, topo do formulário — antes de Quantidade):**

```jsx
<Select
  label="Tipo de Movimento"
  options={[
    { value: 'ENTRADA', label: 'Entrada' },
    { value: 'DEVOLUCAO_CLIENTE', label: 'Devolução de Cliente' },
    { value: 'PERDA', label: 'Perda / Quebra' },
    { value: 'AJUSTE', label: 'Ajuste de Inventário' },
    { value: 'SAIDA_MANUAL', label: 'Saída Manual' },
  ]}
  value={novoMovimento.tipo}
  onChange={(e) => setNovoMovimento((p) => ({ ...p, tipo: e.target.value, quantidade: '' }))}
/>
```

- `ENTRADA_INICIAL` **nunca** aparece nesta lista (uso interno, RF-06).
- Trocar o `tipo` limpa `quantidade` — evita o usuário deixar um valor
  negativo digitado para `AJUSTE` e trocar para `PERDA` sem perceber que o
  sinal não se aplica mais àquele tipo.
- Largura total (não dividir em grid com Quantidade) — é a decisão mais
  importante do formulário, merece linha própria.

**2. Grid Quantidade + Unidade** (mesmo `grid grid-cols-2 gap-2` já existente):
- `Input Quantidade`: `min="0"` **exceto quando `tipo === 'AJUSTE'`** — nesse
  caso remover o atributo `min` (permite negativo) e trocar o `placeholder`
  de `"0"` para `"Ex: -3 ou 3"` só para esse tipo, dando a dica de sinal sem
  precisar de texto de ajuda permanente.
- `Select Unidade`: inalterado.

**3. Preview de conversão** (RF-08 herdado): inalterado, já funciona
independente do tipo.

**4. Campo Motivo (reaproveita o campo Observações existente, não cria campo novo):**

```jsx
<div className="flex flex-col gap-1">
  <label className="text-xs font-medium text-gray-600 dark:text-slate-400">
    {novoMovimento.tipo === 'ENTRADA' ? 'Observações' : 'Motivo'}
    {novoMovimento.tipo !== 'ENTRADA' && <span className="text-red-500 ml-0.5">*</span>}
  </label>
  <textarea
    value={novoMovimento.observacoes}
    onChange={(e) => setNovoMovimento((p) => ({ ...p, observacoes: e.target.value }))}
    rows={2}
    placeholder={novoMovimento.tipo === 'ENTRADA' ? '' : 'Descreva o motivo deste movimento...'}
    className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent dark:border-navy-500 dark:bg-navy-800 dark:text-slate-100 dark:placeholder-slate-500 dark:focus:ring-violet-500"
  />
  {erroMotivo && (
    <p className="text-xs text-red-600 dark:text-red-400">Motivo é obrigatório para este tipo de movimento.</p>
  )}
</div>
```

- Label muda de "Observações" → "Motivo" com asterisco vermelho quando
  `tipo !== 'ENTRADA'` — sinaliza obrigatoriedade sem precisar de campo
  duplicado.
- Validação client-side (RF-06/RN-02): ao submeter, se `tipo !== 'ENTRADA'` e
  `observacoes.trim() === ''`, bloquear o submit e setar `erroMotivo=true`
  (não chamar a API) — mensagem de erro como acima, mesma família de cor de
  erro já usada em toasts do sistema.

**5. Campo Nota Fiscal — condicional:**

```jsx
{novoMovimento.tipo === 'ENTRADA' && (
  <Input
    label="Nota Fiscal"
    value={novoMovimento.nota_fiscal}
    onChange={(e) => setNovoMovimento((p) => ({ ...p, nota_fiscal: e.target.value }))}
    placeholder="NF-e 00001..."
  />
)}
```

- Some da tela quando `tipo !== 'ENTRADA'` (RF-07 — não bloqueado no backend,
  mas sem sentido visual fora de Entrada). Ordem no formulário: depois do
  campo Motivo, não antes — Motivo é a informação mais importante para os
  tipos não-Entrada, deve vir primeiro na leitura vertical.

**6. Botões de ação:** inalterados (`Confirmar` / `Cancelar`, mesmos
`Button size="sm"`).

### Fluxo de confirmação de estoque negativo (RN-04)

Ação client-side, sem novo componente de modal — reaproveita `window.confirm`
nativo (consistente com o resto do projeto, que não tem `ConfirmDialog`
customizado neste módulo):

```jsx
async function handleRegistrarMovimento() {
  setErroMotivo(false)
  if (novoMovimento.tipo !== 'ENTRADA' && !novoMovimento.observacoes.trim()) {
    setErroMotivo(true)
    return
  }
  await enviarMovimento(false)
}

async function enviarMovimento(forcarNegativo) {
  try {
    setSavingMovimento(true)
    await api.post(`/produtos/${editingId}/movimentos/`, {
      ...novoMovimento,
      ...(forcarNegativo ? { forcar_negativo: true } : {}),
    })
    // sucesso: limpa formulario, recarrega lista, toast de sucesso (padrao existente)
  } catch (err) {
    const data = err?.response?.data
    if (data?.confirmacao_necessaria) {
      const ok = window.confirm(data.mensagem)
      if (ok) return enviarMovimento(true)
      return // usuario cancelou — formulario permanece aberto, nada e limpo
    }
    // erro normal (ex: motivo obrigatorio vindo do backend, unidade sem conversao)
    // usar extractErrorMessage(err) + toast, padrao ja usado no resto do arquivo
  } finally {
    setSavingMovimento(false)
  }
}
```

- Sem UI nova a desenhar para o `confirm` — é o diálogo nativo do browser,
  suficiente para esta fase (RN-04 não pede modal customizado).
- Em caso de cancelar a confirmação, o formulário **não** é limpo nem
  fechado — usuário pode ajustar a quantidade e tentar de novo sem redigitar
  tudo.

### Listagem de movimentos (histórico)

Mesma lista compacta já existente (`space-y-1 max-h-40 overflow-y-auto`),
cada linha ganha o `tipo_display` + sinal (`efeito`) antes da quantidade:

```jsx
<div className="min-w-0">
  <span className={mov.efeito === '-' ? 'font-medium text-red-600 dark:text-red-400' : 'font-medium text-gray-700 dark:text-slate-300'}>
    {mov.efeito}{mov.quantidade} {mov.unidade}
  </span>
  <span className="text-gray-400 ml-1 dark:text-slate-500">— {mov.tipo_display}</span>
  {mov.nota_fiscal && <span className="text-gray-400 ml-1 dark:text-slate-500">({mov.nota_fiscal})</span>}
</div>
```

- Cor vermelha só na quantidade quando `efeito === '-'` (Perda, Saída Manual,
  ou Ajuste negativo) — reforço visual mínimo sem precisar de badge/ícone
  extra na lista compacta (a lista já é `text-xs`, um badge cheio poluiria).
  `ENTRADA`/`DEVOLUCAO_CLIENTE`/`AJUSTE` positivo mantêm a cor neutra atual
  (`text-gray-700 dark:text-slate-300`).
- `nota_fiscal` só aparece quando existir (comportamento atual, preservado —
  tipos não-Entrada normalmente não têm nota fiscal).

### Estado vazio / carregando

Inalterados: `"Carregando entradas..."` → renomear para `"Carregando
movimentos..."`; `"Nenhuma entrada registrada."` → `"Nenhum movimento
registrado."`. Mesma classe `text-xs text-gray-400 dark:text-slate-500`.

---

## Ícones (lucide-react)

Adicionar à importação existente no topo do arquivo (linha 2):

```jsx
import { Plus, Trash2, ArrowRight, Gift, Pencil, Package } from 'lucide-react'
```

| Uso | Ícone | Tamanho |
|---|---|---|
| Estoque atual (texto informativo, modo edição) | `<Package />` | 14px |
| Aviso de conversão que não fecha (já existente) | emoji `⚠` (manter — convenção já usada no arquivo para avisos inline, não trocar por ícone Lucide) | — |
| Registrar Movimento (botão) | `<Plus size={14} />` (reaproveita ícone já usado em "+ Registrar Entrada") | 14px |
| Remover item de conversão (já existente, inalterado) | `<Trash2 size={16} />` | 16px |

Não introduzir ícones por tipo de movimento (Entrada/Perda/Ajuste etc.) no
`Select` — poluiria a lista de opções nativa do `<select>` HTML (ícone dentro
de `<option>` não renderiza de forma confiável entre browsers); o texto do
label já é suficientemente descritivo.

---

## Mobile-first (375px)

- Seletor "Tipo de Movimento" em largura total (já decidido acima) — sem
  ajuste adicional necessário em mobile, já ocupa a linha inteira em
  qualquer breakpoint.
- Grid `Quantidade + Unidade` (`grid grid-cols-2 gap-2`) mantido em 2 colunas
  mesmo em 375px (comportamento atual, campos são curtos o suficiente — não
  colapsar para 1 coluna aqui, evita quebra de padrão com o resto do
  formulário).
- Bloco "Estoque Atual" (modo edição) empilha normalmente dentro do grid de 3
  colunas que já colapsa em `sm:` — nenhuma regra nova.
- Botões "Confirmar"/"Cancelar" do sub-formulário: mantêm `flex gap-2`
  existente, sem stack vertical — cabem lado a lado mesmo em 375px por serem
  `size="sm"`.

---

## Resumo de mudanças de estado (mapa para o Loom, não é código final)

| Estado antigo | Estado novo | Motivo |
|---|---|---|
| `novaEntrada` | `novoMovimento` (ganha campo `tipo`) | RF-06 |
| `entradas` | `movimentos` | RF-05 (rota renomeada) |
| `loadingEntradas` | `loadingMovimentos` | idem |
| `savingEntrada` | `savingMovimento` | idem |
| `handleRegistrarEntrada` | `handleRegistrarMovimento` | idem |
| — | `erroMotivo` (novo, bool) | validação client-side RN-02 |
| `form.quantidade_estoque` enviado no payload de submit | removido do payload (RF-03); campo continua no `form` só para exibição no modo edição | RF-03/RN-05 |
| — | `form.estoque_inicial` (novo, write-only, só usado no modo criação) | RF-04 |

---

## O que NÃO fazer

- Não criar modal separado para "Movimentar Estoque" — continua embutido no
  modal de edição de produto, como seção interna (mesmo padrão de hoje).
- Não estilizar o `window.confirm` de estoque negativo — é diálogo nativo,
  fora de escopo desta fase.
- Não adicionar badge de status/cor de fundo por tipo de movimento na lista
  — só a cor do texto da quantidade quando o efeito é negativo (evita
  poluição visual numa lista já compacta).
- Não expor `ENTRADA_INICIAL` em nenhum seletor ou filtro visível ao usuário.
- Não alterar `border-radius`, paleta de cores ou tipografia do projeto —
  esta é uma extensão de tela existente, não um novo design.

---

## Passagem de bastão

```
✅ Especificação UI concluída — UidCore (Manutenção #58, Fase 1)
   Telas analisadas: 2 (Modal de Produto — campo estoque | Seção Movimentar Estoque)
   Componentes reutilizados: Input, Select, Button, Modal (4 existentes)
   Novos padrões: nenhum — extensão fiel do padrão navy/violet já em uso em Produtos.jsx

📁 Arquivo: Especificacao_UI_Hotfix.md (raiz do projeto)

➡️ Loom lê Especificacao_Hotfix.md + Especificacao_UI_Hotfix.md
   antes de implementar o frontend
```
