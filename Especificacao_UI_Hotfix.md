# Especificação UI Hotfix — UidCore (Manutenção #33)
**Elaborado por:** Brush (MODO HOTFIX)
**Data:** 2026-08-15
**Base:** Especificacao_Hotfix.md (Analista, Manutenção #33)

---

## Escopo desta especificação

Rename puro de nomenclatura de domínio — "Funcionário(s)" → "Colaborador(es)" —
dentro do módulo RH (`frontend/src/pages/Rh.jsx`). **Não há tela nova, componente
novo ou mudança estrutural de layout.** O trabalho do Brush aqui é confirmar que
a camada visual não precisa de nenhum ajuste além do texto/labels já especificados
pelo Analista, e documentar os pontos onde há decisão visual (ícone, cor, espaçamento)
para o Loom não improvisar.

---

## Design System do Projeto (referência)

- Cores primárias: `--color-primary` (`bg-primary-600` / `dark:bg-violet-600`) para
  estado ativo de tabs e botões primários
- Cores de fundo: light `bg-white` / `bg-gray-100`; dark `bg-navy-800` /
  `bg-navy-700` (hover) — paleta navy (60%) + violet (30%) + red (10%), conforme
  Manutenção #31 (Dark Mode)
- Fonte: Plus Jakarta Sans (headings) + DM Sans (body/interface) — já confirmadas
  no projeto, não alterar
- BorderRadius padrão: `rounded-lg` (8px) em tabs, botões e cards do `ResourceCrud`
- Padrão de card/lista: componente `ResourceCrud` genérico (`components/ui/
  ResourceCrud.jsx`) — já trata título, botão de criação, colunas, badges, ícone
  de estado vazio e formulário; **reutilizar integralmente, nenhuma prop nova
  precisa ser criada**

---

## Especificação Visual por Tela

### Rh.jsx — Aba "Colaboradores" (renomeada de "Funcionários")

**Layout geral:**
- Estrutura: idêntica à atual — nenhuma mudança de estrutura, grid, ordem de
  campos ou padding. O `ResourceCrud` já resolve layout responsivo (mobile:
  cards empilhados; desktop: tabela).
- Nenhum ajuste de padding/margin necessário — troca é só de string.

**Barra de tabs (topo da página):**
- Sem mudança visual — apenas o `label` do item do array `TABS` muda de
  `'Funcionários'` para `'Colaboradores'` e o `key` de `'funcionarios'` para
  `'colaboradores'` (conforme RF-01/RN-02 do Analista).
- Estado ativo continua: `bg-primary-600 text-white dark:bg-violet-600`
- Estado inativo continua: `bg-white text-gray-600 border border-gray-200
  dark:bg-navy-800 dark:text-slate-400 dark:border-navy-600`
- Nenhum ícone Lucide na tab — segue padrão texto puro já usado nas outras 3
  tabs do módulo (Cargos, Folha de Pagamento, Férias). Não introduzir ícone
  aqui para manter consistência com as demais.

**Card/listagem de Colaboradores (`ResourceCrud`):**
- `title`: "Colaboradores" (era "Funcionários")
- `createLabel`: "+ Novo Colaborador" (era "+ Novo Funcionário") — padrão de
  botão primário do `ResourceCrud`, sem mudança de estilo
- `emptyIcon`: **manter `"👔"`** — decisão de projeto já documentada (DIV-UI03,
  Manutenção #9/#10: emojis na Sidebar/ResourceCrud são intencionais, não
  Lucide). O emoji de gravata já é semanticamente neutro entre
  "funcionário"/"colaborador" — não precisa trocar.
- `emptyText`: "Nenhum colaborador encontrado." (era "Nenhum funcionário
  encontrado.")
- Colunas (`nome`, `cargo_nome`, `regime_label` com badge, `salario_atual` com
  money, `data_admissao` com date): **nenhuma mudança de layout ou formatação**
  — já são neutras quanto ao nome da entidade
- Campos do formulário (`nome`, `cpf`, `email`, `cargo`, `regime`,
  `salario_atual`, `data_admissao`, `data_demissao`, `observacoes`): **nenhuma
  mudança** — já neutros

### Rh.jsx — Aba "Folha de Pagamento" (não renomeada, mas referencia colaborador)

**Layout geral:** sem mudança estrutural.

**Coluna/campo de referência ao colaborador:**
- Coluna da tabela: `label: 'Colaborador'` (era `'Funcionário'`), `key:
  'colaborador_nome'` (era `'funcionario_nome'`) — mesma formatação de texto,
  sem badge, sem ícone
- Campo do formulário: `label: 'Colaborador'`, `name: 'colaborador'`, mesmo
  `type: 'select-remote'`, apontando para `endpoint: 'rh/colaboradores'` (era
  `'rh/funcionarios'`) — o componente de select-remote já existe e não precisa
  de nenhum ajuste visual, só o endpoint/label mudam (RF-05)
- `titleField`: `'colaborador_nome'` (era `'funcionario_nome'`) — usado
  internamente pelo `ResourceCrud` para exibir o item no modal de
  confirmação/edição, sem impacto visual

### Rh.jsx — Aba "Férias" (não renomeada, mas referencia colaborador)

Mesmo padrão da Folha de Pagamento:
- Coluna: `label: 'Colaborador'`, `key: 'colaborador_nome'`
- Campo: `label: 'Colaborador'`, `name: 'colaborador'`, `endpoint:
  'rh/colaboradores'`
- `titleField: 'colaborador_nome'`

### Aba "Cargos" — fora de escopo

Nenhuma alteração visual ou de texto. Não referencia colaborador/funcionário.

---

## Ícones (Lucide React)

Nenhum ícone Lucide novo é necessário nesta manutenção. O módulo RH usa emojis
como `emptyIcon` do `ResourceCrud` (padrão já documentado, não migrar para
Lucide nesta manutenção — fora de escopo do pedido do cliente):

| Aba | emptyIcon atual | Ação |
|---|---|---|
| Colaboradores | 👔 | manter |
| Cargos | 🏷️ | manter (fora de escopo) |
| Folha de Pagamento | 🧾 | manter (fora de escopo) |
| Férias | 🏖️ | manter (fora de escopo) |

---

## Espaçamentos e componentes existentes a reutilizar

- `ResourceCrud` (componente único reutilizado nas 4 abas) — nenhuma prop nova,
  nenhuma variante nova
- Tabs: `flex gap-1 overflow-x-auto pb-1` no container, `px-4 py-2 rounded-lg`
  em cada botão — sem alteração
- Nenhum novo componente de UI precisa ser criado para esta manutenção

---

## Padrões mobile-first do UidCore (dark mode navy/violet)

- Breakpoint de referência: 375px (iPhone SE), conforme padrão Uid
- Tabs: já usam `overflow-x-auto` + `whitespace-nowrap` — comportamento de
  scroll horizontal em mobile preservado, sem mudança
- `ResourceCrud` já resolve o padrão mobile (cards empilhados) vs desktop
  (tabela) internamente — nenhuma alteração necessária para este rename
- Dark mode: classes `dark:bg-navy-800`, `dark:bg-navy-700`, `dark:text-slate-400`,
  `dark:bg-violet-600` já aplicadas na barra de tabs (Manutenção #31) — mantidas
  sem alteração
- Contraste: textos "Colaborador(es)" seguem os mesmos tokens de cor dos textos
  "Funcionário(s)" que substituem — nenhum novo risco de contraste introduzido

---

## O que NÃO fazer (reforço)

```
❌ NÃO criar novo componente para a aba Colaboradores
❌ NÃO trocar o emoji 👔 por ícone Lucide (fora de escopo do pedido)
❌ NÃO alterar layout, grid, padding ou breakpoints do ResourceCrud
❌ NÃO tocar nas abas Cargos (fora de escopo — não referencia colaborador)
❌ NÃO introduzir nova paleta de cor — reaproveitar tokens navy/violet existentes
```

---

## Passagem de bastão

```
✅ Especificação UI concluída — UidCore (Manutenção #33)
   Telas analisadas: 1 arquivo (Rh.jsx), 3 abas afetadas (Colaboradores, Folha
   de Pagamento, Férias)
   Componentes reutilizados: ResourceCrud (100% reaproveitado, 0 mudança de props/estilo)
   Novos padrões: nenhum — rename puro de texto/payload, sem impacto visual

📁 Arquivo: Especificacao_UI_Hotfix.md (em /var/www/uidcore/)

➡️ Loom lê Especificacao_Hotfix.md + Especificacao_UI_Hotfix.md antes de
   implementar as trocas em Rh.jsx (RF-01 a RF-06)
```
