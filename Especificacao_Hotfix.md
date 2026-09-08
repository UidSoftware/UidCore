# Especificação Hotfix — Manutenção #60

**Sistema:** UidCore (OS #7)
**Módulo:** `accounts` (backend) + `authStore`/`Sidebar`/`routes`/telas PDV (frontend)
**Tipo:** `melhoria_ux` + hardening de segurança (RBAC) — não é bug isolado, é reforço de controle de acesso administrativo
**Requer aprovação comercial:** não — hardening interno de segurança, sem novo módulo cobrável
**Analista:** leitura de código confirmada em `backend/accounts/{models,serializers,views,managers,admin}.py`, `backend/common/permissions.py`, `backend/pdv/views.py`, `backend/rh/views.py`, `frontend/src/stores/authStore.js`, `frontend/src/components/layout/Sidebar.jsx`, `frontend/src/routes/index.jsx`, `frontend/src/pages/Usuarios.jsx`, `frontend/src/pages/pdv/{HistoricoVendas,RelatorioSessoesCaixa}.jsx`

---

## 1. Diagnóstico confirmado (grep + leitura de código)

- `PerfilUsuario` (`backend/accounts/models.py`) hoje só tem `ADMIN`, `OPERACIONAL`, `MARKETING`. Não existe `SUPERADMIN`.
- `User.is_staff` é o único campo hoje usado tanto para (a) acesso ao Django Admin (`/admin/`, seu propósito original no `PermissionsMixin`) quanto para (b) toda a checagem de negócio de "é administrador" — os dois papéis estão misturados no mesmo campo. Uso de negócio confirmado em **4 pontos exatos**:
  - `backend/common/permissions.py:6` — `IsAdmin.has_permission` → `request.user.is_staff`
  - `backend/common/permissions.py:17` — `IsMarketing.has_permission` → `... or u.is_staff`
  - `backend/pdv/views.py:74` — `SessaoCaixaViewSet.get_queryset` → `if not self.request.user.is_staff:` (operador só vê as próprias sessões)
  - `backend/rh/views.py:61` — `ColaboradorViewSet._validar_criar_usuario` → `if not self.request.user.is_staff:` (só admin pode criar acesso ao sistema)
  - `IsAdmin` é reutilizada em **todos** os módulos com efeito financeiro/administrativo: `accounts`, `financeiro`, `pdv`, `rh`, `compras`, `marketing` (via `IsAdmin | IsMarketing`) — corrigir a classe central em `common/permissions.py` propaga a correção para todos eles sem tocar em cada `views.py` individualmente.
  - `backend/accounts/tests.py`, `backend/pdv/tests.py`, `backend/financeiro/tests.py`, `backend/rh/tests.py` usam `is_staff=True` nos helpers de fixture (`_make_user`) para simular admin — **não precisam mudar**, pois `is_staff=True` continuará concedendo acesso total via a nova property (regra 100% retrocompatível).
- `UserAdminSerializer` (`backend/accounts/serializers.py:19-25`) expõe `is_staff` como campo editável (não está em `read_only_fields`) — qualquer usuário com acesso à tela de Usuários pode promover/rebaixar `is_staff` de qualquer conta, incluindo a própria, sem nenhuma trava de perfil.
- Não existe hoje **nenhuma validação** impedindo que um ADMIN comum crie ou edite outro usuário definindo um perfil mais privilegiado do que o dele próprio, nem impedindo que um ADMIN edite/desative a conta de outro ADMIN "acima" dele — não há hierarquia nenhuma dentro de `PerfilUsuario`, todos os valores atuais (`ADMIN`, `OPERACIONAL`, `MARKETING`) são irmãos, não há um nível "acima de ADMIN".
- `UserViewSet.destroy()` (`backend/accounts/views.py:24-28`) já é soft-delete (`is_active=False`) — ponto de extensão correto para bloquear desativação de conta `SUPERADMIN` por não-`SUPERADMIN` (item 6).
- **Frontend duplica a checagem `is_staff` em 4 arquivos**, sem nenhuma centralização (grep completo):
  - `frontend/src/components/layout/Sidebar.jsx:23,27-28`
  - `frontend/src/routes/index.jsx:34-35,40-42` (`StaffRoute` e `MarketingRoute`)
  - `frontend/src/pages/pdv/HistoricoVendas.jsx:312,376,516` (`user?.is_staff`)
  - `frontend/src/pages/pdv/RelatorioSessoesCaixa.jsx:181,248` (`user.is_staff`)
  - `frontend/src/stores/authStore.js` não expõe nenhum seletor/computed — cada componente lê `s.user?.is_staff` cru.
- `frontend/src/pages/Usuarios.jsx` tem checkbox `is_staff` (linha 43) e dropdown de Perfil com 3 opções (linhas 48-52).
- **Gap não citado no pedido, mas obrigatório corrigir junto (achado do Analista, não suposição):**
  1. A coluna da listagem `{ key: 'is_staff', label: 'Admin', boolean: true }` (`Usuarios.jsx:26`) vai quebrar silenciosamente assim que `is_staff` sair do `UserAdminSerializer` (item 4) — a API para de devolver o campo, a coluna passa a exibir sempre "não" mesmo para SUPERADMIN/ADMIN reais.
  2. `onBeforeSubmit` (`Usuarios.jsx:72-82`) lê `form.is_staff` para decidir se mostra o aviso de "você está removendo seu próprio acesso" — assim que o checkbox for removido do formulário (item 8), `form.is_staff` vira `undefined`, e `!form.is_staff` passa a ser **sempre `true`**. Resultado: o aviso de autobloqueio dispararia em **toda** edição do próprio usuário, mesmo sem nenhuma perda de acesso real — regressão de UX introduzida pela própria correção se não for ajustada junto.
  Ambos os pontos entram como RF/RN nesta especificação (seções 3 e 6.4) para não deixar a Manutenção #60 incompleta.
- `accounts/migrations/` hoje tem só `0001_initial.py` e `0002_add_perfil_usuario.py` — próxima migration schema é `0003`, próxima migration de dado é `0004`.

---

## 2. Decisões de arquitetura (fechadas nesta especificação)

| Decisão em aberto no pedido | Escolha | Justificativa |
|---|---|---|
| `is_staff` continua existindo no model? | **Sim, sem alteração de significado.** Continua controlando só o acesso ao Django Admin (`PermissionsMixin`/`createsuperuser`). Não é removido nem repurposed. | O pedido pede para trocar as checagens *de negócio*, não para eliminar o campo — `is_staff` é infraestrutura do Django, mexer nele quebraria `createsuperuser`/`/admin/`. `tem_acesso_total` é a camada de negócio que se sobrepõe, mantendo `is_staff=True` como "acesso total sempre concedido" por retrocompatibilidade (superusers legados continuam funcionando sem migração adicional). |
| `tem_acesso_total` é campo persistido ou `@property`? | **`@property` calculada, não é coluna no banco.** | Pedido explícito no item 2 ("property"). Evita duplicar estado (perfil + is_staff já bastam) e evita nova migration de schema para um valor 100% derivável dos dois campos existentes. |
| Como o frontend obtém `tem_acesso_total` sem duplicar a regra `is_staff OR perfil in (...)`? | **Backend expõe `tem_acesso_total` como campo read-only calculado em `UserSerializer`** (endpoint `/api/v1/accounts/me/`, já consumido pelo `authStore.login()`). O `authStore` apenas repassa esse campo via um seletor central — **não reimplementa a regra em JS**. | "Centralizar" (item 7) é mais forte se a fonte da verdade for uma só (o backend). Duplicar `is_staff \|\| ['ADMIN','SUPERADMIN'].includes(perfil)` em JS criaria uma segunda cópia da regra que pode divergir da property do backend se algum dia um novo perfil equivalente for adicionado e alguém esquecer de atualizar o frontend. |
| `UserAdminSerializer` também ganha `tem_acesso_total`? | **Sim, read-only.** Não pedido explicitamente, mas necessário para fechar o gap da coluna "Admin" da listagem de Usuários (achado do diagnóstico, item 1 da seção 1) sem reintroduzir `is_staff` no serializer (o que violaria o item 4 do pedido). | Sem isso, a tela de Usuários perde a única indicação visual de quem tem acesso total — regressão de UX. |
| Onde validar perfil=SUPERADMIN só por SUPERADMIN (item 5)? | **`UserAdminSerializer.validate()`**, usando `self.context['request'].user` (DRF `ModelViewSet.get_serializer_context()` já injeta `request` por padrão, confirmado em `UserViewSet` — não precisa sobrescrever `get_serializer_context`). | Roda tanto em `create` quanto em `update` sem duplicar código, e falha com `400` (erro de validação) antes de qualquer `save()`, em vez de `403` — é uma regra de dado inválido para quem não é SUPERADMIN, não falta de permissão para acessar a tela (o ADMIN pode acessar `UserViewSet` normalmente, só não pode setar esse valor específico). |
| Onde bloquear edição/desativação de conta SUPERADMIN por não-SUPERADMIN (item 6)? | **`UserViewSet.perform_update()` + `UserViewSet.destroy()`**, via helper privado `_bloquear_edicao_superadmin(instance)` chamado nos dois pontos. | `perform_update` cobre `PUT`/`PATCH`; `destroy()` já é sobrescrito no projeto para soft-delete — adicionar a checagem ali evita duplicar a query em `get_object`/`has_object_permission` de uma `BasePermission` nova só para isso. |
| Ordem de execução da migration de dado (item 9) | **Uma única `RunPython`, em duas etapas sequenciais dentro da mesma função**: (1) promove todo `is_staff=True AND is_superuser=True` para `SUPERADMIN`; (2) **depois**, sobrescreve especificamente `editoresdesucessos@gmail.com` para `perfil=ADMIN, is_staff=False`. | Se a etapa 2 rodasse antes da 1, e essa conta hoje for `is_staff=True AND is_superuser=True`, a etapa 1 a promoveria de volta para `SUPERADMIN` — a ordem importa. A etapa 2 usa `.first()` (não `.get()`) e só age `if` o registro existir, para **não quebrar `migrate` em ambientes onde esse e-mail não existe** (ambiente de teste do Sentinel, CI, dev local) — migration de dado nunca pode assumir que uma linha específica existe. |

---

## 3. Requisitos Funcionais (RF)

- **RF-01** — `PerfilUsuario` ganha `SUPERADMIN = 'SUPERADMIN', 'Superadmin'` como 4º valor (mantendo `ADMIN`, `OPERACIONAL`, `MARKETING` inalterados). Nova migration de schema `accounts/migrations/0003_alter_user_perfil.py` (gerada por `makemigrations`, altera só o `choices` do `CharField`, sem alterar dado).
- **RF-02** — `User` ganha `@property tem_acesso_total` (`backend/accounts/models.py`):
  ```python
  @property
  def tem_acesso_total(self):
      return self.is_staff or self.perfil in (PerfilUsuario.ADMIN, PerfilUsuario.SUPERADMIN)
  ```
- **RF-03** — As 4 checagens de negócio identificadas na seção 1 trocam `is_staff` por `tem_acesso_total`:
  - `common/permissions.py::IsAdmin.has_permission` → `request.user.tem_acesso_total`
  - `common/permissions.py::IsMarketing.has_permission` → `u.perfil == 'MARKETING' or u.tem_acesso_total`
  - `pdv/views.py::SessaoCaixaViewSet.get_queryset` (linha 74) → `if not self.request.user.tem_acesso_total:`
  - `rh/views.py::ColaboradorViewSet._validar_criar_usuario` (linha 61) → `if not self.request.user.tem_acesso_total:`
  - Nenhum outro ponto do backend usa `is_staff` para regra de negócio (confirmado por grep completo, seção 1) — não há mais nada a trocar.
- **RF-04** — `UserAdminSerializer.Meta.fields` remove `'is_staff'`. Adiciona `tem_acesso_total = serializers.BooleanField(read_only=True)` como novo campo read-only (ver Decisões, seção 2) para a listagem continuar mostrando quem tem acesso total.
- **RF-05** — `UserSerializer` (usado por `/api/v1/accounts/me/`, fonte do `authStore.user`) ganha o mesmo `tem_acesso_total = serializers.BooleanField(read_only=True)` em `fields` e `read_only_fields` — é o valor que o frontend vai consumir (RF-07).
- **RF-06** — `UserAdminSerializer.validate()`: se `attrs.get('perfil') == PerfilUsuario.SUPERADMIN` e o usuário autenticado (`self.context['request'].user`) não tiver `perfil == PerfilUsuario.SUPERADMIN`, levanta `serializers.ValidationError({'perfil': '...'})`. Cobre tanto `create` quanto `update`.
- **RF-07** — `UserViewSet` ganha `_bloquear_edicao_superadmin(self, instance)`: se `instance.perfil == PerfilUsuario.SUPERADMIN` e `self.request.user.perfil != PerfilUsuario.SUPERADMIN`, levanta `rest_framework.exceptions.PermissionDenied(...)`. Chamado em `perform_update()` (novo método) e no início de `destroy()` (já existente, só adiciona a chamada antes do soft-delete).
- **RF-08 (frontend)** — `authStore.js` exporta um seletor `selectTemAcessoTotal(state)` que retorna `Boolean(state.user?.tem_acesso_total)` — não reimplementa a regra `is_staff OR perfil in (...)`, só repassa o campo que o backend já calculou (RF-05).
- **RF-09 (frontend)** — `Sidebar.jsx`, `routes/index.jsx` (`StaffRoute`, `MarketingRoute`), `HistoricoVendas.jsx` (3 usos) e `RelatorioSessoesCaixa.jsx` (2 usos) trocam toda leitura de `user?.is_staff` / `user.is_staff` por `useAuthStore(selectTemAcessoTotal)` (ou, nos arquivos que já têm `user` completo carregado, `user?.tem_acesso_total`).
- **RF-10 (frontend)** — `Usuarios.jsx`: remove o campo `{ name: 'is_staff', label: 'Administrador', type: 'checkbox' }` de `fields` e `is_staff: false` de `emptyForm`; dropdown `Perfil` ganha a 4ª opção `{ value: 'SUPERADMIN', label: 'Superadmin' }`.
- **RF-11 (frontend, gap do diagnóstico)** — `Usuarios.jsx`: coluna `{ key: 'is_staff', label: 'Admin', boolean: true }` vira `{ key: 'tem_acesso_total', label: 'Acesso total', boolean: true }` (consome RF-04).
- **RF-12 (frontend, gap do diagnóstico)** — `Usuarios.jsx`: `onBeforeSubmit` reescrito para não depender de `form.is_staff` (campo removido em RF-10) — ver regra exata em RN-05.
- **RF-13** — Data migration `accounts/migrations/0004_seed_superadmin_perfil.py` (`RunPython`, ver seção 6.3): promove `is_staff=True AND is_superuser=True` → `perfil=SUPERADMIN`; em seguida força `editoresdesucessos@gmail.com` → `perfil=ADMIN, is_staff=False` (só se a conta existir).

---

## 4. Regras de Negócio (RN)

- **RN-01** — `tem_acesso_total` é **aditivo**, nunca restritivo: uma conta com `is_staff=True` mantém acesso total independentemente do `perfil`, mesmo que o `perfil` seja `OPERACIONAL` ou `MARKETING` (retrocompatibilidade com contas antigas criadas antes desta manutenção).
- **RN-02** — Só uma conta com `perfil == SUPERADMIN` pode **atribuir** `perfil=SUPERADMIN` a qualquer usuário (RF-06). Uma conta `ADMIN` (mesmo com `tem_acesso_total=True`) não pode se autopromover nem promover terceiros a `SUPERADMIN`.
- **RN-03** — Só uma conta com `perfil == SUPERADMIN` pode **editar** (`PUT`/`PATCH`) ou **desativar** (`DELETE`/soft-disable) uma conta que já é `SUPERADMIN` — inclusive a própria conta SUPERADMIN não fica bloqueada de se autoeditar (`instance.perfil == SUPERADMIN and request.user.perfil != SUPERADMIN` só é `True` quando o solicitante **não** é SUPERADMIN; um SUPERADMIN editando outro SUPERADMIN, ou a si mesmo, passa normalmente).
- **RN-04** — Leitura (`GET`/`list`) de contas `SUPERADMIN` continua permitida para qualquer `IsAdmin` (`tem_acesso_total=True`) — a trava é só de escrita (RN-03), pois a tela de Usuários precisa listar todas as contas para um ADMIN comum administrar o restante da equipe.
- **RN-05 (fecha o gap do diagnóstico)** — O aviso de autobloqueio em `Usuarios.jsx` dispara apenas quando a edição **realmente** resultaria em perda de `tem_acesso_total` para o próprio usuário logado:
  ```js
  const currentUser = useAuthStore.getState().user
  const isSelf = editingId && currentUser && String(editingId) === String(currentUser.id)
  const perderiaAcesso =
    isSelf &&
    currentUser.tem_acesso_total &&
    !currentUser.is_staff &&
    !['ADMIN', 'SUPERADMIN'].includes(form.perfil)
  ```
  (`currentUser.is_staff` continua disponível via `UserSerializer`/`/me/`, que não teve `is_staff` removido — só `UserAdminSerializer` perdeu o campo, RF-04.) Se `currentUser.is_staff` for `true`, a conta nunca perde acesso só por causa do `perfil`, então o aviso não deve aparecer.
- **RN-06** — Migration de dado (RF-13) é **idempotente**: rodar `migrate` duas vezes não deve alterar novamente contas já ajustadas nem falhar se `editoresdesucessos@gmail.com` não existir na base (ambiente de teste/CI).

---

## 5. Fora de escopo (Manutenção #60)

- Hierarquia genérica de perfis (ex.: um sistema de "níveis" numéricos comparáveis) — a trava é específica para `SUPERADMIN`, não um sistema geral de hierarquia entre `ADMIN`/`OPERACIONAL`/`MARKETING`.
- Impedir que o **último** `SUPERADMIN` do sistema se autodesative ou se autorrebaixe (risco de sistema ficar sem nenhum SUPERADMIN) — não pedido, fica para uma manutenção futura se for um risco real percebido em produção.
- Esconder na UI os botões de editar/desativar em linhas `SUPERADMIN` para um ADMIN comum — o backend responde `403`/erro de validação (RF-06/RF-07) e o `ResourceCrud` já tem o padrão de exibir a mensagem de erro da API (`.catch` + `extractErrorMessage`, RNF já em produção); esconder o botão é refinamento de UX opcional, não bloqueante.
- Log de auditoria de quem promoveu/editou quem — não pedido nesta manutenção.

---

## 6. Spec Backend

### 6.1 `backend/accounts/models.py`

```python
class PerfilUsuario(models.TextChoices):
    ADMIN = 'ADMIN', 'Admin'
    OPERACIONAL = 'OPERACIONAL', 'Operacional'
    MARKETING = 'MARKETING', 'Marketing'
    SUPERADMIN = 'SUPERADMIN', 'Superadmin'


class User(AbstractBaseUser, PermissionsMixin):
    # ... campos existentes sem alteração ...

    @property
    def tem_acesso_total(self):
        return self.is_staff or self.perfil in (PerfilUsuario.ADMIN, PerfilUsuario.SUPERADMIN)
```

### 6.2 `backend/common/permissions.py`

```python
from rest_framework.permissions import BasePermission


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

### 6.3 `backend/accounts/serializers.py`

```python
class UserSerializer(serializers.ModelSerializer):
    tem_acesso_total = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'email', 'nome_completo', 'telefone', 'is_active', 'is_staff', 'perfil', 'tem_acesso_total', 'date_joined']
        read_only_fields = ['id', 'is_active', 'is_staff', 'perfil', 'tem_acesso_total', 'date_joined']


