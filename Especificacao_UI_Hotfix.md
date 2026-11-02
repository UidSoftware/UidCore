# Especificação UI Hotfix — UidCore (Manutenção #89)

## Modo

**MODO HOTFIX.** Uma FK em cadastro existente (`Despesa.fornecedor_fk`),
dois campos novos (`subcategoria`, `tipo_desconto`/`percentual_desconto`)
e um ajuste de layout num formulário já existente. Sem app novo, sem tela
nova. Nenhuma mudança de identidade visual, paleta ou tipografia — tudo
reaproveita o design system já em produção.

Lido antes de escrever esta especificação: `Especificacao_Hotfix.md`
(Manutenção #89, seções 0-9 completas), `frontend/src/pages/Financeiro.jsx`
(`DespesasTab` completo, linhas 740-985), `frontend/src/pages/Vendas.jsx`
(`BuscaProdutoRapida`, linhas 193-283 — padrão de referência explícito
citado pelo Analista), `frontend/src/components/ui/
CriarCategoriaRapidaModal.jsx` (padrão de "modal rápido inline" já
existente, reaproveitado 3x no projeto), `components/ui/{Select, Input,
Button, Modal}.jsx`.

## Design System do Projeto (referência — não alterado)

- **Cores primárias:** `primary-600` (light) / `violet-600` (dark) —
  botão de ação, foco de input/select. Hover: `primary-700`/`violet-700`.
- **Cores de fundo:** `white`/`gray-50` (light), `navy-800`/`navy-900`
  (dark) — `navy-500`/`navy-600` para bordas de input/select,
  `navy-700` para hover de linha/dropdown.
- **Texto:** `text-gray-900`/`text-gray-700`/`text-gray-400` (light),
  `text-slate-100`/`text-slate-300`/`text-slate-500` (dark) — escala do
  mais forte ao mais apagado, idêntica em toda a tela.
- **Feedback:** vermelho (`red-600`/`red-700`, dark `red-400`/`red-900`)
  já usado para valor de Despesa/saída (`BRL(item.valor_liquido)`) e
  erro de validação — nenhuma cor de feedback nova nesta manutenção.
- **Fonte:** Plus Jakarta Sans (display) + DM Sans (body) — já
  carregadas globalmente, não tocar.
- **BorderRadius:** `rounded-lg` (inputs, selects, botões), `rounded-2xl`
  (`Modal.jsx`).
- **Dark mode:** classe `dark` no `<html>`, toggle já existente — não
  tocar.
- **Ícones:** `lucide-react` (já é dependência do projeto). **Sem emoji
  nesta tela** — emoji é padrão intencional só da Sidebar.
- **Componentes a reutilizar (nenhum componente genérico novo):**
  `Card`, `Modal`, `Button`, `Select`, `Input`, `AuditFooter`. Um
  componente de domínio novo (`BuscaFornecedorRapida`, clone adaptado de
  `BuscaProdutoRapida`) e um modal rápido novo (`NovoFornecedorModal`,
  mesmo molde de `CriarCategoriaRapidaModal`) — ambos seguindo padrões já
  existentes no projeto, nunca inventados do zero.

---

## Especificação Visual por Tela

Única tela afetada: **Financeiro → Contas a Pagar** (`DespesasTab` em
`Financeiro.jsx`) — modal "Nova/Editar Despesa" e a barra de filtros da
listagem. Não cria aba nova, não cria rota nova.

### 1. Modal "Nova Despesa" / "Editar Despesa" — reordenação de campos

**Ordem atual (hoje):**
```
[Tipo | Conta] → Categoria → Descrição → Fornecedor (texto) →
[Valor Bruto | Desconto R$ | Vencimento] → Mês de referência →
Forma de Pagamento → Observações
```

**Ordem nova (RF-F01/RF-F02):**
```
1. Fornecedor (busca + "+ Novo fornecedor")    ← NOVO, 1º campo
2. [Tipo | Conta]                               ← mesma posição de hoje
3. Categoria                                    ← mesma posição relativa
4. Subcategoria                                 ← NOVO, logo após Categoria
5. Descrição
6. [Valor Bruto | Desconto (R$/%) | Vencimento] ← mesmo grid 3 col de hoje
7. Mês de referência (competência)
8. Forma de Pagamento
9. Observações
10. AuditFooter (se edição)
```

Container do form continua `<form className="space-y-4">` — nenhum
espaçamento novo, só reordenação + inserção de 2 blocos (Fornecedor,
Subcategoria) e substituição de 1 campo (Desconto).

**Mobile (375px):** os grids existentes (`grid-cols-1 sm:grid-cols-2` e
`grid-cols-1 sm:grid-cols-3`) já colapsam para coluna única — sem
alteração. Fornecedor e Subcategoria ficam fora de qualquer grid
(`full-width` nativo), herdando o mesmo comportamento.

---

### 2. Campo Fornecedor — `BuscaFornecedorRapida` (substitui o `Input` texto livre)

**Reuso explícito e obrigatório:** clonar `BuscaProdutoRapida`
(`Vendas.jsx`) — mesmo hook de debounce 300ms, mesmo `AbortController`,
mesma técnica `position: fixed` via `getBoundingClientRect()` (escapa o
`overflow-y-auto` do `Modal`, mesmo problema que motivou o fix original
em Vendas/Compras). Só trocam o endpoint (`/fornecedores/?search=`) e o
conteúdo renderizado em cada linha do dropdown.

```
Fornecedor
┌───────────────────────────────────────┬──────────┐
│ 🔍  Buscar fornecedor...               │ + Novo   │
└───────────────────────────────────────┴──────────┘
  (dropdown abre abaixo, position:fixed, mesma técnica de Vendas.jsx)
```

- Label `"Fornecedor"` acima, mesma tipografia de label dos demais
  campos (`text-sm font-medium text-gray-700 dark:text-slate-300`) —
  campo é custom (não usa `Input.jsx` puro, mas replica a label dele
  para não destoar visualmente.
- Input: ícone `Search` (16px) `absolute left-3 top-1/2
  -translate-y-1/2`, mesma classe de borda/foco já usada em
  `BuscaProdutoRapida` (inclui variante dark `navy-500`/`navy-800`/
  `violet-500`). Placeholder: `"Buscar fornecedor..."`.
- Botão `"+ Novo"` ao lado, mesma linha (`flex items-center gap-2`):
  `variant="secondary"`, `size="sm"`, ícone `Plus` (12px) + texto
  `"Novo"`.
- Dropdown: mesma classe de `BuscaProdutoRapida`
  (`bg-white rounded-lg shadow-lg border max-h-64 overflow-y-auto
  dark:bg-navy-800 dark:border-navy-600`). Cada linha:
  - `nome_razao_social` em negrito (`text-sm font-medium`).
  - Segunda linha só se `documento` existir (`text-xs text-gray-400
    dark:text-slate-500`) — omitir a linha inteira quando vazio, nunca
    deixar espaço reservado em branco.
  - Sem coluna à direita (preço/estoque não se aplicam a Fornecedor).
- Selecionar: preenche `fornecedor_fk` + `fornecedor_fk_nome`, limpa a
  busca, dispara a chamada de sugestão (seção 4 abaixo).
- **Depois de selecionado**, o input de busca é substituído por um chip:
  ```
  🏢  Fornecedor Alfa Materiais Ltda                    [Trocar]
  ```
  Ícone `Building2` (16px), `text-sm font-medium text-gray-900
  dark:text-slate-100`; botão `"Trocar"` (`variant="secondary"`,
  `size="sm"`) volta ao estado de busca (limpa `fornecedor_fk`, reabre
  o input vazio).

**Fornecedor legado (edição de despesa com `fornecedor` texto,
`fornecedor_fk=null`) — RN-01:** enquanto nenhum fornecedor novo for
selecionado, mostrar abaixo do campo de busca:
```
ℹ️  Cadastro antigo (texto livre): "Fornecedor Alfa Materiais"
    Buscar e selecionar acima para vincular ao cadastro.
```
Ícone `Info` (14px), `text-xs text-gray-400 dark:text-slate-500` — mesmo
tom das notas explicativas já existentes no form (ex.: a nota abaixo de
"Mês de referência"). Não é erro, não bloqueia nada; some sozinho se o
usuário vincular um fornecedor nessa edição. Se não vincular, o texto
legado em `fornecedor` segue sendo enviado no payload exatamente como
estava (campo preservado no estado do form, só sem `<Input>` visível
dedicado — RF-F01 não pede edição manual desse texto).

---

### 3. Modal "Novo Fornecedor" (rápido, inline) — `NovoFornecedorModal`

**Reuso explícito:** mesma estrutura de `CriarCategoriaRapidaModal.jsx`
— `Modal maxW="max-w-sm"`, form mínimo, rodapé Cancelar/Criar idêntico.

```
┌─ Novo Fornecedor ──────────────────────┐
│  Nome / Razão Social                   │
│  [________________________________]   │
│                                         │
│  Tipo de Pessoa                        │
│  [ Pessoa Física ▾ ]                   │
│                                         │
│  Documento (CPF/CNPJ) — opcional       │
│  [________________________________]   │
│                                         │
│                  [Cancelar]   [Criar]  │
└─────────────────────────────────────────┘
```

- Campos: `nome_razao_social` (`Input`, obrigatório, `autoFocus`),
  `tipo_pessoa` (`Select`, `PF`/`PJ` — reaproveitar as mesmas opções já
  usadas em qualquer outro cadastro de pessoa do projeto, nenhum rótulo
  novo), `documento` (`Input`, opcional, sem máscara — backend já
  valida/normaliza).
- Rodapé: `Button variant="secondary"` Cancelar + `Button` Criar
  (`loading={saving}`).
- Sucesso: `POST /api/v1/fornecedores/`, toast `"Fornecedor
  cadastrado."` (mesmo padrão de texto de `CriarCategoriaRapidaModal`:
  `"Categoria criada."`), fecha o modal, preenche `fornecedor_fk`/
  `fornecedor_fk_nome` no form de Despesa (equivalente a já ter
  "selecionado" via busca) e dispara a sugestão (seção 4 — resultado
  vazio para fornecedor recém-criado, sem efeito visual).
- **Empilhamento sobre o modal "Nova Despesa"** já aberto: mesma técnica
  já validada em `CriarCategoriaRapidaModal` dentro deste mesmo form —
  renderizar o segundo `<Modal>` depois na árvore JSX
  (`{novoFornecedorAberto && <NovoFornecedorModal ... />}` após o modal
  de Despesa) já empilha visualmente por cima, sem tocar em
  `Modal.jsx` nem adicionar `zIndex` novo.

---

### 4. Categoria + Subcategoria

**Categoria:** sem mudança visual — mantém exatamente como está hoje
(label + link "+ Nova categoria" com `Plus` 12px + `Select`).

**Subcategoria (novo, imediatamente depois de Categoria — RF-F02):**
```
Categoria                           [+ Nova categoria]
[ Fornecedores / Serviços ▾ ]

Subcategoria
[ Nenhuma ▾ ]
```
- `Select` com `label`, sem link de "+ Nova" (subcategoria é criada
  escolhendo um `pai` — fluxo já coberto na aba Categorias da
  Manutenção #88, fora do escopo visual desta tela).
- `options` sempre com `{ value: '', label: 'Nenhuma' }` como primeira
  entrada.
- Populado via `GET /financeiro/categorias/?pai=<categoria_id>` sempre
  que `form.categoria` mudar.
- Lista vazia (categoria sem subcategorias) → `Select` mostra só
  "Nenhuma", **`disabled`** — sinaliza visualmente que não há opção, em
  vez de um select clicável sem efeito.
- Trocar/limpar Categoria: reseta `form.subcategoria` para `''`
  imediatamente, antes mesmo da nova lista chegar — nunca deixa uma
  subcategoria "órfã" de uma categoria diferente aparecendo selecionada.

---

### 5. Sugestão automática de categoria/subcategoria por fornecedor (RF-F03)

**Decisão de UX: auto-fill com indicação visual discreta, não
tooltip.** Tooltip depende de hover, mal descobrível em mobile (sem
hover real); auto-fill já é o padrão do próprio form
(`CriarCategoriaRapidaModal` também pré-seleciona a categoria recém-
criada). A etiqueta visual evita o usuário achar que "adivinhou do
nada" sem entender a origem.

Ao selecionar um Fornecedor (via busca ou via "+ Novo fornecedor"):

1. Dispara `GET /financeiro/despesas/sugestao-categoria/
   ?fornecedor_fk=<id>` em paralelo, sem bloquear a UI (sem spinner —
   é dado complementar, não uma ação que o usuário espera).
2. Resposta com `categoria`/`subcategoria` não nulos **e** campos do
   form ainda vazios (nunca sobrescreve escolha manual — RN-05):
   pré-seleciona os dois `Select` e mostra, uma vez, abaixo de
   Subcategoria:
   ```
   ✓ Sugerido com base no histórico deste fornecedor
   ```
   `text-xs text-primary-600 dark:text-violet-400` (mesmo tom do link
   "+ Nova categoria" — sinaliza "preenchimento assistido", não erro/
   aviso). Some se o usuário alterar manualmente Categoria ou
   Subcategoria depois (nesse ponto a escolha já é manual).
3. Resposta `{"categoria": null, "subcategoria": null}` (sem despesa
   anterior) ou campos já preenchidos: nenhuma mudança visual.

---

### 6. Desconto em R$ ou % (RF-F04)

Substitui `<Input label="Desconto (R$)" .../>` (hoje a célula central do
grid `[Valor Bruto | Desconto | Vencimento]`) por um campo composto
dentro da **mesma célula do grid** — não altera o grid de 3 colunas.

```
Desconto                              Desconto
┌──────┬─────────────┐                ┌──────┬─────────────┐
│ R$ ▾ │  [ 20,00  ]  │     ou         │  % ▾ │  [ 10,00  ]  │
└──────┴─────────────┘                └──────┴─────────────┘
                                       ≈ R$ 20,00
```

- Seletor à esquerda: `<select>` compacto (mesma classe de
  `Select.jsx`, largura `w-16` em vez de `w-full`), 2 opções: `R$` / `%`.
  Colado ao input numérico (`flex`, sem gap, `rounded-l-lg` no select e
  `rounded-r-lg` no input — "campo único visual com prefixo").
- Input numérico à direita: mesmas classes de `Input.jsx`, sem label
  própria (compartilha a label "Desconto" do bloco).
- Trocar `R$`↔`%`: limpa o valor numérico (evita interpretar "20"
  digitado como R$ virando "20" como % sem revisão).
- Modo `%`: abaixo do campo, preview em tempo real
  (`valor_bruto * percentual / 100`, formatado com o mesmo `BRL()` já
  usado na tela): `text-xs text-gray-400 dark:text-slate-500`:
  ```
  ≈ R$ 20,00
  ```
  Recalcula ao digitar em `percentual_desconto` ou `valor_bruto`;
  `valor_bruto` vazio/0 → `≈ R$ 0,00` (nunca `NaN`).
- Payload sempre envia os 3 campos juntos (`tipo_desconto`,
  `percentual_desconto`, `desconto`) — o backend decide/recalcula qual
  prevalece (RF-04 backend), o frontend só evita mandar campo vazio
  enquanto isso.
- Editar despesa com `tipo_desconto='%'`: reabre já no modo `%` com
  `percentual_desconto` preenchido (nunca reabre padrão em `R$`).

---

### 7. Filtros na listagem de Contas a Pagar (RF-F05)

```
┌───────────────────────────────────────────────────────────────┐
│ [ Buscar...     ] [ Status ▾ ] [ Categoria ▾ ] [ Subcategoria ▾ ] │
└───────────────────────────────────────────────────────────────┘
```

- Mesmo `Card` + `flex flex-col sm:flex-row gap-3` já existente —
  acrescenta 2 `Select` ao final (`w-full sm:w-48`, mesma largura do
  `Select` de Status já em produção).
- `Select Categoria`: reusa `categoriaOptions` já carregado para o form
  (não duplicar chamada); sem `label` visível (mesmo padrão do Status —
  a primeira option já comunica o que é, ex.: `"Categoria"`/`"Todas"`).
- `Select Subcategoria`: populado a partir da Categoria escolhida no
  filtro (mesmo endpoint `?pai=<id>`); sem Categoria selecionada no
  filtro → lista com só "Todas", não trava a tela.
- Filtro por Fornecedor: **não cria campo novo** — reaproveita o `Input`
  de busca textual já existente (RF-F05 é SHOULD; busca textual já
  cobre o pedido do cliente nesta rodada).
- **Mobile (375px):** linha de filtros já quebra em coluna
  (`flex-col sm:flex-row`); os 2 novos `Select` empilham abaixo do
  Status, `w-full` até o breakpoint `sm`.

---

## Ícones Lucide — consolidado desta manutenção

| Ícone | Tamanho | Uso |
|---|---|---|
| `Search` | 16px | Campo de busca de Fornecedor |
| `Building2` | 16px | Chip de fornecedor selecionado |
| `Info` | 14px | Aviso de cadastro legado (fornecedor texto sem FK) |
| `Plus` | 12px | Botão "+ Novo" (fornecedor) — mesmo padrão já usado em "+ Nova categoria" |
| `Percent` | 12px (opcional, decorativo) | Reforço visual do modo "%" no seletor de desconto |

Todos já fazem parte da dependência `lucide-react` já instalada. Import
a acrescentar em `Financeiro.jsx`: `Search`, `Building2`, `Info` (e
`Percent`, se o Loom optar por usá-lo) junto da lista já existente
(`ChevronDown, ChevronUp, Edit, Plus, Pencil, Trash2, CornerDownRight,
Tag`).

## Badges / Status

Sem badge novo — `Badge status={item.status}` da listagem de Despesas
permanece inalterado.

## Componentes reutilizados (resumo)

| Componente | Onde é usado nesta manutenção | Alterado? |
|---|---|---|
| `Modal.jsx` | Modal Nova/Editar Despesa (sem mudança) + `NovoFornecedorModal` (novo) | Não |
| `Input.jsx` | Campos do `NovoFornecedorModal`, input numérico do seletor de Desconto | Não |
| `Select.jsx` | Subcategoria (form + filtro), Categoria (filtro), seletor compacto R$/% | Não |
| `Button.jsx` | "+ Novo" (fornecedor), "Trocar" (chip), Cancelar/Criar | Não |
| `Card.jsx` | Barra de filtros (sem mudança estrutural) | Não |
| `BuscaProdutoRapida` (`Vendas.jsx`) | **Padrão de referência** — `BuscaFornecedorRapida` é adaptação direta (endpoint + conteúdo de linha trocados; debounce/abort/posicionamento idênticos) | — |
| `CriarCategoriaRapidaModal.jsx` | **Padrão de referência** — `NovoFornecedorModal` segue a mesma estrutura (modal pequeno, 1 POST, toast, fecha, preenche form-pai) | Não |

## Mobile-first (375px)

- Campo de busca de Fornecedor, chip de fornecedor, seletor composto de
  Desconto: todos full-width no mobile — fora de grid, ou herdando o
  colapso de `sm:grid-cols-*` já existente.
- Filtros novos empilham em coluna, herdado do `flex-col sm:flex-row`
  já aplicado ao filtro de Status — nenhum CSS novo.
- Dropdown de busca de Fornecedor usa `position: fixed` (copiado de
  `BuscaProdutoRapida`) — essencial no mobile porque o `Modal` já usa
  `overflow-y-auto`; sem isso o dropdown ficaria cortado/rolando junto
  com o form (mesmo bug que a técnica original corrigiu no PDV/Vendas).
- Nunca `overflow-hidden` no container do form/modal (regra global do
  projeto).

## Decisões do Brush não explícitas na Especificacao_Hotfix.md (registradas para o Loom não precisar adivinhar)

1. Sugestão de categoria/subcategoria por fornecedor (RF-F03) é
   **auto-fill com etiqueta discreta**, não tooltip — justificativa de
   descobribilidade em mobile, ver seção 5.
2. Seletor de Desconto R$/% usa visual de "campo composto com prefixo"
   (select colado ao input, bordas compartilhadas) em vez de 2 campos
   lado a lado com gap — mantém a aparência de "1 campo só" dentro da
   mesma célula do grid de 3 colunas já existente, sem alargar o modal.
3. Fornecedor legado (texto, sem FK) nunca ganha um `<Input>` editável
   visível nesta manutenção — só o aviso informativo (RF-F01 não pede
   edição do texto legado; campo continua preservado no estado/payload
   sem UI dedicada).
4. `NovoFornecedorModal` fica dentro de `pages/Financeiro.jsx` (escopo
   local, não em `components/ui/`) — diferente de
   `CriarCategoriaRapidaModal` (que é reaproveitado em 3 páginas
   diferentes), este modal só é usado em Despesa nesta manutenção; se um
   uso futuro em outra tela aparecer, promover para `components/ui/`
   naquele momento, não antecipar agora.
5. Badge "Sugerido com base no histórico" (seção 5) é texto simples, não
   um componente `Badge` novo — é uma etiqueta textual transitória, não
   um estado persistente de dado como os badges de Status/Ativo já
   existentes.

---

## Passagem de bastão

```
✅ Especificação UI concluída — UidCore (Manutenção #89)
   Telas analisadas: 1 (Financeiro → Contas a Pagar — modal Nova/Editar
     Despesa + barra de filtros)
   Componentes reutilizados: 6 existentes (Modal, Input, Select, Button,
     Card, AuditFooter) + 2 padrões de referência direta
     (BuscaProdutoRapida, CriarCategoriaRapidaModal)
   Novos padrões: 2 — BuscaFornecedorRapida (clone adaptado) e seletor
     composto R$/% (só composição de classes Tailwind já em uso, nenhum
     token novo)

📁 Arquivo: Especificacao_UI_Hotfix.md (em /var/www/uidcore/)

➡️ Loom lê Especificacao_Hotfix.md (Analista) + este arquivo antes de
   implementar o frontend. Nenhum código foi escrito por este agente.
```
