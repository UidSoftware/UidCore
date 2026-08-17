# Especificação UI Hotfix — UidCore (Manutenção #37)
**Elaborado por:** Brush (MODO HOTFIX)
**Data:** 2026-08-17
**Base:** Especificacao_Hotfix.md (Analista, Manutenção #37 — conversão de unidade em cadeia)

---

## Escopo desta especificação

Manutenção com peso real de UI, diferente da #36 (que era quase 100%
backend). Aqui há **3 telas com trabalho visual concreto**:

1. `Produtos.jsx` — seção "Conversões de Unidade": novo Select "Converte
   para" por linha (RF-01), preview de fator composto (RF-04), fix visual
   de feedback em editar/excluir conversão (RF-02/RF-03), preview de
   quantidade em unidade base na Entrada de Estoque (RF-08)
2. `pdv/FrenteDeCaixa.jsx` — seletor de unidade de venda antes de
   adicionar o produto ao carrinho (RF-05), só quando o produto tem
   conversões cadastradas
3. `pdv/components/CarrinhoItem.jsx` — troca de prop lida (RF-07,
   cosmético puro — zero mudança visual, só correção de dado exibido)

Nenhuma tela nova. Nenhum componente novo além do popover de escolha de
unidade no PDV (item 3 abaixo), que reaproveita o padrão visual já
existente na mesma tela (dropdown de busca).

---

## Design System do Projeto (referência — lido em tailwind.config.js + código real das 3 telas)

- **Paleta:** navy (60%) + violet (30%) + red (10%), dark mode via classe
  `dark:` (Tailwind `darkMode: 'class'`) — confirmado em Manutenção #31,
  tokens em `tailwind.config.js` (`navy-950…500`, `violet-50…900`)
- **Fundo de página:** `bg-gray-50 dark:bg-navy-950`
- **Cards:** componente `Card.jsx` — `bg-white rounded-xl border
  border-gray-200 shadow-sm dark:bg-navy-800 dark:border-navy-600
  dark:shadow-none` — 100% reutilizável, nenhuma prop nova
- **Fonte:** Plus Jakarta Sans (headings) + DM Sans (body/interface) — já
  configuradas, não mexer
- **BorderRadius padrão:** `rounded-lg` (8px) em inputs/selects/botões,
  `rounded-xl`/`rounded-2xl` (12-16px) em cards e modais (`Modal.jsx` usa
  `rounded-2xl`), `rounded-full` em badges e botões circulares (stepper
  de quantidade do carrinho)
- **Componentes reutilizáveis confirmados no código:** `Select.jsx`,
  `Input.jsx`, `Button.jsx`, `Card.jsx`, `Modal.jsx` — todos já com
  variante dark aplicada, usar tal como estão, sem criar variante nova
- **Cor de destaque (accent/primary):** `primary-600` claro /
  `dark:violet-400` a `violet-500` para ícones, links, foco de input
  (`focus:ring-primary-500 dark:focus:ring-violet-500`, padrão já em
  todo input/select do projeto)
- **Semântica de cor já em uso** (reaproveitar, nunca inventar nova
  combinação):
  - cinza (`text-gray-400/500` · `dark:text-slate-500/400`) → texto de
    apoio/preview secundário, placeholder, estado vazio
  - vermelho (`text-red-400 hover:text-red-600` ·
    `dark:text-red-400/70 dark:hover:text-red-400`) → ação destrutiva
    (ícone `Trash2` de remover conversão/item do carrinho); badge
    `bg-red-100 text-red-800` · `dark:bg-red-900/30 dark:text-red-300`
    já usado para "Sem estoque" no dropdown do PDV
  - azul/primary (`text-primary-600` · `dark:text-violet-400`) → ação de
    adicionar (`+ Adicionar Conversão`, `+ Registrar Entrada`), link,
    controle interativo
  - amarelo/âmbar (`text-amber-700` · `dark:text-amber-400`, sem
    background — usado inline em texto de aviso, não em badge) → aviso
    não-bloqueante de cadeia de conversão incompleta ou sem conversão
    cadastrada
- **Toast pattern** (já usado em `Produtos.jsx` e `FrenteDeCaixa.jsx`,
  reaproveitar tal qual — não criar novo componente de alerta):
  `fixed top-4 right-4 z-50 max-w-sm px-4 py-3 rounded-lg shadow-lg
  text-sm font-medium text-white whitespace-pre-line break-words` —
  `bg-red-600` erro, `bg-accent-600` sucesso

---

## Especificação Visual por Tela

### 1. `Produtos.jsx` — Seção "Conversões de Unidade" (modal Novo/Editar Produto)