class UserAdminSerializer(serializers.ModelSerializer):
    """Usada pela tela de Usuarios (IsAdmin) — cria/edita qualquer User do sistema."""
    id = serializers.IntegerField(source='pk', read_only=True)
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    colaborador_nome = serializers.CharField(source='colaborador.nome', read_only=True, default=None)
    tem_acesso_total = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'email', 'nome_completo', 'telefone', 'password',
            'is_active', 'perfil', 'tem_acesso_total', 'date_joined', 'colaborador_nome',
        ]
        read_only_fields = ['id', 'date_joined', 'colaborador_nome', 'tem_acesso_total']

    def validate(self, attrs):
        perfil_novo = attrs.get('perfil')
        if perfil_novo == PerfilUsuario.SUPERADMIN:
            request = self.context.get('request')
            solicitante = getattr(request, 'user', None)
            if not solicitante or solicitante.perfil != PerfilUsuario.SUPERADMIN:
                raise serializers.ValidationError(
                    {'perfil': 'Somente um usuário Superadmin pode conceder o perfil Superadmin.'}
                )
        return attrs

    # create()/update() sem alteração
```
(`is_staff` **não é mais campo do formulário** — continua existindo no model, só não é mais editável por esta tela; import de `PerfilUsuario` a adicionar no topo do arquivo.)

### 6.4 `backend/accounts/views.py`

```python
from rest_framework.exceptions import PermissionDenied

