# Especificação de Hotfix — UidCore (OS #7)

**Manutenção #54 — Módulo novo: Marketing (Campanhas + Leads + ROI/CAC) + perfil Marketing**

Data: 2026-08-25
Levantado por: Analista (modo manutenção — briefing técnico já qualificado, sem lacunas)

---

## 1. Contexto

O UidCore hoje não tem nenhuma estrutura de marketing/aquisição — só
`clientes.Cliente` já convertido, sem histórico de como o lead chegou
além do campo livre `origem` (texto). Não existe conceito de campanha,
funil de lead, nem cálculo de custo de aquisição (CAC) ou retorno sobre
investimento (ROI) por canal.

Pedido do cliente: um módulo de Marketing dentro do próprio UidCore para
cadastrar campanhas, registrar leads captados por canal, converter lead
em cliente sem perder o rastro da campanha de origem, e visualizar
ROI/CAC por campanha cruzando o investimento com as vendas fechadas
(`vendas.Pedido`) dos clientes que vieram daquela campanha.

Requisito adicional: como isso é operação comercial e não deve ficar
exposto a quem cuida de Financeiro/RH/PDV, foi pedido um perfil de
usuário `Marketing` com acesso restrito a este módulo novo — o que exige
antes uma decisão de arquitetura, porque o UidCore não tem hoje nenhum
mecanismo de perfil granular (só `is_staff` boolean).

## 2. AS-IS (como é hoje)

```
- accounts.User: email, nome_completo, telefone, is_active, is_staff,
  date_joined — sem campo de perfil/role
- common/permissions.py: só IsAdmin (is_staff) e IsOwner — binário,
  sem granularidade por módulo
- clientes.Cliente (herda PessoaBase/BaseModel): tem campo `origem`
  (CharField 100, texto livre) — não há vínculo formal com nenhuma
  entidade de campanha, porque campanha não existe
- vendas.Pedido: representa venda fechada, tem `cliente` (FK),
  `valor_total` (Decimal), `created_at` (herdado de BaseModel) — é a
  fonte de receita fechada usada para o cálculo de ROI/CAC
- Sidebar.jsx: itens fixos por rota, com `staffOnly` controlando
  visibilidade via `user?.is_staff` — não existe granularidade além de
  staff/não-staff
- Nenhum app `marketing` existe no projeto (confirmado:
  backend/marketing/ não existe, `core/settings.py` LOCAL_APPS e
  `core/urls.py` não referenciam)
```

## 3. TO-BE (como será)

```
- Novo app `marketing` (backend/marketing/) com models Campanha e Lead
- accounts.User ganha campo `perfil` (ADMIN/OPERACIONAL/MARKETING)
- Nova permission IsMarketing em common/permissions.py
- Endpoint de conversão de Lead em Cliente, preservando rastreabilidade
  da campanha de origem via Cliente.origem
- Endpoint de ROI/CAC por campanha, cruzando Lead → Cliente → Pedido
- Novo item "Marketing" na Sidebar, visível para ADMIN ou MARKETING
- Duas telas novas no frontend: Campanhas e Leads
```

---

## 4. Decisão de Arquitetura — mecanismo de perfil (RF05)

**Contexto do problema:** o UidCore não tem precedente de perfil
granular. O SystemD (produto irmão) resolve isso com um campo
`perfil` com choices (`ADMIN`/`OPERACIONAL`/`FINANCEIRO`/`CLIENTE`) direto
no model de usuário — não usa Django Groups/Permissions.

**Opções avaliadas:**

| Opção | Prós | Contras |
|---|---|---|
| Django Groups + Permissions (`auth.Group`) | Nativo do Django, granularidade por permissão individual | Overkill para 1 perfil novo; exige telas de administração de grupos/permissões que não existem no UidCore; mais uma tabela de junção (`user_groups`) só para resolver "vê ou não vê 1 módulo" |
| Campo `perfil` (CharField + choices) em `accounts.User` | Consistente com o padrão já usado no SystemD (produto irmão da mesma stack); 1 migration simples, sem tabela nova; leitura direta em `request.user.perfil` sem joins; frontend já tem precedente de checar `user?.is_staff` do mesmo jeito (`user?.perfil`) | Menos flexível que Groups se no futuro houver dezenas de perfis com permissões cruzadas granulares |

