# Especificação UI Hotfix — UidCore (Manutenção #60)

**Origem:** `Especificacao_Hotfix.md` (Analista) — hardening de RBAC: introduz `PerfilUsuario.SUPERADMIN`,
unifica checagem de negócio em `tem_acesso_total`, remove `is_staff` do formulário/coluna da tela de
Usuários, adiciona 4ª opção de perfil com distinção visual.

**Nota:** este arquivo substitui a versão anterior (Manutenção #58, Fase 2 — módulo Compras). Conteúdo
anterior preservado no histórico de commits do git, não neste documento (mesmo padrão já usado entre
Fase 1 → Fase 2 do #58).

**Modo:** HOTFIX — sistema já tem identidade visual definida (dark mode navy/violet, Manutenção #31).
Esta especificação NÃO cria design system novo — só adiciona a camada visual sobre o que o Analista
já especificou.

---

## Design System do Projeto (referência — já em produção, não recriar)

- **Cores primárias (light):** `primary-*` (azul, base `#3b82f6`/`#2563eb`) — botões, links, foco de input
- **Cores de destaque (accent):** `accent-*` (verde, base `#10b981`) — sucesso, toasts de sucesso
- **Dark mode — superfícies:** `navy-950` (fundo app) → `navy-900` (sidebar/header) → `navy-800` (cards/inputs) → `navy-700` (bordas/hover) → `navy-600`/`navy-500` (bordas mais claras)
- **Dark mode — ação/destaque:** `violet-*` (base `#8b5cf6`/`#7c3aed`) — substitui `primary` no dark mode (botões, foco, badges, item ativo da Sidebar)
- **Fonte:** Plus Jakarta Sans (display) + DM Sans (body) — já configuradas, não mexer
- **BorderRadius padrão:** `rounded-lg` (8px) em inputs/botões/cards, `rounded-full` (pill) em badges e ícones de status
- **Padrão de card:** `Card.jsx` existente — fundo branco/`navy-800`, borda sutil, usado como wrapper da tabela
- **Padrão de badge (já existe em `ResourceCrud.jsx::renderCell`):** `col.badge === true` → pill `text-xs`, `bg-primary-50 text-primary-700` (light) / `dark:bg-violet-900/30 dark:text-violet-300` (dark) — hoje é **uma cor única para qualquer valor** da coluna
- **Padrão boolean (Sim/Não):** pill verde (`bg-green-50 text-green-700` / `dark:bg-emerald-950/40 dark:text-emerald-300`) para `true`, pill cinza para `false`
- **Ícones:** Lucide React, já em uso em `Usuarios.jsx` (`Mail`) e demais páginas (`User`, `Pencil`, `Trash2` etc.)
- **Sidebar:** ícones em **emoji**, não Lucide — decisão de projeto já documentada (DIV-UI03, Manutenção #10) e reafirmada no histórico de #31. Não alterar para Lucide nesta manutenção — fora de escopo, o Analista confirmou que Sidebar não tem mudança visual.

---

## Especificação Visual por Tela

### 1. `Usuarios.jsx`

Único arquivo com mudança visual real nesta manutenção. Escopo: (a) remover checkbox
Administrador do formulário; (b) 4ª opção "Superadmin" no dropdown Perfil, com badge visual
diferenciado tanto no `<select>` quanto na coluna da tabela; (c) esconder/desabilitar a opção
Superadmin quando quem está logado não é SUPERADMIN.

**Layout geral:** sem mudança — mantém header da página (`h1` + subtítulo) + `ResourceCrud` genérico
já em produção. Nenhuma alteração de estrutura de página, só do schema `columns`/`fields` passado ao
`ResourceCrud`.

**Coluna "Perfil" na tabela (`columns`, badge):**

O componente genérico `ResourceCrud::renderCell` hoje trata `col.badge` como uma cor única (violet/primary)
para qualquer valor. Isso não é suficiente para o requisito de "badge visual diferenciado" do Superadmin —
**introduzir suporte a cor por valor** na coluna `perfil`, sem quebrar as outras telas que já usam
`badge: true` com uma cor só (retrocompatibilidade: se a coluna não declarar mapa de cores, cai no
estilo atual).

- Prop nova sugerida na coluna: `badgeColorMap: { SUPERADMIN: 'gold', ADMIN: 'violet', OPERACIONAL: 'neutral', MARKETING: 'neutral' }` (chave = valor bruto do campo, não a label)
- Estilos por variante (Tailwind, sem exigir novo token no `tailwind.config.js` — usa escalas padrão do Tailwind já disponíveis no build):
  - `SUPERADMIN` ("gold"): `bg-amber-50 text-amber-800 ring-1 ring-amber-300` (light) / `dark:bg-amber-500/15 dark:text-amber-300 dark:ring-amber-400/30` (dark) — cor quente, deliberadamente fora da paleta azul/violeta usada por tudo mais na tela, para saltar aos olhos como nível excepcional
  - `ADMIN`/demais perfis ("violet"/padrão atual): mantém `bg-primary-50 text-primary-700` / `dark:bg-violet-900/30 dark:text-violet-300` — **sem alteração**
- Ícone: badge do `SUPERADMIN` ganha `<Crown size={11} />` (lucide-react) antes do texto, badge dos demais perfis continua só texto (sem ícone) — reforça a diferenciação sem exigir nova paleta
- Badge do Superadmin: `inline-flex items-center gap-1` para acomodar ícone + texto, mesmo `rounded-full px-2 py-0.5 text-xs font-medium` das demais

**Dropdown "Perfil" no formulário (`fields`, type select):**

- 4ª opção adicionada ao array `options` do `Select.jsx` existente (sem alterar o componente `Select`):
  `{ value: 'SUPERADMIN', label: '👑 Superadmin' }` — usar o emoji 👑 diretamente na `label` do `<option>`
  é o único jeito de dar destaque visual dentro de um `<select>` nativo do HTML (não é possível estilizar
  `<option>` individualmente com Tailwind/CSS de forma confiável entre navegadores) — mesma lógica de
  "emoji como diferenciador visual leve" já usada na Sidebar (DIV-UI03)
- Opção Superadmin no dropdown deve ser **condicional** conforme quem está logado:
  - Se `currentUser.perfil === 'SUPERADMIN'`: opção aparece normalmente, selecionável
  - Se `currentUser.perfil !== 'SUPERADMIN'`: opção **não aparece na lista** de `options` (filtrar antes de passar pro `Select`, não usar `disabled` no `<option>` — mais simples e evita usuário tentar selecionar e levar erro 400 do backend por RF-06; a validação do backend continua existindo como defesa em profundidade, mas a UI não deve nem oferecer a opção)
  - Exceção: se o registro sendo **editado** já é `SUPERADMIN` e quem edita não é SUPERADMIN, a ação de edição inteira já é bloqueada pelo backend (RN-03/CA-13) — não há necessidade de tratamento visual extra além do erro padrão já exibido pelo `ResourceCrud` (toast vermelho via `extractErrorMessage`, padrão já em produção)
- Fonte da verdade de "quem está logado": `useAuthStore.getState().user` (mesmo padrão já usado em `onBeforeSubmit`) — ler `perfil` do usuário atual, não `is_staff` (RN-02 é sobre `perfil === SUPERADMIN`, não sobre `tem_acesso_total`)

**Checkbox "Administrador" removido:**

- Campo `{ name: 'is_staff', label: 'Administrador', type: 'checkbox' }` sai do array `fields` — sem substituto visual, o dropdown Perfil (com a 4ª opção) passa a cobrir o espectro de acesso administrativo
- Espaçamento do form: `ResourceCrud` usa grid responsivo padrão (`sm:col-span-2` opcional por campo) — remover o checkbox não deixa buraco no layout porque o grid re-flui automaticamente; não precisa de campo "placeholder" nem ajuste manual de grid

**Coluna "Admin" → "Acesso total" (RF-11):**

- Mesma posição na tabela, mesmo estilo boolean (Sim/Não) já existente em `renderCell` — só troca `key: 'is_staff'` → `key: 'tem_acesso_total'` e `label: 'Admin'` → `label: 'Acesso total'`. Nenhuma mudança visual de estilo, é o mesmo pill verde/cinza que já existe.

**Mobile-first (375px):**

- Tabela do `ResourceCrud` já usa `overflow-x-auto` no wrapper (`Card.jsx` + `-mx-6 -my-4`) — comportamento existente, sem alteração. Coluna "Perfil" com badge dourado do Superadmin deve continuar cabendo em `whitespace-nowrap` (ícone `Crown` em 11px + texto curto "Superadmin" — testar que não quebra linha em 375px)
- Modal do formulário (`Modal.jsx`) já é responsivo (campos empilham em coluna única abaixo do breakpoint `sm`) — dropdown Perfil ocupa a largura total da coluna, sem tratamento extra

**Nenhuma mudança de ícone/espaçamento fora do descrito acima** — o restante da tela (botão "+ Novo Usuário", ação "Reenviar acesso" com ícone `Mail`, botão "Editar", confirmação de "Desativar") permanece idêntico.

---

### 2. `Sidebar.jsx`

**Confirmado pelo Analista: nenhuma mudança visual.** A troca de `isStaff` (lido de `user?.is_staff`)
para `temAcessoTotal` (lido de `useAuthStore(selectTemAcessoTotal)`) é substituição de fonte de dado
para a mesma condição booleana já usada em `visibleItems.filter(...)` — os itens `staffOnly`/`marketingOnly`
continuam os mesmos (`Compras`, `Usuários`, `Marketing`), os emojis continuam os mesmos, a estrutura
do `<nav>` não muda. Brush não tem nada a especificar aqui além de confirmar que não há regressão
visual esperada — Loom deve garantir que a lista de itens visíveis para cada perfil de teste (CA-19)
seja idêntica à observada hoje com `is_staff`.

---

### 3. `HistoricoVendas.jsx` e `RelatorioSessoesCaixa.jsx`

**Confirmado pelo Analista: nenhuma mudança visual.** As 5 ocorrências (`user?.is_staff` /
`user.is_staff`) trocam para `user?.tem_acesso_total` / `user.tem_acesso_total` mantendo exatamente
as mesmas condicionais de exibição/ocultação de ações e colunas restritas a admin já implementadas —
é troca de fonte de dado, não de comportamento visual. Nenhum componente, ícone, cor ou espaçamento
muda. Loom deve validar visualmente (CA-21) que a experiência de um usuário com `tem_acesso_total=True`
via `perfil=ADMIN` (sem `is_staff`) é idêntica à de um `is_staff=True` legado — nenhuma tela nova, nenhum
elemento oculto/exibido a mais ou a menos.

---

## Componentes reutilizados (nenhum novo criado)

- `ResourceCrud.jsx` — reutilizado integralmente; só o schema `columns`/`fields` passado por `Usuarios.jsx` muda
- `Select.jsx` — reutilizado sem alteração de componente; só a lista de `options` passada muda (filtrada dinamicamente conforme perfil de quem está logado)
- `Card.jsx`, `Button.jsx`, `Modal.jsx`, `Pagination.jsx` — sem alteração
- **Extensão pontual necessária em `ResourceCrud.jsx::renderCell`** (única peça de "componente" que precisa de código novo, não é componente novo): suporte a `col.badgeColorMap` para permitir cor por valor no badge — hoje só existe cor única fixa. Ver detalhamento acima. Retrocompatível: colunas `badge: true` sem `badgeColorMap` continuam exatamente como estão hoje em todas as outras telas (Marketing, Compras, etc.)

## Ícones Lucide novos

- `Crown` (lucide-react) — usado só no badge da coluna Perfil quando `valor === 'SUPERADMIN'`, tamanho 11px

## Dark mode (paleta navy/violet — sem mudança de token)

- Nenhum token novo necessário no `tailwind.config.js`. O badge dourado do Superadmin usa a escala
  `amber-*` padrão do Tailwind (disponível nativamente, não precisa ser adicionada em `theme.extend.colors`)
  tanto no light quanto no dark mode, com opacidade reduzida (`/15`) no dark mode seguindo o mesmo padrão
  já usado por `emerald-950/40` no badge "Sim" — consistente com o restante da tela.
- Contraste mínimo 4.5:1 a verificar por Loom/Sentinel: `text-amber-800` sobre `bg-amber-50` (light) e
  `text-amber-300` sobre `bg-amber-500/15` (dark) — combinação análoga à já aprovada para o badge
  boolean verde existente, deve passar no mesmo padrão de contraste.

---

## Passagem de bastão

```
✅ Especificação UI concluída — UidCore (Manutenção #60)
   Telas analisadas: 4 (Usuarios.jsx, Sidebar.jsx, HistoricoVendas.jsx, RelatorioSessoesCaixa.jsx)
   Telas com mudança visual real: 1 (Usuarios.jsx)
   Componentes reutilizados: 5 existentes (ResourceCrud, Select, Card, Button, Modal)
   Extensão pontual: badgeColorMap em ResourceCrud::renderCell (retrocompatível)
   Novos padrões: badge dourado (amber-*) + ícone Crown para diferenciar Superadmin

📁 Arquivo: Especificacao_UI_Hotfix.md (no worktree)

➡️ Loom lê Especificacao_Hotfix.md + Especificacao_UI_Hotfix.md
   antes de implementar o frontend
```
