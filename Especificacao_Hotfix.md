# Especificação Hotfix — Manutenção #88

**Sistema:** UidCore (OS #7)
**Projeto:** /var/www/uidcore
**Data:** 2026-11-01
**Tipo:** feature_pequena (classificação: CRUD de cadastro + ajuste em 2 telas existentes — sem novo app, sem integração externa, sem aprovação comercial)
**Analista:** modo manutenção

---

## 0. Achado crítico pré-implementação (ler antes de tudo)

O briefing recebido ("Contexto técnico já levantado") afirma que
**`CategoriaViewSet` NÃO existe e precisa ser criado**. Isso está
**desatualizado** — conferido linha a linha no código real na VPS:

```
backend/financeiro/serializers.py:10  → class CategoriaSerializer(AuditFieldsMixin, ...)  [EXISTE]
backend/financeiro/views.py:37        → class CategoriaViewSet(AuditMixin, ModelViewSet)  [EXISTE]
backend/financeiro/urls.py:7          → router.register('categorias', ...)                [EXISTE]
```

Rota real já ativa: **`/api/v1/financeiro/categorias/`**
(`permission_classes = [IsAdmin | IsFinanceiro]`, `filterset_fields = ['tipo']`,
`AuditMixin` → soft delete via `is_active`, sem busca por nome ainda —
`search_fields` não está declarado, só `filterset_fields`).

Isso veio provavelmente de um ciclo anterior (ex.: Manutenção #57, gráfico
"Gastos por Categoria") que criou o CRUD básico sem nunca ter feito a tela
de frontend correspondente — o que combina com o pedido real do cliente
("tela de cadastro"): **o backend básico (sem hierarquia) já existe, falta
pai/subcategoria + a tela**.

**Impacto no escopo:** Forge não cria o ViewSet/Serializer/rota do zero —
ele **estende** os três (adiciona `pai`, valida hierarquia, adiciona
`search_fields`). Isso reduz risco de regressão (nenhuma breaking change
de contrato — só campos novos, todos opcionais) mas Forge precisa ler
`CategoriaSerializer`/`CategoriaViewSet` atuais antes de editar, não
reescrever.

**Segundo achado, também não citado no briefing:** os formulários de
Receita e Despesa em `frontend/src/pages/Financeiro.jsx`
(`ReceitasTab`/`DespesasTab`) **já têm `categoria` no estado do form e no
payload enviado** (`EMPTY_RECEITA`/`EMPTY_DESPESA`, `openEdit` mapeando
`item.categoria`), **mas não existe nenhum campo `<Select label="Categoria">`
renderizado no modal** — confirmado via grep, zero ocorrência. Ou seja, hoje
é impossível um usuário escolher categoria ao criar Receita/Despesa pela
tela — o campo sempre vai vazio. O pedido "atalho + Nova categoria nos
forms de Receita e Despesa" só faz sentido se esse campo for adicionado
primeiro — por isso isso entra no escopo desta manutenção como RF-11
(não é scope creep, é pré-requisito do que foi pedido).

Já o form de Plano (`Assinaturas.jsx`, `AbaListaPlanos`) **já tem** o select
de Categoria funcionando (`categoriaOptions` buscado de
`/financeiro/categorias/?tipo=ENTRADA`) — só falta o atalho "+ Nova
categoria" ao lado dele.

---

## 1. Contexto

Cliente quer gerenciar categorias financeiras (hoje só existem via Django
admin ou seed manual) e organizá-las em até 1 nível de subcategoria (ex.:
"Combustível" como categoria-pai de "Carro"/"Moto"). Hoje toda tela que usa
categoria (Plano, e — depois desta manutenção — Receita/Despesa) depende de
já existir categoria cadastrada; sem tela de cadastro, a única forma de
criar uma é Django admin (acesso que o cliente final do UidCore não tem —
só a Uid, via `is_staff`, ver RBAC Superadmin/Admin no CLAUDE.md global) ou
`python manage.py shell`.

## 2. AS-IS

- `Categoria` existe (nome, tipo ENTRADA/SAIDA, soft delete), sem hierarquia.
- CRUD via API já existe (`/api/v1/financeiro/categorias/`), mas **sem
  tela de frontend** — único consumidor hoje é leitura (dropdown de Plano
  e, antes desta manutenção, nenhum lugar grava categoria nova pela tela).
- Nenhuma carga inicial de categorias — banco pode estar 100% vazio de
  `Categoria`, travando o cadastro de `Plano` (FK obrigatória; sem opção
  satisfazendo `limit_choices_to`, nenhuma aparece no select).
- Receita/Despesa já têm FK `categoria` (nullable) no model e no
  serializer, mas o campo nunca é exposto no formulário de criação/edição.

## 3. TO-BE

- Tela própria "Categorias" dentro do módulo Financeiro, com hierarquia
  visual (pai → subcategorias), CRUD completo, filtro por tipo, soft
  delete (ativar/desativar).
- Campo `pai` na `Categoria`, restrito a 1 nível, mesmo tipo do pai.
- Atalho "+ Nova categoria" nos 3 forms que consomem `Categoria` (Plano,
  Receita, Despesa) — cria sem navegar para fora do form atual.
- Comando de carga inicial (`carregar_categorias_padrao`) rodável em
  qualquer ambiente (novo fork/cliente) sem duplicar se rodado de novo.

## 4. Requisitos Funcionais

### Backend

- **RF-01 (MUST)** — Adicionar campo `Categoria.pai` (FK nullable para
  `self`, `on_delete=PROTECT` — não deixar apagar categoria-pai com
  filhos ativos sem decisão explícita; `related_name='subcategorias'`).
- **RF-02 (MUST)** — Validação no `CategoriaSerializer.validate()`:
  - se `pai` informado: `pai.tipo == self.tipo` (mesmo tipo ENTRADA/SAIDA),
    senão erro `{"pai": "A subcategoria deve ser do mesmo tipo da categoria-pai."}`.
  - se `pai` informado: `pai.pai is None` (pai não pode já ser subcategoria —
    trava nesting > 1 nível), senão erro
    `{"pai": "Uma subcategoria não pode ter subcategorias (máximo 1 nível)."}`.
  - categoria não pode ser pai de si mesma (`pai_id != self.pk` no update).
- **RF-03 (MUST)** — Estender `CategoriaSerializer` (não recriar): adicionar
  `pai`, `pai_nome` (`source='pai.nome'`, `read_only=True`,
  `default=''`/`allow_null=True`), `subcategorias_count`
  (`SerializerMethodField`, conta `subcategorias.filter(is_active=True).count()`
  — usado pelo frontend pra decidir aviso antes de excluir).
- **RF-04 (MUST)** — Estender `CategoriaViewSet` (não recriar):
  adicionar `SearchFilter` com `search_fields = ['nome']` (hoje só tem
  `DjangoFilterBackend`/`filterset_fields=['tipo']` — falta busca por
  nome, pedida no briefing). Manter `permission_classes = [IsAdmin | IsFinanceiro]`
  (já correto, não alterar).
  - **RN-03**: `queryset` do ViewSet continua `is_active=True` por padrão
    (herda o filtro já existente) — ver seção 8 (Riscos) sobre listagem de
    inativas ficar fora do escopo desta manutenção.
- **RF-05 (MUST)** — Soft delete: `perform_destroy` já vem de
  `AuditMixin`/`BaseModel` padrão da fábrica — **Forge deve ler o
  `AuditMixin` completo** (`backend/common/mixins.py`) antes de assumir que
  ele já cobre `perform_destroy`; se não cobrir, implementar
  `perform_destroy` custom no `CategoriaViewSet` fazendo soft delete +
  bloqueio se tiver subcategoria ativa ou estiver em uso
  (`.planos.exists() or .receitas.exists() or .despesas.exists()`, todos
  filtrando `is_active=True`) — devolver 400 com mensagem clara em vez de
  deixar órfão.
- **RF-06 (MUST)** — Migration para o campo `pai` (`financeiro/migrations/00XX_categoria_pai.py`
  — a última migration hoje é `0012_despesa_financeira_e_competencia.py`,
  confirmar o próximo número livre na hora de gerar — só `AddField`, sem
  `RunPython`).
- **RF-07 (MUST)** — Management command `carregar_categorias_padrao`
  (`backend/financeiro/management/commands/carregar_categorias_padrao.py`
  — seguir o estilo de `backend/assinaturas/management/commands/gerar_cobrancas_assinaturas.py`:
  docstring, `--dry-run` opcional, resumo no `stdout`):
  - Idempotente via `get_or_create(nome=..., tipo=..., pai=pai_obj, defaults={...})`
    — **nunca** `get_or_create` só por `nome` (a `unique_together` real do
    model é `[nome, tipo]`, sem `pai` — ver RN-04 abaixo).
  - **RN-04**: como `unique_together` atual é só `[nome, tipo]`, duas
    subcategorias com mesmo nome e tipo mas pais diferentes colidiriam no
    banco. Para o seed desta manutenção isso não ocorre (só "Carro"/"Moto"
    sob um único pai "Combustível"), mas é uma lacuna de modelagem
    preexistente. **Decisão do Analista:** não alterar `unique_together`
    nesta manutenção (mudar constraint existente tem risco de migration de
    dado em produção, fora do escopo pedido) — Forge deve registrar isso
    como dívida técnica no relatório final, não resolver por conta própria.
  - Seed exato pedido:
    ```
    ENTRADA (sem pai): Venda de serviços, Venda de produtos, Mensalidades, Outras receitas
    SAIDA  (sem pai): Aluguel, Água/Luz/Internet, Salários, Pró-labore,
                       Impostos e taxas, Marketing, Manutenção,
                       Combustível, Outras despesas
    SAIDA  (pai=Combustível): Carro, Moto
    ```
  - Rodar 2x não deve criar duplicata nem alterar `is_active`/`pai` de
    categoria já existente que o usuário tenha editado manualmente
    (`get_or_create` nunca sobrescreve registro já existente).
  - Comando é chamado manualmente pelo Pilot após o deploy (não é
    migration de dado automática).
- **RF-08 (MUST)** — Nenhuma mudança de contrato em `Plano`/`Assinatura` —
  já consomem `Categoria` corretamente (`Plano.categoria`,
  `limit_choices_to={'tipo': 'ENTRADA', 'is_active': True}`).

### Frontend

- **RF-09 (MUST)** — Nova tela/aba **Financeiro → Categorias** (dentro de
  `Financeiro.jsx`, seguindo o padrão `AbaListaPlanos` já usado em
  `Assinaturas.jsx` — Card + Modal, sem componente de biblioteca externa,
  dark mode via tokens `navy-*`/`violet-*`):
  - Lista agrupada por tipo (ENTRADA / SAIDA); dentro de cada tipo,
    categorias-pai com suas subcategorias indentadas/aninhadas
    visualmente (ex.: "Combustível" e, recuado, "↳ Carro", "↳ Moto").
  - Filtro por tipo (select ENTRADA/SAIDA/Todas).
  - Busca por nome (campo de texto, usa o `search_fields` novo do RF-04).
  - CRUD: criar/editar via Modal (campos: nome, tipo, pai — select de
    categorias do MESMO tipo e SEM pai próprio, populado dinamicamente ao
    trocar o tipo); excluir = soft delete com confirmação (`window.confirm`,
    padrão já usado em `handleExcluir` de `Assinaturas.jsx`).
  - Badge visual Ativa/Inativa (mesmo padrão `plano.ativo` em
    `Assinaturas.jsx`).
- **RF-10 (MUST)** — Atalho **"+ Nova categoria"** no modal de Plano
  (`AbaListaPlanos` em `Assinaturas.jsx`, ao lado do
  `<Select label="Categoria" ...>` já existente): abre um segundo Modal
  empilhado (ou inline — decisão do Loom, mas nunca navegar para fora do
  form de Plano) com campos mínimos (nome; tipo pré-travado em ENTRADA,
  já que `Plano.categoria` só aceita `tipo=ENTRADA`), salva via
  `POST /financeiro/categorias/`, e no sucesso: refaz o fetch de
  `categoriaOptions` e **seleciona automaticamente** a categoria recém-criada
  no select do Plano.
- **RF-11 (MUST)** — Mesmo atalho "+ Nova categoria" nos forms de Receita
  e Despesa em `Financeiro.jsx` — **mas primeiro precisa existir o campo
  Categoria nesses forms**, que hoje não existe (achado da seção 0):
  - Adicionar `<Select label="Categoria" name="categoria" ...>` no modal
    de `ReceitasTab` (buscando `/financeiro/categorias/?tipo=ENTRADA`) e
    de `DespesasTab` (`?tipo=SAIDA`) — mesmo padrão já usado em
    `AbaListaPlanos` (`categoriaOptions` com `useEffect`, opção vazia
    "Selecione...").
  - Campo é opcional (`Receita.categoria`/`Despesa.categoria` são
    `null=True, blank=True` no model) — não travar submit sem categoria.
  - Atalho "+ Nova categoria" ao lado, mesmo comportamento do RF-10 (tipo
    pré-travado conforme a aba — ENTRADA em Receita, SAIDA em Despesa).
- **RF-12 (SHOULD)** — Texto de ajuda no campo Categoria do form de Plano:
  *"Categoria financeira em que as mensalidades deste plano entram nos
  relatórios."* (`<p className="text-xs text-gray-400 ...">`, mesmo padrão
  já usado abaixo do campo "Mês de referência" em Receita/Despesa).
