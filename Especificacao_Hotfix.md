# Especificação Hotfix — Manutenção #62

**Sistema:** UidCore (OS #7)
**Pacote:** [NUCLEO 1/5] — melhoria de núcleo vinda da análise do NosFluir (Studio Fluir)
**Módulo:** `common` (novo núcleo de auditoria) + praticamente todos os apps backend + frontend (rodapé de auditoria)
**Tipo:** `feature_grande` — toca o `BaseModel` abstrato herdado por quase todo model do sistema; mudança de núcleo, não de tela isolada
**Requer aprovação comercial:** não — hardening interno de rastreabilidade, sem novo módulo cobrável
**Analista:** leitura de código confirmada em `backend/common/models.py`, `backend/common/permissions.py`, TODOS os `models.py`/`views.py`/`admin.py` dos 14 apps de negócio, grep completo por `criado_por` (backend) e `criado_por` (frontend — 0 ocorrências), estrutura de `frontend/src/components/ui/{ResourceCrud,Modal}.jsx` e das páginas com modal próprio (`Clientes`, `Fornecedores`, `Produtos`, `Vendas`, `Financeiro`, `Compras`).

---

## 1. Diagnóstico confirmado (grep + leitura de código)

### 1.1 Estado atual do `BaseModel`

`backend/common/models.py` hoje só tem:
```python
class BaseModel(models.Model):
    created_at = models.DateTimeField('criado em', auto_now_add=True)
    updated_at = models.DateTimeField('atualizado em', auto_now=True)
    is_active = models.BooleanField('ativo', default=True)
    class Meta:
        abstract = True
```
Não existe `common/mixins.py`. Não existe manager customizado — todo `ModelViewSet.get_queryset()`/`queryset =` filtra `is_active=True` manualmente, app por app (confirmado em `clientes`, `fornecedores`, `produtos`, `rh`, `agendamento`, `administrativo`, `pagamentos`, `financeiro`, `marketing` — nenhum usa manager próprio).

`PessoaBase(BaseModel)` é abstrato também — `Cliente` e `Fornecedor` herdam `BaseModel` indiretamente via `PessoaBase`.

### 1.2 Mapa completo de models que herdam `BaseModel` hoje (grep `^class .*BaseModel\|^class .*PessoaBase`)

| App | Models (herdam BaseModel/PessoaBase) |
|---|---|
| `administrativo` | `TipoDocumento`, `Documento` |
| `agendamento` | `Agenda`, `Compromisso` |
| `clientes` | `Cliente` (via `PessoaBase`), `HistoricoCliente`, `AcionistaCliente` |
| `compras` | `Compra` |
| `financeiro` | `Conta`, `Aporte`, `Categoria`, `Receita`, `EstornoReceita`, `Despesa`, `ConciliacaoExtrato`, `ItemConciliacao`, `PadraoSeguroConciliacao` |
| `fornecedores` | `Fornecedor` (via `PessoaBase`), `AcionistaFornecedor` |
| `marketing` | `Campanha`, `Lead` |
| `pagamentos` | `MetodoPagamento`, `Cobranca`, `Parcela` |
| `pdv` | `SessaoCaixa`, `MovimentoCaixa`, `Venda`, `ItemVenda`, `PagamentoVenda`, `RecebivelCartao` |
| `portal` | `AcessoPortalCliente` |
| `produtos` | `Produto`, `ConversaoUnidade`, `MovimentoEstoque`, `Combo` |
| `rh` | `Cargo`, `Colaborador`, `FolhaPagamento`, `RegistroFerias` |
| `vendas` | `Orcamento`, `Pedido`, `ItemOrcamento`, `ItemPedido` |

**Confirmado fora do `BaseModel` hoje** (bate com o pedido): `compras.ItemCompra`, `produtos.ItemCombo` (ambos `models.Model` puro, comentário no código explica "item filho, ciclo de vida atrelado ao pai"), `financeiro.LivroCaixa` (`models.Model` puro, razão imutável).

### 1.3 Mapa completo de `criado_por` avulso (grep `criado_por` em todo o backend — 0 no frontend)

Todos `ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=SET_NULL, related_name='+')` (exceto `produtos.Combo`, que usa `related_name='combos_criados'` — não `'+'`):

| App.Model | Linha (models.py) | Observação |
|---|---|---|
| `financeiro.Conta` | 23 | |
| `financeiro.Aporte` | 51 | |
| `financeiro.Receita` | 121 | |
| `financeiro.EstornoReceita` | 165 | |
| `financeiro.Despesa` | 231 | |
| `financeiro.LivroCaixa` | 273 | **Não herda BaseModel** — fica fora do item 5 do pedido, mas o campo existe e precisa ser renomeado (ver 2.5) |
| `financeiro.ConciliacaoExtrato` | 310 | |
| `financeiro.PadraoSeguroConciliacao` | 366 | |
| `pdv.RecebivelCartao` | 353 | |
| `vendas.Orcamento` | 30 | |
| `vendas.Pedido` | 86 | |
| `pagamentos.Cobranca` | 55 | |
| `compras.Compra` | 68 | |
| `administrativo.Documento` | 42 | |
| `agendamento.Compromisso` | 44 | |
| `produtos.MovimentoEstoque` | 132 | |
| `produtos.Combo` | 176 | `related_name='combos_criados'` (diferente do padrão `'+'`) |

Pontos de escrita de `criado_por=...` a ajustar (fora dos `models.py`):
- `financeiro/views.py` — `ContaViewSet.perform_create` (L63), `AporteViewSet.perform_create` (L150), `ReceitaViewSet.perform_create` (L173), `DespesaViewSet.perform_create` (L234), `LivroCaixaViewSet.perform_create` (L308)
- `financeiro/signals.py` — `_gerar_lancamento(..., criado_por=None)` (L34) + 3 chamadas internas (L66, L84, L100, L116)
- `financeiro/services.py` — `estornar_receita`/`estornar_despesa` (L80, L102, L170)
- `financeiro/conciliacao_service.py` — `criar_conciliacao(..., criado_por=None, ...)` (L120, L131 docstring, L159)
- `financeiro/management/commands/conciliar_extrato.py` — `criado_por=None` (L80)
- `pdv/services.py` — `_criar_receita_a_vista`/`_criar_receita_cartao` (L131, L159, L168)
- `vendas/views.py` — `OrcamentoViewSet.perform_create` (L28), `PedidoViewSet.perform_create` (L80)
- `pagamentos/views.py` — `CobrancaViewSet.perform_create` (L37)
- `compras/views.py` — `CompraViewSet.perform_create` (L39)
- `administrativo/views.py` — `DocumentoViewSet.perform_create` (L39)
- `agendamento/views.py` — `CompromissoViewSet.perform_create` (L37)
- `produtos/views.py` — `ComboViewSet.perform_create` (L184); `MovimentoEstoque` é criado via `save()` interno (não por ViewSet direto) — conferir chamadas em `produtos/views.py` e `compras/signals.py` (`compras/signals.py:45` — `criado_por=instance.criado_por`, repassa de `Compra` pro `MovimentoEstoque`/`Despesa` gerados)
- `produtos/serializers.py` — **único serializer que expõe `criado_por` hoje**: `criado_por_nome = serializers.CharField(source='criado_por.nome_completo', ...)` (L189) e `'criado_por'` em `fields`/`read_only_fields` (L195, L197) — `ComboSerializer`
- `produtos/tests.py` — `self.assertEqual(combo.criado_por, self.user)` (L739)

### 1.4 Mapa completo de `destroy()`/`perform_destroy()` por ViewSet (grep em todos os `views.py`)

Hoje **100% dos destroys já fazem soft delete** (`instance.is_active = False; instance.save(update_fields=[...])`) — não há `.delete()` hard em nenhum ViewSet de produção (bom, mas nenhum registra quem/quando excluiu). Dois padrões coexistem e importam para o design do `AuditMixin`:

**(A) ViewSets que sobrescrevem `destroy()` inteiro (NÃO chamam `perform_destroy`)** — precisam ser refatorados para delegar a `self.perform_destroy(instance)`, senão o `AuditMixin.perform_destroy` nunca executa:
`clientes.ClienteViewSet`, `fornecedores.FornecedorViewSet`, `administrativo.TipoDocumentoViewSet`, `administrativo.DocumentoViewSet`, `agendamento.AgendaViewSet`, `agendamento.CompromissoViewSet`, `financeiro.CategoriaViewSet`, `financeiro.ContaViewSet`, `financeiro.AporteViewSet`, `financeiro.ReceitaViewSet`, `financeiro.DespesaViewSet`, `pagamentos.MetodoPagamentoViewSet`, `pagamentos.CobrancaViewSet`, `pagamentos.ParcelaViewSet`, `produtos.ProdutoViewSet`, `produtos.ComboViewSet`, `vendas.OrcamentoViewSet`, `vendas.PedidoViewSet`, `vendas.ItemPedidoViewSet`, `rh.CargoViewSet`, `rh.ColaboradorViewSet`, `rh.FolhaPagamentoViewSet`, `rh.RegistroFeriasViewSet`, `marketing.CampanhaViewSet`, `marketing.LeadViewSet`, `pdv.SessaoCaixaViewSet` (linha 147 — mesmo com `http_method_names` sem `'delete'`, o método existe como código morto, manter padronizado), `pdv.VendaViewSet` (linha 408 — `http_method_names` inclui `'delete'` aqui, é usado de fato), `accounts.UserViewSet` (tem lógica extra `_bloquear_edicao_superadmin` — preservar).

**(B) ViewSets que já usam `perform_destroy` (só precisam herdar o mixin em vez de reescrever o corpo)**: `compras.CompraViewSet`, `financeiro.PadraoSeguroConciliacaoViewSet`, `portal.AcessoPortalClienteViewSet`.

**(C) Sem `destroy` exposto (sem ação, fora do escopo de delete)**: `financeiro.LivroCaixaViewSet` (`ReadCreateViewSet` — sem delete, correto, é razão imutável), `financeiro.ConciliacaoViewSet` (`ReadOnlyModelViewSet`).

### 1.5 Admin do Django

Vários arquivos `admin.py` existem (`accounts`, `administrativo`, `agendamento`, `clientes`, `compras`, `financeiro` confirmados por leitura; demais apps a confirmar por grep) — nenhum sobrescreve `get_queryset`, todos usam o manager padrão implicitamente. Isso importa diretamente para o item 3 do pedido (ver 2.3).

---

## 2. Decisões de arquitetura (fechadas nesta especificação)

| Decisão em aberto no pedido | Escolha | Justificativa |
|---|---|---|
| `is_active` muda de comportamento? | **Não.** Continua um campo independente, de negócio ("desligado/arquivado, reversível"). `deleted_at` é um conceito novo e paralelo ("excluído via API/tela, irreversível pela UI"). Um registro pode estar `is_active=False` sem nunca ter sido excluído (ex.: `Cargo` desativado, `Campanha` arquivada). | Pedido explícito no item 1 do escopo: "is_active CONTINUA existindo, com significado diferente". Reaproveitar `is_active` como flag de exclusão quebraria toda a UX hoje baseada nela (filtros, toggles) sem necessidade. |
| Como "registros excluídos somem da listagem" sem tocar em ~20 `get_queryset()`/`queryset =` que já filtram manualmente por `is_active=True`? | **Manager customizado em `BaseModel`**: `objects` (manager padrão) filtra `deleted_at__isnull=True` automaticamente; `all_objects` (manager secundário, sem filtro) para o Django Admin. | Toda `ViewSet` hoje já escreve `Model.objects.filter(is_active=True)` — como `.filter()` encadeia sobre o que `get_queryset()` do manager já devolve, o filtro de `deleted_at` entra de graça, sem editar nenhum desses ~20 pontos. É a opção "manager" citada no próprio pedido (item 3), e a que exige menos arquivos tocados. |
| Como o Admin do Django continua vendo tudo? | Novo `common/admin.py` com `class AuditModelAdmin(admin.ModelAdmin)` que sobrescreve `get_queryset(self, request)` → `self.model.all_objects.all()`. Toda classe `@admin.register(...)` de model que herda `BaseModel` passa a herdar `AuditModelAdmin` em vez de `admin.ModelAdmin` puro. | Sem isso, `self.model._default_manager` (que o `ModelAdmin` usa por padrão) seria o `objects` já filtrado — o superadmin deixaria de ver registros excluídos no `/admin/`, violando o pedido ("Admin do Django continua vendo tudo"). |
| `AuditMixin` fica em `ViewSet` ou em `Serializer`? | **ViewSet** (`common/mixins.py`), exatamente como pedido. `perform_create`/`perform_update`/`perform_destroy` têm acesso direto a `self.request.user`; fazer isso em serializer exigiria injetar `request` no `context` em todo lugar (já funciona via `get_serializer_context` padrão do DRF, mas a simetria com os 3 hooks de ciclo de vida do ViewSet é mais direta e é o que o pedido pede). | Pedido explícito no item 2. |
| ViewSets do grupo (A) (seção 1.4) — como migrar sem duplicar a chamada de `is_active=False`? | `destroy()` sobrescrito é **removido** nesses ViewSets (o `ModelViewSet.destroy()` padrão do DRF já chama `self.perform_destroy(instance)` internamente) — a única coisa que faltava nesses ViewSets era *um* `perform_destroy` customizado, que passa a vir do `AuditMixin`. Onde havia lógica extra antes do soft-delete (ex.: `accounts.UserViewSet._bloquear_edicao_superadmin`), essa checagem migra para dentro de um `perform_destroy` próprio que chama `super().perform_destroy(instance)` (do `AuditMixin`) depois de validar. | Elimina duplicação de `instance.is_active = False; instance.save(...)` repetida em ~25 arquivos — fica 1 implementação central. Onde há lógica extra, o padrão Django de `super()` resolve sem perder comportamento (exigência explícita do pedido, item 2: "chamar super() ou incorporar a lógica: não perder comportamento existente"). |
| `financeiro.LivroCaixa` (fora do `BaseModel`) — fica sem `created_by`? | **Mantém fora do `BaseModel`** (é razão imutável, nunca editada/excluída — RN já documentada no histórico do projeto). Mas o campo próprio `criado_por` (FK local, não herdado) é **renomeado para `created_by`** só por consistência de nomenclatura em toda a base — sem herdar `updated_by`/`deleted_by`/`deleted_at` (não fazem sentido, o model não tem update nem delete). `_gerar_lancamento(criado_por=...)` em `financeiro/signals.py` passa a receber/usar `created_by`. | Pedido explícito: "Só ganha created_by se fizer sentido no signal que o gera (_gerar_lancamento já recebe criado_por: mapear)". Não duplicar o conceito com nome diferente (`criado_por` vs `created_by`) no mesmo banco é mais fácil de auditar depois. |
| `ItemCompra`/`ItemCombo` passam a herdar `BaseModel` — algum ViewSet próprio precisa de `AuditMixin`? | **Não têm `ViewSet` próprio hoje** (são sub-recursos criados via `serializer` aninhado/`bulk create` dentro de `CompraViewSet`/`ComboViewSet` — confirmado em `compras/views.py` e `produtos/views.py`, sem rota própria em `urls.py`). Ganham os 4 campos de auditoria por herança de schema (migration), mas **não são tocados por `created_by`/`updated_by` automaticamente** — ficam `null` até alguém decidir expor isso no serializer pai (fora do escopo desta manutenção, que pede só herdar `BaseModel`, não auditoria completa neles). | Pedido item 5 só pede "passam a herdar BaseModel" — não pede novo endpoint nem `perform_create` próprio para esses dois models. |
| Como as ocorrências de `instance.is_active = False` em sub-recursos sem ViewSet próprio (`AcionistaCliente`, `AcionistaFornecedor`, dentro de `@action` em `ClienteViewSet`/`FornecedorViewSet`) entram no soft delete auditável? | Ganham `deleted_at`/`deleted_by` manualmente dentro da própria `@action` (não passam por `perform_destroy` — não são `destroy()` de ViewSet), usando o mesmo padrão: `from django.utils import timezone; acionista.deleted_at = timezone.now(); acionista.deleted_by = request.user; acionista.is_active = False; acionista.save(update_fields=[...])`. | São ações customizadas (`@action(detail=True, methods=['patch', 'delete'])`), não o `destroy()` padrão do `ModelViewSet` — o `AuditMixin` não entra em ação neles automaticamente, mas o pedido exige rastreabilidade uniforme ("quem apagou esse registro"), então precisam do mesmo tratamento manual. |
| Serializers — como expor `created_by`/`updated_by` sem repetir `source='created_by.nome_completo'` em ~30 arquivos? | Novo `common/serializers.py` com `AuditFieldsMixin`:<br>`created_by_nome = serializers.CharField(source='created_by.nome_completo', read_only=True, default='')`<br>`updated_by_nome = serializers.CharField(source='updated_by.nome_completo', read_only=True, default='')`<br>Cada serializer de model que herda `BaseModel` passa a herdar também `AuditFieldsMixin` e adiciona `'created_by_nome', 'updated_by_nome'` em `Meta.fields` (nunca em `read_only_fields` explicitamente — já são `read_only` por serem `CharField` sem `source` gravável). | Mesmo racional do `AuditMixin` — 1 implementação central, aplicada por herança, em vez de copiar o padrão já visto em `produtos/serializers.py` (`criado_por_nome`) dezenas de vezes. |
| Consolidação de `criado_por` — uma migration por app ou uma só? | **Uma migration de schema + uma `RunPython` por app afetado** (separadas, na mesma leva): 1ª migration adiciona os 4 campos novos de auditoria (via `BaseModel` abstrato, gera automaticamente em cada app que tem model concreto herdando `BaseModel`); 2ª migration (só nos apps com `criado_por` legado) faz `RunPython` copiando `criado_por_id → created_by_id` e depois remove o campo `criado_por` numa migration **seguinte** (nunca na mesma transação do `RunPython` de cópia — se der rollback, o dado de origem ainda existe). | Padrão já usado no projeto (ex.: Manutenção #9, `DIV04/05`: `0003_*_basemodel.py` + `0004_*_basemodel_cleanup.py` em dois passos). Reduz risco de perda de dado se uma migration falhar no meio. |

### 2.1 Nomenclatura final por model (resumo)

Todo model que herda `BaseModel` ganha, além de `created_at`/`updated_at`/`is_active` (inalterados):
```python
created_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='criado por', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='atualizado por', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
deleted_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='excluído por', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
deleted_at = models.DateTimeField('excluído em', null=True, blank=True)
```

### 2.2 `common/mixins.py` (novo arquivo)

```python
from django.utils import timezone


class AuditMixin:
    """
    Aplicar em todo ViewSet cujo model herda common.models.BaseModel.
    perform_create/perform_update/perform_destroy gravam quem fez o quê.
    NUNCA remove o registro do banco (instance.delete()) — regra absoluta
    da fábrica (soft delete em todos os models).
    """

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    def perform_destroy(self, instance):
        instance.deleted_at = timezone.now()
        instance.deleted_by = self.request.user
        instance.is_active = False
        instance.save(update_fields=['deleted_at', 'deleted_by', 'is_active', 'updated_at'])
```
Onde um ViewSet já tem `perform_create`/`perform_update` com lógica própria (ex.: `rh.ColaboradorViewSet`, `accounts.UserViewSet`), **não substituir** — apenas garantir que o `serializer.save(...)` existente passe a incluir `created_by=self.request.user` (em `perform_create`) ou `updated_by=self.request.user` (em `perform_update`) junto dos demais kwargs já salvos, chamando o mixin via `super().perform_create(serializer)` quando a lógica própria permitir, ou replicando a linha inline quando o fluxo tiver `return` antecipado (caso de `ColaboradorViewSet.perform_create`, que tem 2 caminhos de `serializer.save()`).

### 2.3 `BaseModel` com manager próprio

```python
class BaseModelManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class BaseModel(models.Model):
    created_at = models.DateTimeField('criado em', auto_now_add=True)
    updated_at = models.DateTimeField('atualizado em', auto_now=True)
    is_active = models.BooleanField('ativo', default=True)
    created_by = models.ForeignKey(..., related_name='+')
    updated_by = models.ForeignKey(..., related_name='+')
    deleted_by = models.ForeignKey(..., related_name='+')
    deleted_at = models.DateTimeField('excluído em', null=True, blank=True)

    objects = BaseModelManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True
```
**Atenção Forge:** declarar `all_objects` **depois** de `objects` não altera qual é o "default manager" do Django (é sempre o primeiro declarado na classe — `objects`), que é exatamente o comportamento desejado (ViewSets/serializers usam `objects` sem saber que mudou; Admin usa `all_objects` explicitamente).

### 2.4 `common/admin.py` (novo arquivo)

```python
class AuditModelAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        return self.model.all_objects.all()
```
Toda classe em `administrativo/admin.py`, `agendamento/admin.py`, `clientes/admin.py`, `compras/admin.py`, `financeiro/admin.py` e qualquer outro `admin.py` de model que herde `BaseModel` troca `admin.ModelAdmin` → `common.admin.AuditModelAdmin` no `class XAdmin(admin.ModelAdmin):`. `accounts/admin.py` (`UserAdmin(BaseUserAdmin)`) **não entra** — `User` não herda `BaseModel`.

### 2.5 `financeiro.LivroCaixa` — tratamento especial

```python
class LivroCaixa(models.Model):
    ...
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')  # era criado_por
```
`financeiro/signals.py::_gerar_lancamento(..., criado_por=None)` → renomear parâmetro e uso para `created_by`; as 3 chamadas internas (`criado_por=instance.criado_por`) passam a ler o campo já renomeado do model de origem (`Receita.created_by`, `Despesa.created_by`, `EstornoReceita.created_by`).

---

## 3. Requisitos Funcionais (RF) — Backend

- **RF-01** — `common/models.py`: `BaseModel` ganha `created_by`, `updated_by`, `deleted_by` (FK `settings.AUTH_USER_MODEL`, `null=True, blank=True, on_delete=models.SET_NULL, related_name='+'`) e `deleted_at` (`DateTimeField(null=True, blank=True)`), conforme 2.1.
- **RF-02** — `common/models.py`: `BaseModelManager` filtra `deleted_at__isnull=True`; `BaseModel.objects = BaseModelManager()`; `BaseModel.all_objects = models.Manager()`, conforme 2.3.
- **RF-03** — `common/mixins.py` (novo): `AuditMixin` com `perform_create`/`perform_update`/`perform_destroy`, conforme 2.2.
- **RF-04** — `common/admin.py` (novo): `AuditModelAdmin`, conforme 2.4.
- **RF-05** — `common/serializers.py` (novo): `AuditFieldsMixin` com `created_by_nome`/`updated_by_nome`, conforme a tabela de decisões (seção 2).
- **RF-06** — Aplicar `AuditMixin` em **todos** os ViewSets listados nas seções 1.4-(A) e 1.4-(B) (lista completa na seção 8 — "Arquivos a modificar"). Em cada um: adicionar `AuditMixin` como primeira classe-base (`class XViewSet(AuditMixin, ModelViewSet):`); remover `destroy()` sobrescrito que só fazia `is_active=False` (grupo A); onde já existia `perform_create`/`perform_update`/`perform_destroy` próprio, incorporar a gravação de `created_by`/`updated_by`/(`deleted_at`+`deleted_by`) sem perder a lógica existente (ver exceções em RF-07 a RF-10).
- **RF-07 (exceção)** — `accounts.UserViewSet`: mantém `destroy()` próprio (chama `_bloquear_edicao_superadmin` antes), mas troca o corpo de `instance.is_active = False; instance.save(update_fields=['is_active'])` por `self.perform_destroy(instance)`, delegando ao `AuditMixin`. `perform_update` já existe (`_bloquear_edicao_superadmin` + `serializer.save()`) — troca `serializer.save()` por `serializer.save(updated_by=self.request.user)`.
- **RF-08 (exceção)** — `rh.ColaboradorViewSet`: `perform_create` tem 2 caminhos (`criar_usuario` true/false) — ambos os `serializer.save()` (um direto, outro dentro do `transaction.atomic()`) passam a `serializer.save(created_by=self.request.user)`. `perform_update` (RF-04 da Manutenção #45, já existe) — mesmo tratamento com `updated_by`.
- **RF-09 (exceção)** — ViewSets que já tinham `perform_create` setando `criado_por=self.request.user` (lista completa na seção 1.3) trocam o kwarg para `created_by=self.request.user` — é o mesmo lugar onde `AuditMixin.perform_create` seria chamado, então **o override existente é removido** e passa a vir só do `AuditMixin` (não sobra código duplicado).
- **RF-10 (exceção)** — `financeiro.LivroCaixaViewSet.perform_create`: **não** recebe `AuditMixin` (não herda `BaseModel`) — só troca `criado_por=self.request.user` → `created_by=self.request.user`.
- **RF-11** — Renomear campo `criado_por` → `created_by` nos 16 pontos da tabela da seção 1.3 (14 em models que herdam `BaseModel` — nesses casos o campo antigo é **substituído** pelo `created_by` herdado do `BaseModel`, não duplicado — mais `financeiro.LivroCaixa`, tratamento especial 2.5). Atualizar todas as leituras/escritas listadas em `financeiro/signals.py`, `financeiro/services.py`, `financeiro/conciliacao_service.py`, `financeiro/management/commands/conciliar_extrato.py`, `pdv/services.py`, `compras/signals.py` (`instance.criado_por` → `instance.created_by`).
- **RF-12** — `produtos/serializers.py::ComboSerializer`: `criado_por_nome` (`source='criado_por.nome_completo'`) → migra para o padrão `AuditFieldsMixin` (`created_by_nome`); remove `'criado_por'` de `Meta.fields`/`read_only_fields`, adiciona `'created_by_nome', 'updated_by_nome'`.
- **RF-13** — `compras.ItemCompra` e `produtos.ItemCombo` passam a herdar `BaseModel` em vez de `models.Model` puro (sem remover os comentários explicando por que não tinham soft delete próprio antes — atualizar o comentário para refletir que agora herdam, mas continuam sem `ViewSet`/ação de delete própria).
- **RF-14** — Serializers de **todo** model que herda `BaseModel` (lista completa seção 8) ganham `AuditFieldsMixin` + `'created_by_nome', 'updated_by_nome'` em `Meta.fields`. Campos crus `created_by`/`updated_by`/`deleted_by`/`deleted_at` **nunca** entram em `Meta.fields` como graváveis — se precisar expô-los (ex.: para o rodapé do frontend mostrar data), expor só via `created_at`/`updated_at` (já existentes) + os `_nome` novos; `deleted_at`/`deleted_by` não são expostos (registro excluído não aparece mais pra API de qualquer forma, RF-02).
- **RF-15** — Sub-recursos sem `ViewSet` próprio que fazem soft delete manual via `@action` (`AcionistaCliente` em `clientes/views.py`, `AcionistaFornecedor` em `fornecedores/views.py`) ganham `deleted_at`/`deleted_by` no mesmo bloco que já seta `is_active = False`, conforme decisão da seção 2.
- **RF-16** — `common/admin.py` novo; os `admin.py` de `administrativo`, `agendamento`, `clientes`, `compras`, `financeiro` (e demais apps com `admin.py` registrando model `BaseModel` — Forge confirma com `grep -rl "@admin.register" backend/*/admin.py` antes de editar) trocam a classe-base para `AuditModelAdmin`.

---

## 4. Requisitos Funcionais (RF) — Frontend

- **RF-17** — Novo componente `frontend/src/components/ui/AuditFooter.jsx`:
  ```jsx
  export default function AuditFooter({ item }) {
    if (!item?.created_at) return null
    const fmt = (d) => d ? new Date(d).toLocaleDateString('pt-BR') : ''
    return (
      <p className="mt-4 text-xs text-gray-400 dark:text-slate-500 border-t border-gray-100 dark:border-navy-700 pt-3">
        Criado por {item.created_by_nome || '—'} em {fmt(item.created_at)}
        {item.updated_at && item.updated_at !== item.created_at && (
          <> · Alterado por {item.updated_by_nome || '—'} em {fmt(item.updated_at)}</>
        )}
      </p>
    )
  }
  ```
  Sem lib de componentes nova (regra do pedido) — reaproveita só `Tailwind` já em uso, mesmo padrão dark mode (`navy-*`) da Manutenção #31.
- **RF-18** — `components/ui/ResourceCrud.jsx`: dentro do formulário do modal de edição (quando `editingId` não é `null` — ou seja, só em edição, nunca em criação de registro novo, que ainda não tem `created_by`), renderizar `<AuditFooter item={items.find(i => i.id === editingId)} />` antes dos botões de ação. Isso propaga o rodapé automaticamente para as telas que já consomem `ResourceCrud` (`Usuarios`, `Administrativo`, `Pagamentos`, `Portal`, `Agendamento`, `Rh`) sem editar cada uma.
- **RF-19** — Páginas com modal próprio (não usam `ResourceCrud`) ganham o mesmo `<AuditFooter item={...} />` manualmente, dentro do `<Modal>` de edição, antes dos botões `Cancelar`/`Salvar`: `Clientes.jsx` (modal de Cliente), `Fornecedores.jsx` (modal de Fornecedor), `Produtos.jsx` (modal de Produto e modal de Combo), `Vendas.jsx` (modal de Orçamento e modal de Pedido), `Financeiro.jsx` (modais de Conta/Categoria/Aporte/Receita/Despesa/Padrão Seguro Conciliação), `Compras.jsx` (modal de Compra), `Marketing.jsx` (modal de Campanha/Lead). Em todos, só renderizar quando `editingId` estiver setado (mesma regra do RF-18).
- **RF-20** — Nenhum campo novo (`created_by`, `updated_by`, `deleted_at`, `deleted_by`) é exposto como **input editável** em nenhum formulário — são só leitura, consumidos pelo `AuditFooter` a partir do objeto já carregado pela API (`created_by_nome`/`updated_by_nome`/`created_at`/`updated_at`).

---

## 5. Regras de Negócio (RN)

- **RN-01** — `is_active=False` sem `deleted_at` preenchido = registro **desativado** (reversível, ex.: toggle de "Cargo inativo"). `deleted_at` preenchido = registro **excluído** (via `destroy()`/`DELETE`) — sempre acompanhado de `is_active=False` também (RF-03 do `AuditMixin`), mas a recíproca não é verdadeira.
- **RN-02** — `deleted_at`/`deleted_by` só são preenchidos pelo fluxo de exclusão (`perform_destroy` do `AuditMixin` ou tratamento manual equivalente nos sub-recursos RF-15). Nenhuma outra rotina (toggle de `is_active` por uma tela de "ativar/desativar", se existir) deve tocar nesses dois campos.
- **RN-03** — `created_by`/`updated_by`/`deleted_by` nunca são graváveis via payload do cliente — sempre atribuídos pelo backend a partir de `request.user` (RF-06 a RF-10). Um serializer que incluísse esses campos em `fields` sem marcar como calculado/`read_only` permitiria um usuário forjar autoria de outro usuário — bloqueado por desenho (RF-14, campos crus nunca em `Meta.fields`).
- **RN-04** — `objects.all()`/`objects.filter(...)` (manager padrão, RF-02) nunca retorna registro com `deleted_at` preenchido, para nenhum model que herde `BaseModel` — inclusive em querysets que hoje filtram manualmente por `is_active=True` (o filtro de `deleted_at` se soma, não substitui).
- **RN-05** — `all_objects` (manager sem filtro) só é usado pelo Django Admin (`AuditModelAdmin`, RF-16). Nenhum `ViewSet`/`serializer`/`service` de produção deve usar `all_objects` — se precisar ver excluído por algum motivo de negócio futuro (lixeira), é nova manutenção (explicitamente fora de escopo).
- **RN-06** — Signals que gravam `LivroCaixa`/`Receita`/`Despesa`/`EstornoReceita`/`RecebivelCartao`/`MovimentoEstoque` a partir de outro objeto (ex.: `compras/signals.py` gerando `Despesa` a partir de `Compra`) continuam dentro de `transaction.atomic()` (já é o padrão do projeto) — `created_by` repassado é sempre o autor da ação original (ex.: quem criou a `Compra`), nunca `None` nem o usuário de um processo em lote sem autor real (`conciliar_extrato.py` mantém `created_by=None` quando é comando de management sem usuário — RN já documentada no código-fonte atual).
- **RN-07** — Nenhum model novo ganha `created_by`/`updated_by`/`deleted_by`/`deleted_at` fora do que já herda `BaseModel` — `accounts.User` (não herda `BaseModel`, é `AbstractBaseUser`) fica de fora, assim como qualquer model de choices/lookup sem persistência própria.

---

## 6. Migrations — plano de execução

1. **Gerar em container efêmero** (`docker run --rm ... makemigrations`), **revisando antes de aplicar**: cortar qualquer `AlterField` de ruído que o Django gerar por reordenação de campo (comum quando se adiciona campo no meio de uma classe abstrata) — manter só `AddField`.
2. **Ordem por app** (schema primeiro, depois dado, depois cleanup — nunca no mesmo arquivo):
   - `common` não gera migration própria (é abstrato, sem `db_table`) — o `AddField` cai em cada app concreto.
   - Para os apps da tabela 1.2: 1 migration `000X_baseauditoria.py` com os 4 `AddField` (`created_by`, `updated_by`, `deleted_by`, `deleted_at`) em cada model concreto do app.
   - Para os apps com `criado_por` legado (`financeiro`, `pdv`, `vendas`, `pagamentos`, `compras`, `administrativo`, `agendamento`, `produtos`): migration seguinte `000X_consolida_criado_por.py` com `RunPython` copiando `criado_por_id → created_by_id` por model afetado (usar `.update()` em lote, não `save()` por linha, para não disparar signals indevidos em volumes grandes).
   - Migration seguinte `000X_remove_criado_por.py` com `RemoveField('criado_por')` — só depois da `RunPython` ter rodado e sido confirmada (nunca no mesmo arquivo da cópia, RN da seção 2).
   - `financeiro`: migration extra renomeando `LivroCaixa.criado_por` → `created_by` (`RenameField`, já que não é `BaseModel`, é rename simples de FK, sem `RunPython` de cópia necessário — `RenameField` preserva o dado).
   - `compras`/`produtos`: migration convertendo `ItemCompra`/`ItemCombo` de `models.Model` para `BaseModel` (`AddField` dos 7 campos novos: `created_at`, `updated_at`, `is_active`, `created_by`, `updated_by`, `deleted_by`, `deleted_at` — com `created_at`/`updated_at` precisando de `preserve_default=False` + valor default temporário para linhas já existentes, padrão já usado na Manutenção #9).
3. **Rodar `migrate` do zero em banco limpo** (ambiente efêmero) **e** sobre **cópia do banco atual** (snapshot de produção restaurado em container de teste) — confirmar 0 erro nos dois cenários antes de aplicar em produção.
4. Após `migrate`: `makemigrations --check --dry-run` deve retornar 0 pendências.

---

## 7. Lista exata de arquivos a criar

```
backend/common/mixins.py           — AuditMixin (novo)
backend/common/admin.py            — AuditModelAdmin (novo)
backend/common/serializers.py      — AuditFieldsMixin (novo)
backend/common/tests_mixins.py     — testes do AuditMixin (create/update/destroy) e do manager (deleted_at some da listagem)
frontend/src/components/ui/AuditFooter.jsx  — rodapé "Criado por X em ... · Alterado por Y em ..." (novo)

Migrations novas (uma leva por app, nomes exatos a confirmar no makemigrations real):
backend/administrativo/migrations/000X_baseauditoria.py (+ consolida/remove criado_por)
backend/agendamento/migrations/000X_baseauditoria.py (+ consolida/remove criado_por)
backend/clientes/migrations/000X_baseauditoria.py
backend/compras/migrations/000X_baseauditoria.py (+ consolida/remove criado_por + ItemCompra→BaseModel)
backend/financeiro/migrations/000X_baseauditoria.py (+ consolida/remove criado_por + LivroCaixa rename)
backend/fornecedores/migrations/000X_baseauditoria.py
backend/marketing/migrations/000X_baseauditoria.py
backend/pagamentos/migrations/000X_baseauditoria.py (+ consolida/remove criado_por)
backend/pdv/migrations/000X_baseauditoria.py (+ consolida/remove criado_por)
backend/portal/migrations/000X_baseauditoria.py
backend/produtos/migrations/000X_baseauditoria.py (+ consolida/remove criado_por + ItemCombo→BaseModel)
backend/rh/migrations/000X_baseauditoria.py
backend/vendas/migrations/000X_baseauditoria.py (+ consolida/remove criado_por)
```

## 8. Lista exata de arquivos a modificar

```
backend/common/models.py           — BaseModel + BaseModelManager (RF-01/RF-02)

# ViewSets — adicionar AuditMixin, remover destroy() duplicado (RF-06 a RF-10):
backend/accounts/views.py          — UserViewSet (RF-07, exceção)
backend/administrativo/views.py    — TipoDocumentoViewSet, DocumentoViewSet
backend/agendamento/views.py       — AgendaViewSet, CompromissoViewSet
backend/clientes/views.py          — ClienteViewSet (+ RF-15 acionistas)
backend/compras/views.py           — CompraViewSet (grupo B — já usa perform_destroy)
backend/financeiro/views.py        — CategoriaViewSet, ContaViewSet, AporteViewSet, ReceitaViewSet,
                                      DespesaViewSet, LivroCaixaViewSet (RF-10, exceção — sem AuditMixin),
                                      PadraoSeguroConciliacaoViewSet (grupo B)
backend/fornecedores/views.py      — FornecedorViewSet (+ RF-15 acionistas)
backend/marketing/views.py         — CampanhaViewSet, LeadViewSet
backend/pagamentos/views.py        — MetodoPagamentoViewSet, CobrancaViewSet, ParcelaViewSet
backend/pdv/views.py               — SessaoCaixaViewSet, VendaViewSet
backend/portal/views.py            — AcessoPortalClienteViewSet (grupo B)
backend/produtos/views.py          — ProdutoViewSet, ComboViewSet
backend/rh/views.py                — CargoViewSet, ColaboradorViewSet (RF-08, exceção), FolhaPagamentoViewSet, RegistroFeriasViewSet
backend/vendas/views.py            — OrcamentoViewSet, PedidoViewSet, ItemPedidoViewSet

# Models — campo criado_por → herança BaseModel / rename (RF-11):
backend/financeiro/models.py       — Conta, Aporte, Receita, EstornoReceita, Despesa, ConciliacaoExtrato,
                                      PadraoSeguroConciliacao (remove criado_por próprio); LivroCaixa (rename, 2.5)
backend/pdv/models.py              — RecebivelCartao
backend/vendas/models.py           — Orcamento, Pedido
backend/pagamentos/models.py       — Cobranca
backend/compras/models.py          — Compra; ItemCompra (herda BaseModel, RF-13)
backend/administrativo/models.py   — Documento
backend/agendamento/models.py      — Compromisso
backend/produtos/models.py         — MovimentoEstoque, Combo; ItemCombo (herda BaseModel, RF-13)

# Services/signals — criado_por → created_by (RF-11):
backend/financeiro/signals.py
backend/financeiro/services.py
backend/financeiro/conciliacao_service.py
backend/financeiro/management/commands/conciliar_extrato.py
backend/pdv/services.py
backend/compras/signals.py

# Serializers — AuditFieldsMixin em todo serializer de model BaseModel (RF-12/RF-14):
backend/administrativo/serializers.py
backend/agendamento/serializers.py
backend/clientes/serializers.py
backend/compras/serializers.py
backend/financeiro/serializers.py
backend/fornecedores/serializers.py
backend/marketing/serializers.py
backend/pagamentos/serializers.py
backend/pdv/serializers.py
backend/portal/serializers.py
backend/produtos/serializers.py    — ComboSerializer migra criado_por_nome → created_by_nome (RF-12)
backend/rh/serializers.py
backend/vendas/serializers.py

# Admin — troca base para AuditModelAdmin (RF-16):
backend/administrativo/admin.py
backend/agendamento/admin.py
backend/clientes/admin.py
backend/compras/admin.py
backend/financeiro/admin.py
(demais admin.py que registrem model BaseModel — confirmar com grep antes de editar)

# Testes:
backend/produtos/tests.py          — ajustar assertEqual(combo.criado_por, ...) → created_by (RF-12)
backend/*/tests.py                 — testes novos de create/update/destroy cobrindo created_by/updated_by/deleted_at/deleted_by
                                      por app tocado (ao menos 1 teste de ciclo completo por app)

# Frontend:
frontend/src/components/ui/ResourceCrud.jsx  — renderiza AuditFooter no modal de edição (RF-18)
frontend/src/pages/Clientes.jsx              — AuditFooter no modal (RF-19)
frontend/src/pages/Fornecedores.jsx          — AuditFooter no modal (RF-19)
frontend/src/pages/Produtos.jsx              — AuditFooter nos modais de Produto e Combo (RF-19)
frontend/src/pages/Vendas.jsx                — AuditFooter nos modais de Orçamento e Pedido (RF-19)
frontend/src/pages/Financeiro.jsx            — AuditFooter nos modais de Conta/Categoria/Aporte/Receita/Despesa/PadraoSeguro (RF-19)
frontend/src/pages/Compras.jsx               — AuditFooter no modal de Compra (RF-19)
frontend/src/pages/Marketing.jsx             — AuditFooter nos modais de Campanha/Lead (RF-19)
```

---

## 9. Critérios de Aceite (CA) — em produção, não estático

- **CA-01** — `POST /api/v1/clientes/` autenticado como usuário X cria um `Cliente` com `created_by=X`. Confirmar via `GET` subsequente (campo `created_by_nome` no payload de resposta).
- **CA-02** — `PATCH` no mesmo `Cliente` autenticado como usuário Y grava `updated_by=Y`, sem alterar `created_by` (continua `X`).
- **CA-03** — `DELETE` no mesmo `Cliente` autenticado como usuário Z: resposta `204`; registro some de `GET /api/v1/clientes/` (listagem); `GET /api/v1/clientes/{id}/` (detalhe direto) também passa a não encontrar (manager padrão filtra `deleted_at`); consulta direta no banco (`Cliente.all_objects.get(id=...)`) confirma `deleted_at` preenchido, `deleted_by=Z`, `is_active=False` — registro **continua existindo** no banco.
- **CA-04** — Contagem de `Receita` com `criado_por` preenchido antes da migration bate exatamente com a contagem de `created_by` preenchido depois (nenhuma linha perdida na consolidação) — repetir para `Despesa`, `Cobranca`, `Compra`, `Documento`, `Compromisso`, `MovimentoEstoque`, `Combo`, `RecebivelCartao`, `ConciliacaoExtrato`, `PadraoSeguroConciliacao`, `Orcamento`, `Pedido`, `Conta`, `Aporte`, `EstornoReceita`.
- **CA-05** — `showmigrations`/`makemigrations --check --dry-run`: 0 pendências em todos os apps após aplicar.
- **CA-06** — Django Admin (usuário SUPERADMIN): lista de `Cliente` (ou qualquer model com `AuditModelAdmin`) mostra registros com `deleted_at` preenchido; a mesma lista via API (`/api/v1/clientes/`) não mostra.
- **CA-07** — Nenhum serializer de `BaseModel` aceita `created_by`/`updated_by`/`deleted_by`/`deleted_at` no payload de `POST`/`PATCH` — enviar esses campos no corpo da requisição não tem efeito (valor real sempre vem do backend).
- **CA-08** — Frontend: editar um `Cliente` existente mostra o rodapé "Criado por {nome} em {data} · Alterado por {nome} em {data}" no modal; criar um `Cliente` novo (modal de criação) **não** mostra o rodapé (sem `created_at` ainda).
- **CA-09** — 365+ testes Django passando (0 falhas), incluindo os testes novos do `AuditMixin` (create/update/destroy, por app tocado) e da migração de `criado_por` (contagem antes/depois, CA-04).
- **CA-10** — `grep -rn "criado_por" backend/ frontend/src/` retorna 0 ocorrências de uso de negócio (só eventualmente em comentário histórico de migration antiga, que não deve ser editada retroativamente).

---

## 10. Fora de Escopo (nesta manutenção)

- Tela de "lixeira"/restaurar excluídos (fica para manutenção futura — explicitado no pedido).
- Log de histórico campo a campo (auditoria "antes/depois" de cada alteração — explicitado no pedido; esta manutenção só registra quem/quando, não o quê mudou).
- As outras 4 manutenções do pacote [NUCLEO] (2/5 a 5/5) — esta é fase única, independente.
- Qualquer UI de "quem excluiu" fora do rodapé discreto já especificado (RF-17 a RF-19) — sem relatório dedicado, sem filtro de auditoria na listagem.

---

## 11. Riscos e Dependências

- **Risco alto**: volume de arquivos tocados (praticamente todo app do backend + várias páginas do frontend) — recomenda-se ao Forge/Loom dividir a execução por lote de apps (ex.: `common` + `clientes`/`fornecedores` primeiro, validar, depois os demais) em vez de uma única passada, para isolar falha de migration a um app por vez.
- **Risco médio**: `RunPython` de consolidação de `criado_por` em `financeiro` toca 8 models no mesmo app — se uma falhar a transação do app inteiro reverte; testar isoladamente cada `RunPython` por model antes de agrupar.
- **Dependência**: `common.BaseModelManager` muda o comportamento de **todo** `Model.objects.all()/.filter()` do projeto — qualquer código (signals, services, management commands) que hoje dependa de ver um registro `deleted_at` (nenhum caso encontrado nesta análise, mas Forge deve grep `\.objects\.` nos services/signals dos apps antes de aplicar, por segurança) precisa trocar para `all_objects` explicitamente.
- **Dependência**: `AuditModelAdmin` exige que `self.model` tenha `all_objects` — só funciona em model que herda `BaseModel`; não aplicar em `accounts.UserAdmin`.