from .models import PerfilUsuario, User


class UserViewSet(ModelViewSet):
    queryset = User.objects.all().select_related('colaborador').order_by('-date_joined')
    serializer_class = UserAdminSerializer
    permission_classes = [IsAdmin]
    filter_backends = [SearchFilter]
    search_fields = ['email', 'nome_completo']

    def _bloquear_edicao_superadmin(self, instance):
        if instance.perfil == PerfilUsuario.SUPERADMIN and self.request.user.perfil != PerfilUsuario.SUPERADMIN:
            raise PermissionDenied('Somente um usuário Superadmin pode editar ou desativar outra conta Superadmin.')

    def perform_update(self, serializer):
        self._bloquear_edicao_superadmin(serializer.instance)
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self._bloquear_edicao_superadmin(instance)
        instance.is_active = False
        instance.save(update_fields=['is_active'])
        return Response(status=status.HTTP_204_NO_CONTENT)
```

### 6.5 `backend/pdv/views.py` (linha 74) e `backend/rh/views.py` (linha 61)

Troca pontual, sem mudança de estrutura:
```python
# pdv/views.py — SessaoCaixaViewSet.get_queryset
if not self.request.user.tem_acesso_total:
    qs = qs.filter(operador=self.request.user)

# rh/views.py — ColaboradorViewSet._validar_criar_usuario
if not self.request.user.tem_acesso_total:
    raise PermissionDenied('Somente administradores podem criar acesso ao sistema.')
