# Especificação de Hotfix — UidCore PDV (Manutenção #21)

**Sistema:** UidCore (OS #7)
**Tipo:** `melhoria_ux` + `bug` (grupos 1, 2, 3, 5 = melhoria_ux/feature_pequena · grupo 4 = bug)
**Origem:** solicitação pós-lançamento do módulo PDV (Manutenção #15, concluída em 2026-08-05)
**Data:** 2026-08-05
**Complexidade:** média (5 grupos, 3 sem alteração de backend necessária, 1 com fix real de backend/frontend, 1 puramente de UI; frontend com 1 dependência nova)
**Requer aprovação comercial:** não (ajuste de melhoria em módulo já entregue, sem escopo novo de contrato)

> Esta especificação **substitui** o conteúdo anterior deste arquivo (que era
> da Especificação da Manutenção #15, já concluída e registrada no histórico
> do CLAUDE.md do projeto). O conteúdo antigo permanece rastreável via git
> history — não é necessário mantê-lo aqui.

---

## 1. Contexto

O módulo PDV (Manutenção #15, 2026-08-05) foi entregue e está em produção.
Este pedido reúne 5 grupos de ajustes pós-lançamento relatados pelo time de
caixa: leitor de código de barras incompleto, confirmação de que a busca de
produto já funciona, exibição de informações na abertura de caixa, um bug de
mensagem de erro crua na Frente de Caixa, e ajustes de UI no carrinho/split
de pagamento.

Todo o levantamento abaixo foi feito lendo o código real (backend e
frontend) antes de especificar qualquer requisito — nenhum item foi
assumido sem confirmação, conforme instruído pelo pedido.

---

## 2. AS-IS (confirmado por leitura de código)

| Item do pedido | Situação real confirmada |
|---|---|
| 1) Leitor físico | Busca por nome/código já funciona (`backend/produtos/views.py:13` — `search_fields = ['nome', 'codigo_barras']`). Input de busca em `FrenteDeCaixa.jsx:321-329` **não tem `onKeyDown`** — Enter não faz nada. Resultado só é adicionado via clique no dropdown (`onClick={() => adicionarProduto(p)}`, linha 351). |
| 1) Câmera | Não existe — nenhum botão de câmera, nenhuma lib de leitura de código de barras no projeto. `frontend/package.json` confirmado: dependências são apenas `@tanstack/react-query`, `axios`, `lucide-react`, `react`, `react-dom`, `react-router-dom`, `zustand`. Nenhuma lib tipo `@zxing/library`, `html5-qrcode` ou `quagga2` instalada. |
| 2) Vincular produto na busca | Mesmo gap do item 1 — busca e dropdown clicável já funcionam ponta a ponta (backend + frontend). Não é funcionalidade ausente, é o mesmo fix de auto-vínculo via Enter/scan do item 1. Nenhum trabalho adicional além do já descrito ali. |
| 3) Abrir Caixa — fluxo | Confirmado que **já existe e já funciona**: `AberturaCaixa.jsx` → `POST /pdv/sessoes/` → `SessaoCaixaViewSet.create()` (`pdv/views.py:71-83`) → `services.abrir_sessao()` (`pdv/services.py:173-199`) seta `operador=usuario` (linha 194) e `data_abertura` é `auto_now_add=True` no model (`pdv/models.py:49`) — automático, sem intervenção do frontend. **Não falta lógica de backend.** |
| 3) Abrir Caixa — exibição | `AberturaCaixa.jsx` importa `useAuthStore` e lê `user` (linha 15) **mas nunca renderiza** nome do operador nem data/hora atual em nenhum lugar da tela (linhas 85-179 revisadas por completo). O campo de valor de abertura está rotulado apenas "Valor de abertura" (linha 148), sem menção a "Fundo de Troco". |
| 3) Campo `operador` — User vs Funcionario | Confirmado por leitura de `pdv/models.py:43-47`: `SessaoCaixa.operador` é `ForeignKey(settings.AUTH_USER_MODEL, ...)` — aponta pro model `User` do Django, não pro app `rh`. Confirmado por leitura de `rh/models.py` completo: `rh.Funcionario` é uma entidade **isolada**, sem nenhuma FK para `User`/`auth` (campos: nome, cpf, email, cargo, datas, salário, regime) — usada só pelo módulo de RH (cargos, folha, férias). **Hoje não existe nenhuma ponte entre `User` e `Funcionario`.** Trocar `operador` para apontar pra `Funcionario` exigiria: (a) decidir se todo `User` do sistema ganha um `Funcionario` correspondente ou se seria um campo novo paralelo, e (b) migração de dados dos registros de `SessaoCaixa`/`MovimentoCaixa`/`Venda` já existentes em produção — mudança estrutural, não um ajuste de UI. |
| 4) Bug `sessao_caixa: Nenhuma sessao...` | Confirmado por leitura de `pdv/views.py:173-196` (`VendaViewSet.create()`): quando não há `SessaoCaixa` com `operador=request.user, status='ABERTA'`, retorna `400` com `{'sessao_caixa': 'Nenhuma sessao de caixa aberta para este operador.'}` — mensagem crua de backend, exatamente como descrito no pedido. Confirmado em `FrenteDeCaixa.jsx:88-97` (`criarVenda()`): o `catch` desse POST só chama `mostrarToast(extractErrorMessage(err, ...), 'error')` — **não redireciona** para `/pdv/abertura`, diferente do `useEffect` de carregamento de sessão (linhas 65-74) que **já redireciona** corretamente quando `GET /pdv/sessoes/atual/` falha. Existe uma janela de corrida real entre o `GET /sessoes/atual/` (linha 66) e o `POST /pdv/vendas/` disparado logo em seguida pelo `useEffect` da linha 99-103 — se a sessão for fechada nesse intervalo (ex: 2ª aba, expiração, outra sessão fechando a mesma conta), o operador vê o erro cru em vez de ser levado de volta pra abertura. |
| 5) Card Carrinho | `components/ui/Card.jsx` (componente genérico) usa `px-6 py-4` de padding fixo em todo conteúdo, sem `max-height`/scroll interno. Estado vazio do carrinho (`FrenteDeCaixa.jsx:380-383`) soma `py-12` adicional — soma de paddings deixa o card visualmente alto mesmo com poucos ou nenhum item. |
| 5) SplitPagamento | `components/SplitPagamento.jsx` confirmado: grid de 2 colunas (`grid-cols-2 gap-2`, linha 94) para Valor/Conta, labels em `text-xs` (linhas 97, 111) e inputs em `text-sm` (linha 105) dentro de um card já compacto (`p-3 space-y-2`, linha 81) — confirma a queixa de "campos apertados". Responsividade mobile é feita via `BottomBar` fixa em `FrenteDeCaixa.jsx:522-540` (`md:hidden`), que não depende do layout interno do `SplitPagamento` — há margem para aumentar espaçamento sem quebrar o layout mobile. |

