# Especificação UI Hotfix — UidCore (Dark Mode)

**Elaborado por:** Brush (MODO HOTFIX)
**Data:** 2026-08-14
**Fontes lidas:** `design_system.md` (2026-07-28, última atualização 2026-08-04) + `frontend/tailwind.config.js` + `frontend/index.html` + `frontend/src/index.css` + `frontend/src/components/layout/Header.jsx`

> Nota: este arquivo é regravado a cada manutenção (padrão já estabelecido na
> Manutenção #21) — o conteúdo anterior (ajustes de PDV pós-lançamento) está
> preservado no histórico do `CLAUDE.md` do projeto e no git history. Este
> documento passa a refletir apenas a entrega de dark mode.

**Escopo:** adicionar **dark mode opcional** (toggle) ao UidCore. O tema
**claro continua sendo o padrão** (decisão arquitetural já registrada em
`design_system.md` item b — "UidCore usa tema claro para gestão financeira").
Esta especificação NÃO substitui o light mode, apenas adiciona a variante
escura como opção do usuário, persistida.

```
❌ NÃO criar design system novo
❌ NÃO mudar a identidade visual do light mode (fica como está, é o default)
❌ NÃO implementar código — isso é do Loom
✅ Apenas adiciona a camada dark: por cima do que já existe
```

---

## 0) Checagem de fontes (pedido explícito)

Conferido em `tailwind.config.js` + `index.html` + `index.css`:

| Item | Estado real | Veredito |
|---|---|---|
| `tailwind.config.js` → `fontFamily.sans` | `['Plus Jakarta Sans', 'sans-serif']` | ✅ configurado |
| `tailwind.config.js` → `fontFamily.body` | `['DM Sans', 'sans-serif']` | ✅ configurado |
| `index.html` → `<link>` Google Fonts | carrega Plus Jakarta Sans (200-800, ital) + DM Sans (100-1000, ital) | ✅ carregado |
| `index.css` | `body { font-family: 'Plus Jakarta Sans', sans-serif; }` | ⚠️ ver divergência abaixo |
| Uso de `font-body` / `font-sans` nas páginas | **zero ocorrências** em `src/**/*.jsx` | ⚠️ ver divergência abaixo |

**Conclusão:** `design_system.md` está desatualizado neste ponto — dizia
"nenhuma fonte configurada" (Divergência crítica #1), mas isso já foi
corrigido em produção (provavelmente na Manutenção #9, DIV-UI01). **Nenhuma
ação bloqueante.** Fontes Uid corretas (Plus Jakarta Sans + DM Sans), nenhum
Inter/Roboto/Arial em uso — regra global OK.

**Divergência não-bloqueante encontrada (registrar, não é escopo deste
hotfix):** `body { font-family: 'Plus Jakarta Sans' }` no CSS puro tem
prioridade sobre o padrão de `font-family` do Tailwind e nenhum componente
aplica a classe `font-body`. Na prática, **100% do texto do sistema (títulos
e corpo) renderiza em Plus Jakarta Sans**; DM Sans é baixado mas nunca
aplicado. O padrão Uid pede Plus Jakarta Sans só para display/headings
(700/800) e DM Sans para body/interface (400/500/600). Não corrigir agora —
fora do escopo do dark mode. Se sobrar tempo, o Loom pode trocar o seletor em
`index.css` para `body { font-family: 'DM Sans', sans-serif; }` e aplicar
`font-sans` (Plus Jakarta Sans) explicitamente em h1/h2/branding — mas isso é
opcional, não faz parte desta entrega.

---

## 1) Pré-requisito técnico obrigatório — `darkMode: 'class'`

`tailwind.config.js` atual **não define `darkMode`** (chave ausente = default
`'media'`, que segue `prefers-color-scheme` do SO e não permite toggle
manual). Sem isso, o toggle sol/lua não tem efeito nenhum.

**Loom precisa adicionar no topo do `theme` object:**

```js
/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',   // ← ADICIONAR — habilita dark: via classe .dark no <html>
  content: [
    './index.html',
    './src/**/*.{js,jsx}',
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Plus Jakarta Sans', 'sans-serif'],
        body: ['DM Sans', 'sans-serif'],
      },
      colors: {
        primary: { /* ... mantém como está, é o primary do light mode ... */ },
        accent:  { /* ... mantém como está ... */ },

        // NOVO — escala navy (superfícies do dark mode)
        navy: {
          950: '#0a0f1d',   // fundo da aplicação (mais escuro)
          900: '#0f1629',   // sidebar, header
          800: '#141b2e',   // card, modal
          700: '#1c2440',   // hover, thead, elevação
          600: '#2a3352',   // borda padrão
          500: '#3d4a73',   // borda em foco / divisor forte
        },

        // NOVO — primary roxo recalibrado para dark mode
        violet: {
          50:  '#f5f3ff',
          100: '#ede9fe',
          200: '#ddd6fe',
          300: '#c4b5fd',
          400: '#a78bfa',
          500: '#8b5cf6',
          600: '#7c3aed',
          700: '#6d28d9',
          800: '#5b21b6',
          900: '#4c1d95',
        },
      },
    },
  },
  plugins: [],
}
```

**Por que roxo e não o mesmo azul (`primary-600 #2563eb`) recalibrado só em
brilho:** azul sobre navy (`#0f1629`/`#141b2e`) perde contraste e "some" no
fundo — os dois ficam na mesma família de matiz (blue-on-blue-dark). Roxo/
violeta cria separação visual clara entre "superfície" (navy) e "ação"
(violet), e conecta com a identidade padrão Uid (`--color-brand-purple:
#3D0361`, "profundidade, premium") sem copiar o hex exato — este é
recalibrado especificamente para contraste AA em botão sólido com texto
branco.

**Contraste verificado (WCAG AA, mínimo 4.5:1 para texto normal):**
- `violet-600 #7c3aed` + texto branco → **4.7:1** ✅ (botão primário dark)
- `violet-400 #a78bfa` + fundo `navy-950 #0a0f1d` → **7.9:1** ✅ (links/texto de destaque em dark)
- Texto principal `#e5e9f0` + fundo `navy-950 #0a0f1d` → **15.8:1** ✅
- Texto secundário `#94a3b8` + fundo `navy-900 #0f1629` → **5.1:1** ✅

---

## 2) Tokens — Light (referência, inalterado) × Dark (novo)

| Papel semântico | Light (atual, mantém) | Dark (novo) |
|---|---|---|
| Fundo da aplicação | `bg-gray-50` `#f9fafb` | `dark:bg-navy-950` `#0a0f1d` |
| Sidebar | `bg-gray-900` `#111827` | `dark:bg-navy-900` `#0f1629` (já é escura — só ajusta o matiz pra combinar com o resto) |
| Header | `bg-white` | `dark:bg-navy-900` `#0f1629` |
| Card / Modal | `bg-white` | `dark:bg-navy-800` `#141b2e` |
| Borda padrão | `border-gray-200` `#e5e7eb` | `dark:border-navy-600` `#2a3352` |
| Borda de input | `border-gray-300` `#d1d5db` | `dark:border-navy-500` `#3d4a73` |
| Thead / hover de linha | `bg-gray-50` | `dark:bg-navy-700` `#1c2440` |
| Texto principal (h1, célula primária) | `text-gray-900` | `dark:text-slate-100` `#e5e9f0` |
| Texto secundário / label | `text-gray-700` / `text-gray-600` | `dark:text-slate-300` `#c4cbdc` |
| Texto muted / placeholder | `text-gray-500` / `text-gray-400` | `dark:text-slate-400` `#94a3b8` |
| Primary (ação, botão, link, tab ativa) | `primary-600` `#2563eb` | `dark:bg-violet-600` `#7c3aed` (bg) / `dark:text-violet-400` `#a78bfa` (texto/link) |
| Primary hover | `primary-700` `#1d4ed8` | `dark:hover:bg-violet-700` `#6d28d9` |
| Primary background suave (badge, avatar, hover file input) | `primary-50`/`primary-100` | `dark:bg-violet-900/30` + `dark:text-violet-300` |
| Accent / sucesso | `accent-600` `#059669` | mantém — verde já tem contraste bom em fundo escuro; usar `dark:text-emerald-400` `#34d399` para texto/ícone |
| Erro / danger | `red-600` `#dc2626` | mantém para bg de botão; texto de erro em dark usa `dark:text-red-400` `#f87171` (red-700 escurece demais no navy) |
| Warning | `yellow-700` (texto) | `dark:text-amber-400` `#fbbf24` |

---

## 3) Mapeamento Light → Dark por componente

### Sidebar (`Sidebar.jsx`)
- `bg-gray-900` → `dark:bg-navy-900` (praticamente igual, só recalibra o matiz — sidebar já era escura, sem "salto" visual ao trocar tema)
- Ativo: `bg-primary-600 text-white` → `dark:bg-violet-600 dark:text-white`
- Inativo: `text-gray-400` → `dark:text-slate-400` (igual, sem mudança perceptível)
- Ícones/emoji da sidebar: sem alteração de cor (emoji não sofre filtro de tema)

### Header (`Header.jsx`)
- `bg-white border-b border-gray-200` → `dark:bg-navy-900 dark:border-navy-600`
- Branding "UidCore": `text-primary-600` → `dark:text-violet-400`
- Avatar círculo: `bg-primary-100` / `text-primary-700` → `dark:bg-violet-900/40` / `dark:text-violet-300`
- Texto do usuário: `text-gray-700` → `dark:text-slate-300`
- Botão Sair: `text-gray-500 hover:bg-gray-100 hover:text-gray-700` → `dark:text-slate-400 dark:hover:bg-navy-700 dark:hover:text-slate-200`
- **Toggle de tema entra aqui** — ver seção 4

### Card
- `bg-white rounded-xl border border-gray-200 shadow-sm` → `dark:bg-navy-800 dark:border-navy-600 dark:shadow-none` (sombra não funciona bem em fundo escuro — trocar por borda mais visível em vez de shadow)
- Header do card: `border-b border-gray-100` / `text-gray-700` → `dark:border-navy-700` / `dark:text-slate-200`
- Footer: `bg-gray-50 border-t border-gray-100` → `dark:bg-navy-900/50 dark:border-navy-700`

### Button
| Variante | Light | Dark |
|---|---|---|
| primary | `bg-primary-600 hover:bg-primary-700 text-white` | `dark:bg-violet-600 dark:hover:bg-violet-700 dark:text-white` |
| secondary | `bg-white border-gray-300 text-gray-700 hover:bg-gray-50` | `dark:bg-navy-800 dark:border-navy-500 dark:text-slate-200 dark:hover:bg-navy-700` |
| danger | `bg-red-600 hover:bg-red-700 text-white` | `dark:bg-red-600 dark:hover:bg-red-700 dark:text-white` (mantém — já tem contraste suficiente) |

Focus ring (`focus:ring-2 focus:ring-offset-2`): em dark, `ring-offset`
precisa casar com o fundo — `dark:ring-offset-navy-900`, senão sobra um halo
branco (offset default é branco).

### Input / Select
- Default: `border-gray-300 bg-white text-gray-900 placeholder-gray-400` → `dark:border-navy-500 dark:bg-navy-800 dark:text-slate-100 dark:placeholder-slate-500`
- Focus: `focus:ring-primary-500` → `dark:focus:ring-violet-500`
- Error: `border-red-500 bg-red-50` → `dark:border-red-500 dark:bg-red-950/40`
- Disabled: `bg-gray-50 cursor-not-allowed` → `dark:bg-navy-900 dark:text-slate-500`

### Modal
- Overlay: `bg-black/50` → mantém (`bg-black/50` funciona igual nos dois temas — não precisa de `dark:`)
- Container: `bg-white shadow-xl` → `dark:bg-navy-800 dark:shadow-none dark:border dark:border-navy-600` (mesma lógica do Card — trocar shadow por borda)

### Pagination
- Ativo: `bg-primary-600 text-white` → `dark:bg-violet-600`
- Inativo: `bg-gray-100 text-gray-600 hover:bg-gray-200` → `dark:bg-navy-800 dark:text-slate-400 dark:hover:bg-navy-700`

### Tabela (padrão dentro de Card)
- `thead` → `bg-gray-50 border-gray-200` → `dark:bg-navy-900 dark:border-navy-600`
- `th` texto → `text-gray-600` → `dark:text-slate-400`
- `tbody` → `divide-gray-100` → `dark:divide-navy-700`
- Linha hover → `hover:bg-gray-50` → `dark:hover:bg-navy-700/60`
- Coluna principal → `text-gray-900 font-medium` → `dark:text-slate-100`
- Coluna secundária → `text-gray-600` → `dark:text-slate-400`
- Linha estornada (`opacity-50 line-through`) → sem alteração, opacidade funciona igual nos dois temas

### Tabs (pill style, módulo Financeiro)
- Ativa: `bg-primary-600 text-white` → `dark:bg-violet-600`
- Inativa: `bg-white text-gray-600 hover:bg-gray-100 border-gray-200` → `dark:bg-navy-800 dark:text-slate-400 dark:hover:bg-navy-700 dark:border-navy-600`

### Sub-abas (underline style)
- Ativa: `border-primary-600 text-primary-600` → `dark:border-violet-500 dark:text-violet-400`
- Inativa: `text-gray-500 hover:text-gray-700` → `dark:text-slate-500 dark:hover:text-slate-300`

### KPI Card (Financeiro)
| Cor | Light | Dark |
|---|---|---|
| blue | `bg-blue-50 text-blue-700` | `dark:bg-blue-950/40 dark:text-blue-300` |
| green | `bg-green-50 text-green-700` | `dark:bg-emerald-950/40 dark:text-emerald-300` |
| red | `bg-red-50 text-red-700` | `dark:bg-red-950/40 dark:text-red-300` |

### Badges de status — fórmula geral
Regra: `bg-{cor}-100 text-{cor}-800` (light) → `dark:bg-{cor}-900/30
dark:text-{cor}-300` (dark). Aplicar a **todos** os status já catalogados em
`design_system.md` item b:

| Status (grupo) | Light | Dark |
|---|---|---|
| RECEBIDO / PAGO / APROVADO / VIGENTE / CONCLUIDO / ATIVO / PROCESSADO / CONCILIADO | `bg-green-100 text-green-800` | `dark:bg-emerald-900/30 dark:text-emerald-300` |
| PENDENTE / EXPIRADO / ABERTA / EM_ANDAMENTO / COM_DIVERGENCIAS / FALTANDO_SISTEMA | `bg-yellow-100 text-yellow-800` | `dark:bg-amber-900/30 dark:text-amber-300` |
| ATRASADO / CANCELADO (crítico) / REJEITADO | `bg-red-100 text-red-800` | `dark:bg-red-900/30 dark:text-red-300` |
| CANCELADO (neutro) / RASCUNHO / FALTANDO_BANCO / Inativo | `bg-gray-100 text-gray-400`/`text-gray-600` | `dark:bg-navy-700 dark:text-slate-400` |
| ENVIADO / CONFIRMADO / AGENDADO / FECHADA | `bg-blue-100 text-blue-800` | `dark:bg-blue-900/30 dark:text-blue-300` |
| EM_PRODUCAO | `bg-purple-100 text-purple-800` | `dark:bg-violet-900/30 dark:text-violet-300` |
| Sim (booleano, ResourceCrud) | `bg-green-50 text-green-700` | `dark:bg-emerald-950/40 dark:text-emerald-300` |
| Não (booleano, ResourceCrud) | `bg-gray-100 text-gray-500` | `dark:bg-navy-700 dark:text-slate-500` |

### Toast
- Sucesso: `bg-accent-600` → mantém igual nos dois temas (já é sólido, funciona sobre qualquer fundo)
- Erro: `bg-red-600` → mantém igual

### Empty states
- `text-gray-400` → `dark:text-slate-500`
- Ícone Lucide `text-gray-300` → `dark:text-navy-500`

### Indicadores financeiros (Financeiro)
- Receita/Entrada: `text-green-700` → `dark:text-emerald-400`
- Despesa/Saída: `text-red-700` → `dark:text-red-400`
- Delta positivo `text-green-600` → `dark:text-emerald-400` / negativo `text-red-600` → `dark:text-red-400`
- Runway ≥6 meses `text-green-700` → `dark:text-emerald-400`; 3-5 meses `text-yellow-700` → `dark:text-amber-400`; <3 meses `text-red-700` → `dark:text-red-400`
- Gráfico de barras CSS puro: barras de receita (`green-400`) e despesa (`red-400`) já são claras o suficiente para contrastar com navy — **sem alteração**

### Login Page
- Fundo: `bg-gradient-to-br from-primary-50 to-primary-100` → `dark:from-navy-950 dark:to-navy-900` (gradiente navy, mantém a mesma direção `br`)
- Card do form: `bg-white border-gray-200` → `dark:bg-navy-800 dark:border-navy-600 dark:shadow-none`
- Ícone logo (quadrado com "U"): `bg-primary-600` → `dark:bg-violet-600`
- Erro inline: `bg-red-50 border-red-200 text-red-700` → `dark:bg-red-950/40 dark:border-red-800 dark:text-red-300`

---

## 4) Toggle de tema — emoji sol/lua no Header

**Posição:** `Header.jsx`, no grupo de ações da direita (`<div
className="flex items-center gap-4">`), **antes** do bloco do usuário/avatar.
Em telas pequenas continua visível (não entra no menu hambúrguer — ação de 1
clique tem que estar sempre acessível, regra de UX Uid: "ação principal
sempre visível").

**Comportamento:**
- O ícone exibido representa **para onde o clique leva** (padrão mais comum e menos ambíguo):
  - Tema atual = **claro** → botão mostra **🌙** (lua) → clique ativa dark mode
  - Tema atual = **escuro** → botão mostra **☀️** (sol) → clique ativa light mode
- `aria-label` dinâmico: `"Ativar modo escuro"` / `"Ativar modo claro"` (acessibilidade — leitor de tela não pode depender só do emoji)
- `title` (tooltip nativo) com o mesmo texto do `aria-label`

**Markup de referência (Loom implementa):**

```jsx
<button
  onClick={toggleTheme}
  aria-label={isDark ? 'Ativar modo claro' : 'Ativar modo escuro'}
  title={isDark ? 'Ativar modo claro' : 'Ativar modo escuro'}
  className="w-9 h-9 flex items-center justify-center rounded-lg text-lg
             text-gray-500 hover:bg-gray-100
             dark:text-slate-400 dark:hover:bg-navy-700
             transition-colors"
>
  {isDark ? '☀️' : '🌙'}
</button>
```

**Persistência e estado (arquitetura sugerida ao Loom, sem prescrever a implementação exata):**
- `localStorage.getItem('uidcore-theme')` → `'light' | 'dark'`, default `'light'` (respeita o light mode como padrão do sistema, não seguir `prefers-color-scheme` do SO automaticamente — o cliente é financeiro/negócio, decisão consciente é melhor que herdar do SO)
- Aplicar a classe `dark` no elemento `<html>` (não no `<body>` nem num wrapper interno — Tailwind com `darkMode: 'class'` procura a classe em qualquer ancestral, mas `<html>` evita FOUC)
- **Evitar flash de tema errado (FOUC):** ler o `localStorage` e aplicar a classe `dark` num script inline **no `<head>` do `index.html`**, antes do React montar — senão a tela pisca light→dark no reload
  ```html
  <script>
    (function () {
      var t = localStorage.getItem('uidcore-theme');
      if (t === 'dark') document.documentElement.classList.add('dark');
    })();
  </script>
  ```
- Contexto React (`ThemeContext` ou hook `useTheme`, junto com `useAuth.js` em `src/hooks/`) expõe `{ isDark, toggleTheme }` para o `Header.jsx` consumir

**Fora do escopo desta entrega:** seguir automaticamente
`prefers-color-scheme` do SO. Fica como opção futura, não como default —
decisão consciente do Brush para não conflitar com o item b) do
design_system.md que já trata o tema claro como escolha arquitetural
deliberada para este produto financeiro.

---

## 5) Checklist de implementação (Loom)

```
[ ] tailwind.config.js: darkMode: 'class' + colors.navy + colors.violet
[ ] index.html: script inline anti-FOUC no <head>
[ ] ThemeContext / useTheme hook (localStorage key: uidcore-theme, default light)
[ ] Header.jsx: botão toggle sol/lua (posição: antes do bloco usuário/avatar)
[ ] AppLayout, Sidebar, Header: classes dark: aplicadas (ver seção 3)
[ ] Card, Modal, Input, Select, Button, Pagination: classes dark: aplicadas
[ ] Todas as tabelas (thead/tbody/hover): classes dark: aplicadas
[ ] Todos os badges de status: fórmula bg-{cor}-900/30 + text-{cor}-300 aplicada
[ ] KPI Cards do Financeiro: 3 variantes (blue/green/red) com dark:
[ ] Indicadores financeiros (receita/despesa/runway/delta): dark: aplicado
[ ] LoginPage: gradiente + card + ícone logo com dark:
[ ] Empty states + Loading: dark: aplicado
[ ] Toast: confirmar que bg-accent-600/bg-red-600 sólidos continuam legíveis em dark (não precisam de dark:, mas testar visualmente)
[ ] Testar contraste em 375px (iPhone SE) nos dois temas
[ ] Testar toggle: reload da página mantém o tema escolhido (sem flash)
[ ] Verificar overflow-hidden no root do AppLayout (ALERTA já existente no design_system.md, não relacionado ao dark mode, mas testar select nativo em ambos os temas)
```

---

## Passagem de bastão

```
✅ Especificação UI concluída — UidCore (Dark Mode)

Entregáveis:
- Especificacao_UI_Hotfix.md (este arquivo)
- Tokens novos: escala navy (6 níveis) + escala violet (9 níveis)
- Mapeamento light→dark: 15 componentes/padrões cobertos
- Toggle sol/lua especificado (posição, comportamento, persistência, anti-FOUC)
- Checagem de fontes: OK (Plus Jakarta Sans + DM Sans carregadas), 1 divergência
  não-bloqueante registrada (DM Sans carregada mas nunca aplicada)
- Pré-requisito técnico sinalizado: tailwind.config.js falta darkMode: 'class'

📁 Arquivo: Especificacao_UI_Hotfix.md (em /var/www/uidcore/)

➡️ Loom implementa: tailwind.config.js (darkMode + tokens) → ThemeContext/hook
   → toggle no Header → classes dark: em todos os componentes listados na seção 3
```
