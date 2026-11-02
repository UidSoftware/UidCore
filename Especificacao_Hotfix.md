# Especificação Hotfix — Manutenção #90

**Sistema:** UidCore (OS #7, template — `/var/www/uidcore`)
**Módulo:** Financeiro — Contas a Receber (`ReceitasTab`, `financeiro.Receita`)
**Data:** 2026-11-02
**Analista:** Claude (Analista — modo manutenção)
**Origem:** replicação da Manutenção #83 do fork LifeStyle (pedido do Luiz Eduardo,
29/10/2026) — "para todo fork novo já nascer com isso". Esta especificação
é a versão **genérica (multi-nicho)** do mesmo comportamento, escrita direto
contra o código real do UidCore (não é um copy-paste do LifeStyle — há
diferenças reais de estado atual entre os dois, detalhadas na seção 1.2).

---

## 1. Contexto

### 1.1 Pedido original

> Contas a Receber > Nova Receita: campo Cliente com preenchimento automático.
> `Receita` já tem FK `cliente` no backend, mas o form de Nova Receita não
> deixa escolher.
> - Adicionar o campo Cliente (busca no cadastro de clientes) no form.
> - Ao escolher o cliente, buscar no banco e preencher automaticamente Tipo,
>   Descrição e Valor Bruto (todos continuam editáveis):
>   - se o cliente tem assinatura ativa: Tipo = Mensalidade, Descrição =
>     `'Mensalidade <plano> - <mês/ano>'`, Valor Bruto = valor do plano, e
>     vincula a assinatura (`Receita.assinatura`) e a categoria do plano. Se
>     tiver mais de uma assinatura ativa, mostrar a lista para escolher.
>   - se não tem assinatura mas tem venda/pedido em aberto: oferecer para
>     escolher qual.
>   - se não tem nada: só vincula o cliente, sem preencher.
> - Não gerar receita duplicada: se já existir receita da mesma assinatura
>   no mesmo mês de referência, avisar antes de salvar.
> Validação: cliente com assinatura ativa preenche os 3 campos com o valor
> do plano; cliente sem nada só vincula.

### 1.2 Diagnóstico (AS-IS), confirmado em código — não por suposição

- `backend/financeiro/models.py::Receita` já tem `cliente` (FK nullable para
  `clientes.Cliente`, `on_delete=PROTECT`) e `assinatura` (FK nullable para
  `assinaturas.Assinatura`, `on_delete=SET_NULL`, desde a Manutenção #64
  [NUCLEO 3/5]) — **nunca foi problema de banco/model**. Já existe também
  `referencia_mes` (`DateField`, auto-preenchido em `save()` via
  `mes_competencia()` se não vier no payload) e a `UniqueConstraint
  uniq_assinatura_referencia_mes` (condicional, só quando `assinatura` não é
  nulo) como 2ª camada de defesa contra duplicidade.
- `backend/financeiro/serializers.py::ReceitaSerializer` já expõe `cliente`
  (gravável) e `referencia_mes` (gravável, com `input_formats=['%Y-%m',
  'iso-8601']` para aceitar `type="month"` do frontend) em `Meta.fields` —
  **nunca foi problema de serializer para esses dois campos**. O problema
  real está em `assinatura`: hoje está em `read_only_fields = ['valor_liquido',
  'created_at', 'assinatura']` — só `assinaturas/services.py::gerar_cobrancas_mes()`
  grava esse FK, direto no ORM (`Receita.objects.get_or_create(...)`), nunca
  pelo serializer. Para cumprir "vincula a assinatura" a partir do form
  manual, o serializer precisa passar a aceitar esse campo **na criação**
  (RN-07/RN-08 abaixo) — sem isso, o preenchimento automático dos 3 campos
  funcionaria visualmente, mas a Receita seria salva sem o vínculo real,
  quebrando a regra de não-duplicação (a constraint de banco só protege
  linhas com `assinatura` não nulo).
- `frontend/src/pages/Financeiro.jsx::ReceitasTab`: `EMPTY_RECEITA` já tem a
  chave `cliente: ''` (linha 750) e `openEdit()` já lê `item.cliente || ''`
  (linha 562) — o **estado já carrega o valor** — mas o JSX do `<form>`
  dentro do `Modal` (linhas ~698-734) **nunca renderiza um campo/input para
  `cliente`**. O usuário não tem como escolher, então toda Receita manual
  nasce com `cliente=null`. Mesmo bug relatado, mesma causa raiz do
  LifeStyle.
- **Diferença real em relação ao LifeStyle #83 (não ignorar ao implementar):**
  o campo "Mês de Referência" (`referencia_mes`, `type="month"`) **já existe**
  no form do UidCore (linha 721 de `Financeiro.jsx`, introduzido antes desta
  manutenção — ver histórico de competência/DRE no `CLAUDE.md` global). No
  LifeStyle esse campo teve que ser criado do zero na #83; aqui **não**
  precisa — é só reaproveitado como já está.
