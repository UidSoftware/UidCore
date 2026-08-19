# Especificação UI Hotfix — UidCore (Manutenção #45)
**Elaborado por:** Brush (MODO HOTFIX)
**Data:** 2026-08-19
**Referência:** Especificacao_Hotfix.md (Analista) — Manutenção #45

---

## Design System do Projeto (referência — não redefinido aqui)

- **Cores primárias:** `primary-600` (light) / `violet-600` (dark) — botões, tabs ativas, checkbox marcado
- **Cores de fundo:** `white`/`gray-50` (light) / `navy-800`/`navy-900` (dark) — cards, inputs, tabela
- **Bordas:** `gray-300`/`gray-100` (light) / `navy-500`/`navy-600`/`navy-700` (dark)
- **Fonte:** Plus Jakarta Sans (títulos) + DM Sans (corpo) — já configurada globalmente, nenhuma mudança aqui
- **BorderRadius padrão:** `rounded-lg` (inputs, botões) / `rounded-full` (badges/pills)
- **Padrão de card/modal:** `ResourceCrud.jsx` genérico — grid `sm:grid-cols-2`, campos `colSpan2` ocupam a linha inteira

Esta manutenção **não introduz nenhum token novo, cor nova, ícone novo ou componente novo**. É 100% reuso do `ResourceCrud.jsx` já existente. O trabalho do Brush aqui é validar que os **três estados visuais** resultantes da mudança de `hideOnEdit` → `showIf` fazem sentido para o usuário, sem ambiguidade.

---

## Contexto da mudança (resumo funcional, ótica de UI)

Hoje a seção "Criar acesso ao sistema" (divider + checkbox + e-mail + senha)
só aparece ao **criar** um colaborador novo. Passa a aparecer também ao
**editar** um colaborador que ainda não tem acesso (`tem_acesso === false`).
Colaborador que já tem acesso nunca vê essa seção, nem para editar.

Nenhum campo novo visível, nenhum ícone novo, nenhuma tela nova — o único
`field` novo (`tem_acesso`) é **oculto por design** (`showIf: () => false`),
existe só para popular o form ao abrir a edição.

---

## Especificação Visual por Tela

### Rh.jsx — Tab Colaboradores → Modal de Criação/Edição

**Layout geral:** inalterado — modal do `ResourceCrud` já existente, grid
`sm:grid-cols-2`, campos normais ocupam 1 coluna, campos com `colSpan2`
ocupam as 2. Nenhuma mudança de padding, largura de modal ou breakpoint.

**Mobile (375px):** inalterado — grid colapsa para 1 coluna
(`grid-cols-1` implícito fora do `sm:`), campos empilham verticalmente na
ordem declarada em `fields`. A seção de acesso (quando visível) aparece
como bloco full-width no fim do form, igual hoje na criação.

---

#### Estado 1 — Criar colaborador novo

**Sem mudança visual.** `tem_acesso` não existe ainda (colaborador não
foi criado), mas `emptyForm.tem_acesso = false` garante que o predicado
`!form.tem_acesso` seja `true` desde a abertura do modal.

- Divider (`border-t border-gray-100 dark:border-navy-700`) aparece logo
  após "Observações"
- Checkbox "Criar acesso ao sistema" visível, desmarcado por padrão
- Ao marcar: campos "E-mail de acesso" (pré-preenchido com o valor de
  "E-mail" via `onToggle`) e "Senha (opcional)" aparecem abaixo, full-width

#### Estado 2 — Editar colaborador SEM acesso (`tem_acesso === false`) — **novo comportamento**

Idêntico visualmente ao Estado 1, mas agora dentro do fluxo de edição:

- Ao abrir o modal de edição, `ResourceCrud.openEdit` popula
  `form.tem_acesso = false` (vindo da API) → `showIf` de
  `acesso_divider`/`criar_usuario` avalia `true` → seção aparece
- Divider + checkbox "Criar acesso ao sistema" **desmarcado** por padrão
  (diferente da criação, aqui não há razão para vir marcado — é uma ação
  deliberada do usuário ao editar)
- Marcando o checkbox, mesmo comportamento do Estado 1: "E-mail de
  acesso" pré-preenchido com o `email` atual do colaborador (já
  carregado no form pela edição), "Senha (opcional)" com o mesmo
  `helpText` de hoje
