# Especificação UI Hotfix — UidCore (Manutenção #44)
**Elaborado por:** Brush (MODO HOTFIX)
**Data:** 2026-08-19
**Base:** `Especificacao_Hotfix.md` (Analista, Manutenção #44 — gestão de Usuários +
vínculo Colaborador→Usuário: tela nova `Usuarios.jsx`, ajustes em `Rh.jsx` aba
Colaboradores, extensão de `ResourceCrud.jsx` via RF-08)

---

## Design System do Projeto (referência)

UidCore é **light mode por padrão com dark mode completo opt-in** (Manutenção #31 —
toggle ☀️/🌙 no Header, `useTheme.js`, `localStorage` chave `uidcore-theme`, padrão
escuro na 1ª visita). Toda tela nova segue os dois modos lado a lado — nunca só um.

- **Cores primárias:** `primary-600` (#2563eb, light) / `violet-600` (dark) — botões
  primários, item ativo da Sidebar, foco de inputs (`focus:ring-primary-500` /
  `dark:focus:ring-violet-500`)
- **Cores de fundo:** `bg-white` / `dark:bg-navy-800` (cards, modal), `bg-gray-50` /
  `dark:bg-navy-900` (header de tabela, seções agrupadas), `bg-gray-900` /
  `dark:bg-navy-900` (Sidebar)
- **Bordas:** `border-gray-200` / `dark:border-navy-600` (cards), `border-gray-300` /
  `dark:border-navy-500` (inputs/selects)
- **Texto:** `text-gray-900` / `dark:text-slate-100` (títulos, primeira coluna),
  `text-gray-600` / `dark:text-slate-400` (corpo, colunas), `text-gray-400` /
  `dark:text-slate-500` (placeholder, vazio, "—")
- **Feedback:** `bg-red-600` (toast erro, botão `danger`), `bg-accent-600` (toast
  sucesso), `bg-green-50 text-green-700` / `dark:bg-emerald-950/40 dark:text-emerald-300`
  (badge positivo "Sim"), `bg-gray-100 text-gray-500` / `dark:bg-navy-700
  dark:text-slate-500` (badge negativo "Não"), `bg-primary-50 text-primary-700` /
  `dark:bg-violet-900/30 dark:text-violet-300` (badge neutro/label)
- **Fonte:** Plus Jakarta Sans (títulos) + DM Sans (corpo) — herdadas globalmente,
  nenhum ajuste nesta manutenção
- **BorderRadius:** `rounded-lg` (botões, inputs, seções), `rounded-xl` (cards),
  `rounded-2xl` (modal), `rounded-full` (badges/pills)
- **Ícones:** projeto usa **dois padrões coexistentes e intencionais** — Sidebar usa
  emoji (`👥`, `👔`, `📊`...) desde a origem (DIV-UI03, decisão de projeto já
  documentada, não mexer); páginas individuais usam `lucide-react` para ícones
  inline de formulário/lista (`User`, `Building2`, `Plus`, `Trash2`, `ArrowRight`,
  `Search`, `Edit`, `ChevronDown`). Esta manutenção segue os dois: item novo na
  Sidebar = emoji (RF-06 já sugere `👤`); ícones dentro de `Usuarios.jsx` e do
  formulário de Colaborador = Lucide, como em `Clientes.jsx`/`Fornecedores.jsx`.

---

## Escopo desta manutenção (confirmação do Brush)

Lida `Especificacao_Hotfix.md` (RF-01 a RF-08, RN-01 a RN-11): a maior parte é
backend/lógica. A camada visual real fica em três frentes — (1) tela nova
`Usuarios.jsx`, (2) ajustes em `Rh.jsx` aba Colaboradores (colunas + formulário
condicional), (3) as 4 capacidades novas de `ResourceCrud.jsx` (RF-08) precisam de
um comportamento visual concreto para o Loom implementar sem inventar padrão do
zero. Nenhum componente novo de UI é necessário além de um botão de ação de linha
e um bloco de "mostrar senha" — ambos descritos abaixo reaproveitando
`Button`/`Input` existentes, sem criar arquivo novo em `components/ui/`.

---

## Especificação Visual por Tela

### `Usuarios.jsx` (nova) — rota `/usuarios`

**Layout geral:**
- Página inteira, não modal — mesmo padrão estrutural de `Clientes.jsx`/`Rh.jsx`:
  header da página (`<h1>` + `<p>` subtítulo) seguido do `ResourceCrud`.
- Estrutura de topo:
  ```jsx
  <div className="space-y-4">
    <div>
      <h1 className="text-2xl font-bold text-gray-900 dark:text-slate-100">Usuários</h1>
      <p className="text-sm text-gray-500 mt-0.5 dark:text-slate-400">
        Gerencie os acessos administrativos ao sistema
      </p>
    </div>
    <ResourceCrud resource="accounts/usuarios" title="Usuários" createLabel="+ Novo Usuário" ... />
  </div>
  ```
- `emptyIcon`: usar `"👤"` (mesmo estilo emoji-como-string já usado em
  `emptyIcon="👔"` no Rh.jsx — `ResourceCrud` renderiza como texto, não como
  componente, então não misturar com Lucide aqui).
- Mobile (375px): nenhum layout novo — `ResourceCrud` já é responsivo
  (`overflow-x-auto` na tabela, modal com `max-h-[90vh] overflow-y-auto`). Não
  alterar a estrutura de tabela/scroll horizontal existente.

**Colunas da tabela (RF-03):**
```
nome_completo (primeira coluna, negrito automático via first:font-medium)
email
colaborador_nome        → renderCell já trata null como "—", nenhum ajuste
is_staff                → { key: 'is_staff', label: 'Admin', boolean: true }
                           (reaproveita o par de badges Sim/Não que ResourceCrud
                           já tem embutido em renderCell — verde para true,
                           cinza para false, sem criar variante nova)
is_active               → { key: 'is_active', label: 'Ativo', boolean: true }
date_joined              → { key: 'date_joined', label: 'Desde', date: true }
```

**Ações por linha (RF-04, usa a extensão `rowActions` do RF-08):**
- Ordem visual, da esquerda pra direita, ao lado da coluna "Ações" existente
  (Editar / Excluir): **Editar → Reenviar acesso → Desativar**.
- Botão "Reenviar acesso": `<Button size="sm" variant="secondary">` com ícone
  `<Mail size={14} />` antes do texto (import `lucide-react`). Só renderiza quando
  `item.is_active === true` (prop `showIf(item)` do RF-08) — quando oculto, some
  da linha por completo, não fica desabilitado/cinza (evita poluir a linha de um
  usuário já desativado).
- Botão "Desativar" é o próprio botão de exclusão do `ResourceCrud`, só que com
  `deleteLabel="Desativar"` (RF-08 item 4) — mesma cor `variant="danger"`
  (`bg-red-600`) já usada para "Excluir" nas outras 15 telas, **texto muda, cor não
  muda** (continua vermelho — é destrutivo o suficiente para exigir atenção, mesmo
  sendo soft-disable).
- `deleteConfirm` customizado (prop já existe em `ResourceCrud`, sem precisar de
  RF-08): `(item) => \`Desativar o acesso de "${item.nome_completo}"? O usuário
  não poderá mais fazer login, mas o registro não será apagado.\`` — deixa a
  semântica de soft-disable explícita no próprio `window.confirm` (RN-09).

**Formulário (criar/editar), grid 2 colunas (`sm:grid-cols-2`, padrão do Modal):**
```
email          — Input type="email", ícone opcional não necessário (Input.jsx
                 não suporta ícone embutido hoje, não adicionar agora)
nome_completo  — Input type="text"
telefone       — Input type="text", sm:col-span-1
password       — Input type="password" (ver bloco "Campo de senha" abaixo)
is_staff       — checkbox (mesmo componente inline que ResourceCrud já renderiza
                 para type:'checkbox' — ícone <Shield size={14} /> ao lado do
                 label "Administrador" é decorativo, opcional; se usado, só
                 dentro do <label>, não altera o layout do checkbox em si)
```
- Texto de apoio do `password` (`<p className="text-xs text-gray-400 mt-1
  dark:text-slate-500">`, mesmo padrão já usado em `file` fields do
  `ResourceCrud`):
  - Criação: "Deixe em branco para enviar link de definição de senha por e-mail."
  - Edição: "Deixe em branco para não alterar a senha atual."
  - Como o texto muda por contexto (criar vs editar) e o `ResourceCrud` não tem
    hoje um slot de `helpText` condicional por campo, usar a mesma mecânica de
    `showIf`/texto estático simples: **duas entradas de field diferentes não são
    necessárias** — um único campo `password` com `helpText` fixo genérico é
    aceitável ("Em branco: mantém a senha atual ou envia link de acesso por
    e-mail, conforme o caso") SE o Loom não quiser estender `ResourceCrud` com
    `helpText` condicional. Preferência do Brush: se for barato, adicionar
    `helpText: (isEditing) => string` como 5ª capacidade opcional do RF-08;
    senão, usar o texto genérico acima — decisão de custo/benefício do Loom, não
    bloqueante.

**Campo de senha — mostrar/ocultar (Eye/EyeOff):**
- Não é obrigatório pelo RF-03, mas é o padrão esperado para qualquer campo
  `type="password"` em 2026 — usar caso o Loom tenha tempo dentro do RF-03/RF-08,
  do contrário `type="password"` puro (sem toggle) já atende ao requisito
  funcional.
- Se implementado: campo `password` vira um wrapper `relative` com o `<Input
  type={showPw ? 'text' : 'password'} className="pr-10" />` e um `<button
  type="button">` absoluto (`absolute right-2 top-[34px] text-gray-400
  hover:text-gray-600 dark:text-slate-500 dark:hover:text-slate-300`) alternando
  `<Eye size={16} />` / `<EyeOff size={16} />`. Não é um componente novo em
  `components/ui/` — inline dentro de `Usuarios.jsx` (mesmo padrão de "widget
  local" já usado no projeto para casos pontuais, ex. toast inline).

**RN-10 (confirmação extra ao remover o próprio `is_staff`):** sem impacto visual
novo — `window.confirm` nativo, mesmo padrão já usado em `handleDelete`. Não
requer modal customizado.

---

### `Rh.jsx` — aba "Colaboradores" (ajustes)

**Colunas novas (RF-05), inseridas após `regime_label` e antes de `salario_atual`
— ordem sugerida para não quebrar o fluxo de leitura (identidade → acesso →
financeiro):**
```
{ key: 'tem_acesso', label: 'Acesso', boolean: true }   → mesmo par de badges Sim/Não
{ key: 'usuario_email', label: 'E-mail de Acesso' }      → renderCell já trata null como "—"
```

**Formulário de criação — bloco "Criar acesso ao sistema" (RF-05, usa `showIf` e
`hideOnEdit` do RF-08):**
- Posição: ao final do array `fields`, depois de `observacoes` — fica como a
  última seção do formulário, separada visualmente por um divisor leve:
  ```jsx
  <div className="sm:col-span-2 pt-2 border-t border-gray-100 dark:border-navy-700" />
  ```
  (usar como um "field" do tipo `divider` se o Loom preferir tipar, ou aplicar a
  borda diretamente no wrapper do checkbox — decisão de implementação, efeito
  visual é o que importa: uma linha fina separando dados cadastrais do bloco de
  acesso).
- Checkbox `criar_usuario`: mesmo componente checkbox que `ResourceCrud` já
  renderiza para `type: 'checkbox'` (ícone opcional `<Lock size={14} />` ao lado
  do label "Criar acesso ao sistema" — mesma lógica decorativa do `is_staff`
  acima, não obrigatório).
- Campos condicionais (aparecem só quando `criar_usuario` está marcado —
  `showIf: (form) => form.criar_usuario`):
  ```
  usuario_email  — Input type="email", label "E-mail de acesso",
                   valor inicial = form.email (pré-preenchido, editável — RN-04)
  usuario_senha  — Input type="password", label "Senha (opcional)",
                   helpText "Deixe em branco para enviar link de definição de
                   senha por e-mail." (mesmo texto do RF-03)
  ```
  Ambos em `sm:col-span-2` dentro do grid de 2 colunas do Modal (`Modal
  maxW="max-w-2xl"` já usado por `ResourceCrud` — não precisa aumentar), ou lado
  a lado (`sm:col-span-1` cada) se o Loom preferir — largura não é crítica aqui,
  o que importa é o `showIf` funcionar e sumir por completo (não só
  `disabled`) quando desmarcado.
- **Formulário de edição:** bloco inteiro (checkbox + campos condicionais) some
  por completo via `hideOnEdit: true` (RN-08) — não renderiza nem colapsado, nem
  desabilitado. Editar um Colaborador não deve dar a impressão de que dá pra
  mudar o acesso por ali.

**RF-07 (validação client-side antes do submit):** sem impacto visual — se
`criar_usuario && !usuario_email`, usar o mesmo `showToast(msg, 'error')` que
`ResourceCrud` já expõe internamente (ou, se a validação for feita em
`Rh.jsx`/wrapper antes de delegar pro `ResourceCrud`, replicar o toast local já
usado em `Produtos.jsx`/`Vendas.jsx` — mesmo estilo: `fixed top-4 right-4 z-50
max-w-sm ... bg-red-600`, 7000ms). Mensagem sugerida: "Informe o e-mail de acesso
para criar o usuário."

---

### `ResourceCrud.jsx` — as 4 capacidades do RF-08 (especificação visual)

| Capacidade | Efeito visual |
|---|---|
| `rowActions` | Botões extras `<Button size="sm">` entre "Editar" e "Excluir/Desativar", mesmo `gap-2` do `flex items-center justify-end` já existente na célula de ações. Cada action pode ter `variant` próprio (`secondary` por padrão, ex. "Reenviar acesso"); ícone opcional antes do label, mesmo padrão `<Icon size={14} />` + texto usado nos botões existentes do projeto (ex. `+ Adicionar Conversao` em Produtos.jsx). |
| `showIf(form)` por field | Campo simplesmente não é renderizado no `<form>` quando a função retorna `false` — sem placeholder vazio, sem `display:none` (evita o grid `sm:grid-cols-2` deixar buraco); reavaliar a cada `setForm` (input controlado, já é o comportamento natural de um componente React condicional). |
| `hideOnEdit` por field | Mesma mecânica de `showIf`, mas a condição é fixa: `editingId != null`. Visualmente idêntico — campo some por completo do grid ao abrir o modal em modo edição. |
| `deleteLabel` | Só troca o texto do `<Button variant="danger">` (de "Excluir" para o valor customizado, ex. "Desativar") — mesma cor, mesmo tamanho, mesma posição. Default permanece `"Excluir"` para as 15+ telas existentes (nenhuma muda de aparência). |

Nenhum token novo de cor, espaçamento ou raio é necessário para essas 4
capacidades — todas reaproveitam classes já presentes em `Button.jsx`/
`ResourceCrud.jsx`.

---

### `Sidebar.jsx` — item "Usuários" (RF-06)

- Inserido no array `navItems`, logo após o item `{ to: '/rh', label: 'RH', icon:
  '👔' }` (mesma área temática de gestão interna, conforme já indicado na
  Especificação técnica):
  ```js
  { to: '/usuarios', label: 'Usuários', icon: '👤' }
  ```
- Renderização condicional: `navItems` vira uma função/filtro que remove esse item
  quando `useAuthStore(s => s.user?.is_staff)` for falso — **não** renderizar o
  item desabilitado/cinza, ele deve **não existir** no DOM para usuário comum
  (mesmo princípio do "Reenviar acesso" acima: ausência, não estado disabled).
- Nenhuma mudança visual no restante da Sidebar (largura, collapse, cores) —
  o item novo segue exatamente o mesmo `NavLink`/classes de todos os outros 12
  itens existentes.

---

## Ícones Lucide usados nesta manutenção

| Ícone | Uso | Tamanho |
|---|---|---|
| `Mail` | Botão "Reenviar acesso" (linha da tabela, Usuarios.jsx) | 14px |
| `Shield` | Decorativo, ao lado do label "Administrador" (checkbox is_staff) | 14px |
| `Lock` | Decorativo, ao lado do label "Criar acesso ao sistema" (checkbox criar_usuario) | 14px |
| `Eye` / `EyeOff` | Toggle mostrar/ocultar senha (opcional, se implementado) | 16px |
| `Users` | Reservado para o header da página `Usuarios.jsx` se o Loom quiser um ícone ao lado do `<h1>` (opcional — `Clientes.jsx`/`Rh.jsx` não usam ícone no `<h1>` hoje, então **não obrigatório**, manter consistência de não usar se as outras páginas não usam) | 20px se usado |

Todos importados de `lucide-react`, mesmo padrão de `import { X, Y } from
'lucide-react'` já usado em `Clientes.jsx`/`Fornecedores.jsx`/`Vendas.jsx`/
`Produtos.jsx`.

---

## Componentes reutilizados

| Componente | Origem | Uso nesta manutenção |
|---|---|---|
| `ResourceCrud` | `components/ui/ResourceCrud.jsx` | Base de `Usuarios.jsx` (novo) + já usado por `Rh.jsx` (estendido via RF-08) |
| `Card`, `Button`, `Input`, `Select`, `Modal`, `Pagination` | `components/ui/` | Todos herdados via `ResourceCrud`, nenhum uso direto novo fora dele |
| Badge Sim/Não (boolean) | Inline em `ResourceCrud.renderCell` | `is_staff`, `is_active` (Usuarios.jsx) e `tem_acesso` (Rh.jsx) — nenhuma variante nova |
| Toast inline | Inline em `ResourceCrud` (já existente) | Sucesso/erro de CRUD padrão, reaproveitado sem mudança |

**Nenhum componente novo criado em `components/ui/`.** As únicas peças de UI sem
precedente direto no projeto são o botão "Reenviar acesso" (resolvido via
`rowActions`, RF-08) e o toggle de senha (opcional, inline, sem novo arquivo).

---

## Mobile-first (375px)

- `Usuarios.jsx`: mesma estrutura de `Clientes.jsx`/`Rh.jsx` — tabela com
  `overflow-x-auto`, modal `max-h-[90vh] overflow-y-auto`, formulário em
  `grid-cols-1` abaixo do breakpoint `sm` (640px), virando `sm:grid-cols-2` acima.
  Nenhum ajuste de breakpoint novo necessário.
- Botões de ação por linha (`rowActions` + Editar + Desativar): em telas muito
  estreitas, a célula de ações pode ficar com 3 botões lado a lado — já é o
  comportamento aceito no projeto (`overflow-x-auto` no container da tabela
  permite rolagem horizontal, mesmo padrão de outras telas com múltiplas ações).
  Não introduzir menu "..." (kebab) nesta manutenção — fora de escopo, manter
  simples como o resto do projeto.
- Bloco condicional de acesso em `Rh.jsx`: campos em `sm:col-span-2` empilham
  naturalmente em telas pequenas, sem necessidade de tratamento especial.
- ⚠️ Lembrete de regra global: **nenhuma tela nova usa `overflow-hidden` no root**
  — `Usuarios.jsx` segue o `AppLayout` existente sem alterá-lo.

---

## Passagem de bastão

```
✅ Especificação UI concluída — UidCore (Manutenção #44)
   Telas analisadas: 2 (Usuarios.jsx — nova; Rh.jsx aba Colaboradores — ajustes)
   Componentes reutilizados: 6 (ResourceCrud, Card, Button, Input, Select, Modal)
   Novos padrões visuais: 0 tokens novos — reaproveita paleta navy/violet dark
   mode (Manutenção #31) e badges boolean já existentes em ResourceCrud
   Novos ícones Lucide: Mail, Shield, Lock, Eye/EyeOff (Users opcional)
   Extensões de componente especificadas: rowActions, showIf, hideOnEdit,
   deleteLabel (RF-08) — efeito visual de cada uma detalhado acima

📁 Arquivo: Especificacao_UI_Hotfix.md (neste diretório)

➡️ Loom lê Especificacao_Hotfix.md + Especificacao_UI_Hotfix.md antes de
   implementar RF-03 a RF-08 — nenhum componente novo em components/ui/
   necessário, apenas extensão aditiva de ResourceCrud.jsx e composição dos
   componentes existentes em Usuarios.jsx (nova) e Rh.jsx (ajustes).
```