---

## 3. TO-BE

### Grupos 1+2 — Leitor de código de barras (físico + câmera) e auto-vínculo

- Enter no campo de busca com 1 resultado de match exato de `codigo_barras` adiciona o produto direto ao carrinho, sem exigir clique.
- Botão "Escanear com câmera" ao lado da busca, usando lib leve de leitura de código de barras via `getUserMedia`, preenchendo o campo de busca e disparando o mesmo fluxo de auto-adição.
- Permissão de câmera negada exibe mensagem clara via toast já existente na tela, sem travar a tela.

### Grupo 3 — Abrir Caixa

- Tela de abertura exibe operador logado e data/hora atual antes de confirmar.
- Campo de valor de abertura reforça o termo "Fundo de Troco" usado pelo time de caixa.
- Campo `operador` continua apontando para `User` do Django — mudança para `rh.Funcionario` fica **fora de escopo** deste hotfix (ver RN-03).

### Grupo 4 — Bug de sessão

- `criarVenda()` trata o erro 400 de `sessao_caixa` redirecionando para `/pdv/abertura` com mensagem amigável, no mesmo padrão já usado pelo carregamento inicial de sessão.

### Grupo 5 — UI Carrinho e SplitPagamento

- Card do Carrinho reduzido em altura/padding sem cortar funcionalidade.
- Campos do SplitPagamento com mais espaçamento e fonte legível, preservando o layout mobile (`BottomBar`, breakpoints `<768px`).

