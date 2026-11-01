# Especificação UI Hotfix — UidCore (Manutenção #88)

## Modo

**MODO HOTFIX.** Uma tela nova (Financeiro → Categorias, CRUD com
hierarquia pai/subcategoria), um micro-componente novo reaproveitado em
3 formulários (atalho "+ Nova categoria" em Plano/Receita/Despesa) e um
campo que falta em 2 formulários existentes (`<Select>` de Categoria em
Receita e Despesa — hoje só existe no estado do form, nunca foi
renderizado). Nenhuma mudança de identidade visual, paleta ou tipografia
— tudo reaproveita o design system já em produção.

Lido antes de escrever esta especificação: `Especificacao_Hotfix.md`
(Manutenção #88), `frontend/tailwind.config.js`, `components/ui/{Select,
Modal,Card,Button,Input}.jsx`, `pages/Assinaturas.jsx` (`AbaListaPlanos`,
linhas 626-803) e `pages/Financeiro.jsx` (`TABS`, `ReceitasTab`,
`DespesasTab`, `MesColapsavel`) — trechos relevantes, não o arquivo
inteiro de cabo a rabo.

## Design System do Projeto (referência — não alterado)

- **Cores primárias:** `primary-600` (light) / `violet-600` (dark) —
  botão de ação, aba ativa. Hover: `primary-700`/`violet-700`.
- **Cores de fundo:** `white`/`gray-50` (light), `navy-800`/`navy-900`
  (dark) — `navy-700` para bordas/divisores (`divide-navy-700`).
- **Texto:** `text-gray-900`/`text-gray-700`/`text-gray-400` (light),
  `text-slate-100`/`text-slate-300`/`text-slate-500` (dark).
- **Fonte:** Plus Jakarta Sans (display) + DM Sans (body) — já carregadas
  globalmente, não tocar.
- **BorderRadius:** `rounded-lg` (inputs, botões, badges não-pill),
  `rounded-xl` (`Card.jsx`), `rounded-full`/pill (badges de status, ex.:
  `plano.ativo` em `AbaListaPlanos`).
- **Padrão de card:** `Card.jsx` — `bg-white dark:bg-navy-800 border
  border-gray-200 dark:border-navy-600 rounded-xl shadow-sm
  dark:shadow-none`.
- **Padrão de lista dentro de Card:** `divide-y divide-gray-100
  dark:divide-navy-700` envolvendo linhas `flex items-center
  justify-between gap-3 py-3 first:pt-0 last:pb-0` — é exatamente o
  padrão de `AbaListaPlanos`, citado no briefing do Analista como
  referência, e é o que esta especificação usa para a tela de
  Categorias (ver seção 1).
- **Dark mode:** classe `dark` no `<html>`, toggle ☀️/🌙 já existente —
  não tocar.
- **Ícones:** `lucide-react` (biblioteca já é dependência do projeto,
  usada em praticamente toda tela — `Pencil`, `Trash2`, `Plus`, `Search`
  etc.). **Sem emoji nesta tela** — emoji é padrão intencional só da
  Sidebar (ver CLAUDE.md global), nunca de telas internas de cadastro.
- **Componentes a reutilizar (nenhum componente novo de base — só 1
  micro-componente de domínio, ver seção 2):** `Card`, `Modal`, `Button`,
  `Select`, `Input`, `AuditFooter`. **Nada de `ResourceCrud.jsx`** — a
  hierarquia pai/subcategoria com indentação visual não cabe no contrato
  genérico de tabela do `ResourceCrud` (que não suporta linhas
  aninhadas/indentadas); seguir o padrão `AbaListaPlanos` (lista manual em
  `Card`), como o Analista já apontou.

---

## Especificação Visual por Tela

### 1. Financeiro → Categorias (nova aba dentro de `Financeiro.jsx`)

**Localização exata:**
- Novo item no array `TABS` (topo de `Financeiro.jsx`): `{ key:
  'categorias', label: 'Categorias' }`, inserido **depois de `contas` e
  antes de `livro`** — agrupa as duas abas de "cadastro base" (Contas,
  Categorias) antes das abas de livro/relatório (Livro Caixa, DRE,
  EBITDA, Balanço, Indicadores).
- Novo componente `CategoriasTab` no mesmo arquivo, renderizado como
  `{tab === 'categorias' && <CategoriasTab showToast={showToast} />}`,
  ao lado de `ReceitasTab`/`DespesasTab`/`ContasTab`.
- Tabs continuam sem ícone (texto puro) — `TABS.map` atual não tem slot
  de ícone; não adicionar um só para esta aba (quebraria o padrão visual
  das outras 9 abas).

**Layout geral:**
- `<div className="space-y-4">` (mesmo padrão de `ReceitasTab`).
- **Cabeçalho da aba** (igual `ReceitasTab`/`DespesasTab`, não igual
  `AbaListaPlanos` — dentro de `Financeiro.jsx` toda aba já mostra seu
  próprio `<h2>`, diferente de `Assinaturas.jsx` onde o título da página
  já existe em outro lugar; seguir a convenção do arquivo-pai):
  ```
  <div className="flex items-center justify-between gap-3">
    <h2 className="text-lg font-semibold text-gray-800 dark:text-slate-100">Categorias</h2>
    <Button onClick={openNovo}><Plus size={16} />Nova Categoria</Button>
  </div>
  ```
- **Barra de filtros** — `Card` envolvendo `flex flex-col sm:flex-row
  gap-3` (cópia exata do bloco de filtro de `ReceitasTab`, linhas
  563-572):
  - `Input` `flex-1`, `placeholder="Buscar categoria..."`, sem ícone
    prefixado (ReceitasTab/DespesasTab também usam `Input` simples sem
    ícone — manter consistência dentro do mesmo arquivo em vez de copiar
    o padrão com ícone de `Vendas.jsx`/`Compras.jsx`, que é de outra
    tela).
  - `Select` `w-full sm:w-48`, options `[{value:'',label:'Todas'},
    {value:'ENTRADA',label:'Entrada'},{value:'SAIDA',label:'Saída'}]`
    (nova constante `TIPO_CATEGORIA_FILTRO`, perto das outras constantes
    `TIPO_*`/`STATUS_*` no topo do arquivo).
  - Busca consome `search_fields=['nome']` novo do backend (RF-04);
    filtro consome `filterset_fields=['tipo']` já existente.
- **Cards de agrupamento (por tipo, com hierarquia pai→subcategoria):**
  - Quando o filtro é "Todas": renderizar **dois `Card`s**, um por
    tipo (`Entradas` primeiro, `Saídas` depois), cada um só aparece se
    tiver ao menos 1 categoria daquele tipo.
  - Quando o filtro é `ENTRADA` ou `SAIDA`: renderizar **um único
    `Card`**, sem repetir o cabeçalho de tipo (já está implícito no
    filtro ativo).
  - Cabeçalho de cada bloco de tipo (só quando "Todas", para
    diferenciar os dois grupos):
    ```
    <p className="text-xs font-semibold uppercase tracking-wide text-green-700 dark:text-emerald-400 mb-2">Entradas</p>
    <p className="text-xs font-semibold uppercase tracking-wide text-red-700 dark:text-red-400 mb-2">Saídas</p>
    ```
    (mesmas classes de cor já usadas em `colorClass` de `MesColapsavel`,
    linha ~157 de `Financeiro.jsx` — reaproveitar, não inventar tom novo).
  - Dentro do `Card`, lista única `divide-y divide-gray-100
    dark:divide-navy-700` (padrão `AbaListaPlanos`), montada em código
    assim: para cada categoria-pai (ordenada por `nome`, `pai === null`)
    do tipo, renderizar a linha do pai e, imediatamente depois, as
    linhas de `subcategorias` dela (ordenadas por `nome`) — **mesma
    lista `divide-y`**, não uma lista aninhada dentro da outra (evita
    duplicar borda/padding).
  - **Linha de categoria-pai:**
    ```
    <div className="flex items-center justify-between gap-3 py-3 first:pt-0 last:pb-0">
      <div className="min-w-0 flex items-center gap-2">
        <p className="font-medium text-gray-800 dark:text-slate-200 truncate">{cat.nome}</p>
        {cat.subcategorias_count > 0 && (
          <span className="text-xs text-gray-400 dark:text-slate-500 shrink-0">
            {cat.subcategorias_count} subcategoria{cat.subcategorias_count > 1 ? 's' : ''}
          </span>
        )}
      </div>
      <div className="flex items-center gap-3 shrink-0">
        {/* badge tipo + badge ativo/inativo + Pencil + Trash2 — ver abaixo */}
      </div>
    </div>
    ```
  - **Linha de subcategoria** (mesma estrutura, com indentação e peso
    visual menor, pra marcar subordinação ao pai):
    ```
    <div className="flex items-center justify-between gap-3 py-3 pl-6">
      <div className="min-w-0 flex items-center gap-2">
        <CornerDownRight size={14} className="text-gray-400 dark:text-slate-500 shrink-0" />
        <p className="text-sm text-gray-600 dark:text-slate-300 truncate">{sub.nome}</p>
      </div>
      <div className="flex items-center gap-3 shrink-0">
        {/* badge tipo + badge ativo/inativo + Pencil + Trash2 */}
      </div>
    </div>
    ```
    (subcategoria nunca mostra o contador "N subcategorias" — modelagem
    trava nesting em 1 nível, RN-03).
  - **Badges nas duas linhas** (mesmo padrão pill de
    `plano.ativo`/`Badge status` já no arquivo):
    - Tipo: `bg-green-100 text-green-800 dark:bg-emerald-900/30
      dark:text-emerald-300` para `ENTRADA` → texto "Entrada"; `bg-red-100
      text-red-800 dark:bg-red-900/30 dark:text-red-300` para `SAIDA` →
      texto "Saída". (Só exibir o badge de tipo quando o filtro ativo for
      "Todas" — se o usuário já filtrou por um tipo, o badge é ruído
      redundante; decisão do Loom se quiser manter sempre visível, não é
      bloqueante.)
    - Ativo/Inativo: `bg-green-100 text-green-800
      dark:bg-emerald-900/30 dark:text-emerald-300` / `bg-gray-100
      text-gray-600 dark:bg-navy-700 dark:text-slate-400` — idêntico ao
      badge `plano.ativo` de `AbaListaPlanos`.
  - **Ações por linha:** `Pencil` (16px, `text-gray-400
    hover:text-primary-600 dark:text-slate-500 dark:hover:text-violet-400`)
    e `Trash2` (16px, `text-gray-400 hover:text-red-600 dark:text-slate-500
    dark:hover:text-red-400`) — exatamente os botões de ícone de
    `AbaListaPlanos` (linhas 755-762), sem adaptação.
  - **Exclusão:** `window.confirm('Excluir a categoria "${cat.nome}"?')`
    → `DELETE /financeiro/categorias/{id}/`. Em caso de erro 400 (RN-06 —
    categoria-pai com subcategoria ativa, ou em uso por Plano/Receita/
    Despesa), mostrar a mensagem real do backend via `extractErrorMessage`
    em toast de erro (nunca um "erro ao excluir" genérico — o backend já
    devolve o motivo específico).
- **Estado vazio (nenhuma categoria de nenhum tipo):**
  ```
  <div className="flex flex-col items-center justify-center py-12 gap-2 text-gray-400 dark:text-slate-500">
    <Tag size={32} className="text-gray-300 dark:text-slate-600" />
    <p className="text-sm">Nenhuma categoria cadastrada.</p>
    <p className="text-xs">Crie a primeira pelo botão "Nova Categoria" acima.</p>
  </div>
  ```
- **Estado vazio por filtro** (ex.: filtrou "Saída" mas só existe
  "Entrada" cadastrada): dentro do `Card` daquele grupo, `<p
  className="text-sm text-gray-400 dark:text-slate-500 py-6
  text-center">Nenhuma categoria do tipo selecionado.</p>`.
