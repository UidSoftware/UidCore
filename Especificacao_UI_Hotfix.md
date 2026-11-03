# Especificação UI Hotfix — UidCore (Manutenção #92)

## Modo

**MODO HOTFIX.** Três frentes dentro do módulo **Agendamento já existente**
(`frontend/src/pages/Agendamento.jsx`), nenhuma tela nova de ponta a ponta,
nenhuma mudança de identidade visual/paleta/tipografia/design system. Tudo
reaproveita os componentes e tokens navy/violet já em produção (confirmado
no `Especificacao_Hotfix.md` seção 8 — "não requer novo design_system nem
ADR de arquitetura").

Lido antes de escrever esta especificação: `Especificacao_Hotfix.md`
(Manutenção #92, completo — RF-01 a RF-14, RN-01 a RN-07, seções 4 e 5),
`frontend/src/pages/Agendamento.jsx` (completo, 1184 linhas — `HorariosTab`
linhas 48-406, `PendentesTab` linhas 412-609, `CompromissosTab`/
`CompromissosResourceCrud` linhas 615-1098, componente principal + `TABS`
linhas 1104-1183), `frontend/src/pages/pdv/FrenteDeCaixa.jsx` (referência
de padrão de dropdown de busca com badge inline, já citado nas
Manutenções #91/#92 anteriores), `components/ui/{Button, Select, Input,
Modal}.jsx`.

**Resumo das 3 frentes (mapeadas às telas que o Loom vai tocar):**

| Frente | O que muda na UI | Tela afetada |
|---|---|---|
| 1 — Profissional vem do RH | Dropdown de Profissional passa a buscar em `rh/colaboradores` em vez de `accounts/usuarios` | Aba **Agendas** (form Nova/Editar Agenda, via `ResourceCrud`) |
| 2 — Vagas visíveis + trava no update | Reordenar Data→Horário, mostrar "X/Y vagas" no dropdown, opção lotada desabilitada | Aba **Compromissos** (modal Novo/Editar Compromisso) |
| 3 — Pendentes explicado + origem/canal | Texto explicativo novo, coluna Origem na tabela, badge de canal (opcional) | Aba **Pendentes** |

---

## Design System do Projeto (referência — não alterado)

- **Cores primárias:** `primary-600` (light) / `violet-600` (dark) — botão
  de ação, aba ativa, foco de input/select. Hover: `primary-700`/
  `violet-700` (light), `violet-700` (dark).
- **Cores de fundo:** `white` (light) / `navy-800` (dark) — cards, modal,
  dropdown nativo; `gray-50`/`navy-900` — header de tabela; `navy-600`/
  `navy-700` — borda de card/divisor/linha de tabela; `navy-500` — borda
  de input/select.
- **Texto:** `text-gray-900`/`text-gray-600`/`text-gray-500`/`text-gray-400`
  (light); `text-slate-100`/`text-slate-300`/`text-slate-400`/
  `text-slate-500` (dark).
- **Feedback (badges `rounded-full`, já usados em `Agendamento.jsx`):**
  - Violeta (`bg-violet-400/15 text-violet-400 border border-violet-400/30`)
    — já usado para "Público" (horário público, origem do compromisso).
    Reaproveitar **sem alteração** para o badge de Origem da Frente 3.
  - Cinza navy (`bg-navy-600 text-slate-400` ou `text-slate-500`) — já
    usado para "Privado"/"Interno". Reaproveitar para contraponto de
    Origem se algum dia a aba deixar de filtrar só `PUBLICO`.
  - Âmbar (`bg-amber-400/20 text-amber-400 border border-amber-400/30`) —
    já usado no contador de Pendentes e no aviso de conflito. Não usar
    para vagas/lotado (reservado a "atenção pendente de ação humana").
  - Verde esmeralda (`bg-emerald-400/15 text-emerald-400`) — já usado em
    `vagas_restantes > 0` na coluna Vagas da tabela de Compromissos.
    Reaproveitar **sem alteração** para "vagas disponíveis" no dropdown.
  - Vermelho (`bg-red-400/15 text-red-400`) — já usado em
    `vagas_restantes <= 0` (horário lotado) na mesma coluna. Reaproveitar
    para o estado "Lotado" em qualquer lugar novo que precise indicar
    isso.
- **Fonte:** Plus Jakarta Sans (display) + DM Sans (body) — já carregadas
  globalmente, não tocar.
- **BorderRadius:** `rounded-lg` (inputs, selects, botões, modal interno),
  `rounded-xl` (card de tabela, `rounded-2xl` no `Modal.jsx` — não tocar),
  `rounded-full` (todo badge/pill, incluindo os novos desta manutenção).
- **Dark mode:** classe `dark` no `<html>`, toggle já existente — todo
  elemento novo precisa das duas variantes (light + `dark:`), seguindo
  exatamente o padrão já presente em cada trecho tocado (ex.: tabela de
  Pendentes já é 100% dark-token puro — `text-slate-*`/`bg-navy-*` sem
  variante light — manter esse mesmo estilo ali; o modal de Compromisso
  mistura light+dark — manter os dois ali também, sem unificar de
  propósito nesta manutenção).
- **Ícones:** `lucide-react`, já importados em `Agendamento.jsx`: `Clock,
  CalendarDays, Users, Plus, Pencil, CheckCircle, X, RefreshCw,
  CalendarCheck, Shield, Globe, AlertTriangle, User`. Emoji só na Sidebar
  (regra global do CLAUDE.md) — dentro de telas/formulários, ícone é
  sempre Lucide. Dois ícones novos a importar nesta manutenção (Frente 3,
  só se RF-14 entrar): `Instagram`, `MessageCircle` (WhatsApp).

---

## Especificação Visual por Tela

### Frente 1 — Aba **Agendas** (form Nova/Editar Agenda via `ResourceCrud`)

**Arquivo:** `Agendamento.jsx`, bloco `tab === 'agendas'`, linhas 1140-1172.

**Mudança — apenas a origem dos dados do campo, zero mudança de layout:**

```js
{
  name: 'profissional',
  label: 'Profissional responsável',
  type: 'select-remote',
  endpoint: 'rh/colaboradores',   // era: 'accounts/usuarios'
  labelField: 'nome',             // era: 'nome_completo'
  params: {},                     // era: { perfil: 'PROFISSIONAL' }
  // remover por completo a prop filterOptions — o backend já filtra
  // is_active=True no queryset do campo (RN-02); não há mais perfil para
  // filtrar no frontend.
},
```

- **Posição do campo:** mesma (2º campo do form, entre "Nome" e "Cor").
- **Label:** mantém "Profissional responsável" — sem mudança de texto,
  já é claro.
- **Placeholder/empty state:** mesmo comportamento padrão do
  `select-remote` (ver `ResourceCrud.jsx` — não precisa de ajuste).
- **Coluna na tabela de Agendas** (`profissional_nome`): zero mudança —
  continua mesma posição/rótulo, só o dado por trás muda (`Colaborador.nome`
  em vez de `User.nome_completo`).
- **Nenhum ícone novo necessário aqui** — o campo já é um `select-remote`
  puro sem ícone ao lado do label, igual aos demais campos do form de
  Agenda (`Nome`, `Cor`). Não introduzir ícone onde não havia, por
  consistência com os outros campos do mesmo formulário.
- **RN-01 (não visual, mas relevante pro Loom saber):** o endpoint
  `rh/colaboradores` passa a responder `200` em `GET` para qualquer
  usuário autenticado (fix de permissão no backend, Forge) — o
  `select-remote` não precisa de nenhum tratamento especial de erro 403
  diferente do que já tem hoje.

---

### Frente 2 — Aba **Compromissos** (modal Novo/Editar Compromisso)

**Arquivo:** `Agendamento.jsx`, componente `CompromissosResourceCrud`,
linhas 690-1098. Bloco a reescrever: linhas 958-997 (hoje "Horário
Disponível" + "Data do Horário", nessa ordem) + a lógica de
`handleChange`/`carregarHorariosDaAgenda` (linhas 631-641 e 760-776).

#### 2.1 Reordenação dos campos — Data antes de Horário

Layout atual (`grid grid-cols-1 sm:grid-cols-2 gap-4`, mantém a mesma
grid de 2 colunas em telas ≥ 640px, 1 coluna em mobile):

```
┌─────────────────────────┬──────────────────────────┐
│ 📅 Data do Compromisso   │ 🕐 Horário Disponível      │
│ (type="date")            │ (select, disabled até      │
│ habilitado após Agenda   │  Data preenchida)          │
└─────────────────────────┴──────────────────────────┘
```

- **Campo 1 — Data do Compromisso** (`type="date"`, usar `Input`
  component, igual ao já usado em "Data do Horário" hoje — mesmo visual,
  só muda a ordem e o nome interno do estado):
  - `label="Data do Compromisso *"`
  - Ícone: `CalendarDays` (já importado) ao lado do label, mesmo padrão
    do label "Horário Disponível" atual (que usa `<Clock size={14} />`
    antes do texto, linhas 962-964) — aplicar o mesmo padrão aqui:
    ```jsx
    <label className="text-sm font-medium text-gray-700 dark:text-slate-300 flex items-center gap-1.5 mb-1">
      <CalendarDays size={14} />
      Data do Compromisso *
    </label>
    ```
  - `disabled` enquanto `!form.agenda` (mesma regra de habilitação que
    "Horário" tem hoje em relação à Agenda).
  - Texto de ajuda abaixo (`text-xs text-slate-500 mt-1`): "Selecione a
    agenda primeiro" quando desabilitado; some quando habilitado (não
    precisa de texto de ajuda permanente).

- **Campo 2 — Horário Disponível** (select nativo, mesmo elemento HTML
  já usado hoje — não trocar por `Select` component, porque precisa de
  `disabled` por `<option>`, que o `Select.jsx` genérico do projeto não
  suporta):
  - `label="Horário Disponível *"` com ícone `Clock` (mantém, só ajusta
    o `*` de obrigatório se for o caso — hoje o campo é opcional
    "agendamento avulso"; manter opcional, sem `*`).
  - `disabled` enquanto `!form.data_horario` (antes era `!form.agenda`
    — agora a dependência avança um passo).
  - Texto de ajuda: "Selecione a data primeiro" quando desabilitado;
    quando habilitado, manter o texto já existente "Vincula este
    compromisso a um horário com controle de vagas".
  - **Rótulo de cada `<option>`** (RF-07, formato exato pedido pelo
    Analista):
    ```
    "{hora_inicio} — {servico || 'Sem rótulo'} ({vagas_ocupadas}/{vagas} vagas)"
    ```
    Exemplo real: `"09:00 — Corte (1/3 vagas)"`. Quando lotado:
    `"09:00 — Corte (3/3 vagas) (Lotado)"` **com o atributo `disabled`**
    no `<option>` — o navegador já aplica o estilo nativo de opção
    desabilitada (cinza/acinzentado), não precisa de CSS customizado:
    ```jsx
    {horarioOpts.map((o) => (
      <option key={o.value} value={o.value} disabled={o.disabled}>
        {o.label}
      </option>
    ))}
    ```
  - Opção "Nenhum (agendamento avulso)" continua existindo como primeira
    opção quando `form.data_horario` está preenchido mas o usuário quer
    um compromisso sem vínculo a horário com vaga.

#### 2.2 Fluxo de dados (lógica, para o Loom implementar — não é CSS, mas define o que a tela precisa buscar)

1. Escolher **Agenda** → limpa `data_horario` e `horario` (igual já
   acontece hoje com `agenda` limpando `horario`/`data_horario`, RF-08
   mantém essa direção).
2. Escolher **Data** (com Agenda já escolhida) → calcular dia da semana
   (`new Date(data + 'T00:00:00').getDay()` convertido para a convenção
   0=Segunda do backend — mesma lógica já usada em `formatarDataHora` da
   aba Pendentes para evitar bug de fuso horário, linha 471) → chamar
   `GET /agendamento/horarios-disponiveis/?agenda={id}&dia_semana={d}&ativo=true&data={data}`
   → popular as opções do select de Horário já com `vagas_ocupadas`/
   `vagas_disponiveis`/`lotado` vindos do backend (RF-06 — o backend já
   calcula, o frontend só formata o rótulo e aplica `disabled`).
3. Trocar a **Data** de novo (já com Horário escolhido) → limpa
   `horario` e refaz a busca do passo 2 (RF-08).
4. Submeter → payload igual a hoje (`agenda`, `horario`, `data_horario`),
   sem campo novo. Erro 400 do backend (`{"erro": "Horário sem vagas
   disponíveis."}`) já cai no fluxo de toast existente
   (`extractErrorMessage`, usado em todo o arquivo) — **nenhum componente
   de erro novo é necessário**, só garantir que esse `catch` já cobre
   esse caminho (hoje cobre, via `handleSubmit` linhas 789-820).

#### 2.3 Coluna "Vagas" da tabela de Compromissos (linha 893-912) — sem mudança

Já mostra o badge verde/vermelho com `Users` icon e contagem "ocupados/
total" — **nenhuma alteração visual aqui**, é só o backend (RF-10) que
passa a também bloquear o `PATCH`, então essa coluna continua
refletindo a realidade sem precisar de novo código de tela.

---

### Frente 3 — Aba **Pendentes**

**Arquivo:** `Agendamento.jsx`, componente `PendentesTab`, linhas
412-609.

#### 3.1 Texto explicativo (RF-12)

Trocar o parágrafo atual (linha 508-510):

```diff
- Compromissos recebidos pelo agendamento público aguardando confirmação.
+ Pedidos feitos pelo link público de agendamento (aberto pelo cliente
+ final, sem login) chegam aqui como pendentes — confirme ou recuse cada
+ um. Compromissos criados direto pela equipe (aba Compromissos) não
+ passam por esta etapa.
```

Mesmo elemento (`<p className="text-sm text-slate-400 mt-0.5">`), sem
negrito/markup — o `**...**` do texto do Analista no RF-12 é só para
dar ênfase na redação da spec, não significa `<strong>` na tela (manter
texto corrido simples, consistente com o resto da aba, que não usa
negrito em nenhum parágrafo de apoio).

#### 3.2 Nova coluna "Origem" (RF-13)

Tabela hoje (linha 533): `['Contato', 'Telefone', 'Data', 'Serviço',
'Recebido em', 'Ações']`.

Nova ordem de colunas: `['Contato', 'Telefone', 'Data', 'Serviço',
'Origem', 'Recebido em', 'Ações']` (Origem entre Serviço e Recebido em,
exatamente como pedido no RF-13/seção 4.3).

Célula da coluna Origem — reaproveitar **exatamente** o badge já usado
no modal de edição de Compromisso para `origemAtual === 'PUBLICO'`
(linhas 1042-1046 do arquivo atual), sem inventar estilo novo:

```jsx
<td className="px-4 py-3">
  <span className="bg-violet-400/15 text-violet-400 border border-violet-400/30 rounded-full px-2 py-0.5 text-xs inline-flex items-center gap-1">
    <Globe size={10} />
    Público
  </span>
</td>
```

Como a aba já filtra `origem=PUBLICO` (linha 428), todo item desta
tabela sempre mostra esse mesmo badge — é redundante com o filtro por
design (pedido explícito do cliente, RF-13, "para deixar claro de onde
cada pedido vem" mesmo sendo sempre o mesmo valor hoje).

#### 3.3 Badge de canal (RF-14 — opcional, só se o Forge implementar o campo `canal`)

Se `canal` existir no payload do item (`p.canal`), mostrar um 2º badge
**ao lado** do badge de Origem, na mesma célula (`flex items-center
gap-1.5` envolvendo os dois):

| `canal` | Ícone Lucide | Rótulo | Classes (mesmo padrão de badge do projeto) |
|---|---|---|---|
| `INSTAGRAM` | `Instagram` size={10} | "Instagram" | `bg-pink-400/15 text-pink-400 border border-pink-400/30` |
| `WHATSAPP` | `MessageCircle` size={10} | "WhatsApp" | `bg-emerald-400/15 text-emerald-400 border border-emerald-400/30` |
| `SITE` | `Globe` size={10} | "Site" | `bg-sky-400/15 text-sky-400 border border-sky-400/30` |
| `OUTRO` / vazio (`''`) | — (sem ícone) | "—" | `text-slate-500 text-xs` (texto solto, sem badge/pill — não criar badge para "nada informado") |

```jsx
{p.canal && p.canal !== 'OUTRO' ? (
  <span className={`rounded-full px-2 py-0.5 text-xs inline-flex items-center gap-1 ${CANAL_BADGE[p.canal]}`}>
    {CANAL_ICON[p.canal]}
    {CANAL_LABEL[p.canal]}
  </span>
) : (
  <span className="text-slate-500 text-xs">—</span>
)}
```

(`CANAL_BADGE`/`CANAL_ICON`/`CANAL_LABEL` — pequenos mapas de constante
no topo do arquivo, mesmo padrão já usado para `DIAS_SEMANA_LABELS`.)

Cores novas (`pink-*`, `sky-*`) só para este badge opcional — não reusar
violeta/âmbar/verde/vermelho já comprometidos com outros significados
(Origem, Pendente, Vagas OK, Vagas lotado) para não gerar ambiguidade
visual entre conceitos diferentes na mesma tabela.

**Se RF-14 não for implementado nesta rodada:** pular esta subseção por
completo — a coluna Origem (3.2) é suficiente para fechar CA-07 sozinha.

#### 3.4 Página pública `/agendar/{slug}` (só se RF-14 entrar — `AgendamentoPublico.jsx`)

Fora do escopo de redesenho visual: é só uma leitura de querystring
(`?canal=`) e inclusão no payload do POST, sem nenhum componente visual
novo na página pública (o visitante nunca vê o parâmetro refletido na
tela — é só telemetria interna consumida na aba Pendentes). Nenhuma
especificação de UI adicional necessária aqui.

---

## Componentes existentes reutilizados (nenhum componente novo criado)

| Componente | Uso nesta manutenção |
|---|---|
| `components/ui/Select.jsx` | Form de Agenda (campo Profissional, via `ResourceCrud`/`select-remote` — sem mudança de componente) |
| `components/ui/Input.jsx` | Campo "Data do Compromisso" (type="date", reaproveitando exatamente como "Data do Horário" é usado hoje) |
| `<select>` nativo (não `Select.jsx`) | Campo "Horário Disponível" — mantém elemento nativo por precisar de `disabled` por `<option>` |
| `components/ui/Button.jsx` | Sem mudança — botões Cancelar/Salvar do modal, Confirmar/Recusar da aba Pendentes |
| `components/ui/Modal.jsx` | Sem mudança — mesmo modal `maxW="max-w-2xl"` do Compromisso |
| Badge inline `violet-400/15` (padrão "Público") | Reaproveitado tal e qual para a nova coluna Origem (3.2) |
| `extractErrorMessage` + toast pattern | Sem mudança — já cobre o novo erro 400 de vaga no `perform_update` |

## Ícones Lucide — tabela de referência para o Loom

| Ícone | Contexto | Status |
|---|---|---|
| `CalendarDays` | Label "Data do Compromisso" (novo lugar, ícone já importado) | Reaproveitado |
| `Clock` | Label "Horário Disponível" (mantém posição) | Sem mudança |
| `Users` | Contagem de vagas (coluna da tabela — sem mudança) | Sem mudança |
| `Globe` | Badge "Origem: Público" na aba Pendentes (novo uso, mesmo ícone já usado no modal) | Reaproveitado |
| `Instagram` | Badge de canal Instagram (RF-14, se implementado) | **Novo import** |
| `MessageCircle` | Badge de canal WhatsApp (RF-14, se implementado) | **Novo import** |

Nenhum ícone de "Lotado"/"vaga esgotada" é necessário — o texto
`"(Lotado)"` no rótulo da `<option>` já é suficiente (dentro de um
`<select>` nativo não dá pra colorir texto por opção de forma confiável
entre navegadores, então a comunicação é só textual ali, reforçada pelo
`disabled`).

---

## Padrões mobile-first

- **Modal de Compromisso:** grid `grid-cols-1 sm:grid-cols-2` já existe
  e é mantida — em telas < 640px, Data e Horário ficam um abaixo do
  outro (Data sempre primeiro, reforçando visualmente a nova ordem de
  preenchimento também no mobile).
- **Aba Pendentes:** tabela já é `overflow-x-auto` (linha 529) — a
  coluna Origem nova (e o badge de canal opcional) cabe dentro do scroll
  horizontal existente, sem precisar de tratamento especial; testar em
  375px (iPhone SE) que a tabela não quebra feio com a coluna extra —
  se ficar muito larga, a aba já tem o padrão de scroll horizontal
  resolvendo isso, não precisa virar cards no mobile (diferente de
  outras telas do projeto que já usam esse padrão alternativo — fora de
  escopo mudar isso aqui).
- **Dropdown "Horário Disponível" lotado:** no mobile, o `<select>`
  nativo abre o picker do próprio sistema operacional (iOS/Android) —
  o atributo `disabled` por opção é respeitado nativamente pelos dois,
  sem necessidade de nenhum ajuste condicional por device.

---

## Passagem de bastão

```
✅ Especificação UI concluída — UidCore (Manutenção #92)
   Telas analisadas: 3 (Agendas, Compromissos, Pendentes — todas dentro
   de Agendamento.jsx)
   Componentes reutilizados: 7 (Select, Input, <select> nativo, Button,
   Modal, badge Origem existente, extractErrorMessage/toast)
   Novos padrões: 0 de identidade visual — só 2 ícones novos (Instagram,
   MessageCircle), condicionados a RF-14 ser implementado
```

📁 Arquivo: `Especificacao_UI_Hotfix.md` (neste diretório)

➡️ Loom lê `Especificacao_Hotfix.md` + `Especificacao_UI_Hotfix.md` antes
de implementar o frontend.

BRUSH CONCLUIDO
