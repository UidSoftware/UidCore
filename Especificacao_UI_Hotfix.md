# Especificação UI Hotfix — UidCore (Manutenção #36)
**Elaborado por:** Brush (MODO HOTFIX)
**Data:** 2026-08-17
**Base:** Especificacao_Hotfix.md (Analista, Manutenção #36)

---

## Escopo desta especificação

Manutenção majoritariamente de **backend** (validação de servidor RF-01/RF-02,
cálculo de resumo RF-03). Do lado visual há só **3 pontos reais de UI**:

1. `AberturaCaixa.jsx` — tratar a nova chave de erro `operador` (RF-02) como toast
2. `FechamentoCaixa.jsx` + `ResumoSessao.jsx` — **zero mudança de código**, só passam
   a receber dado real do backend (RF-03) — os componentes já foram desenhados
   para esse formato
3. `RelatorioSessoesCaixa.jsx` — corrigir campo (RF-04, sem impacto visual) +
   **adicionar filtro de operador** (RF-05, único elemento de UI novo desta manutenção)

Não há tela nova nem componente novo a criar. O trabalho do Brush aqui é
garantir que o único elemento novo (Select de operador) segue exatamente o
padrão visual já estabelecido no módulo PDV, e documentar os pontos de
atenção para o Loom não improvisar decisão de estilo.

---

## Design System do Projeto (referência — lido em design_system.md + código real do PDV)

- **Paleta:** navy (60%) + violet (30%) + red (10%), dark mode via classe
  `dark:` (Tailwind `darkMode: 'class'`) — confirmado em Manutenção #31
- **Fundo de página:** `bg-gray-50 dark:bg-navy-950`
- **Cards:** `bg-white rounded-xl border border-gray-200 shadow-sm dark:bg-navy-800
  dark:border-navy-600 dark:shadow-none` (componente `Card.jsx`, já usado em
  todas as 4 telas do PDV — 100% reutilizável, nenhuma prop nova)
- **Fonte:** Plus Jakarta Sans (headings) + DM Sans (body/interface) — já
  configuradas no projeto, não mexer
- **BorderRadius:** `rounded-lg` (8px) em inputs/selects/botões, `rounded-xl`
  (12px) em cards e KPI tiles, `rounded-full` em badges de status
- **Cor de destaque (accent/primary):** `primary-600` / `dark:violet-500-600`
  para foco de input, ícones de header e botão primário
- **Semântica de cor já em uso no PDV** (reaproveitar sempre, nunca inventar
  nova combinação):
  - azul (`blue-50/700` · `dark:blue-950/40 dark:blue-300`) → valores neutros/informativos (Abertura)
  - verde (`green-50/700` · `dark:emerald-950/40 dark:emerald-300`) → entradas positivas (Vendas, Suprimentos, "sem diferença")
  - vermelho (`red-50/700` · `dark:red-950/40 dark:red-300`) → saídas/alertas (Sangrias, diferença de caixa)
  - amarelo/âmbar (`yellow-50/700` · `dark:amber-950/40 dark:amber-300`) → status ABERTA (badge), diferença pequena
- **Toast pattern (já usado nas 4 telas do PDV, reaproveitar tal qual):**
  `fixed top-4 right-4 z-50 max-w-sm px-4 py-3 rounded-lg shadow-lg text-sm
  font-medium text-white` — `bg-red-600` para erro, `bg-accent-600` para
  sucesso, timeout 7000ms erro / 3500-4000ms sucesso

---

## Especificação Visual por Tela

### 1. `AberturaCaixa.jsx` — erro `operador` (RF-02)

**Diagnóstico:** a tela não tem campo de formulário para "operador" (é o
usuário logado, não um input) — não há onde anexar um erro inline como já
é feito com `errors.conta`. O padrão correto é o já existente `mostrarToast`.

**Especificação:**
- Quando `err.response.data.operador` vier no catch de `handleSubmit`, chamar
  `mostrarToast(extractErrorMessage(err, 'Você já tem uma sessão de caixa aberta em outra conta.'), 'error')`
  — mesmo padrão de toast já usado para o erro genérico do `else`, **não**
  criar um novo tipo de alerta visual
- Não usar `setErrors({...})` para essa chave — reservado a campos com input
  visível (`conta`, `valorAbertura`)
- Duração do toast: 7000ms (padrão já definido em `mostrarToast` para
  `tipo === 'error'`) — mensagem é acionável ("vá lá fechar o outro caixa
  primeiro"), operador precisa de tempo de leitura maior que o de sucesso
- **Nenhuma mudança de layout, cor ou ícone** — reaproveita 100% o bloco de
  toast já renderizado no topo do componente (linhas 103-109 do arquivo atual)

### 2. Card "Você já tem uma sessão aberta" (`AberturaCaixa.jsx:112-128` e `FrenteDeCaixa.jsx:353`)

Fora do escopo de mudança desta manutenção (RF-06 é validação do Sentinel em
produção, não alteração de código) — documentando aqui só para confirmar que
o padrão visual atual **está correto e não deve ser alterado**:

- Container: `bg-blue-50 border border-blue-200 text-blue-700 dark:bg-blue-950/40
  dark:border-blue-800 dark:text-blue-300`, `rounded-lg`, `px-4 py-3`
- Estrutura: título em negrito ("Você já tem uma sessão aberta.") + linha de
  detalhe com `Conta: {nome} · Aberta às {hora}` + link de ação
  ("Ir para o caixa aberto") em `text-primary-600 dark:text-violet-400` com
  `hover:underline`
- Fallback de nome de conta: `sessaoAtiva.conta_nome || `#${sessaoAtiva.conta}``
  — já correto, mantido
- Se o Sentinel confirmar em produção que o bug reproduz (bundle desatualizado),
  a correção é **redeploy**, não mudança visual — nada a fazer aqui

### 3. `FechamentoCaixa.jsx` + `ResumoSessao.jsx` (RF-03)

**Zero mudança de código.** Os componentes já foram implementados esperando
exatamente o formato `{ por_metodo, vendas_dinheiro, sangrias, suprimentos,
valor_calculado_dinheiro }` — só nunca receberam dado real do backend.
Confirmação visual do que já existe (para o Sentinel validar contra):

**KPI Cards (`ResumoSessao.jsx`, grid `grid-cols-2 md:grid-cols-4 gap-3`):**
| Label | Cor | Fonte do valor |
|---|---|---|
| Abertura | azul | `sessao.valor_abertura` |
| Total Vendas | verde | soma de `resumo.por_metodo[].total` |
| Sangrias | vermelho, prefixo `- ` | `resumo.sangrias` |
| Suprimentos | verde, prefixo `+ ` | `resumo.suprimentos` |

Cada tile: `rounded-xl p-4`, label em `text-xs font-medium opacity-70`, valor
em `text-lg font-bold mt-1 font-mono` — **já implementado, sem alteração**.

**Lista "Vendas por forma de pagamento":** só renderiza se
`resumo.por_metodo.length > 0` — card branco/navy com header
`px-4 py-3 border-b`, linhas `flex justify-between` com nome à esquerda
(`text-gray-600 dark:text-slate-400`) e valor em `font-mono font-medium` à
direita. **Já implementado, sem alteração.**

**Ponto de atenção para o Sentinel (não para o Loom):** antes desta
manutenção, `resumo.por_metodo` sempre chegava vazio → essa seção nunca
renderizava. Validar visualmente que ela aparece quando há vendas na sessão.

**Card "Valor calculado em caixa" (`FechamentoCaixa.jsx`, fora do `ResumoSessao`):**
`Card` simples com `flex justify-between`, valor grande à direita
(`text-lg font-bold font-mono`), legenda abaixo em `text-xs text-gray-400`.
Antes desta manutenção mostrava sempre o fallback `sessao?.valor_fechamento_calculado`
(null enquanto ABERTA); agora deve refletir `resumo.valor_calculado_dinheiro`
em tempo real. **Nenhuma mudança de estilo — só o dado que chega muda.**

### 4. `RelatorioSessoesCaixa.jsx` — RF-04 (rename de campo, sem UI) + RF-05 (filtro de operador, novo)

#### RF-04 — sem impacto visual
As 3 ocorrências de `sessao.valor_contagem_fisica` (linhas 151, 155 no modal
`ResumoSessaoModal`, e 453-454 na coluna "Contagem" da tabela desktop) trocam
para `sessao.valor_fechamento_informado`. **Mesma formatação BRL, mesmo
container, mesma cor** (`text-gray-900 dark:text-slate-100 font-mono
font-semibold`) — é troca de nome de propriedade, não de layout.

**Achado do Brush ao ler o componente:** o card mobile (linhas 356-401, grid
`grid-cols-2 gap-2 text-xs`) hoje **não exibe** o campo de contagem/fechamento
informado — só mostra Abertura, Fechamento, Calculado e Diferença. Isso não é
regressão desta manutenção (o campo nunca existiu no card mobile, só no modal
e na tabela desktop) e **não está no escopo de RF-04** — o Analista descreveu
3 ocorrências, mas o código real só tem 2 pontos de uso (modal + tabela
desktop; nenhuma no card mobile). Registrado para não confundir o Loom
tentando achar uma 3ª ocorrência inexistente. Se o cliente quiser paridade
(mostrar contagem física no card mobile também), é melhoria nova, fora do
escopo desta manutenção — não adicionar por conta própria.

#### RF-05 — novo Select de operador na barra de filtros

**Reutilizar exatamente o componente `Select.jsx`** já usado nos filtros de
Status e Conta na mesma barra (`Card` no topo, `flex flex-wrap gap-3 items-end`).

**Posicionamento:** logo após o Select de "Conta" (linhas 328-337 do arquivo
atual), antes do botão "Limpar filtros" — mesma ordem lógica do padrão já
usado (texto → data → enums → relacionamento → ação).

**Markup/estilo idêntico ao filtro de Conta (copiar padrão, não inventar):**
```jsx
{operadores.length > 0 && (
  <div className="w-48">
    <p className="text-xs text-gray-500 dark:text-slate-400 mb-1">Operador</p>
    <Select
      options={[{ value: '', label: 'Todos os operadores' }, ...operadores]}
      value={operadorFiltro}
      onChange={(e) => { setOperadorFiltro(e.target.value); setPage(1) }}
    />
  </div>
)}
```
- Largura: `w-48` (mesma dos outros dois Selects da barra — Status e Conta —
  para grid visual consistente)
- Label acima do input: `text-xs text-gray-500 dark:text-slate-400 mb-1`,
  **sem ícone** (o filtro de Conta também não tem ícone — só "De"/"Até" têm
  `<Calendar size={12} />`, por serem datas; manter essa distinção, não
  adicionar ícone ao Select de operador)
- Opção "Todos os operadores" como primeiro item, mesmo texto-padrão de
  "Todas as contas"/"Todos os status" já usados nos outros dois Selects
- **Condicional de render:** `operadores.length > 0`, mesmo padrão do filtro
  de Conta (`contas.length > 0`) — evita mostrar Select vazio enquanto a
  fonte de dados carrega
- Este filtro entra em `filtrosAtivos` (linha 211) e em `limparFiltros()`
  (linha 254-260), mesmo tratamento dos demais — decisão de estado, não de
  UI, mas registrado para o Loom não esquecer o botão "Limpar filtros" de
  cobrir o novo filtro também

**Rótulo de exibição do operador na option:** usar o mesmo formato já
aplicado nas colunas da própria tabela (`operador?.first_name ||
operador?.username || '—'`, linhas 374 e 436) — se a fonte de dados do
Select vier de outro formato, normalizar para esse padrão antes de montar
`options`, para o texto do filtro bater com o texto exibido nas linhas
filtradas.

**Nota técnica (decisão de dado, não de UI — fora da alçada do Brush):** o
projeto não tem hoje um endpoint dedicado de listagem de usuários/operadores
(`accounts/urls.py` só tem `register/` e `me/`). Cabe ao Loom decidir a forma
mais simples de popular esse Select sem criar endpoint novo — por exemplo,
extrair a lista de operadores distintos a partir dos dados já retornados por
`GET /pdv/sessoes/` (mesmo endpoint que a própria tela já consome), já que o
pedido do Analista foi explícito em não criar endpoint novo se já houver algo
reaproveitável. Do ponto de vista visual, o resultado final tem que ser
indistinguível do padrão dos outros dois filtros, qualquer que seja a fonte.

**Mobile:** a barra de filtros já usa `flex flex-wrap gap-3` — o novo Select
de `w-48` empilha/quebra junto com os demais automaticamente em telas
estreitas (comportamento já testado com 3 filtros de largura fixa + 2 datas +
botão; adicionar um 4º elemento de mesma largura não quebra o wrap). Testar
em 375px conforme padrão Uid — nenhum CSS adicional necessário.

---

## Ícones (Lucide React)

Nenhum ícone novo necessário nesta manutenção. Confirmação dos já usados nas
telas afetadas (não trocar nenhum):

| Tela | Ícone | Uso |
|---|---|---|
| AberturaCaixa | `Unlock` (32px header / 18px botão) | ação principal |
| AberturaCaixa | `User` (12px) | operador logado |
| AberturaCaixa | `Clock` (12px) | data/hora |
| FechamentoCaixa | `Lock` (22px header / 16px botão) | ação principal |
| FechamentoCaixa/ResumoSessao | `AlertTriangle` (14-16px) | diferença de caixa |
| FechamentoCaixa/ResumoSessao | `CheckCircle` (14-16px) | sem diferença |
| RelatorioSessoesCaixa | `ClipboardList` (24px header / 32px estado vazio) | identidade da tela |
| RelatorioSessoesCaixa | `Calendar` (12px) | filtros de data |
| RelatorioSessoesCaixa | `AlertTriangle` (14px) | célula de diferença ≠ 0 |

---

## Espaçamentos e componentes existentes a reutilizar

- `Card.jsx` — container de filtros, resumo, conferência (100% reaproveitado)
- `Select.jsx` — Status, Conta, e o novo Operador — **mesmo componente, mesma prop shape**
- `Input.jsx` — datas De/Até, contagem física, observações
- `Button.jsx` — variantes `primary`/`secondary`/`danger` já cobrem todos os
  casos desta manutenção (nenhuma variante nova)
- `Modal.jsx` — detalhe de sessão no relatório (`maxW="max-w-2xl"`) — sem alteração
- `Pagination.jsx` — sem alteração
- `ResumoSessao.jsx` (componente compartilhado FechamentoCaixa ↔ modal do
  Relatório) — **atenção:** o modal do Relatório (`ResumoSessaoModal`, dentro
  do próprio `RelatorioSessoesCaixa.jsx`) é um componente **local diferente**
  de `ResumoSessao.jsx` (o componente compartilhado usado em
  `FechamentoCaixa.jsx`) — mesma finalidade visual, implementações duplicadas
  já existentes. Não é bug desta manutenção e não deve ser unificado agora
  (fora do escopo do pedido) — só registrando para o Loom não confundir os
  dois ao aplicar RF-04.

---

## Padrões mobile-first do UidCore (dark mode navy/violet)

- Breakpoint de referência: 375px (iPhone SE)
- `RelatorioSessoesCaixa.jsx` já resolve mobile via card empilhado
  (`md:hidden`) vs tabela desktop (`hidden md:block`) — padrão mantido,
  nenhuma mudança estrutural
- Barra de filtros com `flex flex-wrap gap-3 items-end` — o novo Select de
  operador entra no fluxo do wrap sem CSS adicional
- Toast fixo `top-4 right-4` — mesmo em mobile, `max-w-sm` evita overflow
  horizontal
- Contraste: todas as combinações de cor usadas (azul/verde/vermelho/âmbar
  sobre fundo claro e fundo navy) já são as mesmas testadas na Manutenção #31
  — nenhum novo par de cor introduzido nesta manutenção, logo nenhum novo
  risco de contraste

---

## O que NÃO fazer (reforço)

```
❌ NÃO criar novo componente visual — Select de operador reaproveita Select.jsx tal qual
❌ NÃO adicionar ícone ao novo filtro de operador (inconsistente com o filtro de Conta, que também não tem)
❌ NÃO unificar ResumoSessao.jsx com ResumoSessaoModal (duplicação pré-existente, fora de escopo)
❌ NÃO tentar achar uma "3ª ocorrência" de valor_contagem_fisica no card mobile — ela não existe no código atual
❌ NÃO mudar o padrão de toast (cor, posição, duração) para o novo erro `operador` — reaproveitar tal qual
❌ NÃO alterar o card "sessão já aberta" (AberturaCaixa/FrenteDeCaixa) — está correto, RF-06 é validação em produção, não redesign
❌ NÃO criar endpoint novo de operadores se já for possível derivar a lista do próprio GET /pdv/sessoes/
```

---

## Passagem de bastão

```
✅ Especificação UI concluída — UidCore (Manutenção #36)
   Telas analisadas: 4 (AberturaCaixa, FechamentoCaixa + ResumoSessao,
   RelatorioSessoesCaixa) + 1 componente de card (sessão já aberta,
   confirmado sem alteração)
   Componentes reutilizados: Card, Select, Input, Button, Modal, Pagination
   (100% reaproveitados, 0 mudança de props/estilo)
   Novos padrões: 1 — Select de operador em RelatorioSessoesCaixa.jsx,
   clone visual exato do Select de Conta já existente

📁 Arquivo: Especificacao_UI_Hotfix.md (em /var/www/uidcore/)

➡️ Loom lê Especificacao_Hotfix.md + Especificacao_UI_Hotfix.md antes de
   implementar RF-04/RF-05 em RelatorioSessoesCaixa.jsx e o tratamento de
   erro `operador` em AberturaCaixa.jsx (RF-02). FechamentoCaixa.jsx e
   ResumoSessao.jsx não precisam de nenhuma edição de código.
```
