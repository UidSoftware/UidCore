# Especificação UI Hotfix — UidCore (Manutenção #87)

## Modo

**MODO HOTFIX.** Esta manutenção é puramente de parametrização de nome —
não há tela nova, não há componente novo, não há mudança de layout,
cor, espaçamento ou ícone. A UI existente permanece **visualmente
idêntica**; o único efeito observável é a origem do texto: de string
`'UidCore'` escrita à mão em 7 arquivos `.jsx` + `index.html` para uma
única fonte de configuração (`APP_NAME`/`APP_DESCRIPTION`, lidos de
`frontend/src/utils/appConfig.js`). Com `.env` atual (sem as variáveis
novas), nada muda — RNF-01 da `Especificacao_Hotfix.md` exige paridade
visual 1:1 antes/depois.

## Design System do Projeto (referência — não alterado)

- **Cores primárias:** `primary-600`/`primary-50` (light) e `violet-600`/
  `violet-400` (dark) — accent do produto (logo, título, badges de ação).
- **Cores de fundo:** `gray-50`/`white` (light) e `navy-950`/`navy-900`/
  `navy-800` (dark) — gradiente `from-primary-50 to-primary-100` (light) /
  `from-navy-950 to-navy-900` (dark) nas telas de autenticação.
- **Texto:** `text-gray-900`/`text-gray-500` (light), `text-slate-100`/
  `text-slate-400`/`text-slate-500` (dark).
- **Fonte:** Plus Jakarta Sans (display/headings) + DM Sans (body) — já
  carregadas via Google Fonts em `index.html` (`<link>` de preconnect +
  stylesheet, linhas 15-17). **Não tocar** — fora do escopo desta
  manutenção.
- **BorderRadius padrão:** `rounded-2xl` (cards de auth, avatar-badge),
  `rounded-lg` (inputs, botões de ícone).
- **Padrão de card:** `bg-white dark:bg-navy-800 border border-gray-200
  dark:border-navy-600 rounded-2xl shadow-sm dark:shadow-none`.
- **Dark mode:** classe `dark` no `<html>`, controlada por
  `localStorage['uidcore-theme']` + script anti-FOUC inline no `<head>`
  do `index.html` (linhas 5-9) — **não tocar**, não faz parte desta
  manutenção e é o mesmo padrão que o `transformIndexHtml` novo do
  `vite.config.js` precisa respeitar (RN-02: edição cirúrgica, só
  `<title>` e `<meta name="description">`).

## Especificação Visual por Componente/Tela

Para cada ponto, a regra geral é a mesma: **nenhuma classe Tailwind,
nenhuma estrutura de layout, nenhum ícone muda** — só a fonte do texto.
Todo `.jsx` passa a `import { APP_NAME } from '../utils/appConfig.js'`
(ou `'../../utils/appConfig.js'`/`'./utils/appConfig.js'` conforme a
profundidade real da pasta de cada arquivo — Loom confere o caminho
relativo correto por arquivo, não copiar literalmente) e usa `{APP_NAME}`
no JSX exatamente onde hoje está a string `'UidCore'`.

### `index.html` (`<title>` + `<meta name="description">`)

- **Elemento:** `<title>UidCore</title>` (linha 14) e
  `<meta name="description" content="UidCore — Template Financeiro
  Multi-Nicho">` (linha 13).
- **Fonte do texto:** não é importado em JS (é HTML estático lido antes
  do React montar) — resolvido pelo `transformIndexHtml` do
  `vite.config.js`, que lê `process.env.VITE_APP_NAME`/
  `VITE_APP_DESCRIPTION` em build/dev e substitui o conteúdo dessas duas
  tags. `appConfig.js` continua sendo a fonte de verdade conceitual
  (mesmos nomes de variável, mesmos fallbacks), só que consumida pelo
  Vite config, não por um componente React.
- **Considerações:** o `<title>`/`<meta>` literal no arquivo-fonte
  permanece como `UidCore` (fallback visível em `view-source` antes do
  JS/build processar) — comportamento aceitável, equivalente ao flash
  inicial que o próprio script anti-FOUC do tema já tem hoje. Nenhuma
  outra tag do `<head>` (preconnect de fontes, favicon, script do tema)
  é tocada — RN-02.
- **Dark mode/responsivo/espaçamento:** não aplicável (tag de documento,
  sem renderização visual própria).
- **Ícones Lucide:** nenhum.

### Sidebar (`Sidebar.jsx`, logo expandida)

