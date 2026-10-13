# Especificação UI Hotfix — Manutenção #66 [NUCLEO 5/5]
## LGPD: exportação de dados do titular + anonimização

**Sistema:** UidCore
**Data:** 2026-10-13
**Autor:** Brush (MODO HOTFIX)
**Base:** Especificacao_Hotfix.md (Analista, mesma data)

---

## Design System do Projeto (referência)

O UidCore usa dark mode com classe `dark` no root. Paleta definida em
`frontend/tailwind.config.js` (Manutenção #31):

**Superfícies (navy):**
- `navy-950` (`#0a0f1e`) — fundo da aplicação
- `navy-900` (`#0f1729`) — fundo de blocos secundários dentro de modal
- `navy-800` (`#1a2540`) — cards, modais, tabelas, inputs
- `navy-700` (`#232f4d`) — hover de linhas, bordas de separação
- `navy-600` (`#2a3352`) — bordas de cards e inputs
- `navy-500` (`#3d4a73`) — ícones e elementos de apoio

**Interação (violet):**
- `violet-600` (`#7c3aed`) — botão primário (dark), aba ativa
- `violet-700` (`#6d28d9`) — hover de botão primário (dark)
- `violet-500` (`#8b5cf6`) — destaque de link, badge de ação
- `violet-400` (`#a78bfa`) — texto de label ativo, ícone selecionado

**Texto:**
- `text-slate-100` — texto principal
- `text-slate-400` — texto secundário / labels
- `text-slate-500` — placeholder / muted

**Feedback:**
- Success: `text-emerald-400` / `bg-emerald-400/15`
- Warning: `text-amber-400` / `bg-amber-400/15`
- Error / Perigo: `text-red-400` / `bg-red-400/15` (light: `text-red-700` / `bg-red-50`)

**Fontes:**
- Títulos/labels de peso: `font-sans` (Plus Jakarta Sans), weight 600–800
- Body / dados: `font-body` (DM Sans), weight 400–500

**BorderRadius padrão:**
- Botões: `rounded-lg` (8px)
- Modal: `rounded-2xl`
- Blocos de aviso/cards internos: `rounded-lg`
- Badges: `rounded-full`

**Componentes reutilizáveis a usar (nenhum componente novo de base):**
- `Modal` (`components/ui/Modal.jsx`) — overlay centralizado, `maxW`
  configurável, já em dark mode. Reutilizar para o modal de anonimização.
- `Button` (`components/ui/Button.jsx`) — variantes `primary` / `secondary`
  / `danger`, suporta `loading` e `disabled`.
- `Input` (`components/ui/Input.jsx`) — label + input + error, dark mode
  pronto. Reutilizar para o campo de confirmação por digitação.
- Banner de toast local (`useState({ type, msg })` + bloco fixo) — mesmo
  padrão já usado em `Agendamento.jsx`/`Financeiro.jsx`/`Fornecedores.jsx`.
  **Não** introduzir lib de toast nova.
- `extractErrorMessage` (`utils/errors.js`) — mensagem de erro da API em
  toda falha de exportar/anonimizar.

**Ícones (Lucide React) para esta feature:**

| Ação/Elemento | Ícone | Tamanho |
|---|---|---|
| Aba/menu "LGPD" | `<Shield />` | 14px |
| Exportar dados | `<Download />` | 14–16px |
| Formato PDF | `<FileText />` | 14px (dentro do dropdown/botão) |
| Formato JSON | `<FileJson />` | 14px (dentro do dropdown/botão) |
| Anonimizar titular | `<UserX />` | 14–16px |
| Aviso de irreversibilidade (modal) | `<AlertTriangle />` | 20px, cor de perigo |
| Linha do histórico de exportação | `<History />` | 12px, `text-slate-400` |
| Status "já anonimizado" | `<ShieldCheck />` | 12px, `text-slate-400` |

---

## Tela 1 — Aba "LGPD" na ficha do Cliente (`Clientes.jsx`)

### Integração na tela existente

O modal de edição do Cliente (`Clientes.jsx`, ~linha 524) já tem abas
condicionadas a `editingId` (só aparecem quando o cliente já existe, nunca
em "Novo Cliente"):

```
Dados | Assinaturas
```

Adicionar uma terceira aba na sequência, **visível somente quando
`selectTemAcessoTotal(usuarioLogado)` for `true`** (mesma guarda já usada
desde a Manutenção #60 — perfis sem acesso total não devem nem ver a aba,
pois o backend (RF-05/RF-06) também exige `IsAdmin`/`tem_acesso_total`):

```
Dados | Assinaturas | LGPD
```

Mesmo padrão visual das abas existentes — reutilizar a classe condicional
já escrita no componente, só adicionando o terceiro `<button>`:

```
ativa:   border-violet-500 text-violet-600 dark:text-violet-400
inativa: border-transparent text-gray-400 dark:text-slate-500
         hover:text-gray-600 dark:hover:text-slate-300
comum:   px-3 py-2 text-sm font-medium border-b-2 transition-colors
```

Label da aba: `<Shield size={14} className="inline mr-1 -mt-0.5" /> LGPD`
— único item do conjunto de abas com ícone, para sinalizar visualmente
que é uma área sensível (dado pessoal), diferente do CRUD comum das
outras duas.

### Conteúdo da aba "LGPD" (`AbaLgpdCliente`)

Componente novo, mesmo padrão de `AbaAssinaturasCliente` já existente
(função isolada recebendo `clienteId` e o `cliente` corrente como props,
sem compartilhar estado com o form de edição de "Dados").

**Layout (mobile-first — coluna única sempre; a aba nunca precisa de 2
colunas mesmo em desktop, pois o modal já é `max-w-2xl`):**

```
┌──────────────────────────────────────────────────────────┐
│ Exportação e eliminação de dados (LGPD)                   │  ← título
│ Direitos do titular previstos no art. 18 da LGPD.          │  ← subtítulo
│                                                              │
│ ┌──────────────────────────────────────────────────────┐ │
│ │ [Download] Exportar dados do titular                    │ │  ← card 1
│ │ Gera um relatório completo (cadastro, financeiro,       │ │
│ │ vendas, agendamentos) para entregar ao titular.          │ │
│ │                                                           │ │
│ │  [Button secondary: PDF]   [Button secondary: JSON]     │ │
│ └──────────────────────────────────────────────────────┘ │
│                                                              │
│ ┌──────────────────────────────────────────────────────┐ │
│ │ [UserX] Anonimizar titular         [badge se já feito]  │ │  ← card 2
│ │ Remove dados pessoais permanentemente. Exige             │ │
│ │ exportação prévia. Ação irreversível.                      │ │
│ │                                                           │ │
│ │  [Button danger: Anonimizar titular]                     │ │
│ └──────────────────────────────────────────────────────┘ │
│                                                              │
│ Histórico de exportações                                   │  ← título h4
│ [History] 13/10/2026 14:02 — PDF — por Ana Souza            │  ← lista
│ [History] 10/10/2026 09:15 — JSON — por Luiz Eduardo         │
└──────────────────────────────────────────────────────────┘
```

**Título da seção:**
`text-sm font-semibold text-gray-700 dark:text-slate-200` — "Exportação e
eliminação de dados (LGPD)"

**Subtítulo:**
`text-xs text-gray-400 dark:text-slate-500` — "Direitos do titular
previstos no art. 18 da LGPD (acesso, portabilidade, eliminação)."

**Espaçamento entre blocos:** `space-y-4` no container da aba, mesmo
padrão usado nos demais formulários do projeto.

#### Card "Exportar dados do titular"

```
bg-gray-50 dark:bg-navy-900/50
border border-gray-200 dark:border-navy-700
rounded-lg p-4
```

- Cabeçalho do card: `flex items-center gap-2` —
  `<Download size={16} className="text-primary-600 dark:text-violet-400" />`
  + título `text-sm font-semibold text-gray-700 dark:text-slate-200`
- Descrição: `text-xs text-gray-500 dark:text-slate-400 mt-1 mb-3`
- Botões: `flex gap-2 flex-wrap` (quebra naturalmente em telas estreitas —
  suficiente para mobile, já que o modal tem largura controlada e os dois
  botões cabem lado a lado em ~320px)
  - `<Button variant="secondary" size="sm"><FileText size={14}/> PDF</Button>`
  - `<Button variant="secondary" size="sm"><FileJson size={14}/> JSON</Button>`
- Ação de cada botão: dispara `GET /api/v1/clientes/{id}/exportar/?formato=pdf|json`
  via `api.get(..., { responseType: 'blob' })`, cria link temporário
  (`URL.createObjectURL` + `<a download>`) e dispara o download —
  **nenhum conteúdo renderizado na tela**, conforme RF-08. Enquanto a
  requisição está em voo, apenas o botão clicado entra em `loading`
  (spinner já embutido no `Button`); o outro permanece clicável.
- Erro: toast vermelho padrão do projeto com `extractErrorMessage(err)`.

#### Card "Anonimizar titular"

```
bg-red-50 dark:bg-red-950/20
border border-red-200 dark:border-red-900/40
rounded-lg p-4
```

Único card com fundo de alerta (vermelho claro/escuro) em toda a ficha do
cliente — destaque deliberado por ser a única ação irreversível da tela.
O restante da ficha usa superfícies neutras (`navy-900`/`gray-50`); este
card precisa "gritar" mais que os outros.

- Cabeçalho: `flex items-center justify-between`
  - Esquerda: `<UserX size={16} className="text-red-600 dark:text-red-400" />`
    + título `text-sm font-semibold text-red-700 dark:text-red-300` —
    "Anonimizar titular"
  - Direita (somente quando `cliente.anonimizado === true`): badge
    `bg-gray-100 text-gray-500 dark:bg-navy-700 dark:text-slate-400
    rounded-full px-2 py-0.5 text-xs font-medium flex items-center gap-1`
    — `<ShieldCheck size={12}/> Já anonimizado`
- Descrição: `text-xs text-red-600/80 dark:text-red-400/80 mt-1 mb-3` —
  "Remove nome, documento, contato e observações do titular de forma
  permanente. Requer uma exportação prévia (é o backup exigido antes da
  eliminação). Registros financeiros e fiscais são mantidos por
  obrigação legal."
- Botão: `<Button variant="danger" size="sm" disabled={cliente.anonimizado}>
  <UserX size={14}/> Anonimizar titular</Button>` — abre o Modal de
  confirmação (Tela 2). Quando `cliente.anonimizado` já é `true`, o botão
  fica **desabilitado**, não escondido — o usuário precisa entender que a
  ação já foi feita, não que ela desapareceu da tela.

#### Histórico de exportações

Lista simples, sem paginação (poucos registros por cliente na prática).
Fonte de dados: endpoint/campo que o Forge decidir expor para leitura das
`ExportacaoTitular` do cliente (ex.: incluso no detalhe do `Cliente` ou
endpoint próprio) — a UI só precisa de uma lista
`[{formato, created_at, created_by_nome}]`.

- Título: `text-xs font-semibold text-gray-500 dark:text-slate-400
  uppercase tracking-wide mt-2` — "Histórico de exportações"
- Item: `flex items-center gap-2 text-xs text-slate-400 py-1` —
  `<History size={12}/>` + `{data formatada} — {formato} — por
  {created_by_nome}`
- Estado vazio: `text-xs text-gray-400 dark:text-slate-500 text-center
  py-3` — "Nenhuma exportação registrada ainda."
- Ordenação: mais recente primeiro.

---

## Tela 2 — Modal de confirmação de anonimização

Reutiliza o componente `Modal` existente (`components/ui/Modal.jsx`),
**não criar modal novo do zero**.

```jsx
<Modal title="Anonimizar titular" onClose={fecharModalAnonimizar} maxW="max-w-md">
  ...
</Modal>
```

### Layout interno do modal

```
┌─────────────────────────────────────────────────┐
│ Anonimizar titular                           [×] │  ← título do Modal (já existe)
│                                                    │
│ ┌────────────────────────────────────────────┐  │
│ │ [AlertTriangle] Esta ação é irreversível.     │  │  ← bloco de aviso
│ │ Nome, documento, telefone, e-mail e           │  │
│ │ observações de "{nome atual}" serão            │  │
│ │ removidos permanentemente. Registros          │  │
│ │ financeiros e fiscais continuam vinculados    │  │
│ │ ao cliente, por obrigação legal (LGPD          │  │
│ │ art. 16, I).                                   │  │
│ └────────────────────────────────────────────┘  │
│                                                    │
│ Para confirmar, digite o nome completo do          │
│ titular:                                           │
│ "{nome_razao_social atual}"                        │
│                                                    │
│ [Input: __________________________]               │
│                                                    │
│ [Button secondary: Cancelar]  [Button danger:      │
│                                 Confirmar            │
│                                 anonimização]        │
└─────────────────────────────────────────────────┘
```

**Bloco de aviso (topo do modal, antes de qualquer input):**
```
bg-red-50 dark:bg-red-950/30
border border-red-200 dark:border-red-900/50
rounded-lg p-3
flex gap-2 items-start
```
- Ícone: `<AlertTriangle size={20} className="text-red-600 dark:text-red-400 shrink-0 mt-0.5" />`
- Texto: `text-sm text-red-700 dark:text-red-300` — negrito só na primeira
  frase (`<strong>Esta ação é irreversível.</strong>`), resto peso normal.
  Interpolar o nome atual do cliente dentro do texto (entre aspas, igual
  ao wireframe) para reforçar qual registro será afetado.

**Campo de confirmação por digitação:**
- Label: `text-sm text-gray-700 dark:text-slate-300 mb-1` — "Para
  confirmar, digite o nome completo do titular:"
- Abaixo do label, o nome atual em destaque:
  `text-sm font-semibold text-gray-900 dark:text-slate-100 mb-2` —
  `"{cliente.nome_razao_social}"` (entre aspas, cor neutra — não é erro,
  é referência)
- `<Input placeholder="Digite o nome exatamente como mostrado acima" />`
  — comparação **estritamente local** (`valorDigitado === nomeAtual`,
  sem `trim()` nem case-insensitive — fricção deliberada, conforme RF-08:
  comparar string local, sem chamar a API a cada tecla)
- Enquanto o valor não bate, **não** usar a prop `error` do `Input` (não é
  erro de validação de campo, é estado incompleto da confirmação) — em
  vez disso, o botão de confirmar simplesmente permanece `disabled`. Não
  exibir mensagem de erro embaixo do campo enquanto o usuário ainda está
  digitando.

**Botões (footer do modal):**
`flex justify-end gap-2 mt-5 flex-wrap`
- `<Button variant="secondary" onClick={fechar}>Cancelar</Button>`
- `<Button variant="danger" disabled={valorDigitado !== nomeAtual} loading={enviando}>
  Confirmar anonimização</Button>`
  — ao clicar, `POST /api/v1/clientes/{id}/anonimizar/` com
  `{ confirmo: true }`. Erro (400 sem exportação prévia, 400 já
  anonimizado) exibido como banner de erro **dentro do próprio modal**
  (acima dos botões, mesmo padrão `bg-red-50`/`text-red-700` já usado em
  outros formulários do projeto), usando `extractErrorMessage(err)` — o
  modal **não fecha** em caso de erro, para o usuário poder ler a
  orientação (ex.: "exporte os dados antes de anonimizar") e agir (trocar
  para a aba/card "Exportar", sem perder o contexto do que estava fazendo).
- Sucesso: fecha o modal, atualiza o `cliente` em memória na ficha
  (`anonimizado: true`, `nome_razao_social` com o novo valor retornado
  pela API), dispara o toast de sucesso padrão do projeto
  (`bg-accent-600 dark:bg-violet-600`) com a mensagem "Titular anonimizado
  com sucesso." Ao reabrir a ficha/voltar para a aba "Dados", o nome já
  aparece atualizado, sem precisar recarregar a listagem inteira.

### Mobile (375px)

- `Modal` já é responsivo (`w-full` com `px-4` no overlay) — nada
  específico a ajustar na estrutura do componente em si.
- Botões do footer: `flex-wrap` evita que "Cancelar" e "Confirmar
  anonimização" espremam o texto em telas muito estreitas — testar em
  375px; se o texto do botão `danger` cortar, aplicar `flex-col` abaixo
  de `sm:` apenas nesse footer (decisão de implementação do Loom).
- Cards da aba "LGPD" (Tela 1): botões PDF/JSON com `flex-wrap` já
  cobrem o caso mobile sem precisar de `flex-col` forçado.

---

## Resumo de ícones novos usados nesta manutenção (import único em `Clientes.jsx`)

```js
import { Shield, Download, FileText, FileJson, UserX, AlertTriangle, History, ShieldCheck } from 'lucide-react'
```

Nenhum ícone fora do catálogo Lucide já em uso no projeto — consistente
com a regra de ícones Lucide em todo o sistema (nunca emoji, exceto a
exceção já documentada da Sidebar, que não se aplica aqui).

---

## O que NÃO fazer (armadilhas desta tela)

```
❌ NÃO renderizar o conteúdo exportado na tela — exportar é download
   direto (blob + <a download>), nunca abrir o PDF/JSON embutido na página
❌ NÃO comparar o campo de confirmação com debounce/chamada à API —
   é comparação de string 100% local, sem round-trip de rede
❌ NÃO usar trim()/lowercase na comparação do nome digitado — fricção
   deliberada, igual aos demais padrões de confirmação crítica do projeto
❌ NÃO esconder o botão "Anonimizar titular" quando já anonimizado —
   desabilitar e mostrar o badge "Já anonimizado", nunca remover da tela
❌ NÃO fechar o modal de anonimização em caso de erro da API — usuário
   precisa ler a mensagem (ex: "exporte antes") sem perder o contexto
❌ NÃO criar um componente de modal novo — reutilizar Modal/Button/Input
   já existentes, mesmo padrão usado em Assinaturas/Agendamento
❌ NÃO introduzir lib de toast nova — usar o banner local já padronizado
❌ NÃO mostrar a aba "LGPD" para usuário sem tem_acesso_total — ela some
   da UI da mesma forma que outras áreas sensíveis desde a Manutenção #60
```

---

## Componentes existentes a reutilizar (mapa explícito)

| Componente | Onde reutilizar |
|---|---|
| `Modal` | Modal de confirmação de anonimização (`maxW="max-w-md"`) |
| `Input` | Campo de confirmação por digitação do nome |
| `Button` | Botões PDF/JSON, Anonimizar titular, Cancelar/Confirmar |
| Banner de toast local | Sucesso/erro de exportar e anonimizar |
| `extractErrorMessage` | Toda mensagem de erro da API nesta feature |

Nenhum componente de base foi alterado — apenas consumido como já existe.
A aba "Dados" e a aba "Assinaturas" do mesmo modal permanecem com zero
alteração visual. A tela de listagem de Clientes (tabela, filtros,
paginação) também é inalterada — a aba LGPD vive inteiramente dentro do
modal de edição já existente.

---

## Passagem de bastão

```
Especificacao UI concluida — UidCore [NUCLEO 5/5]
Telas especificadas: 2
  1. Aba "LGPD" na ficha do Cliente (Clientes.jsx) — exportar PDF/JSON +
     card de anonimização + histórico de exportações
  2. Modal de confirmação forte de anonimização (digitar nome atual)

Componentes reutilizados: Modal, Input, Button, banner de toast local,
                          extractErrorMessage
Novos componentes:        AbaLgpdCliente (função isolada, mesmo padrão de
                          AbaAssinaturasCliente)
Modo: Padrão Uid (dark mode navy/violet já estabelecido, Manutenção #31)

Arquivo: /var/www/uidcore/Especificacao_UI_Hotfix.md

-> Loom le Especificacao_Hotfix.md + Especificacao_UI_Hotfix.md
   antes de implementar a aba LGPD e o modal de anonimizacao em
   Clientes.jsx.
```
