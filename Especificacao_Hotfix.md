# Especificação Hotfix — Manutenção #89

**Sistema:** UidCore (OS #7)
**Projeto:** /var/www/uidcore
**Data:** 2026-11-01
**Tipo:** feature_pequena (FK em cadastro existente + 2 campos novos em model existente + ajuste de 1 formulário — sem app novo, sem integração externa)
**Analista:** modo manutenção

---

## 0. Achados de leitura do código real (antes de especificar)

Lidos integralmente antes de escrever esta especificação:
`backend/financeiro/models.py`, `backend/financeiro/serializers.py`,
`backend/financeiro/views.py`, `backend/financeiro/urls.py`,
`backend/fornecedores/models.py`, `backend/fornecedores/views.py`,
`backend/fornecedores/urls.py`, `backend/common/models.py`,
`frontend/src/pages/Financeiro.jsx` (trecho `DespesasTab` completo).

Confirmações relevantes (o briefing recebido já estava, no geral, correto —
estes são os detalhes exatos encontrados no código, não suposição):

- `Despesa.fornecedor` é `CharField(max_length=150, blank=True)` — texto
  livre, sem FK. Confirmado.
- `Despesa.categoria` **já é FK** para `Categoria`
  (`limit_choices_to={'tipo': 'SAIDA', 'is_active': True}`, `on_delete=
  SET_NULL`) — já existia antes da #88, não é novidade desta manutenção.
- `Categoria.pai` (FK para `self`, `on_delete=PROTECT`,
  `related_name='subcategorias'`) existe desde a migration
  `financeiro/migrations/0013_categoria_pai.py` (Manutenção #88, já em
  produção) — "subcategoria" é simplesmente uma `Categoria` com `pai !=
  null`, não é tabela nova. Confirmado.
- `Despesa.desconto` é `DecimalField(max_digits=12, decimal_places=2,
  default=0)`. `Despesa.save()` sempre recalcula
  `valor_liquido = valor_bruto - (desconto or Decimal('0'))` em
  `Decimal` — **este cálculo não muda nesta manutenção**; só passa a
  existir uma segunda forma de preencher `desconto` (a partir de um
  percentual), resolvida **antes** de chegar no `save()` do model.
- `DespesaSerializer.validate()` já bloqueia `desconto > valor_bruto`
  (`ValidationError`) — a validação permanece, aplicada ao valor final
  em R$ depois de resolvido o percentual.
- `fornecedores.models.Fornecedor` herda `common.models.PessoaBase`
  (`nome_razao_social`, `documento`, `tipo_pessoa`, `cpf`/`cnpj`, soft
  delete via `BaseModel`). Endpoint já existe:
  `GET /api/v1/fornecedores/` (`FornecedorViewSet`, `search_fields =
  ['nome_razao_social', 'documento', 'email', 'contato_nome']`,
  `queryset` filtra `is_active=True`).
- Última migration do app `financeiro` hoje: `0013_categoria_pai.py`.
  Esta manutenção usa `0014` e `0015` (nomes definidos em RF-02).
- `DespesaViewSet.filterset_fields` hoje é `['tipo', 'status', 'conta',
  'estornado']` — **`categoria` não está na lista**, apesar de já ser FK
  há mais tempo. O pedido do cliente ("filtros... aceitam fornecedor_fk,
  categoria e subcategoria") exige adicionar `categoria` também, não só
  os dois campos novos.
- `frontend/src/pages/Financeiro.jsx::DespesasTab` (linhas ~740-985 hoje):
  modal "Nova Despesa" já tem `Select Tipo` → `Select Conta` →
  `Select Categoria` (com atalho "+ Nova categoria", `CriarCategoriaRapidaModal`)
  → `Input Descrição` → **`Input Fornecedor` (texto livre, linha 946)**
  → grid Valor Bruto / Desconto (R$) / Vencimento → Mês de referência →
  Forma de Pagamento → Observações. O campo Fornecedor hoje fica no meio
  do form, não no topo.
- Já existe no histórico do projeto um padrão de "busca rápida no
  cadastro com debounce + dropdown + seleção direta" —
  `BuscaProdutoRapida` em `Vendas.jsx` (Manutenção #32) — é a referência
  de UX a seguir para o campo de Fornecedor, em vez de inventar uma
  interação nova.

---

## 1. Contexto

Hoje, ao lançar uma Despesa ("Contas a Pagar"), o campo **Fornecedor** é
texto livre — sem nenhum vínculo com o cadastro de Fornecedores que já
existe no sistema (`fornecedores.Fornecedor`). O cliente quer: (1) esse
campo passar a buscar no cadastro real de fornecedores e virar o primeiro
campo do formulário; (2) poder escolher Categoria **e** Subcategoria (a
hierarquia já existe desde a Manutenção #88); (3) poder lançar o desconto
tanto em reais quanto em percentual.

## 2. AS-IS

- `Despesa.fornecedor`: texto livre, sem FK, sem autocomplete — qualquer
  grafia diferente do mesmo fornecedor não é reconhecida como "o mesmo".
- `Despesa.categoria`: FK existente, exposta no form, mas sem campo de
  Subcategoria — mesmo a hierarquia já existindo em `Categoria.pai`.
- `Despesa.desconto`: só aceita valor em R$ digitado direto.
- Nenhuma sugestão de categoria baseada no histórico do fornecedor.

## 3. TO-BE

- `Despesa.fornecedor_fk`: FK opcional para `fornecedores.Fornecedor`,
  convivendo com o campo de texto legado (nunca removido, nunca
  obrigatório).
- Form de Nova Despesa: Fornecedor (busca + "+ Novo fornecedor") como
  **primeiro campo**; Categoria e Subcategoria logo depois de Tipo.
- Escolher um fornecedor sugere a categoria/subcategoria da última
  despesa dele (editável).
- Desconto em R$ **ou** % — sempre persistido em R$ no campo `desconto`
  já existente, com o percentual guardado para poder reexibir/reeditar.
- Filtros de Despesa por `fornecedor_fk`, `categoria` e `subcategoria`.

## 4. Requisitos Funcionais — Backend

- **RF-01 (MUST)** — `Despesa.fornecedor_fk`:
  ```python
  fornecedor_fk = models.ForeignKey(
      'fornecedores.Fornecedor', null=True, blank=True,
      on_delete=models.SET_NULL, related_name='despesas',
  )
  ```
  `Despesa.fornecedor` (CharField legado) permanece no model, inalterado,
  sem se tornar obrigatório nem ser removido.

- **RF-02 (MUST)** — Duas migrations:
  1. `financeiro/migrations/0014_despesa_fornecedor_fk.py` — `AddField`
     de `fornecedor_fk` (nullable) + `AddField` de `subcategoria` (RF-03)
     + `AddField` de `tipo_desconto`/`percentual_desconto` (RF-04) — ou
     separadas em migrations distintas, a critério do Forge; não há
     exigência de agrupar.
  2. `financeiro/migrations/0015_despesa_fornecedor_fk_backfill.py` —
     `RunPython` (`atomic=True`) idempotente: para cada `Despesa` com
     `fornecedor_fk IS NULL` e `fornecedor` não vazio, buscar
     `Fornecedor.objects.filter(nome_razao_social__iexact=<fornecedor
     .strip()>, is_active=True)`:
     - **exatamente 1 resultado** → seta `fornecedor_fk` para esse id.
     - **0 ou 2+ resultados** (ambíguo/sem match) → não altera nada; o
       texto legado em `fornecedor` permanece visível e intacto (RN-01).
     - Função reversa pode ser `migrations.RunPython.noop` (o rollback
       real é o `RemoveField` da migration anterior, se algum dia
       necessário).

- **RF-03 (MUST)** — `Despesa.subcategoria`:
  ```python
  subcategoria = models.ForeignKey(
      'Categoria', null=True, blank=True,
      on_delete=models.SET_NULL, related_name='despesas_subcategoria',
      limit_choices_to={'tipo': 'SAIDA', 'is_active': True},
  )
  ```
  Validação (serializer, RN-04): só aceita `Categoria` com `pai_id IS NOT
  NULL`; se `categoria` também vier no mesmo payload, exige
  `subcategoria.pai_id == categoria.id`.

- **RF-04 (MUST)** — Desconto em R$ ou %:
  ```python
  TIPO_DESCONTO = [('R$', 'Valor fixo (R$)'), ('%', 'Percentual (%)')]

  tipo_desconto = models.CharField(max_length=2, choices=TIPO_DESCONTO, default='R$')
  percentual_desconto = models.DecimalField(max_digits=5, decimal_places=2, default=0)
  ```
  - `desconto` (já existente) continua sendo a fonte de verdade em reais
    usada por `Despesa.save()` para `valor_liquido` — **nenhuma mudança
    no `save()` do model**.
  - Resolução do percentual acontece no **serializer**
    (`DespesaSerializer.validate()`), sempre com `Decimal` — nunca
    `float`: quando `tipo_desconto == '%'`,
    `desconto = (valor_bruto * percentual_desconto /
    Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)`,
    sobrescrevendo o que vier em `desconto` no payload (a % manda).
  - Quando `tipo_desconto == 'R$'`: `percentual_desconto` é zerado/
    ignorado pelo serializer; `desconto` é o valor informado direto,
    como já funciona hoje.
  - `percentual_desconto` validado em `[0, 100]`; fora disso → 400.
  - Validação já existente "`desconto` não pode ser maior que
    `valor_bruto`" permanece, aplicada ao valor final já resolvido.

- **RF-05 (MUST)** — `DespesaSerializer` (estender o já existente, não
  recriar):
  - Novos campos em `Meta.fields`: `fornecedor_fk`,
    `fornecedor_fk_nome` (`source='fornecedor_fk.nome_razao_social'`,
    `read_only=True`, `default=''`, `allow_null=True`), `subcategoria`,
    `subcategoria_nome` (`source='subcategoria.nome'`, `read_only=True`),
    `tipo_desconto`, `percentual_desconto`.
  - `fornecedor` (CharField legado) permanece no `Meta.fields`, editável.
  - `validate()`: resolver desconto percentual (RF-04) e validar
    subcategoria/categoria (RF-03/RN-04) antes da checagem já existente
    de `desconto > valor_bruto`.

- **RF-06 (MUST)** — `DespesaViewSet.filterset_fields` passa a ser
  `['tipo', 'status', 'conta', 'estornado', 'categoria', 'subcategoria',
  'fornecedor_fk']` (adiciona `categoria`, que faltava, junto com os dois
  campos novos).

- **RF-07 (MUST)** — Endpoint de sugestão de categoria/subcategoria por
  fornecedor, como `@action` dentro do próprio `DespesaViewSet` (mesmo
  padrão de `marcar_pago`/`estornar_despesa` já no arquivo):
  ```
  GET /api/v1/financeiro/despesas/sugestao-categoria/?fornecedor_fk=<id>
  ```
  - Sem `fornecedor_fk` na query string → 400.
  - Busca a `Despesa` mais recente (`is_active=True`,
    `fornecedor_fk=<id>`, ordenada por `pagamento` desc, depois
    `vencimento` desc, depois `created_at` desc — a mais recente por
    data real de negócio, não por `id`) e devolve
    `{"categoria": <id ou null>, "subcategoria": <id ou null>}`.
  - Nenhuma despesa anterior desse fornecedor → `{"categoria": null,
    "subcategoria": null}` (200, não erro).
  - Somente leitura, mesma permissão do restante do ViewSet (`IsAdmin |
    IsFinanceiro`).

- **RF-08 (MUST)** — Nenhuma alteração em `financeiro/relatorios.py` nem
  em `dashboard_financeiro` nesta manutenção — pedido explícito do
  cliente é "não criar gráfico novo"; os filtros do RF-06 já atendem
  "relatórios/filtros de despesa aceitam fornecedor_fk/categoria/
  subcategoria".

- **RF-09 (SHOULD)** — Confirmar se `CategoriaViewSet.filterset_fields`
  (hoje `['tipo']`) precisa de `'pai'` para o frontend filtrar
  subcategorias de uma categoria (`GET /financeiro/categorias/
  ?pai=<id>`) — se não aceitar, adicionar `'pai'` à lista como parte
  desta manutenção (1 linha, mesmo arquivo já sendo tocado).

## 5. Regras de Negócio

| RN | Regra |
|---|---|
| RN-01 | Despesa com `fornecedor` (texto legado) preenchido e `fornecedor_fk=null` nunca é escondida, apagada ou bloqueada — continua aparecendo normalmente em listagem/edição/filtro, mostrando o texto legado. |
| RN-02 | O backfill (RF-02) só vincula automaticamente em caso de match exato único (case-insensitive, strip); qualquer ambiguidade fica para resolução manual futura, sem bloquear deploy nem apagar dado. |
| RN-03 | Nenhuma conversão para `float` em nenhum ponto do cálculo de desconto percentual → reais; usar `Decimal`/`quantize` do início ao fim. |
| RN-04 | `subcategoria` só é aceita se `pai_id is not None`; se `categoria` vier junto, `subcategoria.pai_id` tem que ser igual a `categoria.id` — senão 400 com mensagem clara. |
| RN-05 | A sugestão de categoria/subcategoria (RF-07) nunca é aplicada automaticamente pelo backend — decisão de preencher o form é do frontend, e o campo continua editável/sobrescrevível pelo usuário. |
| RN-06 | `LivroCaixa`, estorno de despesa e cálculo de `valor_liquido` (`valor_bruto - desconto`) não são alterados nesta manutenção — só a origem do valor gravado em `desconto` muda (pode vir de % em vez de digitado direto em R$). |

## 6. Requisitos Funcionais — Frontend

Arquivo: `frontend/src/pages/Financeiro.jsx`, componente `DespesasTab`
(modal "Nova Despesa"/"Editar Despesa").

- **RF-F01 (MUST)** — Fornecedor como primeiro campo do formulário:
  substituir `<Input label="Fornecedor" name="fornecedor" .../>` (hoje no
  meio do form) por um componente de busca no cadastro
  (`BuscaFornecedorRapida` — mesma UX de `BuscaProdutoRapida` em
  `Vendas.jsx`: campo único, debounce ~300ms, `GET /api/v1/fornecedores/
  ?search=`, dropdown com `nome_razao_social`), posicionado **antes** de
  Tipo/Conta — primeiro campo visível do modal.
  - Selecionar um resultado preenche `form.fornecedor_fk`; não preenche
    mais `form.fornecedor` (texto).
  - "+ Novo fornecedor" ao lado, abrindo modal rápido de criação
    (`nome_razao_social`, `tipo_pessoa`, `documento` opcional) — ao
    salvar, preenche `fornecedor_fk` com o novo id automaticamente.
  - Editar despesa antiga (`fornecedor` texto, `fornecedor_fk=null`):
    mostrar o texto legado (ex.: rótulo "Fornecedor (cadastro antigo):
    <valor>") ao lado/abaixo do campo de busca, sem forçar vínculo —
    usuário pode deixar como está ou buscar e vincular.

- **RF-F02 (MUST)** — Categoria + Subcategoria depois de Tipo:
  `Select Categoria` (já existe, preservar atalho "+ Nova categoria") e,
  logo depois, novo `Select Subcategoria`, filtrado pela categoria
  escolhida (`GET /financeiro/categorias/?pai=<categoria_id>`). Trocar/
  limpar a Categoria esvazia e reseta a Subcategoria. Subcategoria é
  opcional (opção "Nenhuma" sempre presente).

- **RF-F03 (MUST)** — Sugestão por fornecedor: ao selecionar um
  fornecedor (RF-F01), chamar `GET /financeiro/despesas/sugestao-
  categoria/?fornecedor_fk=<id>`; se vier `categoria`/`subcategoria` não
  nulos **e** os campos correspondentes do form ainda estiverem vazios,
  pré-selecionar — nunca sobrescrever escolha já feita manualmente pelo
  usuário (RN-05). Sempre editável depois.

- **RF-F04 (MUST)** — Desconto em R$ ou %: substituir
  `<Input label="Desconto (R$)" .../>` por um seletor de 2 opções
  ("R$"/"%") + um campo numérico cujo rótulo acompanha a escolha.
  - Modo "%": mostrar preview do valor em R$ calculado em tempo real
    (`valor_bruto * percentual_desconto / 100`, formatado BRL) — o valor
    gravado de fato é sempre recalculado no backend.
  - Payload sempre envia `tipo_desconto`, `percentual_desconto` e
    `desconto` juntos; backend decide qual prevalece (RF-04 backend).
  - Editar uma despesa com `tipo_desconto='%'`: reabrir já no modo "%"
    com `percentual_desconto` preenchido, não só o valor em R$.

- **RF-F05 (SHOULD)** — Filtros na listagem de Contas a Pagar: adicionar
  filtro por Categoria e Subcategoria na área de busca já existente
  (mesmo padrão visual do filtro de Status atual). Filtro por fornecedor
  pode reaproveitar a busca textual já existente.

## 7. Critérios de Aceite

| # | Critério |
|---|---|
| CA-01 | `Despesa.fornecedor_fk` existe (FK nullable → `Fornecedor`); `Despesa.fornecedor` (texto) continua existindo e editável. |
| CA-02 | Migration de backfill roda sem erro contra dado real; despesa com nome batendo exatamente (case-insensitive, strip) com 1 único Fornecedor ativo ganha `fornecedor_fk`; ambíguas/sem match ficam com `fornecedor_fk=null` e texto legado intacto. |
| CA-03 | Form de Nova Despesa tem a busca de Fornecedor como primeiro campo, com "+ Novo fornecedor". |
| CA-04 | Categoria aparece depois de Tipo; Subcategoria aparece depois de Categoria e só lista categorias cujo `pai` é a categoria escolhida. |
| CA-05 | Escolher um Fornecedor que já teve despesa antes pré-preenche categoria/subcategoria sugeridas, mantendo-as editáveis. |
| CA-06 | Despesa de R$ 200,00 com 10% de desconto grava `desconto=20.00` e `valor_liquido=180.00`; o `LivroCaixa` gerado reflete R$ 180,00. |
| CA-07 | Reabrir para edição uma despesa criada com desconto em % mostra o modo "%" com o percentual original preenchido, não só o valor em R$. |
| CA-08 | Despesa antiga (fornecedor texto, sem FK) continua aparecendo normalmente em listagem/edição com o texto legado visível. |
| CA-09 | `GET /api/v1/financeiro/despesas/?subcategoria=<id>` filtra corretamente. |
| CA-10 | `GET /api/v1/financeiro/despesas/?fornecedor_fk=<id>` e `?categoria=<id>` filtram corretamente. |
| CA-11 | Enviar `subcategoria` cujo `pai` é `null`, ou cujo `pai` difere da `categoria` informada, retorna 400 com mensagem clara. |
| CA-12 | Enviar `percentual_desconto` fora de `[0, 100]` retorna 400. |
| CA-13 | Fluxo antigo (desconto em R$ direto, sem fornecedor_fk/subcategoria) continua funcionando sem regressão. |
| CA-14 | Todos os testes Django existentes continuam passando; novos testes cobrem CA-02, CA-06, CA-07, CA-11, CA-12. |
| CA-15 | 0 migrations pendentes pós-deploy. |

## 8. Fora do Escopo (WON'T nesta manutenção)

- Gráfico novo de despesas por fornecedor/subcategoria (pedido explícito
  do cliente: "não criar gráfico novo").
- Qualquer alteração em `LivroCaixa`, estorno de despesa ou regra de
  competência (`referencia_mes`).
- Remover ou obrigar o campo `Despesa.fornecedor` (texto legado).
- Replicar o mesmo padrão (fornecedor FK / categoria+subcategoria /
  desconto %) em `Receita` — pedido é só sobre `Despesa`.
- Resolver a lacuna preexistente de `Categoria.unique_together =
  ['nome', 'tipo']` (sem `pai`) — já registrada como dívida técnica na
  Manutenção #88, não reaberta aqui.

## 9. Riscos e Dependências

- O backfill (RF-02) depende de `nome_razao_social` estar bem cadastrado
  nos Fornecedores existentes — se o cadastro de Fornecedor estiver
  vazio ou pouco povoado em produção, a maioria das despesas antigas
  simplesmente não vincula automaticamente (comportamento esperado por
  RN-02, não é falha — mas Sentinel deve confirmar isso rodando contra
  dado real, não só fixture de teste).
- `on_delete=SET_NULL` em `fornecedor_fk`: se um Fornecedor for
  desativado (soft delete), despesas antigas mantêm o vínculo (soft
  delete não aciona `SET_NULL`, que só dispara em hard delete) — isso é
  o comportamento correto esperado (RN-01), só registrar para Sentinel
  confirmar que a FK aponta para um Fornecedor com `is_active=False` sem
  quebrar a tela (exibir normalmente, talvez com indicação visual —
  decisão de UX do Loom, não bloqueante).
- RF-09 é condicional: só implementar se `CategoriaViewSet` de fato não
  aceitar `?pai=` hoje — Forge confirma antes de criar migration/código
  desnecessário.

---

**Observação de autoria:** `backend/financeiro/models.py`,
`backend/financeiro/serializers.py`, `backend/financeiro/views.py`,
`backend/financeiro/urls.py`, `backend/fornecedores/models.py`,
`backend/fornecedores/views.py`, `backend/fornecedores/urls.py`,
`backend/common/models.py` e `frontend/src/pages/Financeiro.jsx`
(`DespesasTab` completo) foram lidos integralmente antes de escrever esta
especificação — os achados da seção 0 baseiam-se em código real, não só
no briefing recebido do Planner/Hotfix.