- **Elemento:** `<span className="text-lg font-bold text-white
  tracking-tight">UidCore</span>` (linha 47), dentro do header da
  sidebar (`flex items-center justify-between px-4 py-5 ...`),
  renderizado só quando `!collapsed`.
- **Fonte do texto:** `{APP_NAME}` via `import { APP_NAME } from
  '../../utils/appConfig.js'` (Sidebar.jsx está em
  `src/components/layout/`, dois níveis abaixo de `src/`).
- **Considerações:** classe `text-lg font-bold text-white tracking-tight`
  preservada sem alteração — nomes mais longos que "UidCore" quebram
  linha naturalmente dentro do `flex` existente (sem `truncate`/
  `overflow-hidden` hoje); se um fork futuro usar um nome muito longo, a
  sidebar expandida (`w-64`) tem espaço suficiente para a maioria dos
  nomes de produto razoáveis — não é requisito desta manutenção
  acomodar nome arbitrariamente longo, só documentar que não há
  `truncate` aplicado caso o fork precise ajustar depois.
- **Dark mode:** sem mudança — `text-white` já funciona em ambos os
  temas (fundo da sidebar é `bg-gray-900 dark:bg-navy-900`, sempre
  escuro).
- **Responsivo:** span só aparece com `!collapsed` — comportamento
  inalterado (colapsar a sidebar já esconde o nome hoje, independente
  do texto).
- **Ícones Lucide:** nenhum — a sidebar usa emojis nos itens de menu
  (padrão intencional da fábrica, CLAUDE.md global) e não tem ícone ao
  lado do nome do produto.

### Header (`Header.jsx`, nome no header desktop)

- **Elemento:** `<span className="hidden md:block text-sm font-semibold
  text-primary-600 dark:text-violet-400 tracking-wide">UidCore</span>`
  (linha 127).
- **Fonte do texto:** `{APP_NAME}` via `import { APP_NAME } from
  '../../utils/appConfig.js'` (mesma profundidade de pasta que
  Sidebar.jsx).
- **Considerações:** `hidden md:block` preservado — span só aparece em
  telas ≥768px (md breakpoint), mesmo comportamento de hoje, qualquer
  que seja o nome.
- **Dark mode:** `text-primary-600 dark:text-violet-400` preservado —
  cor de destaque (accent) já adaptada aos dois temas, sem mudança.
- **Responsivo:** inalterado (classe `hidden md:block` já cobre mobile).
- **Ícones Lucide:** nenhum.

### Login (`Login.jsx`)

- **Elemento 1 (título):** `<h1 className="text-2xl font-bold
  text-gray-900 dark:text-slate-100">UidCore</h1>` (linha 42).
- **Elemento 2 (rodapé):** `<p className="text-center text-xs
  text-gray-400 dark:text-slate-500 mt-6">UidCore &copy; {new
  Date().getFullYear()} — Uid Software</p>` (linha 83).
- **Fonte do texto:** `{APP_NAME}` via `import { APP_NAME } from
  '../utils/appConfig.js'` (Login.jsx está em `src/pages/`, um nível
  abaixo de `src/`) em ambos os pontos — o rodapé troca só o trecho
  `UidCore` por `{APP_NAME}`, mantendo literal ` &copy; {new
  Date().getFullYear()} — Uid Software` (atribuição à Uid Software é
  institucional, não faz parte do nome do produto e não está no escopo
  do RF-01/RF-03).
- **Considerações (fora do escopo, só observação para registro):** o
  badge circular acima do título (`<div className="inline-flex ...
  rounded-2xl bg-primary-600 dark:bg-violet-600 ..."><span
  className="text-3xl font-bold text-white">U</span></div>`, linha ~39)
  usa a letra **"U" hardcoded** (inicial de "UidCore"), sem vínculo com
  `APP_NAME`. A `Especificacao_Hotfix.md` não lista esse ponto entre os
  8 pontos de UI em escopo (RF-03) — **não alterar nesta manutenção**.
  Registrado aqui só para o próximo fork saber que a letra do badge
  precisa ser trocada manualmente (ou numa manutenção futura, derivando
  a 1ª letra de `APP_NAME`) se o nome do produto mudar de verdade — o
  mesmo vale para `DefinirSenha.jsx`, que repete este badge idêntico.
- **Dark mode:** `dark:text-slate-100` (título) e `dark:text-slate-500`
  (rodapé) preservados, sem mudança.
- **Responsivo:** container `max-w-sm` centralizado, inalterado.
- **Ícones Lucide:** nenhum.

