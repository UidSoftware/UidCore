# Especificação UI Hotfix — UidCore (Manutenção #62)

**Origem:** `Especificacao_Hotfix.md` (Analista) — núcleo de auditoria [NUCLEO 1/5]: `BaseModel`
ganha `created_by`/`updated_by`/`deleted_by`/`deleted_at`; frontend ganha um rodapé discreto de
autoria (`AuditFooter.jsx`) nos modais de edição de registro.

**Nota:** este arquivo substitui a versão anterior (Manutenção #60 — RBAC/Superadmin). Conteúdo
anterior preservado no histórico de commits do git, não neste documento (mesmo padrão já usado
entre ciclos anteriores — #58 Fase 1→2, #60→#62).

**Modo:** HOTFIX — sistema já tem identidade visual definida (dark mode navy/violet, Manutenção
#31). Esta especificação NÃO cria design system novo — só define a camada visual de um componente
novo (`AuditFooter`) e onde ele se encaixa nos modais já existentes, em cima do que o Analista já
especificou (RF-17 a RF-20 e RF-07/RF-19 da especificação de hotfix).

---

## Design System do Projeto (referência — já em produção, não recriar)

- **Dark mode — superfícies:** `navy-950` (fundo app) → `navy-900` (sidebar/header) → `navy-800`
  (cards/inputs/`Modal`) → `navy-700` (bordas/divisores/hover) → `navy-600`/`navy-500` (bordas mais
  claras, inputs)
- **Dark mode — ação/destaque:** `violet-*` (base `#8b5cf6`/`#7c3aed`) — substitui `primary` no dark
  mode
- **Texto meta/caption (padrão já estabelecido, confirmado em `ResourceCrud.jsx` e em todas as
  páginas com modal próprio):** `text-xs text-gray-400 dark:text-slate-500` — é exatamente o token
  usado hoje para "Carregando...", `emptyText`, help text de campo (`f.helpText`), legenda de
  despesa vinculada em `Compras.jsx` etc. **O `AuditFooter` usa este mesmo token — não inventa cor
  nova.**
- **Divisor (`border-t`) antes de bloco secundário dentro de modal/card:** `border-gray-100
  dark:border-navy-700` — mesmo token usado no `divider` de `ResourceCrud::renderField` e no total
  do Modal Detalhe de `Compras.jsx` (`border-t border-gray-200 dark:border-navy-700` — variante só
  um tom mais forte no light, `navy-700` repete igual no dark).
- **Fonte:** Plus Jakarta Sans (display) + DM Sans (body) — já configuradas, não mexer.
- **BorderRadius padrão:** `rounded-lg` (8px) em inputs/botões/cards — não se aplica ao
  `AuditFooter` (é texto plano, sem container próprio).
- **Ícones:** Lucide React — já em uso em quase todas as páginas.

---

## Componente novo: `AuditFooter.jsx`

### Especificação visual

O Analista já fechou a implementação (RF-17) — Brush confirma que os tokens usados batem 100% com
o padrão visual já em produção e não requer ajuste:

```jsx
<p className="mt-4 text-xs text-gray-400 dark:text-slate-500 border-t border-gray-100 dark:border-navy-700 pt-3">
  Criado por {item.created_by_nome || '—'} em {fmt(item.created_at)}
  {item.updated_at && item.updated_at !== item.created_at && (
    <> · Alterado por {item.updated_by_nome || '—'} em {fmt(item.updated_at)}</>
  )}
</p>
```

- **Posição dentro do modal:** sempre o último bloco antes da linha de botões (`Cancelar`/
  `Salvar`), nunca depois — rodapé de metadado vem antes da ação, não compete visualmente com o
  CTA principal.
- **Espaçamento:** `mt-4` separa do campo anterior do formulário; `pt-3` dá respiro entre a linha
  divisória e o texto; `border-t` substitui a necessidade de um `<hr>` — é o mesmo padrão já usado
  em `ResourceCrud` para separar seções dentro de um formulário longo.
- **Tipografia:** `text-xs` (12px) — mesmo tamanho de toda legenda/caption da aplicação. **Não
  usar `font-medium`/`font-semibold`** — o rodapé é intencionalmente de baixo contraste visual
  ("discreto", conforme o pedido original), para não competir com o conteúdo do formulário.
- **Separador "·":** usar exatamente o caractere `·` (middle dot, não hífen nem pipe) rodeado de
  espaço em cada lado — já é convenção do projeto em textos compostos (ver changelog deste próprio
  CLAUDE.md, "Criado por X em dd/mm/aaaa · Alterado por Y em ...").
- **Fallback de nome ausente:** `'—'` (em-dash) quando `created_by_nome`/`updated_by_nome` vier
  vazio (ex.: registro criado por comando de management sem usuário, RN-06 do backend, ou usuário
  deletado/com FK `SET_NULL`) — mesmo caractere de "vazio" já usado em toda a aplicação
  (`ResourceCrud::renderCell`, `InfoField` de `Compras.jsx`).
- **Condição "Alterado por" só aparece se houve edição real:** `updated_at !== created_at` evita
  mostrar "Alterado por {mesmo autor} em {mesmo instante}" logo depois da criação (o
  `auto_now`/`auto_now_add` do Django grava os dois timestamps idênticos no `POST` inicial) — sem
  isso o rodapé mentiria "foi alterado" em todo registro recém-criado. Confirmar este comportamento
  no CA de aceite do Sentinel.
- **Formato de data:** `toLocaleDateString('pt-BR')` → `dd/mm/aaaa`, sem hora. Consistente com o
  pedido original ("em dd/mm/aaaa") e com o padrão de exibição de data já usado em `col.date` do
  `ResourceCrud`. **Não usar `toLocaleString`** (adicionaria hora, fora do que foi pedido).
- **Ícone:** **nenhum.** Decisão deliberada — o pedido pede "rodapé discreto", e nenhum outro
  elemento de metadado/caption da aplicação (help text, empty state de lista, legenda de despesa
  vinculada) usa ícone. Adicionar um Lucide aqui (`History`, `Info`, `UserCheck` seriam candidatos)
  destacaria visualmente algo que o pedido quer discreto — contrariaria o objetivo. Não introduzir.
- **Quando não renderizar:** `item?.created_at` ausente → retorna `null` (já no código do
  Analista). Isso cobre tanto "modal de criação, sem registro ainda" quanto "item não encontrado no
  array local por algum motivo" — fail-safe sem quebrar o layout do modal.

### Largura e quebra de linha (mobile-first)

- O texto é um `<p>` simples, sem `whitespace-nowrap` — quebra naturalmente em telas estreitas
  (375px). Não precisa de tratamento especial: todos os modais (`Modal.jsx`) já têm `px-4` de
  margem lateral da viewport e `max-h-[90vh] overflow-y-auto` internos, então o rodapé de 1-2
  linhas em 375px não corta nem força scroll horizontal.
- Testar visualmente em 375px o caso mais longo (nome completo + "Alterado por" + nome completo) —
  cenário esperado: quebra em 2 linhas, sem `·` isolado no início de uma linha (comportamento padrão
  do navegador ao quebrar por espaço, não requer CSS extra).

---

## Especificação Visual por Tela/Integração

### 1. `ResourceCrud.jsx` (RF-18 — propagação automática)

**Layout:** nenhuma mudança estrutural. `<AuditFooter item={items.find(i => i.id === editingId)} />`
entra dentro do `<form>`, imediatamente **antes** do `<div className="flex justify-end gap-3
pt-2">` que contém `Cancelar`/`Salvar Alterações` — ou seja, depois do grid de campos
(`visibleFields.map(...)`), fora do `grid grid-cols-1 sm:grid-cols-2 gap-4` (o footer ocupa largura
total, não é um campo do formulário).

- Só renderiza quando `editingId` não é `null` (a prop já cuida disso via early-return no
  componente, mas o ponto de chamada deve só passar `item` quando `editingId` existir — passar
  `undefined` em modo criação é seguro, pois o componente trata `item?.created_at`).
- Propaga automaticamente para: `Usuarios.jsx`, `Administrativo.jsx` (`TipoDocumento`/`Documento`),
  `Pagamentos.jsx` (`MetodoPagamento`/`Cobranca`/`Parcela`), `Portal.jsx`
  (`AcessoPortalCliente`), `Agendamento.jsx` (`Agenda`/`Compromisso`), `Rh.jsx`
  (`Cargo`/`Colaborador`/`FolhaPagamento`/`RegistroFerias`) — **nenhuma dessas telas precisa de
  edição manual**, confirmando o ganho de usar o CRUD genérico citado pelo próprio Analista.

### 2. `Clientes.jsx` e `Fornecedores.jsx` (RF-19)

**Inserção exata:** imediatamente antes do `<div className="flex justify-end gap-3 pt-2">` que
envolve `Cancelar`/`Salvar Alteracoes` (confirmado nas duas telas, mesma estrutura de formulário).

```jsx
<AuditFooter item={clientes.find((c) => c.id === editingId)} />      {/* Clientes.jsx */}
<AuditFooter item={fornecedores.find((f) => f.id === editingId)} />  {/* Fornecedores.jsx */}
```

Sem mudança de layout do restante do modal — formulário de Cliente/Fornecedor já é longo (dados
cadastrais, acionistas), o rodapé fecha a lista de campos sem precisar de novo agrupamento visual.

### 3. `Produtos.jsx` — dois modais (RF-19)

**Modal de Produto:** `<AuditFooter item={produtos.find((p) => p.id === editingId)} />` antes do
`<div className="flex justify-end gap-3 pt-2">` final (depois do campo "Observacoes", mesma
posição-padrão das demais telas).

**Modal de Combo:** `<AuditFooter item={combos.find((c) => c.id === editingComboId)} />` antes do
bloco de botões `Cancelar`/`Cadastrar Combo` (variável de estado é `editingComboId`, não
`editingId` — nome diferente nesta tela, atenção do Loom ao copiar o padrão das outras páginas).

Ambos os modais já têm seções internas com `border-t`/box cinza (`bg-gray-50 ... dark:bg-navy-900/50
dark:border-navy-700`, ex. seção "Itens do Combo") — o `AuditFooter` não reutiliza esse estilo de
"card", fica fora de qualquer box, direto no corpo do formulário, igual às demais telas.

### 4. `Vendas.jsx` — Orçamento e Pedido (RF-19)

Ambas as abas (`OrcamentosTab`/`PedidosTab`) usam a variável de estado genérica `items` — mesmo
padrão do `ResourceCrud`:

```jsx
<AuditFooter item={items.find((i) => i.id === editingId)} />
```

Inserir antes de `<div className="flex gap-3 justify-end pt-2">` (bloco com `Button
Cancelar`/`Button submit`) em cada um dos dois modais (`Editar Orcamento`/`Editar Pedido`). Formato
de modal aqui é `maxW="max-w-2xl"` com seção de itens dinâmica (linhas de produto) — o rodapé entra
depois dessa seção, não entre as linhas de item.

### 5. `Financeiro.jsx` — Receita, Despesa e Conta (RF-19, com correção de escopo)

**Confirmado nos 3 modais que de fato têm edição (`editingId`-based) nesta tela:** `Receita`,
`Despesa`, `Conta` — todos usam a variável genérica `items`:

```jsx
<AuditFooter item={items.find((i) => i.id === editingId)} />
```

Inserir antes de `<Button variant="secondary" onClick={closeModal}>Cancelar</Button>` em cada um
dos 3 formulários (`Nova/Editar Receita`, `Nova/Editar Despesa`, `Nova/Editar Conta`).

**Correção de escopo em relação à Especificação do Analista (seção RF-19):** o pedido lista
"Categoria/Aporte" como modais de `Financeiro.jsx` que também ganhariam `AuditFooter` — leitura do
código-fonte atual (`grep` em `Financeiro.jsx`) confirma que **não existe modal de edição próprio
para `Categoria` nem `Aporte`** nesta tela hoje: `categoria` é só um campo de texto/seleção dentro
dos formulários de Receita/Despesa (não um recurso com CRUD e modal próprio), e `Aporte` aparece
apenas como valor agregado somente-leitura no Balanço (`Capital / Aportes`). Não há modal existente
para anexar o rodapé — **sem ação do Loom aqui nesta manutenção** (ambos os models já ganham
`created_by`/`updated_by` no backend, RF-01/RF-14; se e quando ganharem tela de CRUD própria, o
`AuditFooter` entra então, seguindo o mesmo padrão documentado acima).

**Correção de arquivo — Padrão Seguro de Conciliação:** o modal de edição de
`PadraoSeguroConciliacao` (`editingId ? 'Editar Padrão' : 'Novo Padrão'`) **não vive em
`Financeiro.jsx`** — está em `Conciliacao.jsx` (confirmado por leitura de código, linha ~646).
Mesmo padrão de inserção se aplica lá: `<AuditFooter item={items.find((i) => i.id ===
editingId)} />` antes do bloco de botões `Cancelar`/`Salvar`/`Cadastrar`.

### 6. `Compras.jsx` — correção de escopo (RF-19)

O pedido do Analista lista "modal de Compra" para `Compras.jsx`. Leitura do código-fonte (RN-05, já
documentada no próprio componente) confirma que **não existe edição de Compra** — só dois modais:

- **"Nova Compra"** — formulário de criação pura, sem `editingId`/estado de edição. **Não recebe
  `AuditFooter`** — no momento em que esse modal está aberto o registro ainda não existe, não há
  `created_at` para mostrar (mesma regra geral do RF-20: nunca aparece em tela de criação).
- **"Compra #{id}" (Detalhe, somente leitura)** — este é o modal correto para o rodapé: sempre
  mostra um registro já persistido (`detalheItem`), nunca um formulário vazio. Inserir
  `<AuditFooter item={detalheItem} />` como último elemento do modal, depois do bloco "Despesa
  vinculada" (quando existir) — sem `border-t` duplicado, já que o próprio modal termina ali (o
  `AuditFooter` mantém seu próprio `border-t`/`pt-3`, que passa a ser o único divisor nessa posição).
  Não precisa de `.find(...)` — `detalheItem` já é o objeto completo vindo da API.

### 7. `Marketing.jsx` — Campanha e Lead (RF-19)

Ambas as abas usam a variável genérica `items`:

```jsx
<AuditFooter item={items.find((i) => i.id === editingId)} />
```

- **Campanha:** inserir antes de `<div className="flex justify-end gap-3 pt-2">` (bloco
  `Cancelar`/`Salvar`) do modal `Editar Campanha`/`Nova Campanha`.
- **Lead:** mesmo padrão, antes do bloco de botões do modal `Editar Lead`/`Novo Lead`.
- **Modal de ROI (`ROI — {nome}`)** — **não** recebe `AuditFooter`: é um painel agregado/analítico
  (CAC, ROI, receita fechada), não um formulário de edição de um registro único com
  `created_at`/`updated_at` próprios. Fora de escopo, confirmando o que o próprio RF-19 já implicava
  (lista só "modal de Campanha/Lead", não o modal de ROI).

---

## Componentes reutilizados (nenhum novo criado além do `AuditFooter`, já especificado pelo Analista)

- `Modal.jsx`, `Button.jsx`, `Input.jsx`, `Select.jsx`, `ResourceCrud.jsx` — sem alteração de
  componente, só o ponto de inserção do `AuditFooter` dentro do `<form>` já existente em cada tela.
- Nenhuma extensão de prop/API de componente existente é necessária nesta manutenção (diferente da
  Manutenção #60, que precisou estender `ResourceCrud::renderCell` com `badgeColorMap` — aqui o
  `AuditFooter` é 100% autocontido, só consome `item` por prop).

## Ícones Lucide novos

Nenhum. Decisão documentada acima (rodapé é só texto, sem ícone, por ser deliberadamente discreto).

## Dark mode (paleta navy/violet — sem token novo)

- `text-gray-400 dark:text-slate-500` e `border-gray-100 dark:border-navy-700` já são tokens em
  produção (confirmado em `ResourceCrud.jsx` e em `Compras.jsx`) — zero adição ao
  `tailwind.config.js`.
- Contraste: mesmo par já usado hoje para texto de apoio em toda a aplicação (help text de campo,
  empty state, legendas) — já validado nos ciclos anteriores (Manutenção #31), não é combinação
  nova a testar do zero. Ainda assim, Sentinel deve confirmar visualmente em pelo menos 1 tela no
  dark mode (contraste mínimo 4.5:1 é regra global da Uid) e 1 no light mode, já que o rodapé é
  elemento novo mesmo usando tokens antigos.

## Mobile-first

- Nenhum modal muda de `maxW`/padding por causa do `AuditFooter` — ele herda a largura do modal já
  responsiva (`Modal.jsx` já trata `px-4` na viewport + `overflow-y-auto` interno).
- Validar em 375px (iPhone SE, padrão de teste da Uid) o cenário com os dois nomes mais longos do
  banco de teste, nome + "Alterado por" + nome — deve quebrar em 2 linhas sem cortar texto nem gerar
  scroll horizontal.

---

## Passagem de bastão

```
✅ Especificação UI concluída — UidCore (Manutenção #62)
   Telas/modais analisados: 13 (ResourceCrud + 12 modais manuais em 8 páginas)
   Componente novo especificado: AuditFooter.jsx (visual já definido pelo Analista, RF-17 — confirmado consistente com tokens em produção)
   Componentes reutilizados: Modal, Button, Input, Select, ResourceCrud (sem extensão de API)
   Novos padrões: nenhum — 100% tokens já existentes (text-gray-400/dark:text-slate-500, border-gray-100/dark:border-navy-700)
   Correções de escopo vs. Especificacao_Hotfix.md: Padrão Seguro de Conciliação está em Conciliacao.jsx (não Financeiro.jsx); Compras.jsx não tem edição — footer vai no modal "Detalhe" (detalheItem), não em "Nova Compra"; Categoria/Aporte não têm modal de edição próprio em Financeiro.jsx hoje — sem ação nesta manutenção

📁 Arquivo: Especificacao_UI_Hotfix.md (no worktree)

➡️ Loom lê Especificacao_Hotfix.md + Especificacao_UI_Hotfix.md
   antes de implementar o frontend
```
