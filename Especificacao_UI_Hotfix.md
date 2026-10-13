# Especificação UI Hotfix — Manutenção #65 [NUCLEO 4/5]
## Agenda com capacidade (vagas) + agendamento público

**Sistema:** UidCore
**Data:** 2026-10-13
**Autor:** Brush (MODO HOTFIX)
**Base:** Especificacao_Hotfix.md (Analista, mesma data)

---

## Design System do Projeto (referência)

O UidCore usa dark mode com classe `dark` no root. Paleta definida em
`frontend/tailwind.config.js` (Manutenção #31):

**Superfícies (navy):**
- `navy-950` (`#0a0f1e`) — fundo da aplicação / página pública
- `navy-900` (`#0f1729`) — fundo de cards secundários, slots lotados
- `navy-800` (`#1a2540`) — cards, modais, tabelas, inputs
- `navy-700` (`#232f4d`) — hover de linhas, bordas de separação
- `navy-600` (`#2a3352`) — bordas de cards e inputs
- `navy-500` (`#3d4a73`) — ícones e elementos de apoio

**Interação (violet):**
- `violet-600` (`#7c3aed`) — botão primário (dark), aba ativa
- `violet-700` (`#6d28d9`) — hover de botão primário (dark)
- `violet-500` (`#8b5cf6`) — destaque de link, badge de ação
- `violet-400` (`#a78bfa`) — texto de label ativo, ícone selecionado
- `violet-300` (`#c4b5fd`) — texto de caption sobre fundo escuro

**Texto:**
- `text-slate-100` — texto principal
- `text-slate-400` — texto secundário / labels
- `text-slate-500` — placeholder / muted

**Feedback:**
- Success: `text-emerald-400` / `bg-emerald-400/15`
- Warning: `text-amber-400` / `bg-amber-400/15`
- Error: `text-red-400` / `bg-red-400/15`
- Info: `text-violet-400` / `bg-violet-400/15`

**Fontes:**
- Títulos/labels de peso: `font-sans` (Plus Jakarta Sans), weight 600–800
- Body / dados: `font-body` (DM Sans), weight 400–500

**BorderRadius padrão:**
- Botões: `rounded-lg` (8px)
- Cards: `rounded-xl` (12px)
- Badges: `rounded-full`
- Inputs: `rounded-lg`
- Modal: `rounded-2xl`

**Padrão de card:**
```
bg-white dark:bg-navy-800
border border-gray-200 dark:border-navy-600
rounded-xl
p-6
```

**Padrão de tabela (linha de item):**
```
border-b border-navy-700
hover:bg-navy-700/40
px-4 py-3
text-sm text-slate-200
```

**Componentes reutilizáveis disponíveis:**
- `ResourceCrud` — CRUD genérico com tabela, modal, paginação, toast
- `Modal` — overlay centralizado, `maxW` configurável, dark mode pronto
- `Input` — label + input + error, dark mode pronto
- `Select` — label + select + error, dark mode pronto
- `Button` — variantes primary/secondary/danger, dark mode pronto
- `Card` — superfície com sombra leve
- `Pagination` — paginação paginada
- `AuditFooter` — rodapé created_by/updated_by em modais

---

## Tela 1 — Aba "Horários" dentro de Agendamento.jsx

### Integração na tela existente

`Agendamento.jsx` hoje tem 3 abas: Compromissos | Agendas | Calendário.
Adicionar duas abas novas na sequência:

```
Compromissos | Agendas | Calendário | Horários | Pendentes
```

Padrão visual das abas (já existe, manter idêntico):
```
ativa:   bg-violet-600 text-white rounded-lg px-4 py-2 text-sm font-medium
inativa: bg-navy-800 text-slate-400 hover:bg-navy-700 border border-navy-600
         rounded-lg px-4 py-2 text-sm font-medium
```

Container de abas: `flex gap-1 overflow-x-auto pb-1` — já existe, não alterar.

---

### Layout da aba "Horários"

**Cabeçalho da aba:**
```
┌────────────────────────────────────────────────────────────────┐
│ [Select: Agenda ▼]                   [+ Novo Horário]          │
└────────────────────────────────────────────────────────────────┘
```

- Select de agenda: componente `Select` existente, `w-64`, label "Agenda",
  opções carregadas de `GET /api/v1/agendamento/agendas/`
- Botão "+ Novo Horário": `Button variant="primary"`, ícone `<Plus size={14} />`
- Layout: `flex items-center justify-between gap-4 mb-4`

**Tabela de horários:**

Colunas: Dia | Hora | Duração | Serviço | Vagas | Público | Ativo | Ações

```
┌──────────┬───────┬──────────┬──────────────┬───────┬─────────┬───────┬────────┐
│ Dia      │ Hora  │ Duração  │ Serviço      │ Vagas │ Público │ Ativo │ Ações  │
├──────────┼───────┼──────────┼──────────────┼───────┼─────────┼───────┼────────┤
│ Segunda  │ 09:00 │ 30 min   │ Consulta     │ 2     │ [badge] │ [tog] │ [edit] │
│ Quarta   │ 10:00 │ 60 min   │ Avaliação    │ 5     │ [badge] │ [tog] │ [edit] │
└──────────┴───────┴──────────┴──────────────┴───────┴─────────┴───────┴────────┘
```

Estilos da tabela:
- Container: `overflow-x-auto rounded-xl border border-navy-600`
- `<table>` com `w-full`
- `<thead>`: `bg-navy-900`, células `px-4 py-3 text-xs font-semibold
  text-slate-400 uppercase tracking-wide text-left`
- `<tbody>` linha: `border-b border-navy-700 hover:bg-navy-700/40 transition-colors`
- Células: `px-4 py-3 text-sm text-slate-200`

**Coluna "Dia":** texto por extenso a partir de `dia_semana_label`
(ex: "Segunda"), `text-slate-200 font-medium`

**Coluna "Hora":** `hora_inicio` formatado como "HH:mm", `text-slate-200`

**Coluna "Duração":** `duracao_minutos` + " min" (ex: "30 min"), `text-slate-400`

**Coluna "Serviço":** `servico` ou "—" se vazio, `text-slate-200`

**Coluna "Vagas":** número, `text-slate-200 font-medium`

**Coluna "Público":**
- `publico=true`: badge `bg-violet-400/15 text-violet-400 border border-violet-400/30
  rounded-full px-2 py-0.5 text-xs font-medium` — label "Público"
- `publico=false`: badge `bg-navy-600 text-slate-500 rounded-full px-2 py-0.5
  text-xs font-medium` — label "Privado"

**Coluna "Ativo" (toggle):**
- Toggle inline: `relative inline-flex h-5 w-9 cursor-pointer
  items-center rounded-full transition-colors`
- Ligado: `bg-emerald-500`
- Desligado: `bg-navy-600`
- Bolinha: `absolute h-3.5 w-3.5 rounded-full bg-white shadow transition-transform`
- Ao clicar: PATCH `{ativo: !atual}` para
  `/api/v1/agendamento/horarios-disponiveis/{id}/`
- Toast "Horário ativado" / "Horário desativado" após sucesso

**Coluna "Ações":**
- Ícone `<Pencil size={14} />` — abre modal de edição do horário
- `text-slate-500 hover:text-violet-400 transition-colors cursor-pointer`
- Sem label — apenas ícone, `title="Editar"`

**Estado vazio (sem horários para a agenda selecionada):**
```
ícone <Clock size={32} /> + texto "Nenhum horário cadastrado para esta agenda."
```
Centralizado, `text-slate-500`, padding `py-12`

**Estado inicial (nenhuma agenda selecionada):**
```
ícone <CalendarDays size={32} /> + texto "Selecione uma agenda para ver os horários."
```
Centralizado, `text-slate-500`, padding `py-12`

**Mobile (375px):**
- Tabela com `overflow-x-auto` — scroll horizontal
- Colunas mínimas visíveis sem scroll: Dia, Hora, Vagas, Ativo
- Colunas Duração, Serviço, Público ficam acessíveis via scroll

---

### Modal "Novo / Editar Horário"

Reutilizar componente `Modal` existente com `maxW="max-w-md"`.

**Título:** "Novo Horário" / "Editar Horário"

**Campos (em grid `grid grid-cols-2 gap-4`):**

```
┌─────────────────────┬─────────────────────┐
│ Dia da Semana *     │ Hora de Início *     │
│ [Select ▼]          │ [Input type=time]    │
├─────────────────────┼─────────────────────┤
│ Duração (min) *     │ Vagas *              │
│ [Input type=number] │ [Input type=number]  │
├─────────────────────┴─────────────────────┤
│ Serviço (rótulo livre)                    │
│ [Input placeholder="ex: Consulta 30min"] │
├───────────────────────────────────────────┤
│ [checkbox] Público  [checkbox] Ativo      │
└───────────────────────────────────────────┘
```

Detalhes dos campos:

- **Dia da Semana** (`Select`): opções 0=Segunda, 1=Terça, 2=Quarta,
  3=Quinta, 4=Sexta, 5=Sábado, 6=Domingo. Obrigatório.

- **Hora de Início** (`Input type="time"`): `step="300"` (intervalos de
  5 min), obrigatório.

- **Duração (min)** (`Input type="number"`): `min="5"`, `step="5"`,
  placeholder "30". Obrigatório.

- **Vagas** (`Input type="number"`): `min="1"`, placeholder "1".
  Obrigatório.

- **Serviço**: `Input type="text"`, placeholder "ex: Consulta 30min".
  Opcional.

- **Público**: checkbox inline com label "Horário visível no agendamento
  público". Padrão marcado.

- **Ativo**: checkbox inline com label "Aceitar novos agendamentos".
  Padrão marcado. Hint abaixo (`text-xs text-slate-500`): "Desativar impede
  novos agendamentos, mas não cancela os já existentes."

**Checkboxes estilo:**
```
flex items-center gap-2
input[type=checkbox]: w-4 h-4 rounded accent-violet-600
label: text-sm text-slate-300
```

**Rodapé do modal:**
```
[Cancelar]  [Salvar Horário]
```
- Cancelar: `Button variant="secondary" size="md"`
- Salvar: `Button variant="primary" size="md"`, loading spinner durante POST/PATCH
- Layout: `flex justify-end gap-2 mt-6 pt-4 border-t border-navy-600`

Validação inline: mostrar `error` nas props do `Input` quando campo
obrigatório estiver vazio ao tentar salvar.

---

## Tela 2 — Indicador de vagas na aba Calendário/lista

### Contexto

A aba "Calendário" (`CalendarioTab`) exibe eventos/slots. Quando um slot
está vinculado a um `HorarioDisponivel`, exibir badge de ocupação.

### Badge de vagas

Posição: à direita do nome do serviço/horário, na mesma linha.

**Visual:**
```
[09:00 Consulta]  [2/5]
```

- Badge container: `inline-flex items-center gap-1 rounded-full px-2 py-0.5
  text-xs font-semibold`
- Com vagas disponíveis (`vagas_disponiveis > 0`):
  `bg-emerald-400/15 text-emerald-400`
  ícone: `<Users size={10} />` antes do número
- Lotado (`vagas_disponiveis == 0`):
  `bg-red-400/15 text-red-400`
  ícone: `<Users size={10} />` antes do número

Formato do texto: "{vagas_ocupadas}/{vagas}" (ex: "2/5", "5/5")

Tooltip ao hover: "X vagas disponíveis" ou "Horário lotado" via `title`
HTML nativo.

**Carregamento:**
- Ao montar o dia no calendário, buscar
  `GET /api/v1/agendamento/horarios-disponiveis/{horario_id}/ocupacao/?data={AAAA-MM-DD}`
  para cada slot com `horario` vinculado
- Durante carregamento: exibir `—` em `text-slate-500`
- Badge não bloqueia a renderização do evento (lazy, independente)

**Mobile:** badge permanece visível; o evento fica em card empilhado,
badge na linha abaixo do nome se não couber na mesma linha

---

## Tela 3 — Aba "Pendentes" (painel de confirmação)

### Layout da aba

**Cabeçalho:**
```
┌─────────────────────────────────────────────────────────────────┐
│  Pendentes de Confirmação          [badge contador]             │
│  Compromissos recebidos pelo agendamento público aguardando...  │
└─────────────────────────────────────────────────────────────────┘
```

- Título: `text-lg font-semibold text-slate-100` (Plus Jakarta Sans)
- Subtítulo: `text-sm text-slate-400 mt-0.5`
- Badge contador: `bg-amber-400/20 text-amber-400 border border-amber-400/30
  rounded-full px-2 py-0.5 text-xs font-bold` — ao lado do título
- Layout header: `flex items-start justify-between gap-4 mb-4`

**Tabela de pendentes:**

Colunas: Contato | Telefone | Data | Serviço | Recebido em | Ações

Estilos da tabela: idênticos ao padrão já descrito na Tela 1.

**Coluna "Contato":** `nome_contato`, `text-slate-200 font-medium`.
Se `email_contato` existir: exibir abaixo em `text-xs text-slate-500`

**Coluna "Telefone":** `telefone_contato`, `text-slate-300`

**Coluna "Data":** `data_horario` formatado como "DD/MM/AAAA" +
dia da semana abreviado (ex: "20/10 — Ter"), `text-slate-300`

**Coluna "Serviço":** campo `horario_servico` no serializer do
compromisso (ou "—" se sem horário vinculado), `text-slate-400`

**Coluna "Recebido em":** `created_at` como tempo relativo ("há 2h"),
`text-slate-500 text-xs`

**Coluna "Ações":**

Botão Confirmar:
```
Button variant="secondary" size="sm"
ícone <CheckCircle size={14} /> + label "Confirmar"
classes extras: dark:border-emerald-500/50 dark:text-emerald-400
                dark:hover:bg-emerald-500/10
```

Botão Cancelar (recusar):
```
ícone <X size={14} /> apenas, sem label
text-slate-500 hover:text-red-400 transition-colors
title="Recusar agendamento"
```

Ao clicar "Confirmar": PATCH `{status: "CONFIRMADO"}` —
sucesso: toast verde "Agendamento confirmado.", linha some da tabela.

Ao clicar recusar (X): exibir popover inline de confirmação (sem modal):
```
"Recusar este agendamento?"  [Sim, recusar]  [Não]
```
- Popover: `absolute bg-navy-800 border border-navy-600 rounded-lg
  p-3 shadow-xl z-10 text-sm`
- Posicionado abaixo do ícone X, alinhado à direita

**Estado vazio:**
```
ícone <CalendarCheck size={32} /> + "Nenhum agendamento pendente."
```
Centralizado, `text-slate-500`, padding `py-12`

**Atualização:** ao entrar na aba, buscar
`GET /api/v1/agendamento/compromissos/?origem=PUBLICO&status=AGENDADO`.
Botão de refresh manual `<RefreshCw size={14} />` no canto superior
direito do cabeçalho, `text-slate-500 hover:text-slate-300 cursor-pointer`,
sem label.

**Mobile (375px):** tabela com scroll horizontal; colunas Telefone e
"Recebido em" ficam acessíveis via scroll.

---

## Tela 4 — Formulário de Compromisso ampliado

### Contexto

O formulário de Compromisso está dentro do `ResourceCrud` da aba
"Compromissos". Os novos campos são condicionais e devem ser inseridos
após o campo "Cliente" existente.

### Ordem dos campos no modal (completo)

```
1. Título *
2. Agenda *
3. Profissional
4. Cliente (opcional)
── separador visual ──
5. Horário Disponível (select, opcional)
6. Data do Horário (date, condicional: visível só quando horário selecionado)
── separador visual ──
7. Nome do Contato (condicional: visível quando Cliente vazio)
8. Telefone do Contato (condicional: visível quando Cliente vazio)
9. Email do Contato (condicional: visível quando Cliente vazio)
── separador visual ──
10. Início (datetime-local)
11. Fim (datetime-local)
12. Local
13. Status
14. Descrição
15. Observações
```

Separador visual entre seções:
```html
<div class="border-t border-navy-700 my-3" />
```

**Campo "Horário Disponível" (campo 5):**
- `Select` existente, carregado de
  `GET /api/v1/agendamento/horarios-disponiveis/?agenda={agenda_id}&ativo=true`
- Só habilita quando "Agenda" já estiver selecionada; caso contrário,
  `disabled`, placeholder "Selecione uma agenda primeiro"
- Ao selecionar: auto-preencher `inicio` e `fim` quando `data_horario`
  também estiver preenchida
- Label: "Horário Disponível"
- Hint abaixo (`text-xs text-slate-500`): "Vincula este compromisso a um
  horário com controle de vagas"
- Ícone `<Clock size={14} />` no início do label: `flex items-center gap-1.5`

**Campo "Data do Horário" (campo 6):**
- `Input type="date"`, label "Data do Horário"
- Visível somente quando `horario` estiver selecionado
- Hint (`text-xs text-slate-500`): "Deve ser uma {dia_semana_label}"
- Erro de dia errado: `text-red-400 text-xs` com ícone `<AlertTriangle size={12} />`

**Badge de origem (read-only na edição):**
- INTERNO: `bg-navy-600 text-slate-400 rounded-full px-2 py-0.5 text-xs`
  + ícone `<Shield size={10} />` — "Interno"
- PUBLICO: `bg-violet-400/15 text-violet-400 border border-violet-400/30
  rounded-full px-2 py-0.5 text-xs` + ícone `<Globe size={10} />` — "Público"
- Posição: linha própria acima do campo Status
- Label: `text-xs text-slate-500 mb-1` "Origem"

**Seção de campos de contato (campos 7–9, condicionais):**

Cabeçalho da seção (quando visível):
```
texto: "Dados de contato"
style: text-xs font-semibold text-slate-500 uppercase tracking-wide
       flex items-center gap-1.5
ícone: <User size={12} />
```

- Nome do Contato: `Input`, label "Nome do contato"
- Telefone do Contato: `Input type="tel"`, placeholder "(00) 00000-0000"
- Email do Contato: `Input type="email"`, label "Email (opcional)"

Visibilidade: seção inteira aparece quando `cliente` estiver vazio
(`""` ou `null`). Usar `transition-all duration-150` para entrada suave.

**Toast de aviso de conflito** (quando API retorna `aviso` no 201):
```
style:  bg-amber-400/20 border border-amber-400/40 text-amber-300
        rounded-lg px-4 py-3 flex items-start gap-2.5
ícone:  <AlertTriangle size={16} className="text-amber-400 shrink-0 mt-0.5" />
texto:  "Cliente já possui compromisso no mesmo período."
```
Duração: 6 segundos.

**Mobile (375px):** modal já usa `overflow-y-auto` — campos novos
seguem o scroll vertical natural.

---

## Tela 5 — Página pública `/agendar/{slug}`

Esta página não usa AppLayout, Sidebar nem header de admin. É standalone
com visual limpo, dark mode por padrão (classe `dark` no root da página),
otimizada para 375px.

### Estrutura HTML da página

```
<div class="min-h-screen bg-navy-950 text-slate-100 font-body">
  <header>          Identidade da agenda
  <main>
    <section>       Seletor de data (semana)
    <section>       Lista de horários do dia
    <section>       Formulário de contato (condicional)
    <section>       Estado de sucesso (condicional)
  </main>
  <footer>          Rodapé discreto
</div>
```

### Header

```
┌────────────────────────────────────┐
│  [dot de cor 12px]                 │
│  Nome da Agenda                    │
│  Descrição curta da agenda         │
└────────────────────────────────────┘
```

- Container: `px-4 pt-8 pb-6 max-w-lg mx-auto`
- Dot de cor: `w-3 h-3 rounded-full inline-block mr-2`, cor do campo `cor`
  da agenda (inline style)
- Nome: `text-xl font-bold text-slate-100` (Plus Jakarta Sans 700)
- Descrição: `text-sm text-slate-400 mt-1`
- Separador: `border-b border-navy-700 mt-6`

### Seletor de data (navegação por semana)

```
┌──────────────────────────────────────────────┐
│  [<]   Seg 13    Ter 14    Qua 15  ...  [>]  │
└──────────────────────────────────────────────┘
```

- Container: `px-4 py-4 max-w-lg mx-auto`
- Row de navegação: `flex items-center justify-between gap-2`
- Botões `[<]` e `[>]`:
  `w-8 h-8 rounded-lg bg-navy-800 hover:bg-navy-700 border border-navy-600
  flex items-center justify-center text-slate-400 hover:text-slate-200 transition-colors`
  Ícones: `<ChevronLeft size={16} />` / `<ChevronRight size={16} />`
- Dias da semana (7 botões, scroll horizontal em mobile):
  Container: `flex gap-1.5 overflow-x-auto py-1 flex-1`
  Cada dia inativo:
  ```
  min-w-[52px] flex flex-col items-center gap-0.5 rounded-xl px-2 py-2 text-center
  cursor-pointer transition-colors bg-navy-800 hover:bg-navy-700 border border-navy-600
  texto do dia: text-xs text-slate-500 uppercase tracking-wide
  número:       text-base font-semibold text-slate-300
  ```
  Ativo:
  ```
  bg-violet-600 border-violet-600
  texto do dia: text-xs text-violet-200 uppercase tracking-wide
  número:       text-base font-semibold text-white
  ```
  Hoje: ponto `w-1.5 h-1.5 rounded-full bg-emerald-400 mx-auto mt-0.5`

- Mobile: row de dias com `overflow-x-auto`, 5 dias visíveis (2 via scroll)

### Lista de horários do dia selecionado

**Container:** `px-4 max-w-lg mx-auto space-y-2 mt-2`

**Estado de carregamento:**
```html
<div class="flex justify-center py-8">
  <div class="w-6 h-6 border-2 border-violet-600 border-t-transparent rounded-full animate-spin" />
</div>
```

**Card de slot disponível:**
```
bg-navy-800 hover:bg-violet-700/60 border border-navy-600
hover:border-violet-500 rounded-xl px-4 py-3.5
flex items-center justify-between
cursor-pointer transition-all duration-150

Hora:     text-base font-bold text-slate-100 (Plus Jakarta Sans)
Serviço:  text-sm text-slate-300 mt-0.5
Duração:  text-xs text-slate-500
Vagas:    flex items-center gap-1 text-xs text-emerald-400
          ícone: <Users size={12} />
          texto: "{vagas_disponiveis} vaga(s)"
```

**Slot selecionado (clicado, antes do submit):**
```
bg-violet-700/40 border-violet-500 border-2
(ícone <CheckCircle size={14} className="text-violet-400" /> no canto superior direito)
```

**Card de slot lotado:**
```
bg-navy-900 border border-navy-700 rounded-xl px-4 py-3.5
flex items-center justify-between
opacity-60 cursor-not-allowed

Hora:     text-base font-bold text-slate-500
Serviço:  text-sm text-slate-600
Badge:    bg-red-400/10 text-red-400 rounded-full px-2 py-0.5 text-xs — "Lotado"
```

**Estado sem horários no dia:**
```
ícone <Clock size={28} className="text-slate-600" />
texto "Nenhum horário disponível neste dia."
style: text-center py-8 text-slate-500 text-sm space-y-2
```

### Formulário de contato (aparece ao clicar em slot disponível)

Transição de entrada suave (o Loom decide a implementação — slide-in ou
transition-all, desde que a entrada não seja abrupta).

**Cabeçalho do formulário:**
```
┌──────────────────────────────────────────────────────┐
│  Horário selecionado                    [×]          │
│  Segunda, 20 de outubro • 09:00 • Consulta 30min     │
└──────────────────────────────────────────────────────┘
```

- Container: `bg-navy-800 border border-navy-600 rounded-xl p-4 mt-4`
- Label "Horário selecionado": `text-xs text-slate-500 uppercase tracking-wide
  font-semibold`
- Resumo do slot: `text-sm text-slate-200 mt-1`
- Botão X (desselecionar):
  `text-slate-500 hover:text-slate-300 text-lg leading-none`

**Campos do formulário:**
```
space-y-3 mt-4
```

- Nome (`Input`, `label="Seu nome"`, obrigatório):
  placeholder "Como você prefere ser chamado(a)?"

- Telefone (`Input type="tel"`, `label="Telefone"`, obrigatório):
  placeholder "(00) 00000-0000"
  hint (`text-xs text-slate-500 mt-1`): "Usaremos para confirmar seu agendamento"

- Email (`Input type="email"`, `label="Email (opcional)"`):
  placeholder "seu@email.com"

Os componentes `Input` e `Select` existentes têm dark mode pronto
(`dark:bg-navy-800 dark:border-navy-500 dark:text-slate-100`) — a classe
`dark` no root da página pública ativa esses tokens automaticamente.

**Botão de submissão:**
```
Button variant="primary" size="lg" className="w-full mt-4"
loading={enviando}
ícone à esquerda: <CalendarCheck size={16} />
label: "Confirmar Agendamento"
```

**Nota de privacidade (abaixo do botão):**
```
text-xs text-slate-600 text-center mt-2
"Seus dados são usados apenas para confirmar seu agendamento."
```

**Mobile (375px):** formulário em coluna única, `px-4`, botão full-width.

### Estado de sucesso

Substitui toda a `<main>` após confirmação:

```
ícone <CheckCircle size={56} className="text-emerald-400 mb-4" />

"Agendamento confirmado!"          text-xl font-bold text-slate-100 (Plus Jakarta Sans)
"Segunda, 20 de outubro de 2026"   text-sm text-slate-300 mt-2
"09:00 — Consulta 30min"
"Anote o horário ou tire um print  text-sm text-slate-500 mt-3
 desta tela como comprovante."

[Fazer outro agendamento]          Button variant="secondary" size="md" mt-6
```

Container: `flex flex-col items-center justify-center text-center
px-6 py-16 max-w-sm mx-auto`

Botão "Fazer outro agendamento": ao clicar, resetar todos os estados
(volta ao início, mesma página).

### Exibição de erros (feedback inline)

**Vaga esgotada** (400 `{"erro": "Horário sem vagas disponíveis."}`):
```
bg-red-400/10 border border-red-400/30 rounded-xl px-4 py-3 mt-3
flex items-start gap-2.5
ícone:  <AlertTriangle size={16} className="text-red-400 shrink-0 mt-0.5" />
texto:  "Este horário foi preenchido. Escolha outro."
style:  text-sm text-red-300
```
Ao exibir: desselecionar o slot (volta à lista de horários).

**Throttle** (429):
```
mesmo container visual
texto: "Muitas tentativas. Aguarde antes de tentar novamente."
```

**Erro genérico** (qualquer 4xx/5xx não mapeado):
```
texto: "Algo deu errado. Tente novamente em instantes."
```

Todos os erros exibidos abaixo do botão, sem substituir a UI.

### Rodapé da página pública

```html
<footer class="text-center py-6 mt-8 border-t border-navy-800">
  <p class="text-xs text-slate-700">Powered by UidCore</p>
</footer>
```

### Breakpoints da página pública

| Viewport | Layout |
|---|---|
| 375px (padrão) | Coluna única, header compacto, dias em scroll horizontal |
| 768px | Centralizado max-w-lg, padding lateral maior (px-8) |
| 1024px+ | max-w-xl centrado, seletor de dias cabe todo em linha sem scroll |

---

## Resumo de ícones Lucide (todos os ícones desta spec)

| Contexto | Ícone Lucide | Tamanho |
|---|---|---|
| Botão "+ Novo Horário" | `<Plus />` | 14px |
| Ação editar linha | `<Pencil />` | 14px |
| Ação confirmar pendente | `<CheckCircle />` | 14px |
| Ação recusar pendente | `<X />` | 14px |
| Refresh pendentes | `<RefreshCw />` | 14px |
| Badge vagas (calendário) | `<Users />` | 10px |
| Vagas no card público | `<Users />` | 12px |
| Empty state horários | `<Clock />` | 32px |
| Empty state agenda | `<CalendarDays />` | 32px |
| Empty state pendentes | `<CalendarCheck />` | 32px |
| Botão confirmar agendamento | `<CalendarCheck />` | 16px |
| Label "Horário" no formulário | `<Clock />` | 14px |
| Badge origem Interno | `<Shield />` | 10px |
| Badge origem Público | `<Globe />` | 10px |
| Toast aviso de conflito | `<AlertTriangle />` | 16px |
| Erro inline público | `<AlertTriangle />` | 16px |
| Erro dia errado | `<AlertTriangle />` | 12px |
| Seção dados de contato | `<User />` | 12px |
| Seletor data — anterior | `<ChevronLeft />` | 16px |
| Seletor data — próximo | `<ChevronRight />` | 16px |
| Slot selecionado | `<CheckCircle />` | 14px |
| Sucesso agendamento público | `<CheckCircle />` | 56px |

---

## Componentes existentes a reutilizar (mapa explícito)

| Componente | Onde reutilizar |
|---|---|
| `ResourceCrud` | Aba Horários (com `resource="agendamento/horarios-disponiveis"`) |
| `Modal` | Modal de Novo/Editar Horário (`maxW="max-w-md"`) |
| `Input` | Todos os campos de formulário (interno e público) |
| `Select` | Select de agenda, dia da semana, horário disponível |
| `Button` | Todos os botões (interno e público) |
| `AuditFooter` | Rodapé do modal de Horário |
| `Pagination` | Se lista de horários for paginada |

A aba "Horários" pode usar `ResourceCrud` para o CRUD básico, mas os
campos condicionais do modal de Compromisso ampliado e a lógica de toggle
do campo "Ativo" exigem lógica fora do `ResourceCrud` padrão. O Loom
decide a estratégia (extensão via `rowActions` + modal customizado, ou
componente próprio `HorariosTab.jsx`).

A página pública `AgendamentoPublico.jsx` é standalone — não usa
`AppLayout`, não importa `api` de `../../api/client.js` (que adiciona token),
mas pode reutilizar `Input`, `Button` e `Select` como componentes de UI
pura (sem dependência de auth).

---

## O que NÃO fazer (armadilhas desta tela)

```
❌ NÃO usar overflow-hidden em nenhum container novo — clipa select no Linux
❌ NÃO mostrar dados pessoais de outros agendamentos no frontend público
❌ NÃO usar tokenRef na página pública — não tem autenticação
❌ NÃO bloquear a lista de horários enquanto carrega badges de vaga
   (carregamento do badge é lazy, independente da lista)
❌ NÃO mostrar o formulário de contato antes do usuário clicar em um slot
❌ NÃO substituir o estado de sucesso por um toast simples — o usuário
   precisa da tela de confirmação para tirar print como comprovante
❌ NÃO usar BottomBar na página pública — é fluxo linear, não app admin
❌ NÃO colocar labels nos botões de ação da tabela — ícone + title apenas
❌ NÃO adicionar ícone Lucide no item da Sidebar — é emoji (padrão do projeto)
```

---

## Passagem de bastão

```
Especificacao UI concluida — UidCore [NUCLEO 4/5]
Telas especificadas: 5
  1. Aba "Horários" em Agendamento.jsx (CRUD de HorarioDisponivel)
  2. Badge de vagas "X/Y" na aba Calendário
  3. Aba "Pendentes" (painel de confirmação de origem=PUBLICO)
  4. Formulário de Compromisso ampliado (horário, data, contato, origem)
  5. Página pública /agendar/{slug} (standalone, sem auth, mobile-first 375px)

Componentes reutilizados: ResourceCrud, Modal, Input, Select, Button,
                          AuditFooter, Pagination
Novos componentes:        HorariosTab (ou extensão do ResourceCrud),
                          AgendamentoPublico (standalone, sem tokenRef)
Modo: Padrão Uid (dark mode navy/violet já estabelecido)

Arquivo: /var/www/uidcore/Especificacao_UI_Hotfix.md

-> Loom le Especificacao_Hotfix.md + Especificacao_UI_Hotfix.md
   antes de implementar Agendamento.jsx (abas Horários e Pendentes),
   CalendarioTab (badge de vagas), formulário de Compromisso ampliado
   e AgendamentoPublico.jsx.
```