- **Modal de criar/editar** (`title={editingId ? 'Editar Categoria' :
  'Nova Categoria'}`, `maxW="max-w-lg"`, mesmo tamanho do modal de Plano):
  1. `Select label="Tipo"` — options `[{value:'ENTRADA',label:'Entrada'},
     {value:'SAIDA',label:'Saída'}]` (nova constante `TIPO_CATEGORIA`,
     **sem opção vazia** — tipo é obrigatório, default `ENTRADA` em
     criação). Ao mudar o tipo: resetar `form.pai` para `''` e refazer o
     fetch de `paiOptions` filtrado pelo novo tipo (ver abaixo).
  2. `Input label="Nome"`.
  3. `Select label="Categoria-pai (opcional)"` — options `[{value:'',
     label:'Nenhuma (categoria principal)'}, ...lista]`. A lista vem de
     `GET /financeiro/categorias/?tipo={form.tipo}&page_size=200`,
     filtrada **no cliente** (replicando manualmente o que
     `limit_choices_to` faria — ver seção 8 da Especificacao_Hotfix.md):
     só categorias com `pai === null` (não pode escolher uma subcategoria
     como pai — RN-03) e, em modo edição, excluindo a própria categoria
     (`c.id !== editingId`, RN-02 — não pode ser pai de si mesma) e
     excluindo o pai da categoria em edição caso ela já tenha
     subcategorias ativas (RN-01 — opcional reforçar no frontend, o
     backend já bloqueia, mas evita round-trip de erro desnecessário).
     Texto de ajuda abaixo: `<p className="text-xs text-gray-400
     dark:text-slate-500 -mt-2">Deixe em branco para criar uma categoria
     principal. Só é possível 1 nível de subcategoria.</p>`.
  4. (só em edição) `<AuditFooter item={categoriaEmEdicao} />` — mesmo
     padrão já usado em todo modal de edição do projeto.
  5. Rodapé: `Button variant="secondary"` Cancelar + `Button` Salvar/
     Cadastrar (`loading={saving}`), mesmo padrão de `AbaListaPlanos`.
  - **Sem toggle "Ativa/Inativa" no formulário** — desativação é só via
    ícone `Trash2` + confirmação (soft delete); não há reativação pela
    tela nesta manutenção (decisão já registrada na Especificacao_Hotfix.md,
    seção 8 — manter o caminho mais simples).