**Contexto atual (confirmado lendo o código, linhas ~440-486):** cada
linha de conversão hoje é `Select "Unidade"` + `Input "Qtd por
{unidade_base}"` + botão lixeira, dentro de um card `bg-gray-50
dark:bg-navy-900/50 border border-gray-200 dark:border-navy-700
rounded-lg p-4`. Layout de linha: `flex items-end gap-2`, cada campo
`flex-1`. `EMPTY_CONVERSAO = { unidade: '', quantidade_por_base: '' }`.

**Mudança de layout — nova coluna "Converte para" (RF-01):**
- Linha de conversão passa de 2 campos (Unidade, Qtd) para 3 campos +
  lixeira: `Select "Unidade"` (existente) + `Select "Converte para"`
  (**novo**) + `Input "Quantidade"` (existente). `EMPTY_CONVERSAO` ganha
  `converte_para: ''`.
- Estrutura da linha: `flex-col gap-2 sm:flex-row sm:items-end` — em
  ≥640px os 3 campos ficam lado a lado (`flex-1` cada, proporção igual);
  em <640px empilham em coluna. 3 selects/input + lixeira lado a lado em
  375px não cabe com labels legíveis (regra mobile-first do Brush,
  testar em iPhone SE).
- `Select "Converte para"`: mesmo componente `Select.jsx`, `label=
  "Converte para"`, options dinâmicas = unidade base do produto (sempre
  primeira opção, ex. `"UN — Unidade (base)"`) + demais unidades já
  presentes nas outras linhas de `conversoes`, excluindo a própria
  unidade da linha atual (não faz sentido "CX converte para CX").
  Default = unidade base do produto — comportamento hoje implícito,
  preservado 100% (usuário que nunca mexe nesse campo tem exatamente o
  comportamento de antes da manutenção).
- Label do `Input "Quantidade"` muda de fixo `Qtd por {unidade_base}`
  para dinâmico `Qtd por {converte_para || unidade_base}` — reflete pra
  qual unidade aquela linha está convertendo (ex.: linha CX→PT mostra
  "Qtd por PT", não mais sempre "Qtd por UN").
- Ícone: manter `Trash2` (lucide-react, já importado) 16px, mesma cor
  atual. Nenhuma mudança de ícone nesta linha.

**Preview do fator composto (RF-04) — elemento novo:**
- Abaixo de cada linha de conversão (dentro do mesmo `space-y-2`, como
  linha de texto extra, não card separado): `text-xs text-gray-500
  dark:text-slate-400 pl-1 flex items-center gap-1`.
- Formato: `"1 {unidade} = {quantidade_por_base} {converte_para} =
  {fator_composto} {unidade_base}"` — ex.: `"1 CX = 6 PT = 300 UN"`. Só
  mostrar o segundo `=` (fator composto) quando `converte_para !==
  unidade_base` — conversão direta pra base não precisa de preview
  redundante (já é auto-evidente: "1 CX = 300 UN").
- Ícone à esquerda do texto: `ArrowRight` (lucide-react, **novo
  import**) 12px, `text-gray-400 dark:text-slate-500`, decorativo, sem
  clique.
- Calculado no cliente por função local `resolverFatorBase` (mesma
  lógica recursiva do backend, só para conferência — fonte de verdade
  continua sendo a validação do servidor no submit).
- **Cadeia não fecha na base ou tem ciclo (RN-01):** trocar o texto pelo
  padrão de aviso âmbar (`text-amber-700 dark:text-amber-400`, sem
  background, mesmo tamanho `text-xs`) com `"⚠ conversão não fecha na
  unidade base"`. Não bloqueia digitação — só alerta antes do usuário
  levar o 400 do backend no submit.

**Fix de feedback visual em editar/excluir (RF-02/RF-03):**
- Nenhuma mudança de layout — o bug era 100% de lógica (submit não
  persistia PATCH, remove não chamava DELETE de verdade). Especificação
  de UI aqui é garantir que o toast de erro padrão dispare quando o
  `DELETE` falhar por RN-06 (conversão é elo de outra) — usar a mesma
  classe já existente (`bg-red-600`, `whitespace-pre-line break-words`)
  e **não truncar** a mensagem do backend (ela lista quem depende da
  conversão — informação útil pro usuário entender o bloqueio).
- Excluir uma linha com sucesso: nenhuma confirmação visual adicional
  além da própria linha sumir da lista — **não** usar `window.confirm()`
  aqui (padrão reservado a `handleDelete` de produto inteiro, ação fora
  de contexto de formulário); dentro do modal já aberto, remover e poder
  simplesmente não salvar já é reversível o suficiente.

### 2. `Produtos.jsx` — Entrada de Estoque (RF-08, dentro do modal de edição)

**Contexto atual:** formulário `novaEntrada` (linhas ~508-548) já tem
`Input "Quantidade"` + `Select "Unidade"` lado a lado em `grid
grid-cols-2 gap-2`, dentro de card branco `bg-white dark:bg-navy-800
border border-gray-200 dark:border-navy-600 rounded-lg p-3`.