---

## 4. Requisitos Funcionais

| ID | Descrição | MoSCoW |
|---|---|---|
| RF-17 | Ao pressionar Enter no campo de busca de produto da Frente de Caixa, se houver exatamente 1 resultado com match exato de `codigo_barras`, o sistema deve adicionar o produto ao carrinho automaticamente, sem exigir clique. | Must |
| RF-18 | O sistema deve oferecer um botão "Escanear com câmera" ao lado do campo de busca que abre a câmera do dispositivo e decodifica código de barras em tempo real. | Must |
| RF-19 | Ao decodificar um código de barras via câmera, o sistema deve preencher o campo de busca com o código lido e disparar o mesmo fluxo de adição automática do RF-17. | Must |
| RF-20 | Se a permissão de câmera for negada, o sistema deve exibir mensagem clara ao operador sem travar a tela do PDV. | Must |
| RF-21 | A tela de Abertura de Caixa deve exibir o nome do operador logado e a data/hora atual antes ou durante o preenchimento do formulário. | Should |
| RF-22 | O campo "Valor de abertura" deve deixar explícito o termo "Fundo de Troco" (rótulo e/ou texto de apoio). | Should |
| RF-23 | Quando `POST /pdv/vendas/` retornar 400 por ausência de sessão de caixa aberta (`sessao_caixa`), o frontend deve redirecionar o operador para `/pdv/abertura` com mensagem amigável, em vez de exibir a mensagem crua do backend. | Must |

## 5. Requisitos Não Funcionais

| ID | Descrição |
|---|---|
| RNF-06 | Leitura de código de barras via câmera deve ser testada em pelo menos 1 dispositivo Android e, se possível, 1 iOS, antes da entrega ao Sentinel. |
| RNF-07 | Câmera só pode ser acessada via HTTPS (já garantido em produção pelo domínio + nginx) — não implementar fallback HTTP. |
| RNF-08 | Ajustes de UI (Carrinho, SplitPagamento) não podem quebrar o layout mobile existente (`BottomBar`, breakpoints `<768px` já usados em `FrenteDeCaixa.jsx`). |
| RNF-09 | A lib de leitura de código de barras adicionada deve ser leve e estável — Loom decide entre `@zxing/library`, `html5-qrcode` ou `quagga2`, documentando a escolha no commit. |

## 6. Regras de Negócio

- **RN-09** — O auto-vínculo por Enter/scan (RF-17/RF-19) só dispara quando há **exatamente 1** resultado com match **exato** de `codigo_barras` (não usar match parcial/nome, para evitar adicionar produto errado). Múltiplos resultados ou match parcial mantêm o comportamento atual (dropdown clicável).
- **RN-10** — O leitor físico (USB/Bluetooth) continua funcionando por emulação de teclado — RF-17 não substitui esse fluxo, apenas completa o passo final que faltava.
- **RN-11** — A leitura por câmera é complementar ao leitor físico, nunca obrigatória — o operador pode continuar digitando/usando leitor físico normalmente.
- **RN-12 [CONFIRMAR COM LUIZ EDUARDO]** — o campo `SessaoCaixa.operador` permanece apontando para `User` do Django nesta manutenção. Não existe hoje nenhuma ligação entre `User` e `rh.Funcionario` no UidCore — migrar esse campo é mudança estrutural (models + dados já em produção), fora do escopo deste hotfix. Se houver necessidade de vincular sessões de caixa a um cadastro de RH, tratar como manutenção própria, com o Analista rodando levantamento dedicado.
- **RN-13** — O redirecionamento do RF-23 deve usar o mesmo padrão de UX já usado no carregamento inicial da Frente de Caixa (`navigate('/pdv/abertura')`), para manter consistência.

