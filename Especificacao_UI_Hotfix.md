# Especificação UI Hotfix — UidCore (Manutenção #53)
**Elaborado por:** Brush (MODO HOTFIX)
**Data:** 2026-08-25
**Referência:** Especificacao_Hotfix.md (Analista) — Manutenção #53

---

## Design System do Projeto (referência — não redefinido aqui)

Tokens navy/violet estabelecidos na Manutenção #31, já em uso em 100% de
`Produtos.jsx` (805 linhas atuais). Esta manutenção **não introduz paleta
nova** — só aplica os mesmos tokens à seção Combos.

| Token | Light | Dark | Uso |
|---|---|---|---|
| Superfície de página | `white` | `navy-800` | `Card` |
| Superfície de bloco interno (seção dentro de modal) | `gray-50` | `navy-900/50` | box de "Itens do Combo" |
| Superfície de linha de tabela hover | `gray-50` | `navy-700/60` | `hover:` na tabela |
| Header de tabela | `gray-50` / `border-gray-200` | `navy-900` / `border-navy-600` | `<thead>` |
| Bordas | `gray-300` / `gray-100` | `navy-500` / `navy-600` / `navy-700` | inputs, divisores |
| Interação (link/ação) | `primary-600` → `primary-800` hover | `violet-400` → `violet-300` hover | "+ Adicionar Item", links de ação |
| Interação (botão) | `primary-600` → `primary-700` hover | `violet-600` → `violet-700` hover | `Button variant="primary"` |
| Texto principal | `gray-900` | `slate-100` | nome do combo |
| Texto secundário | `gray-500` / `gray-600` | `slate-400` / `slate-500` | data, labels |
| Sucesso/dinheiro | `green-600`/`green-700` | `green-400`/`emerald-300` | Valor Total do combo |
| Perigo | `red-400`/`red-600` | `red-400/70`/`red-400` | remover item, botão Desativar |
| Fonte | Plus Jakarta Sans (headings) + DM Sans (corpo) | idem | já global, nenhuma mudança |
| BorderRadius | `rounded-lg` (inputs/botões), `rounded-full` (badges/pills), `rounded-xl` (Card) | idem | já global |

**Componentes a reutilizar (nenhum componente novo):**
`Card`, `Button`, `Input`, `Select`, `Modal`, de
`/var/www/uidcore/frontend/src/components/ui/`. `Pagination` **não é
necessário** nesta seção — lista de combos tende a ser pequena; se
crescer no futuro, replicar o mesmo padrão já usado na tabela de
Produtos (fora de escopo agora).

**Correção sobre a Especificacao_Hotfix.md do Analista:** o RF-06 sugere
emoji (`🎁 Combo`) e o estado vazio sugerido usa emoji (`🎁`). Regra
global Uid: **ícones sempre Lucide React, nunca emoji** (Produtos.jsx já
importa `lucide-react` para `Plus`/`Trash2`/`ArrowRight`). A seção Combos
usa exclusivamente ícones Lucide — ver seção "Ícones" abaixo. O emoji
`📦` do estado vazio de Produtos já existente **não é tocado** por esta
manutenção (fora de escopo, é código legado), mas o novo estado vazio de
Combos não deve repetir o padrão emoji.

---

## Ícones (Lucide React) — únicos a adicionar ao import de `Produtos.jsx`

```jsx
import { Plus, Trash2, ArrowRight, Gift, Pencil } from 'lucide-react'
```

(`Plus`, `Trash2`, `ArrowRight` já estão importados — só adicionar `Gift`
e `Pencil`.)

| Ícone | Tamanho | Onde |
|---|---|---|
| `<Gift size={18} />` | 18px | ao lado do título "Combos" da seção (identifica visualmente que é um grupo diferente da tabela de Produtos) |
| `<Gift size={40} />` | 40px | estado vazio da seção Combos (substitui emoji) |
| `<Plus size={16} />` | 16px | botão "Novo Combo" no header da seção |
| `<Plus size={14} />` | 14px | botão "Adicionar Item" dentro do modal (mesmo padrão de `addConversao`) |
| `<Trash2 size={16} />` | 16px | remover linha de item dentro do modal (mesmo padrão de `removeConversao`) |
| `<Trash2 size={14} />` | 14px | botão "Desativar" na tabela/cards de Combos |
| `<Pencil size={14} />` | 14px | botão "Editar" na tabela/cards de Combos |

---

## Especificação Visual por Tela

