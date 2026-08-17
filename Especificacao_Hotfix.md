# Especificação — Manutenção #36
**Elaborado por:** Analista (MODO HOTFIX)
**Data:** 2026-08-17
**Sistema:** UidCore (OS #7)
**Solicitação original:** módulo PDV/Caixa parcialmente implementado com bugs — card de
"sessão já aberta" quebrado (Conta: #undefined / Aberta às Invalid Date), dropdown
"Conta" na abertura de caixa misturando contas financeiras com caixa operacional, e
gestão de caixas (sangria/suprimento/histórico) incompleta.

**Instrução do Planner:** investigar o código atual antes de alterar — a modelagem já
existe (Manutenção #15, #21-24), ajustar em vez de recriar do zero, exceto onde houver
erro conceitual.

---

## Classificação

```
tipo: bug + melhoria_ux (parte já implementada, parte com gaps reais de validação)
sistema: UidCore
caminho_afetado: backend/pdv/* (models, services, views, serializers) +
                 frontend/src/pages/pdv/* (AberturaCaixa, FrenteDeCaixa,
                 FechamentoCaixa, RelatorioSessoesCaixa, components/ResumoSessao)
complexidade: media
requer_aprovacao_comercial: false
```

---

## Diagnóstico confirmado (leitura direta dos arquivos — não do pedido)

O pedido descreve o módulo como "parcialmente implementado". A leitura direta mostra
algo diferente: a modelagem de `SessaoCaixa`/`MovimentoCaixa`/`Venda` já existe desde a
Manutenção #15 e já recebeu 4 rodadas de ajuste (#21, #22, #23, #24). Boa parte do que o
pedido pede como "a fazer" **já está implementada**. A investigação encontrou um
conjunto diferente de problemas reais — alguns coincidem com o pedido, outros não.

### BUG 1 do pedido ("Conta: #undefined" / "Aberta às Invalid Date") — NÃO reproduzido no código-fonte atual

Os dois únicos lugares do frontend que renderizam esse card:
- `AberturaCaixa.jsx:117` — `sessaoAtiva.conta_nome || `#${sessaoAtiva.conta}`` +
  `data_abertura` formatado com `toLocaleTimeString`
- `FrenteDeCaixa.jsx:353` — mesmo padrão, `sessao.conta_nome || `Conta #${sessao.conta}``

Ambos já usam fallback correto e o nome de campo bate com o que o backend envia:
`SessaoCaixaSerializer` (backend/pdv/serializers.py) já expõe `conta_nome` (via
`source='conta.nome'`) e `data_abertura` (DateTimeField, `auto_now_add=True`). A action
`GET /pdv/sessoes/atual/` (views.py) retorna esse serializer. Não há mismatch de nome de
campo nesses dois pontos hoje.

**Não estou descartando o bug — estou documentando que ele não está no código-fonte que
foi lido.** Duas hipóteses, ambas a verificar pelo Sentinel antes de fechar como
resolvido:
1. Já foi corrigido em ciclo anterior não documentado no CLAUDE.md;
2. O bundle de produção está desatualizado em relação ao código-fonte (stale build) —
   nesse caso a ação correta é um novo deploy, não uma mudança de código.

Achado relevante (ver seção seguinte): o mesmo *padrão* de bug (nome de campo que o
frontend espera e o backend não envia, ou vice-versa) **existe de fato em outro lugar**
do mesmo módulo — o que sugere que o relato do cliente é real, só que a tela errada foi
identificada. Ver RF-04 e RF-05 abaixo.

### BUG 2 do pedido (dropdown "Conta" misturando contas financeiras) — JÁ IMPLEMENTADO no frontend, FALTA reforço no backend

A decisão arquitetural já foi tomada e já está no código: `Conta.tipo` (financeiro/models.py)
já tem o choice `CAIXA` desde antes desta manutenção, e `AberturaCaixa.jsx` já busca
`api.get('/financeiro/contas/?tipo=CAIXA&page_size=100')` — o dropdown já filtra
corretamente, sem misturar CORRENTE/POUPANCA/CARTEIRA.

**Confirmando a decisão pedida:** a opção certa aqui é a primeira listada no pedido
(filtrar por `tipo=CAIXA` na `Conta` existente), não criar um model `PontoDeVenda`
separado — é exatamente o que já foi implementado. Não recriar, não desacoplar.

**Gap real encontrado:** o filtro por `tipo=CAIXA` existe **apenas no frontend**. O
backend (`services.abrir_sessao()`, backend/pdv/services.py:173-199) aceita qualquer
`conta_id` ativo, sem validar `conta.tipo == 'CAIXA'`. Uma chamada direta à API
(`POST /api/v1/pdv/sessoes/` com `conta` de uma conta CORRENTE ou CARTEIRA) abre sessão
de caixa vinculada a uma conta financeira — a regra de negócio só existe como filtro de
UI, não como validação de servidor. Isso é o "erro conceitual" residual do BUG 2: a
modelagem está certa, a garantia não está. Ver RF-01.

### Gap real 1 — "1 caixa aberto por operador" não é validado (o pedido pede isso explicitamente)

A constraint atual (`SessaoCaixa.Meta.constraints`, models.py) é:
```python
models.UniqueConstraint(fields=['conta'], condition=models.Q(status='ABERTA'),
                         name='uniq_sessao_aberta_por_conta')
```
Ou seja, **1 sessão aberta por CONTA**, não por operador. `services.abrir_sessao()`
só faz lock e checagem por `conta`. Isso significa que hoje o mesmo operador pode abrir
sessão ABERTA simultânea em duas contas-caixa diferentes (ex: "Caixa Loja 1" e "Caixa
Loja 2") sem que nada no backend impeça — só a constraint de conta única bloqueia
reabrir a mesma conta duas vezes.

O pedido é explícito: *"Só pode existir 1 caixa ABERTO por operador (validar no
backend, não confiar só no frontend)."* Isso não existe hoje. É RN nova, não ajuste de
UI. Ver RN-01 e RF-02.

(Nota: `sessao_atual` e `VendaViewSet.create()` já *assumem* implicitamente 1 sessão por
operador ao fazer `filter(operador=..., status='ABERTA').first()` — mas isso é uma
leitura, não uma trava de escrita. Se dois abrirem simultaneamente em contas
diferentes, ambas ficam "atuais" para esse operador ao mesmo tempo, e esse `.first()`
vira não-determinístico.)

### Gap real 2 — resumo da sessão (vendas por forma de pagamento, sangrias, suprimentos) nunca chega do backend

`FechamentoCaixa.jsx` e `ResumoSessao.jsx` (componente compartilhado) esperam um campo
`resumo` no payload de `GET /pdv/sessoes/atual/` (ou do objeto sessão), com o formato
(documentado no próprio comentário do componente):
```js
// resumo — { por_metodo: [{metodo_nome, total}], vendas_dinheiro, sangrias, suprimentos }
```
`SessaoCaixaSerializer` (backend) **não tem esse campo**. Resultado real hoje em produção
(se o build estiver atualizado):
- Na tela de Fechar Caixa, os KPIs "Total Vendas", "Sangrias", "Suprimentos" sempre
  mostram R$ 0,00 (porque `resumo` chega `undefined` → `res.data.resumo || {}` vira `{}`);
  a seção "Vendas por forma de pagamento" nunca renderiza (`resumo.por_metodo` vazio).
- O "Valor calculado em caixa" mostrado antes de fechar usa
  `resumo?.valor_calculado_dinheiro ?? sessao?.valor_fechamento_calculado ?? 0` — mas
  `valor_fechamento_calculado` só é preenchido em `fechar_sessao()` (services.py:247),
  ou seja, é `null` enquanto a sessão está ABERTA. O operador não vê o valor calculado
  do caixa (o próprio propósito da tela) até *depois* de já ter fechado.

Esse é o gap mais importante da seção "ESCOPO GERAL" do pedido — "preciso enxergar...
sangrias e suprimentos" já existe em modelo e em cálculo (a lógica de
`valor_abertura + vendas à vista + suprimentos - sangrias` já está pronta e testada
dentro de `fechar_sessao()`), só não é exposta **antes** do fechamento, que é quando o
operador precisa dela para conferir. Ver RF-03.

### Gap real 3 — mesmo padrão do BUG 1 (mismatch de campo), confirmado em outra tela

`RelatorioSessoesCaixa.jsx` (linhas ~152, ~419, ~426) usa `sessao.valor_contagem_fisica`
para a coluna "Contagem". Esse campo **não existe** — nem no model, nem no serializer.
O nome real do campo é `valor_fechamento_informado`. Resultado: a coluna "Contagem" no
relatório de sessões sempre mostra "—", mesmo para sessões fechadas com contagem física
informada pelo operador. Este é o achado que dá mais peso à hipótese de "stale build"
para o BUG 1 original — o padrão de erro (frontend referenciando um nome de campo que
não bate com a API) é real e comprovado neste módulo, só que num arquivo diferente do
citado no pedido. Ver RF-04.

### Gap real 4 — filtro por operador no relatório de histórico (pedido explícito) existe no backend, falta na tela

`SessaoCaixaViewSet.filterset_fields = ['conta', 'operador', 'status']` (views.py) já
aceita `?operador=<id>` — o backend está pronto. `RelatorioSessoesCaixa.jsx` tem filtro
de período (`dataInicio`/`dataFim`), status e conta, mas **não tem filtro de operador na
UI** — o pedido pede explicitamente "filtro por período e por operador". Ver RF-05.

### O que já está correto e não deve ser mexido

- Modelagem `SessaoCaixa` / `MovimentoCaixa` já bate com a modelagem de referência do
  pedido (nomes diferentes em alguns campos — ver Nota de nomenclatura abaixo — mas
  semanticamente equivalente). Não recriar.
- `MovimentoSerializer.motivo` já é `CharField()` obrigatório (não `allow_blank`) —
  sangria/suprimento sem motivo já retorna 400. RN já satisfeita, nenhuma ação.
- Cálculo de fechamento (`fechar_sessao()`) já implementa exatamente a fórmula pedida:
  abertura + suprimentos + vendas à vista - sangrias, comparado com o informado, com
  `diferenca` exposta. RN já implementada e testada
  (`AbrirSessaoServiceTest.test_fechar_sessao_calcula_diferenca`), e nunca bloqueia por
  diferença.
- Tela de listagem/histórico (`RelatorioSessoesCaixa.jsx`) já existe com paginação,
  filtro de período, status, conta, totalizador de diferença e modal de detalhe — só
  falta o filtro de operador (gap real 4) e o campo com nome errado (gap real 3).

### Nota de nomenclatura (não é bug, é mapeamento pedido → existente)

| Pedido | Já existe como | Ação |
|---|---|---|
| `Caixa` | `SessaoCaixa` | manter nome existente |
| `valor_fechamento_sistema` | `valor_fechamento_calculado` | manter nome existente |
| `MovimentoCaixa.responsavel` | `MovimentoCaixa.operador` | manter nome existente |
| `MovimentoCaixa.criado_em` | `MovimentoCaixa.data_hora` (+ `created_at` do BaseModel) | manter nome existente |

Não renomear campos já em produção sem necessidade — risco de regressão sem ganho real
(a Manutenção #33 foi um rename intencional pedido explicitamente pelo cliente; aqui não
há esse pedido).

---

## Requisitos Funcionais

```
RF-01 (Must)   - Backend valida conta.tipo == 'CAIXA' na abertura de sessão
                 (services.abrir_sessao()), rejeitando com 400 legível
                 ({'conta': 'Conta informada não é do tipo CAIXA.'}) qualquer
                 conta_id de tipo diferente, mesmo que ativa. Fecha o gap
                 conceitual do BUG 2 — regra deixa de depender só do filtro de UI.
RF-02 (Must)   - Backend valida "1 sessão ABERTA por operador" dentro da mesma
                 transação/lock já usada em abrir_sessao(), retornando 400
                 legível ({'operador': 'Você já tem uma sessão de caixa aberta
                 em outra conta.'}) em vez de permitir abertura simultânea.
                 UniqueConstraint condicional em operador + status='ABERTA'
                 como barreira de última linha (mesmo padrão já usado hoje para
                 conta). Nota técnica para o Forge: usar chave de lock advisory
                 distinta da usada para conta_id (ex.: pg_advisory_xact_lock(2,
                 operador.id) vs. o pg_advisory_xact_lock(conta.id) de 1
                 argumento já usado hoje) para não colidir namespaces de lock.
RF-03 (Must)   - Backend expõe resumo calculado ao vivo (sem persistir) na
                 resposta de GET /pdv/sessoes/atual/ e GET /pdv/sessoes/{id}/,
                 no formato já esperado pelo frontend: { por_metodo:
                 [{metodo_nome, total}], vendas_dinheiro, sangrias,
                 suprimentos, valor_calculado_dinheiro }. Reaproveitar a lógica
                 já escrita em fechar_sessao() (services.py:222-244), extraída
                 para função utilitária compartilhada (ex.:
                 calcular_resumo_sessao(sessao)) — sem duplicar a fórmula.
RF-04 (Must)   - Corrigir em RelatorioSessoesCaixa.jsx as 3 ocorrências de
                 sessao.valor_contagem_fisica para sessao.valor_fechamento_informado
                 (coluna desktop, card mobile, modal de detalhe).
RF-05 (Should) - Adicionar filtro por operador em RelatorioSessoesCaixa.jsx —
                 novo Select na barra de filtros, ao lado do filtro de conta
                 já existente. Backend já aceita ?operador=<id>; só falta
                 popular a lista de operadores e incluir no params de
                 carregarSessoes(), no mesmo padrão já usado para contaFiltro.
RF-06 (Must)   - Sentinel deve validar em ambiente real (não só ler código) se
                 o BUG 1 do pedido (card "Conta: #undefined"/"Invalid Date")
                 ainda reproduz, já que não foi encontrado no código-fonte
                 lido. Se reproduzir, é sinal de bundle de produção
                 desatualizado — escalar para o Pilot confirmar publicação do
                 deploy mais recente, não reabrir código já correto.
```

## Regras de Negócio

```
RN-01 - Uma Conta só pode receber SessaoCaixa se tipo == 'CAIXA' (validação de
        servidor, não só filtro de dropdown). Cobre RF-01.
RN-02 - Um operador não pode ter mais de 1 SessaoCaixa com status='ABERTA'
        simultaneamente, independente da conta. Cobre RF-02 — é a regra
        literal pedida pelo cliente.
RN-03 - Sangria e Suprimento exigem motivo não vazio — JÁ IMPLEMENTADO
        (MovimentoSerializer.motivo é CharField() obrigatório), nenhuma ação.
RN-04 - Fechamento calcula valor_fechamento_calculado automaticamente
        (abertura + suprimentos + vendas em dinheiro/pix/débito − sangrias) e
        nunca bloqueia por diferença — JÁ IMPLEMENTADO em fechar_sessao(),
        nenhuma ação.
RN-05 - O resumo de vendas por forma de pagamento, sangrias e suprimentos deve
        estar disponível ANTES do fechamento (sessão ainda ABERTA), não só
        depois. Cobre RF-03.
```

---

## Telas afetadas (detalhamento)

### Tela: Abrir Caixa (`AberturaCaixa.jsx`)
- Sem mudança de layout. O dropdown já filtra por `tipo=CAIXA` — nenhuma ação de UI.
- Tratamento de erro: já existe `if (data?.conta) setErrors({conta: ...})` — precisa
  também tratar a nova chave de erro `operador` vinda de RF-02 (mostrar como toast de
  erro via `mostrarToast`, já que não há campo "operador" no formulário para anexar
  inline).

### Tela: Frente de Caixa (`FrenteDeCaixa.jsx`)
- Nenhuma mudança funcional nesta manutenção — card de sessão já usa os nomes de campo
  corretos (ver RF-06 para validação em produção).

### Tela: Fechar Caixa (`FechamentoCaixa.jsx`) + componente `ResumoSessao.jsx`
- Passam a receber `resumo` de verdade do backend (RF-03) — sem mudança de código nesses
  dois arquivos além de garantir que o `resumo` chega preenchido; o componente já foi
  escrito esperando esse formato, só nunca recebeu dado real.

### Tela: Relatório de Sessões de Caixa (`RelatorioSessoesCaixa.jsx`)
- Corrigir `valor_contagem_fisica` → `valor_fechamento_informado` (RF-04).
- Adicionar filtro de operador na barra de filtros, mesmo padrão visual do filtro de
  conta já existente (RF-05).

---

## Especificação técnica — Backend (Forge)

1. `backend/pdv/services.py`:
   - `abrir_sessao()`: adicionar validação `conta.tipo == 'CAIXA'` (RF-01) e validação
     de sessão já aberta por operador, com lock advisory dedicado (RF-02).
   - Extrair `calcular_resumo_sessao(sessao)` a partir da lógica hoje inline em
     `fechar_sessao()` (linhas 222-244), reutilizável tanto para sessão ABERTA quanto
     FECHADA.
2. `backend/pdv/models.py`: nova `UniqueConstraint` condicional em `operador` +
   `status='ABERTA'` em `SessaoCaixa.Meta.constraints` (RF-02) — gerar migration.
   **Atenção:** antes de aplicar, auditar se já existem sessões ABERTAS duplicadas por
   operador em produção — a migration falha ao criar a constraint se já houver violação
   nos dados atuais.
3. `backend/pdv/serializers.py`: `SessaoCaixaSerializer` ganha campo `resumo` (via
   `SerializerMethodField`, chamando `calcular_resumo_sessao`) — não persistido, só
   leitura (RF-03).
4. `backend/pdv/tests.py`: cobrir os 2 casos novos (conta tipo errado rejeitada com 400;
   segunda sessão do mesmo operador em conta diferente rejeitada com 400) + teste de que
   `resumo` vem populado corretamente com vendas/sangria/suprimento reais, tanto para
   sessão ABERTA quanto FECHADA.
5. Nenhuma mudança em `urls.py` — rotas existentes já bastam.

## Especificação técnica — Frontend (Loom)

1. `frontend/src/pages/pdv/RelatorioSessoesCaixa.jsx`:
   - Trocar as 3 ocorrências de `valor_contagem_fisica` por `valor_fechamento_informado`.
   - Adicionar estado `operadorFiltro`, `Select` de operador na barra de filtros
     (reaproveitar fonte de dados de usuários/operadores já disponível no projeto — não
     criar endpoint novo se já existir algo equivalente), incluir em `params` de
     `carregarSessoes()` e em `limparFiltros()`.
2. `frontend/src/pages/pdv/AberturaCaixa.jsx`:
   - Tratar chave de erro `operador` retornada pelo backend (RF-02) como toast de erro
     (`mostrarToast(extractErrorMessage(err, ...), 'error')`, mesmo padrão já usado).
3. `FechamentoCaixa.jsx` / `ResumoSessao.jsx`: nenhuma mudança de código — validar que os
   KPIs passam a mostrar valores reais assim que o backend enviar `resumo` (RF-03).

---

## Fora do Escopo

```
- Criação de model PontoDeVenda/Terminal separado de Conta — decisão já tomada
  (filtro por tipo=CAIXA) e já implementada no frontend; não revisitar.
- Rename de campos já em produção (valor_fechamento_calculado, operador,
  data_hora) para bater literalmente com a nomenclatura do pedido — mapeamento
  documentado acima, sem ganho em renomear.
- Qualquer mudança em Venda/ItemVenda/PagamentoVenda/RecebivelCartao — fora do
  escopo do pedido (que é sobre sessão de caixa, não sobre o fluxo de venda em si).
- Endpoint novo de listagem de usuários/operadores, se já existir algo
  equivalente reaproveitável no projeto.
```

---

## Critérios de Aceite (para o Sentinel)

```
CA-01 - POST /api/v1/pdv/sessoes/ com conta de tipo != CAIXA retorna 400 com
        mensagem legível (RF-01/RN-01)
CA-02 - Operador com sessão ABERTA na Conta A recebe 400 legível ao tentar
        abrir sessão na Conta B (RF-02/RN-02) — testado via API real
CA-03 - UniqueConstraint condicional por operador+ABERTA criada e migration
        aplicada sem erro (checar dados de produção antes, achado de risco)
CA-04 - GET /pdv/sessoes/atual/ com sessão ABERTA retorna campo resumo
        populado com por_metodo, vendas_dinheiro, sangrias, suprimentos e
        valor_calculado_dinheiro refletindo movimentos reais da sessão (RF-03)
CA-05 - Tela Fechar Caixa exibe KPIs de Total Vendas/Sangrias/Suprimentos com
        valores reais (não R$ 0,00) antes do fechamento
CA-06 - grep -in "valor_contagem_fisica" em RelatorioSessoesCaixa.jsx retorna
        vazio; coluna "Contagem" exibe valor real de sessões fechadas (RF-04)
CA-07 - Filtro de operador funcional em RelatorioSessoesCaixa.jsx — selecionar
        operador filtra a listagem via ?operador=<id> (RF-05)
CA-08 - Card de sessão já aberta (AberturaCaixa.jsx e FrenteDeCaixa.jsx)
        exibe conta e data/hora reais em ambiente de produção — testado
        ponta a ponta, não só lido no código (RF-06)
CA-09 - RN-03 e RN-04 (motivo obrigatório em sangria/suprimento; cálculo de
        fechamento sem bloqueio por diferença) continuam passando — sem
        regressão nos testes já existentes
CA-10 - Suite backend/pdv/tests.py 100% passando, incluindo os novos testes
        de RF-01/RF-02/RF-03
```

---

## Observações finais do Analista

- Este pedido chegou descrevendo o módulo como "parcialmente implementado", mas a
  leitura direta mostrou um módulo maduro (5 manutenções anteriores) com um conjunto de
  gaps mais estreito e mais preciso do que o relatado — dois dos "bugs" do pedido já
  estão corrigidos no código-fonte, e os gaps reais encontrados (validação de servidor
  ausente para regras já assumidas na UI, campo de resumo nunca implementado, um mismatch
  de nome de campo em tela diferente da citada) são mais úteis para o Forge/Loom do que
  o relato original.
- Não há lacuna a confirmar com o cliente antes de iniciar — RF-01 a RF-05 são
  acionáveis imediatamente. RF-06 depende de validação do Sentinel em ambiente real
  antes de fechar o ciclo, não de confirmação do cliente.
- Risco a não pular: aplicar a `UniqueConstraint` de RF-02 sem antes auditar dados de
  produção pode quebrar a migration ou, pior, mascarar uma violação já existente.

---

➡️ **Planner: rotear para Pipeline B (bug + validação de backend) — Forge (services.py,
models.py, serializers.py, tests.py) e Loom (RelatorioSessoesCaixa.jsx, AberturaCaixa.jsx)
em paralelo → Sentinel (validar CA-01 a CA-10, incluindo teste ponta a ponta do BUG 1
original) → Pilot.**
