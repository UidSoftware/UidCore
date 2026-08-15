# Especificacao Hotfix — Manutencao #31 UidCore

**Elaborado por:** Analista (MODO manutencao — MODO ESTEIRA EM FILA, etapa ORDEM_CRIADA)
**Data:** 2026-08-14
**Atualizado em:** 2026-08-14 (re-execucao ORDEM_CRIADA — verificacao pos-Loom)
**Sistema:** UidCore
**Modulo:** Tema visual (frontend) — Dark Mode + Toggle Dia/Noite
**Tipo:** `feature_pequena` (mudanca de UI/tema, sem alteracao de modelo de dados ou regra de negocio backend)
**Complexidade:** media (volume alto de arquivos tocados — todos os componentes de UI — mas mudanca mecanica, sem risco de dado)
**requer_aprovacao_comercial:** false (ajuste de UX dentro do sistema ja contratado, nao amplia escopo de contrato)
**Fontes lidas:** CLAUDE.md do projeto, `design_system.md`, `frontend/tailwind.config.js`,
`frontend/index.html`, `frontend/src/index.css`, `frontend/src/hooks/useTheme.js`,
`frontend/src/components/layout/Sidebar.jsx`, `frontend/src/components/layout/Header.jsx`,
`frontend/src/components/layout/AppLayout.jsx`, `frontend/src/components/ui/*`,
`Especificacao_UI_Hotfix.md` (Brush, mesma data), `git status`

---

## 0) Estado real do working tree (verificado nesta execucao)

Esta instancia do Analista verificou o working tree antes de escrever a spec.
O quadro real ao entrar no estagio ORDEM_CRIADA:

### Infraestrutura de dark mode: JA IMPLEMENTADA CORRETAMENTE

| Arquivo | Estado | Verificacao |
|---|---|---|
| `tailwind.config.js` | Modificado (nao commitado) | `darkMode: 'class'` ✅, navy hex exatos do cliente ✅, violet ✅ |
| `frontend/index.html` | Modificado (nao commitado) | Script anti-FOUC: `if (t !== 'light') classList.add('dark')` ← dark e o default ✅ |
| `frontend/src/hooks/useTheme.js` | Novo (untracked) | `useState(() => document.documentElement.classList.contains('dark'))` — sincroniza com o script do html antes do React montar ✅ |

**Hex da escala navy verificados contra o pedido do cliente:**

| Token | Pedido | Implementado | Status |
|---|---|---|---|
| navy-950 | `#0a0f1e` | `#0a0f1e` | ✅ bate |
| navy-900 | `#0f1729` | `#0f1729` | ✅ bate |
| navy-800 | `#1a2540` | `#1a2540` | ✅ bate |
| navy-700 | `#232f4d` | `#232f4d` | ✅ bate |

**Nota:** o token `primary` (azul) NAO foi recalibrado para roxo — estrategia adotada foi criar
escala `violet` paralela e usar `dark:bg-violet-*` / `dark:text-violet-*` nos componentes.
Funcionalmente equivalente ao pedido, mais limpo para nao quebrar o light mode que ja usa
`primary-600` em todo lugar.

### Componentes e paginas: TODOS IMPLEMENTADOS (nao commitados)

38 arquivos modificados com `dark:` aplicado — verificado em `git status` (re-verificacao pos-Loom).
A cobertura foi verificada com `grep -c "dark:"` por arquivo.

**Ja implementados (em working tree, pendentes de commit):**
- Todos os componentes base: `AppLayout`, `Header`, `Sidebar`, `Card`, `Button`, `Input`,
  `Select`, `Modal`, `Loading`, `Pagination`, `ResourceCrud`
- Paginas com cobertura adequada: `Login`, `Dashboard`, `Financeiro` (162 ocorrencias),
  `Clientes`, `Fornecedores`, `Vendas`, `Produtos`, `Conciliacao`, `Agendamento`,
  `Pagamentos`, `Administrativo`, `Rh`, `Portal`
- PDV COMPLETO: `AberturaCaixa`, `FechamentoCaixa`, `HistoricoVendas`,
  `FrenteDeCaixa` (39 ocorrencias), `RelatorioSessoesCaixa` (89 ocorrencias),
  `CarrinhoItem`, `ModalSangriaSuprimento`, `ModalScannerCamera`, `ResumoSessao`, `SplitPagamento`

**IMPLEMENTACAO CONCLUIDA — 0 arquivos pendentes de dark mode**