### Produtos.jsx — Nova Seção "Combos" (abaixo da `<Pagination>` de Produtos)

**Posição exata:** entre o fechamento do bloco `<Pagination page={page}
totalPages={totalPages} onPageChange={setPage} />` (linha 487 atual) e o
fechamento do `)` do bloco condicional de conteúdo (linha 489), OU como
um novo bloco irmão logo após esse `)}` de conteúdo de Produtos, antes do
Modal de Produto — a seção Combos **não depende** de `produtos.length >
0`, deve renderizar mesmo com lista de produtos vazia (são seções
independentes). Recomendação: bloco próprio fora do `{loading ? ... :
produtos.length === 0 ? ... : (...)}`, direto no JSX principal,
envolvido em `<div className="mt-8 space-y-4">`.

**Layout geral:**
- Wrapper: `<div className="mt-8 space-y-4">` (separa visualmente da
  tabela de Produtos acima com respiro vertical, sem usar `<hr>` — mesmo
  espaçamento vertical (`space-y-4`) já usado no container raiz da
  página)
- Padding: nenhum padding lateral extra — a página já usa `<div
  className="space-y-4">` como container raiz (linha 363), a seção
  Combos herda o mesmo alinhamento

**Mobile (< 640px, testar em 375px):**
- Cards empilhados em coluna única (`flex flex-col gap-3`), mesmo padrão
  exato dos cards de Produto (linhas 404–436 do arquivo atual)
- Modal de Combo: mesma resposividade do modal de Produto —
  `maxW="max-w-2xl"`, `max-h-[90vh] overflow-y-auto` já vem do `Modal.jsx`
  genérico, nenhuma customização extra
- Linhas de item dentro do modal: `flex-col` empilhado no mobile,
  `sm:flex-row` a partir de 640px — mesmo padrão de `conversoes` (ver
  linha 607 do arquivo atual: `flex flex-col gap-2 sm:flex-row
  sm:items-end`)

---

#### Header da seção Combos (RF-06)

```jsx
<div className="flex items-center justify-between gap-3">
  <div className="flex items-center gap-2">
    <Gift size={18} className="text-primary-600 dark:text-violet-400" />
    <div>
      <h2 className="text-lg font-bold text-gray-900 dark:text-slate-100">Combos</h2>
      <p className="text-xs text-gray-500 dark:text-slate-400">
        {combos.length} combo{combos.length !== 1 ? 's' : ''} cadastrado{combos.length !== 1 ? 's' : ''}
      </p>
    </div>
  </div>
  <Button size="sm" onClick={openNewCombo}>
    <Plus size={16} />
    Novo Combo
  </Button>
</div>
```

Nota: `Button` já renderiza `children` após o spinner de loading — passar
o ícone como primeiro filho funciona sem alteração no componente (mesmo
padrão do próprio `Button` interno, que usa `inline-flex items-center
gap-2`).

---

#### Estado vazio da seção Combos

```jsx
{loadingCombos ? (
  <div className="flex justify-center py-12 text-gray-400 dark:text-slate-500 text-sm">Carregando...</div>
) : combos.length === 0 ? (
  <div className="flex flex-col items-center justify-center py-12 gap-2 text-gray-400 dark:text-slate-500">
    <Gift size={40} className="text-gray-300 dark:text-navy-600" />
    <p className="text-sm">Nenhum combo cadastrado.</p>
  </div>
) : (
  /* tabela desktop + cards mobile abaixo */
)}
```

---

#### Tabela desktop (RF-08) — colunas Data, Nome, Valor Total, Ações

Estrutura idêntica à tabela de Produtos (`Card` + `overflow-x-auto -mx-6
-my-4` + `<table className="w-full text-sm">`), envolvida em `<div
className="hidden md:block">`:

