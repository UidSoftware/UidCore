# Especificação UI Hotfix — UidCore (Manutenção #40)
**Elaborado por:** Brush (MODO HOTFIX)
**Data:** 2026-08-18
**Base:** Especificacao_Hotfix.md (Analista, Manutenção #40 — fix `converteParaOptions`
dependente de ordem + reordenação topológica no `handleSubmit`, seção "Conversões de
Unidade" de `Produtos.jsx`)

---

## Design System do Projeto (referência)

UidCore é **light mode por padrão** (divergência documentada em `design_system.md` —
não é o padrão escuro da Uid, decisão arquitetural do projeto, não alterar aqui).

- **Cores primárias:** `primary-600` (#2563eb) — ações/links; `primary-800` — hover de
  texto de ação (usado no botão "+ Adicionar Conversao" desta mesma seção)
- **Cores de fundo:** `bg-gray-50` (seções agrupadas dentro do modal) /
  `dark:bg-navy-900/50` — já aplicado no container "Conversões de Unidade", sem mudança
- **Cores de feedback:** `bg-red-600` (toast de erro) / `bg-accent-600` (toast de
  sucesso) — componente de toast já existente na própria página, local a cada `.jsx`
  (padrão replicado em Vendas/Fornecedores/Conciliacao/Clientes), não um componente
  compartilhado
- **Fonte:** Plus Jakarta Sans (títulos) + DM Sans (corpo) — herdadas globalmente,
  nenhum ajuste nesta tela
- **BorderRadius padrão:** `rounded-lg` (seções/cards), `rounded` (inputs/selects via
  `Select.jsx`/`Input.jsx`)
- **Padrão de card/seção agrupada:** `bg-gray-50 rounded-lg border border-gray-200 p-4
  dark:bg-navy-900/50 dark:border-navy-700` — usado tanto em "Conversões de Unidade"
  quanto em "Entradas de Estoque", mesmo padrão visual

---

## Escopo desta manutenção (confirmação do Brush)

Lido `Especificacao_Hotfix.md`: **RF-01 e RF-02 são 100% lógica, zero mudança
visual.** O próprio Analista já confirma: *"Nenhuma mudança visual nova: o Select
'Converte para' passa a listar mais opções ... em vez de só as que já têm linha
criada"* e RF-03 mantém o aviso por linha exatamente como está hoje.

Confirmado lendo `Produtos.jsx` diretamente (linhas ~522-635):

- O `<Select>` "Converte para" já é o componente `Select.jsx` existente — só a prop
  `options={converteParaOptions}` passa a receber mais itens (todas as unidades de
  `UNIDADE_OPTIONS` exceto a base e a própria linha, em vez de só as unidades já
  criadas em outras linhas). Aparência, largura (`flex-1`), label ("Converte para"),
  posição no layout: **nada muda**.
- O layout responsivo da linha de conversão já é mobile-first:
  `flex flex-col gap-2 sm:flex-row sm:items-end` — empilha verticalmente abaixo do
  breakpoint `sm` (640px) e vira linha horizontal acima disso. Não precisa de ajuste.
- O toast de erro (RF-02, ciclo de dependência) usa o `showToast(msg, 'error')` já
  implementado na própria página (linha 90-93) — mesmo componente inline usado em
  "Erro ao remover conversao." (linha 197) e nas demais páginas do projeto
  (Vendas/Fornecedores/Conciliacao/Clientes têm o mesmo padrão local). Estilo:
  `fixed top-4 right-4 z-50 max-w-sm px-4 py-3 rounded-lg shadow-lg text-sm
  font-medium text-white whitespace-pre-line break-words bg-red-600`, timeout 7000ms
  (padrão já usado para `type === 'error'`, mais longo que o de sucesso). A mensagem
  do RF-02 (`"Conversões em ciclo: CX → PT → CX. Corrija antes de salvar."`) cabe
  dentro de `max-w-sm` e `whitespace-pre-line` já existente — nenhum ajuste de
  container necessário.

**Conclusão: nenhum token novo, nenhum componente novo, nenhum ícone novo.** Esta
especificação existe para confirmar formalmente que o Loom não precisa criar nada
visual além do que já está implementado — só trocar a lógica que monta o array
`converteParaOptions` e adicionar a função de ordenação topológica antes do loop de
`handleSubmit`, exatamente como descrito na Especificação técnica do Analista.

---

## Especificação Visual por Tela

### `Produtos.jsx` — Modal de cadastro/edição, seção "Conversões de Unidade"

**Layout geral (inalterado):**
- Seção dentro do modal: `bg-gray-50 rounded-lg border border-gray-200 p-4` (light) /
  `dark:bg-navy-900/50 dark:border-navy-700` (dark)
- Header da seção: título "Conversoes de Unidade" (`text-sm font-semibold
  text-gray-700 dark:text-slate-200`) + botão "+ Adicionar Conversao"
  (`<Plus size={14} />` + texto, `text-primary-600 dark:text-violet-400`) alinhados
  com `flex items-center justify-between`
- Cada linha de conversão: `flex flex-col gap-2 sm:flex-row sm:items-end` — 3 campos
  (`Select` Unidade, `Select` Converte para, `Input` Qtd por X) + botão remover
  (`<Trash2 size={16} />`, `text-red-400 hover:text-red-600`)
- Preview do resultado da cadeia abaixo de cada linha: `<ArrowRight size={12} />` +
  texto (`text-gray-500 dark:text-slate-400`), ou aviso âmbar
  (`text-amber-700 dark:text-amber-400`) quando a cadeia não fecha — **RF-03 mantém
  exatamente esse comportamento**, sem alteração

**Select "Converte para" (RF-01 — única mudança de dado, zero mudança visual):**
- Componente: `Select.jsx` existente, mesma instância já usada (label "Converte
  para", `value={convertePara}`, `onChange` inalterado)
- Options: passam de "base + unidades já criadas em outras linhas" para "base +
  todas as unidades de `UNIDADE_OPTIONS` exceto a própria linha" — mais itens na
  mesma lista, mesmo estilo de `<option>` nativo herdado do `Select.jsx`
- Ordem das opções: manter "(base)" sempre primeiro (já é o padrão), demais unidades
  na ordem de `UNIDADE_OPTIONS` (UN, PT, CX, KG, L, M, filtrando base e própria linha)
  — ordem estável e previsível, sem necessidade de ordenação alfabética adicional

**Toast de erro de ciclo (RF-02 — reaproveita componente existente):**
- Nenhum componente novo — usar `showToast(mensagem, 'error')` já implementado
  (linha 90-93 de `Produtos.jsx`)
- Estilo herdado: `fixed top-4 right-4 z-50 max-w-sm px-4 py-3 rounded-lg shadow-lg
  text-sm font-medium text-white bg-red-600`, `whitespace-pre-line break-words`,
  timeout 7000ms
- Texto da mensagem: usar literalmente o `error.message` lançado por
  `ordenarConversoesPorDependencia` (ex.: `"Conversões em ciclo: CX → PT → CX.
  Corrija antes de salvar."`) — sem ícone adicional, sem cor diferente da já usada
  para erro

**Mobile-first (375px):**
- Já coberto pelo breakpoint `sm:` existente na linha de conversão — abaixo de 640px,
  os 3 campos + botão remover empilham em coluna (`flex-col`), acima disso viram
  linha (`sm:flex-row sm:items-end`). Nenhum ajuste necessário: a mudança é só na
  quantidade de `<option>` dentro do `<select>` nativo, que não afeta layout em
  nenhuma largura de tela.
- Toast `fixed top-4 right-4 max-w-sm` já é seguro em 375px (não ultrapassa a
  viewport, `max-w-sm` = 24rem com margem via `right-4`).

---

## Componentes reutilizados (nenhum novo)

| Componente | Origem | Uso nesta manutenção |
|---|---|---|
| `Select` | `components/ui/Select.jsx` | Campo "Converte para" — mesma instância, só mais `options` |
| Toast inline (`showToast`) | Já existente em `Produtos.jsx` (padrão replicado em outras páginas) | Mensagem de erro de ciclo (RF-02) |
| `Plus`, `Trash2`, `ArrowRight` (ícones) | `lucide-react`, já importados em `Produtos.jsx` | Inalterados — nenhum ícone novo necessário |

Nenhum componente novo criado. Nenhum ícone novo. Nenhum token de cor/espaçamento
novo adicionado ao `tailwind.config.js`.

---

## Passagem de bastão

```
✅ Especificação UI concluída — UidCore (Manutenção #40)
   Telas analisadas: 1 (Produtos.jsx — Modal de Produto, seção
   Conversões de Unidade)
   Componentes reutilizados: 2 (Select.jsx, toast inline showToast)
   Novos padrões visuais: 0 — mudança é puramente de dados
   (options do Select) e de ordem de chamadas HTTP (handleSubmit),
   sem impacto em layout, cor, espaçamento ou ícone

📁 Arquivo: Especificacao_UI_Hotfix.md (neste diretório)

➡️ Loom lê Especificacao_Hotfix.md + Especificacao_UI_Hotfix.md antes
   de implementar RF-01/RF-02/RF-03 — nenhuma mudança visual a
   implementar além da lógica já detalhada na Especificação técnica
   do Analista.
```