```

### 6.6 Migrations

```
backend/accounts/migrations/
├── 0003_alter_user_perfil.py     # gerada por `makemigrations` — só amplia choices
└── 0004_seed_superadmin_perfil.py  # RunPython — dado, ver abaixo
```

```python
# 0004_seed_superadmin_perfil.py
from django.db import migrations


def seed_superadmin(apps, schema_editor):
    User = apps.get_model('accounts', 'User')

    User.objects.filter(is_staff=True, is_superuser=True).update(perfil='SUPERADMIN')

    conta_especifica = User.objects.filter(email__iexact='editoresdesucessos@gmail.com').first()
    if conta_especifica:
        conta_especifica.perfil = 'ADMIN'
        conta_especifica.is_staff = False
        conta_especifica.save(update_fields=['perfil', 'is_staff'])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0003_alter_user_perfil'),
    ]
    operations = [
        migrations.RunPython(seed_superadmin, noop),
    ]
```

---

## 7. Spec Frontend

### 7.1 `frontend/src/stores/authStore.js`

```js
const useAuthStore = create(persist(/* ...sem alteração no corpo... */))

export const selectTemAcessoTotal = (state) => Boolean(state.user?.tem_acesso_total)

export default useAuthStore
```

### 7.2 `frontend/src/components/layout/Sidebar.jsx`

```jsx
import useAuthStore, { selectTemAcessoTotal } from '../../stores/authStore.js'
// ...
const temAcessoTotal = useAuthStore(selectTemAcessoTotal)
const perfil = useAuthStore((s) => s.user?.perfil)
const visibleItems = navItems.filter(
  (item) =>
    (!item.staffOnly || temAcessoTotal) &&
    (!item.marketingOnly || temAcessoTotal || perfil === 'MARKETING'),
)
```

### 7.3 `frontend/src/routes/index.jsx`

```jsx
function StaffRoute({ children }) {
  const temAcessoTotal = useAuthStore(selectTemAcessoTotal)
  if (!temAcessoTotal) return <Navigate to="/dashboard" replace />
  return children
}