```jsx
<div className="hidden md:block">
  <Card>
    <div className="overflow-x-auto -mx-6 -my-4">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-gray-50 border-b border-gray-200 dark:bg-navy-900 dark:border-navy-600">
            <th className="text-left px-6 py-3 font-semibold text-gray-600 whitespace-nowrap dark:text-slate-400">Data</th>
            <th className="text-left px-4 py-3 font-semibold text-gray-600 whitespace-nowrap dark:text-slate-400">Nome</th>
            <th className="text-right px-4 py-3 font-semibold text-gray-600 whitespace-nowrap dark:text-slate-400">Valor Total</th>
            <th className="text-right px-6 py-3 font-semibold text-gray-600 whitespace-nowrap dark:text-slate-400">Ações</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100 dark:divide-navy-700">
          {combos.map((c) => (
            <tr key={c.id} className="hover:bg-gray-50 dark:hover:bg-navy-700/60 transition-colors">
              <td className="px-6 py-3 text-gray-600 whitespace-nowrap dark:text-slate-400">
                {c.created_at ? new Date(c.created_at).toLocaleDateString('pt-BR') : '—'}
              </td>
              <td className="px-4 py-3 whitespace-nowrap max-w-[240px]">
                <p className="font-medium text-gray-900 truncate dark:text-slate-100">{c.nome}</p>
                <span className="text-xs text-gray-400 dark:text-slate-500">
                  {c.itens?.length || 0} item{(c.itens?.length || 0) !== 1 ? 's' : ''}
                </span>
              </td>
              <td className="px-4 py-3 text-right font-bold text-green-600 whitespace-nowrap dark:text-green-400">
                {BRL(c.valor_total)}
              </td>
              <td className="px-6 py-3 text-right whitespace-nowrap">
                <div className="flex items-center justify-end gap-2">
                  <Button size="sm" variant="secondary" onClick={() => openEditCombo(c)}>
                    <Pencil size={14} />
                    Editar
                  </Button>
                  <Button size="sm" variant="danger" onClick={() => handleDeleteCombo(c)}>
                    <Trash2 size={14} />
                    Desativar
                  </Button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  </Card>
</div>
```

**Decisão de design — Valor Total em verde:** diferente da coluna "Preco
Venda" da tabela de Produtos (que usa `text-gray-900 dark:text-slate-100`,
neutro), o Valor Total do Combo usa `text-green-600 dark:text-green-400`
(cor de dinheiro/sucesso do design system). Justificativa: é o dado mais
importante da linha (o "resultado" do combo, soma de itens), e a origem
no SystemD já usava verde (`#34d399`) para esse mesmo campo — mantém
consistência de leitura entre os dois produtos Uid sem violar o token set
do UidCore (`green-400`/`emerald-300` já documentado como "Sucesso/dinheiro").

**Label do botão de exclusão:** "Desativar" (não "Excluir") — reforça que
é soft delete (RF-04/RNF-03), mesmo texto usado no combo de origem
(SystemD) e coerente com o botão "Desativar" já usado em outras telas do
UidCore para soft delete. Diferente do botão "Excluir" já existente na
tabela de Produtos (nomenclatura legada, fora de escopo mudar aqui) —
aceitar a pequena inconsistência entre as duas seções da mesma página
por ora; não é objeto desta manutenção uniformizar o texto do botão de
Produtos.

---

#### Cards mobile (RF-08) — `md:hidden`

```jsx
<div className="flex flex-col gap-3 md:hidden">
  {combos.map((c) => (
    <Card key={c.id}>
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="font-semibold text-gray-900 truncate dark:text-slate-100">{c.nome}</p>
          <p className="text-xs text-gray-400 mt-0.5 dark:text-slate-500">
            {c.created_at ? new Date(c.created_at).toLocaleDateString('pt-BR') : '—'}
            {' · '}
            {c.itens?.length || 0} item{(c.itens?.length || 0) !== 1 ? 's' : ''}
          </p>
        </div>
        <span className="shrink-0 font-bold text-green-600 dark:text-green-400">
          {BRL(c.valor_total)}
        </span>
      </div>
      <div className="mt-3 flex gap-2">
        <Button size="sm" variant="secondary" onClick={() => openEditCombo(c)} className="flex-1">
          <Pencil size={14} />
          Editar
        </Button>
        <Button size="sm" variant="danger" onClick={() => handleDeleteCombo(c)} className="flex-1">
          <Trash2 size={14} />
          Desativar
        </Button>
      </div>
    </Card>
  ))}
</div>
```

Padrão idêntico aos cards de Produto (linhas 404–436): `Card` envolvendo
header flex + linha de ações no fim, mas com botões `flex-1` (ocupam a
largura toda, lado a lado) em vez de largura automática — como Combo tem
só 2 ações (Editar/Desativar) contra as mesmas 2 de Produto, mantém
paridade exata de estilo; a única diferença é o `className="flex-1"`
adicional nos botões, puramente estético para preencher a largura do
card em telas pequenas (Produtos já faz `gap-2` sem `flex-1` — ambos são
aceitáveis, mas `flex-1` fica mais equilibrado com 2 botões com ícone).