**Ícones Lucide usados nesta tela:** `Plus` (botão "Nova Categoria"),
`Pencil` (editar linha), `Trash2` (excluir linha), `CornerDownRight`
(indentação de subcategoria), `Tag` (estado vazio). Import a adicionar em
`Financeiro.jsx`: `import { ChevronDown, ChevronUp, Edit, Plus, Pencil,
Trash2, CornerDownRight, Tag } from 'lucide-react'` (os três primeiros já
existem no arquivo — só acrescentar os novos à lista existente).

**Mobile-first (375px):**
- Barra de filtros: `flex-col` empilha Input e Select (já é o
  comportamento padrão herdado de `ReceitasTab`).
- Linha de categoria: `justify-between` com `shrink-0` nas badges/ícones
  garante que nome longo trunca (`truncate`) em vez de empurrar os
  controles de ação pra fora da tela — mesmo mecanismo já usado em
  `AbaListaPlanos`.
- Botão "Nova Categoria" no cabeçalho: em telas muito estreitas, se o
  `<h2>` + botão não couberem numa linha, o `flex items-center
  justify-between` já deixado quebra para o botão ficar à direita sem
  overflow — mesmo padrão de `ReceitasTab`/`DespesasTab`, sem CSS novo.
- Nunca usar `overflow-hidden` no container da aba (regra global do
  projeto).