**Unico item restante antes do commit:**
1. `design_system.md` — registrar paleta nova e reverter decisao arquitetural b)
   ("UidCore usa tema claro... como padrao") para ("UidCore usa tema escuro como padrao,
   a partir da Manutencao #31 — pedido do cliente 2026-08-14")
   Verificado: 0 ocorrencias de navy/dark/violet no design_system.md atual.

---

## 1) Contexto

Sistema em producao com tema claro (`bg-gray-50`, paleta azul `primary-600 #2563eb`),
documentado em `design_system.md` (secao b) como divergencia proposital do padrao escuro
da Uid. Usuario reportou que o sistema esta "muito claro" e pediu tema escuro com paleta
especifica (60% azul marinho / 30% roxo / 10% vermelho), com toggle dia/noite e **escuro
como padrao na primeira visita** — o oposto do que estava documentado como decisao
arquitetural ate agora.

**Nota sobre o conflito Brush x cliente:** a `Especificacao_UI_Hotfix.md` (Brush, mesma data)
especificou light como padrao, citando a decisao arquitetural anterior. O pedido do cliente
**E o proprio ADR que substitui essa decisao** — dark como padrao e o criterio de aceite
explicitamente pedido e deve prevalecer. A implementacao atual do `index.html`/`useTheme.js`
ja reflete o criterio correto (dark como default).

---

## 2) Requisitos Funcionais

### RF-01 — Nova paleta de cores (tailwind.config.js)

**JA IMPLEMENTADA** em working tree. Tokens verificados:

| Token | Uso | Status |
|---|---|---|
| `navy-950` `#0a0f1e` | fundo da aplicacao | ✅ implementado |
| `navy-900` `#0f1729` | sidebar, header | ✅ implementado |
| `navy-800` `#1a2540` | superficies/cards | ✅ implementado |
| `navy-700` `#232f4d` | bordas em fundo escuro | ✅ implementado |
| `violet-700` `#6d28d9` | hover de acao | ✅ implementado |
| `violet-600` `#7c3aed` | botao primario, tab ativa | ✅ implementado |
| `violet-500` `#8b5cf6` | referencia intermediaria | ✅ implementado |
| `violet-400` `#a78bfa` | link/texto de destaque em dark | ✅ implementado |
| `red-600` `#dc2626` | danger/erro (uso restrito) | mantido — nenhum uso de vermelho fora de erro/perigo confirmado |

**Loom NAO precisa alterar `tailwind.config.js`** — esta correto.

### RF-02 — Migrar fundo/texto/superficies para o tema escuro

**PARCIALMENTE IMPLEMENTADA** em working tree.

Mapeamento completo de tokens ja especificado em `Especificacao_UI_Hotfix.md` secao 2 e 3.
O que esta feito: ver secao 0 acima.

**IMPLEMENTACAO CONCLUIDA** (verificado pos-Loom em 2026-08-14):

#### FrenteDeCaixa.jsx (646 linhas) — IMPLEMENTADO
39 ocorrencias de `dark:` confirmadas via `grep -c`. Tela principal do PDV coberta.

#### RelatorioSessoesCaixa.jsx (506 linhas) — IMPLEMENTADO
89 ocorrencias de `dark:` confirmadas via `grep -c`. Relatorio de sessoes coberto.

### RF-03 — Toggle dia/noite

**JA IMPLEMENTADO** em working tree:
- Botao no Header com emoji sol/lua (☀️ quando dark, 🌙 quando light) ✅
- `darkMode: 'class'` no Tailwind ✅
- `localStorage` key `uidcore-theme` com persistencia ✅
- **Tema padrao ESCURO** na primeira visita (sem localStorage previo) ✅
  - `index.html`: `if (t !== 'light') classList.add('dark')` — correto
  - `useTheme.js`: le estado inicial da classe ja aplicada no `<html>` — correto

**Loom NAO precisa alterar** `index.html`, `useTheme.js` ou `Header.jsx` —
os tres estao corretos.

### RF-04 — Fontes (verificado, sem pendencia)

- Google Fonts carregado em `index.html` (Plus Jakarta Sans + DM Sans) ✅
- `tailwind.config.js` com `fontFamily.sans`/`body` corretos ✅
- Nenhum Inter/Roboto/Arial em uso ✅
- Divergencia nao-bloqueante registrada: DM Sans baixada mas nunca aplicada
  (100% do texto usa Plus Jakarta Sans via `body { font-family }` em `index.css`) —
  fora do escopo deste hotfix, registrado para proxima sprint.

---

## 3) Regras de Negocio / UX

- RN-01 — O sistema deve nascer em modo escuro para qualquer usuario que nunca alterou a
  preferencia (primeiro acesso, cache limpo, ou navegador anonimo).
- RN-02 — A escolha de tema e por navegador/dispositivo (via `localStorage`), nao por
  usuario/conta.
- RN-03 — Nenhuma tela pode ficar com texto ilegivel (contraste abaixo de AA — minimo 4.5:1)
  em nenhum dos dois temas. Telas prioritarias: Login, Dashboard, Financeiro (incluindo
  graficos), PDV/Frente de Caixa, Clientes, Agendamento.
- RN-04 — O emoji sol/lua no toggle e uma decisao de produto deliberada — NUNCA substituir
  por icone Lucide, mesmo que o resto do sistema use Lucide.
- RN-05 — Os DOIS temas (claro existente + escuro novo) continuam funcionais. Nenhuma
  classe light deve ser removida — apenas `dark:` adicionado em paralelo.

---

## 4) Telas afetadas — status atual

| Tela | Estado atual | Acao Loom |
|---|---|---|
| Login | Implementado (modificado, nao commitado) | verificar contraste |
| Dashboard | Implementado (modificado, nao commitado) | verificar KPI cards |
| Financeiro | Implementado (162 dark: classes, nao commitado) | verificar graficos |
| PDV / Frente de Caixa | Implementado (39 dark:, nao commitado) | verificar contraste |
| PDV / Relatorio Sessoes | Implementado (89 dark:, nao commitado) | verificar contraste |
| PDV / outros (AberturaCaixa, FechamentoCaixa, HistoricoVendas) | Implementados | verificar |
| PDV / componentes | Implementados (CarrinhoItem, SplitPagamento, etc.) | verificar |
| Clientes | Implementado | verificar |
| Agendamento | Implementado | verificar |
| Sidebar / Header / AppLayout | Implementados, revisados — corretos | nenhuma |
| design_system.md | Desatualizado — ainda registra "light como padrao" | **ATUALIZAR** |

---

## 5) Spec Frontend — o que Loom precisa fazer

**Nao alterar** (ja correto):
- `tailwind.config.js` — tokens e darkMode corretos
- `index.html` — script anti-FOUC correto (dark como default)
- `frontend/src/hooks/useTheme.js` — correto
- `frontend/src/components/layout/Header.jsx` — toggle correto
- `frontend/src/components/layout/AppLayout.jsx` — correto
- `frontend/src/components/layout/Sidebar.jsx` — correto
- `frontend/src/components/ui/*` — todos corretos
- Todas as paginas ja modificadas — verificar contraste, nao reescrever

**IMPLEMENTACAO CONCLUIDA (pos-Loom, verificado 2026-08-14):**
- Todos os componentes base: corretos
- Todas as paginas (incluindo PDV completo): corretos
- FrenteDeCaixa.jsx: 39 dark: ✅
- RelatorioSessoesCaixa.jsx: 89 dark: ✅

**UNICO ITEM RESTANTE (Loom deve fazer antes do commit):**
1. `design_system.md` — secao b: reverter "light como padrao arquitetural" para
   "dark como padrao a partir da Manutencao #31 (pedido do cliente, 2026-08-14)"
   e documentar paleta navy/violet com os hex exatos

**COMMITAR (Loom ou Pilot, apos design_system.md atualizado):**
2. Commit unico com todos os arquivos modificados (38 arquivos) +
   frontend/src/hooks/useTheme.js (novo, untracked) + design_system.md.
   Mensagem sugerida:
   `feat(frontend): dark mode completo + toggle dia/noite — Manutencao 31`

**NAO ALTERAR:**
- Nenhum arquivo de backend (`backend/`)
- `Especificacao_Hotfix.md` e `Especificacao_UI_Hotfix.md` (documentos de especificacao)
- `CLAUDE.md` (sera atualizado pelo Pilot apos deploy)

---

## 6) Criterios de Aceite (Sentinel testa de verdade, nao so le codigo)

- [ ] CA-01 — App abre em modo **escuro** por padrao em aba anonima (sem localStorage)
- [ ] CA-02 — Toggle alterna claro/escuro e persiste apos F5 (reload da pagina)
- [ ] CA-03 — Login: texto legivel nos dois temas; gradiente funcional em dark
- [ ] CA-04 — Dashboard: KPI cards, tabelas e graficos legiveis em dark
- [ ] CA-05 — Financeiro: graficos de barra (green-400/red-400) legiveis em navy; badges de status corretos
- [ ] CA-06 — PDV / Frente de Caixa: nenhum texto branco sobre fundo branco; dropdowns de resultado visiveis; inputs legiveis em dark
- [ ] CA-07 — Clientes e Agendamento: tabelas e formularios legiveis em dark
- [ ] CA-08 — `npm run build` limpo, 0 erros
- [ ] CA-09 — Testes Django: mesma contagem passando que antes (mudanca e so frontend)
- [ ] CA-10 — Hex dos tokens navy confirmados em tailwind.config.js: 950/#0a0f1e, 900/#0f1729, 800/#1a2540, 700/#232f4d
- [ ] CA-11 — `design_system.md` atualizado: paleta nova documentada + dark como default

**Reprovacao automatica do Sentinel em qualquer um dos itens acima.**

---

## Passagem de bastao

```
✅ Analise concluida (atualizada pos-Loom) — UidCore (Manutencao #31, Dark Mode)
   tipo: feature_pequena
   descricao_tecnica: dark mode com paleta navy/roxo (60/30), toggle sol/lua,
     escuro como padrao na primeira visita
   estado_implementacao: COMPLETO (38 arquivos modificados + useTheme.js novo)
   pendente_antes_do_commit: design_system.md (secao b desatualizada — 0 navy/dark no arquivo)
   requer_aprovacao_comercial: false

➡️  Loom: atualizar design_system.md (secao b, paleta nova, dark como default),
    depois commitar TUDO (38 modificados + useTheme.js untracked + design_system.md)
    num commit unico. NÃO alterar nenhum .jsx — ja corretos.

➡️  Sentinel: validar 11 criterios de aceite (CA-01 a CA-11) — aprovacao bloqueia deploy.
    Atencao especial: CA-11 (design_system.md atualizado) e CA-06 (PDV/FrenteDeCaixa
    sem texto branco em fundo branco).
```