---

#### Modal de Criar/Editar Combo (RF-01, RF-03, RF-07)

`maxW="max-w-2xl"` (mesma largura do modal de Produto — precisa de
espaço para as linhas de item com 3 campos + botão remover lado a lado
no desktop).

```jsx
{comboModalOpen && (
  <Modal
    title={editingComboId ? 'Editar Combo' : 'Novo Combo'}
    onClose={() => setComboModalOpen(false)}
    maxW="max-w-2xl"
  >
    <form onSubmit={handleSubmitCombo} className="space-y-4">
      <Input
        label="Nome"
        name="nome"
        value={comboForm.nome}
        onChange={(e) => setComboForm((p) => ({ ...p, nome: e.target.value }))}
        placeholder="Ex.: Combo Café da Manhã"
        required
      />

      <div className="flex flex-col gap-1">
        <label className="text-sm font-medium text-gray-700 dark:text-slate-300">Descrição</label>
        <textarea
          value={comboForm.descricao}
          onChange={(e) => setComboForm((p) => ({ ...p, descricao: e.target.value }))}
          rows={2}
          placeholder="Opcional"
          className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent dark:border-navy-500 dark:bg-navy-800 dark:text-slate-100 dark:placeholder-slate-500 dark:focus:ring-violet-500 transition-colors duration-150"
        />
      </div>

      {/* Secao Itens do Combo — mesmo box visual da secao Conversoes de Unidade */}
      <div className="bg-gray-50 rounded-lg border border-gray-200 p-4 dark:bg-navy-900/50 dark:border-navy-700">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-gray-700 dark:text-slate-200">Itens do Combo</h3>
          <button
            type="button"
            onClick={addComboItem}
            className="flex items-center gap-1 text-xs text-primary-600 font-medium hover:text-primary-800 transition-colors dark:text-violet-400 dark:hover:text-violet-300"
          >
            <Plus size={14} />
            Adicionar Item
          </button>
        </div>

        {comboItens.length === 0 && (
          <p className="text-xs text-gray-400 dark:text-slate-500">
            Nenhum item adicionado. Clique em "Adicionar Item" para começar.
          </p>
        )}

        <div className="space-y-2">
          {comboItens.map((item, idx) => {
            const subtotal = Number(item.quantidade || 0) * Number(item.valor_unitario || 0)
            return (
              <div key={idx} className="flex flex-col gap-2 sm:flex-row sm:items-end">
                <div className="flex-1 sm:flex-[2]">
                  <Select
                    label="Produto"
                    options={produtoSelectOptions}
                    value={item.produto || ''}
                    onChange={(e) => updateComboItem(idx, 'produto', e.target.value, produtoSelectOptions)}
                  />
                </div>
                <div className="w-full sm:w-24">
                  <Input
                    label="Qtd."
                    type="number"
                    step="0.001"
                    min="0.001"
                    value={item.quantidade}
                    onChange={(e) => updateComboItem(idx, 'quantidade', e.target.value)}
                    placeholder="1"
                  />
                </div>
                <div className="w-full sm:w-32">
                  <Input
                    label="Valor Unit. (R$)"
                    type="number"
                    step="0.01"
                    min="0"
                    value={item.valor_unitario}
                    onChange={(e) => updateComboItem(idx, 'valor_unitario', e.target.value)}
                    placeholder="0,00"
                  />
                </div>
                <div className="flex items-center gap-2 sm:mb-1">
                  <span className="text-xs font-medium text-gray-600 whitespace-nowrap dark:text-slate-300 flex-1 sm:flex-none text-right sm:text-left">
                    {BRL(subtotal)}
                  </span>
                  <button
                    type="button"
                    onClick={() => removeComboItem(idx)}
                    className="text-red-400 hover:text-red-600 transition-colors p-1 dark:text-red-400/70 dark:hover:text-red-400"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
            )
          })}
        </div>

        {comboItens.length > 0 && (
          <div className="flex justify-between items-center pt-3 mt-3 border-t border-gray-200 dark:border-navy-700">
            <span className="text-sm font-semibold text-gray-700 dark:text-slate-200">Valor Total</span>
            <span className="text-base font-bold text-green-600 dark:text-green-400">
              {BRL(comboItens.reduce((acc, i) => acc + Number(i.quantidade || 0) * Number(i.valor_unitario || 0), 0))}
            </span>
          </div>
        )}
      </div>

      <div className="flex justify-end gap-3 pt-2">
        <Button type="button" variant="secondary" onClick={() => setComboModalOpen(false)}>
          Cancelar
        </Button>
        <Button type="submit" loading={savingCombo}>
          {editingComboId ? 'Salvar Alteracoes' : 'Cadastrar Combo'}
        </Button>
      </div>
    </form>
  </Modal>
)}
```