function MarketingRoute({ children }) {
  const temAcessoTotal = useAuthStore(selectTemAcessoTotal)
  const perfil = useAuthStore((s) => s.user?.perfil)
  if (!temAcessoTotal && perfil !== 'MARKETING') return <Navigate to="/dashboard" replace />
  return children
}
```
(import `selectTemAcessoTotal` de `../stores/authStore.js`)

### 7.4 `frontend/src/pages/pdv/HistoricoVendas.jsx` (linhas 312, 376, 516)

Trocar `user?.is_staff` → `user?.tem_acesso_total` nas 3 ocorrências (o componente já obtém `user` completo do `authStore` — não precisa do seletor, só ler o novo campo).

### 7.5 `frontend/src/pages/pdv/RelatorioSessoesCaixa.jsx` (linhas 181, 248)

Trocar `user.is_staff` → `user.tem_acesso_total` nas 2 ocorrências.

### 7.6 `frontend/src/pages/Usuarios.jsx`

```jsx
columns={[
  { key: 'nome_completo', label: 'Nome' },
  { key: 'email', label: 'E-mail' },
  { key: 'colaborador_nome', label: 'Colaborador' },
  { key: 'perfil', label: 'Perfil', badge: true },
  { key: 'tem_acesso_total', label: 'Acesso total', boolean: true },  // era 'is_staff'/'Admin'
  { key: 'is_active', label: 'Ativo', boolean: true },
  { key: 'date_joined', label: 'Desde', date: true },
]}
fields={[
  { name: 'email', label: 'E-mail', type: 'email', required: true },
  { name: 'nome_completo', label: 'Nome completo', type: 'text', required: true },
  { name: 'telefone', label: 'Telefone', type: 'text' },
  { name: 'password', label: 'Senha', type: 'password', helpText: (isEditing) => /* sem alteração */ },
  // checkbox is_staff REMOVIDO
  {
    name: 'perfil',
    label: 'Perfil',
    type: 'select',
    options: [
      { value: 'ADMIN', label: 'Admin' },
      { value: 'OPERACIONAL', label: 'Operacional' },
      { value: 'MARKETING', label: 'Marketing' },
      { value: 'SUPERADMIN', label: 'Superadmin' },
    ],
  },
]}
emptyForm={{ email: '', nome_completo: '', telefone: '', password: '', perfil: 'OPERACIONAL' }}  // is_staff removido
// ...
onBeforeSubmit={(form, editingId) => {
  const currentUser = useAuthStore.getState().user
  const isSelf = editingId && currentUser && String(editingId) === String(currentUser.id)
  const perderiaAcesso =
    isSelf &&
    currentUser.tem_acesso_total &&
    !currentUser.is_staff &&
    !['ADMIN', 'SUPERADMIN'].includes(form.perfil)
  if (perderiaAcesso) {
    const confirmado = window.confirm(
      'Você está removendo seu próprio acesso administrativo. Depois de salvar, não poderá mais acessar esta tela. Deseja continuar?',
    )
    if (!confirmado) return false
  }
  return true
}}
```

---

## 8. Riscos e Dependências

```
- RISCO: se algum ambiente (dev/homolog) não tiver nenhum usuario com
  is_staff=True AND is_superuser=True, a migration 0004 não promove
  ninguem a SUPERADMIN — nesse caso nenhuma conta consegue setar
  perfil=SUPERADMIN depois (RN-02 bloqueia todo mundo). Forge deve
  confirmar, apos aplicar a migration em cada ambiente, que existe pelo
  menos 1 conta SUPERADMIN (query manual: User.objects.filter(perfil=
  'SUPERADMIN').exists()) — se nao existir, promover manualmente 1 conta
  via shell antes de considerar o deploy concluido.