**Decisão:** campo `perfil` em `accounts.User`, choices
`ADMIN` / `OPERACIONAL` / `MARKETING`, default `OPERACIONAL`. Justificativa:
escopo atual é 1 perfil novo com acesso binário (vê o módulo Marketing
ou não vê) — Groups resolveria o mesmo problema com mais peça móvel e
sem nenhuma tela de administração de grupos para sustentar isso.
Padrão consistente com o irmão SystemD reduz a distância entre os dois
codebases da Uid. Se no futuro o UidCore precisar de permissão granular
por ação (não só por módulo), Groups deve ser revisitado — não é o caso
hoje.

`is_staff` continua existindo e controlando Financeiro/RH/PDV/Usuários
(`IsAdmin`) — `perfil` é aditivo, não substitui `is_staff`. Um usuário
`is_staff=True` continua com acesso total (inclusive Marketing, ver
RF05/RN08 abaixo), independente do valor de `perfil`.

**Migration de dados:** nenhuma migration de dados necessária — usuários
existentes recebem `perfil='OPERACIONAL'` (default) automaticamente;
usuários com `is_staff=True` mantêm acesso total via `IsAdmin` sem
depender do novo campo.

---

## 5. Requisitos Funcionais (RF)

### RF01 — Model `Campanha` (app `marketing`)

```python
class CanalCampanha(models.TextChoices):
    ADS = 'ads', 'Ads'
    REDES_SOCIAIS = 'redes_sociais', 'Redes Sociais'
    EMAIL = 'email', 'E-mail'
    ORGANICO = 'organico', 'Orgânico'
    OUTRO = 'outro', 'Outro'

class StatusCampanha(models.TextChoices):
    PLANEJADA = 'planejada', 'Planejada'
    ATIVA = 'ativa', 'Ativa'
    ENCERRADA = 'encerrada', 'Encerrada'

class Campanha(BaseModel):
    nome = models.CharField('nome', max_length=255)
    canal = models.CharField('canal', max_length=20, choices=CanalCampanha.choices)
    data_inicio = models.DateField('data de início')
    data_fim = models.DateField('data de fim', null=True, blank=True)
    orcamento = models.DecimalField('orçamento', max_digits=12, decimal_places=2, default=0)
    status = models.CharField('status', max_length=10, choices=StatusCampanha.choices, default=StatusCampanha.PLANEJADA)

    class Meta:
        db_table = 'marketing_campanha'
        ordering = ['-created_at']
```

Endpoint CRUD completo: `/api/v1/marketing/campanhas/` (`DefaultRouter`,
igual ao padrão de `clientes/urls.py`).

### RF02 — Model `Lead` (app `marketing`)

```python
class StatusLead(models.TextChoices):
    NOVO = 'novo', 'Novo'
    QUALIFICADO = 'qualificado', 'Qualificado'
    CONVERTIDO = 'convertido', 'Convertido'
    DESCARTADO = 'descartado', 'Descartado'

class Lead(BaseModel):
    nome = models.CharField('nome', max_length=200)
    email = models.EmailField('e-mail', blank=True)
    telefone = models.CharField('telefone', max_length=20, blank=True)
    campanha = models.ForeignKey(
        Campanha, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='leads',
    )
    observacoes = models.TextField('observações', blank=True)
    status = models.CharField('status', max_length=12, choices=StatusLead.choices, default=StatusLead.NOVO)
    cliente_convertido = models.ForeignKey(
        'clientes.Cliente', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='leads_origem',
    )

    class Meta:
        db_table = 'marketing_lead'
        ordering = ['-created_at']
```

Notas de implementação:
- `data_criacao` do RF original é o `created_at` herdado de `BaseModel`
  — não criar campo duplicado.
- `campanha` usa `on_delete=models.SET_NULL` (não `PROTECT`) porque
  RN07 exige que excluir (soft delete) uma campanha não pode quebrar o
  histórico de leads — e soft delete não aciona `on_delete` mesmo, mas
  a FK correta evita erro caso algum dia a exclusão física seja cogitada.