---

### 2. Modal "+ Nova categoria" (atalho empilhado — reaproveitado em Plano, Receita e Despesa)

**Componente novo e onde ele vive:** este é o único ponto desta
manutenção que precisa de um componente **compartilhado entre arquivos**
(`Assinaturas.jsx` e `Financeiro.jsx`) — por isso não pode viver dentro
de um dos dois `.jsx` de página. Local sugerido:
`frontend/src/components/ui/CriarCategoriaRapidaModal.jsx`. É o
único componente "de domínio financeiro" dentro de `components/ui/`
(resto da pasta é genérico) — aceitável porque ele só compõe `Modal` +
`Input` + `Button` genéricos, sem lógica de negócio presa a uma tela
específica; qualquer forma futura que precise criar Categoria rápida
(ex.: um 4º form) reaproveita o mesmo componente em vez de duplicar.

**Layout:**
- `<Modal title="Nova Categoria" maxW="max-w-sm" onClose={...}>` — menor
  que o modal de CRUD completo (`max-w-lg`), porque só tem 1 campo
  editável de verdade.
- Conteúdo:
  - Texto fixo informando o tipo implícito (não editável, sem `<Select>`
    de tipo neste modal — o objetivo é criar rápido sem redundância, tipo
    já vem do contexto de onde o atalho foi clicado):
    `<p className="text-xs text-gray-400 dark:text-slate-500">Tipo: {tipo === 'ENTRADA' ? 'Entrada' : 'Saída'}</p>`.
  - `<Input label="Nome" autoFocus ... />`.
  - Rodapé: `Button variant="secondary"` Cancelar + `Button` Criar
    (`loading={saving}`).