- RISCO: `editoresdesucessos@gmail.com` pode não existir em bancos de
  teste/CI/homolog — a migration trata isso com `.first()` + `if`, não
  deve quebrar `migrate` nesses ambientes (RN-06).
- DEPENDÊNCIA: `UserSerializer` é consumida também por `UserProfileView`
  (`GET/PATCH /api/v1/accounts/me/`) — adicionar `tem_acesso_total` não
  quebra `PATCH` porque o campo é `read_only`, mas Sentinel deve
  confirmar que o payload de `PATCH /me/` continua aceitando os mesmos
  campos de antes.
- DEPENDÊNCIA: `accounts/tests.py::UserViewSetTest` já teem casos
  `test_list_por_nao_staff_403` / `test_create_por_nao_staff_403_zero_registros`
  / `test_destroy_por_nao_staff_403` — nomes de teste ficam desatualizados
  semanticamente (a checagem real agora é `tem_acesso_total`, não mais
  só `is_staff`), mas o comportamento esperado (403) não muda — Forge
  pode manter os nomes ou renomeá-los, não é bloqueante.
```

---

## Critérios de Aceite (para o Sentinel)

```
CA-01 - PerfilUsuario.SUPERADMIN existe e aparece nas choices do campo
        perfil do model User
CA-02 - User(is_staff=False, perfil='OPERACIONAL').tem_acesso_total é False
CA-03 - User(is_staff=False, perfil='ADMIN').tem_acesso_total é True
CA-04 - User(is_staff=False, perfil='SUPERADMIN').tem_acesso_total é True
CA-05 - User(is_staff=True, perfil='OPERACIONAL').tem_acesso_total é True
        (retrocompatibilidade RN-01)