- `cliente_convertido` é `SET_NULL` pelo mesmo motivo de resiliência —
  cliente é o "produto final" da conversão, não deve travar a exclusão
  do lead nem vice-versa.

Endpoint CRUD completo: `/api/v1/marketing/leads/`.

### RF03 — Ação "Converter em Cliente"

`POST /api/v1/marketing/leads/{id}/converter/`

```python
@action(detail=True, methods=['post'], url_path='converter')
def converter(self, request, pk=None):
    lead = self.get_object()
    if lead.status == StatusLead.CONVERTIDO:
        return Response({'detail': 'Lead já convertido.'}, status=400)

    with transaction.atomic():
        cliente = None
        if lead.email:
            cliente = Cliente.objects.filter(email=lead.email, is_active=True).first()
        if cliente is None:
            cliente = Cliente.objects.create(
                tipo_pessoa='PF',
                nome_razao_social=lead.nome,
                email=lead.email,
                telefone=lead.telefone,
                origem=lead.campanha.nome if lead.campanha else 'Sem campanha',
            )
        lead.status = StatusLead.CONVERTIDO
        lead.cliente_convertido = cliente
        lead.save(update_fields=['status', 'cliente_convertido', 'updated_at'])

    return Response(LeadSerializer(lead).data, status=200)
```

Regras:
- Busca de duplicidade por `email` **apenas quando `lead.email` não é
  vazio** — lead sem e-mail sempre cria `Cliente` novo (não há chave
  segura para deduplicar).
- Tudo em `transaction.atomic()` — se a criação do Cliente falhar, o
  Lead não pode ficar marcado como convertido sem cliente vinculado.
- RN06: uma vez `convertido`, a action retorna 400 numa segunda
  tentativa — conversão não é reversível via API.

### RF04 — Endpoint de ROI por Campanha

`GET /api/v1/marketing/campanhas/{id}/roi/`

```python
@action(detail=True, methods=['get'], url_path='roi')
def roi(self, request, pk=None):
    campanha = self.get_object()
    leads_qs = Lead.objects.filter(campanha=campanha, is_active=True)
    leads_total = leads_qs.count()
    leads_convertidos = leads_qs.filter(status=StatusLead.CONVERTIDO).count()

    clientes_ids = leads_qs.filter(
        status=StatusLead.CONVERTIDO, cliente_convertido__isnull=False,
    ).values_list('cliente_convertido_id', flat=True)

    receita_fechada = Pedido.objects.filter(
        cliente_id__in=clientes_ids,
        is_active=True,
        created_at__gte=campanha.data_inicio,
    ).aggregate(total=Sum('valor_total'))['total'] or Decimal('0')

    orcamento = campanha.orcamento
    cac = (orcamento / leads_convertidos) if leads_convertidos > 0 else None
    roi = (
        ((receita_fechada - orcamento) / orcamento) * 100
        if orcamento > 0 else None
    )

    return Response({
        'campanha_id': campanha.pk,
        'leads_total': leads_total,
        'leads_convertidos': leads_convertidos,
        'orcamento': orcamento,
        'receita_fechada': receita_fechada,
        'cac': cac,
        'roi': roi,
    })
```

Notas:
- `created_at__gte=campanha.data_inicio` — `data_inicio` é `DateField` e
  `created_at` é `DateTimeField`; comparação funciona (Django converte
  a data para o início do dia), sem necessidade de cast manual.
- `cac` e `roi` retornam `null` (não `0` nem erro) quando o divisor é
  zero — regra explícita do pedido, evitar `ZeroDivisionError` e evitar
  o valor enganoso `0`.
- `leads_qs` filtra `is_active=True` — lead excluído (soft delete) não
  deve contar no ROI, mesmo que já tenha sido convertido antes (decisão
  do Analista: manter simetria com o resto do sistema, que sempre
  exclui `is_active=False` das contagens operacionais).

### RF05 — Perfil "Marketing"

Ver decisão de arquitetura na seção 4. Resumo de implementação:

