# Especificação UI Hotfix — UidCore (OS #7)

**Manutenção #55 — Módulo Agendamento: visualização em Calendário mensal**

Data: 2026-08-26
Baseado em: `Especificacao_Hotfix.md` (Analista, Manutenção #55)

---

## Design System do Projeto (referência)

- **Modo:** Padrão Uid — dark mode como default (Manutenção #31), sem marca própria de cliente
- **Cores primárias:** `primary-600`/`violet-600` (ação, botão "Nova Agenda"/"Novo Compromisso", aba ativa, foco de input), `navy-950/900/800/700/600` (superfícies, do fundo ao elemento mais elevado)
- **Cores de fundo:** `bg-white` / `dark:bg-navy-800` (cards), `dark:bg-navy-900` (fundo de página/header de tabela)
- **Bordas:** `border-gray-200` / `dark:border-navy-600` (cards), `dark:border-navy-700` (divisores internos)
- **Fonte:** Plus Jakarta Sans (títulos) + DM Sans (corpo) — já globais, nenhuma ação nova
- **BorderRadius padrão:** `rounded-xl`/`rounded-2xl` (cards, modal), `rounded-lg` (botões, células do grid, inputs), `rounded-full` (badges, indicadores de agenda)
- **Padrão de aba (TABS):** já existente em `Agendamento.jsx` — botão ativo `bg-primary-600 text-white dark:bg-violet-600`, inativo `bg-white text-gray-600 border border-gray-200 dark:bg-navy-800 dark:text-slate-400 dark:border-navy-600`. A aba "Calendário" segue **exatamente** esse padrão, sem nenhuma classe nova no array `TABS`.
- **Padrão de badge de status:** `span` inline `text-xs rounded-full px-2 py-0.5 font-medium`, classe única `bg-primary-50 text-primary-700 dark:bg-violet-900/30 dark:text-violet-300` — é o mesmo bloco já produzido por `ResourceCrud.renderCell` quando `col.badge === true` (ver `ResourceCrud.jsx`, bloco `if (col.badge)`). **Não** criar um `STATUS_BADGES` colorido por status (padrão que existe em `Vendas.jsx`, mas RF04 da Especificação de Hotfix pede explicitamente "mesmo badge de status já usado em ResourceCrud.renderCell" — é esse span violeta único, não um mapa de cores novo).
- **Padrão de card:** `Card.jsx` existente — `rounded-xl border border-gray-200 dark:border-navy-600 dark:bg-navy-800`, conteúdo em `px-6 py-4`
- **Ícones:** projeto não usa lucide-react nem shadcn — módulo Agendamento usa emojis (`📅`, `🗓️`) como o resto do projeto fora da Sidebar. Nenhum ícone novo necessário nesta manutenção (nenhuma seta de biblioteca — usar caracteres `‹ ›` como texto, já sugerido pelo próprio Analista em RF02).
- **Mobile-first:** grid responsivo, `space-y-4` no container raiz — **nunca** `overflow-hidden` na raiz (regra global do projeto)
- **Cor de dado do usuário (exceção legítima a token):** `Agenda.cor` (hex livre) é aplicada via `style={{ backgroundColor: agenda.cor }}` — única exceção a cor arbitrária fora dos tokens Tailwind, conforme RNF03 da Especificação de Hotfix.

---

## Especificação Visual por Tela

### 1. Agendamento.jsx — nova aba "Calendário"

**Mudança:**
```jsx
const TABS = [
  { key: 'compromissos', label: 'Compromissos' },
  { key: 'agendas', label: 'Agendas' },
  { key: 'calendario', label: 'Calendário' },
]
...
{tab === 'calendario' && <CalendarioTab />}
```
- Zero classe nova — o botão da aba "Calendário" herda o mesmo `className` condicional já usado nas outras duas (bloco `.map((t) => ...)` em `Agendamento.jsx`), sem nenhum branch visual extra.

---

### 2. CalendarioTab — Cabeçalho + navegação de mês (RF02)

**Layout:**
```jsx
<div className="flex items-center justify-between gap-3 mb-4">
  <button className="px-3 py-1.5 text-sm font-medium rounded-lg
    bg-white text-gray-600 hover:bg-gray-100 border border-gray-200
    dark:bg-navy-800 dark:text-slate-400 dark:hover:bg-navy-700 dark:border-navy-600">
    ‹ Mês anterior
  </button>
  <h2 className="text-base font-semibold text-gray-900 dark:text-slate-100 capitalize">
    Agosto 2026
  </h2>
  <button className="px-3 py-1.5 text-sm font-medium rounded-lg
    bg-white text-gray-600 hover:bg-gray-100 border border-gray-200
    dark:bg-navy-800 dark:text-slate-400 dark:hover:bg-navy-700 dark:border-navy-600">
    Mês seguinte ›
  </button>
</div>
```
- Mesmos tokens do botão "inativo" das TABS (reuso 1:1, zero classe nova) — reforça que é navegação, não uma ação primária.
- Label do mês: formatar manualmente `"{Mês} {Ano}"` (ex.: "Agosto 2026") capitalizando a primeira letra — `toLocaleDateString('pt-BR', { month: 'long', year: 'numeric' })` retorna "agosto de 2026", então montar a string à mão em vez de usar o resultado bruto.
- Mobile (375px): mesmo `flex items-center justify-between`, mas texto dos botões reduz para só `‹`/`›` abaixo de `sm:` (ex.: `<span className="hidden sm:inline">Mês anterior</span><span className="sm:hidden">‹</span>`) — evita quebra de linha em tela estreita.
- Enquanto `loading === true`, mostrar um texto discreto no lugar do grid, mesmo padrão textual já usado em `ResourceCrud` (`flex justify-center py-12 text-gray-400 dark:text-slate-500 text-sm`, texto "Carregando...").

---

### 3. Grid mensal — células de dia (RF02, RF03, RF04, RF06)

**Estrutura:**
```jsx
<div className="grid grid-cols-7 gap-1 sm:gap-2">
  {/* cabeçalho dia da semana */}
  {['Dom','Seg','Ter','Qua','Qui','Sex','Sáb'].map((d) => (
    <div key={d} className="text-center text-xs font-semibold text-gray-400 dark:text-slate-500 pb-1">{d}</div>
  ))}
  {/* células vazias de preenchimento antes do dia 1 do mês */}
  {/* uma célula por dia do mês */}
</div>
```
- Cabeçalho de dia da semana: abreviação de 3 letras, `text-xs font-semibold text-gray-400 dark:text-slate-500`, sem fundo, `text-center`.
- Células de preenchimento (antes do dia 1, para alinhar no dia da semana correto): `<div />` vazio, sem borda, sem conteúdo — só ocupa a posição no grid.

**Célula de dia (estado base):**
```jsx
<button
  className="aspect-square sm:aspect-auto sm:h-20 flex flex-col items-start p-1.5 sm:p-2
    rounded-lg border text-left transition-colors
    bg-white border-gray-200 hover:bg-gray-50
    dark:bg-navy-800 dark:border-navy-700 dark:hover:bg-navy-700/60"
>
  <span className="text-xs sm:text-sm font-medium text-gray-700 dark:text-slate-300">
    {diaNumero}
  </span>
  <div className="flex flex-wrap gap-0.5 mt-auto">
    {/* indicadores de agenda, ver abaixo */}
  </div>
</button>
```
- Base: `rounded-lg border bg-white border-gray-200 dark:bg-navy-800 dark:border-navy-700`, mesmo par claro/escuro de `Card.jsx`, mas com `border` sempre visível (não só `border-b` como header de card) — a célula precisa se destacar como item clicável de grid.
- `aspect-square` no mobile (célula quadrada, compacta) → `sm:h-20 sm:aspect-auto` no desktop (célula mais alta, permitindo mostrar mais indicadores).

**Estado "dia de hoje" (RF06) — independente da seleção:**
```
ring-2 ring-primary-500 dark:ring-violet-500
```
- Adiciona `ring-2 ring-primary-500 dark:ring-violet-500` (sem alterar `border`/`background`) — contorno fino ao redor da célula do dia atual, sempre visível, mesmo quando não está selecionado.

**Estado "dia selecionado" (RF04):**
```
bg-primary-50 border-primary-300 dark:bg-violet-900/20 dark:border-violet-600
```
- Preenchimento leve + borda mais forte na cor de destaque do projeto (mesma família do botão primário) — substitui `bg-white border-gray-200` quando `diaSelecionado === dataDaCelula`.

**Hoje E selecionado ao mesmo tempo (RF06 exige diferenciação clara mesmo nesse caso):**
- Aplicar os dois efeitos simultaneamente: `bg-primary-50 border-primary-300 ring-2 ring-primary-500` (light) / `dark:bg-violet-900/20 dark:border-violet-600 dark:ring-violet-500` (dark) — o preenchimento entrega "selecionado" e o `ring` entrega "hoje", sobrepostos sem conflito visual (o `ring` do Tailwind é um box-shadow, não é encoberto pelo `background`).

**Indicadores de compromisso por Agenda (RF03, RN03):**
```jsx
<span
  key={agendaId}
  className={`w-1.5 h-1.5 rounded-full shrink-0 ${!agendaCor ? 'bg-gray-400 dark:bg-slate-500' : ''}`}
  style={agendaCor ? { backgroundColor: agendaCor } : undefined}
/>
```
- Um ponto (`w-1.5 h-1.5 rounded-full`) por Agenda **distinta** presente no dia — não um ponto por compromisso (vários compromissos da mesma Agenda no mesmo dia = 1 ponto só, conforme RF03: "um indicador por Agenda distinta presente naquele dia").
- Cor do ponto: `style={{ backgroundColor: agenda.cor }}` quando a Agenda existe; **compromisso sem Agenda (RN03)** usa token neutro do projeto — `bg-gray-400 dark:bg-slate-500` (mesmo tom neutro já usado em textos secundários/estado "Não" do `ResourceCrud`), nunca cor arbitrária.
- Limite de indicadores visíveis por célula: **4 pontos** no desktop (`sm:h-20` comporta 2 linhas de até 4-5 pontos de `w-1.5`), **3 pontos** no mobile (célula `aspect-square` menor). Acima do limite, substituir o(s) ponto(s) excedente(s) por um texto `+N`:
  ```jsx
  <span className="text-[10px] leading-none text-gray-400 dark:text-slate-500 font-medium">+{extra}</span>
  ```
- Célula sem nenhum compromisso: `<div className="flex flex-wrap gap-0.5 mt-auto" />` vazia — sem placeholder, sem "traço", só ausência de pontos (mantém a grade limpa).

---

### 4. Lista de compromissos do dia selecionado (RF04, abaixo do grid)

**Container:**
```jsx
<Card className="mt-4">
  <div className="flex items-center justify-between mb-3">
    <h3 className="text-sm font-semibold text-gray-700 dark:text-slate-200">
      {formatarDataLonga(diaSelecionado)} {/* ex.: "26 de agosto de 2026" */}
    </h3>
    <span className="text-xs text-gray-400 dark:text-slate-500">
      {compromissosDoDia.length} compromisso(s)
    </span>
  </div>
  {/* lista de cards de compromisso, ou estado vazio */}
</Card>
```
- Renderiza **só** quando `diaSelecionado !== null` (toggle: clicar de novo no mesmo dia → `diaSelecionado = null` → a seção inteira some, sem animação, mesmo padrão binário já usado no projeto para blocos condicionais).
- Usa `Card.jsx` (wrapper padrão do projeto), sem `title` prop — cabeçalho customizado (data + contador) montado manualmente.
- Estado vazio (dia selecionado sem compromisso — pode acontecer se o usuário clicar numa célula sem indicador): `<p className="text-sm text-gray-400 dark:text-slate-500 py-4 text-center">Nenhum compromisso neste dia.</p>`, mesmo tom textual do `emptyText` do `ResourceCrud`.

**Card de compromisso na lista (RF04, RF05):**
```jsx
<button
  onClick={() => setCompromissoEditando(compromisso)}
  className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left
    hover:bg-gray-50 dark:hover:bg-navy-700/60 transition-colors
    border-b border-gray-100 dark:border-navy-700 last:border-b-0"
>
  <span
    className={`w-1.5 h-1.5 rounded-full shrink-0 ${!agendaCor ? 'bg-gray-400 dark:bg-slate-500' : ''}`}
    style={agendaCor ? { backgroundColor: agendaCor } : undefined}
  />
  <div className="flex-1 min-w-0">
    <p className="text-sm font-medium text-gray-900 dark:text-slate-100 truncate">
      {compromisso.titulo}
    </p>
    <p className="text-xs text-gray-400 dark:text-slate-500">
      {horaInicio}{compromisso.fim ? `–${horaFim}` : ''}
    </p>
  </div>
  <span className="text-xs bg-primary-50 text-primary-700 rounded-full px-2 py-0.5 font-medium
    dark:bg-violet-900/30 dark:text-violet-300 shrink-0">
    {compromisso.status_label}
  </span>
</button>
```
- Linha inteira é o alvo de clique (RF05 — "clicar em um Compromisso... a partir da lista expandida") — `<button>` full width, não só um ícone/link, para acerto de clique confortável em mobile.
- Ponto de cor da Agenda reaparece aqui (mesma lógica de cor/neutro de RN03), reforçando visualmente de qual Agenda é o compromisso mesmo dentro da lista.
- Horário formatado `HH:mm–HH:mm` a partir de `inicio`/`fim`; se `fim` for nulo, exibir só `HH:mm` de início, sem traço solto.
- Badge de status: **exatamente** o mesmo span violeta do `ResourceCrud.renderCell` (`col.badge`), reforçando RF04 ("mesmo badge de status já usado na tabela de Compromissos") — não um `STATUS_BADGES` colorido por status.
- Separador entre itens: `border-b border-gray-100 dark:border-navy-700 last:border-b-0` (lista "flat", sem gap entre itens — mais compacta que um grid de cards, adequada a uma lista potencialmente longa dentro de um `Card` já posicionado abaixo do grid mensal).

---

### 5. Modal de edição reaproveitado (RF05, RF07, §7.2 da Especificação de Hotfix)

- **Nenhum modal novo é desenhado aqui** — é o mesmo `Modal.jsx` + formulário já usado pela aba "Compromissos" (`rounded-2xl`, `max-w-2xl`, mesmos campos: título, agenda, cliente, início, fim, local, status, descrição, observações).
- Independente de o Loom optar pela abordagem de prop (`externalEditItem`/`onExternalEditClose`) ou de `ref`/`useImperativeHandle` (§7.2 da Especificação de Hotfix deixa as duas em aberto), o resultado visual é idêntico: o mesmo modal de edição de Compromisso que já existe, sem nenhuma classe ou layout novo.
- Ao fechar o modal (sucesso ou cancelar), a seção 4 (lista do dia) e os indicadores da seção 3 (grid) devem refletir o estado atualizado sem reload — comportamento de dado (RF07), não de UI; nenhuma transição visual especial é necessária (sem skeleton/spinner extra — o `loading` do fetch do mês já cobre o intervalo de refetch).

---

### 6. Responsividade — resumo mobile-first (RNF06)

| Elemento | Mobile (< 640px) | Desktop (≥ 640px) |
|---|---|---|
| Navegação de mês | Botões só com `‹`/`›` | Botões com texto completo "Mês anterior"/"Mês seguinte ›" |
| Célula de dia | `aspect-square`, até 3 indicadores + "+N" | `h-20`, até 4 indicadores + "+N" |
| Cabeçalho dia da semana | 3 letras (`Dom`, `Seg`...) | mesmo (não precisa de versão longa) |
| Lista do dia selecionado | Mesma largura do grid (`w-full`), itens empilhados | mesma estrutura, sem coluna dupla |
| Grid geral | `grid-cols-7 gap-1` (gap reduzido) | `grid-cols-7 gap-2` |

- Nenhum componente muda de eixo (sem "cards empilhados vs. tabela" como em outras telas) — o calendário é sempre grid 7 colunas; só o conteúdo interno da célula e o espaçamento reduzem.

---

### 7. Componentes existentes reutilizados

| Componente | Uso no Calendário |
|---|---|
| `Card.jsx` | Wrapper da lista de compromissos do dia selecionado (seção 4) |
| `Modal.jsx` | Modal de edição de Compromisso (reaproveitado via ResourceCrud, seção 5) |
| `ResourceCrud.jsx` (formulário interno) | Fonte do modal de edição — nenhum formulário duplicado |
| Badge inline `bg-primary-50 text-primary-700 dark:bg-violet-900/30 dark:text-violet-300` | Badge de status em cada compromisso da lista (seção 4), idêntico ao já usado em `ResourceCrud.renderCell` |
| Estilo de botão "aba inativa" (`Agendamento.jsx`, array `TABS`) | Botões de navegação de mês (seção 2) |

**Nenhum componente novo de UI é necessário** — `CalendarioTab.jsx` é 100% composição de padrões já existentes no projeto (grid Tailwind + Card + Modal reaproveitado), conforme RNF03/RNF04 da Especificação de Hotfix (proibido introduzir lib de calendário, shadcn ou paleta nova).

---

## Passagem de bastão

```
✅ Especificação UI concluída — UidCore (Manutenção #55)
   Telas analisadas: 1 (CalendarioTab — grid mensal + lista do dia + reuso de modal)
   Componentes reutilizados: Card, Modal, badge inline do ResourceCrud,
     estilo de aba/botão de Agendamento.jsx
   Novos padrões: nenhum — apenas composição de tokens e componentes já existentes

📁 Arquivo: Especificacao_UI_Hotfix.md (raiz do projeto, sobrescrevendo a versão da Manutenção #54)

➡️ Loom lê Especificacao_Hotfix.md + Especificacao_UI_Hotfix.md
   antes de implementar CalendarioTab.jsx e a extensão retrocompatível do ResourceCrud (§7.2)
```