### DefinirSenha (`DefinirSenha.jsx`)

- **Elemento 1 (título):** `<h1 className="text-2xl font-bold
  text-gray-900 dark:text-slate-100">UidCore</h1>` (linha 63) — estrutura
  idêntica ao título do Login.jsx (mesmo padrão de tela de autenticação).
- **Elemento 2 (rodapé):** `<p className="text-center text-xs
  text-gray-400 dark:text-slate-500 mt-6">UidCore &copy; {new
  Date().getFullYear()} — Uid Software</p>` (linha 106) — idêntico ao
  rodapé do Login.jsx.
- **Fonte do texto:** `{APP_NAME}` via `import { APP_NAME } from
  '../utils/appConfig.js'`, mesmo caminho relativo do Login.jsx (mesma
  pasta `src/pages/`).
- **Considerações:** mesma observação do badge "U" hardcoded do
  Login.jsx acima (linha ~61 do DefinirSenha.jsx) — fora de escopo,
  registrado só para referência futura.
- **Dark mode/responsivo:** idêntico ao Login.jsx — mesmo padrão visual
  de tela de autenticação, nenhuma classe tocada.
- **Ícones Lucide:** nenhum.

### Dashboard (`Dashboard.jsx` — saudação, 3 variantes)

- **Elementos (3 ocorrências do mesmo texto, estados diferentes da
  mesma tela):**
  - Linha 40 — estado `loading`: `<h1 className="text-2xl font-bold
    text-gray-900 dark:text-slate-100">Bem-vindo ao UidCore,
    {firstName}!</h1>`
  - Linha 56 — estado `erro`: mesma estrutura.
  - Linha 101 — estado normal (dados carregados): mesma estrutura.
- **Fonte do texto:** `{APP_NAME}` via `import { APP_NAME } from
  '../utils/appConfig.js'`, substituindo só o trecho `UidCore` dentro
  da string — resultado: `Bem-vindo ao {APP_NAME}, {firstName}!` nas
  3 ocorrências. **Importar uma única vez no topo do arquivo** e
  reusar nas 3 — não duplicar o import nem criar 3 constantes locais.
- **Considerações:** as 3 ocorrências precisam ficar sincronizadas —
  Loom deve trocar as 3, não só a do estado "normal" (RF-03 exige
  paridade nos 3 estados: loading, erro, dados carregados). `h1`
  mantém `text-2xl font-bold text-gray-900 dark:text-slate-100` sem
  alteração nas 3.
- **Dark mode:** `dark:text-slate-100` preservado nas 3 ocorrências.
- **Responsivo:** `h1` dentro de `<div className="space-y-6">`, sem
  classe responsiva própria — inalterado.
- **Ícones Lucide:** nenhum (os cards de métrica abaixo usam emoji —
  `📈`/`📉`/`💰`/`📊` — fora do escopo desta manutenção, não tocados).

### AgendamentoPublico (`AgendamentoPublico.jsx` — rodapé da página pública)

- **Elemento:** `<footer className="text-center py-6 mt-8 border-t
  border-navy-800"><p className="text-xs text-slate-700">Powered by
  UidCore</p></footer>` (linha 513).
- **Fonte do texto:** `{APP_NAME}` via `import { APP_NAME } from
  '../utils/appConfig.js'` (mesma pasta `src/pages/`), resultado:
  `Powered by {APP_NAME}`.