**Preview de quantidade em unidade base:**
- Nova linha de texto logo abaixo do `grid grid-cols-2` (antes do campo
  "Nota Fiscal"), só visível quando `novaEntrada.unidade !==
  form.unidade_base` **e** `novaEntrada.quantidade` preenchido.
- Estilo: `text-xs text-gray-500 dark:text-slate-400`, formato `"=
  {quantidade_convertida} {unidade_base}"` — ex. usuário digita "2" +
  unidade "CX" (produto com base UN e conversão CX→300UN) → mostra `"=
  600 UN"`.
- Reaproveita a mesma função `resolverFatorBase` do item 1 — não
  duplicar lógica de cálculo entre as duas seções do mesmo arquivo.
- Unidade sem conversão cadastrada (o backend passa a rejeitar com 400
  por RN-05): mesmo padrão de aviso âmbar do item 1 — `"⚠ sem conversão
  cadastrada para esta unidade"` — sinaliza **antes** do usuário tentar
  salvar e levar o erro só depois via toast.

### 3. `pdv/FrenteDeCaixa.jsx` — Seletor de unidade de venda (RF-05)

**Contexto atual:** `adicionarProduto(produto)` (linha ~154) é chamado
direto ao clicar num item do dropdown de busca (linha ~430,
`onClick={() => adicionarProduto(p)}`) e sempre envia `unidade:
produto.unidade_base || 'UN'` — sem passo intermediário. A tela já tem
padrão de modal leve pra ações secundárias (`ModalSangriaSuprimento`,
`ModalScannerCamera`), mas um modal cheio é peso demais pra uma decisão
de 1 campo — segue o princípio "menos é mais" do Brush.

**Especificação — popover inline, não modal:**
- Regra de entrada: se `produto.conversoes?.length > 0` (campo já vem
  nested da API — confirmado em `ProdutoSerializer.conversoes`), **não**
  chama `adicionarProduto(produto)` direto no clique do item — abre um
  popover pequeno ancorado no item clicado, em vez disso.
- Produto **sem** conversões cadastradas: mantém o clique direto atual,
  zero fricção nova — regra explícita de RF-05 (não pode piorar o fluxo
  do caso comum, que é a maioria dos produtos hoje).
- Layout do popover: `bg-white dark:bg-navy-800 border border-gray-200
  dark:border-navy-600 rounded-lg shadow-lg p-3`, largura ~220px.
  **Atenção de posicionamento:** o dropdown de resultados que contém os
  itens já é `overflow-y-auto` — usar `position: fixed` +
  `getBoundingClientRect()` do item clicado para posicionar o popover,
  mesma técnica já aplicada nas Manutenções #23/#24 para o
  `ProdutoAutocomplete` não ser cortado por overflow do container pai.
  **Nunca** `overflow-hidden` em nenhum container envolvido (regra
  global do Brush).
- Conteúdo: título `text-xs font-medium text-gray-500 dark:text-slate-400`
  = `"Vender em:"` + `Select` (componente existente) com options =
  unidade base (default, primeira opção) + cada `conversao.unidade`
  cadastrada, usando `unidade_display` da API (já vem formatado, ex.
  "CX — Caixa"). Botão `Button` `size="sm"`, label "Adicionar", full
  width dentro do popover.
- Fechar: clique fora (mesmo padrão já usado para fechar o dropdown de
  busca) ou `Escape`.
- Ao confirmar: `adicionarProduto(produto, unidadeEscolhida)` —
  `adicionarProduto` ganha 2º parâmetro opcional, default
  `produto.unidade_base || 'UN'` quando omitido. Preserva as 3 chamadas
  existentes que não passam por escolha manual (RF-17 Enter/código de
  barras, RF-19 câmera) — leitura física de código de barras já
  identifica a unidade cadastrada do produto, não precisa de escolha.
- Ícone no gatilho: nenhum novo — o item da lista já é o gatilho; não
  adicionar chevron/seta que sugira "abrir menu", o texto "Vender em:"
  já sinaliza o comportamento quando aparece.

### 4. `pdv/components/CarrinhoItem.jsx` — RF-07 (cosmético)

**Nenhuma mudança visual.** Trocar as 2 ocorrências de
`item.produto_unidade` por `item.unidade` (JSDoc do cabeçalho +
`{BRL(item.valor_unitario)} / {item.produto_unidade || 'UN'}` +
`<span>...{item.produto_unidade || 'UN'}</span>` no rodapé do stepper).
Mesma posição, mesmo estilo (`text-xs text-gray-500 dark:text-slate-400`
e `text-xs text-gray-400 dark:text-slate-500`), só o dado exibido passa
a ser real — hoje sempre mostra "UN" mesmo vendendo CX/PT; depois do
RF-05 isso ficaria visivelmente errado se não corrigido junto.

