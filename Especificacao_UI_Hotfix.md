# Especificação UI Hotfix — UidCore (Manutenção #72)

**Tarefa:** Foto de perfil do usuário (Avatar.jsx + modal "Alterar foto" no Header + coluna avatar em Usuários)
**Brush — MODO HOTFIX.** Esta especificação NÃO cria design system novo — reaproveita os tokens já documentados em `design_system.md` e os já em uso em `Header.jsx`/`Usuarios.jsx`. O `Especificacao_Hotfix.md` do Analista já incluiu bastante detalhe de implementação (inclusive trechos de JSX) — esta spec complementa com a camada visual: estados, espaçamentos, responsividade e critério de escolha de ícone, sem duplicar os RFs/RNs já escritos lá.

---

## 0. Design System do Projeto (referência, não redefinição)

⚠️ **Divergência arquitetural já documentada** (`design_system.md`): o UidCore roda em **light mode como padrão** (`bg-gray-50`), com dark mode via classe `.dark` (`darkMode: 'class'` no Tailwind) — diferente do padrão Uid (escuro por padrão). Esta spec segue o par light/dark já implementado nas Manutenções #9 e #31, não o padrão Uid genérico do CLAUDE.md global.

| Token | Light | Dark | Uso nesta tarefa |
|---|---|---|---|
| Fundo do avatar (sem foto) | `bg-primary-100` (#dbeafe) | `bg-violet-900/40` | Círculo de iniciais — já em uso no Header atual, apenas migra para o componente `Avatar` |
| Texto da inicial | `text-primary-700` (#1d4ed8) | `text-violet-300` | Idem |
| Botão de ação secundária no Header ("Senha", "Sair") | `text-gray-500 hover:bg-gray-100 hover:text-gray-700` | `text-slate-400 hover:bg-navy-700 hover:text-slate-200` | Botão "Alterar foto" **herda exatamente esta classe** — zero cor nova |
| Erro em modal | `bg-red-50 border-red-200 text-red-700` | `bg-red-950/40 border-red-800 text-red-300` | Bloco de erro do modal de foto — mesmo padrão do modal de senha, reaproveitado 1:1 |
| Ação destrutiva ("Remover foto") | `text-red-600` | `text-red-400` | Ver nota 2.2/2.4 — link textual, não botão sólido |
| Fonte | Plus Jakarta Sans (display) / DM Sans (body) | idem | Já carregada globalmente — nenhuma ação |
| Border-radius | `rounded-full` (avatar), `rounded-lg` (modal/inputs/botões) | idem | Padrão já em uso em `Modal.jsx`/`Button.jsx`/`Input.jsx` |
| Ícones | **lucide-react** (já é dependência do projeto — `Mail` em `Usuarios.jsx`, `ModalScannerCamera.jsx` no PDV) | — | Usar `Camera` (lucide) no botão "Alterar foto" — ver nota 1.3 |

**Componentes existentes a reutilizar (não recriar):** `Modal.jsx`, `Button.jsx` (variants `primary`/`secondary`, prop `loading`), bloco de erro do modal de senha (classe pronta, só copiar), `ResourceCrud.jsx` (extensão, não substituição).

---

## 1. `Avatar.jsx` — componente novo (`frontend/src/components/ui/Avatar.jsx`)

### 1.1 Tamanhos

| Size | Classe | Diâmetro | Fonte da inicial | Onde usa |
|---|---|---|---|---|
| `sm` | `w-8 h-8 text-xs` | 32px | `font-semibold text-xs` | Header (substitui o círculo atual `w-8 h-8`) e coluna "Foto" do `ResourceCrud` (linha de tabela) |
| `md` | `w-10 h-10 text-sm` | 40px | `font-semibold text-sm` | Reserva para uso futuro (ex.: card de perfil, listagem mais espaçosa) — não usado nesta manutenção, mas o componente já nasce com a variante pronta |
| `lg` | `w-24 h-24 text-2xl` | 96px | `font-semibold text-2xl` | Preview grande dentro do modal "Alterar foto" (seção 2.2) |

Regra de implementação: tamanhos ficam num dict interno do componente (`{ sm: '...', md: '...', lg: '...' }`), nunca via prop `className` de fora sobrescrevendo dimensão — evita avatar com proporção quebrada (retangular) em algum ponto de uso futuro.

### 1.2 Cor por inicial

**Decisão de Brush:** manter **uma única cor fixa** (`bg-primary-100`/`text-primary-700` claro, `bg-violet-900/40`/`text-violet-300` escuro) para todos os usuários sem foto — **não** gerar cor variável por hash do nome/e-mail nesta manutenção.

Motivo: o pedido original ("cores por inicial") sugere paleta rotativa (estilo Gmail/Slack, uma cor por pessoa), mas isso não está no `Especificacao_Hotfix.md` do Analista — o RF-08 especifica exatamente `bg-primary-100/dark:bg-violet-900/40` fixo, "mesmo padrão de cor hoje hardcoded no Header". São os RFs que governam o escopo do Forge/Loom; introduzir paleta rotativa aqui seria o Brush discordando do RF sem ADR. Fica **registrado como sugestão de UX para ciclo futuro** (seção 5), não implementado agora.

### 1.3 Ícone do botão "Alterar foto"

Duas opções válidas; Brush recomenda a opção A por consistência local:

- **Opção A (recomendada):** ícone de câmera via **lucide-react** (`import { Camera } from 'lucide-react'`), `className="w-4 h-4"` — mesma dimensão dos ícones SVG inline já usados nos botões "Senha" (`w-4 h-4`) e "Sair" ao lado dele. `lucide-react` já é dependência do projeto (`Usuarios.jsx`, `ModalScannerCamera.jsx` do PDV) — não é biblioteca nova.
- **Opção B** (alternativa, se Loom preferir zero import novo no arquivo): inline SVG com o mesmo `strokeWidth={2}` dos ícones vizinhos, path de câmera simples. Visualmente equivalente, só evita um import adicional em `Header.jsx` (que hoje usa só SVG inline, nenhum lucide).

Qualquer uma das duas deve ter o **mesmo peso visual** (viewBox 24x24, stroke 2, 16px renderizado) dos ícones de "Senha"/"Sair" ao lado — não introduzir ícone preenchido (filled) num Header que usa só outline.

### 1.4 Estados do Avatar

| Estado | Comportamento |
|---|---|
| `foto` presente | `<img>` com `object-cover`, `rounded-full`, fundo `bg-primary-100 dark:bg-violet-900/40` visível durante o carregamento da imagem (evita "flash" transparente) |
| `foto` ausente | Círculo com inicial (ver 1.2) |
| `foto` com URL que falha ao carregar (404/erro de rede) | **Não especificado no RF do Analista — Brush define:** `onError` do `<img>` deve cair para o estado "sem foto" (iniciais), nunca deixar ícone de imagem quebrada do navegador. Implementação sugerida: estado local `erroCarregamento` no próprio `Avatar.jsx`, setado `true` no `onError`, renderizando o bloco de iniciais quando `true` mesmo com `foto` preenchido |
| Avatar clicável (Header) | `cursor-pointer`, `hover:opacity-80` — sem necessidade de anel de foco adicional além do que o elemento clicável-pai já fornece |
| Avatar não-clicável (tabela de Usuários) | Sem `cursor-pointer`, sem `onClick` — é só visualização (RN-01 do Analista: essa tela não edita foto de terceiro) |

---

## 2. Modal "Alterar foto" (Header)

### 2.1 Gatilho e posicionamento

- Mesmo padrão visual do botão "Senha" já existente: `flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm`, cores conforme tabela da seção 0.
- Ordem no Header (grupo da direita, esquerda→direita): toggle tema → avatar + nome (clicável, abre o mesmo modal) → botão "Alterar foto" → botão "Senha" → botão "Sair". Avatar clicável e botão "Alterar foto" abrindo o **mesmo modal** é intencional — redundância de affordance é aceitável aqui, já que o botão com label explícito cobre o caso do usuário não perceber que o avatar é clicável.
- Label do botão: **"Foto"** (não "Alterar foto" por extenso) — segue a convenção de label curta já usada ao lado ("Senha", "Sair"), visível só em `sm:` e acima (`hidden sm:block`, igual aos vizinhos). Em mobile (<640px), só o ícone aparece — mesmo comportamento dos botões vizinhos.

### 2.2 Layout do modal (`<Modal title="Foto de perfil">`)

Largura/padding seguem o `Modal.jsx` genérico (não alterar o componente). Conteúdo interno, de cima para baixo:

```
┌─────────────────────────────────────┐
│  Foto de perfil                  ×  │  ← título do Modal (padrão)
├─────────────────────────────────────┤
│                                      │
│          [Avatar lg, 96px]           │  ← foto atual OU preview local OU iniciais
│         centralizado, mx-auto        │
│                                      │
│   [Remover foto]  (só se tem foto    │  ← texto link/secundário, abaixo do avatar,
│    E nenhum arquivo novo escolhido)  │     text-red-600 dark:text-red-400, sem
│                                      │     borda (link destrutivo, não botão
│                                      │     sólido — ação pouco frequente)
│                                      │
│   [input file: "Escolher foto"]      │  ← Button variant="secondary" cobrindo um
│                                      │     <input type="file" accept="image/*"
│                                      │     className="hidden"> — padrão de "botão
│                                      │     disfarçado de input file" já usado no
│                                      │     upload de extrato em Conciliação
│                                      │
│   [bloco de erro, se houver]         │  ← bg-red-50/border-red-200, mesmo padrão
│                                      │     do modal de senha
│                                      │
│              [Cancelar] [Salvar]     │  ← mesmo rodapé do modal de senha:
│                                      │     justify-end gap-3 pt-2
└─────────────────────────────────────┘
```

Espaçamento vertical interno: `space-y-4` entre os blocos (avatar+remover / input / erro / rodapé) — igual ao `space-y-4` já usado no `<form>` do modal de senha, nenhum espaçamento novo inventado.

### 2.3 Estados do modal

| Estado | O que muda visualmente |
|---|---|
| **Sem foto, nenhum arquivo escolhido** (quem nunca teve foto) | Avatar `lg` com iniciais. Sem "Remover foto" (RF-09: só aparece se `user.foto_url` existir). Botão "Escolher foto" visível. |
| **Com foto, nenhum arquivo novo escolhido** | Avatar `lg` mostra a foto atual (`user.foto_url`). "Remover foto" visível, abaixo do avatar. "Escolher foto" visível (permite trocar). |
| **Arquivo novo escolhido (preview local, ainda não enviado)** | Avatar `lg` passa a mostrar o **preview local** (`URL.createObjectURL`), não mais a foto antiga nem a inicial. "Remover foto" **esconde** nesse momento (ação não faz sentido para um arquivo que ainda nem foi salvo — evita ambiguidade "remover o quê, o antigo ou o novo?"). Nome do arquivo escolhido aparece como texto pequeno (`text-xs text-gray-500 dark:text-slate-400`) abaixo do botão "Escolher foto" (ex.: "foto-perfil.jpg selecionada"). "Salvar" passa a ficar habilitado (antes, sem arquivo escolhido, "Salvar" deve estar desabilitado — só "Cancelar" faz sentido sozinho). |
| **Enviando (loading)** | `Button` com prop `loading` no "Salvar" (spinner já padrão do componente, igual ao modal de senha) — desabilita "Cancelar" e "Escolher foto" durante o envio, para não trocar de arquivo no meio do upload. |
| **Erro** (RF-02/RN-02/RN-03 do backend: arquivo >5MB ou não é imagem) | Bloco vermelho acima do rodapé com a mensagem exata devolvida pela API (`error?.response?.data?.erro`) — nunca texto genérico tipo "Erro ao enviar". Preview local permanece visível (usuário pode trocar o arquivo sem perder o modal aberto). |
| **Sucesso** | Fecha o modal imediatamente (RF-10). Diferente do modal de senha (que mostra uma tela de confirmação intermediária), para foto Brush recomenda fechar direto — o resultado já é visualmente confirmado na hora pelo Avatar do Header mudando. Menos um clique que no fluxo de senha, intencional, não é inconsistência. |
| **Removendo foto (loading)** | Mesmo spinner, no link "Remover foto" em vez do botão "Salvar". |

### 2.4 Confirmação de remoção

RF-09 não especifica se "Remover foto" exige confirmação extra. Brush define: **sim**, `window.confirm('Remover sua foto de perfil?')` antes de disparar o `DELETE` — mesmo padrão já usado em `Usuarios.jsx::onBeforeSubmit` para o autobloqueio de acesso. É ação destrutiva sem "desfazer", então pede confirmação mesmo sendo de baixo impacto (alinhado à regra global "Ações destrutivas sem confirmação" como armadilha a evitar).

---

## 3. Integração no Header (visual, complementando RF-09/seção 7.2 do Analista)

- O avatar `sm` (32px) substitui exatamente o círculo de iniciais atual nas mesmas coordenadas (`gap-2` com o nome ao lado, nome em `<span className="hidden sm:block">`) — nenhuma mudança de espaçamento no Header fora da troca do próprio círculo.
- Área clicável do avatar: o `<div className="flex items-center gap-2">` que hoje envolve avatar+nome deve virar um elemento interativo (`<button>` ou `<div role="button" tabIndex={0}>` com handler de `Enter`/`Space`) para abrir o modal — hoje é `<div>` estático, sem affordance de clique nenhum. Precisa de `cursor-pointer` + `hover:opacity-80` para sinalizar que é interativo; sem isso, o usuário não tem pista visual de que pode clicar ali.

---

## 4. Integração em `Usuarios.jsx` / `ResourceCrud` (CA-08)

- Nova coluna **primeira da tabela**, `label: ''` (sem texto no cabeçalho — é só o avatar) — já especificado assim no RF-11/seção 7.4 do Analista; Brush confirma e detalha o visual:
  - Avatar `size="sm"` (32px) — mesma dimensão do Header, consistência entre os dois únicos pontos de avatar do sistema nesta manutenção.
  - Largura da coluna: só o círculo + padding de célula padrão da tabela (`px-4 py-3`, já usado nas demais colunas) — não alargar a coluna além do necessário; ela não deve competir por espaço com "Nome"/"E-mail" em telas estreitas.
  - Mobile (<640px): manter o comportamento de scroll horizontal padrão já existente no `ResourceCrud` para tabelas com várias colunas — avatar rola junto com o resto. Column-pinning é melhoria separada, fora de escopo (ver seção 5).

---

## 5. Sugestões para ciclo futuro (não implementar agora — fora de escopo desta manutenção)

```
- Paleta de cores rotativa por hash do nome/e-mail para o círculo de iniciais
  (estilo Gmail/Slack), em vez da cor fixa atual — mencionado no pedido original
  ("cores por inicial"), mas RF-08 do Analista já fixou cor única; mudar isso
  exigiria realinhar com Analista/Planner antes de implementar, não é decisão
  unilateral do Brush.
- Avatar de rh.Colaborador e clientes.Cliente — RN-10 do Analista já deixa isso
  fora de escopo; quando vier, o Avatar.jsx criado aqui é reaproveitável sem
  nenhuma mudança (props genéricas foto/nome/size, zero acoplamento a User).
- Column-pinning da coluna "Foto" na tabela de Usuários em viewport mobile.
```

---

## 6. Checklist de consistência visual (Sentinel pode usar para validar)

```
[ ] Avatar sm no Header tem exatamente 32px (w-8 h-8), igual ao círculo que substituiu
[ ] Cores do avatar sem foto idênticas nos dois modos (light/dark) às já usadas
    hoje no Header antes da mudança — nenhuma cor nova introduzida
[ ] Botão "Foto" no Header tem o mesmo padding/hover/cor dos botões "Senha"/"Sair"
    (comparar classes Tailwind, não só "parecido visualmente")
[ ] Modal "Alterar foto" usa o componente Modal.jsx genérico, não um modal customizado
[ ] Bloco de erro do modal de foto é idêntico (classes) ao bloco de erro do modal de senha
[ ] Botão "Salvar" desabilitado quando nenhum arquivo foi escolhido
[ ] "Remover foto" só aparece quando há foto_url E nenhum arquivo novo em preview
[ ] Avatar na tabela de Usuários tem o mesmo tamanho (sm) do Avatar do Header
[ ] onError da <img> do Avatar cai para iniciais, nunca ícone de imagem quebrada
[ ] Fontes seguem Plus Jakarta Sans/DM Sans já carregadas — nenhum import de fonte novo
[ ] Nenhuma biblioteca de componente nova introduzida (Avatar é inline Tailwind,
    igual ao resto do projeto)
```

---

## Passagem de bastão

```
✅ Especificação UI concluída — UidCore (Manutenção #72)
   Telas analisadas: 2 (Header.jsx, Usuarios.jsx) + 1 componente novo (Avatar.jsx)
   Componentes reutilizados: Modal.jsx, Button.jsx, ResourceCrud.jsx (extensão),
     padrão "botão disfarçado de input file" já usado em Conciliação
   Novos padrões: Avatar.jsx (3 tamanhos sm/md/lg), estado onError com fallback
     para iniciais, confirmação window.confirm() para "Remover foto"

📁 Arquivo: Especificacao_UI_Hotfix.md (salvo em /var/www/uidcore/)

➡️ Loom lê Especificacao_Hotfix.md (Analista, RFs/RNs/código de referência)
   + Especificacao_UI_Hotfix.md (este arquivo, camada visual/estados/espaçamento)
   antes de implementar Avatar.jsx, o modal do Header e a coluna do ResourceCrud
```