## 7. Telas Detalhadas

### 7.1 Frente de Caixa (`FrenteDeCaixa.jsx`)

- Campo de busca de produto (`buscaRef`, linha 322): adicionar `onKeyDown` que, ao detectar `Enter`, verifica se `resultadosBusca` tem exatamente 1 item com `codigo_barras` igual ao texto digitado (match exato) e, se sim, chama `adicionarProduto(resultadosBusca[0])` diretamente.
- Botão "Escanear com câmera": novo ícone ao lado do botão `ScanLine` existente (linha 331-338, que hoje só foca o campo) — abrir modal/overlay com preview de câmera via lib escolhida pelo Loom. Ao decodificar, chamar `setBusca(codigoLido)` e reaproveitar o mesmo fluxo de match exato do Enter.
- Erro de permissão de câmera: usar o sistema de toast já existente (`mostrarToast(msg, 'error')`, linha 59-62).
- Card "Carrinho" (linha 378-397): reduzir padding do estado vazio (`py-12` → algo menor, ex. `py-6`/`py-8`) e avaliar `max-height` com scroll interno se a lista de itens crescer.
- `criarVenda()` (linha 88-97): no bloco `catch`, verificar se `err?.response?.data?.sessao_caixa` existe — se sim, chamar `navigate('/pdv/abertura')` com toast explicativo (ex: "Sua sessão de caixa foi encerrada. Abra o caixa novamente."); caso contrário, manter o comportamento atual de toast genérico para outros erros.

### 7.2 Abertura de Caixa (`AberturaCaixa.jsx`)

- Adicionar bloco visual (ex: acima do formulário ou dentro do card, linha 115+) mostrando `user.nome` (ou campo equivalente do `useAuthStore`, já importado na linha 15 mas não usado para exibição) e a data/hora atual formatada em pt-BR.
- Label do campo (linha 147-149): alterar para "Fundo de Troco" ou manter "Valor de abertura" com texto de apoio explícito "(Fundo de Troco)" — Loom decide o texto exato mantendo consistência com o restante da UI.

### 7.3 SplitPagamento (`components/SplitPagamento.jsx`)

- Grid de Valor/Conta (linha 94): aumentar `gap` e padding interno das linhas (`p-3` → `p-4`), aumentar tamanho de fonte dos labels (`text-xs` → `text-sm` onde couber) e dos inputs, sem estourar o grid de 2 colunas em telas pequenas — testar em `<768px` junto da `BottomBar`.

## 8. Spec Backend

**Nenhuma alteração de backend é necessária nesta manutenção.** Confirmado por leitura de código:

- Busca por `nome`/`codigo_barras` já existe (`produtos/views.py:13`).
- `abrir_sessao()` já seta `operador` e `data_abertura` automaticamente (`pdv/services.py:173-199`, `pdv/models.py:43-49`).
- O erro 400 de `VendaViewSet.create()` (`pdv/views.py:173-196`) já está correto e semanticamente claro — o ajuste é 100% de tratamento no frontend (RF-23).

Se o Forge, ao implementar, identificar necessidade real de endpoint novo (ex: dados de operador mais ricos que o `User` já expõe), deve escalar para o Planner antes de expandir escopo — não está previsto aqui.

## 9. Spec Frontend

- **Nova dependência** (Loom escolhe): `@zxing/library`, `html5-qrcode` ou `quagga2` — adicionar via gerenciador de pacotes padrão do projeto, documentar escolha no commit (RNF-09).
- `FrenteDeCaixa.jsx`: `onKeyDown` no input de busca (RF-17), novo botão + modal/overlay de câmera (RF-18/19/20), tratamento de erro 400 de `sessao_caixa` em `criarVenda()` (RF-23), redução de padding do Card Carrinho (item 5).
- `AberturaCaixa.jsx`: exibição de operador + data/hora (RF-21), reforço textual "Fundo de Troco" (RF-22).
- `components/SplitPagamento.jsx`: ajustes de espaçamento/fonte (item 5), preservando grid mobile.
- Nenhuma alteração em rotas, stores ou contratos de API — mudanças são internas às páginas/componentes já existentes.