---

## Ícones (Lucide React) — resumo desta manutenção

| Ação | Ícone | Tamanho | Já importado? |
|---|---|---|---|
| Adicionar conversão | `<Plus />` | 14px | sim (Produtos.jsx) |
| Remover conversão | `<Trash2 />` | 16px | sim (Produtos.jsx) |
| Preview de cadeia (decorativo) | `<ArrowRight />` | 12px | **novo import** em Produtos.jsx |
| Registrar entrada | `<Plus />` | 14px | sim (Produtos.jsx) |

Nenhum ícone novo necessário em `FrenteDeCaixa.jsx` nem `CarrinhoItem.jsx`.

---

## Espaçamentos e componentes existentes a reutilizar

- `Select.jsx` — Unidade, Converte para (novo), Vender em (novo no PDV) — mesmo componente, mesma prop shape
- `Input.jsx` — Quantidade da conversão, campos da Entrada de Estoque
- `Button.jsx` — botão "Adicionar" do popover de unidade (`size="sm"`, variante default)
- `Card.jsx` — sem alteração, contexto já existente
- `Modal.jsx` — modal Novo/Editar Produto, sem alteração de estrutura
- Toast pattern — reaproveitado tal qual em ambas as telas

---

## Mobile-first (375px)

- Seção Conversões (`Produtos.jsx`): linha de conversão empilha em
  coluna (`flex-col sm:flex-row`) a partir de <640px — 3 campos +
  lixeira lado a lado em 375px não cabe com labels legíveis.
- Preview de fator composto: sem `whitespace-nowrap` — texto pode
  quebrar linha naturalmente em cadeias de 3+ elos.
- Popover "Vender em" (PDV): ~220px cabe em 375px sem estourar a
  viewport; se o item clicado estiver perto da borda direita, abrir
  alinhado à direita (flip), não cortar.
- Preview de RF-08 (Entrada de Estoque): já dentro do modal
  (`maxW="max-w-2xl"`, que ocupa a largura útil em mobile) — nenhum
  ajuste extra além da quebra de linha natural do texto.

---

## Dark Mode — checklist de tokens (nenhum token novo necessário)

| Elemento novo | Light | Dark |
|---|---|---|
| Select "Converte para" / "Vender em" | Select.jsx (já dark-aware) | idem |
| Texto de preview (fator composto / entrada) | `text-gray-500` | `dark:text-slate-400` |
| Aviso de cadeia quebrada / sem conversão | `text-amber-700` | `dark:text-amber-400` |
| Ícone ArrowRight decorativo | `text-gray-400` | `dark:text-slate-500` |
| Popover "Vender em" (PDV) | `bg-white border-gray-200 shadow-lg` | `dark:bg-navy-800 dark:border-navy-600` |
| Label "Vender em:" | `text-gray-500` | `dark:text-slate-400` |

---

## O que NÃO fazer (reforço)

```
❌ NÃO criar componente novo além do popover "Vender em" — reaproveitar Select/Input/Button tal qual
❌ NÃO usar overflow-hidden em nenhum container do popover de unidade no PDV — repete a armadilha já corrigida nas Manutenções #23/#24
❌ NÃO usar window.confirm() para excluir linha de conversão dentro do modal — reservado a exclusão de produto inteiro
❌ NÃO abrir modal cheio (Modal.jsx) para escolha de unidade no PDV — é decisão de 1 campo, popover inline é suficiente
❌ NÃO forçar seleção de unidade em produto sem conversão cadastrada — mantém clique direto, zero fricção nova
❌ NÃO truncar a mensagem de erro RN-06 (lista de dependência) no toast — usar whitespace-pre-line já existente
❌ NÃO alterar unidade enviada pelas chamadas de adicionarProduto vindas de RF-17 (Enter/código físico) ou RF-19 (câmera) — continuam na unidade base
```

---

## Passagem de bastão

```
✅ Especificação UI concluída — UidCore (Manutenção #37)
   Telas analisadas: 3 (Produtos.jsx, FrenteDeCaixa.jsx, CarrinhoItem.jsx)
   Componentes reutilizados: 5 existentes (Select, Input, Button, Card, Modal)
   Novos padrões: 1 — popover inline "Vender em:" no PDV (não é modal,
   não é o dropdown de busca — anotado explicitamente para o Loom não
   confundir com nenhum dos dois)

📁 Arquivo: Especificacao_UI_Hotfix.md (em /var/www/uidcore/)

➡️ Loom lê Especificacao_Hotfix.md + Especificacao_UI_Hotfix.md antes de
   implementar RF-01/RF-02/RF-03/RF-04/RF-08 em Produtos.jsx e
   RF-05/RF-06/RF-07 em FrenteDeCaixa.jsx + CarrinhoItem.jsx.
```
