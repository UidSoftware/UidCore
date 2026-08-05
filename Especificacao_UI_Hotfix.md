# Especificação UI Hotfix — UidCore — Manutenção #21 (Ajustes pós-lançamento PDV)

**Base:** Especificacao_Hotfix.md (Analista, Manutenção #21, RF-17 a RF-23) + design_system.md (Brush, Manutenção #8, ainda válido — nenhuma decisão de paleta/tipografia/model é tomada aqui).

**Modo:** MODO HOTFIX — camada visual sobre spec já aprovada pelo Analista. Nenhum
model, endpoint ou contrato de API é definido aqui (nenhum é necessário — Seção 8
da Especificacao_Hotfix.md confirma 0 alterações de backend). Este documento só
diz **onde** e **como** cada RF aparece na tela, reutilizando ao máximo os
componentes e padrões já existentes no módulo PDV.

> Nota: este arquivo é regravado a cada manutenção — o conteúdo anterior
> (Manutenção #15, especificação completa das 6 telas do módulo PDV, já
> concluída e em produção) está preservado no histórico do `CLAUDE.md` do
> projeto e no git history. Este documento passa a refletir apenas os ajustes
> da Manutenção #21.

---

## Design System do Projeto (referência — não redefinido aqui)

- **Tema:** claro (light mode), `bg-gray-50` app.
- **Cor primária:** `primary-600` (#2563eb) / hover `primary-700`.
- **Sucesso:** `accent-600` (#059669). **Erro:** `red-600` (#dc2626). **Atenção:** `yellow-700`/`bg-yellow-50`. **Info:** `blue-600`/`bg-blue-50`.
- **BorderRadius:** `rounded-lg` (8px) inputs/botões, `rounded-xl`/`rounded-2xl` cards e modais.
- **Toast:** `fixed top-4 right-4 z-50 px-4 py-3 rounded-lg shadow-lg text-sm font-medium text-white` — `bg-accent-600` sucesso / `bg-red-600` erro. Já implementado em `FrenteDeCaixa.jsx` e `AberturaCaixa.jsx` via `mostrarToast(msg, tipo)` — **reutilizar exatamente o que já existe em cada arquivo, não criar padrão novo.**
- **Modal:** `Modal.jsx` já existente — overlay `fixed inset-0 z-50 bg-black/50`, container `bg-white rounded-2xl shadow-xl p-6 max-h-[90vh] overflow-y-auto`, `maxW` configurável (`max-w-md` para forms rápidos).
- ⚠️ **NUNCA** `overflow-hidden` em elemento raiz de tela — não se aplica a nenhuma mudança desta manutenção (nenhuma tela nova é criada), mas vale reforçar ao mexer no Modal de câmera: usar `overflow-hidden` **só** no wrapper do preview de vídeo (elemento local, não a tela), nunca no container do Modal.

---

## Componentes existentes a reutilizar (nenhum componente novo em `components/ui/`)

| Componente | Uso nesta manutenção |
|---|---|
| `Modal.jsx` | Overlay de "Escanear com câmera" (RF-18/19/20) |
| `Button.jsx` | Nenhum botão novo de `variant` — os botões novos (câmera) seguem o padrão de botão-ícone já usado pelo `ScanLine` em `FrenteDeCaixa.jsx:331-338` (`<button>` HTML direto com classes Tailwind, não o componente `Button.jsx` — mesmo padrão do botão de foco já existente) |
| Toast pattern (já implementado em `FrenteDeCaixa.jsx:270-276` e `AberturaCaixa.jsx:87-93`) | Erro de permissão de câmera (RF-20), erro de sessão encerrada (RF-23) |
| `useAuthStore` (`AberturaCaixa.jsx:7,15`) | Já importa `user` — hoje não é renderizado em lugar nenhum; RF-21 passa a usá-lo |
| `extractErrorMessage` (`utils/errors.js`) | Mensagem amigável no toast de erro de sessão (RF-23) |

**Nenhum componente novo em `components/ui/` é necessário.** O overlay de câmera é local a `FrenteDeCaixa.jsx` (ou um sub-componente em `pdv/components/`, ex. `ModalScannerCamera.jsx`, seguindo o mesmo padrão de `ModalSangriaSuprimento.jsx` já existente na mesma pasta — decisão de organização de arquivo é do Loom, mas **deve** ficar em `pdv/components/`, não em `components/ui/`, pois é específico do PDV).

---

## Ícones (Lucide React) — novos desta manutenção

| Ação/Contexto | Ícone | Tamanho | Cor |
|---|---|---|---|
| Escanear com câmera (botão trigger) | `Camera` | 16px | `text-gray-500` (mesmo estilo do botão `ScanLine` já existente) |
| Câmera inicializando / decodificando | `Loader2` | 16px | `text-gray-500`, classe `animate-spin` |
| Câmera não suportada pelo navegador (estado inline, não toast) | `AlertCircle` | 20px | `text-red-600` |
| Guia de mira dentro do preview de vídeo | linha `div` com `bg-primary-500/80`, não é ícone Lucide | — | `bg-primary-500/80` |
| Operador logado (Abertura de Caixa) | `User` | 12px | `text-gray-500` |
| Data/hora atual (Abertura de Caixa) | `Clock` | 12px | `text-gray-500` |

Ícones já existentes reutilizados sem alteração: `Search`, `ScanLine`, `Unlock`, `PackageSearch`.

---

## RF-17 — Enter no campo de busca aciona match exato (Frente de Caixa)

**Arquivo:** `frontend/src/pages/pdv/FrenteDeCaixa.jsx`

Nenhuma mudança visual — é comportamento sobre o campo já existente
(`buscaRef`, linhas 321-329, dentro do `Card` de busca em 316-375). Não
adicionar ícone, badge ou feedback visual novo para o Enter em si; o próprio
item já sendo adicionado ao carrinho (re-render do `Card` "Carrinho") já é o
feedback. Se quiser reforço visual opcional (não obrigatório pela spec):
piscar brevemente a borda do input em `border-primary-500` por ~200ms ao
adicionar via Enter — **não implementar isso se adicionar complexidade**,
RF-17 não pede feedback visual dedicado.

`onKeyDown` no `<input>` da linha 321-329: ao `Enter`, se
`resultadosBusca.filter(p => p.codigo_barras === busca.trim())` tiver
exatamente 1 item, chamar `adicionarProduto()` com esse item — mesma função
já usada pelo clique do dropdown (linha 351), sem duplicar lógica.

---

## RF-18/19/20 — Escanear com câmera (Frente de Caixa)

**Arquivo:** `frontend/src/pages/pdv/FrenteDeCaixa.jsx`, componente de câmera novo em `frontend/src/pages/pdv/components/`

### Botão trigger — ao lado do botão `ScanLine` existente

Layout atual do bloco de busca (linhas 317-339):
```
[ Search icon | input busca ..................... ] [ ScanLine ]
```
Layout novo — adicionar um terceiro botão-ícone à direita do `ScanLine`,
mesmo estilo (`p-2 rounded-lg border border-gray-300 text-gray-500
hover:bg-gray-50 transition-colors`), `gap-2` entre os três elementos
(mesma classe `flex items-center gap-2` do wrapper em 318):
```
[ Search icon | input busca ..................... ] [ ScanLine ] [ Camera ]
```
- `title="Focar para leitura de código de barras"` no `ScanLine` (já existe) — manter.
- `title="Escanear com câmera"` no novo botão `Camera`.
- Em 375px (mobile): os dois botões-ícone (36px cada + gap-2) cabem ao lado do input sem quebrar linha — o input já é `flex-1`, ele encolhe para dar espaço. **Testar em 375px antes de considerar pronto** (regra padrão do Brush).
- Ao clicar: abre o `Modal` de câmera (novo componente, ex. `ModalScannerCamera.jsx`).

### Modal de câmera — estados

Usar `Modal.jsx` com `title="Escanear código de barras"` e `maxW="max-w-md"`.

**Estado 1 — inicializando (enquanto `getUserMedia` não resolve):**
```
┌─────────────────────────────────────┐
│  Escanear código de barras      [×] │
│                                       │
│  ┌─────────────────────────────────┐ │
│  │                                   │ │  ← wrapper preview: aspect-video,
│  │        (preto, sem preview)      │ │     bg-black, rounded-lg,
│  │                                   │ │     overflow-hidden (local, não
│  └─────────────────────────────────┘ │     no root da tela)
│                                       │
│     ⟳ Iniciando câmera...           │  ← Loader2 16px animate-spin +
│                                       │     texto text-sm text-gray-500,
│                                       │     flex items-center justify-
│                                       │     center gap-2 py-4
└─────────────────────────────────────┘
```

**Estado 2 — câmera ativa (permissão concedida, decodificando):**
```
┌─────────────────────────────────────┐
│  Escanear código de barras      [×] │
│                                       │
│  ┌─────────────────────────────────┐ │
│  │ ▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂ │ │  ← <video> object-cover, w-full h-full
│  │ ────────────────────────────── │ │  ← linha-guia horizontal, absolute,
│  │ ▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂ │ │     inset-x-8 top-1/2 -translate-y-1/2
│  └─────────────────────────────────┘ │     h-0.5 bg-primary-500/80
│                                       │
│  Aponte a câmera para o código de   │  ← text-xs text-gray-500 text-center
│  barras do produto                   │     mt-3
└─────────────────────────────────────┘
```
- Wrapper do preview: `relative rounded-lg overflow-hidden bg-black aspect-video`.
- `<video>`: `w-full h-full object-cover`, `autoPlay`, `playsInline`, `muted` (obrigatório em iOS Safari para autoplay funcionar).
- Linha-guia é puramente decorativa (reforça "aponte aqui"), não precisa ter posição funcional real ligada à lib de decodificação escolhida pelo Loom.
- Ao decodificar com sucesso: fechar o Modal automaticamente, chamar `setBusca(codigoLido)` e disparar o mesmo fluxo de match exato do RF-17 (idealmente buscando direto pelo código exato via API em vez de esperar o debounce de 300ms do `useEffect` de busca em 106-124, para resposta instantânea — decisão de implementação do Loom, não afeta o layout aqui descrito).

**Estado 3 — permissão negada (RF-20):**
- **Não** manter um 4º estado visual persistente dentro do Modal — fechar o Modal imediatamente e mostrar o toast de erro já existente: `mostrarToast('Permissão de câmera negada. Você pode continuar digitando ou usando o leitor físico.', 'error')`. Consistente com "sem travar a tela do PDV" (RF-20) — o operador volta pro fluxo normal de busca sem nenhuma tela bloqueada.

**Estado 4 — câmera não suportada pelo navegador** (`navigator.mediaDevices` ausente — cenário diferente de permissão negada, é incapacidade do browser/dispositivo):
- Este caso **fica dentro do Modal** (não fecha sozinho, pois não é um erro transitório de permissão — o operador precisa entender que a opção não está disponível *neste* dispositivo/navegador antes de fechar):
```
┌─────────────────────────────────────┐
│  Escanear código de barras      [×] │
│                                       │
│      ⚠ Câmera não suportada         │  ← AlertCircle 20px text-red-600
│      neste navegador.                │     + texto text-sm text-gray-600,
│      Use o leitor físico ou digite   │     text-center, py-8
│      o código manualmente.           │
│                                       │
│              [ Fechar ]              │  ← Button variant="secondary" size="sm"
└─────────────────────────────────────┘
```

---

## RF-21/RF-22 — Abertura de Caixa: operador + data/hora + "Fundo de Troco"

**Arquivo:** `frontend/src/pages/pdv/AberturaCaixa.jsx`

### RF-21 — exibir operador logado + data/hora atual

Local: dentro do card branco (linhas 115-175), logo abaixo do bloco de
cabeçalho existente (`text-center mb-6`, linhas 116-122: ícone `Unlock` +
título + subtítulo), **antes** do `<form>` (linha 124).

```
┌─────────────────────────────────┐
│         🔓 Abrir Caixa           │  ← já existe, sem alteração
│  Selecione a conta e informe o   │  ← já existe, sem alteração
│  valor de abertura               │
│                                   │
│   👤 João Silva    🕐 05/08 14:32 │  ← NOVO — linha de info
│  ─────────────────────────────   │  ← NOVO — separador sutil
│                                   │
│  Conta (Select)                  │  ← já existe
│  ...                              │
```

- Novo bloco: `<div className="flex items-center justify-center gap-4 text-xs text-gray-500 pb-4 mb-4 border-b border-gray-100">`.
- Operador: `<span className="flex items-center gap-1"><User size={12} /> {user?.nome || user?.email || 'Operador'}</span>` — usar o campo que `useAuthStore` já expõe (linha 15, `user`), sem chamada de API nova.
- Data/hora: `<span className="flex items-center gap-1"><Clock size={12} /> {dataHoraFormatada}</span>`, formatada em pt-BR com data curta + hora: `new Date().toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })` — mesmo padrão de formatação já usado em `formatarHora()` de `FrenteDeCaixa.jsx:18-21`, só que incluindo a data. Atualizar 1x no mount é suficiente (não precisa de relógio ao vivo — a tela é um gate rápido, não um dashboard).
- Mobile (375px): o `flex` com `gap-4` e textos `text-xs` cabe numa linha só mesmo em telas pequenas; se o nome do operador for muito longo, aplicar `truncate max-w-[140px]` no `<span>` do nome para não quebrar o layout.

### RF-22 — reforçar "Fundo de Troco" no campo de valor

Local: label do campo na linha 147-149.

- Trocar o texto do `<label>` de `"Valor de abertura"` para
  `"Valor de Abertura (Fundo de Troco)"` — mesma classe
  (`block text-sm font-medium text-gray-700 mb-1`), sem alterar o `<input>`
  em si (linhas 150-160) nem o `placeholder="0,00"`. Mudança mínima e sem
  risco de quebrar layout (`text-sm` já acomoda o texto mais longo em
  `max-w-md`; testado visualmente em 375px o texto quebra em até 2 linhas
  no pior caso, o que é aceitável para um label).

---

## RF-23 — Redirecionar ao abrir caixa quando sessão foi encerrada

**Arquivos:** `frontend/src/pages/pdv/FrenteDeCaixa.jsx` (lógica) + `frontend/src/pages/pdv/AberturaCaixa.jsx` (exibição da mensagem no destino)

Sem elemento visual novo em `FrenteDeCaixa.jsx` — o padrão de UX é: erro em
`criarVenda()` (linhas 88-97, especificamente o `catch` em 94-96) deixa de
mostrar o texto cru do backend e navega para `/pdv/abertura`, no mesmo
padrão já usado pelo `useEffect` de carregamento de sessão (linhas 65-74,
que já faz `navigate('/pdv/abertura')` sem toast quando `GET
/pdv/sessoes/atual/` falha).

**Problema de UX a resolver na navegação:** um `mostrarToast()` chamado
imediatamente antes de `navigate()` some da tela porque o componente
`FrenteDeCaixa` desmonta. Padrão recomendado (reaproveita a already-existing
prop `state` do React Router, sem criar mecanismo novo):

```
navigate('/pdv/abertura', {
  state: { mensagem: 'Sua sessão de caixa foi encerrada. Abra o caixa novamente.' }
})
```

Em `AberturaCaixa.jsx`: ler `useLocation().state?.mensagem` no mount (`useEffect`
com array de deps vazio, junto do `useEffect` já existente em 31-44) e, se
presente, chamar o `mostrarToast(msg, 'error')` **já existente nesse arquivo**
(linhas 26-29) — reaproveita o mesmo componente de toast já renderizado em
87-93, nenhum elemento visual novo. Sem necessidade de limpar o `state` do
histórico manualmente (comportamento padrão do React Router já evita
reexibição em refresh simples da página).

Visualmente, o toast de erro em `AberturaCaixa.jsx` já segue o padrão
`bg-red-600` — nenhuma alteração de estilo necessária, só popular o
conteúdo.

---

## Grupo 5 — Card do Carrinho e SplitPagamento

### Card "Carrinho" (`FrenteDeCaixa.jsx:378-397`)

- Estado vazio (linha 379-383): reduzir `py-12` → `py-6` no `<div
  className="text-center py-12">` (linha 380). Mantém `PackageSearch` 32px +
  texto, só reduz o respiro vertical, já que o `Card` (componente genérico,
  `components/ui/Card.jsx:9`) já soma `px-6 py-4` de padding no body por
  fora — não alterar `Card.jsx` (é componente compartilhado por todo o
  sistema), só o conteúdo interno específico do carrinho.
- Lista de itens (linha 385-395, `<div>` que envolve o `.map`): adicionar
  `max-h-[420px] overflow-y-auto` para conter o crescimento vertical do
  Card quando o carrinho tiver muitos itens — sem isso, um carrinho com 15+
  itens empurra o botão "Finalizar Venda" (coluna direita, sticky) para
  fora da viewport em telas menores. `420px` é uma estimativa segura (cabe
  ~6-7 linhas de `CarrinhoItem` antes de rolar) — Loom pode ajustar o valor
  exato após ver o `CarrinhoItem.jsx` renderizado, o importante é que exista
  um teto com scroll interno, não altura livre.

### SplitPagamento (`components/SplitPagamento.jsx`)

Ajustes pontuais de espaçamento, mantendo o grid 2 colunas e sem alterar
lógica:

| Linha atual | De | Para |
|---|---|---|
| 81 (`<div key={linha._key} className="rounded-lg border ...">`) | `p-3 space-y-2` | `p-4 space-y-3` |
| 94 (`<div className="grid grid-cols-2 ...">` Valor/Conta) | `grid-cols-2 gap-2` | `grid-cols-2 gap-3` |
| 97 (label "Valor (R$)") | `text-xs` | `text-sm` |
| 111 (label "Conta de destino") | `text-xs` | `text-sm` |
| 127 (`<div className="grid grid-cols-2 gap-2 pt-1 ...">` Taxa/Prazo) | `gap-2 pt-1` | `gap-3 pt-2` |
| 129 (label "Taxa (%)") | `text-xs` | `text-sm` |
| 142 (label "Prazo (dias)") | `text-xs` | `text-sm` |

- Inputs (linhas ~98-106, ~112-121, ~130-139, ~143-151) já estão em
  `text-sm` — **manter**, não subir pra `text-base`: em `grid-cols-2` numa
  tela de 375px cada coluna tem ~150-165px de largura útil (considerando
  `p-4` do card pai + `gap-3`), `text-base` nos inputs de valor/taxa
  arrisca *overflow* horizontal do texto digitado. `text-sm` já resolve a
  queixa de "campos apertados" descrita no pedido — o problema real
  confirmado pelo Analista era o padding (`p-3`→`p-4`, `gap-2`→`gap-3`),
  não o tamanho da fonte do input em si.
- **Não alterar** o grid de chips de método de pagamento (linha 61,
  `grid-cols-2 sm:grid-cols-3 gap-2`) — item 5 do pedido é especificamente
  sobre as linhas de pagamento já adicionadas, não sobre os chips de
  seleção inicial.
- Testar em `<768px` (breakpoint da `BottomBar`, que é independente do
  layout interno do `SplitPagamento` — confirmado pelo Analista, RNF-08)
  antes de considerar pronto.

---

## Mobile-first — resumo transversal desta manutenção

- Breakpoint crítico: 768px (`md:`), igual ao resto do sistema — nenhuma
  mudança de breakpoint nesta manutenção.
- Testar em 375px (iPhone SE): botão `Camera` novo ao lado do `ScanLine`
  (bloco de busca), linha de info operador+data/hora na Abertura de Caixa,
  e o novo espaçamento do `SplitPagamento` — os três pontos com maior risco
  de quebra em tela pequena.
- Modal de câmera: `maxW="max-w-md"` já é mobile-safe (o `Modal.jsx` tem
  `px-4` no overlay e `w-full` no container — cabe em qualquer largura).
- Nenhuma tela nova precisa da barra fixa de total no rodapé (`fixed
  bottom-0`, `FrenteDeCaixa.jsx:522-540`) — já existe e não é afetada por
  nenhum RF desta manutenção.

---

## O que NÃO foi definido aqui (propositalmente)

- Qual lib de leitura de código de barras usar (`@zxing/library`,
  `html5-qrcode` ou `quagga2`) — decisão técnica do Loom (RNF-09 da
  Especificacao_Hotfix.md), documentada no commit. O layout do Modal
  (Estados 1-4 acima) funciona com qualquer uma das três.
  Nome/organização do arquivo do componente de câmera novo.
- Threshold exato de `max-h-[420px]` no Carrinho — estimativa, Loom ajusta
  após ver o componente `CarrinhoItem.jsx` renderizado de verdade.
- Detalhe de implementação de como a decodificação da câmera dispara o
  match exato (chamada direta à API vs. reaproveitar o `useEffect` de
  debounce) — é lógica de estado, não UI.
- Qualquer mudança em `Card.jsx`, `Modal.jsx` ou `Button.jsx` genéricos —
  nenhuma foi necessária; todos os ajustes desta manutenção ficam isolados
  nos arquivos específicos do PDV.

---

## Passagem de bastão

```
✅ Especificação UI concluída — UidCore (Manutenção #21 — ajustes PDV)
   RFs cobertos: RF-17 a RF-23 (7 requisitos, 4 grupos de ajuste)
   Telas/componentes analisados: FrenteDeCaixa.jsx, AberturaCaixa.jsx,
     SplitPagamento.jsx, Card.jsx, Modal.jsx, Button.jsx
   Componentes reutilizados: Modal.jsx, toast pattern (já existente em
     cada arquivo), useAuthStore, extractErrorMessage
   Novos padrões: Modal de câmera com 4 estados (inicializando / ativo /
     permissão negada → toast / não suportado → inline), linha de info
     operador+data/hora na Abertura de Caixa
   Nenhum componente novo em components/ui/ — tudo específico de pdv/

📁 Arquivo: Especificacao_UI_Hotfix.md (em /var/www/uidcore/)

➡️ Loom lê Especificacao_Hotfix.md + Especificacao_UI_Hotfix.md
   antes de implementar RF-17 a RF-23 no frontend do PDV
```