```python
# accounts/models.py
class PerfilUsuario(models.TextChoices):
    ADMIN = 'ADMIN', 'Admin'
    OPERACIONAL = 'OPERACIONAL', 'Operacional'
    MARKETING = 'MARKETING', 'Marketing'

class User(AbstractBaseUser, PermissionsMixin):
    ...
    perfil = models.CharField(
        'perfil', max_length=12,
        choices=PerfilUsuario.choices, default=PerfilUsuario.OPERACIONAL,
    )
```

```python
# common/permissions.py
class IsMarketing(BasePermission):
    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and (u.perfil == 'MARKETING' or u.is_staff))
```

Uso nos ViewSets do módulo:
```python
class CampanhaViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdmin | IsMarketing]
    ...

class LeadViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdmin | IsMarketing]
    ...
```

RN08 (nova, formalizada pelo Analista): módulos Financeiro, RH e PDV
**não mudam** — continuam exigindo `IsAdmin` (`is_staff`) puro, sem
`IsMarketing` na composição. `perfil='MARKETING'` dá acesso **apenas**
a Campanha/Lead/ROI — nunca a Financeiro/RH/PDV/Usuários.

**Exposição do campo `perfil` ao frontend** — obrigatório para RF06
funcionar (Sidebar decide visibilidade no cliente):
- `accounts/serializers.py::UserSerializer` (usado em `GET /accounts/me/`
  — é o que preenche `authStore.user`): adicionar `'perfil'` em `fields`
  e em `read_only_fields` (usuário comum não pode alterar o próprio
  perfil via `/me/`).
- `accounts/serializers.py::UserAdminSerializer` (tela de Usuários,
  `IsAdmin`): adicionar `'perfil'` em `fields` — é o Admin quem define o
  perfil MARKETING de outro usuário, via `PATCH /accounts/usuarios/{id}/`.

### RF06 — Menu Marketing na Sidebar (frontend)

```jsx
{ to: '/marketing/campanhas', label: 'Campanhas', icon: '📣', marketingOnly: true }
{ to: '/marketing/leads', label: 'Leads', icon: '📣', marketingOnly: true }
```