## 10. Fora do Escopo

- Migração do campo `operador` de `User` para `rh.Funcionario` (RN-12) — decisão estrutural, requer confirmação de Luiz Eduardo e levantamento próprio.
- Qualquer alteração no backend do PDV — nenhum gap real de backend foi encontrado nos 5 grupos.
- Redesenho completo do SplitPagamento ou do fluxo de pagamento — apenas ajuste de espaçamento/legibilidade.

## 11. Riscos e Dependências

- Bibliotecas de leitura de código de barras via câmera variam em performance entre navegadores mobile (Android Chrome vs iOS Safari) — Loom deve validar em pelo menos 1 dispositivo real antes de considerar RF-18/19 concluído (RNF-06).
- A janela de corrida do bug do item 4 (RF-23) é rara em uso normal (1 operador, 1 aba) — o fix cobre o sintoma (UX do erro) mas não elimina a possibilidade de concorrência real entre abas/dispositivos; se o time de caixa relatar recorrência alta, pode indicar necessidade de trava adicional no backend (fora de escopo aqui, tratar como nova manutenção se ocorrer).
- Nenhuma migration nova é esperada — validar com o Forge que de fato nenhuma alteração de model é necessária antes de fechar o ciclo.

## 12. Sentinel — Roteiro de Teste

1. Buscar produto por nome parcial → múltiplos resultados → confirmar que Enter **não** adiciona nada automaticamente (RN-09).
2. Buscar produto digitando `codigo_barras` exato com 1 único resultado → pressionar Enter → confirmar item adicionado ao carrinho sem clique (RF-17).
3. Testar leitor físico USB/Bluetooth (emulação de teclado) ponta a ponta — digita código + Enter automático → item adicionado (RN-10).
4. Abrir "Escanear com câmera" em pelo menos 1 dispositivo Android real → escanear código de barras real → confirmar preenchimento do campo + adição automática (RF-18/19, RNF-06).
5. Negar permissão de câmera no navegador → confirmar mensagem clara via toast, sem tela travada (RF-20).
6. Abrir tela de Abertura de Caixa → confirmar exibição do nome do operador logado e data/hora atual (RF-21) e menção a "Fundo de Troco" no campo de valor (RF-22).
7. Simular sessão fechada em outra aba/dispositivo enquanto a Frente de Caixa está carregando → confirmar redirecionamento para `/pdv/abertura` com mensagem amigável, sem exibir o texto cru `sessao_caixa: Nenhuma sessao de caixa aberta...` (RF-23).
8. Conferir visualmente Card do Carrinho com 0, 1 e vários itens — altura reduzida sem cortar conteúdo (item 5).
9. Conferir SplitPagamento em desktop e mobile (`<768px`) — campos legíveis, `BottomBar` intacta, nenhuma quebra de layout (RNF-08).
10. 0 falhas obrigatório, 100% dos RFs Must com verificação — conforme regra global do Sentinel (CLAUDE.md).

---

## 13. Observações finais do Analista

Dos 5 grupos do pedido, os itens 2 e parte do item 3 (fluxo de abertura de
caixa) **já estão implementados corretamente no backend** — o pedido do
cliente descrevia como "faltando" algo que na verdade é só falta de
**exibição**/UX, não de lógica ausente. Isso foi confirmado lendo o código
real antes de especificar qualquer RF, evitando retrabalho desnecessário.

O único ponto que abre uma decisão de arquitetura (RN-12, campo `operador`)
foi marcado como fora de escopo e não prescrito como fix — cabe a Luiz
Eduardo decidir se isso vira uma manutenção própria.

➡️ **Planner:** rotear conforme tipo — grupos 1, 2, 3 e 5 = `melhoria_ux`/
`feature_pequena` (Pipeline B/C, sem aprovação comercial); grupo 4 = `bug`
(Pipeline B, direto). Nenhum requer escalonamento a Luiz Eduardo, exceto a
confirmação assíncrona de RN-12 (não bloqueia o restante da entrega).
