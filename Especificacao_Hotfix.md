# Especificação — Manutenção #37
**Elaborado por:** Analista (MODO HOTFIX)
**Data:** 2026-08-17
**Sistema:** UidCore (OS #7)
**Solicitação original (verbatim):** "Produtos tanto Novo, quanto editar, Conversões de
unidade seja possível fazer mais de uma conversão, exemplo: 1cx = 6pt, e 6pt = 50un, pois
na entrada seja via manual ou nota fiscal vai ser CX e vendas pode ser tanto PT quanto UN."

**Instrução do Planner:** decompor em RF/RN/telas, verificar se já existe estrutura de
conversão de unidade antes de desenhar algo novo, e cobrir tanto a entrada (NF/manual)
quanto a venda com conversão automática de quantidade/preço.

---

## Classificação

```
tipo: feature_pequena (evolução de estrutura já existente, dentro do módulo produtos/pdv)
sistema: UidCore
caminho_afetado: backend/produtos/* (models, serializers, views)
                 backend/pdv/* (services, views)
                 frontend/src/pages/Produtos.jsx
                 frontend/src/pages/pdv/FrenteDeCaixa.jsx
                 frontend/src/pages/pdv/components/CarrinhoItem.jsx
complexidade: media
requer_aprovacao_comercial: false
```

---

## Diagnóstico confirmado (leitura direta dos arquivos — não do pedido)

O pedido presume que "fazer mais de uma conversão" não existe. **Não é bem assim.** Já
existe `produtos.models.ConversaoUnidade` (desde o desenho original do módulo) e o
formulário de Produto em `Produtos.jsx` já tem botão "Adicionar Conversão" permitindo N
linhas por produto. Ou seja: hoje já dá pra cadastrar CX **e** PT **e** UN no mesmo
produto. O problema real, encontrado lendo o código, é mais específico e mais grave do
que "falta permitir mais de uma":

### O que já existe e funciona
- `Produto.unidade_base` + `ConversaoUnidade(produto, unidade, quantidade_por_base)` —
  cada conversão já é relativa à unidade base do produto.
- `EntradaEstoque` já aceita `unidade` livre (inclusive CX) e já converte pra base no
  `save()` antes de somar no `Produto.quantidade_estoque`.
- `pdv/services.py` já espelha essa mesma conversão na baixa/reversão de estoque de uma
  venda (`_quantidade_base`, `_debitar_estoque`, `_reverter_estoque`).
- Múltiplas conversões por produto já são aceitas pelo backend (`unique_together` é só
  `(produto, unidade)`, não limita quantidade de unidades diferentes).

### O que NÃO existe / está quebrado (achados reais)

**ACHADO 1 — Cadeia não é suportada, só conversão direta pra base (o pedido literal).**
Hoje cada `ConversaoUnidade.quantidade_por_base` tem que ser o fator **já multiplicado**
até a unidade base. Pra reproduzir o exemplo do cliente (1 CX = 6 PT, 6 PT-ish = 50 UN),
o usuário precisa calcular `300` de cabeça e digitar direto em "Qtd por UN" pra CX — o
sistema não deixa ele digitar "1 CX = 6 PT" e "1 PT = X UN" separadamente e compor sozinho.
É exatamente o que o pedido descreve.

**ACHADO 2 — Editar/excluir conversão já salva não funciona pela tela, apesar do backend
já ter os endpoints prontos.** `ProdutoViewSet.conversao_detalhe` (PATCH/DELETE) já existe
em `backend/produtos/views.py`. Mas no frontend:
- `handleSubmit` em `Produtos.jsx` só faz `POST` de conversões **sem `id`** (linha 172:
  `if (!conv.id && conv.unidade && conv.quantidade_por_base)`). Editar o valor de uma
  conversão já salva e clicar em Salvar **não persiste nada**.
- `removeConversao` (linha 145) só tira a linha do estado local do React — nunca chama
  `DELETE /produtos/{id}/conversoes/{conv_id}/`. A conversão continua existindo no banco.

Isso bate direto com a primeira frase do pedido: **"Produtos tanto Novo, quanto editar"**
— editar já estava quebrado antes mesmo de pensar em cadeia.

**ACHADO 3 — CRÍTICO: fallback silencioso 1:1 quando não há conversão cadastrada.**
`EntradaEstoque.save()` e `pdv/services.py._quantidade_base`/`_reverter_estoque` caem em
`except ConversaoUnidade.DoesNotExist: assume 1:1` sem avisar ninguém. Se o operador
lançar uma entrada de 1 CX num produto sem a conversão cadastrada, o sistema soma **1**
no estoque em vez de 300 — silenciosamente. Isso é mais perigoso do que a ausência de
cadeia; precisa virar erro 400 explícito (ver RN-05).

**ACHADO 4 — CRÍTICO: preço de venda não é convertido por unidade.** Em
`backend/pdv/views.py::adicionar_item` (linha 266):
```python
valor_unitario=produto.preco_venda,  # RN-03: snapshot
```
`valor_unitario` é sempre `produto.preco_venda` cru, **independente da `unidade`
enviada**. Como `preco_venda` é definido por unidade base (ex. preço por UN), vender "1
CX" hoje cobraria o preço de **1 UN** por uma caixa inteira. É o motivo pelo qual, mesmo
que o item tivesse um seletor de unidade, vender em PT/CX estaria quebrado hoje.

**ACHADO 5 — PDV nunca deixa escolher a unidade na venda.** Em
`FrenteDeCaixa.jsx::adicionarProduto` a unidade enviada é sempre fixa:
```js
unidade: produto.unidade_base || 'UN',
```
Não existe seletor de unidade no carrinho. `ItemVenda.unidade` (backend) já aceita
qualquer unidade — só o frontend nunca oferece escolha. É o motivo técnico central do
pedido ("vendas pode ser tanto PT quanto UN").

**ACHADO 6 — bug cosmético já existente, some junto.** `CarrinhoItem.jsx` lê
`item.produto_unidade`, um campo que **não existe** no serializer (`ItemVendaSerializer`
retorna `unidade`, não `produto_unidade`). Hoje passa despercebido porque a unidade é
sempre UN; ao habilitar seleção de unidade (ACHADO 5) isso ficaria visivelmente errado
(carrinho sempre mostrando "UN" mesmo vendendo em CX).

**Conclusão:** a infraestrutura de conversão de unidade já existe e já é usada de verdade
em estoque (entrada e baixa por venda). O pedido do cliente é real, mas o gap não é "criar
do zero" — é (a) permitir cadastrar a conversão em cadeia em vez de forçar cálculo manual,
(b) destravar edição/exclusão que já deveria funcionar, (c) corrigir dois bugs que
inviabilizam vender em unidade diferente da base (preço errado + sem seletor), e (d)
fechar um fallback silencioso perigoso no cálculo de estoque.

---

## Requisitos Funcionais (RF)

```
RF-01 (Must) - Produto (Novo/Editar): permitir cadastrar uma conversão de unidade
        relativa a QUALQUER unidade já definida no produto (base ou intermediária),
        não só direto à unidade base — cobre o exemplo literal do pedido
        (1 CX = 6 PT, 1 PT = 50 UN).
RF-02 (Must) - Corrigir edição de conversão já salva: alterar o valor de uma conversão
        existente e salvar deve persistir via PATCH real no backend (ACHADO 2).
RF-03 (Must) - Corrigir exclusão de conversão já salva: remover uma linha da lista deve
        chamar DELETE real no backend, não só sumir da tela (ACHADO 2).
RF-04 (Should) - Exibir, ao lado de cada conversão cadastrada em cadeia, o fator composto
        equivalente à unidade base (ex.: "1 CX = 6 PT = 300 UN") para conferência antes
        de salvar.
RF-05 (Must) - PDV (Frente de Caixa): permitir escolher a unidade de venda do item
        (unidade base OU qualquer unidade com conversão cadastrada para o produto),
        em vez de travar sempre em `unidade_base` (ACHADO 5).
RF-06 (Must) - Corrigir `valor_unitario` do item vendido em unidade diferente da base:
        calcular automaticamente a partir de `preco_venda` × fator de conversão da
        unidade escolhida (ACHADO 4) — é o "conversão automática de quantidade/preço"
        citado na instrução do Planner.
RF-07 (Must) - Corrigir exibição da unidade real no carrinho (`CarrinhoItem.jsx`
        usa prop inexistente `produto_unidade`) (ACHADO 6).
RF-08 (Should) - Entrada de Estoque (manual, com ou sem número de NF já suportado pelo
        campo `nota_fiscal`): mostrar preview da quantidade equivalente em unidade base
        (ex. "= 300 UN") antes de confirmar, quando a unidade escolhida ≠ unidade base.
RF-09 (Could) - Preço de venda específico por unidade (override manual, para casos em
        que o preço não é estritamente proporcional — ex. desconto por caixa fechada).
        Fora do MVP desta manutenção, registrado como sugestão futura.
```

---

## Regras de Negócio (RN)

```
RN-01 - Toda ConversaoUnidade deve, direta ou indiretamente (em cadeia), terminar na
        unidade_base do produto. Cadeia que não termina na base, ou que forma ciclo
        (A→B, B→A), é inválida e deve ser rejeitada com erro 400 legível. Cobre RF-01.
RN-02 - Uma unidade só pode ter UMA conversão definida por produto — mantém a
        constraint já existente `unique_together (produto, unidade)`. Evita
        ambiguidade (ex. CX não pode valer "6 PT" e "300 UN direto" ao mesmo tempo).
RN-03 - Profundidade máxima de cadeia: 5 elos. Proteção técnica contra configuração
        cíclica ou erro de cadastro, não é requisito do cliente.
RN-04 - valor_unitario de ItemVenda continua sendo SEMPRE calculado/definido pelo
        backend, nunca aceito do payload (regra já existente do módulo, preservada) —
        agora calculado como preco_venda × fator_de_conversão(unidade) quando
        unidade ≠ unidade_base. Cobre RF-06.
RN-05 (ACHADO CRÍTICO) - Se o produto não tiver conversão cadastrada (direta ou em
        cadeia) para a unidade informada numa entrada de estoque ou item de venda, o
        sistema NÃO pode mais assumir silenciosamente fator 1:1 — deve rejeitar com
        erro 400 legível ("Conversão de unidade não cadastrada para X"). O
        comportamento atual (fallback mudo) é o risco mais grave encontrado nesta
        análise: uma entrada de 1 CX sem conversão cadastrada soma 1 no estoque em vez
        do valor real.
RN-06 - Excluir ou editar uma conversão que é elo intermediário de outra (ex.: excluir
        PT quando CX está definida "1 CX = 6 PT") deve ser bloqueada com mensagem
        clara listando quem depende dela — nunca deixar uma cadeia quebrada em
        silêncio.
```

---

## Telas afetadas (detalhamento)

### Tela: Produtos — Novo/Editar (`Produtos.jsx`, seção "Conversões de Unidade")
- Trocar o campo único "Qtd por {unidade_base}" por: Select "Unidade" (já existe) +
  novo Select "Converte para" (opções: unidade base do produto + demais unidades já
  adicionadas na lista, exceto a própria linha; default = unidade base) + Input
  "Quantidade" (já existe, reaproveitar).
- Ao montar o payload de cada linha pro backend: enviar `{unidade, converte_para,
  quantidade_por_base}` — `converte_para` omitido/vazio quando a referência é a
  unidade base (mantém compatibilidade com o que já existe).
- RF-04: exibir ao lado de cada linha o fator composto até a base (calculado no
  cliente replicando a mesma lógica de resolução em cadeia do backend — só para
  conferência visual, backend continua sendo a fonte de verdade).
- RF-02/RF-03: `handleSubmit` passa a fazer `PATCH /produtos/{id}/conversoes/{id}/`
  para linhas com `id` cujo valor mudou, e `removeConversao` passa a chamar
  `DELETE /produtos/{id}/conversoes/{id}/` de verdade quando a linha já existe no
  backend (hoje só mexe em estado local do React).

### Tela: Produtos — Entrada de Estoque (dentro do modal de edição, `Produtos.jsx`)
- RF-08: ao escolher unidade diferente da base no formulário de nova entrada, exibir
  preview "= X {unidade_base}" ao lado do campo quantidade.

### Tela: PDV — Frente de Caixa (`FrenteDeCaixa.jsx`)
- RF-05: `adicionarProduto` deixa de forçar `unidade: produto.unidade_base`. Se o
  produto tiver conversões cadastradas, oferecer escolha de unidade (dropdown rápido
  ou passo extra leve) antes de confirmar a adição ao carrinho; produto sem conversão
  cadastrada mantém o fluxo atual (adiciona direto na unidade base, sem fricção extra).

### Componente: Carrinho (`components/CarrinhoItem.jsx`)
- RF-07: trocar as duas ocorrências de `item.produto_unidade` (prop que não existe)
  por `item.unidade` (campo real devolvido pela API).

---

## Especificação técnica — Backend (Forge)

1. `backend/produtos/models.py`:
   - `ConversaoUnidade`: adicionar campo `converte_para = models.CharField(max_length=2,
     choices=UnidadeBase.choices, null=True, blank=True)` — quando vazio, significa
     "relativo à unidade_base do produto" (mesmo comportamento de hoje, 100%
     retrocompatível: todas as linhas existentes continuam com `converte_para=NULL` e
     seguem funcionando sem qualquer migração de dado). `quantidade_por_base` passa a
     significar "quantos de `converte_para` (ou da base, se vazio) equivalem a 1 desta
     unidade" — nome do campo mantido para não quebrar consumidores existentes.
   - Migration: apenas 1 coluna nova nullable. **Sem necessidade de data migration** —
     ponto que reduz bastante o risco desta manutenção comparado a uma reescrita de
     schema.
   - Criar `produtos/services.py` (novo arquivo) com `fator_para_base(produto, unidade)`
     — resolve recursivamente a cadeia (máx. 5 saltos, RN-03), detecta ciclo, levanta
     `django.core.exceptions.ValidationError` legível se a unidade não tiver conversão
     cadastrada (RN-05) ou se a cadeia não terminar na base (RN-01). Esta função
     substitui a lógica hoje **triplicada** em `EntradaEstoque.save()`,
     `pdv/services.py._quantidade_base` e `pdv/services.py._reverter_estoque` — os
     três pontos devem passar a chamá-la em vez de repetir
     `ConversaoUnidade.objects.get(...)` cada um com seu próprio fallback 1:1 (achado
     de duplicação de código independente do pedido, mas que esta manutenção já
     resolve de graça ao consolidar a função).
2. `backend/produtos/models.py::EntradaEstoque.save()`: usar `fator_para_base`; deixar
   de silenciar `ConversaoUnidade.DoesNotExist` (RN-05) — erro deve subir até a view
   pra virar 400.
3. `backend/pdv/services.py::_quantidade_base` / `_reverter_estoque`: idem, delegar
   para `fator_para_base` compartilhado.
4. `backend/pdv/views.py::adicionar_item`: calcular
   `valor_unitario = produto.preco_venda * fator_para_base(produto, unidade)` quando
   `unidade != produto.unidade_base`, senão manter `produto.preco_venda` (RF-06/RN-04).
   Capturar `ValidationError` de `fator_para_base` e devolver 400 legível (RN-05).
5. `backend/produtos/serializers.py::ConversaoUnidadeSerializer`: adicionar
   `converte_para` + `converte_para_display` (`SerializerMethodField` ou
   `get_converte_para_display`); `validate()` chama a mesma resolução de cadeia
   considerando as conversões já existentes do produto (RN-01/RN-03) — rejeitar antes
   de salvar, não só no uso posterior.
6. `backend/produtos/views.py`: endpoints de conversão (`conversoes` GET/POST e
   `conversao_detalhe` PATCH/DELETE) já existem e já cobrem edição/exclusão — nenhuma
   rota nova. Adicionar checagem em `conversao_detalhe` (PATCH e DELETE) que bloqueia
   a operação se outra `ConversaoUnidade` ativa do mesmo produto tiver
   `converte_para == unidade` desta linha, retornando 400 com a lista de quem depende
   dela (RN-06).
7. Testes (`backend/produtos/tests.py`, `backend/pdv/tests.py`):
   - Cadeia de 2 elos (CX→PT, PT→UN) resolvendo corretamente para a base.
   - Ciclo (A→B, B→A) rejeitado com 400.
   - Cadeia que não termina na base rejeitada com 400.
   - Unidade sem conversão cadastrada agora retorna 400 em `EntradaEstoque` e em
     `adicionar_item` do PDV (RN-05) — teste explícito de que o fallback 1:1 mudo foi
     removido.
   - `valor_unitario` correto ao vender em unidade não-base (RF-06).
   - Baixa/reversão de estoque correta vendendo em unidade intermediária da cadeia.
   - Exclusão/edição de conversão usada como elo por outra é bloqueada (RN-06).
   - Regressão: os testes já existentes de `EntradaEstoque` e baixa de estoque do PDV
     continuam passando com a nova função compartilhada.

## Especificação técnica — Frontend (Loom)

1. `frontend/src/pages/Produtos.jsx`:
   - Seção Conversões: adicionar `Select` "Converte para" por linha; opções dinâmicas
     = `[unidade_base do form, ...conversoes.map(c => c.unidade).filter(u => u !==
     linha atual)]`.
   - `EMPTY_CONVERSAO` ganha `converte_para: ''`.
   - `handleSubmit`: além do `POST` já existente para linhas sem `id`, adicionar
     `PATCH /produtos/{id}/conversoes/{conv.id}/` para linhas com `id` que mudaram
     (comparar contra snapshot carregado) (RF-02).
   - `removeConversao`: se a linha tiver `id`, chamar
     `DELETE /produtos/{id}/conversoes/{id}/` antes de tirar do estado local; tratar
     erro 400 de RN-06 com toast explicando a dependência (RF-03).
   - RF-04: função local `resolverFatorBase(conversoes, unidadeBase, unidade)` —
     mesma lógica recursiva do backend, só para preview; não substitui validação do
     servidor.
   - RF-08: preview "= X {unidade_base}" no formulário de nova entrada usando a mesma
     função.
2. `frontend/src/pages/pdv/FrenteDeCaixa.jsx`:
   - `adicionarProduto`: se `produto.conversoes?.length` (já vem no payload do
     `ProdutoSerializer` — campo `conversoes` já existe, nested, confirmado em
     `produtos/serializers.py`), oferecer seletor de unidade (base + unidades com
     conversão) antes do POST; produto sem conversão mantém comportamento atual.
   - Repassar a unidade escolhida em `unidade` no `POST /pdv/vendas/{id}/itens/`.
3. `frontend/src/pages/pdv/components/CarrinhoItem.jsx`: trocar as 2 ocorrências de
   `item.produto_unidade` por `item.unidade` (RF-07).

---

## Fora do Escopo

```
- frontend/src/pages/Vendas.jsx (Orçamento/Pedido): ItemOrcamento e ItemPedido não têm
  campo `unidade` hoje e, por decisão de arquitetura já registrada (ADR-015), não
  fazem baixa de estoque — adicionar conversão de unidade nesse fluxo é uma feature
  nova e maior, de escopo próprio. O pedido fala em "entrada" (estoque) e "vendas" no
  sentido de venda de balcão (PDV), que é o par natural de "entrada de estoque" — mas
  se o cliente também quiser isso em Orçamento/Pedido, precisa de confirmação
  explícita antes de entrar em uma próxima rodada (não é ambiguidade que bloqueie
  esta manutenção, é escopo adicional).
- RF-09 (preço de venda específico por unidade, não-proporcional) — sugestão futura,
  não faz parte deste MVP.
- Importação automática de XML de NF-e — não existe hoje no sistema. "Entrada via nota
  fiscal" continua sendo lançamento manual referenciando o número da NF (campo
  `nota_fiscal` de `EntradaEstoque`, já existente) — nenhuma mudança nesta manutenção.
- Qualquer mudança em PagamentoVenda, RecebivelCartao, SessaoCaixa — módulos tratados
  na Manutenção #36, sem relação com este pedido.
```

---

## Critérios de Aceite (para o Sentinel)

```
CA-01 - Cadastrar produto com unidade_base=UN e duas conversões em cadeia
        (1 CX = 6 PT; 1 PT = 50 UN) sem precisar digitar o fator composto (300) na
        mão — testado via formulário/API real (RF-01).
CA-02 - Editar o valor de uma conversão já salva e confirmar reflete via PATCH real
        no backend, visível após reload da página (RF-02).
CA-03 - Remover uma conversão já salva chama DELETE real; ela não reaparece após
        reload (RF-03).
CA-04 - Cadeia circular (A→B, B→A) rejeitada com 400 legível (RN-01).
CA-05 - Cadeia que não termina na unidade_base rejeitada com 400 legível (RN-01).
CA-06 - Entrada de estoque ou item de venda em unidade sem conversão cadastrada
        retorna 400 legível — não soma/debita mais estoque com fallback 1:1 mudo
        (RN-05, achado crítico desta análise).
CA-07 - PDV: vender 1 PT de um produto com cadeia CX→PT→UN debita a quantidade
        correta em UN do estoque (via resolução de cadeia, não só conversão direta).
CA-08 - PDV: valor_unitario do item vendido em PT/CX é calculado automaticamente a
        partir de preco_venda × fator de conversão — não é mais o preco_venda cru
        (RF-06).
CA-09 - Carrinho do PDV exibe a unidade real vendida (ex. "PT"), não sempre "UN"
        fixo (RF-07).
CA-10 - Excluir/editar uma conversão usada como elo intermediário por outra é
        bloqueado com mensagem clara (RN-06).
CA-11 - Suite backend/produtos/tests.py e backend/pdv/tests.py 100% passando,
        incluindo os novos testes de cadeia/ciclo/erro 400 — 0 falhas, sem @skip.
CA-12 - npm run build limpo, 0 erros.
```

---

## Observações finais do Analista

- O pedido presumia ausência total de estrutura de conversão de unidade; a leitura
  direta do código mostrou o oposto — a estrutura já existe e já é usada de verdade em
  `EntradaEstoque` e na baixa de estoque do PDV. O trabalho real não é "criar do zero",
  é evoluir de fator-direto-à-base para cadeia, destravar edição/exclusão que já
  deveriam funcionar, e corrigir dois bugs (preço não convertido, seletor de unidade
  ausente no PDV) que hoje inviabilizam a segunda metade do pedido ("vendas pode ser
  tanto PT quanto UN").
- O achado mais grave (RN-05, ACHADO 3) não veio do pedido do cliente — é um
  comportamento silencioso já em produção (fallback 1:1 quando falta conversão
  cadastrada) que pode estar mascarando erro de estoque hoje, em qualquer produto que
  já tenha entrada/venda em unidade sem `ConversaoUnidade` correspondente. Recomendo
  ao Sentinel, antes do deploy, uma consulta rápida em produção
  (`EntradaEstoque.objects.exclude(unidade=F('produto__unidade_base'))` cruzado com
  produtos sem `ConversaoUnidade` correspondente) para medir se já existe dado
  histórico afetado — não bloqueia esta manutenção, mas é um risco operacional real
  que vale reportar a Luiz Eduardo separadamente se aparecer.
- O exemplo numérico do próprio cliente ("1cx = 6pt, e 6pt = 50un") é literalmente
  ambíguo — "6pt = 50un" não é múltiplo redondo de "1pt = X un", o que sugere ou um
  erro de digitação (provavelmente queria dizer "1 pt = 50 un") ou um caso legítimo de
  conversão não-proporcional. O desenho desta especificação (campo quantidade livre,
  não travado em múltiplos inteiros) suporta ambas as leituras sem precisar confirmar
  com o cliente antes de iniciar — não é uma lacuna bloqueante.
- Não há lacuna que exija pausar o pipeline: RF-01 a RF-08 são acionáveis
  imediatamente com o que já foi lido no código. RF-09 e a extensão para
  Orçamento/Pedido ficam registrados como possível próxima rodada, não como pendência
  desta.

---

➡️ **Planner: rotear para Pipeline C (feature pequena sobre módulo existente) — Forge
(produtos/models.py, produtos/services.py novo, produtos/serializers.py,
produtos/views.py, pdv/services.py, pdv/views.py, testes) e Loom (Produtos.jsx,
pdv/FrenteDeCaixa.jsx, pdv/components/CarrinhoItem.jsx) em paralelo → Sentinel (validar
CA-01 a CA-12, com atenção especial a CA-06/RN-05 por ser o achado de maior risco) →
Pilot.**