Visibilidade: `isStaff || user?.perfil === 'MARKETING'` — mesmo padrão
booleano já usado para o item `staffOnly` (`Usuários`), estendido com a
condição de perfil. Ícone único 📣 para o grupo Marketing (submenu
Campanhas/Leads), consistente com os demais itens emoji da Sidebar —
nunca Lucide/ícone de lib nesse componente (regra já documentada nas
manutenções anteriores, ex. #10 DIV-UI03).

---

## 6. Requisitos Não Funcionais (RN)

```
RN01 - DecimalField para todo campo monetário (orcamento, receita_fechada,
       cac, roi em base percentual) — NUNCA float. [já contemplado nos
       models/cálculos acima]
RN02 - Soft delete via BaseModel (is_active=False) em Campanha e Lead —
       NUNCA objeto.delete()
RN03 - Autenticação por e-mail (já existente, USERNAME_FIELD='email') —
       não alterar
RN04 - Frontend consome via response.data.results (paginação DRF padrão)
       em Campanhas e Leads — mesmo padrão dos demais módulos
RN05 - id = serializers.IntegerField(source='pk', read_only=True) como
       primeiro campo em CampanhaSerializer e LeadSerializer
RN06 - Lead.status='convertido' é irreversível via API (RF03) — a action
       /converter/ bloqueia segunda chamada com 400; não expor PATCH
       direto de status='convertido' → 'novo'/outro no serializer padrão
       (campo status editável via PATCH normal para os demais valores,
       mas não deve permitir voltar de 'convertido')
RN07 - Campanha excluída (is_active=False) mantém histórico de Leads —
       FK campanha em Lead usa SET_NULL, não CASCADE nem PROTECT;
       queryset padrão de Lead não filtra por campanha.is_active (lead
       antigo continua visível mesmo se a campanha for arquivada depois)
RN08 - Financeiro/RH/PDV/Usuários continuam exigindo IsAdmin (is_staff)
       puro — perfil MARKETING nunca dá acesso a esses módulos
```

---

## 7. Especificação Backend (para o Forge)

```
Novo app: backend/marketing/
├── migrations/0001_initial.py   → Campanha, Lead
├── models.py                    → RF01, RF02
├── serializers.py                → CampanhaSerializer, LeadSerializer
│                                    (RN05 — id explícito),
│                                    campos *_display para choices
├── views.py                     → CampanhaViewSet (+ action roi),
│                                    LeadViewSet (+ action converter)
├── urls.py                      → DefaultRouter, registrar 'campanhas'
│                                    e 'leads' (padrão de accounts/urls.py,
│                                    não raiz única como clientes/urls.py,
│                                    porque marketing tem 2 recursos)
├── admin.py                     → registro básico (padrão dos demais apps)
└── tests.py                     → cobertura mínima: CRUD Campanha/Lead,
                                     conversão (com e sem duplicidade de
                                     e-mail), ROI (com 0 leads convertidos
                                     → cac/roi null; com orcamento=0 →
                                     roi null), soft delete, RN06, RN07,
                                     permissão IsMarketing vs usuário comum

Alterações em apps existentes:
- backend/core/settings.py → adicionar 'marketing' em LOCAL_APPS
- backend/core/urls.py → path('api/v1/marketing/', include('marketing.urls'))
- backend/accounts/models.py → campo perfil (RF05) + migration nova em
  accounts/migrations/ (0002_user_perfil.py)
- backend/accounts/serializers.py → UserSerializer e UserAdminSerializer
  expõem 'perfil' (ver RF05, obrigatório para o frontend funcionar)
- backend/common/permissions.py → IsMarketing (RF05)

urls.py do marketing (padrão a seguir — ver accounts/urls.py como
referência de múltiplos recursos no mesmo app):
    router = DefaultRouter()
    router.register('campanhas', CampanhaViewSet, basename='campanha')
    router.register('leads', LeadViewSet, basename='lead')
    urlpatterns = router.urls
```

**Atenção Forge:** `Pedido` está em `vendas.models` — import cruzado
`from vendas.models import Pedido` dentro de `marketing/views.py`. Não
há import circular (vendas não importa marketing).

---

## 8. Especificação Frontend (para o Loom)

```
Novas páginas:
- frontend/src/pages/marketing/Campanhas.jsx
- frontend/src/pages/marketing/Leads.jsx

Padrão a seguir (mesmo de Clientes.jsx/Produtos.jsx):
- Card + Button + Input + Select + Modal + Pagination (components/ui/)
- api/client.js para chamadas HTTP, extractErrorMessage nos catches
- response.data.results (RN04)
- dark mode com tokens navy-*/violet-* já estabelecidos (Manutenção #31)
- Plus Jakarta Sans + DM Sans (fontes já globais, nenhuma ação nova)

Campanhas.jsx:
- Listagem com filtro por status/canal, CRUD via Modal
- Card por campanha exibindo orçamento, status e um botão "Ver ROI"
  que chama GET /marketing/campanhas/{id}/roi/ e abre modal/seção com
  leads_total, leads_convertidos, orcamento, receita_fechada, cac, roi
  — exibir "—" quando cac/roi vier null (nunca "R$ NaN" ou "0")

Leads.jsx:
- Listagem com filtro por status/campanha, CRUD via Modal
- Select de campanha populado via GET /marketing/campanhas/ (apenas
  is_active=True, status != encerrada é sugestão de UX, não bloqueio)
- Botão "Converter em Cliente" visível apenas quando status != convertido
  → POST /marketing/leads/{id}/converter/ → toast de sucesso + refresh
  da linha (RN06: botão desaparece/desabilita após convertido)

Sidebar.jsx (RF06):
- Novo item de menu (ou 2 itens agrupados) — icon: '📣', visibilidade
  condicionada a isStaff || user?.perfil === 'MARKETING'

routes/index.jsx:
- Novo helper de rota (padrão StaffRoute) para perfil Marketing:
    function MarketingRoute({ children }) {
      const isStaff = useAuthStore((s) => s.user?.is_staff)
      const perfil = useAuthStore((s) => s.user?.perfil)
      if (!isStaff && perfil !== 'MARKETING') return <Navigate to="/dashboard" replace />
      return children
    }
- <Route path="/marketing/campanhas" element={<MarketingRoute><Campanhas /></MarketingRoute>} />
- <Route path="/marketing/leads" element={<MarketingRoute><Leads /></MarketingRoute>} />

Usuarios.jsx (tela existente, IsAdmin):
- Select de perfil (ADMIN/OPERACIONAL/MARKETING) no formulário de
  criar/editar usuário — sem isso, Admin não tem como promover ninguém
  a Marketing pela UI (ficaria só via admin do Django, o que quebra o
  fluxo operacional do pedido)
```

---

## Atores e Perfis

```
ADMIN (is_staff=True)      → acesso total, inclusive Marketing
MARKETING (perfil=MARKETING) → acesso apenas a Campanhas, Leads e ROI
OPERACIONAL (default)      → sem acesso a Marketing (mesma regra atual,
                              sem mudança de comportamento para o restante
                              do sistema)
```

---

## Fora do Escopo (Won't — MoSCoW)

```
- Integração real com plataformas de Ads/redes sociais (importação
  automática de leads via API do Facebook/Google Ads) — pedido é
  cadastro manual/CRUD
- Django Groups/Permissions granulares — decisão de arquitetura (seção 4)
  optou pelo campo perfil simples para este escopo
- Funil de Lead com múltiplos estágios além dos 4 status definidos
  (novo/qualificado/convertido/descartado)
- Edição de status='convertido' de volta para outro status via API
  (RN06) — se for necessário desfazer, é ação manual via admin do
  Django, não faz parte do fluxo operacional normal
- Dashboards/gráficos de ROI agregando todas as campanhas numa view só
  — RF04 é por campanha individual; visão agregada fica para uma
  manutenção futura se houver demanda
- Reatribuição de perfil em massa — troca de perfil é 1 a 1, via tela
  de Usuários já existente
```

## Riscos e Dependências

```
- RISCO: cálculo de receita_fechada usa created_at__gte=campanha.
  data_inicio sem limite superior (data_fim) — decisão deliberada: uma
  venda fechada depois do fim da campanha ainda é atribuível a ela
  (ciclo de vendas B2B costuma ser mais longo que a campanha). Se o
  cliente achar contra-intuitivo, ajustar em manutenção futura — não
  bloqueante para esta entrega, mas documentar no teste do Sentinel
  para não ser confundido com bug.
- RISCO: Lead sem e-mail sempre cria Cliente novo na conversão (RF03) —
  pode gerar Cliente duplicado se dois leads sem e-mail forem, na
  prática, a mesma pessoa. Aceito conscientemente: não há chave segura
  de deduplicação sem e-mail/documento, e o pedido não trouxe CPF/CNPJ
  no cadastro de Lead.
- DEPENDÊNCIA: migration nova em accounts (0002_user_perfil) — Forge
  deve rodar makemigrations/migrate em dev antes do Sentinel validar;
  nenhuma migration pendente hoje no app accounts (só 0001_initial),
  então não há conflito de numeração esperado.
- DEPENDÊNCIA: RF04 depende de vendas.Pedido.valor_total e
  vendas.Pedido.cliente — ambos já existentes e estáveis, confirmado
  em vendas/models.py, sem mudança necessária nesse app.
- RISCO BAIXO: se o Admin nunca usar a tela de Usuários para promover
  alguém a MARKETING (RF05 exige isso no frontend), o perfil fica
  inacessível na prática — Loom não pode esquecer o Select de perfil em
  Usuarios.jsx (ver seção 8), senão a feature existe no backend mas é
  inutilizável pela UI.
```

---

## Critérios de Aceite (para o Sentinel)

```
CA-01 - POST /api/v1/marketing/campanhas/ com dados válidos → 201
CA-02 - GET /api/v1/marketing/campanhas/ retorna response.data.results
        paginado, apenas is_active=True
CA-03 - DELETE em campanha → 204, is_active=False no banco (soft delete,
        RN02), nunca remove a linha do banco
CA-04 - POST /api/v1/marketing/leads/ com campanha válida → 201, lead
        vinculado corretamente
CA-05 - POST /api/v1/marketing/leads/ sem campanha (null) → 201 (RF02
        permite lead sem origem paga)
CA-06 - POST .../leads/{id}/converter/ em lead com e-mail que já existe
        em Cliente ativo → vincula ao Cliente existente, não duplica
        (RF03)
CA-07 - POST .../leads/{id}/converter/ em lead com e-mail novo → cria
        Cliente novo com origem=nome da campanha (ou 'Sem campanha')
CA-08 - POST .../leads/{id}/converter/ chamado 2x no mesmo lead → 2ª
        chamada retorna 400 (RN06, irreversibilidade)
CA-09 - GET .../campanhas/{id}/roi/ com 0 leads convertidos → cac=null,
        roi calculado normalmente se orcamento>0
CA-10 - GET .../campanhas/{id}/roi/ com orcamento=0 → roi=null,
        cac calculado normalmente se leads_convertidos>0
CA-11 - GET .../campanhas/{id}/roi/ com leads convertidos e Pedido(s)
        fechado(s) para o(s) Cliente(s) correspondente(s) → receita_fechada
        soma corretamente (testar com 2+ pedidos do mesmo cliente)
CA-12 - Usuário com perfil=OPERACIONAL (is_staff=False) → 403 em
        qualquer endpoint /marketing/*
CA-13 - Usuário com perfil=MARKETING (is_staff=False) → 200 em
        /marketing/campanhas/ e /marketing/leads/, 403 em
        /financeiro/*, /rh/*, /pdv/* (RN08)
CA-14 - Usuário is_staff=True (ADMIN) → 200 em /marketing/* mesmo com
        perfil=OPERACIONAL (is_staff sempre passa, RF05)
CA-15 - GET /api/v1/accounts/me/ retorna campo perfil no payload
CA-16 - PATCH /api/v1/accounts/usuarios/{id}/ (por Admin) altera perfil
        de um usuário para MARKETING com sucesso
CA-17 - Frontend: item Marketing na Sidebar visível para is_staff e
        para perfil=MARKETING, ausente para OPERACIONAL comum
CA-18 - Frontend: telas Campanhas e Leads funcionando ponta a ponta
        contra a API real (criar, editar, excluir, converter, ver ROI)
CA-19 - Frontend: Select de perfil disponível em Usuarios.jsx para o Admin
CA-20 - npm run build limpo (0 erros)
CA-21 - Testes Django cobrindo RF01-RF05 e RN01-RN08 (mínimo — ver
        backend/marketing/tests.py na seção 7)
```

---

## Passagem de bastão

```
✅ Solicitação classificada — UidCore (OS #7)
   tipo: feature_grande
   descricao_tecnica: novo app marketing (Campanha + Lead + ação
     converter + endpoint ROI/CAC) + perfil Marketing via campo
     accounts.User.perfil (decisão de arquitetura documentada na
     seção 4) + IsMarketing permission + telas Campanhas/Leads +
     item de Sidebar condicionado a perfil
   caminho_afetado:
     backend: novo app marketing/ (models, serializers, views, urls,
       migration, tests) + accounts/models.py (perfil) +
       accounts/serializers.py (expor perfil) + common/permissions.py
       (IsMarketing) + core/settings.py + core/urls.py
     frontend: pages/marketing/Campanhas.jsx (novo),
       pages/marketing/Leads.jsx (novo), Sidebar.jsx, routes/index.jsx,
       Usuarios.jsx (Select de perfil)
   requer_aprovacao_comercial: false (módulo já definido e detalhado
     pelo pedido — sem lacuna a confirmar com o cliente)
➡️  Planner: rotear para Forge (backend) + Loom (frontend) em paralelo.
    Módulo novo com model novo + permissão nova → Sentinel deve validar
    os 21 critérios de aceite acima, com atenção especial a CA-12/13/14
    (isolamento de permissão entre perfis) antes de liberar para o Pilot.
```
