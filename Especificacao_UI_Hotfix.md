# Especificação UI Hotfix — UidCore (Manutenção #90)

## Modo

**MODO HOTFIX.** Um campo novo (`cliente`) num formulário já existente
(`ReceitasTab`, `Financeiro.jsx`) + preenchimento automático condicional
(3 ramos: assinatura ativa → venda em aberto → nada) baseado num novo
endpoint de sugestão. Sem app novo, sem tela nova, sem rota nova. Nenhuma
mudança de identidade visual, paleta ou tipografia — tudo reaproveita o
design system já em produção.

Lido antes de escrever esta especificação: `Especificacao_Hotfix.md`
(Manutenção #90, seções 1-9 completas), `frontend/src/pages/Financeiro.jsx`
(`ReceitasTab` completo, linhas 511-747; `BuscaFornecedorRapida` e
`NovoFornecedorModal`, linhas 759-933 — padrão de referência direto da
Manutenção #89, já no mesmo arquivo e no mesmo `Modal`),
`frontend/src/pages/Assinaturas.jsx` (`ClienteAutocomplete`, linhas 81-167
— citado pelo Analista como componente a clonar), `components/ui/{Input,
Button, Select, Modal}.jsx`.

## Design System do Projeto (referência — não alterado)

- **Cores primárias:** `primary-600` (light) / `violet-600` (dark) —
  botão de ação, foco de input/select. Hover: `primary-700`/`violet-700`.
- **Cores de fundo:** `white`/`gray-50` (light), `navy-800`/`navy-900`
  (dark) — `navy-500`/`navy-600` para bordas de input/select,
  `navy-700` para hover de linha/dropdown.
- **Texto:** `text-gray-900`/`text-gray-700`/`text-gray-400` (light),
  `text-slate-100`/`text-slate-300`/`text-slate-500` (dark).
- **Feedback:** amarelo (`yellow-100`/`yellow-800` light,
  `amber-900/30`/`amber-300` dark — mesma classe já usada em
  `STATUS_BADGES.PAUSADA` de `Assinaturas.jsx`) para o aviso "já cobrado
  este mês". Verde (`green-700`/`emerald-400`) já é a cor de valor de
  Receita nesta mesma tela — não reutilizar para nenhum estado novo desta
  manutenção, para não confundir com "valor recebido".
- **Fonte:** Plus Jakarta Sans (display) + DM Sans (body) — já
  carregadas globalmente, não tocar.
- **BorderRadius:** `rounded-lg` (inputs, selects, botões, cards de
  escolha), `rounded-2xl` (`Modal.jsx`, não tocar).
- **Dark mode:** classe `dark` no `<html>`, toggle já existente — não
  tocar.
- **Ícones:** `lucide-react` (já é dependência do projeto). Sem emoji
  nesta tela — emoji é padrão intencional só da Sidebar.
- **Componentes a reutilizar (nenhum componente genérico novo):**
  `Card`, `Modal`, `Button`, `Select`, `Input`, `AuditFooter`. Um
  componente de domínio novo (`ClienteAutocomplete`, clone local em
  `Financeiro.jsx` — ver seção 2 sobre por que **não** é um clone 1:1 do
  de `Assinaturas.jsx`). Nenhum modal novo nesta manutenção (diferente da
  #89, que criou `NovoFornecedorModal` — aqui não há "+ Novo cliente").

---

## Especificação Visual por Tela

Única tela afetada: **Financeiro → Contas a Receber** (`ReceitasTab` em
`Financeiro.jsx`) — modal "Nova Receita" / "Editar Receita". Não cria aba
nova, não cria rota nova, não altera a listagem/filtros (diferente da
#89, que também tocou a barra de filtros — aqui RF-06 não pede filtro por
Cliente na listagem).

### 1. Modal "Nova Receita" / "Editar Receita" — novo campo no topo

**Ordem atual (hoje, linhas 699-727):**
```
[Tipo | Conta] → Categoria → Descrição →
[Valor Bruto | Desconto | Vencimento] → Mês de referência → Observações
```

**Ordem nova (RF-01):**
```
1. Cliente (autocomplete)                        ← NOVO, 1º campo
2. [Tipo | Conta]                                 ← mesma posição de hoje
3. (sugestão de assinatura/venda, se houver)      ← NOVO, condicional, logo
                                                     após o campo Cliente,
                                                     ANTES do grid Tipo/Conta
4. Categoria
5. Descrição
6. [Valor Bruto | Desconto | Vencimento]
7. Mês de referência (competência)                ← já existe, sem mudança
8. Observações
9. AuditFooter (se edição)
```

Correção de ordem em relação ao RF-01 (seção 6.1 do Analista, item 1 diz
"logo no topo, antes do grid Tipo/Conta" — mas a lista de escolha de
assinatura/venda do item 2 só pode aparecer **depois** que o cliente foi
selecionado): o bloco de sugestão (passo 3 acima) fica **entre** o campo
Cliente e o grid Tipo/Conta, nunca deslocando os campos de baixo para
cima/baixo de forma inesperada — é inserção, não reposicionamento do que
já existe.

Container do form continua `<form className="space-y-4">` — nenhum
espaçamento novo, só inserção de 2 blocos (Cliente + bloco de sugestão
condicional).

**Mobile (375px):** os grids existentes (`grid-cols-1 sm:grid-cols-2` e
`grid-cols-1 sm:grid-cols-3`) já colapsam para coluna única — sem
alteração. Cliente e o bloco de sugestão ficam fora de qualquer grid
(`full-width` nativo), herdando o mesmo comportamento.

---

### 2. Campo Cliente — `ClienteAutocomplete` (clone local em `Financeiro.jsx`)

**Atenção — não é um clone 1:1 do `ClienteAutocomplete` de
`Assinaturas.jsx`.** O comentário original em `Assinaturas.jsx` (linhas
77-80) diz explicitamente que o dropdown ali **não** usa a técnica
`position: fixed` "porque não há overflow-y-auto agressivo o suficiente
pra justificar o truque". Isso não vale para este modal: o modal de
Receita (`Modal.jsx`, `max-h-[90vh] overflow-y-auto`) já tem **9 campos**
e cresce mais com o bloco de sugestão condicional — exatamente o cenário
que já forçou a técnica `position: fixed` + `getBoundingClientRect()` em
`BuscaFornecedorRapida` (mesmo arquivo, Manutenção #89, linhas 771-787).
**Clonar a estrutura dos 3 estados (busca/selecionado/disabled) do
`ClienteAutocomplete` de `Assinaturas.jsx`, mas clonar a técnica de
posicionamento de dropdown do `BuscaFornecedorRapida`** — são dois
pontos de referência diferentes, cada um pelo motivo certo. Não escolher
só um dos dois.

**Os 3 estados do componente (`editingId` vindo de `ReceitasTab`,
`clienteSelecionado` e `onSelecionar`/`onLimpar` como props):**

**Estado 1 — busca (criação, nada selecionado ainda):**
```
Cliente
┌───────────────────────────────────────┐
│ 🔍  Buscar cliente por nome...         │
└───────────────────────────────────────┘
  (dropdown abre abaixo, position:fixed — mesma técnica de
   BuscaFornecedorRapida: top = rect.bottom+4, left = rect.left,
   width = rect.width, zIndex 9999, recalculado em scroll/resize)
```
- Ícone `Search` (16px, já importado), mesma classe de borda/foco de
  `BuscaFornecedorRapida` (inclui variante dark).
- Dropdown: mesma classe (`bg-white rounded-lg shadow-lg border
  max-h-64 overflow-y-auto dark:bg-navy-800 dark:border-navy-600`). Cada
  linha mostra só `nome_razao_social` (`text-sm font-medium`) — **sem**
  segunda linha de documento (diferente do dropdown de Fornecedor): o
  endpoint `/clientes/?search=` já é o mesmo usado em
  `ClienteAutocomplete` de `Assinaturas.jsx`, que também só mostra o
  nome — manter paridade visual entre os dois usos do mesmo tipo de
  busca.
- Estado "buscando": linha única `text-sm text-gray-400 dark:text-slate-500
  text-center` com texto `"Buscando..."` (idêntico aos dois componentes
  de referência).
- Estado "nenhum resultado": **não** precisa de mensagem dedicada —
  dropdown simplesmente não aparece quando `resultados.length === 0 &&
  !buscando` (mesmo comportamento de `ClienteAutocomplete` de
  `Assinaturas.jsx` — diferente de `BuscaFornecedorRapida`, que mostra
  "Nenhum fornecedor encontrado."; manter o comportamento do componente
  de origem citado pelo Analista para este campo específico).

**Estado 2 — selecionado, ainda em criação (`!editingId`):**
```
Cliente
┌─────────────────────────────────────────┬──────────┐
│ 👤  Maria Oliveira                        │ Trocar   │
└─────────────────────────────────────────┴──────────┘
```
- Mesmo molde visual do chip de Fornecedor selecionado
  (`BuscaFornecedorRapida`, linhas 829-841): `flex items-center
  justify-between gap-2 rounded-lg border border-gray-300 bg-white px-3
  py-2 dark:border-navy-500 dark:bg-navy-800`, ícone à esquerda do nome.
- Ícone: `User` (16px, novo import — paralelo ao `Building2` usado no
  chip de Fornecedor).
- Botão `"Trocar"` (`variant="secondary"`, `size="sm"`) — clicar limpa
  `cliente`, fecha o bloco de sugestão (seção 3) e **limpa também
  `assinatura` do form** (RN-02) — reabre o Estado 1.

**Estado 3 — modo edição (`editingId` setado) — campo sempre somente
leitura, independente de ter cliente ou não (RF-01/RN-01):**
```
Cliente
┌───────────────────────────────────────┐
│ Maria Oliveira                         │   (input disabled)
└───────────────────────────────────────┘
```
- Reaproveita exatamente o branch `disabled` já existente em
  `ClienteAutocomplete` de `Assinaturas.jsx` (linhas 114-118):
  `<Input label="Cliente" value={clienteSelecionado?.nome || ''}
  disabled />` — **sem** ícone, **sem** botão, **sem** chip customizado.
  É o único dos 3 estados em que o componente novo não precisa de nada
  visual além do que o `Input.jsx` já faz com `disabled` (fundo
  `bg-gray-50`/`dark:bg-navy-900`, cursor `not-allowed`).
- Nenhum clique neste estado dispara `GET sugestao-cliente` — reforça
  CA-11.
- Se a Receita em edição não tiver `cliente` (registro antigo, criado
  antes desta manutenção): mesmo Estado 3, só com `value=''` — campo
  disabled vazio, nunca volta a ficar buscável em modo edição.

**Busca:** debounce 300ms em `/clientes/?search=<nome>&page_size=10`
(idêntico ao `ClienteAutocomplete` de `Assinaturas.jsx` — **sem**
`AbortController` aqui, só `clearTimeout` do debounce, porque o
componente de origem citado pelo Analista não usa abort; manter paridade
com ele, diferente de `BuscaFornecedorRapida` que usa abort). Clique fora
(`mousedown` fora do `wrapRef`) fecha o dropdown — mesmo padrão dos dois
componentes de referência.

---

### 3. Bloco de sugestão condicional (RF-03/04/05/08) — logo abaixo do campo Cliente

Renderizado **só durante a criação** (`!editingId`) e **só depois** de um
cliente ser selecionado. Três sub-estados, mutuamente exclusivos, na
ordem definida por RN-11 (assinatura sempre tem prioridade sobre venda):

**3.0 — Carregando (transitório, enquanto `GET sugestao-cliente` resolve):**
```
Verificando assinaturas e vendas deste cliente...
```
`text-xs text-gray-400 dark:text-slate-500` — sem spinner, mesmo
princípio já usado na #89 para a sugestão de categoria por fornecedor
(dado complementar, não ação bloqueante que o usuário espera). Dura
tipicamente menos de 1s; não há botão "Cancelar" nem skeleton.

**3.1 — Exatamente 1 assinatura ativa (RF-03, auto-aplicado sem clique):**
Depois do preenchimento automático já ter sido aplicado, mostrar uma
tira de confirmação (não uma lista — não há nada para escolher):
```
🔁  Assinatura: Plano Mensal — R$ 199,90/mês          [Remover vínculo]
```
- Ícone `Repeat` (16px, novo import).
- Texto `text-sm text-gray-800 dark:text-slate-200`, valor formatado com
  o `BRL()` já existente na tela.
- Botão `"Remover vínculo"` (`variant="secondary"`, `size="sm"`) — limpa
  `assinatura` do form e esconde a tira, **sem** limpar os campos já
  preenchidos (Tipo/Descrição/Valor/Categoria/Mês continuam como
  estavam — RN-03, são só sugestão, o usuário decide manter o texto e só
  descartar o vínculo formal). Rótulo diferente de "Trocar" de propósito:
  com 1 única assinatura não há para onde "trocar", só para desvincular.

**3.2 — 2+ assinaturas ativas (RF-03, lista de escolha):**
```
Este cliente tem mais de uma assinatura ativa — escolha qual cobrar:

┌───────────────────────────────────────────────────┐
│ 🔁  Plano Mensal                        R$ 199,90   │
├───────────────────────────────────────────────────┤
│ 🔁  Plano Anual                       R$ 1.499,00   │
│                                ⚠ já cobrado este mês│
└───────────────────────────────────────────────────┘
```
- Texto de instrução: `text-sm text-gray-700 dark:text-slate-300`.
- Lista: mesmo container visual do dropdown de busca (`bg-white
  rounded-lg border divide-y dark:bg-navy-800 dark:border-navy-600`),
  porém **estático** (não é `position:fixed`, não fecha ao clicar fora —
  faz parte do fluxo do form, não é um dropdown transitório).
- Cada linha é um `<button type="button">` full-width, mesmo padrão de
  hover dos outros dropdowns (`hover:bg-gray-50 dark:hover:bg-navy-700`):
  ícone `Repeat` (16px) + `plano_nome` (`text-sm font-medium`) + valor à
  direita (`text-sm font-semibold`, BRL de `valor`).
  - Quando `ja_tem_receita_mes_atual === true`: segunda linha abaixo do
    nome, alinhada à direita, badge `⚠ já cobrado este mês` —
    `inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs
    font-semibold bg-yellow-100 text-yellow-800 dark:bg-amber-900/30
    dark:text-amber-300` (mesma classe de `STATUS_BADGES.PAUSADA` em
    `Assinaturas.jsx`), ícone `AlertTriangle` (12px). **Não bloqueia o
    clique** — é só aviso (RF-07); a validação real é no backend (RN-08,
    `400` só no submit se o usuário insistir).
- Ao clicar numa linha: aplica o preenchimento (RF-03), fecha a lista e
  passa a mostrar a tira de confirmação do item **3.1** (mesmo visual,
  agora com botão `"Trocar"` em vez de `"Remover vínculo"` — aqui faz
  sentido trocar porque havia mais de uma opção). Clicar em "Trocar"
  reabre esta mesma lista (3.2) — **sem** refazer a chamada à API
  (`assinaturas_ativas` já está em memória desde a consulta inicial,
  RN-02 só exige refetch ao trocar o **cliente**, não a assinatura
  dentro da mesma sugestão).

**3.3 — 0 assinaturas ativas e 1+ vendas em aberto (RF-04, lista de
escolha — sempre escolha explícita, mesmo com só 1 item, por RF-04):**
```
Este cliente tem vendas em aberto — vincular a uma delas?

┌───────────────────────────────────────────────────┐
│ 📋  PED-2026-0034 - Pedido              R$ 450,00   │
├───────────────────────────────────────────────────┤
│ 📋  ORC-2026-0012 - Orçamento           R$ 1.200,00 │
└───────────────────────────────────────────────────┘
```
- Mesmo container/hover dos itens de 3.2. Ícone `ClipboardList` (16px,
  novo import) — genérico para os dois tipos (`ORCAMENTO`/`PEDIDO`); o
  texto de cada linha já distingue o tipo via `descricao_sugerida`
  (formato `"<numero> - Orçamento"`/`"<numero> - Pedido"`, já vem pronto
  do backend — RF-06) e `numero` com o prefixo (`PED-`/`ORC-`) — não é
  necessário ícone diferente por tipo.
- Sem badge de aviso aqui (RF-07/`ja_tem_receita_mes_atual` só existe
  para assinatura).
- Ao clicar: aplica RF-04 (Tipo/Descrição/Valor Bruto), **não** seta
  `assinatura`, fecha a lista e mostra tira de confirmação:
  ```
  📋  Vinculado a: PED-2026-0034 - Pedido — R$ 450,00    [Trocar]
  ```
  mesmo ícone `ClipboardList`, botão `"Trocar"` reabre a lista 3.3 (sem
  refetch, mesma lógica de 3.2).

**3.4 — 0 assinaturas e 0 vendas (RF-05):** nenhum elemento visual
adicional é renderizado — o bloco de sugestão simplesmente não aparece
depois do estado "Carregando" (3.0) desaparecer. Só o campo Cliente fica
preenchido.

**Trocar o cliente (RN-02), em qualquer sub-estado 3.0 a 3.3:** volta
direto para o Estado 1 do campo Cliente (busca) e, ao selecionar um novo
cliente, reinicia em 3.0 — todo o bloco de sugestão anterior (lista,
tira de confirmação, `assinatura` oculto) é descartado e refeito do
zero para o novo cliente.

---

### 4. Campos preenchidos automaticamente — sem mudança visual no próprio campo

Tipo (`Select`), Descrição (`Input`), Valor Bruto (`Input`), Categoria
(`Select`), Mês de referência (`Input type="month"`) **não ganham nenhum
estilo novo** quando preenchidos automaticamente (sem borda destacada,
sem ícone "✓ sugerido" dentro do campo) — diferente da sugestão de
categoria por fornecedor na #89, que usa uma etiqueta textual
(`"✓ Sugerido com base no histórico deste fornecedor"`) porque ali a
origem do valor não é óbvia visualmente. Aqui a própria tira de
confirmação da seção 3 (`🔁 Assinatura: ...` / `📋 Vinculado a: ...`) já
comunica a origem do preenchimento — adicionar uma 2ª etiqueta dentro de
cada campo seria redundante. Os campos continuam 100% editáveis (RN-03);
o usuário percebe isso pelo cursor/foco normal, sem necessidade de
indicação visual extra de "este campo é editável".

---

## Ícones Lucide — consolidado desta manutenção

| Ícone | Tamanho | Uso | Já importado? |
|---|---|---|---|
| `Search` | 16px | Campo de busca de Cliente (Estado 1) | Sim (linha 2) |
| `User` | 16px | Chip de cliente selecionado em criação (Estado 2) | **Novo** |
| `Repeat` | 16px | Linha de assinatura na lista (3.2) + tira de confirmação (3.1) | **Novo** |
| `ClipboardList` | 16px | Linha de venda na lista (3.3) + tira de confirmação | **Novo** |
| `AlertTriangle` | 12px | Badge "já cobrado este mês" (3.2) | **Novo** |

Import a acrescentar em `Financeiro.jsx`: `User`, `Repeat`,
`ClipboardList`, `AlertTriangle`, junto da lista já existente
(`ChevronDown, ChevronUp, Edit, Plus, Pencil, Trash2, CornerDownRight,
Tag, Search, Building2, Info`).

## Badges

| Badge | Classe | Ícone |
|---|---|---|
| "⚠ já cobrado este mês" | `bg-yellow-100 text-yellow-800 dark:bg-amber-900/30 dark:text-amber-300` (= `STATUS_BADGES.PAUSADA` de `Assinaturas.jsx`) | `AlertTriangle` 12px |

Nenhum badge de `Badge status={...}` (componente local da própria
`ReceitasTab`) é alterado — ele continua só para `status` da Receita
(PENDENTE/RECEBIDO/ATRASADO/CANCELADO), sem relação com esta manutenção.

## Componentes reutilizados (resumo)

| Componente/padrão | Onde é usado nesta manutenção | Alterado? |
|---|---|---|
| `Modal.jsx` | Modal Nova/Editar Receita (sem mudança estrutural) | Não |
| `Input.jsx` | Estado 3 do Cliente (disabled), demais campos do form (sem mudança) | Não |
| `Button.jsx` | "Trocar" (chip de cliente, confirmação de assinatura/venda), "Remover vínculo" | Não |
| `ClienteAutocomplete` (`Assinaturas.jsx`) | **Padrão de referência para os 3 estados** — clone local em `Financeiro.jsx`, adaptado (ver seção 2) | — |
| `BuscaFornecedorRapida` (`Financeiro.jsx`, Manutenção #89) | **Padrão de referência para o posicionamento do dropdown** (`position:fixed` + `getBoundingClientRect()`) | Não (só referência) |
| `STATUS_BADGES.PAUSADA` (`Assinaturas.jsx`) | Classe reaproveitada para o badge "já cobrado este mês" | Não |

## Mobile-first (375px)

- Campo de busca de Cliente, chip de cliente, listas de escolha
  (assinatura/venda) e tira de confirmação: todos full-width, fora de
  qualquer grid — herdam o comportamento de coluna única já existente no
  resto do form.
- Dropdown de busca de Cliente usa `position: fixed` (mesma técnica de
  `BuscaFornecedorRapida`) — essencial no mobile porque o `Modal` já usa
  `overflow-y-auto`; sem isso o dropdown ficaria cortado/rolando junto
  com o form (mesmo bug que a técnica original corrigiu no PDV/Vendas e,
  nesta mesma tela, no campo Fornecedor da #89).
- Listas de escolha (3.2/3.3) **não** usam `position:fixed` — fazem
  parte do fluxo normal do form (empurram os campos de baixo), não são
  um overlay transitório. Em 375px cada linha continua full-width,
  badge "já cobrado este mês" quebra para a linha de baixo naturalmente
  (`flex-wrap` ou bloco próprio, sem truncar o nome do plano).
- Nunca `overflow-hidden` no container do form/modal (regra global do
  projeto) — já garantido, nenhuma mudança necessária aqui.

## Decisões do Brush não explícitas na Especificação_Hotfix.md (registradas para o Loom não precisar adivinhar)

1. **Dois componentes de referência, não um só** (seção 2): os 3 estados
   do `ClienteAutocomplete` seguem `Assinaturas.jsx`, mas o
   posicionamento do dropdown segue `BuscaFornecedorRapida`
   (`Financeiro.jsx`). Clonar só `Assinaturas.jsx` literalmente
   reproduziria, dentro deste modal específico, o mesmo bug de corte de
   dropdown que a #89 já teve que corrigir para Fornecedor — por isso a
   divergência explícita é necessária e intencional, não uma
   inconsistência a "resolver" escolhendo um dos dois padrões.
2. **Confirmação por tira, não etiqueta dentro do campo** (seção 4): ao
   contrário da sugestão de categoria/subcategoria por fornecedor da
   #89 (`"✓ Sugerido com base no histórico"` dentro do bloco de
   Categoria), aqui a origem do preenchimento (assinatura X ou venda Y)
   já é autoexplicativa pela própria tira de confirmação — evita
   duplicar a mesma informação em dois lugares da tela.
3. **Rótulo do botão varia por contexto** (seção 3.1 vs 3.2/3.3):
   "Remover vínculo" quando só havia 1 opção (não há "outra coisa" para
   trocar, só desfazer), "Trocar" quando havia uma lista real de opções
   — microcópia pensada para não confundir o usuário sobre o que vai
   acontecer ao clicar.
4. **Dropdown de busca de Cliente sem mensagem de "nenhum resultado"**
   (seção 2, Estado 1): segue o comportamento do componente de origem
   citado pelo Analista (`Assinaturas.jsx`), que simplesmente não
   renderiza nada quando a busca não encontra ninguém — diferente de
   `BuscaFornecedorRapida`, que mostra uma mensagem explícita. Mantido
   assim de propósito (paridade com o padrão já em uso para busca de
   Cliente especificamente, não para busca de Fornecedor).
5. **Nenhum ícone/borda especial nos 5 campos preenchidos
   automaticamente** (Tipo, Descrição, Valor Bruto, Categoria, Mês de
   referência) — decisão deliberada para não haver 2 pontos de
   indicação visual competindo com a tira de confirmação (ver item 2).
6. **Listas de escolha (3.2/3.3) são estáticas, não dropdown** — fazem
   parte do fluxo vertical do form (empurram os campos seguintes para
   baixo), diferente do dropdown de busca que flutua por cima. Isso
   evita usar `position:fixed`/`zIndex` onde não é necessário e deixa a
   altura do modal crescer naturalmente (o `Modal.jsx` já tem
   `overflow-y-auto` para isso).

---

## Passagem de bastão

```
✅ Especificação UI concluída — UidCore (Manutenção #90)
   Telas analisadas: 1 (Financeiro → Contas a Receber — modal
     Nova/Editar Receita)
   Componentes reutilizados: 4 existentes (Modal, Input, Button, classe
     de badge de Assinaturas.jsx) + 2 padrões de referência direta
     (ClienteAutocomplete de Assinaturas.jsx para os 3 estados,
     BuscaFornecedorRapida para o posicionamento do dropdown)
   Novos padrões: 1 — ClienteAutocomplete clonado localmente em
     Financeiro.jsx (combinação deliberada dos dois padrões acima,
     nenhum token visual novo) + bloco de sugestão condicional (3
     sub-estados: confirmação única, lista de assinaturas, lista de
     vendas)
   Modo: Padrão Uid (sistema interno já em produção, dark mode
     navy/violet — sem alteração de identidade)

📁 Arquivo: Especificacao_UI_Hotfix.md (em /var/www/uidcore/)

➡️ Loom lê Especificacao_Hotfix.md (Analista) + este arquivo antes de
   implementar o frontend. Nenhum código foi escrito por este agente.
```