CA-06 - Endpoints protegidos por IsAdmin (financeiro, pdv, rh, compras,
        accounts/usuarios) continuam retornando 403 para usuario com
        tem_acesso_total=False e 200/201 para tem_acesso_total=True,
        via perfil OU via is_staff (testar as duas formas)
CA-07 - GET /api/v1/pdv/sessoes/ por operador comum (tem_acesso_total=
        False) retorna só as sessoes do proprio operador; por usuario
        com tem_acesso_total=True retorna todas
CA-08 - POST em ColaboradorViewSet com "criar acesso" por usuario sem
        tem_acesso_total retorna PermissionDenied; com tem_acesso_total
        (via perfil=ADMIN sem is_staff) funciona
CA-09 - UserAdminSerializer não expõe mais o campo is_staff em nenhuma
        resposta (GET/POST/PATCH em /api/v1/accounts/usuarios/); expõe
        tem_acesso_total (read-only, calculado)
CA-10 - UserSerializer (/api/v1/accounts/me/) expõe tem_acesso_total
        calculado corretamente para o usuário logado
CA-11 - POST/PATCH em /api/v1/accounts/usuarios/ tentando setar
        perfil=SUPERADMIN por um solicitante com perfil != SUPERADMIN
        retorna 400 com mensagem no campo perfil; nenhum registro é
        alterado no banco
CA-12 - POST/PATCH em /api/v1/accounts/usuarios/ tentando setar
        perfil=SUPERADMIN por um solicitante com perfil=SUPERADMIN
        funciona normalmente (200/201)
