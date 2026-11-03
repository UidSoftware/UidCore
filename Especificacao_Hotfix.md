# Especificação — Manutenção #91

**Sistema:** UidCore (OS #7)
**Título:** Produtos: cadastrar também Serviço (botão "+ Novo Item")
**Origem:** replicado do fork LifeStyle (Manutenção #84, pedido do Luiz Eduardo, 29/10/2026) — implementado aqui de forma genérica, multi-nicho, sem nada específico de estúdio/pilates, para todo fork novo do UidCore já nascer com a funcionalidade.
**Autor:** Analista
**Data:** 2026-11-02

---

## 1. Contexto

O app `produtos` hoje só modela mercadoria física (`Produto` com estoque,
código de barras, unidade de medida). Vários nichos atendidos pela Uid
(estúdio, salão, clínica, prestador de serviço em geral) vendem **serviços**
junto com produtos — sessão, corte, consulta, aula — que não têm estoque,
não têm unidade de medida e não devem gerar `MovimentoEstoque`.

Decisão de modelagem: **Serviço não é um app novo, é um novo `tipo` dentro
do model `Produto`** existente, reaproveitando nome/preço/observações,
cadastro, listagem, PDV e Vendas (Orçamento/Pedido) já prontos — evita
duplicar CRUD, FK e telas inteiras só para trocar os campos exibidos.

## 2. AS-IS

- `Produto` (`backend/produtos/models.py`) é sempre mercadoria: tem
  `quantidade_estoque`, `estoque_minimo`, `unidade_base`, `codigo_barras`.
- `MovimentoEstoque.save()` sempre debita/credita `Produto.quantidade_estoque`
  via `F()` ao criar.
- PDV (`backend/pdv/services.py::finalizar_venda`) sempre valida estoque de
  TODOS os itens (RF-07 original) e debita estoque de todos ao finalizar;
  `cancelar_venda`/`devolver_item` sempre revertem estoque.
- `vendas.ItemPedido`/`vendas.ItemOrcamento` já têm `produto` nullable e
  **nunca** baixam estoque (ADR-015: módulo B2B sem baixa de estoque) — não
  precisam de ajuste de estoque, só precisam continuar aceitando produto ou
  serviço sem diferença de tratamento.
- Frontend `Produtos.jsx`: botão "+ Novo Produto", 1 form único sempre com
  campos de produto físico; listagem em cards/tabela sempre mostrando coluna
  Estoque.

## 3. TO-BE

- `Produto.tipo` (choices `PRODUTO` | `SERVICO`, default `PRODUTO`).
- Botão "+ Novo Produto" → "+ Novo Item"; primeira escolha no form é o tipo;
  campos do form mudam conforme o tipo escolhido.
- Serviço: `nome`, `descricao` (reaproveita `observacoes`), `preco_venda`,
  `duracao_minutos` (opcional), `categoria_financeira_entrada` (opcional,
  FK para `financeiro.Categoria` tipo `ENTRADA`). Sem estoque, sem unidade,
  sem código de barras, sem custo (`valor_unitario`) — campos ficam
  ocultos/sem sentido para esse tipo (não removidos do model, só não usados).
- Serviço nunca aciona `MovimentoEstoque` nem entra em alerta de estoque
  mínimo; a regra "estoque só muda por movimento" (`CLAUDE.md` global,
  padrão Uid) permanece válida — simplesmente SERVICO nunca gera movimento.
- Listagem de Produtos com filtro/aba **Produtos | Serviços | Todos**.
- PDV e Vendas (Orçamento/Pedido) passam a poder vender/listar Serviço sem
  baixa de estoque.

## 4. Requisitos Funcionais

**RF-01** — `Produto` ganha campo `tipo` (choices `TipoProduto.PRODUTO` /
`TipoProduto.SERVICO`, default `PRODUTO`, `max_length=10`). Migration de
schema (`AddField`, default `PRODUTO`) garante que **todo registro
existente** vira `PRODUTO` automaticamente (default aplicado em massa pelo
Django na migration, sem precisar de `RunPython` — basta `default='PRODUTO'`
na definição do campo).

**RF-02** — Novos campos em `Produto`, usados somente quando `tipo=SERVICO`:
- `duracao_minutos` (`PositiveIntegerField`, `null=True, blank=True`) —
  duração padrão do serviço em minutos, opcional.
- `categoria_financeira_entrada` (`ForeignKey` para `financeiro.Categoria`,
  `null=True, blank=True, on_delete=models.SET_NULL`, `related_name='produtos_servico'`)
  — categoria de entrada (RECEITA) sugerida quando esse serviço é vendido;
  puramente informativo nesta manutenção (RN-07), sem efeito automático
  ainda na geração da Receita.

**RF-03** — Serializer `ProdutoSerializer` expõe `tipo` e os dois campos
novos. Campos que só fazem sentido para `PRODUTO` (`codigo_barras`,
`quantidade_estoque`, `estoque_minimo`, `unidade_base`, `valor_unitario`,
`estoque_inicial`, `nota_fiscal_inicial`) continuam existindo no payload mas
são ignorados/zerados quando `tipo=SERVICO` (RN-01).

**RF-04** — `ProdutoViewSet.get_queryset()` ganha filtro por `tipo` via
query param (`?tipo=PRODUTO` / `?tipo=SERVICO` — sem o param, retorna todos,
igual hoje). Implementado como `filterset_fields` simples ou leitura manual
de `request.query_params.get('tipo')` em `get_queryset()` — qualquer um dos
dois é aceitável, manter o padrão de código já usado no app (sem
`django-filter` configurado neste ViewSet hoje; decisão do Forge: filtro
manual por `request.query_params`, consistente com o restante do arquivo).

**RF-05** — `MovimentoEstoque` e o endpoint `produtos/{id}/movimentos/`
(`ProdutoViewSet.movimentos`) passam a bloquear criação de movimento para
produto com `tipo=SERVICO`: `POST .../movimentos/` em serviço retorna 400
(`{'tipo': ['Serviço não possui controle de estoque.']}`). A action
`conversoes` (`ConversaoUnidade`) do mesmo motivo é bloqueada para serviço
(400) — conversão de unidade não se aplica a quem não tem unidade.

**RF-06** — `ProdutoSerializer.create()` não cria `MovimentoEstoque`
(estoque inicial) quando `tipo=SERVICO`, mesmo que `estoque_inicial` venha
preenchido no payload por engano — campo é ignorado nesse caso (RN-02).

**RF-07** — PDV (`backend/pdv/services.py` e `views.py`):
- `ProdutoViewSet`/`AdicionarItemSerializer`/`adicionar_item` (ação
  `POST /pdv/vendas/{id}/itens/`) passam a aceitar produto com
  `tipo=SERVICO`. Para serviço: `unidade` do payload é ignorada (RN-04);
  `valor_unitario` do item é sempre `produto.preco_venda` direto (sem
  cálculo de fator de conversão); `ItemVenda.unidade` é gravado como
  `produto.unidade_base` (valor neutro, nunca usado para cálculo quando
  o item é de serviço — ver RN-05).
- `finalizar_venda`: a validação de estoque insuficiente (RF-07 original)
  e `_debitar_estoque` passam a **pular itens cujo `produto.tipo ==
  SERVICO`** — nenhuma linha de serviço entra no loop de checagem/débito.
- `cancelar_venda`: a reversão de estoque (`_reverter_estoque`) passa a
  **pular itens de serviço** — a reversão financeira (estorno de Receita)
  continua normal para todo item, produto ou serviço.
- `devolver_item`: devolução parcial de item de serviço continua permitida
  no aspecto financeiro (estorno proporcional de Receita), mas **nunca**
  chama `_reverter_estoque` quando `item.produto.tipo == SERVICO`.

**RF-08** — Vendas (Orçamento/Pedido): nenhuma mudança de lógica é
necessária em `backend/vendas/` — `ItemOrcamento.produto`/`ItemPedido.produto`
já são nullable e o app nunca baixa estoque (ADR-015). Confirmar apenas
(via teste) que criar item de Orçamento/Pedido com produto `tipo=SERVICO`
funciona sem erro e sem qualquer `MovimentoEstoque` criado.

**RF-09** — Frontend `Produtos.jsx`:
- Botão "+ Novo Produto" renomeado para "+ Novo Item".
- Modal do form: primeiro campo é um seletor **Produto | Serviço** (ex.:
  dois botões/tabs no topo do modal, ou `Select`). A escolha reconfigura os
  campos exibidos abaixo:
  - **Produto** (como hoje): nome, código de barras, unidade base, estoque
    inicial, estoque mínimo, custo (valor_unitario), preço de venda,
    observações, seção de conversões de unidade, seção "Movimentar
    Estoque".
  - **Serviço**: nome, descrição (reaproveita o campo `observacoes`),
    preço de venda, duração em minutos (opcional), categoria financeira de
    entrada (select opcional, populado via `GET /api/v1/financeiro/categorias/?tipo=ENTRADA`).
    Sem código de barras, sem estoque, sem unidade, sem custo, sem seção de
    conversões, sem seção "Movimentar Estoque".
  - Ao editar um item existente, o seletor de tipo fica **desabilitado**
    (RN-06) — trocar PRODUTO↔SERVICO depois de criado não é suportado
    nesta manutenção (mudaria o significado de estoque/histórico já
    existente).

**RF-10** — Listagem de Produtos ganha abas/filtro **Produtos | Serviços |
Todos** acima da tabela/lista de cards — equivalente a um `Tabs`/segmented
control simples que ajusta o parâmetro `?tipo=` da chamada
`GET /api/v1/produtos/`. "Todos" é o padrão ao abrir a tela (comportamento
atual preservado). Card/linha de Serviço na listagem não mostra a coluna
"Estoque" (mostra "—" ou oculta a célula); mostra um badge "Serviço"
diferenciando visualmente de "Produto".

**RF-11** — PDV (`FrenteDeCaixa.jsx`/componente de busca de produto) e
Vendas (`BuscaProdutoRapida`/`ProdutoAutocomplete` em `Vendas.jsx`) passam a
listar também Serviço nos resultados de busca (sem filtrar por tipo —
busca já reaproveita `GET /api/v1/produtos/?search=`). Resultado de busca
mostra um badge "Serviço" para diferenciar. Ao adicionar um item de
serviço ao carrinho/orçamento/pedido, a UI não pede/mostra campo de
unidade (campo é ocultado quando o produto escolhido é `tipo=SERVICO`) e
nunca exibe badge de "Sem estoque" (esse badge é exclusivo de produto com
`quantidade_estoque <= 0`, nunca se aplica a serviço).

## 5. Requisitos Não Funcionais

**RNF-01** — Migration de `tipo` não pode quebrar nenhum registro
existente: todo `Produto` já cadastrado deve continuar com
`quantidade_estoque`/`unidade_base`/etc. intactos e virar `tipo=PRODUTO`
automaticamente, sem exigir `RunPython` nem intervenção manual.

**RNF-02** — Nenhuma migration de dado (RunPython) é necessária nesta
manutenção — só `AddField` com `default` resolve o backfill (confirmar no
teste do Sentinel que 0 registros ficam com `tipo` nulo/vazio).

**RNF-03** — Zero regressão nos testes existentes de PDV, Produtos e
Vendas (toda a suíte Django precisa continuar passando, incluindo os
testes de estoque negativo, cadeia de conversão de unidade e split de
pagamento — nenhum desses fluxos deve mudar de comportamento para
`tipo=PRODUTO`).

## 6. Atores e Perfis

Sem mudança de RBAC — mesmas permissões já existentes em `ProdutoViewSet`
(`AuditMixin` + permissão padrão do projeto) valem igual para Produto e
Serviço. Nenhum perfil novo.

## 7. Regras de Negócio

**RN-01** — Campos de estoque/unidade/custo/código de barras só têm
significado para `tipo=PRODUTO`. Para `tipo=SERVICO`, o backend sempre
ignora/zera esses campos no `create`/`update`, independentemente do que o
payload envie (nunca confiar em validação só no frontend).

**RN-02** — `estoque_inicial`/`nota_fiscal_inicial` (campos write-only do
`ProdutoSerializer`) são ignorados quando `tipo=SERVICO` — nenhum
`MovimentoEstoque` é criado nesse caso, mesmo se o valor vier preenchido.

**RN-03** — Estoque só muda por `MovimentoEstoque` (regra já existente,
preservada) — para Serviço, nenhum caminho do sistema pode criar
`MovimentoEstoque`: nem cadastro, nem PDV, nem Vendas.

**RN-04** — No PDV, ao adicionar item de Serviço ao carrinho, a conversão
de unidade (`fator_para_base`) nunca é chamada — `valor_unitario` do item é
sempre `produto.preco_venda` direto, sem multiplicar por fator nenhum.

**RN-05** — `ItemVenda.unidade` continua sendo um campo obrigatório do
model (NOT NULL) por motivo de schema compartilhado com `ItemVenda` de
produto — para serviço, grava-se `produto.unidade_base` (valor default
`UN`, nunca exibido/usado para cálculo). Essa gravação é só para satisfazer
a constraint do banco, nunca tem efeito de conversão/estoque para serviço.

**RN-06** — `tipo` de um `Produto` já criado não pode ser alterado via
`PATCH`/`PUT` — frontend desabilita o seletor na edição; backend marca
`tipo` como campo que, se vier diferente do valor atual num `update`, é
ignorado silenciosamente (mesmo padrão já usado para outros campos
protegidos no projeto — ex.: `is_staff` no serializer de usuário) **ou**
retorna 400 explícito. Decisão do Forge: usar o padrão já predominante no
código (campo fica fora de `fields` editáveis nesse contexto / ignorado no
`update()`), documentando a escolha no código.

**RN-07** — `categoria_financeira_entrada` é apenas sugestão/metadado
nesta manutenção — **não** altera automaticamente a criação de `Receita`
no PDV/Vendas (fora de escopo; é preparação para uma manutenção futura que
use essa categoria na hora de lançar a Receita da venda do serviço).

**RN-08** — Serviço nunca aparece em: seção "Movimentar Estoque" do modal
de edição, action `conversoes` (`ConversaoUnidade`), alerta/relatório de
estoque mínimo (se existir hoje em Dashboard — conferir e excluir
`tipo=SERVICO` do cálculo, caso exista).

## 8. Fora do Escopo

- Geração automática de Receita financeira usando
  `categoria_financeira_entrada` ao vender um serviço (RN-07) — fica para
  manutenção futura.
- Conversão de um `Produto` existente em `Serviço` (ou vice-versa) depois
  de criado (RN-06) — bloqueado nesta manutenção.
- Qualquer regra específica de nicho (ex.: duração vinculada a agenda/
  profissional do módulo `agendamento`) — a duração cadastrada aqui é só um
  campo informativo, sem integração com `agendamento.Compromisso` nesta
  manutenção.
- Combos (`Combo`/`ItemCombo`) contendo Serviço — não testado nem vedado
  explicitamente; comportamento herdado (FK para `Produto` aceita
  qualquer `tipo`), sem tratamento especial. Se o Sentinel encontrar
  problema real nesse cruzamento, reportar como achado, não bloquear a
  manutenção por isso (fora do pedido original).

## 9. Riscos e Dependências

- Depende do app `financeiro` já ter `Categoria` com `tipo=ENTRADA`
  (existe desde a Manutenção #88) — sem risco, já em produção.
- Risco de regressão: qualquer lugar do código que itere
  `Produto.objects.all()` assumindo implicitamente "é sempre mercadoria
  com estoque" (ex.: relatório de estoque baixo no Dashboard financeiro,
  export de catálogo) precisa ser auditado pelo Forge/Loom e, se existir,
  filtrar por `tipo=PRODUTO` antes de aplicar lógica de estoque. Grep
  recomendado: `quantidade_estoque`, `estoque_minimo`, `unidade_base` fora
  de `produtos/` e `pdv/`.
- Risco de UX: usuários já acostumados com "+ Novo Produto" — o rename
  para "+ Novo Item" é intencional (pedido explícito), mas vale confirmar
  que nenhum texto de ajuda/tooltip ficou órfão mencionando "produto"
  onde agora pode ser serviço.

---

## Spec Backend (Forge)

### `backend/produtos/models.py`

```python
class TipoProduto(models.TextChoices):
    PRODUTO = 'PRODUTO', 'Produto'
    SERVICO = 'SERVICO', 'Serviço'


class Produto(BaseModel):
    tipo = models.CharField(
        'tipo', max_length=10,
        choices=TipoProduto.choices, default=TipoProduto.PRODUTO,
    )
    nome = models.CharField('nome', max_length=200)
    codigo_barras = models.CharField('código de barras', max_length=50, blank=True, default='')
    quantidade_estoque = models.DecimalField(..., default=0)   # inalterado
    estoque_minimo = models.DecimalField(..., default=0)        # inalterado
    unidade_base = models.CharField(..., default=UnidadeBase.UN) # inalterado
    valor_unitario = models.DecimalField(..., default=0)        # inalterado
    preco_venda = models.DecimalField(..., default=0)           # inalterado
    observacoes = models.TextField(blank=True, default='')      # reaproveitado como "descrição" do serviço
    duracao_minutos = models.PositiveIntegerField(
        'duração (minutos)', null=True, blank=True,
    )
    categoria_financeira_entrada = models.ForeignKey(
        'financeiro.Categoria', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='produtos_servico',
    )
    ...
```

Migration: `0008_produto_tipo_servico.py` — `AddField tipo` (default
`PRODUTO`), `AddField duracao_minutos`, `AddField
categoria_financeira_entrada`. Sem `RunPython` (RNF-02).

### `backend/produtos/serializers.py` (`ProdutoSerializer`)

- Adicionar `tipo`, `tipo_display` (`SerializerMethodField`/
  `get_tipo_display`), `duracao_minutos`, `categoria_financeira_entrada`,
  `categoria_financeira_entrada_nome` (read-only) aos `fields`.
- `validate()` (novo): se `tipo == SERVICO`, força em `attrs`
  `quantidade_estoque`/`estoque_minimo` para não aceitar valor diferente de
  0 silenciosamente adulterado — na prática, como esses campos já são
  `read_only_fields`/calculados, o ponto real de ignorar é em
  `estoque_inicial`/`nota_fiscal_inicial` dentro de `create()` (ver abaixo).
  Para `codigo_barras`/`unidade_base`/`valor_unitario`, aceitar o que vier
  (não é crítico zerar — são campos inofensivos sem lógica de negócio
  acoplada, mas o Brush/Loom não deve exibi-los no form de Serviço, RN-01).
- `create()`: só cria `MovimentoEstoque` de `estoque_inicial` quando
  `validated_data.get('tipo', TipoProduto.PRODUTO) == TipoProduto.PRODUTO`
  (RN-02).
- `update()` (se não existir sobrescrito hoje — confirmar; se o
  `ModelViewSet` usa o `update()` padrão do `ModelSerializer`, adicionar um
  `update()` customizado só para aplicar RN-06: remover `tipo` de
  `validated_data` antes de salvar, sempre que `self.instance` já existir
  — ou seja, `tipo` só é gravável no `create`).

### `backend/produtos/views.py` (`ProdutoViewSet`)

- `get_queryset()`: ler `tipo = self.request.query_params.get('tipo')`; se
  presente e válido (`PRODUTO`/`SERVICO`), aplicar `.filter(tipo=tipo)`
  além do `is_active=True` já existente.
- `movimentos()` (action): no início, após `produto = self.get_object()`,
  checar `if produto.tipo == TipoProduto.SERVICO: return Response({'tipo':
  ['Serviço não possui controle de estoque.']}, status=400)` — bloqueia
  tanto `GET` (histórico, sempre vazio para serviço — retornar lista vazia
  é aceitável também, mas 400 deixa explícito; decisão do Forge entre as
  duas, documentar a escolhida) quanto `POST`.
- `conversoes()` (action): mesma checagem — serviço não tem
  `unidade_base` relevante para conversão; bloquear com 400 análogo.

### `backend/pdv/views.py` (`adicionar_item`)

Após obter `produto`:
```python
if produto.tipo == TipoProduto.SERVICO:
    valor_unitario = produto.preco_venda
    unidade = produto.unidade_base  # RN-05: valor neutro, sem efeito
else:
    unidade = d['unidade']
    if unidade not in UnidadeBase.values:
        ...
    if unidade == produto.unidade_base:
        valor_unitario = produto.preco_venda
    else:
        ... fator_para_base ...
```

### `backend/pdv/services.py`

- `_debitar_estoque(item)` e `_reverter_estoque(item, quantidade)`: no
  início de cada função, `if item.produto.tipo == TipoProduto.SERVICO:
  return` (no-op para serviço).
- `finalizar_venda()`: no loop de validação de estoque insuficiente
  (`itens_sem_estoque`), pular item quando `item.produto.tipo ==
  TipoProduto.SERVICO` (não entra na checagem, nunca pode ficar
  "sem estoque"). O loop de débito já fica correto automaticamente ao
  tornar `_debitar_estoque` um no-op para serviço — mas preferir o skip
  explícito também no loop de validação, para não gastar uma query de
  `select_for_update()` desnecessária por item de serviço (pequena
  otimização, não obrigatória).
- `cancelar_venda()`: o `_reverter_estoque` já vira no-op para serviço
  automaticamente — nenhuma mudança adicional necessária na função em si.
- `devolver_item()`: idem, `_reverter_estoque` já é no-op — o restante da
  função (estorno financeiro) continua rodando normalmente.

### `backend/vendas/` — sem alteração de código

Confirmar via teste (Sentinel) que criar `ItemOrcamento`/`ItemPedido` com
`produto.tipo=SERVICO` funciona sem erro (já é esperado, já que o app
nunca acessa `quantidade_estoque`/`unidade_base` em lugar nenhum do
`models.py`/`serializers.py`/`views.py` atual — confirmar com grep antes de
considerar RF-08 fechado).

### Testes obrigatórios (Sentinel)

- Criar Produto `tipo=PRODUTO` (comportamento legado intacto).
- Criar Produto `tipo=SERVICO` sem estoque → sucesso, `quantidade_estoque=0`,
  nenhum `MovimentoEstoque` criado.
- Criar Serviço com `estoque_inicial` preenchido no payload → ignorado,
  nenhum `MovimentoEstoque`.
- `POST .../movimentos/` em Serviço → 400.
- `POST .../conversoes/` em Serviço → 400.
- Migration aplicada sobre fixture com produtos pré-existentes → todos
  virando `tipo=PRODUTO`, zero null.
- PDV: adicionar item de Serviço ao carrinho → `ItemVenda` criado, sem
  checagem de unidade/fator.
- PDV: `finalizar_venda` com carrinho tendo 1 Produto + 1 Serviço → baixa
  de estoque só no Produto; Serviço não gera `MovimentoEstoque`; venda
  finaliza normalmente, Receita criada pelo valor total (produto+serviço).
- PDV: `finalizar_venda` só com Serviço, estoque do serviço "zero" (sem
  sentido) → nunca bloqueia por "estoque insuficiente".
- PDV: `cancelar_venda` de venda com Serviço → não tenta reverter estoque
  de serviço (sem erro, sem alterar `quantidade_estoque` de nada
  relacionado a ele).
- PDV: `devolver_item` de item de Serviço → estorno financeiro ocorre,
  sem chamada de reversão de estoque.
- Vendas: `ItemOrcamento`/`ItemPedido` com produto Serviço → sucesso, 0
  `MovimentoEstoque` relacionado.
- Tentar alterar `tipo` de um Produto existente via `PATCH` → valor
  permanece o original (RN-06).
- `GET /api/v1/produtos/?tipo=SERVICO` / `?tipo=PRODUTO` → cada filtro
  retorna só o subconjunto correto; sem o param, retorna todos (0
  regressão).

---

## Spec Frontend (Loom)

### `frontend/src/pages/Produtos.jsx`

- `TIPO_OPTIONS = [{value:'PRODUTO', label:'Produto'}, {value:'SERVICO', label:'Serviço'}]`.
- `EMPTY_FORM` ganha `tipo: 'PRODUTO'`, `duracao_minutos: ''`,
  `categoria_financeira_entrada: ''`.
- Botão do header: `+ Novo Produto` → `+ Novo Item`.
- Modal (`title={editingId ? 'Editar Item' : 'Novo Item'}`): logo abaixo do
  título, seletor de tipo (dois botões estilo toggle, ou `Select`
  `TIPO_OPTIONS`) — `disabled` quando `editingId` existe (RN-06).
- Renderização condicional dos campos do form conforme `form.tipo`:
  - `PRODUTO`: bloco atual inteiro (código de barras, unidade base,
    estoque inicial/mínimo, custo, preço de venda, observações, seção
    conversões, seção "Movimentar Estoque") — sem mudança de layout.
  - `SERVICO`: nome, descrição (reaproveita input de `observacoes`, label
    "Descrição"), preço de venda, duração em minutos (`Input type=number`,
    opcional), categoria financeira de entrada (`Select` populado via
    `GET /api/v1/financeiro/categorias/?tipo=ENTRADA`, opcional). Nenhuma
    seção de conversões nem "Movimentar Estoque" aparece.
- `handleSubmit`: ao montar o payload, se `form.tipo === 'SERVICO'`, não
  enviar `codigo_barras`/`unidade_base`/`estoque_inicial`/
  `nota_fiscal_inicial`/`estoque_minimo`/`valor_unitario` (ou enviar
  vazios/zero — backend já ignora, mas evitar poluir o payload é mais
  limpo); enviar `duracao_minutos`/`categoria_financeira_entrada` só
  quando preenchidos.
- Listagem: novo controle de abas/filtro acima da tabela —
  `['Todos', 'Produtos', 'Serviços']` — ao trocar, refaz
  `GET /api/v1/produtos/?tipo=...&search=...&page=...` com o `tipo`
  correspondente (ou sem `tipo` para "Todos"). Estado novo:
  `const [filtroTipo, setFiltroTipo] = useState('')`.
- Card/linha da listagem: mostrar badge "Produto"/"Serviço"
  (`p.tipo_display` ou mapeado localmente); quando `p.tipo === 'SERVICO'`,
  ocultar a célula/linha "Estoque" (ex.: renderizar "—" ou nada).

### PDV (`frontend/src/pages/pdv/FrenteDeCaixa.jsx` e componentes de busca)

- Resultado de busca de produto: exibir badge "Serviço" quando
  `produto.tipo === 'SERVICO'`; nunca exibir o badge "Sem estoque" nesse
  caso (badge de estoque continua exclusivo de Produto com
  `quantidade_estoque <= 0`).
- Ao adicionar um item de Serviço ao carrinho: não solicitar/exibir campo
  de unidade na linha do carrinho (ou exibir vazio/"—" em vez do seletor
  de unidade usado para Produto).

### Vendas (`frontend/src/pages/Vendas.jsx` — `BuscaProdutoRapida` e
`ProdutoAutocomplete`, usados em Orçamento/Pedido)

- Mesmo tratamento do PDV: badge "Serviço" no resultado de busca; item de
  serviço adicionado à lista de itens do Orçamento/Pedido sem campo de
  unidade (o model `ItemOrcamento`/`ItemPedido` já não tem campo
  `unidade`, então não há mudança de payload aqui — é só visual, exibir
  badge no autocomplete).

### Combos (`ComboForm`, dentro de `Produtos.jsx`)

- Sem mudança obrigatória — autocomplete de produto do Combo pode
  continuar listando Produto e Serviço juntos (fora de escopo vedar isso,
  ver seção "Fora do Escopo").

---

## Critérios de Aceite

- CA-01: migration aplicada sem erro; todo `Produto` pré-existente fica
  `tipo=PRODUTO`.
- CA-02: criar Serviço via API sem estoque → sucesso, 0 `MovimentoEstoque`
  criado, `quantidade_estoque` permanece 0.
- CA-03: `POST /produtos/{id}/movimentos/` em Serviço → 400.
- CA-04: `POST /produtos/{id}/conversoes/` em Serviço → 400.
- CA-05: vender um Serviço no PDV (`finalizar_venda`) → nenhum
  `MovimentoEstoque` criado, nenhuma tentativa de baixa de estoque, venda
  finalizada normalmente com Receita pelo valor correto.
- CA-06: vender Produto + Serviço na mesma Venda → só o Produto baixa
  estoque; total da venda soma os dois corretamente.
- CA-07: cancelar venda com item de Serviço → sem erro, sem alteração de
  estoque relacionada ao serviço; estorno financeiro ocorre normalmente.
- CA-08: `GET /produtos/?tipo=PRODUTO` e `?tipo=SERVICO` retornam
  subconjuntos corretos; sem o parâmetro, retorna todos (0 regressão).
- CA-09: tentar trocar `tipo` de um Produto existente via PATCH não altera
  o valor gravado.
- CA-10: criar item de Serviço em Orçamento/Pedido → sucesso, 0
  `MovimentoEstoque`.
- CA-11: frontend — botão "+ Novo Item" presente; form muda de campos
  conforme Produto/Serviço escolhido; listagem com abas Produtos/Serviços/
  Todos funcionando; seletor de tipo desabilitado na edição.
- CA-12: 100% dos testes Django pré-existentes continuam passando (0
  regressão) — suíte completa, não só os testes novos desta manutenção.

---

*Gerado pelo Analista — Manutenção #91, UidCore. Pronto para Blueprint/
Forge/Loom seguirem via Planner.*
