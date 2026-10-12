# Especificação Hotfix — Manutenção #63

**Sistema:** UidCore (OS #7)
**Pacote:** [NUCLEO 2/5] — melhoria de núcleo vinda da análise do NosFluir (Studio Fluir, papéis Administrador/Professor/Financeiro/Recepcionista via Grupos Django). Fase única, independente das outras do pacote [NUCLEO] (não depende da #62 nem bloqueia #64/#65).
**Módulo:** `accounts` (novos valores de `PerfilUsuario`) + `common/permissions.py` (novas permission classes) + `financeiro`, `compras`, `agendamento`, `clientes` (views/permissions) + frontend (`authStore`, `Sidebar`, `routes`, `Usuarios.jsx`)
**Tipo:** `feature_grande` — toca RBAC de núcleo (`PerfilUsuario`), não é tela isolada
**Requer aprovação comercial:** não — hardening interno de RBAC, sem novo módulo cobrável
**Analista:** leitura de código confirmada em `backend/accounts/models.py`, `backend/accounts/serializers.py`, `backend/accounts/views.py`, `backend/common/permissions.py`, `backend/common/mixins.py`, `backend/common/models.py`, `backend/financeiro/views.py` (todas as 804 linhas), `backend/financeiro/urls.py`, `backend/compras/views.py`, `backend/fornecedores/views.py`, `backend/pagamentos/views.py`, `backend/clientes/views.py`, `backend/rh/views.py`, `backend/pdv/views.py`, `backend/marketing/views.py`, `backend/agendamento/views.py`, `backend/agendamento/models.py`, `backend/agendamento/serializers.py`, `backend/agendamento/urls.py`, `backend/core/urls.py`, `backend/core/settings.py` (`DEFAULT_PERMISSION_CLASSES`), migrations de `accounts`/`agendamento`/`pagamentos`/`compras`/`fornecedores`/`clientes`, `frontend/src/stores/authStore.js`, `frontend/src/components/layout/Sidebar.jsx`, `frontend/src/routes/index.jsx`, `frontend/src/pages/Usuarios.jsx`, `frontend/src/pages/Dashboard.jsx`, `frontend/src/pages/Financeiro.jsx` (grep de todas as chamadas a `/financeiro/*`), `frontend/src/components/ui/Select.jsx`/`ResourceCrud.jsx`.

---

## 1. Diagnóstico confirmado (leitura de código)

### 1.1 Estado atual do RBAC (Manutenção #60 — intacto, não refazer)

```python
# backend/accounts/models.py
class PerfilUsuario(models.TextChoices):
    ADMIN = 'ADMIN', 'Admin'
    OPERACIONAL = 'OPERACIONAL', 'Operacional'
    MARKETING = 'MARKETING', 'Marketing'
    SUPERADMIN = 'SUPERADMIN', 'Superadmin'
```
`User.perfil` é `CharField(max_length=12, ...)` — `'PROFISSIONAL'` tem exatamente 12 caracteres, cabe sem alterar `max_length`.

`User.tem_acesso_total` (propriedade, única fonte de "acesso total"): `is_staff or perfil in (ADMIN, SUPERADMIN)`. **Não será alterada** — `FINANCEIRO`/`PROFISSIONAL` nunca entram nela.

`common/permissions.py` hoje:
```python
class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.tem_acesso_total)

class IsOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj == request.user

class IsMarketing(BasePermission):
    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and (u.perfil == 'MARKETING' or u.tem_acesso_total))
```
`IsMarketing` é o padrão a clonar — grant-style, `perfil == X OR tem_acesso_total`, composável com `|` (confirmado em uso real: `marketing/views.py` → `permission_classes = [IsAdmin | IsMarketing]`).

### 1.2 Mapa de permissão por ViewSet/view hoje (antes desta manutenção)

| App | View | `permission_classes` hoje | Fonte |
|---|---|---|---|
| financeiro | `CategoriaViewSet`, `ContaViewSet`, `AporteViewSet`, `ReceitaViewSet`, `DespesaViewSet`, `LivroCaixaViewSet`, `ConciliacaoViewSet`, `PadraoSeguroConciliacaoViewSet` | `[IsAdmin]` | views.py L40,53,131,144,196,262,699,803 |
| financeiro | `ReceitaViewSet.estornar` (`@action`), `DespesaViewSet.estornar_despesa` (`@action`), `LivroCaixaViewSet.estornar` (`@action`) | **`permission_classes=[IsAdmin]` declarado no próprio `@action`** — sobrescreve o da classe | views.py L165, L221 (via nome `estornar_despesa`), L270 |
| financeiro | `fluxo_caixa`, `dre`, `dashboard_financeiro`, `balanco_patrimonial`, `fluxo_projetado`, `indicadores_cfo`, `inferir_categoria` (`@api_view`) | nenhum decorator `@permission_classes` → cai no `DEFAULT_PERMISSION_CLASSES` global = `IsAuthenticated` puro | views.py L336-468, `settings.py` L118-120 |
| compras | `CompraViewSet` | `[IsAdmin]` | compras/views.py L25 |
| pagamentos | `MetodoPagamentoViewSet`, `CobrancaViewSet`, `ParcelaViewSet` | nenhum `permission_classes` → `IsAuthenticated` puro (qualquer perfil autenticado já acessa) | pagamentos/views.py |
| fornecedores | `FornecedorViewSet` | nenhum `permission_classes` → `IsAuthenticated` puro | fornecedores/views.py |
| clientes | `ClienteViewSet` | nenhum `permission_classes` → `IsAuthenticated` puro (qualquer perfil autenticado, CRUD completo) | clientes/views.py |
| agendamento | `AgendaViewSet`, `CompromissoViewSet` | nenhum `permission_classes` → `IsAuthenticated` puro, sem filtro de queryset | agendamento/views.py |
| rh | `CargoViewSet`, `ColaboradorViewSet`, `FolhaPagamentoViewSet`, `RegistroFeriasViewSet` | `[IsAdmin]` | rh/views.py |
| accounts | `UserViewSet` | `[IsAdmin]` | accounts/views.py L21 |
| pdv | `SessaoCaixaViewSet`, `VendaViewSet` | `[IsAdmin]` | pdv/views.py |

**Nenhum ViewSet tocado nesta manutenção sobrescreve `get_permissions()`** (confirmado por leitura linha a linha de `financeiro/views.py`, `compras/views.py`, `pagamentos/views.py`, `fornecedores/views.py`, `clientes/views.py`, `agendamento/views.py`, `accounts/views.py`, `rh/views.py`). O aviso do pedido sobre "`get_permissions()` vence o `permission_classes` do `@action`" **não se aplica por esse mecanismo aqui** — mas existe a **mesma categoria de armadilha por outro caminho**: 3 `@action` em `financeiro/views.py` declaram `permission_classes=[IsAdmin]` **direto no decorator**, o que também vence o `permission_classes` da classe. Ver seção 2.4 — se só a classe for trocada para `IsAdmin | IsFinanceiro` e esses 3 `@action` forem esquecidos, `FINANCEIRO` ganha CRUD completo em Receita/Despesa/LivroCaixa mas recebe 403 especificamente em "estornar" (regressão parcial, bug real do mesmo tipo já visto na #60).

### 1.3 `dashboard_financeiro` é a tela HOME — não pode ser restringida

`frontend/src/pages/Dashboard.jsx` chama `GET /api/v1/financeiro/dashboard/` **incondicionalmente no `useEffect` de qualquer usuário logado** (é a rota `index`/`/dashboard`, destino padrão pós-login para todo perfil). Hoje esse endpoint é `IsAuthenticated` puro — `OPERACIONAL`/`MARKETING` já o acessam normalmente. Se fosse restringido a `IsAdmin | IsFinanceiro`, `OPERACIONAL`, `MARKETING` e o novo `PROFISSIONAL` passariam a ver a tela inicial quebrada ("Não foi possível carregar o painel") — regressão explicitamente proibida pelo pedido. **Decisão: `dashboard_financeiro` e `inferir_categoria` (utilitário de sugestão de texto, sem dado financeiro sensível, não listado no escopo) permanecem abertos (`IsAuthenticated`, sem mudança).** Os "403 em `/financeiro/*`" do critério de aceite se referem aos **recursos do módulo** citados no pedido — contas, receitas, despesas, livro-caixa, dre, balanço, fluxo, indicadores, conciliação — todos confirmados (grep em `frontend/src/pages/Financeiro.jsx`) como consumidos **somente** dentro da própria tela Financeiro, nunca pela Dashboard. Zero risco de regressão ao restringi-los.

### 1.4 `pagamentos` e `fornecedores`: por que **não** ganham `IsFinanceiro`

O pedido lista "pagamentos, compras e fornecedores" como acesso do `FINANCEIRO`, e pede para mapear esses apps. Mapeados — conclusão: **nenhuma mudança de permissão neles**, pelo motivo abaixo (documentado aqui para a próxima pessoa não reabrir a dúvida):

- Hoje ambos são `IsAuthenticated` puro, ou seja, `OPERACIONAL` e `MARKETING` **já** têm acesso de produção a eles (Sidebar sem `staffOnly`/flag nenhuma nos itens Pagamentos e Fornecedores).
- `FINANCEIRO` é um perfil autenticado → **já** satisfaz `IsAuthenticated` → já tem o acesso que o pedido pede, sem precisar de classe nova.
- Restringir para `IsAdmin | IsFinanceiro` bloquearia `OPERACIONAL`/`MARKETING`, que é regressão explicitamente proibida pelo critério de aceite ("OPERACIONAL e MARKETING sem regressão").
- `compras` é diferente: já era `IsAdmin` puro (`OPERACIONAL` **já não tinha** acesso — Sidebar já marca `staffOnly: true`). Abrir para `FINANCEIRO` aqui é estritamente aditivo, sem risco de regressão. Por isso só `compras` ganha `IsFinanceiro` entre os três.

### 1.5 `agendamento`/`clientes` não têm hoje nenhum conceito de "profissional responsável"

`Compromisso`/`Agenda` herdam `common.models.BaseModel`, que desde a Manutenção #62 já tem `created_by` (FK para `accounts.User`, `related_name='+'`, preenchido automaticamente pelo `AuditMixin.perform_create`). **Isso já basta para "próprios compromissos"** — não precisa de campo novo. Mas não existe nenhum campo que modele "agendas a que o profissional está vinculado" (ex.: agenda da Dra. Ana, mantida por uma recepcionista em nome dela) — precisa de campo novo em `Agenda` (seção 2.2).

`Cliente` (`clientes/views.py`) é `IsAuthenticated` puro, CRUD completo para qualquer perfil autenticado — inclusive o `PROFISSIONAL` novo teria, por padrão, permissão de editar/excluir cliente. O pedido pede leitura para `PROFISSIONAL`; **decisão: restringir só a escrita, só para o perfil `PROFISSIONAL` puro — todos os demais perfis mantêm exatamente o comportamento de hoje** (seção 2.4).

---

## 2. Especificação Backend

### 2.1 `accounts/models.py` — `PerfilUsuario`

```python
class PerfilUsuario(models.TextChoices):
    ADMIN = 'ADMIN', 'Admin'
    OPERACIONAL = 'OPERACIONAL', 'Operacional'
    MARKETING = 'MARKETING', 'Marketing'
    SUPERADMIN = 'SUPERADMIN', 'Superadmin'
    FINANCEIRO = 'FINANCEIRO', 'Financeiro'          # RF-01 (novo)
    PROFISSIONAL = 'PROFISSIONAL', 'Profissional'    # RF-01 (novo)
```
`User.tem_acesso_total` **não muda uma linha** (RN-01 — travas da #60 intactas: só `SUPERADMIN` concede/edita `SUPERADMIN`; `FINANCEIRO`/`PROFISSIONAL` não entram em `tem_acesso_total` sob nenhuma condição).

**Migration:** `backend/accounts/migrations/0005_alter_user_perfil_financeiro_profissional.py` — `AlterField` em `perfil` com o novo `choices` (mesmo padrão de `0003_alter_user_perfil.py` da Manutenção #60). Não precisa de `RunPython` (ninguém é promovido automaticamente — perfil novo é opt-in via tela Usuários).

### 2.2 `agendamento/models.py` — vínculo profissional↔agenda (RF-05)

```python
class Agenda(BaseModel):
    nome        = models.CharField(max_length=100, blank=True)
    descricao   = models.TextField(blank=True)
    cor         = models.CharField(max_length=7, default='#3B82F6')
    profissional = models.ForeignKey(            # novo (RF-05)
        settings.AUTH_USER_MODEL, verbose_name='profissional responsável',
        null=True, blank=True, on_delete=models.SET_NULL, related_name='agendas_vinculadas',
    )
```
**Decisão de projeto (Analista):** "agendas a que está vinculado" é modelado como **1 profissional responsável por agenda** (`Agenda.profissional`, nullable — agendas sem dono explícito continuam existindo, ex. "Agenda Geral" da recepção). Não é M2M — o pedido descreve o caso genérico (professor, terapeuta, esteticista, técnico) como "a agenda da pessoa", não "a agenda compartilhada por um time"; M2M ficaria fora do escopo mínimo necessário para o critério de aceite e seria over-engineering para a Fase única desta manutenção. Se um nicho futuro precisar de agenda com múltiplos profissionais, isso é "perfil específico de nicho" — explicitamente fora de escopo aqui.

`related_name='agendas_vinculadas'` (não `'+'`, diferente do padrão de `created_by`/`updated_by`/`deleted_by` do `BaseModel`) **de propósito** — precisamos consultar `user.agendas_vinculadas.all()` ao decidir o que um `PROFISSIONAL` vê.

**Migration:** `backend/agendamento/migrations/0007_agenda_profissional.py` (sequência atual: `0001` a `0006_remove_criado_por.py`).

### 2.3 `common/permissions.py` — novas classes

```python
from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsFinanceiro(BasePermission):
    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and (u.perfil == 'FINANCEIRO' or u.tem_acesso_total))


class IsProfissional(BasePermission):
    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and (u.perfil == 'PROFISSIONAL' or u.tem_acesso_total))


class BloqueiaEscritaDeProfissional(BasePermission):
    """
    RF-06 (Manutencao 63) — Cliente em leitura para PROFISSIONAL. Nao e o
    mesmo padrao de IsFinanceiro/IsProfissional (grant-style) porque aqui a
    regra e "nega escrita SO para esse perfil, mantem os demais exatamente
    como estao" -- nao daria pra compor so com | / ~ sobre um grant-style
    sem tambem bloquear quem tem tem_acesso_total (ADMIN/SUPERADMIN), que
    IsProfissional.has_permission tambem retorna True para eles. Consulta
    IsProfissional() diretamente (nao decorativo -- e o "alguem le
    IsProfissional" exigido pelo item 5 do pedido, com teste proprio).
    """
    def has_permission(self, request, view):
        u = request.user
        if not (u and u.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        eh_profissional_puro = (
            IsProfissional().has_permission(request, view)
            and not u.tem_acesso_total
            and u.perfil == 'PROFISSIONAL'
        )
        return not eh_profissional_puro
```

Mantém `IsAdmin`/`IsOwner`/`IsMarketing` existentes intactos (RN-02).

### 2.4 Views a alterar — lista exaustiva

#### `financeiro/views.py`

| View | De | Para |
|---|---|---|
| `CategoriaViewSet` | `[IsAdmin]` | `[IsAdmin \| IsFinanceiro]` |
| `ContaViewSet` | `[IsAdmin]` | `[IsAdmin \| IsFinanceiro]` |
| `AporteViewSet` | `[IsAdmin]` | `[IsAdmin \| IsFinanceiro]` |
| `ReceitaViewSet` | `[IsAdmin]` | `[IsAdmin \| IsFinanceiro]` |
| `ReceitaViewSet.estornar` (`@action`) | `permission_classes=[IsAdmin]` no decorator | `permission_classes=[IsAdmin \| IsFinanceiro]` — **não esquecer, é o ponto da seção 1.2** |
| `DespesaViewSet` | `[IsAdmin]` | `[IsAdmin \| IsFinanceiro]` |
| `DespesaViewSet.estornar_despesa` (`@action`) | `permission_classes=[IsAdmin]` no decorator | `permission_classes=[IsAdmin \| IsFinanceiro]` |
| `LivroCaixaViewSet` | `[IsAdmin]` | `[IsAdmin \| IsFinanceiro]` |
| `LivroCaixaViewSet.estornar` (`@action`) | `permission_classes=[IsAdmin]` no decorator | `permission_classes=[IsAdmin \| IsFinanceiro]` |
| `LivroCaixaViewSet.totais` (`@action`, sem override) | herda da classe | `IsAdmin \| IsFinanceiro` automaticamente — nenhuma mudança de código |
| `ConciliacaoViewSet` (+ `upload`, `itens`, `confirmar_item`, sem override em nenhum `@action`) | `[IsAdmin]` | `[IsAdmin \| IsFinanceiro]` |
| `PadraoSeguroConciliacaoViewSet` | `[IsAdmin]` | `[IsAdmin \| IsFinanceiro]` |
| `fluxo_caixa`, `dre`, `balanco_patrimonial`, `fluxo_projetado`, `indicadores_cfo` (`@api_view`) | sem decorator → `IsAuthenticated` global | **adicionar** `@permission_classes([IsAdmin \| IsFinanceiro])` — fecha gap pré-existente (hoje `MARKETING`/`OPERACIONAL`/`PROFISSIONAL` conseguiriam ver DRE/balanço/indicadores sem nunca ter sido avaliado — nada no histórico do projeto cobre isso) |
| `dashboard_financeiro`, `inferir_categoria` | sem decorator | **sem mudança** (seção 1.3) |

Import novo em `financeiro/views.py`: `from common.permissions import IsAdmin, IsFinanceiro` e `from rest_framework.decorators import action, api_view, permission_classes` (`permission_classes` do DRF ainda não está importado — só `action`/`api_view`).

#### `compras/views.py`

```python
from common.permissions import IsAdmin, IsFinanceiro
...
class CompraViewSet(AuditMixin, ModelViewSet):
    ...
    permission_classes = [IsAdmin | IsFinanceiro]   # era [IsAdmin]
```
`CompraViewSet.cancelar` (`@action`, sem override de `permission_classes`) herda automaticamente — nenhuma mudança adicional de código, mas **conferir no Sentinel** que o teste cobre `FINANCEIRO` chamando `cancelar` com sucesso (RN-05 do pedido: "self.action" explícito).

#### `pagamentos/views.py`, `fornecedores/views.py`

**Sem alteração** — decisão justificada na seção 1.4.

#### `agendamento/views.py` (RF-07/RF-08)

```python
from django.db.models import Q
from accounts.models import PerfilUsuario

class AgendaViewSet(AuditMixin, ModelViewSet):
    serializer_class = AgendaSerializer
    filter_backends = [SearchFilter]
    search_fields = ['nome']
    # permission_classes: SEM mudança (continua IsAuthenticated puro) —
    # restringir quebraria OPERACIONAL/MARKETING, que hoje gerenciam
    # agendas livremente (sem staffOnly no Sidebar). Regra do PROFISSIONAL
    # e so de ESCOPO DE DADOS (get_queryset), nao de permissao de entrada.

    def get_queryset(self):
        qs = Agenda.objects.filter(is_active=True).order_by('nome')
        u = self.request.user
        if u.perfil == PerfilUsuario.PROFISSIONAL and not u.tem_acesso_total:
            qs = qs.filter(Q(profissional=u) | Q(created_by=u))
        return qs


class CompromissoViewSet(AuditMixin, ModelViewSet):
    serializer_class = CompromissoSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['agenda', 'status', 'cliente']
    search_fields = ['titulo', 'descricao']
    ordering_fields = ['inicio', 'fim']
    # permission_classes: idem AgendaViewSet — sem mudanca.

    def get_queryset(self):
        qs = (
            Compromisso.objects.filter(is_active=True)
            .select_related('agenda', 'cliente')
            .order_by('inicio')
        )
        u = self.request.user
        if u.perfil == PerfilUsuario.PROFISSIONAL and not u.tem_acesso_total:
            qs = qs.filter(Q(created_by=u) | Q(agenda__profissional=u))
        return qs
```
**RN-03 (Should, não bloqueia o critério de aceite):** esta fase não impede um `PROFISSIONAL` de criar um `Compromisso` em uma `Agenda` de outro profissional (`POST`/`PATCH` não validam `agenda.profissional == request.user`) — o pedido só exige que ele **veja** o escopo certo (critério de aceite: "vê só os próprios compromissos"). Validar o vínculo também na escrita é recomendado para uma fase futura, registrado aqui para não se perder.

#### `clientes/views.py` (RF-06)

```python
from common.permissions import BloqueiaEscritaDeProfissional

class ClienteViewSet(AuditMixin, viewsets.ModelViewSet):
    serializer_class = ClienteSerializer
    permission_classes = [BloqueiaEscritaDeProfissional]   # era implícito (nenhum = IsAuthenticated)
    ...
```
Comportamento: leitura (`GET`) — qualquer autenticado, igual a hoje. Escrita (`POST`/`PATCH`/`PUT`/`DELETE`) — qualquer autenticado **exceto** `PROFISSIONAL` puro (sem `tem_acesso_total`), que recebe 403. `ADMIN`/`OPERACIONAL`/`MARKETING`/`FINANCEIRO`/`SUPERADMIN` mantêm CRUD completo — zero regressão.

As `@action` (`adicionar_historico`, `acionistas`, `acionista_detalhe`) são todas de escrita ou leitura condicionada ao método HTTP real da requisição — `BloqueiaEscritaDeProfissional` já cobre (`has_permission` olha `request.method`, que para essas actions é `POST`/`GET`/`PATCH`/`DELETE` reais). Confirmar no Sentinel que `PROFISSIONAL` recebe 403 em `POST /clientes/{id}/historico/` e `POST /clientes/{id}/acionistas/` também (são escrita).

#### `rh/views.py`, `accounts/views.py` (`UserViewSet`), `pdv/views.py`

**Sem alteração** — já são `[IsAdmin]` puro, `FINANCEIRO`/`PROFISSIONAL` já recebem 403 automaticamente (nem `IsFinanceiro` nem `IsProfissional` entram no OR). Cobrir com teste mesmo sem mudar código (RF-09).

### 2.5 Testes obrigatórios (RF-09 / item 5 do pedido — "nenhum perfil decorativo")

Novo arquivo ou extensão dos existentes, nos apps tocados. Nos dois sentidos (permite / bloqueia) para cada perfil novo:

| App | Caso | Esperado |
|---|---|---|
| `common` (novo `test_permissions.py` ou dentro de `accounts/tests.py`) | `IsFinanceiro().has_permission` com `perfil='FINANCEIRO'` | `True` |
| | `IsFinanceiro().has_permission` com `perfil='OPERACIONAL'`, sem `tem_acesso_total` | `False` |
| | `IsProfissional().has_permission` com `perfil='PROFISSIONAL'` | `True` |
| | `IsProfissional().has_permission` com `perfil='OPERACIONAL'` | `False` |
| | `BloqueiaEscritaDeProfissional` — `PROFISSIONAL` + `GET` | `True` |
| | `BloqueiaEscritaDeProfissional` — `PROFISSIONAL` + `POST` | `False` |
| | `BloqueiaEscritaDeProfissional` — `ADMIN` (`tem_acesso_total`) + `POST` | `True` |
| `financeiro` | usuário `FINANCEIRO` → `GET /api/v1/financeiro/contas/` | 200 |
| | usuário `FINANCEIRO` → `POST /api/v1/financeiro/receitas/{id}/estornar/` | 200/201 (não 403) |
| | usuário `OPERACIONAL`/`PROFISSIONAL`/`MARKETING` → `GET /api/v1/financeiro/contas/` | 403 |
| | usuário `PROFISSIONAL` → `GET /api/v1/financeiro/dre/` | 403 |
| | usuário `OPERACIONAL` → `GET /api/v1/financeiro/dashboard/` | 200 (sem regressão — não é recurso do módulo, seção 1.3) |
| `compras` | `FINANCEIRO` → `GET /api/v1/compras/` e `POST .../cancelar/` | 200 |
| | `OPERACIONAL`/`PROFISSIONAL` → `GET /api/v1/compras/` | 403 (sem regressão — já era assim) |
| `rh`/`accounts` | `FINANCEIRO` → `GET /api/v1/rh/colaboradores/` | 403 |
| | `FINANCEIRO` → `GET /api/v1/accounts/usuarios/` | 403 |
| | `PROFISSIONAL` → `GET /api/v1/rh/colaboradores/`, `GET /api/v1/accounts/usuarios/` | 403 |
| `agendamento` | `PROFISSIONAL` A cria `Compromisso` (vira `created_by=A`) → `GET /api/v1/agendamento/compromissos/` autenticado como A | retorna o compromisso criado por A |
| | `PROFISSIONAL` B (nunca criou nada, sem agenda vinculada) → mesma listagem | não retorna o compromisso de A |
| | `Agenda` com `profissional=A`, `Compromisso` nela criado por outro usuário (ex. recepcionista `OPERACIONAL`) → listagem de A | retorna (via `agenda__profissional=A`) |
| | `ADMIN`/`tem_acesso_total` → listagem | retorna todos, sem filtro |
| `clientes` | `PROFISSIONAL` → `GET /api/v1/clientes/` | 200, lista normal |
| | `PROFISSIONAL` → `POST /api/v1/clientes/` | 403 |
| | `OPERACIONAL`/`MARKETING`/`FINANCEIRO` → `POST /api/v1/clientes/` | 200/201 (sem regressão) |
| regressão geral | `OPERACIONAL`/`MARKETING` em todos os endpoints que já acessavam antes (`pagamentos`, `fornecedores`, `vendas`, `produtos`, `agendamento` sem filtro, `clientes` leitura+escrita exceto o caso acima) | mesmo status code de antes desta manutenção |

---

## 3. Especificação Frontend

### 3.1 `frontend/src/stores/authStore.js` — selectors centrais (RF-10)

Hoje só existe `selectTemAcessoTotal`. A duplicação que o pedido pede para eliminar: `Sidebar.jsx` calcula `perfil === 'MARKETING'` inline (linha 28) e `routes/index.jsx` recalcula a **mesma** condição inline dentro de `MarketingRoute` (linha ~40) — duas fontes da verdade para a mesma regra. Centralizar:

```js
export const selectTemAcessoTotal = (state) => Boolean(state.user?.tem_acesso_total)
export const selectPerfil = (state) => state.user?.perfil ?? null
export const selectPodeAcessarMarketing = (state) =>
  selectTemAcessoTotal(state) || state.user?.perfil === 'MARKETING'
export const selectPodeAcessarFinanceiro = (state) =>
  selectTemAcessoTotal(state) || state.user?.perfil === 'FINANCEIRO'   // novo (RF-10)
export const selectPodeAcessarProfissional = (state) =>
  selectTemAcessoTotal(state) || state.user?.perfil === 'PROFISSIONAL' // novo, uso futuro/consistência
```

### 3.2 `Sidebar.jsx`

```js
const navItems = [
  { to: '/dashboard', label: 'Dashboard', icon: '📊' },
  { to: '/clientes', label: 'Clientes', icon: '👥' },
  { to: '/fornecedores', label: 'Fornecedores', icon: '🏭' },
  { to: '/compras', label: 'Compras', icon: '🧾', requer: 'financeiro' },   // era staffOnly: true
  { to: '/vendas', label: 'Vendas', icon: '🛒' },
  { to: '/produtos', label: 'Produtos', icon: '📦' },
  { to: '/marketing', label: 'Marketing', icon: '📣', requer: 'marketing' }, // era marketingOnly: true
  { to: '/pagamentos', label: 'Pagamentos', icon: '💳' },
  { to: '/financeiro', label: 'Financeiro', icon: '💰', requer: 'financeiro' },   // novo filtro
  { to: '/conciliacao', label: 'Conciliação', icon: '🔄', requer: 'financeiro' }, // novo filtro
  { to: '/administrativo', label: 'Administrativo', icon: '📁' },
  { to: '/rh', label: 'RH', icon: '👔', requer: 'staff' },   // novo filtro — ja era IsAdmin no backend, Sidebar nao escondia
  { to: '/usuarios', label: 'Usuários', icon: '👤', requer: 'staff' },  // era staffOnly: true
  { to: '/agendamento', label: 'Agendamento', icon: '📅' },
  { to: '/portal', label: 'Portal do Cliente', icon: '🌐' },
]

export default function Sidebar({ collapsed, onToggle }) {
  const temAcessoTotal = useAuthStore(selectTemAcessoTotal)
  const podeMarketing = useAuthStore(selectPodeAcessarMarketing)
  const podeFinanceiro = useAuthStore(selectPodeAcessarFinanceiro)
  const visibleItems = navItems.filter((item) => {
    if (item.requer === 'staff') return temAcessoTotal
    if (item.requer === 'marketing') return podeMarketing
    if (item.requer === 'financeiro') return podeFinanceiro
    return true
  })
  ...
```
**RF-11 (visibilidade de menu, não é checagem de segurança — a segurança real é o backend da seção 2):** `RH` passa a ficar escondido de quem não tem acesso total, mesmo sem nenhum perfil novo logado — é correção de uma inconsistência pré-existente (API já era `IsAdmin` há várias manutenções, o menu nunca escondia), feita agora porque o pedido pede explicitamente que `FINANCEIRO`/`PROFISSIONAL` não vejam RH no menu, e a forma certa de garantir isso é a mesma regra central (`requer: 'staff'`), não uma regra nova e paralela só para os 2 perfis novos. Zero perda de funcionalidade para quem já tinha acesso de verdade (só quem recebia 403 ao clicar deixa de ver o item).

### 3.3 `routes/index.jsx`

Troca `MarketingRoute` (hoje recalcula perfil inline) para usar o selector central, e adiciona `FinanceiroRoute` no mesmo padrão, aplicada em `/financeiro`, `/conciliacao` e `/compras` (RF-12):

```jsx
import useAuthStore, {
  selectTemAcessoTotal, selectPodeAcessarMarketing, selectPodeAcessarFinanceiro,
} from '../stores/authStore.js'

function StaffRoute({ children }) {
  const temAcessoTotal = useAuthStore(selectTemAcessoTotal)
  if (!temAcessoTotal) return <Navigate to="/dashboard" replace />
  return children
}

function MarketingRoute({ children }) {
  const podeAcessar = useAuthStore(selectPodeAcessarMarketing)   // antes recalculava perfil aqui
  if (!podeAcessar) return <Navigate to="/dashboard" replace />
  return children
}

function FinanceiroRoute({ children }) {           // novo
  const podeAcessar = useAuthStore(selectPodeAcessarFinanceiro)
  if (!podeAcessar) return <Navigate to="/dashboard" replace />
  return children
}
```
E trocar `<StaffRoute><Compras /></StaffRoute>` por `<FinanceiroRoute><Compras /></FinanceiroRoute>`; envolver `/financeiro` e `/conciliacao` (hoje sem guarda nenhuma) com `<FinanceiroRoute>`. `/rh` e `/usuarios` — `/usuarios` continua em `StaffRoute` conforme já estava; `/rh` hoje **não tem guarda de rota nenhuma** (só o Sidebar escondia via a inconsistência da seção 3.2); por simetria com RH agora ficar `requer: 'staff'` no menu, envolver também `/rh` com `<StaffRoute>` para a navegação direta por URL (não só o clique no menu) respeitar a mesma regra — sem isso, um `FINANCEIRO` digitando `/rh` na barra de endereço veria a tela (que erraria todas as chamadas com 403, mas chegaria a renderizar).

### 3.4 `Usuarios.jsx` — combobox com descrição (RF-13)

`Select.jsx` (componente genérico) só renderiza `label` dentro do `<option>` — não tem slot de descrição por item. Duas mudanças, sem precisar alterar o componente genérico:

```js
const PERFIL_OPTIONS = [
  { value: 'ADMIN', label: 'Admin' },
  { value: 'OPERACIONAL', label: 'Operacional' },
  { value: 'FINANCEIRO', label: 'Financeiro' },        // novo
  { value: 'PROFISSIONAL', label: 'Profissional' },     // novo
  { value: 'MARKETING', label: 'Marketing' },
  { value: 'SUPERADMIN', label: '👑 Superadmin' },
]
```
E no campo `perfil` dentro de `fields={[...]}` do `ResourceCrud`, adicionar `helpText` estático (mesmo padrão já usado no campo `password`, que já aceita string ou função) listando a legenda curta de cada perfil, sempre visível (não só condicionada a `isEditing`):
```js
{
  name: 'perfil',
  label: 'Perfil',
  type: 'select',
  options: perfilOptions,
  helpText: 'Admin/Superadmin: acesso total. Operacional: uso geral do sistema. '
    + 'Financeiro: financeiro, pagamentos, compras e fornecedores — sem Usuários/RH/Marketing. '
    + 'Profissional: agenda própria e clientes em leitura — sem financeiro/compras/RH/PDV. '
    + 'Marketing: campanhas e leads.',
},
```

---

## 4. Requisitos Funcionais

- **RF-01** — `PerfilUsuario` ganha `FINANCEIRO` e `PROFISSIONAL`.
- **RF-02** — `common/permissions.py` ganha `IsFinanceiro`, `IsProfissional` (padrão `IsMarketing`) e `BloqueiaEscritaDeProfissional`.
- **RF-03** — Todos os ViewSets/views listados na seção 2.4 (financeiro — classe + 3 `@action` com override próprio + 5 `@api_view`; compras) passam a aceitar `FINANCEIRO` via `IsAdmin | IsFinanceiro`.
- **RF-04** — `pagamentos`/`fornecedores` permanecem sem alteração de permissão (já abertos; ver seção 1.4).
- **RF-05** — `Agenda` ganha campo `profissional` (FK nullable a `accounts.User`).
- **RF-06** — `ClienteViewSet` bloqueia escrita (`POST`/`PUT`/`PATCH`/`DELETE`, incluindo as `@action` de histórico/acionistas) para perfil `PROFISSIONAL` puro; leitura e demais perfis inalterados.
- **RF-07** — `AgendaViewSet.get_queryset` filtra para `PROFISSIONAL` puro: `profissional=self OR created_by=self`.
- **RF-08** — `CompromissoViewSet.get_queryset` filtra para `PROFISSIONAL` puro: `created_by=self OR agenda__profissional=self`.
- **RF-09** — Testes nos dois sentidos (permite/bloqueia) para `FINANCEIRO` e `PROFISSIONAL` em cada app tocado, incluindo os 3 `@action` de estorno e as `@action` de Cliente.
- **RF-10** — `authStore.js` ganha `selectPerfil`, `selectPodeAcessarFinanceiro`, `selectPodeAcessarProfissional`, e `selectPodeAcessarMarketing` (extraído da expressão hoje duplicada entre `Sidebar` e `routes`).
- **RF-11** — `Sidebar.jsx` usa os selectors centrais para `Compras`, `Marketing`, `Financeiro`, `Conciliação`, `RH`, `Usuários` (sem expressão de perfil inline em nenhum item).
- **RF-12** — `routes/index.jsx` usa os mesmos selectors (`FinanceiroRoute` novo; `MarketingRoute` reescrito para consumir o selector em vez de recalcular; `/rh` ganha `StaffRoute`).
- **RF-13** — Combobox de perfil em `Usuarios.jsx` lista `Financeiro`/`Profissional` com legenda curta visível (via `helpText`).

## 5. Regras de Negócio

- **RN-01** — `User.tem_acesso_total` não é alterada; `FINANCEIRO`/`PROFISSIONAL` nunca satisfazem `tem_acesso_total`.
- **RN-02** — Travas da Manutenção #60 (só `SUPERADMIN` concede/edita `SUPERADMIN`) permanecem intactas — `UserAdminSerializer.validate`/`UserViewSet._bloquear_edicao_superadmin` não são tocados.
- **RN-03 (Should)** — Escrita de `Compromisso` não valida (nesta fase) que `agenda.profissional == request.user` para o perfil `PROFISSIONAL` — só a leitura é escopada. Registrado para fase futura.
- **RN-04** — `dashboard_financeiro` e `inferir_categoria` permanecem `IsAuthenticated` puro — não são "recursos do módulo financeiro" para fins do critério de aceite, são utilitário/tela universal (seção 1.3).
- **RN-05** — `pagamentos` e `fornecedores` permanecem sem permission class nova — já satisfazem o pedido via `IsAuthenticated` (seção 1.4). Qualquer restrição futura nesses dois apps é uma manutenção própria, não implícita nesta.
- **RN-06** — Nenhum valor de `PerfilUsuario` fica sem permission class lendo-o: `FINANCEIRO` → `IsFinanceiro`; `PROFISSIONAL` → `IsProfissional` (direto, com teste unitário) e `BloqueiaEscritaDeProfissional` (uso em produção, com teste de integração).

## 6. Critérios de Aceite (produção)

| # | Cenário | Esperado |
|---|---|---|
| CA-01 | `FINANCEIRO` → `GET /api/v1/financeiro/contas/`, `/receitas/`, `/despesas/`, `/livro-caixa/`, `/dre/`, `/balanco/`, `/fluxo-projetado/`, `/indicadores/`, `/conciliacoes/` | 200 em todos |
| CA-02 | `FINANCEIRO` → `POST /api/v1/financeiro/receitas/{id}/estornar/`, `.../despesas/{id}/estornar/`, `.../livro-caixa/{id}/estornar/` | 200/201 (não 403 — pega o bug do `@action` com `permission_classes` próprio) |
| CA-03 | `FINANCEIRO` → `GET/POST /api/v1/compras/` | 200/201 |
| CA-04 | `FINANCEIRO` → `GET /api/v1/accounts/usuarios/`, `GET /api/v1/rh/colaboradores/`, `GET /api/v1/rh/folhas/` | 403 em todos |
| CA-05 | `PROFISSIONAL` → `GET /api/v1/agendamento/compromissos/` | retorna só os com `created_by=self` ou `agenda__profissional=self` |
| CA-06 | `PROFISSIONAL` → `GET /api/v1/clientes/` | 200, lista completa (leitura liberada) |
| CA-07 | `PROFISSIONAL` → `POST /api/v1/clientes/` | 403 |
| CA-08 | `PROFISSIONAL` → `GET /api/v1/financeiro/contas/`, `/receitas/`, qualquer recurso de `financeiro/*` listado no CA-01 | 403 em todos |
| CA-09 | `PROFISSIONAL` → `GET /api/v1/compras/`, `/api/v1/rh/colaboradores/`, `/api/v1/accounts/usuarios/`, `/api/v1/pdv/sessoes/` | 403 em todos |
| CA-10 | `ADMIN`/`SUPERADMIN` (`tem_acesso_total`) | continua com acesso total em tudo acima, sem exceção |
| CA-11 | `OPERACIONAL` → endpoints que já acessava antes desta manutenção (`pagamentos`, `fornecedores`, `clientes` leitura+escrita, `vendas`, `produtos`, `agendamento` sem filtro de queryset porque não é `PROFISSIONAL`, `/financeiro/dashboard/`) | mesmo status code de antes — 0 regressão |
| CA-12 | `MARKETING` → `/marketing/*`, `/pagamentos/*`, `/fornecedores/*` | mesmo status code de antes — 0 regressão |
| CA-13 | Teste unitário de `IsFinanceiro`/`IsProfissional`/`BloqueiaEscritaDeProfissional` isolado (sem HTTP, request mockado) | cobre as 6+ combinações da tabela da seção 2.5 |
| CA-14 | Frontend: usuário `FINANCEIRO` logado vê no Sidebar `Financeiro`, `Conciliação`, `Compras` (além dos itens comuns); não vê `RH`/`Usuários`/`Marketing` | confirmado por inspeção/teste de Sidebar |
| CA-15 | Frontend: usuário `PROFISSIONAL` digitando `/rh` ou `/financeiro` direto na URL é redirecionado para `/dashboard` (`StaffRoute`/`FinanceiroRoute`) | confirmado |
| CA-16 | `makemigrations --check --dry-run` | 0 pendências após `accounts/0005` e `agendamento/0007` |

## 7. Fora de Escopo

- Permissão campo a campo (ex.: `FINANCEIRO` ver receita mas não ver valor de despesa específica).
- Perfis específicos de nicho (ex.: "Terapeuta" com regras próprias diferentes de "Professor") — `PROFISSIONAL` é deliberadamente genérico.
- Validar na escrita que `Compromisso.agenda.profissional == request.user` (RN-03, fase futura).
- M2M de profissionais por agenda (seção 2.2 — decisão de manter 1:N).
- Restringir `pagamentos`/`fornecedores` a um subconjunto de perfis (seção 1.4/RN-05).
