# Especificação UI Hotfix — UidCore (Manutenção #63)

**Pacote:** [NUCLEO 2/5] — RBAC (perfis `FINANCEIRO`/`PROFISSIONAL`)
**Natureza desta fase:** 100% lógica de visibilidade/roteamento + 1 combobox. **Nenhuma tela nova, nenhum componente novo.** Brush aqui só confirma que os componentes existentes já cobrem o caso e aponta os 2 ajustes de camada visual que a Especificacao_Hotfix.md não detalhou (helpText do select não renderiza hoje; badge de perfil sem cor própria).
**Sobrescreve:** versão anterior deste arquivo era da Manutenção #62 (auditoria BaseModel/AuditFooter) — conteúdo totalmente substituído, sem relação com esta fase.

---

## Design System do Projeto (referência — não alterado nesta fase)

- **Modo:** Padrão Uid adaptado — tema **claro** (divergência documentada em `design_system.md`, não corrigir aqui)
- **Cores primárias:** `primary-600` (#2563eb) ação/link/tab ativa · `primary-700` hover · `primary-50`/`primary-100` fundos leves
- **Cores de fundo:** `bg-gray-50` (app) · `bg-white` (cards/header) · Sidebar `bg-gray-900` (dark mode: `navy-900`/`navy-950`, já convertida desde a Manutenção #31)
- **Fonte:** nenhuma Uid configurada ainda (divergência pré-existente, fora de escopo desta fase — não tocar `tailwind.config.js`/`index.html` por isto)
- **BorderRadius padrão:** `rounded-lg` (inputs, nav items, botões) · `rounded-xl` (Card) · `rounded-2xl` (Modal) · `rounded-full` (badge, paginação)
- **Padrão de badge:** `text-xs font-medium rounded-full px-2 py-0.5` — variante default `bg-primary-50 text-primary-700` (claro) / `bg-violet-900/30 text-violet-300` (escuro); variante `gold` (só `SUPERADMIN`) usa `bg-amber-50 text-amber-800 ring-1 ring-amber-300` + ícone `Crown`
- **Ícones de navegação (Sidebar):** emoji, não Lucide — migração para Lucide é dívida técnica já registrada em `design_system.md`, **fora de escopo desta manutenção** (nenhum item de menu novo é criado; só a regra de visibilidade dos existentes muda)
- **Mobile:** Sidebar reaproveitada como drawer off-canvas (`AppLayout.jsx`, já existente) — qualquer mudança no array `navItems`/filtro em `Sidebar.jsx` vale automaticamente para mobile e desktop, é o **mesmo componente** nos dois `<div>` (`hidden md:flex` e o `fixed ... md:hidden`). Nenhum ajuste adicional necessário.

---

## Especificação Visual por Componente

### 1. `Sidebar.jsx` — troca de flags booleanas por `requer`

**Nada muda visualmente.** Os itens afetados continuam com o mesmo emoji, mesmo texto, mesmas classes de estado ativo/inativo (`bg-primary-600 dark:bg-violet-600 text-white` quando ativo; `text-gray-400 hover:bg-gray-700 hover:text-white dark:hover:bg-navy-700` quando inativo). A única mudança é **qual perfil enxerga qual item** — pura lógica de filtro, zero CSS novo.

**Itens e sua condição de visibilidade (consolidado — Especificacao_Hotfix.md §3.2 já define o `requer`, aqui só confirmo que não precisa de ícone/estilo novo):**

| Item | Emoji (mantido) | Condição |
|---|---|---|
| Dashboard, Clientes, Fornecedores, Vendas, Produtos, Pagamentos, Administrativo, Agendamento, Portal do Cliente | 📊 👥 🏭 🛒 📦 💳 📁 📅 🌐 | sempre visível (sem mudança) |
| Compras | 🧾 | `requer: 'financeiro'` → visível para `tem_acesso_total \|\| perfil === 'FINANCEIRO'` |
| Financeiro | 💰 | `requer: 'financeiro'` (novo filtro — hoje não tinha nenhum) |
| Conciliação | 🔄 | `requer: 'financeiro'` (novo filtro) |
| Marketing | 📣 | `requer: 'marketing'` (sem mudança de comportamento, só de implementação — usa selector central) |
| RH | 👔 | `requer: 'staff'` (novo filtro — item nunca teve guarda nenhuma até hoje) |
| Usuários | 👤 | `requer: 'staff'` (sem mudança de comportamento) |

**Ordem do array `navItems` não muda.** Não reordenar por perfil — a Sidebar é uma lista fixa que apenas esconde/mostra, nunca reordena (evita o usuário perder a referência espacial do menu entre uma sessão e outra).

**Estado vazio não se aplica aqui** — mesmo um usuário `PROFISSIONAL` (o perfil com menos itens visíveis: Dashboard, Clientes, Vendas, Produtos, Pagamentos, Administrativo, Agendamento, Portal) continua com pelo menos 8 itens — não há risco de Sidebar "vazia" a especificar.

### 2. `routes/index.jsx` — `FinanceiroRoute` novo + `/rh` ganha `StaffRoute`

**Nada visual aqui também.** Comportamento de redirecionamento é `<Navigate to="/dashboard" replace />` silencioso — **mesmo padrão exato já usado por `StaffRoute`/`MarketingRoute` hoje**, decisão deliberada de manter consistência, não uma lacuna a corrigir nesta fase:

- Não existe mecanismo de toast global no projeto (o `showToast` atual é local a cada instância de `ResourceCrud.jsx`, não acessível em `routes/index.jsx`) — criar um toast global só para este redirect seria infraestrutura nova fora do escopo da Especificacao_Hotfix.md (que não pede isso) e da Manutenção #63 (RBAC, não UX de notificação).
- Se um usuário `PROFISSIONAL`/`FINANCEIRO` digitar `/rh` ou `/financeiro` direto na URL sem ter o item no menu, ele simplesmente "bate" de volta no Dashboard — mesma experiência que `OPERACIONAL` já tem hoje ao tentar `/usuarios`. Não é regressão, é extensão do padrão existente.
- **Registrado para backlog futuro** (não bloqueia CA-15): se a Uid padronizar um toast global de "Acesso restrito" em outra manutenção, aplicar retroativamente em `StaffRoute`/`MarketingRoute`/`FinanceiroRoute` ao mesmo tempo, para não ficar inconsistente entre as 3 guards.

### 3. `Usuarios.jsx` — combobox de Perfil com `FINANCEIRO`/`PROFISSIONAL`

**3.1 Opções do select (`PERFIL_OPTIONS`):**

```
Admin
Operacional
Financeiro        ← novo
Profissional      ← novo
Marketing
👑 Superadmin
```

Ordem: inserir `Financeiro` e `Profissional` **entre `Operacional` e `Marketing`** (não no fim da lista) — agrupa visualmente os 4 perfis "de uso diário" (Admin, Operacional, Financeiro, Profissional) antes dos 2 perfis "especiais" (Marketing, que já tem posição própria; Superadmin, sempre por último e com ícone 👑 como já é hoje). Nenhum emoji novo nos dois perfis novos — `Financeiro`/`Profissional` seguem o padrão neutro de `Admin`/`Operacional`/`Marketing` (só `Superadmin` leva emoji, é o único com badge "gold").

**3.2 Badge da coluna "Perfil" na tabela (`columns` → `badgeColorMap`):**

```js
badgeColorMap: {
  SUPERADMIN: 'gold',
  ADMIN: 'violet',
  OPERACIONAL: 'neutral',
  FINANCEIRO: 'violet',       // novo — perfil com permissão elevada em módulo sensível (dinheiro), mesma categoria visual de ADMIN
  PROFISSIONAL: 'neutral',    // novo — perfil de uso operacional, mesma categoria visual de OPERACIONAL/MARKETING
  MARKETING: 'neutral',
}
```

**Nota para o Loom:** hoje `renderCell` em `ResourceCrud.jsx` só diferencia visualmente a variante `'gold'` (ring âmbar + ícone `Crown`) — qualquer outro valor de `badgeColorMap` (incluindo `'violet'` e `'neutral'`) cai no mesmo badge default (`bg-primary-50 text-primary-700` / `dark:bg-violet-900/30 dark:text-violet-300`). Isso **já é o comportamento atual** para `ADMIN`/`OPERACIONAL`/`MARKETING` — logo `FINANCEIRO`/`PROFISSIONAL` ficarem com a mesma aparência visual entre si e com os demais não-Superadmin é **esperado, não um bug a corrigir nesta fase**. Os valores `'violet'`/`'neutral'` no mapa servem só como metadado de intenção para o código (documentação interna), sem efeito visual diferenciado hoje. Não expandir `renderCell` com variantes novas de cor nesta manutenção — fora de escopo (a Especificacao_Hotfix.md não pede diferenciação de cor por perfil, só a listagem correta no combobox).

**3.3 `helpText` do campo `perfil` — ajuste obrigatório no componente, não só na página**

A Especificacao_Hotfix.md (§3.4) pede `helpText` estático no campo `perfil`, "mesmo padrão já usado no campo `password`". **Isso não é verdade para campos `type: 'select'` no estado atual de `ResourceCrud.jsx`** — Brush confirmou lendo o código-fonte:

```js
// renderField() em ResourceCrud.jsx, hoje:
if (f.type === 'select') {
  return <Select {...commonProps} options={f.options} />   // f.helpText NUNCA é lido aqui
}
...
// só o branch default (campos sem type especial — ex. password, text) faz:
{f.helpText && (
  <p className="text-xs text-gray-400 mt-1 dark:text-slate-500">
    {typeof f.helpText === 'function' ? f.helpText(!!editingId) : f.helpText}
  </p>
)}
```

Se o Loom só adicionar a prop `helpText` no objeto do campo `perfil` em `Usuarios.jsx` (como a Especificacao_Hotfix.md literalmente mostra), **o texto não aparece em tela** — vira prop morta. O fix tem que tocar o branch `f.type === 'select'` dentro de `ResourceCrud.jsx`, replicando o mesmo parágrafo de ajuda usado no branch default:

```jsx
if (f.type === 'select') {
  return (
    <div key={f.name} className={f.colSpan2 ? 'sm:col-span-2' : undefined}>
      <Select {...commonProps} options={f.options} />
      {f.helpText && (
        <p className="text-xs text-gray-400 mt-1 dark:text-slate-500">
          {typeof f.helpText === 'function' ? f.helpText(!!editingId) : f.helpText}
        </p>
      )}
    </div>
  )
}
```

Isso é uma extensão genérica do componente (qualquer campo `select` futuro em qualquer outra página ganha a capacidade de ter `helpText`), não um hack específico de `Usuarios.jsx` — mesma filosofia de componente reutilizável já seguida no resto do `ResourceCrud.jsx`.

**3.4 Texto e tipografia do `helpText`:**

- Classe: `text-xs text-gray-400 dark:text-slate-500` (idêntica ao `helpText` do campo `password` já existente — nenhuma classe nova)
- Posição: imediatamente abaixo do `<select>`, dentro do mesmo grupo de campo (`sm:col-span-2` se o form usar grid — `perfil` hoje não tem `colSpan2`, então ocupa só 1 coluna do grid 2 colunas do modal; o texto de ajuda, sendo mais longo que o campo, vai quebrar linha naturalmente dentro da largura da coluna — comportamento aceitável, mesmo texto cabe em ~3 linhas a 320px de largura de coluna)
- Conteúdo (definido pela Especificacao_Hotfix.md, Brush só confirma formatação — sem alteração de texto):
  ```
  Admin/Superadmin: acesso total. Operacional: uso geral do sistema.
  Financeiro: financeiro, pagamentos, compras e fornecedores — sem
  Usuários/RH/Marketing. Profissional: agenda própria e clientes em
  leitura — sem financeiro/compras/RH/PDV. Marketing: campanhas e leads.
  ```
- Sem ícone, sem cor de destaque — é texto de apoio neutro, não um aviso (não usar `text-yellow-700`/ícone de alerta; isso é reservado para mensagens de risco real, ex. o `window.confirm` de autobloqueio que já existe em `onBeforeSubmit`)

**3.5 Mobile (375px):** `ResourceCrud` já abre o form em `Modal` com `max-w-lg`/grid responsivo (`grid-cols-1 sm:grid-cols-2`) — em telas < 640px o campo `perfil` ocupa 100% da largura do modal, o `helpText` quebra em mais linhas (texto mais longo relativo à largura), sem necessidade de truncamento ou tooltip. Nenhum ajuste de breakpoint novo necessário.

### 4. Telas que **não** precisam de nenhuma mudança visual (confirmação explícita do Brush)

Para não deixar dúvida pro Loom sobre o que NÃO tocar:

- **`Financeiro.jsx`, `Compras.jsx`, `Rh.jsx`, `Produtos.jsx`, `Pagamentos.jsx`, `Fornecedores.jsx`, `Agendamento.jsx`, `Clientes.jsx`, `Dashboard.jsx`** — zero alteração de JSX/CSS. O 403 de permissão já é tratado pelo fluxo de erro padrão existente (`extractErrorMessage` + toast local de cada página/`ResourceCrud`) — nenhuma tela nova de "acesso negado" a desenhar.
- **`Agendamento.jsx`** especificamente: o filtro de queryset para `PROFISSIONAL` (RF-07/RF-08 da Especificacao_Hotfix.md) é feito **inteiramente no backend** (`get_queryset`) — a tela já renderiza "o que a API devolve", sem saber nem precisar saber que existe um filtro por perfil. Nenhuma coluna, filtro de UI ou aviso novo a adicionar.
- **`Clientes.jsx`**: o bloqueio de escrita para `PROFISSIONAL` puro (RF-06) também é só backend (403 em POST/PATCH/DELETE) — o botão "+ Novo Cliente"/ações de editar continuam visíveis para todo mundo (a Especificacao_Hotfix.md não pede escondê-los condicionalmente); se um `PROFISSIONAL` clicar, recebe o toast de erro padrão do `ResourceCrud` com a mensagem que vier da API. **Não esconder os botões de escrita condicionalmente ao perfil nesta fase** — fora de escopo, a Especificacao_Hotfix.md trata isso como validação de backend, não como adaptação de UI por perfil (e esconder o botão sem o usuário entender por quê violaria o princípio Uid de feedback claro — melhor ele tentar e ver a mensagem do que não entender por que a opção nem aparece).

---

## Resumo de componentes reutilizados vs. padrões novos

- **Componentes existentes reutilizados (sem alteração):** `NavLink`/estrutura de `Sidebar.jsx`, `Navigate`/padrão de Route guard, `Select.jsx`, `Input.jsx` (padrão de `helpText` copiado), badge default do `ResourceCrud.jsx`, `Modal`/grid responsivo do form de `ResourceCrud.jsx`
- **Extensão de componente necessária (não é componente novo, é o mesmo `ResourceCrud.jsx` ganhando uma capacidade que já tinha para outros tipos de campo):** branch `f.type === 'select'` em `renderField()` passa a renderizar `helpText`, igual ao branch default
- **Padrão novo:** nenhum — zero ADR de design necessário, zero exceção ao padrão Uid

---

## Passagem de bastão

```
✅ Especificação UI concluída — UidCore (Manutenção #63)
   Telas analisadas: 2 (Sidebar.jsx, Usuarios.jsx) + 1 arquivo de rotas (sem tela própria)
   Componentes reutilizados: 6 existentes (Select, Input, Modal, badge default, NavLink, Route guard)
   Novos padrões: 0
   Extensão necessária em componente genérico: 1 (ResourceCrud.jsx — helpText em campos select)

📁 Arquivo: Especificacao_UI_Hotfix.md (em /var/www/uidcore/, sobrescreve versão da Manutenção #62)

➡️ Loom lê Especificacao_Hotfix.md + Especificacao_UI_Hotfix.md antes de implementar o frontend.
   Atenção especial ao item 3.3 — sem o ajuste em ResourceCrud.jsx, o helpText do campo
   perfil fica mudo em produção mesmo com o código "parecendo certo" na página Usuarios.jsx.
```