- **Nenhum indicador visual adicional necessário** (ex.: badge "sem
  acesso" dentro do modal) — o próprio aparecimento do checkbox
  desmarcado já comunica o estado; a coluna "Acesso" na tabela (badge
  `boolean`, ver abaixo) já informa isso antes de abrir o modal

#### Estado 3 — Editar colaborador COM acesso (`tem_acesso === true`)

- Seção inteira (divider + checkbox + e-mail + senha) **não é
  renderizada** — mesmo resultado visual de hoje (antes garantido por
  `hideOnEdit`, agora por `showIf: (form) => !form.tem_acesso`
  avaliando `false`)
- Nenhum elemento novo no lugar da seção oculta — o form termina em
  "Observações", sem gap visual estranho (comportamento padrão do
  `ResourceCrud`: campo com `showIf` falso simplesmente não renderiza
  nenhum nó, sem espaço reservado)

---

## Coluna "Acesso" na tabela (já existente, não alterada)

Continua usando o badge `boolean` padrão do `ResourceCrud.jsx`
(linhas 184–199 do componente, reaproveitado sem alteração):

- `tem_acesso = true`: badge `bg-primary-50 text-primary-700` (light) /
  `bg-violet-900/30 text-violet-300` (dark), `rounded-full px-2 py-0.5`
- `tem_acesso = false`: badge `bg-gray-100 text-gray-500` (light) /
  `bg-navy-700 text-slate-500` (dark), mesmo `rounded-full`

Essa coluna já é o sinal visual que diferencia, na listagem, quais
colaboradores vão ver a seção de acesso ao abrir a edição (Estado 2) e
quais não vão (Estado 3) — reforça a previsibilidade da mudança sem
precisar de nenhum elemento novo.

---

## Ícones (Lucide React)

**Nenhum ícone novo.** A tab Colaboradores usa `emptyIcon="👔"` (emoji,
padrão já documentado como decisão de projeto — DIV-UI03, não
lucide-react) e o `ResourceCrud` não usa ícone no checkbox/divider.
Nenhuma ação desta manutenção introduz ícone.

---

## Dark Mode — tokens a respeitar (já aplicados, apenas confirmação)

Todos os elementos envolvidos já herdam os tokens corretos do
`ResourceCrud.jsx` — nenhuma classe nova necessária:

| Elemento | Light | Dark |
|---|---|---|
| Divider | `border-gray-100` | `border-navy-700` |
| Checkbox | `border-gray-300 text-primary-600` | `border-navy-500 bg-navy-800 text-violet-600` |
| Input e-mail/senha | `border-gray-300 bg-white text-gray-900` | `border-navy-500 bg-navy-800 text-slate-100` |
| Badge "Acesso: Sim" | `bg-primary-50 text-primary-700` | `bg-violet-900/30 text-violet-300` |
| Badge "Acesso: Não" | `bg-gray-100 text-gray-500` | `bg-navy-700 text-slate-500` |

---

## Espaçamentos

Inalterados — `pt-2 mt-2` no divider, `pt-6` no wrapper do checkbox
(alinha com o baseline do label dos inputs vizinhos), `colSpan2` usando
`sm:col-span-2` do grid pai. Nenhum ajuste de espaçamento é necessário
para os 3 estados descritos — a mecânica de show/hide do `ResourceCrud`
já lida com a ausência de gap quando um campo não renderiza.

---

## Mobile-first

Breakpoint de referência: 375px. Nenhuma mudança de comportamento
responsivo — os 4 campos da seção de acesso já empilham em coluna única
abaixo de `sm:` (640px), igual a todos os outros campos `colSpan2` do
form. Testado mentalmente contra os 3 estados: em nenhum deles há
overflow ou corte, pois a seção é tudo-ou-nada (nunca meio-visível).

---

## O que NÃO foi feito (por escopo)

```
❌ Nenhuma paleta de cores nova
❌ Nenhum componente novo
❌ Nenhum ícone novo (Lucide ou emoji)
❌ Nenhuma mudança de layout do modal ou da tabela
❌ Nenhum badge/indicador novo além do "Acesso" já existente
```

---

## Passagem de bastão

```
✅ Especificação UI concluída — UidCore (Manutenção #45)
   Telas analisadas: 1 (Rh.jsx — tab Colaboradores, modal de criação/edição)
   Componentes reutilizados: 5 (divider, checkbox, input email, input password, badge boolean)
   Novos padrões: 0

📁 Arquivo: Especificacao_UI_Hotfix.md (neste worktree)

➡️ Loom lê Especificacao_Hotfix.md + Especificacao_UI_Hotfix.md
   antes de implementar RF-05/RF-06/RF-07 em Rh.jsx
```