**Sobre o Select de produto (`produtoSelectOptions`):** montar a partir
do catálogo carregado uma vez ao abrir o modal (`api.get('/produtos/', {
params: { page_size: 200 } })`, conforme já especificado pelo Analista),
no formato `{ value: produto.id, label: produto.nome }`, com um item
`{ value: '', label: 'Selecione um produto...' }` no topo — mesmo padrão
de `UNIDADE_SELECT` já existente no arquivo (linha 23). Ao selecionar um
produto (`onChange`), `updateComboItem` deve também pré-preencher
`valor_unitario` com `produto.preco_venda` do catálogo carregado (RF-07)
— só na primeira seleção da linha, o campo continua editável depois
(snapshot ajustável, RN-03).

**Enquanto o catálogo de produtos carrega** (entre abrir o modal e a
resposta do `GET /produtos/`): `Select` de produto deve mostrar apenas
`{ value: '', label: 'Carregando produtos...' }` e ficar `disabled`
(prop nativa do `<select>`, `Select.jsx` já repassa via `...props`).

**Erros de validação (RN-01/RN-02):** exibidos via `showToast` (padrão
`extractErrorMessage`/toast já usado em toda a página) — não introduzir
caixa de erro inline nova dentro do modal. Mesma decisão já tomada nas
Conversões de Unidade da própria página.

---

## Estrutura de estado sugerida (alinhamento com o Analista)

A Especificacao_Hotfix.md já define o estado (`combos`, `comboForm`,
`comboItens`, `editingComboId`, `comboModalOpen`, `savingCombo`,
`loadingCombos`). Do lado de UI, `comboItens` deve ter o formato:

```js
{ produto: '', quantidade: '1', valor_unitario: '' }
```

(igual ao formato de `EMPTY_CONVERSAO` já usado para as linhas de
conversão — objeto simples, sem `id` até ser persistido; ao editar um
combo existente, os itens vindos de `combo.itens` são mapeados para
`{ produto: item.produto, quantidade: item.quantidade, valor_unitario:
item.valor_unitario }`, descartando `id`/`subtotal`/`produto_nome` que
só existem para leitura, já que RF-03/RN-04 fazem delete-and-recreate no
backend — não há PATCH de item individual).

---

## Checklist de consistência visual (para o Sentinel validar)

```
✅ Nenhum emoji na seção Combos (Gift/Plus/Trash2/Pencil via lucide-react)
✅ Nenhum style={{...}} inline — só classes Tailwind
✅ Todas as classes dark:* espelham exatamente os tokens já usados na
   tabela/modal de Produtos (mesmo arquivo)
✅ Valor Total em verde (green-600/green-400) — única cor nova aplicada
   nesta seção, já parte do design system documentado (Sucesso/dinheiro)
✅ Botão de soft delete rotulado "Desativar", não "Excluir"
✅ Botões Editar/Desativar com ícone (Pencil/Trash2) + texto — não
   icon-only (mantém legibilidade, mesmo padrão textual já usado em
   Produtos, só adicionando o ícone)
✅ Modal com mesma largura (max-w-2xl) e comportamento de overflow do
   modal de Produto
✅ Testado visualmente em 375px: linhas de item do modal empilham em
   coluna única, botões de ação dos cards mobile ocupam a largura toda
```

---

## Passagem de bastão

```
✅ Especificação UI concluída — UidCore (Manutenção #53)
   Telas analisadas: 1 (Produtos.jsx — nova seção Combos)
   Componentes reutilizados: 5 (Card, Button, Input, Select, Modal)
   Ícones novos: 2 (Gift, Pencil — ambos lucide-react, já na mesma
     biblioteca importada no arquivo)
   Novos padrões: 1 (cor verde para valor monetário de destaque —
     justificada, dentro do token set já documentado)

📁 Arquivo: Especificacao_UI_Hotfix.md (no worktree)

➡️ Loom lê Especificacao_Hotfix.md + Especificacao_UI_Hotfix.md
   antes de implementar RF-06/RF-07/RF-08 em Produtos.jsx
```