- `frontend/src/pages/Assinaturas.jsx::ClienteAutocomplete` (linhas 81-167)
  já é o componente de referência a clonar: busca debounced (300ms) em
  `/clientes/?search=`, chip com nome quando selecionado, botão "✕" para
  limpar. **Mesmo padrão de clone local** já usado nesta mesma
  `Financeiro.jsx` para `BuscaFornecedorRapida` (Manutenção #89, linha 759) —
  esta manutenção replica o padrão de "clone visual local", não extrai
  componente compartilhado.
- `backend/assinaturas/models.py::Assinatura` já tem `status`
  (`ATIVA|PAUSADA|ENCERRADA`), `plano` (FK `Plano`, com `valor` e
  `categoria`), `valor` (snapshot próprio da assinatura, pode ter desconto
  negociado — **não** é o mesmo que `plano.valor` "ao vivo") e é filtrável
  por `cliente`.
- `backend/vendas/models.py` tem `Orcamento` (status
  `RASCUNHO|ENVIADO|APROVADO|REJEITADO|CANCELADO`, campos `numero`,
  `descricao`, `valor_total`) e `Pedido` (status
  `PENDENTE|CONFIRMADO|EM_PRODUCAO|ENTREGUE|CANCELADO`, campos `numero`,
  `observacoes`, `valor_total`), ambos com FK `cliente` nullable. **Nenhum
  dos dois tem FK de volta para `Receita`** — "vincular" uma venda/pedido em
  aberto só pode significar *copiar dados para pré-preencher*, nunca um
  vínculo formal em banco (fora de escopo criar isso agora — ver seção 7).
- Precedente direto no mesmo módulo e mesmo estilo: Manutenção #89
  (`DespesaViewSet.sugestao_categoria`, `url_path='sugestao-categoria'`,
  `GET`, `detail=False`) já resolve o mesmo formato de problema para
  Despesa/Fornecedor — sugestão sem bloquear, nunca falha por falta de
  dado, resposta `200` com campos `null`/listas vazias quando não há nada a
  sugerir. Esta manutenção replica esse padrão para Receita/Cliente.
- Nenhuma migration é necessária — `cliente`, `assinatura` e
  `referencia_mes` já existem no model `Receita` desde manutenções
  anteriores (#64 e a criação original do módulo financeiro). A mudança é
  só em `serializer`/`view`/`frontend`.

### 1.3 Por que isso não é só "adicionar um input"

O pedido exige comportamento condicional em 3 camadas (assinatura ativa →
venda/pedido em aberto → nada) com regra de não-duplicação amigável. Por
isso a FK `cliente` sozinha não resolve: é preciso um endpoint de agregação
(o frontend não deve fazer 3 requisições e cruzar os dados sozinho com a
mesma robustez de regra de negócio) e uma mudança pontual de contrato no
serializer (`assinatura` gravável na criação, com validação de
imutabilidade pós-criação e de não-duplicação).

### Arquivos lidos para esta especificação
- `backend/financeiro/models.py` (Receita, Categoria, StatusReceita, TipoReceita, `mes_competencia`)
- `backend/financeiro/serializers.py` (ReceitaSerializer, DespesaSerializer — padrão `sugestao-categoria`)
- `backend/financeiro/views.py` (ReceitaViewSet, DespesaViewSet.sugestao_categoria)
- `backend/assinaturas/models.py` (Plano, Assinatura, StatusAssinatura)
- `backend/assinaturas/serializers.py`, `backend/assinaturas/views.py` (padrão de actions/transições)
- `backend/clientes/models.py` (Cliente, PessoaBase)
- `backend/vendas/models.py` (Orcamento, Pedido, StatusOrcamento, StatusPedido)
- `frontend/src/pages/Financeiro.jsx` (ReceitasTab, EMPTY_RECEITA, BuscaFornecedorRapida — padrão de clone local)
- `frontend/src/pages/Assinaturas.jsx` (ClienteAutocomplete — componente a clonar)

---

## 2. AS-IS → TO-BE (resumo)

| Item | AS-IS | TO-BE |
|---|---|---|
| Campo Cliente no form de Receita | Existe no state (`cliente`), nunca renderizado | Autocomplete visível, grava `cliente` |
| `ReceitaSerializer.assinatura` | `read_only_fields` (nunca gravável via API) | Gravável **só na criação**; imutável em edição (RN-07) |
| Endpoint de sugestão | Não existe | `GET /api/v1/financeiro/receitas/sugestao-cliente/?cliente_id=<id>` |
| Preenchimento automático (Tipo/Descrição/Valor) | Não existe | Árvore de decisão: assinatura ativa → venda aberta → nada |
| Mês de Referência no form | **Já existe** (linha 721, `type="month"`) | Sem mudança — só passa a ser preenchido junto quando há assinatura |
| Duplicidade de receita de assinatura no mês | Só a `UniqueConstraint` de banco (erro genérico de integridade) | Validação amigável em `validate()` antes de chegar na constraint (RN-08) |

---

## 3. Requisitos Funcionais (RF)

- **RF-01** — O form de "Nova Receita"/"Editar Receita" (`ReceitasTab`,
  `Financeiro.jsx`) passa a exibir um campo **Cliente** no topo do form
  (antes de Tipo/Conta), com busca por nome (autocomplete, não `<select>`).
  Componente `ClienteAutocomplete` clonado localmente em `Financeiro.jsx` a
  partir do já existente em `Assinaturas.jsx` (mesmo visual, mesma busca
  debounced em `/clientes/?search=`).

- **RF-02** — Ao selecionar um Cliente no autocomplete **somente no fluxo
  de criação** (nunca ao editar uma Receita já existente — RN-01), o
  frontend chama `GET /api/v1/financeiro/receitas/sugestao-cliente/?cliente_id=<id>`
  e usa a resposta para decidir o que pré-preencher, seguindo a árvore de
  decisão do RF-03/04/05.

- **RF-03** — **Caso 1 — cliente com assinatura(s) ativa(s):**
  - Se houver **exatamente 1** `Assinatura` com `status=ATIVA` e
    `cliente=<selecionado>`: pré-preenche automaticamente, sem ação extra:
    - `tipo` = `MENSALIDADE`
    - `descricao` = `"Mensalidade <nome do plano> - <mês/ano atual>"`
      (ex.: `"Mensalidade Plano Mensal - 11/2026"`)
    - `valor_bruto` = `Assinatura.valor` (snapshot próprio — **nunca**
      `Assinatura.plano.valor`, que pode ter sido alterado depois da
      contratação)
    - `categoria` = `Assinatura.plano.categoria_id`
    - `referencia_mes` = 1º dia do mês atual (campo já existente no form)
    - campo oculto `assinatura` = id da Assinatura (estado interno do
      form, enviado no payload, grava `Receita.assinatura`)
  - Se houver **mais de 1** Assinatura ativa: não pré-preenche nada ainda —
    exibe uma lista para o usuário escolher qual (seção 6.1). Ao escolher,
    aplica o mesmo preenchimento acima para a assinatura escolhida.
  - Todos os campos preenchidos continuam **editáveis** — nada fica
    `disabled`.

- **RF-04** — **Caso 2 — cliente sem assinatura ativa, mas com venda em
  aberto:** "venda em aberto" = `Pedido` com `status` em `PENDENTE`,
  `CONFIRMADO` ou `EM_PRODUCAO` (não `ENTREGUE`/`CANCELADO`), **ou**
  `Orcamento` com `status` em `RASCUNHO`, `ENVIADO` ou `APROVADO` (não
  `REJEITADO`/`CANCELADO`), filtrados por `cliente=<selecionado>`. Exibe
  lista para o usuário escolher qual venda (mesmo quando houver só 1 — aqui
  é sempre escolha explícita, diferente do caso de assinatura única, porque
  pode haver Orçamento *e* Pedido abertos ao mesmo tempo). Ao escolher:
  - `tipo` = `SERVICO` se Orçamento, `PRODUTO` se Pedido (sugestão inicial,
    continua editável)
  - `descricao` = `"<numero> - <descricao ou 'Orçamento'/'Pedido'>"`
    (ex.: `"PED-2026-0034 - Pedido"`)
  - `valor_bruto` = `valor_total` do Orçamento/Pedido escolhido
  - `categoria` e `assinatura` **não** são preenchidos (Orçamento/Pedido não
    têm categoria financeira nem é assinatura)

- **RF-05** — **Caso 3 — cliente sem assinatura ativa e sem venda em
  aberto:** só vincula o `cliente` selecionado. Nenhum outro campo é
  tocado (continuam como o usuário já tinha digitado, se algo).

- **RF-06** — Novo endpoint `GET /api/v1/financeiro/receitas/sugestao-cliente/?cliente_id=<id>`
  (action `detail=False` em `ReceitaViewSet`, mesmo padrão de
  `DespesaViewSet.sugestao_categoria`), retornando:
  ```json
  {
    "assinaturas_ativas": [
      {
        "id": 7,
        "plano_id": 2,
        "plano_nome": "Plano Mensal",
        "valor": "199.90",
        "categoria_id": 5,
        "categoria_nome": "Mensalidades",
        "referencia_mes_sugerido": "2026-11-01",
        "descricao_sugerida": "Mensalidade Plano Mensal - 11/2026",
        "ja_tem_receita_mes_atual": false
      }
    ],
    "vendas_abertas": [
      {
        "tipo": "PEDIDO",
        "id": 12,
        "numero": "PED-2026-0034",
        "descricao_sugerida": "PED-2026-0034 - Pedido",
        "valor_total": "450.00"
      }
    ]
  }
  ```
  Nunca falha por falta de dado — cliente sem nada retorna
  `{"assinaturas_ativas": [], "vendas_abertas": []}` com `200` (mesmo
  princípio de `sugestao-categoria`, Manutenção #89).

- **RF-07** — `ja_tem_receita_mes_atual` (RF-06) é só um indicador
  informativo de UI (aviso leve ao lado da assinatura na lista de escolha,
  ex. "⚠ já existe cobrança deste mês"). A regra de bloqueio real (RN-08)
  vive no backend e cobre qualquer mês escolhido, não só o atual.

- **RF-08** — Campo **Mês de Referência já existente** no form (sem
  mudança de código nesse ponto): quando uma assinatura é selecionada
  (RF-03), o frontend também seta `referencia_mes` para o mês sugerido
  pelo endpoint, usando o mesmo campo que já existe. Continua editável.

---

## 4. Regras de Negócio (RN)

- **RN-01** — O preenchimento automático (RF-03/04/05) só acontece ao
  **criar** uma Receita nova, nunca ao abrir o modal de **edição** de uma
  Receita existente. Editar uma Receita já salva não re-dispara a consulta
  de assinatura/venda nem sobrescreve valores já ajustados manualmente.

- **RN-02** — Trocar o Cliente selecionado (antes de salvar) re-dispara o
  fluxo de sugestão do zero para o novo cliente (limpa escolha de
  assinatura/venda anterior, se havia, e limpa o `assinatura` oculto do
  form).

- **RN-03** — Todos os campos preenchidos automaticamente (`tipo`,
  `descricao`, `valor_bruto`, `categoria`, `referencia_mes`) continuam
  100% editáveis pelo usuário antes de salvar — preenchimento automático é
  só sugestão de ponto de partida, nunca valor travado.

- **RN-04** — "Assinatura ativa" = `Assinatura.status == 'ATIVA'` e
  `Assinatura.is_active == True` (soft delete) e `Assinatura.cliente_id ==
  cliente_id` informado. Não considerar `PAUSADA` nem `ENCERRADA` como
  ativa, mesmo que `data_fim` ainda esteja no futuro — status é a fonte de
  verdade (mesmo critério de `assinaturas/services.py::gerar_cobrancas_mes`).

- **RN-05** — "Venda em aberto" (RF-04) é definida pelos status listados
  no RF-04 — não incluir `Orcamento`/`Pedido` com `is_active=False`
  (soft-deletados).

- **RN-06** — O endpoint `sugestao-cliente` exige `cliente_id` (`400` com
  mensagem clara se ausente, ou se o cliente não existir/estiver
  soft-deletado) — mesmo padrão de validação de `sugestao-categoria`.

- **RN-07** — `ReceitaSerializer.assinatura` passa a ser **gravável na
  criação** (sai de `read_only_fields`), mas **imutável após a criação**:
  tentativa de alterar `assinatura` num `PATCH`/`PUT` de Receita já
  existente é rejeitada com `400` e mensagem clara (mesmo padrão de campo
  imutável pós-criação já usado em `CategoriaSerializer.tipo`, Manutenção
  #88). Isso preserva o vínculo automático criado por
  `gerar_cobrancas_mes()` (via ORM direto, nunca passa pelo serializer) e
  impede reatribuir depois do fato uma Receita de uma assinatura para
  outra.

- **RN-08** — **Não duplicar receita da mesma assinatura no mesmo mês de
  referência** (pedido explícito). Ao criar ou editar uma Receita com
  `assinatura` preenchido e `referencia_mes` preenchido, o backend verifica
  se já existe outra Receita **ativa** (`is_active=True`), **não
  cancelada** (`status != 'CANCELADO'`), com o mesmo `assinatura_id` e
  `referencia_mes` (excluindo a própria instância em caso de edição). Se
  existir, rejeita com `400` e mensagem legível:
  `"Já existe uma receita para esta assinatura no mês de referência informado (Receita #<id>, status <status>)."`
  Esta validação é **independente e complementar** à `UniqueConstraint`
  de banco já existente (`uniq_assinatura_referencia_mes`) — a constraint
  não distingue `CANCELADO` de outros status e devolveria erro genérico de
  integridade; `validate()` do serializer devolve a mensagem amigável
  antes de chegar lá. Cumpre literalmente "avisar antes de salvar".

- **RN-09** — Se `assinatura` for informado no payload, precisa pertencer
  ao `cliente` informado na mesma Receita (`Assinatura.cliente_id ==
  Receita.cliente_id`) — senão `400`:
  `"A assinatura informada não pertence ao cliente selecionado."`
  Protege contra payload manipulado/inconsistência de UI.

- **RN-10** — Selecionar uma venda em aberto (RF-04) nunca grava nenhum FK
  novo em `Receita` (não existe campo para isso no model, e criar um está
  fora do escopo — seção 7). É só preenchimento de texto/valor, sem
  rastreabilidade formal Receita↔Pedido/Orçamento.

- **RN-11** — `vendas_abertas` e `assinaturas_ativas` no retorno do
  endpoint (RF-06) podem vir ambos preenchidos pelo backend (regra "o que
  mostrar" não é só backend), mas a **UI segue a árvore de decisão do
  RF-03/04/05 estritamente na ordem** — assinatura ativa tem prioridade
  sobre venda em aberto. O frontend só mostra a lista de vendas abertas se
  `assinaturas_ativas` estiver vazio.

- **RN-12 (multi-nicho)** — Nada nesta manutenção referencia nicho
  específico (estúdio, pilates, clínica etc.) — "assinatura" é sempre
  `assinaturas.Assinatura` (módulo núcleo), "venda/pedido" é sempre
  `vendas.Orcamento`/`vendas.Pedido` (módulo núcleo). Qualquer fork futuro
  que personalize nomenclatura de tela não deve exigir mudança neste
  endpoint/serializer — é comportamento de template, replicável sem
  adaptação por nicho.

---

## 5. Especificação Backend (para o Forge)

### 5.1 `backend/financeiro/serializers.py` — `ReceitaSerializer`

```python
class ReceitaSerializer(AuditFieldsMixin, serializers.ModelSerializer):
    id = serializers.IntegerField(source='pk', read_only=True)
    cliente_nome = serializers.CharField(source='cliente.nome_razao_social', read_only=True)
    conta_nome = serializers.CharField(source='conta.nome', read_only=True)
    categoria_nome = serializers.CharField(source='categoria.nome', read_only=True)

    class Meta:
        model = Receita
        fields = [
            'id', 'tipo', 'descricao',
            'cliente', 'cliente_nome',
            'categoria', 'categoria_nome',
            'valor_bruto', 'desconto', 'valor_liquido',
            'conta', 'conta_nome',
            'vencimento', 'recebimento', 'status',
            'referencia_mes', 'assinatura', 'observacoes', 'is_active', 'created_at',
            'created_by_nome', 'updated_by_nome',
        ]
        # Manutencao #90 (RN-07) — 'assinatura' SAI de read_only_fields:
        # passa a ser gravavel na CRIACAO (fluxo manual de Nova Receita
        # vinculando a uma assinatura ativa, RF-03/06). Antes disso so
        # assinaturas.services.gerar_cobrancas_mes gravava esse FK (via
        # Receita.objects.get_or_create, direto no ORM, nunca pelo
        # serializer) — esse fluxo continua intacto, nao passa por aqui.
        # Imutabilidade pos-criacao e garantida em validate(), nao aqui.
        read_only_fields = ['valor_liquido', 'created_at']
        extra_kwargs = {'referencia_mes': {'input_formats': ['%Y-%m', 'iso-8601']}}

    def validate(self, data):
        bruto = data.get('valor_bruto', getattr(self.instance, 'valor_bruto', Decimal('0')))
        desconto = data.get('desconto', getattr(self.instance, 'desconto', Decimal('0')))
        if desconto > bruto:
            raise serializers.ValidationError({'desconto': 'Desconto não pode ser maior que o valor bruto.'})

        # RN-07: assinatura imutavel apos criacao — so pode ser definida no
        # POST de criacao; PATCH/PUT que tenta mudar o vinculo e rejeitado.
        if self.instance and 'assinatura' in data:
            nova = data['assinatura']
            atual = self.instance.assinatura
            if (nova.pk if nova else None) != (atual.pk if atual else None):
                raise serializers.ValidationError(
                    {'assinatura': 'Não é possível alterar a assinatura vinculada após a criação.'}
                )

        assinatura = data.get('assinatura', getattr(self.instance, 'assinatura', None))
        cliente = data.get('cliente', getattr(self.instance, 'cliente', None))
        referencia_mes = data.get('referencia_mes', getattr(self.instance, 'referencia_mes', None))

        if assinatura:
            # RN-09 — assinatura informada precisa pertencer ao cliente informado.
            if cliente and assinatura.cliente_id != cliente.pk:
                raise serializers.ValidationError(
                    {'assinatura': 'A assinatura informada não pertence ao cliente selecionado.'}
                )
            # RN-08 — nao duplicar receita da mesma assinatura no mesmo mes
            # de referencia. Complementar (nao substitui) a UniqueConstraint
            # uniq_assinatura_referencia_mes ja existente no model.
            if referencia_mes:
                conflito_qs = Receita.objects.filter(
                    assinatura_id=assinatura.pk, referencia_mes=referencia_mes, is_active=True,
                ).exclude(status='CANCELADO')
                if self.instance:
                    conflito_qs = conflito_qs.exclude(pk=self.instance.pk)
                existente = conflito_qs.first()
                if existente:
                    raise serializers.ValidationError({
                        'assinatura': (
                            f'Já existe uma receita para esta assinatura no mês de referência '
                            f'informado (Receita #{existente.pk}, status {existente.get_status_display()}).'
                        )
                    })
        return data
```

Nenhuma migration necessária — `cliente`, `assinatura` e `referencia_mes`
já existem no model `Receita`. A `extra_kwargs` de `referencia_mes` já
existe hoje — manter tal como está, não remover.

### 5.2 `backend/financeiro/views.py` — `ReceitaViewSet`

Nova action, mesmo estilo de `DespesaViewSet.sugestao_categoria`:

```python
@action(detail=False, methods=['get'], url_path='sugestao-cliente')
def sugestao_cliente(self, request):
    """
    Manutencao 90 — sugere assinatura ativa ou venda em aberto do cliente
    para pre-preencher o form de Nova Receita no frontend (RF-03/04/05).
    Nunca bloqueia nem falha: cliente sem nada -> 200 com listas vazias.
    """
    from clientes.models import Cliente
    from assinaturas.models import Assinatura
    from vendas.models import Orcamento, Pedido

    cliente_id = request.query_params.get('cliente_id')
    if not cliente_id:
        return Response({'detail': 'cliente_id é obrigatório.'}, status=400)
    if not Cliente.objects.filter(pk=cliente_id, is_active=True).exists():
        return Response({'detail': 'Cliente não encontrado.'}, status=400)

    hoje = date.today()
    mes_atual = hoje.replace(day=1)

    assinaturas = (
        Assinatura.objects.filter(
            cliente_id=cliente_id, status='ATIVA', is_active=True,
        )
        .select_related('plano', 'plano__categoria')
    )
    assinaturas_data = []
    for a in assinaturas:
        ja_tem = Receita.objects.filter(
            assinatura_id=a.pk, referencia_mes=mes_atual, is_active=True,
        ).exclude(status='CANCELADO').exists()
        assinaturas_data.append({
            'id': a.pk,
            'plano_id': a.plano_id,
            'plano_nome': a.plano.nome,
            'valor': str(a.valor),
            'categoria_id': a.plano.categoria_id,
            'categoria_nome': a.plano.categoria.nome,
            'referencia_mes_sugerido': mes_atual.isoformat(),
            'descricao_sugerida': f'Mensalidade {a.plano.nome} - {mes_atual.strftime("%m/%Y")}',
            'ja_tem_receita_mes_atual': ja_tem,
        })

    vendas_abertas = []
    if not assinaturas_data:  # RN-11
        orcamentos = Orcamento.objects.filter(
            cliente_id=cliente_id, is_active=True,
            status__in=['RASCUNHO', 'ENVIADO', 'APROVADO'],
        )
        for o in orcamentos:
            vendas_abertas.append({
                'tipo': 'ORCAMENTO', 'id': o.pk, 'numero': o.numero,
                'descricao_sugerida': f'{o.numero} - {o.descricao or "Orçamento"}',
                'valor_total': str(o.valor_total),
            })
        pedidos = Pedido.objects.filter(
            cliente_id=cliente_id, is_active=True,
            status__in=['PENDENTE', 'CONFIRMADO', 'EM_PRODUCAO'],
        )
        for p in pedidos:
            vendas_abertas.append({
                'tipo': 'PEDIDO', 'id': p.pk, 'numero': p.numero,
                'descricao_sugerida': f'{p.numero} - {p.observacoes or "Pedido"}',
                'valor_total': str(p.valor_total),
            })

    return Response({'assinaturas_ativas': assinaturas_data, 'vendas_abertas': vendas_abertas})
```

**Import circular** — `financeiro/views.py` precisa importar de
`assinaturas.models` e `vendas.models`. Esses apps já importam `financeiro`
só via string de FK (`'financeiro.Categoria'`, `'financeiro.Conta'`), o que
não gera import Python real — sem risco esperado. Mesmo assim, fazer o
import **local dentro do método** (como já é o padrão em `estornar()`/
`estornar_despesa()` neste mesmo arquivo), nunca no topo do módulo.

Adicionar `'referencia_mes'` a `filterset_fields` de `ReceitaViewSet` (hoje
`['tipo', 'status', 'cliente', 'conta', 'assinatura']`) — barato e
consistente, útil para telas futuras que consultem por mês (ex. aba
Assinaturas na ficha do Cliente). Incluir se de baixo risco.

### 5.3 Testes (`backend/financeiro/tests.py`)

Cobrir, no mínimo (espelhando os critérios de aceite da seção 8):
- `sugestao-cliente` sem `cliente_id` → `400`.
- `sugestao-cliente` com cliente inexistente/soft-deletado → `400`.
- `sugestao-cliente` com cliente sem assinatura/venda → `200`, listas vazias.
- `sugestao-cliente` com 1 assinatura ativa → `assinaturas_ativas` com 1
  item, campos corretos (`valor` = `Assinatura.valor`, não `Plano.valor`).
- `sugestao-cliente` com 2+ assinaturas ativas → lista com 2+ itens.
- `sugestao-cliente` com assinatura ativa **e** venda aberta → `vendas_abertas`
  vazio (RN-11 — prioridade de assinatura).
- `sugestao-cliente` sem assinatura mas com Orçamento `APROVADO` e Pedido
  `CONFIRMADO` → ambos aparecem em `vendas_abertas`.
- POST de Receita com `assinatura` válida e pertencente ao cliente → `201`,
  `Receita.assinatura` gravado corretamente.
- POST de Receita com `assinatura` de outro cliente → `400` (RN-09).
- POST de 2ª Receita para a mesma assinatura + mesmo `referencia_mes`
  (status != CANCELADO) → `400` com mensagem citando a Receita existente
  (RN-08) — e **não** o erro genérico de `IntegrityError`.
- PATCH tentando trocar `assinatura` de uma Receita já criada → `400`
  (RN-07).
- PATCH sem tocar `assinatura` → `200`, sem erro (RN-07 não deve bloquear
  edição de outros campos).

---

## 6. Telas (detalhamento, para o Loom)

### 6.1 Modal "Nova Receita" / "Editar Receita" (`ReceitasTab`, `Financeiro.jsx`)

**Antes:** Tipo, Conta, Categoria, Descrição, Valor Bruto, Desconto,
Vencimento, Mês de Referência, Observações. Sem campo Cliente visível.

**Depois:**

1. Logo no topo do form (antes do grid Tipo/Conta), novo campo **Cliente**
   — componente `ClienteAutocomplete` clonado de `Assinaturas.jsx` para
   dentro de `Financeiro.jsx` (mesmo padrão de clone local já usado para
   `BuscaFornecedorRapida`, Manutenção #89). Visível em criação e edição;
   em edição, mostra o cliente já vinculado (se houver) mas **sem**
   disparar a lógica de sugestão (RN-01) — usar a prop `disabled` do
   componente quando `editingId` estiver setado (mostra chip somente
   leitura com o nome do cliente, sem possibilidade de busca/troca).

2. Ao selecionar um cliente **durante a criação** (`!editingId`):
   - Chama `GET /financeiro/receitas/sugestao-cliente/?cliente_id=<id>`.
   - Se `assinaturas_ativas.length === 1`: aplica o preenchimento
     automático direto (RF-03), seta `assinatura` (estado interno do form,
     nunca exibido como campo editável) e `referencia_mes`.
   - Se `assinaturas_ativas.length > 1`: renderiza lista/rádio abaixo do
     campo Cliente: "Este cliente tem mais de uma assinatura ativa —
     escolha qual cobrar:" com `plano_nome` + valor formatado em BRL +
     badge "⚠ já cobrado este mês" quando `ja_tem_receita_mes_atual=true`.
     Ao clicar numa opção, aplica o preenchimento.
   - Se `assinaturas_ativas.length === 0` e `vendas_abertas.length > 0`:
     renderiza lista "Este cliente tem vendas em aberto — vincular a uma
     delas?" com `descricao_sugerida` + valor. Ao clicar, aplica RF-04
     (sem setar `assinatura`).
   - Se ambas vazias: nenhuma UI extra aparece, só o campo Cliente fica
     preenchido (RF-05).

3. Campo **"Mês de referência (competência)"** (`referencia_mes`) **já
   existe** — nada a criar aqui. Quando uma assinatura é escolhida (RF-03),
   o form também preenche esse campo com o mês sugerido pelo endpoint
   (continua editável, igual já é hoje).

4. Trocar o Cliente selecionado (RN-02) limpa a escolha de assinatura/venda
   feita anteriormente (e o `assinatura` oculto) e refaz a consulta.

5. `handleSubmit` já envia `cliente`/`referencia_mes` (já estão no `form`
   state) — só precisa garantir que `assinatura` (quando setado via fluxo
   de assinatura) também esteja no `form` state antes de
   `stripEmptyStrings(form)`.

6. Erro de validação do backend (RN-08/RN-09, `400` com
   `{"assinatura": "..."}`) usa o mesmo fluxo já existente
   (`extractErrorMessage(error, 'Erro ao salvar receita.')` +
   `showToast(..., 'error')`) — sem UI de erro nova, só garantir que a
   mensagem do backend (não um texto genérico) chegue ao usuário.

### 6.2 Novo state em `ReceitasTab`

```js
const EMPTY_RECEITA = {
  tipo: 'SERVICO', descricao: '', cliente: '', categoria: '',
  valor_bruto: '', desconto: '0', conta: '', vencimento: '',
  referencia_mes: '', assinatura: '', observacoes: '',
}
```

+ estados auxiliares: `clienteSelecionado` (objeto `{id, nome}`, mesmo
padrão de `Assinaturas.jsx`), `sugestaoCliente` (resultado do endpoint:
`{assinaturas_ativas, vendas_abertas}` ou `null`), `vendaEscolhida`
(`{tipo, id}` só para destacar visualmente a opção escolhida, se
necessário).

### 6.3 Novo componente local `ClienteAutocomplete` em `Financeiro.jsx`

Clonar o componente já existente em `Assinaturas.jsx` (linhas 81-167),
mesmo padrão já replicado para `BuscaFornecedorRapida` nesta mesma
`Financeiro.jsx` (Manutenção #89, comentário de precedente na linha 754).
**Não extrair para componente compartilhado** nesta manutenção — mudança
de escopo maior (afetaria 2+ arquivos); o próprio código já documenta esse
padrão de "clone visual local" como aceito na fábrica.

---

## 7. Fora de Escopo (explicitamente, para não virar discussão em revisão)

- Criar FK formal `Receita.pedido`/`Receita.orcamento` para rastrear
  formalmente de onde veio a receita de uma venda — hoje é só
  preenchimento de texto/valor (RN-10). Manutenção própria se o negócio
  precisar disso depois.
- Geração automática de Receita a partir de Pedido/Orçamento fechado (ex.
  "ao aprovar Orçamento, criar Receita sozinho") — não foi pedido; é
  sempre o usuário abrindo "Nova Receita" manualmente e escolhendo.
- Qualquer mudança em `gerar_cobrancas_mes()` (cron mensal de assinaturas,
  Manutenção #64) — continua gravando `Receita.assinatura` direto via ORM,
  sem passar pelo serializer, não afetado pela saída de `assinatura` de
  `read_only_fields` (RN-07).
- Alterar `Categoria`/`Plano`/`Assinatura` — nenhum model novo, nenhum
  campo novo nesses apps.
- Extrair `ClienteAutocomplete` para componente compartilhado entre
  `Assinaturas.jsx`/`Financeiro.jsx` — mantém o padrão de clone local já em
  uso na fábrica.
- Qualquer personalização por nicho (estúdio, pilates, clínica, etc.) —
  este comportamento é 100% núcleo/template, replicável em qualquer fork
  sem adaptação (RN-12).

---

## 8. Critérios de Aceite

- **CA-01** — Form de Nova Receita exibe campo Cliente com autocomplete
  funcional (busca real em `/clientes/`).
- **CA-02** — Selecionar um cliente com exatamente 1 assinatura ativa
  preenche automaticamente Tipo=MENSALIDADE, Descrição
  (`"Mensalidade <plano> - <mês/ano>"`), Valor Bruto (= `Assinatura.valor`),
  Categoria (= categoria do plano) e Mês de Referência (mês atual) — todos
  continuam editáveis.
- **CA-03** — Selecionar um cliente com 2+ assinaturas ativas exibe lista
  de escolha; escolher uma aplica o mesmo preenchimento do CA-02 para a
  assinatura escolhida.
- **CA-04** — Selecionar um cliente sem assinatura ativa mas com Pedido ou
  Orçamento em aberto exibe lista de escolha; escolher um preenche
  Tipo/Descrição/Valor Bruto a partir dele, sem setar `assinatura`.
- **CA-05** — Selecionar um cliente sem assinatura ativa e sem venda em
  aberto só vincula o Cliente — nenhum outro campo é alterado.
- **CA-06** — Salvar uma Receita vinculada a uma assinatura grava
  `Receita.assinatura` corretamente (confirmado via API real).
- **CA-07** — Tentar salvar uma segunda Receita para a mesma assinatura e
  mesmo mês de referência é rejeitado pelo backend com mensagem legível
  citando a Receita já existente (não erro genérico de integridade de
  banco).
- **CA-08** — Editar uma Receita já existente nunca tenta alterar seu
  `assinatura` — tentativa via payload direto (teste de API) retorna
  `400` com mensagem clara.
- **CA-09** — `assinatura` informado para um cliente diferente do
  `cliente` informado é rejeitado (`400`, RN-09).
- **CA-10** — `GET /financeiro/receitas/sugestao-cliente/` sem
  `cliente_id` retorna `400`; com `cliente_id` de cliente
  inexistente/soft-deletado também retorna `400`; com cliente válido sem
  nenhuma assinatura/venda retorna `200` com as duas listas vazias.
- **CA-11** — Abrir o modal de **edição** de uma Receita existente nunca
  dispara a lógica de sugestão (RN-01) — campo Cliente aparece preenchido
  (somente leitura), sem o endpoint de sugestão sendo chamado.
- **CA-12** — `0` migrations novas necessárias (`makemigrations --check
  --dry-run` limpo) — mudança é só serializer/view/frontend.
- **CA-13** — Com assinatura ativa **e** venda em aberto simultaneamente
  para o mesmo cliente, só a lista de assinaturas é exibida (RN-11) —
  venda em aberto nunca aparece nesse cenário.

---

## 9. Riscos / Pontos de Atenção para Forge e Loom

- **`Assinatura.valor` vs `Plano.valor`:** usar sempre `Assinatura.valor`
  (snapshot, pode ter desconto negociado) — nunca `Assinatura.plano.valor`
  — para o Valor Bruto sugerido (RF-03). Confundir os dois é erro já
  citado em manutenções anteriores (preço "ao vivo" vs snapshot).
- **`UniqueConstraint` de banco existente:** `uniq_assinatura_referencia_mes`
  continua valendo como 2ª camada de defesa — a validação em `validate()`
  (RN-08) é a 1ª camada (mensagem amigável), não a substitui.
- **Campo `cliente` em edição:** não reverter para `disabled=true` em TODO
  o form — só o componente `ClienteAutocomplete` fica somente-leitura em
  edição; os demais campos (Tipo, Descrição, Valor Bruto etc.) continuam
  editáveis como já são hoje.
- **Import circular:** se o Forge notar qualquer erro de import ao
  executar `sugestao_cliente`, preferir import local dentro do método
  (já é o padrão recomendado nesta spec) — nunca subir os imports de
  `assinaturas`/`vendas` para o topo de `financeiro/views.py`.
- **Replicação para outros forks:** este comportamento deve se comportar
  de forma idêntica em qualquer fork futuro do UidCore (LifeStyle já tem a
  versão equivalente, Manutenção #83) — ao revisar, não introduzir nada
  específico de nicho.