- **Comportamento:** `POST /financeiro/categorias/` com `{nome, tipo}`
  (tipo vem fixo da prop, nunca do usuário). Sucesso → chama
  `onCreated(categoriaCriada)` (devolve o objeto completo, não só o id,
  pro componente-pai poder atualizar `categoriaOptions` sem precisar
  refazer o fetch se preferir) e fecha o modal. Erro → `extractErrorMessage`
  em toast (reaproveitar o `showToast` do componente-pai via prop, nunca
  falhar silenciosamente).
- **Empilhamento visual (sem mudar `Modal.jsx`):** o modal-pai (Plano/
  Receita/Despesa) já está aberto quando o atalho é clicado. Renderizar
  este segundo `<Modal>` **depois** dele na árvore JSX (ex.:
  `{modalOpen && <Modal>...</Modal>}` seguido de `{categoriaRapidaAberta
  && <CriarCategoriaRapidaModal ... />}`) já posiciona o novo modal por
  cima — ambos usam `z-50` fixo, e o elemento inserido depois no DOM
  pinta por cima dentro do mesmo contexto de empilhamento. **Não é
  necessário** adicionar prop de `zIndex` ao `Modal.jsx` nem criar
  variante nova — isso evita tocar num componente consumido por toda
  tela do sistema. O overlay escurece em dobro (aceitável); fechar o
  modal de cima primeiro é o único fluxo (clicar fora/✕ do modal rápido
  nunca fecha os dois de uma vez).