- **RF-13 (COULD)** — Texto de ajuda equivalente em Receita/Despesa (ex.:
  *"Categoria em que este lançamento entra no relatório de DRE/Gastos por
  Categoria."*).

## 5. Regras de Negócio (RN) — consolidado

| RN | Regra |
|---|---|
| RN-01 | Categoria com subcategoria ativa não pode, ela mesma, receber um `pai` (não inverte hierarquia). |
| RN-02 | Categoria não pode ser pai de si mesma. |
| RN-03 (já citada acima) | Subcategoria só pode ter pai do MESMO `tipo`; pai não pode ter pai (nesting limitado a 1 nível). |
| RN-04 (já citada acima) | `unique_together` de `Categoria` continua `[nome, tipo]` nesta manutenção — lacuna de modelagem para nomes repetidos sob pais diferentes é dívida técnica registrada, não resolvida agora. |
| RN-05 | `carregar_categorias_padrao` é idempotente — `get_or_create` por (nome, tipo, pai), nunca duplica ao rodar 2x. |
| RN-06 | Exclusão (soft delete) de categoria com subcategoria ativa ou em uso (Plano/Receita/Despesa `is_active=True`) é bloqueada com erro 400 explicativo — nunca deixa órfão silencioso. |
| RN-07 | Campo Categoria em Receita/Despesa é opcional — não quebra lançamento já existente sem categoria (todos os lançamentos atuais, já que o campo nunca foi exposto antes desta manutenção). |

## 6. Critérios de Aceite

- **CA-01**: Com o banco sem nenhuma `Categoria` de tipo ENTRADA, usuário
  consegue: abrir tela Financeiro → Categorias (ou atalho no form de
  Plano) → criar categoria ENTRADA pela tela → voltar ao form de Plano →
  nova categoria aparece no select → salvar Plano com sucesso.
- **CA-02**: Tentar criar subcategoria de tipo diferente do pai (ex.: pai
  SAIDA, subcategoria tentando ENTRADA) é rejeitado com mensagem clara
  (400, não 500).
- **CA-03**: Tentar criar uma subcategoria de uma subcategoria (nesting > 1
  nível) é rejeitado.
- **CA-04**: `python manage.py carregar_categorias_padrao` executado 2x
  seguidas não duplica nenhuma categoria (contagem igual nas duas rodadas,
  conferir via `Categoria.objects.filter(is_active=True).count()`).
- **CA-05**: Seed cria exatamente a árvore pedida — `Combustível` sem pai,
  `Carro`/`Moto` com `pai=Combustível`, todas as demais sem pai.
- **CA-06**: Tela de Categorias lista hierarquia corretamente (pai e
  subcategorias visualmente distintos), filtra por tipo, busca por nome.
- **CA-07**: Atalho "+ Nova categoria" em Plano, Receita e Despesa cria a
  categoria sem navegar para fora do form, e a seleciona automaticamente
  no campo de origem.
- **CA-08**: Excluir (soft delete) categoria-pai com subcategoria ativa é
  bloqueado com mensagem explicativa; excluir categoria sem filhos e sem
  uso funciona normalmente.
- **CA-09**: Receita/Despesa criadas pela tela agora persistem `categoria`
  corretamente quando selecionada (hoje sempre vai `null`/vazio — regressão
  zero: lançamentos antigos sem categoria continuam válidos).
- **CA-10**: 0 migrations pendentes pós-deploy; 0 regressão nos testes
  existentes de `financeiro`/`assinaturas`.

## 7. Fora do Escopo (WON'T nesta manutenção)

- Mudar `unique_together` de `Categoria` para incluir `pai` (ver RN-04 —
  fica como dívida técnica documentada, não bloqueante).
- Permitir mais de 1 nível de subcategoria.
- Relatórios financeiros (DRE, Gastos por Categoria) agruparem
  automaticamente subcategoria dentro do total do pai — melhoria futura.
- Expor reativação de categoria inativa pela tela (listagem de inativas) —
  ver seção 8; fica só via Django admin da Uid por ora.
- Migração de dado retroativo (lançamentos antigos sem categoria não
  precisam ser preenchidos).

## 8. Riscos e Dependências

- Campo `pai` com `on_delete=PROTECT` pode gerar erro 500 não tratado se
  o Forge não implementar o `perform_destroy` customizado do RF-05 —
  Sentinel deve testar exclusão de categoria-pai via API real, não só
  teste unitário de model.
- `limit_choices_to` em `Plano.categoria`/`Receita.categoria`/
  `Despesa.categoria` já filtra por `tipo` E `is_active=True` — o select de
  "pai" no form de Categoria (frontend) precisa replicar esse filtro
  manualmente (mesmo tipo, mesmo `is_active`), já que é outro endpoint
  (`/financeiro/categorias/?tipo=X`), não há `limit_choices_to` client-side
  automático.
- Dívida técnica preexistente identificada (fora do escopo, só registrar):
  `CategoriaViewSet` atual não tem forma de listar categorias inativas
  (reativação) — se o Forge/Loom não tiverem certeza sobre expor isso,
  **implementar o caminho mais simples (criar/editar/desativar, sem
  reativar pela tela nesta manutenção)** e registrar a lacuna no
  CLAUDE.md para decisão futura do Luiz Eduardo.

---

**Observação de autoria:** `backend/financeiro/models.py`,
`backend/financeiro/serializers.py`, `backend/financeiro/views.py`,
`backend/financeiro/urls.py`, `backend/assinaturas/models.py`,
`backend/assinaturas/serializers.py`, `frontend/src/pages/Financeiro.jsx`
e `frontend/src/pages/Assinaturas.jsx` foram lidos integralmente (trechos
relevantes) antes de escrever esta especificação — os achados da seção 0
são baseados em código real, não no briefing recebido do Planner/Hotfix.