CA-13 - PATCH ou DELETE em /api/v1/accounts/usuarios/{id}/ onde o
        {id} é uma conta perfil=SUPERADMIN, feito por um solicitante
        com perfil != SUPERADMIN (mesmo com tem_acesso_total=True via
        ADMIN), retorna 403; nenhuma alteração persiste
CA-14 - PATCH ou DELETE na mesma conta SUPERADMIN feito por outro
        SUPERADMIN (ou pela própria conta) funciona normalmente
CA-15 - Leitura (GET list e GET detail) de contas SUPERADMIN por um
        ADMIN comum continua funcionando (RN-04 — só escrita é bloqueada)
CA-16 - Migration 0004 aplicada: toda conta com is_staff=True AND
        is_superuser=True antes da migration está com perfil=SUPERADMIN
        depois
CA-17 - Migration 0004 aplicada em base com editoresdesucessos@gmail.com
        presente: essa conta fica com perfil=ADMIN e is_staff=False
        após a migration
CA-18 - Migration 0004 aplicada em base SEM editoresdesucessos@gmail.com
        (ex.: ambiente de teste do Sentinel): migrate não falha, nenhum
        erro/exception
CA-19 - Frontend: Sidebar mostra itens staffOnly/marketingOnly
        corretamente para usuário perfil=ADMIN sem is_staff, perfil=
        SUPERADMIN sem is_staff, e perfil=OPERACIONAL com is_staff=True
CA-20 - Frontend: rotas /compras e /usuarios (StaffRoute) e /marketing
        (MarketingRoute) redirecionam corretamente para os mesmos 3
        perfis de teste do CA-19
CA-21 - Frontend: HistoricoVendas e RelatorioSessoesCaixa liberam as
        ações/telas restritas a admin usando tem_acesso_total (mesmos
        3 perfis de teste)
CA-22 - Frontend: tela Usuarios sem checkbox "Administrador"; dropdown
        Perfil com 4 opções (Admin, Operacional, Marketing, Superadmin);
        coluna "Acesso total" refletindo o valor real vindo da API
CA-23 - Frontend: editar o próprio usuário mudando perfil de ADMIN para
        OPERACIONAL (usuário sem is_staff) dispara o aviso de
        autobloqueio; mudar de ADMIN para MARKETING mantendo is_staff=
        True (se aplicável) ou editar QUALQUER outro campo sem mexer no
        perfil NÃO dispara o aviso indevidamente (fecha a regressão do
        gap identificado no diagnóstico)
CA-24 - npm run build limpo (0 erros) após as mudanças no frontend
CA-25 - Testes Django cobrindo RF-01 a RF-13 e RN-01 a RN-06 (mínimo:
        um teste por CA acima que envolva backend)
```

---

## Passagem de bastão

```
✅ Solicitação classificada — UidCore (OS #7)
   MANUTENCAO_ID: 60
   tipo: melhoria_ux (hardening de RBAC — perfil SUPERADMIN + tem_acesso_total)
   descricao_tecnica: introduz PerfilUsuario.SUPERADMIN, unifica toda
     checagem de negócio de admin em User.tem_acesso_total (is_staff OR
     perfil in ADMIN/SUPERADMIN), remove is_staff do serializer de
     edição de usuários, bloqueia promoção/edição de contas SUPERADMIN
     por não-SUPERADMIN, centraliza a mesma checagem no frontend
     (authStore) e corrige 2 gaps encontrados no diagnóstico (coluna
     "Admin" da listagem e aviso de autobloqueio em Usuarios.jsx que
     quebrariam silenciosamente com a remoção do checkbox is_staff)
   caminho_afetado: backend/accounts/{models,serializers,views}.py,
     backend/common/permissions.py, backend/pdv/views.py (linha 74),
     backend/rh/views.py (linha 61), migrations 0003/0004 de accounts,
     frontend/src/stores/authStore.js, frontend/src/components/layout/
     Sidebar.jsx, frontend/src/routes/index.jsx, frontend/src/pages/
     Usuarios.jsx, frontend/src/pages/pdv/{HistoricoVendas,
     RelatorioSessoesCaixa}.jsx
   requer_aprovacao_comercial: false
➡️  Planner: rotear para Forge (backend, itens 1-6 e 9) + Loom
    (frontend, itens 7-8, incluindo os 2 gaps RF-11/RF-12/RN-05) em
    paralelo. Sentinel valida os 25 critérios de aceite acima — atenção
    especial a CA-16/CA-17/CA-18 (migration de dado idempotente e
    segura em base sem a conta específica) antes do Pilot.
```