**Gatilho "+ Nova categoria" (nos 3 forms):**
- Como `Select.jsx` não tem slot para uma ação ao lado do `<label>`,
  **não alterar o componente genérico** (ele é usado em toda tela do
  sistema — mudar o contrato dele é risco de regressão fora do escopo).
  Em vez disso, nos 3 pontos específicos (Plano/Receita/Despesa),
  substituir o uso do `<Select label="Categoria" .../>` por um bloco
  manual que replica a estrutura interna do `Select` (label + select) e
  adiciona o botão ao lado — mesmo nível de "customização pontual" já
  usado hoje pros textos de ajuda abaixo de outros campos (ex.: "Mês de
  referência"):
  ```
  <div className="flex flex-col gap-1">
    <div className="flex items-center justify-between">
      <label className="text-sm font-medium text-gray-700 dark:text-slate-300">Categoria</label>
      <button type="button" onClick={() => setCategoriaRapidaAberta(true)}
        className="text-xs text-primary-600 hover:underline dark:text-violet-400 inline-flex items-center gap-1">
        <Plus size={12} />Nova categoria
      </button>
    </div>
    <Select name="categoria" options={categoriaOptions} value={form.categoria} onChange={handleChange} />
  </div>
  ```
- Depois de criar com sucesso (`onCreated`): refaz o fetch de
  `categoriaOptions` (reaproveitar a mesma função `useEffect` já existente
  em cada form) e `setForm((f) => ({ ...f, categoria: categoriaCriada.id }))`
  — seleciona automaticamente a categoria recém-criada (CA-07).
- Em **Plano** (`AbaListaPlanos`): `tipo="ENTRADA"` fixo (já é a única
  opção válida, `Plano.categoria` só aceita `tipo=ENTRADA`).
- Em **Receita**: `tipo="ENTRADA"` fixo. Em **Despesa**: `tipo="SAIDA"`
  fixo.

**Ícones Lucide:** `Plus` (12px, dentro do botão-link "Nova categoria" —
tamanho menor que os 16px usados em botões normais, porque é um
link/ação secundária inline, não um botão de destaque).

---

### 3. Campo Categoria em Receita e Despesa (RF-11 — hoje inexistente)

**Contexto:** o `<Select>` nunca existiu nesses dois modais — só o
estado (`form.categoria`) e o payload já previam o campo. Esta seção
define onde o campo novo entra visualmente.

**Layout — `ReceitasTab` (modal "Nova/Editar Receita"):**
- Posição: **linha própria**, entre o grid `grid-cols-1 sm:grid-cols-2`
  de Tipo/Conta (linhas 654-657 atuais) e o `Input label="Descrição"`
  (linha 658). Não encaixar como 3ª coluna do grid existente (isso
  apertaria Tipo/Conta em telas intermediárias) — usar o mesmo padrão já
  aplicado ao campo "Mês de referência" (campo único, linha cheia, com
  texto de ajuda abaixo em `-mt-2`).
- Bloco completo (usa a estrutura manual com atalho da seção 2):
  ```
  <div className="flex flex-col gap-1">
    <div className="flex items-center justify-between">
      <label className="text-sm font-medium text-gray-700 dark:text-slate-300">Categoria</label>
      <button type="button" onClick={() => setCategoriaRapidaAberta(true)}
        className="text-xs text-primary-600 hover:underline dark:text-violet-400 inline-flex items-center gap-1">
        <Plus size={12} />Nova categoria
      </button>
    </div>
    <Select name="categoria" options={categoriaOptions} value={form.categoria} onChange={handleChange} />
  </div>
  <p className="text-xs text-gray-400 dark:text-slate-500 -mt-2">Categoria em que este lançamento entra no relatório de DRE/Gastos por Categoria.</p>
  ```
  (texto de ajuda = RF-13, SHOULD — incluir mesmo assim, é 1 linha e
  mesmo padrão já usado 2x no arquivo).
- `categoriaOptions` é **estado próprio de `ReceitasTab`** (não
  compartilhado com `AbaListaPlanos`, que vive em outro arquivo/página),
  populado via `useEffect` idêntico ao de `AbaListaPlanos`:
  `GET /financeiro/categorias/?tipo=ENTRADA&page_size=200`, mapeado pra
  `[{value:'',label:'Selecione...'}, ...]`.
- Campo **opcional** — nunca `required`, nunca bloqueia submit vazio
  (RN-07). `EMPTY_RECEITA` já tem `categoria: ''`; `openEdit` já mapeia
  `item.categoria` — nenhuma mudança de estado necessária, só o `<Select>`
  visual que faltava.

**Layout — `DespesasTab` (modal "Nova/Editar Despesa"):**
- Mesma posição relativa: entre o grid Tipo/Conta e o `Input
  label="Descrição"` (antes do `Input label="Fornecedor"`, que continua
  logo depois da Descrição, sem mudar de lugar).
- Mesmo bloco, com `tipo="SAIDA"` no atalho e fetch
  `?tipo=SAIDA&page_size=200`. Texto de ajuda: mesmo texto do Receita
  (RF-13).

**Ícones Lucide:** nenhum novo nesta seção além do `Plus` já descrito na
seção 2 (botão "Nova categoria" inline).

---

### 4. Texto de ajuda no campo Categoria do form de Plano (RF-12, SHOULD)

- `AbaListaPlanos` já tem `<Select label="Categoria" ... />` (linha 776)
  — só falta o texto de ajuda abaixo, mesmo padrão `-mt-2` dos outros
  textos de ajuda do projeto:
  ```
  <p className="text-xs text-gray-400 dark:text-slate-500 -mt-2">Categoria financeira em que as mensalidades deste plano entram nos relatórios.</p>
  ```
- O atalho "+ Nova categoria" ao lado do label (seção 2) também se
  aplica aqui — envolve o `Select` existente na mesma estrutura manual de
  label+botão descrita acima, em vez do `<Select label="Categoria" .../>`
  direto que existe hoje.

---

## Ícones Lucide — consolidado desta manutenção

| Ícone | Tamanho | Uso |
|---|---|---|
| `Plus` | 16px (botão principal) / 12px (link inline) | "+ Nova Categoria" (tela) e "+ Nova categoria" (atalho nos 3 forms) |
| `Pencil` | 16px | Editar linha de categoria (pai ou subcategoria) |
| `Trash2` | 16px | Excluir (soft delete) linha de categoria |
| `CornerDownRight` | 14px | Marca visual de subcategoria (indentação) |
| `Tag` | 32px | Ícone do estado vazio geral da tela Categorias |

Todos já fazem parte da dependência `lucide-react` já instalada — nenhuma
lib nova.

## Componentes reutilizados (resumo)

| Componente | Onde é usado nesta manutenção | Alterado? |
|---|---|---|
| `Card.jsx` | Barra de filtros e lista de categorias | Não |
| `Modal.jsx` | CRUD de Categoria + atalho "+ Nova categoria" (empilhado) | Não |
| `Button.jsx` | Todos os botões (Nova Categoria, Salvar, Cancelar, Criar) | Não |
| `Select.jsx` | Tipo, Categoria-pai, Categoria (Receita/Despesa/Plano) | Não |
| `Input.jsx` | Nome (Categoria), Nome (atalho rápido), Busca | Não |
| `AuditFooter.jsx` | Modal de edição de Categoria | Não |
| `CriarCategoriaRapidaModal.jsx` (**novo**) | Atalho em Plano/Receita/Despesa | — |

## Decisões do Brush não explícitas na Especificacao_Hotfix.md (registradas para o Loom não precisar adivinhar)

1. Cabeçalho da aba Categorias segue o padrão `<h2>` + `Button` das abas
   vizinhas (`ReceitasTab`/`DespesasTab`/`ContasTab`), não o padrão sem
   título de `AbaListaPlanos` (que só faz sentido na página Assinaturas,
   onde já existe título em outro nível).
2. `CriarCategoriaRapidaModal` vive em `components/ui/` por ser
   compartilhado entre `Assinaturas.jsx` e `Financeiro.jsx` — único
   componente "de domínio" nessa pasta, justificado pela reutilização em
   3 pontos.
3. Campo Categoria em Receita/Despesa entra como linha própria (não
   como 3ª coluna do grid Tipo/Conta), para não apertar os dois campos
   já existentes.
4. Badge de tipo (Entrada/Saída) na lista de Categorias é redundante
   quando o filtro já está restrito a um tipo — decisão de exibir ou
   ocultar nesse caso é não-bloqueante, fica a critério do Loom.
5. Sem toggle "Ativa/Inativa" no formulário de Categoria — desativação
   só via exclusão (soft delete) com confirmação, sem reativação pela
   tela (mesma decisão já registrada pelo Analista na seção 8 da
   Especificacao_Hotfix.md).

---

## Passagem de bastão

✅ Especificação UI concluída — UidCore (Manutenção #88)
Telas analisadas: 3 (Financeiro → Categorias; atalho "+ Nova categoria"
empilhado; campos de Categoria em Receita/Despesa) + 1 ajuste pontual
(texto de ajuda em Plano).
Componentes reutilizados: 6 existentes (`Card`, `Modal`, `Button`,
`Select`, `Input`, `AuditFooter`).
Novos padrões: 1 componente compartilhado (`CriarCategoriaRapidaModal`)
+ 1 padrão de lista hierárquica (pai→subcategoria indentada, dentro do
mesmo `divide-y` do `Card`, nunca implementado antes no projeto).

📁 Arquivo: `Especificacao_UI_Hotfix.md` (neste worktree, `/var/www/uidcore/`)

➡️ Loom lê `Especificacao_Hotfix.md` (Analista) + este arquivo antes de
implementar o frontend. Nenhum código foi escrito por este agente.