- **Considerações:** esta é a **única tela pública sem autenticação**
  entre os 8 pontos (visitante final agendando, Manutenção #65) — o
  tom "Powered by X" é institucional (atribuição de quem fez o
  sistema, não nome da tela em si); ao trocar `APP_NAME` num fork
  futuro, o texto passa a refletir o nome do produto do cliente, o que
  é o comportamento esperado (RF-03). Layout de página pública (fundo
  escuro `navy-950`-like, sem toggle de tema visível) não é alterado.
- **Dark mode:** página pública já é fixa em tema escuro (`border-navy-800`,
  `text-slate-700`), sem alternância — nenhuma classe tocada.
- **Responsivo:** `footer` centralizado, `py-6 mt-8`, inalterado.
- **Ícones Lucide:** nenhum no rodapé em si — a tela usa `AlertTriangle`
  (Lucide) em mensagens de erro acima, não relacionado a esta mudança.

### Django Admin (`backend/accounts/admin.py` ou `backend/core/urls.py`)

- **Elemento:** `site_header`/`site_title` do Django admin, hoje no
  default ("Django administration") — **não é UI React**, é o template
  padrão do Django admin (`admin/base_site.html`), fora da camada que o
  Loom controla.
- **Fonte do texto:** `settings.APP_NAME` (Python/backend), não
  `appConfig.js` — documentado aqui só para registro cruzado, já que a
  `Especificacao_Hotfix.md` pede `admin.site.site_header =
  settings.APP_NAME` e `admin.site.site_title = settings.APP_NAME`
  (RF-04, RN-03).
- **Considerações visuais:** o Django admin usa o tema visual padrão do
  próprio Django (não o design system Uid/Tailwind do frontend) — isso
  é esperado e não faz parte do escopo visual desta manutenção; nenhuma
  customização de CSS/template do admin é necessária ou desejada aqui.
- **Dark mode/responsivo:** não aplicável — admin não segue o dark mode
  do app React.
- **Ícones Lucide:** não aplicável (admin não usa Lucide).

### Email de primeiro acesso (`backend/accounts/services.py`)

- **Elemento:** `<h2>UidCore</h2>` no corpo HTML do email (linha 27) +
  assunto `'Acesso ao UidCore — defina sua senha'` (linha 42) — **não é
  tela**, é conteúdo de email transacional enviado fora do app.
- **Fonte do texto:** `settings.APP_NAME` (backend), via
  `f'<h2>{settings.APP_NAME}</h2>'` e `f'Acesso ao {settings.APP_NAME}
  — defina sua senha'`.
- **Considerações visuais:** o HTML do email não segue Tailwind/design
  tokens do app (é HTML inline de email, compatibilidade com clientes
  de email) — Forge mantém a estrutura/estilo inline já existente,
  trocando só o texto. Nenhum ajuste de estilo de email é parte desta
  manutenção.
- **Dark mode/responsivo:** não aplicável a email transacional nesta
  manutenção (fora de escopo — clientes de email variam, não há dark
  mode controlado pelo sistema).
- **Ícones Lucide:** não aplicável (HTML de email, sem Lucide).

## Observação final (paridade visual obrigatória)

Todos os 8 pontos acima devem renderizar **pixel-a-pixel idênticos** ao
estado atual quando `VITE_APP_NAME`/`APP_NAME` estiverem ausentes ou
vazios (RN-01 + RNF-01 da `Especificacao_Hotfix.md`) — o fallback
`'UidCore'` (frontend, em `appConfig.js`) e `default='UidCore'`
(backend, em `settings.py`) é o que garante isso. Loom e Forge não
devem introduzir nenhuma classe, espaçamento, cor ou ícone novo em
nenhum dos 8 pontos — esta é uma manutenção de **fonte do dado**, não
de **design**.

## O que NÃO foi feito (fora de escopo, confirmado)

```
❌ Nenhum design system novo — paleta, fontes e tokens do UidCore
   permanecem exatamente os já documentados/implementados
❌ Nenhuma mudança de identidade visual (cores, logo, ícones)
❌ Nenhuma implementação de código — isso é Forge (backend) e Loom
   (frontend)
❌ Nenhum ajuste no badge "U" hardcoded de Login.jsx/DefinirSenha.jsx —
   fora do escopo do pedido original, só registrado como observação
❌ Nenhum manifest.json/ícone PWA — não existe ainda, não criado aqui
❌ Nenhuma alteração em comentários/docstrings mencionando "UidCore"
```

## Passagem de bastão

```
✅ Especificação UI concluída — UidCore (Manutenção #87)
   Telas/componentes analisados: 8 pontos (index.html, Sidebar, Header,
   Login, DefinirSenha, Dashboard x3, AgendamentoPublico, Django Admin,
   email de primeiro acesso)
   Componentes reutilizados: 100% (nenhum componente novo — só fonte
   do texto trocada: appConfig.js no frontend, settings.APP_NAME no
   backend)
   Novos padrões: nenhum — appConfig.js segue o mesmo princípio já
   usado em selectTemAcessoTotal (authStore.js, Manutenção #60):
   único ponto de leitura, consumido por import em todo o resto

📁 Arquivo: Especificacao_UI_Hotfix.md (neste diretório)

➡️ Loom lê Especificacao_Hotfix.md + Especificacao_UI_Hotfix.md antes
   de implementar frontend/src/utils/appConfig.js, vite.config.js e os
   7 arquivos .jsx
➡️ Forge lê Especificacao_Hotfix.md para settings.py, services.py e
   admin.py/urls.py (esta spec de UI serve só de referência cruzada
   para os pontos de admin/email, que não são componente React)
```
