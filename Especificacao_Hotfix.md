# Especificação — Manutenção #44
**Elaborado por:** Analista (MODO HOTFIX)
**Data:** 2026-08-19
**Sistema:** UidCore (OS #7)

**Solicitação original (resumida):**
"Implementar gestão de Usuários e vínculo Colaborador→Usuário no UidCore."
Contexto técnico informado como já existente em diff não commitado (backend
`accounts` e `rh`) e trabalho pendente listado pelo solicitante: (1) gerar a
migration da FK `usuario` em `Colaborador` — só depois de revisar o backend
completo; (2) revisar e commitar o backend; (3) frontend completo — tela
Usuários (CRUD admin) e tela/form de Colaborador com toggle "Criar acesso ao
sistema"; (4) validar os fluxos de criação com/sem acesso e o CRUD de
usuário pela tela admin.

---

## Classificação

```
tipo: feature_pequena
sistema: UidCore
caminho_afetado: backend/accounts/ (serializers.py, urls.py, views.py — já em diff)
                 backend/rh/ (models.py, serializers.py, views.py — já em diff)
                 backend/rh/migrations/ (nova migration da FK usuario — AINDA NÃO GERADA)
                 frontend/src/pages/Usuarios.jsx (novo)
                 frontend/src/pages/Rh.jsx (aba Colaboradores)
                 frontend/src/components/ui/ResourceCrud.jsx (extensão — ver RF-08)
                 frontend/src/routes/index.jsx, frontend/src/components/layout/Sidebar.jsx
complexidade: media
requer_aprovacao_comercial: false
```

---

## Diagnóstico confirmado (leitura direta do diff e dos arquivos — não do pedido)

Lido `git diff HEAD` nos 6 arquivos indicados + arquivos correlatos
(`accounts/models.py`, `accounts/services.py`, `accounts/managers.py`,
`common/permissions.py`, `rh/models.py`, `rh/urls.py`, `core/settings.py`,
`core/urls.py`, `frontend/src/components/ui/ResourceCrud.jsx`,
`frontend/src/pages/Rh.jsx`, `frontend/src/routes/index.jsx`,
`frontend/src/components/layout/Sidebar.jsx`, `frontend/src/stores/authStore.js`).

### O que já está pronto no diff (confirmado linha a linha)

- `UserAdminSerializer` (accounts/serializers.py): CRUD completo de `User`,
  `id = IntegerField(source='pk')` no padrão do projeto, senha write-only
  opcional (vazio → `set_unusable_password()`), `colaborador_nome` read-only.
- `UserViewSet` (accounts/views.py): `ModelViewSet` com `IsAdmin`,
  `SearchFilter` em `email`/`nome_completo`, `destroy` faz soft-disable
  (`is_active=False`), **não é soft delete por `deleted_at`** — `User` não
  herda `BaseModel`, é o `is_active` nativo do `AbstractBaseUser` do Django.
- Rota real: `router.register('usuarios', UserViewSet, basename='usuario')`
  dentro de `accounts/urls.py`, incluído em `core/urls.py` como
  `path('api/v1/accounts/', include('accounts.urls'))`. **Caminho final
  correto é `/api/v1/accounts/usuarios/`**, não `/api/usuarios/` como
  citado de forma simplificada no pedido — usar o caminho real na spec de
  frontend (RF-02) para não gerar 404.
- `Colaborador.usuario` (rh/models.py): `OneToOneField('accounts.User',
  null=True, blank=True, on_delete=SET_NULL, related_name='colaborador')`
  — correto, colaborador desligado não arrasta exclusão do usuário.
- `ColaboradorSerializer`: `tem_acesso` (`SerializerMethodField`, calcula
  `obj.usuario_id is not None`) + `usuario_email` read-only. A queryset do
  ViewSet já foi ajustada com `.select_related('cargo', 'usuario')`, então
  não gera N+1.
- `ColaboradorViewSet.perform_create`: cria o `User` vinculado quando o
  request manda `criar_usuario` truthy, só se `request.user.is_staff`,
  valida email (usa o do colaborador se `usuario_email` não vier, rejeita
  duplicado) e senha (mínimo 6, opcional → dispara `enviar_primeiro_acesso`
  já existente em `accounts/services.py`, reaproveitado sem duplicar lógica).
- `enviar_primeiro_acesso` / fluxo de definir senha por link (token de uso
  único, expira 24h) já existem e já têm 100% de cobertura de teste em
  `accounts/tests.py` — não precisa reimplementar, só reaproveitar.

### RN-CRÍTICA encontrada pelo Analista — ordem de operações em `perform_create` deixa Colaborador órfão em caso de erro

`ColaboradorViewSet.perform_create` (rh/views.py, linhas 43-92) faz, nesta ordem:

```python
colaborador = serializer.save()          # 1. Colaborador JÁ PERSISTIDO

criar_usuario = ...
if not criar_usuario:
    return
if not self.request.user.is_staff:
    raise PermissionDenied(...)           # 2. 403 -- mas o Colaborador do passo 1 continua salvo
...
if User.objects.filter(email__iexact=email).exists():
    raise ValidationError(...)            # 3. 400 -- mesmo problema
```

Cenário de falha real: um usuário autenticado **não-admin** manda
`criar_usuario=true` (ex.: bug de frontend, ou alguém testando a API
direto) → a API responde `403 Forbidden`, o frontend mostra erro e o
usuário acha que nada foi criado — **mas o registro de `Colaborador` já
está no banco**, sem usuário vinculado, sem nenhum aviso. Mesmo problema
se o e-mail já existir (`400`) ou a senha for curta (`400`): o
`Colaborador` fica órfão, e uma nova tentativa de "criar com acesso" pelo
mesmo formulário cria um **segundo** Colaborador duplicado.

Isso não é o comportamento "tudo ou nada" que os RFs abaixo pedem (RF-02/
RN-03) e é o tipo de bug que só aparece em produção, quando alguém erra o
e-mail ou a senha na hora de cadastrar. **Bloqueante para o Forge**: mover
toda a validação (permissão, e-mail duplicado, senha) para ANTES de
`serializer.save()`, ou envolver a criação do `Colaborador` + `User` no
mesmo bloco — ver RF-02/RN-03 abaixo. Reportado como diagnóstico, não
corrigido aqui — Analista não edita código.

### Lacuna encontrada — vincular usuário a Colaborador já existente não é suportado

O diff só resolve "criar colaborador COM acesso" (via `perform_create`).
Não existe `perform_update` equivalente: se um Colaborador foi criado SEM
acesso e depois o admin quiser liberar acesso (ou vincular um `User` já
existente), a API atual não tem esse caminho. Documentado como fora do
escopo desta manutenção (RN-07 / MoSCoW: Won't) — a menos que Luiz Eduardo
priorize antes do Sentinel validar.

---

## Requisitos Funcionais

```
RF-01 - O sistema deve corrigir a ordem de validação em
        ColaboradorViewSet.perform_create: toda validação relacionada a
        criar_usuario (permissão is_staff, e-mail obrigatório e não
        duplicado, tamanho mínimo de senha) deve ocorrer ANTES de
        persistir o Colaborador — ou a criação do Colaborador e do User
        devem estar no mesmo transaction.atomic com rollback conjunto em
        qualquer falha. Nenhum Colaborador órfão pode ficar no banco se
        a criação de acesso falhar.

RF-02 - O sistema deve ter a migration da FK Colaborador.usuario gerada e
        aplicada (rh/migrations/) — campo null=True/blank=True, sem default
        necessário, não deve pedir input interativo do makemigrations.
        Gerar SOMENTE depois do RF-01 estar implementado, para não gerar 2
        migrations por causa de um fix tardio no mesmo ciclo.

RF-03 - O sistema deve prover uma tela "Usuários" (nova página
        frontend/src/pages/Usuarios.jsx), acessível somente a
        administradores (is_staff), consumindo GET/POST/PATCH/DELETE em
        /api/v1/accounts/usuarios/:
        - Listagem: nome_completo, email, colaborador_nome (— se null),
          is_staff (badge), is_active (Sim/Não), date_joined.
        - Criar: email, nome_completo, telefone, password (opcional —
          texto de apoio "deixe em branco para enviar link de definição
          de senha por e-mail"), is_staff.
        - Editar: mesmos campos, password continua opcional ("deixe em
          branco para não alterar a senha atual").
        - "Excluir" na tela Usuários deve chamar DELETE (que no backend já
          faz soft-disable, is_active=False) e o rótulo do botão/confirm
          deve dizer "Desativar", não "Excluir" — evita o admin pensar que
          o registro foi apagado (RN-09).

RF-04 - O sistema deve prover uma ação "Reenviar acesso" por linha na
        tela Usuários, chamando POST /api/v1/accounts/solicitar-acesso/
        {usuario_id}. Endpoint já existe e já tem teste cobrindo (accounts/
        tests.py::SolicitarAcessoViewTest) — reaproveitar, não duplicar.
        Ação deve ficar desabilitada/oculta quando is_active=False (não
        faz sentido reenviar acesso pra usuário desativado).

RF-05 - O sistema deve adicionar, na aba "Colaboradores" de Rh.jsx:
        - Colunas novas na listagem: tem_acesso (badge Sim/Não),
          usuario_email (— se null).
        - No formulário de CRIAÇÃO (não edição — ver RN-08): checkbox
          "Criar acesso ao sistema" (nome: criar_usuario). Quando marcado,
          exibir dois campos adicionais: usuario_email (pré-preenchido com
          o e-mail do colaborador, editável) e usuario_senha (opcional,
          com o mesmo texto de apoio do RF-03).

RF-06 - O sistema deve exibir o item de menu "Usuários" na Sidebar
        (ícone sugerido: 👤) somente quando o usuário logado tiver
        is_staff=true (useAuthStore.user.is_staff — já vem do payload de
        /api/v1/accounts/me/, nenhuma mudança de backend necessária pra
        isso). Rota /usuarios deve barrar quem não é staff na própria UI
        (redirect para /dashboard), já que o backend vai rejeitar com 403
        mas a UI não deve nem oferecer o link.

RF-07 - O sistema deve validar no frontend, antes de enviar o POST de
        Colaborador com criar_usuario=true, que usuario_email não está
        vazio (mesma regra que o backend já aplica) — evita um round-trip
        de erro 400 desnecessário e dá feedback imediato.

RF-08 - (infraestrutura de frontend, necessária pros RF-03/RF-04/RF-05)
        ResourceCrud.jsx (componente genérico reaproveitado por 15+ telas
        do projeto) deve ganhar 3 capacidades novas, todas opt-in via
        props/campos — nenhuma tela existente pode mudar de comportamento:
        1. rowActions: array opcional de { label, onClick(item), variant,
           showIf(item) } renderizado ao lado de "Editar"/"Excluir" na
           coluna Ações — usado pelo RF-04.
        2. showIf(form) por field: função opcional que decide se o campo
           aparece no formulário, avaliada a cada render do form — usado
           pelo RF-05 (mostrar usuario_email/usuario_senha só quando
           criar_usuario estiver marcado).
        3. hideOnEdit por field: boolean opcional, esconde o campo
           inteiro quando editingId != null — usado pelo RF-05 (RN-08:
           esconder o bloco "criar acesso" inteiro na edição).
        4. deleteLabel customizável por tela (default mantém "Excluir" em
           todas as 15 telas existentes) — usado pelo RF-03 pra virar
           "Desativar" só na tela Usuários.
```

---

## Regras de Negócio

```
RN-01 - Somente is_staff=true pode acessar /api/v1/accounts/usuarios/
        (IsAdmin já implementado) e pode disparar criar_usuario=true em
        Colaborador (já implementado, mas com o bug de ordem — ver RF-01).

RN-02 - Um Colaborador só pode ter 1 usuário vinculado — já garantido pelo
        OneToOneField no model. Não há fluxo de "trocar" o usuário
        vinculado nesta manutenção (ver RN-07).

RN-03 - Ver "RN-CRÍTICA" no diagnóstico acima — criação de Colaborador +
        User deve ser tudo-ou-nada. Coberto por RF-01.

RN-04 - Se usuario_email não for enviado explicitamente ao criar acesso,
        o backend usa o e-mail do próprio Colaborador — o formulário do
        frontend deve deixar isso visível (campo pré-preenchido, não
        escondido), porque o Colaborador pode não ter e-mail cadastrado
        (campo é blank=True em Colaborador.email).

RN-05 - Senha em branco → conta criada com set_unusable_password() e
        link de primeiro acesso por e-mail (24h de validade). O envio de
        e-mail pode falhar silenciosamente (perform_create engole a
        exceção em `except Exception: pass`, comentário no próprio código
        diz "o admin pode reenviar depois pela tela Usuários") — RF-04
        existe justamente para cobrir essa falha; o frontend deve deixar
        claro (texto de apoio, não popup bloqueante) que a confirmação do
        envio de e-mail não é garantida.

RN-06 - Desativar (soft-disable) um Colaborador que tem usuário vinculado
        NÃO desativa o usuário automaticamente — nenhuma lógica no diff
        faz isso, o `usuario` permanece com is_active=True e continua
        logando após o colaborador ser desligado. Não é bug de código (o
        diff não promete esse comportamento), mas é um risco de processo
        real: documentado aqui para o Planner decidir se entra nesta
        manutenção ou numa seguinte — MoSCoW: Should, não Must, pois o
        pedido original não menciona desligamento. Se ficar de fora,
        registrar como pendência explícita no fechamento do Pilot.

RN-07 - Vincular um usuário existente (ou liberar acesso depois) a um
        Colaborador que já existe sem usuário: fora do escopo desta
        manutenção (backend não tem esse caminho — ver "Lacuna encontrada"
        no diagnóstico). MoSCoW: Won't (nesta rodada).

RN-08 - O checkbox "Criar acesso ao sistema" e os campos usuario_email/
        usuario_senha só aparecem no formulário de CRIAÇÃO de Colaborador,
        nunca na edição — o backend não tem lógica equivalente em update,
        então mostrar esses campos na edição seria oferecer algo que não
        funciona (payload seria ignorado silenciosamente pelo
        perform_update padrão do ModelViewSet).

RN-09 - "Excluir" na tela Usuários é soft-disable (is_active=False), não
        apaga o registro — rótulo de UI deve dizer "Desativar" (RF-03).

RN-10 - UserAdminSerializer permite editar is_staff de qualquer User,
        inclusive o do próprio admin logado. Risco: um admin remove o
        próprio is_staff e perde acesso à tela Usuários (não há outro
        admin pra reverter sem acesso direto ao banco/Django admin). O
        frontend deve pedir confirmação extra (window.confirm) quando o
        formulário estiver editando o id do usuário logado
        (useAuthStore.user.id) E desmarcando is_staff.

RN-11 - Padrões obrigatórios Uid respeitados pelo diff: autenticação por
        e-mail (USERNAME_FIELD='email', já era assim), paginação padrão
        do projeto (StandardPagination, response.data.results). Não se
        aplica: DecimalField (não há valor monetário neste módulo).
```

---

## Telas detalhadas

### Tela "Usuários" (nova) — rota `/usuarios`

```
Acesso: somente is_staff (RF-06)
Componente: ResourceCrud (com as extensões do RF-08)
Resource: accounts/usuarios  →  GET/POST/PATCH/DELETE /api/v1/accounts/usuarios/

Colunas:
  nome_completo | email | colaborador_nome (— se null) | is_staff (badge) | is_active (Sim/Não) | date_joined (data)

Ações por linha:
  Editar | Reenviar acesso (RF-04, oculta se is_active=false) | Desativar (RF-03/RN-09)

Formulário (criar/editar):
  email (obrigatório, type=email)
  nome_completo (obrigatório)
  telefone (opcional)
  password (opcional — texto de apoio conforme contexto criar/editar, RF-03)
  is_staff (checkbox — RN-10 na hora de submeter, se for o próprio usuário)
```

### Tela "RH" → aba "Colaboradores" (existente, Rh.jsx) — ajustes

```
Colunas novas: tem_acesso (badge Sim/Não) | usuario_email (— se null)

Formulário de CRIAÇÃO ganha, ao final:
  [ ] Criar acesso ao sistema        (checkbox, name=criar_usuario)
      └─ visível só quando marcado (RF-08 showIf):
         usuario_email  (pré-preenchido = email do colaborador, editável)
         usuario_senha  (opcional, texto de apoio "deixe em branco para
                          enviar link de definição de senha por e-mail")

Formulário de EDIÇÃO: bloco acima não aparece (RN-08/hideOnEdit)
```

---

## Especificação Backend (para o Forge)

```
1. Implementar RF-01 (RN-03) primeiro: mover as validações de permissão/
   e-mail/senha de ColaboradorViewSet.perform_create para ANTES de
   serializer.save(), ou envolver Colaborador.save() + User.save() no
   mesmo transaction.atomic com validação prévia fora do bloco atômico.
2. Só depois: gerar e revisar a migration da FK Colaborador.usuario
   (rh/migrations/, RF-02) — conferir que não introduz default nem pede
   input interativo (campo já null=True).
3. Escrever/completar testes (rh/tests.py e accounts/tests.py):
   - criar colaborador com criar_usuario=true por admin → sucesso, User
     criado, e-mail de primeiro acesso disparado (mock) quando sem senha.
   - criar colaborador com criar_usuario=true por usuário NÃO staff →
     403 e ZERO Colaborador e ZERO User persistidos (cobre RF-01/RN-03
     corrigido — este é o teste que vai pegar a regressão se o fix for
     desfeito no futuro).
   - criar_usuario=true com e-mail já existente → 400, zero registros
     órfãos.
   - criar_usuario=true com senha curta (<6) → 400, zero registros
     órfãos.
   - criar colaborador sem criar_usuario → sucesso, usuario=None,
     tem_acesso=False.
   - UserViewSet: list/create/update/partial_update/destroy (soft-disable)
     + SearchFilter por email e nome_completo, tudo só acessível a
     is_staff (403 pra usuário comum).
   - UserAdminSerializer: senha em branco no create → unusable password;
     senha preenchida no update → set_password chamado (checar hash
     mudou, não checar a senha em texto puro).
4. Confirmar rota final /api/v1/accounts/usuarios/ (já registrada em
   accounts/urls.py via router — não precisa mudança, só confirmar no
   teste de integração que bate com o que o frontend vai chamar).
5. RN-06 (desativar colaborador não desativa o usuário vinculado): não
   implementar nesta manutenção a menos que o Planner explicitamente
   priorize — está documentado como pendência conhecida, não como bug.
```

---

## Especificação Frontend (para o Loom)

```
1. ResourceCrud.jsx (frontend/src/components/ui/ResourceCrud.jsx) —
   extensão aditiva, ver RF-08 para as 4 capacidades exatas. Confirmar que
   as 15+ telas existentes (Clientes, Vendas, Financeiro, Rh abas
   cargos/folhas/ferias etc.) continuam funcionando sem nenhuma prop nova
   — todas as extensões são opt-in.

2. frontend/src/pages/Usuarios.jsx (novo) — usar ResourceCrud com
   resource="accounts/usuarios" e rowActions para "Reenviar acesso"
   (POST direto via api client em accounts/solicitar-acesso, não é um
   resource do ResourceCrud). deleteLabel="Desativar". Confirm de exclusão
   customizado avisando que é uma desativação, não uma remoção definitiva.

3. frontend/src/pages/Rh.jsx — aba colaboradores: adicionar colunas
   tem_acesso/usuario_email e os campos condicionais do formulário
   (criar_usuario checkbox + showIf + hideOnEdit conforme RF-08). Validar
   client-side (RF-07) antes do submit: se criar_usuario && !usuario_email
   → toast de erro, não envia.

4. frontend/src/routes/index.jsx — nova rota protegida `/usuarios`
   (dentro do mesmo <ProtectedRoute><AppLayout/></ProtectedRoute> das
   demais). Guardar contra acesso de não-staff (RF-06) — redirect simples
   para /dashboard se !user.is_staff, mesmo padrão de ProtectedRoute já
   usado no arquivo.

5. frontend/src/components/layout/Sidebar.jsx — novo item condicional a
   useAuthStore(s => s.user?.is_staff), inserido logo após "RH" (mesma
   área temática de gestão interna).

6. Fontes (Plus Jakarta Sans + DM Sans) e paleta navy/violet dark mode já
   cobertas pelos componentes reaproveitados (Card, Modal, Input, Select,
   ResourceCrud) — nenhuma tela nova introduz componente visual do zero,
   então não precisa de nova passagem do Brush.

7. RN-10 no formulário de edição de Usuários: antes de submeter, se
   editingId === useAuthStore.getState().user.id e is_staff está sendo
   desmarcado, window.confirm("Você está removendo seu próprio acesso de
   administrador. Continuar?") — cancelar aborta o submit.
```

---

## Critérios de Aceite

```
CA-01 - POST /api/v1/rh/colaboradores/ com criar_usuario=true por um
        usuário is_staff cria Colaborador + User vinculados (usuario_id
        preenchido), tem_acesso=true na resposta.
CA-02 - POST idêntico ao CA-01 mas por usuário NÃO staff retorna 403 e
        NÃO deixa nenhum Colaborador nem User órfão no banco (a
        verificação real é: contar registros antes e depois da chamada).
CA-03 - POST com criar_usuario=true e e-mail já existente retorna 400 e
        não deixa nenhum registro órfão (mesma verificação do CA-02).
CA-04 - POST com criar_usuario=true, senha=12345 (5 chars) retorna 400 e
        não deixa registro órfão.
CA-05 - POST sem criar_usuario cria Colaborador normalmente, usuario=null,
        tem_acesso=false.
CA-06 - Migration da FK Colaborador.usuario aplicada sem erro, 0 migrations
        pendentes pós-deploy (showmigrations --plan).
CA-07 - GET/POST/PATCH/DELETE em /api/v1/accounts/usuarios/ funcionam só
        para is_staff (403 para usuário comum autenticado, 401 sem
        autenticação).
CA-08 - DELETE em /api/v1/accounts/usuarios/{id}/ faz is_active=False
        (soft-disable) — usuário ainda existe no banco, só não consegue
        mais logar (checar via login real ou via query direta).
CA-09 - POST /api/v1/accounts/solicitar-acesso/ dispara e-mail (mockado
        no teste) para o usuário certo — endpoint já existente,
        confirmar que a tela nova consegue chamá-lo (integração, não
        unidade).
CA-10 - Tela Usuários carrega, lista, cria, edita e "desativa" um usuário
        via UI real (não só API) — rótulo do botão diz "Desativar".
CA-11 - Tela Colaboradores exibe tem_acesso/usuario_email nas colunas;
        checkbox "Criar acesso" some no formulário de edição (RN-08).
CA-12 - Item "Usuários" na Sidebar só aparece para usuário logado com
        is_staff=true (testar com um usuário comum logado — item não
        deve aparecer).
CA-13 - As 15+ telas existentes que usam ResourceCrud continuam
        funcionando sem alteração de comportamento após a extensão do
        RF-08 (regressão — revisão de pelo menos 2-3 telas
        representativas: Clientes, Vendas, Rh/cargos).
CA-14 - npm run build limpo, 0 erros.
CA-15 - Suíte Django completa (backend/) 0 falhas, incluindo os testes
        novos listados na Especificação Backend acima.
```

---

## Fora do Escopo (MoSCoW: Won't nesta rodada)

```
- Vincular um User já existente a um Colaborador que já existe sem acesso
  (RN-07) — requer endpoint novo, não pedido explicitamente no pedido
  original.
- Desativar automaticamente o User quando o Colaborador vinculado é
  desligado (RN-06) — risco documentado, decisão de priorização do
  Planner/Luiz Eduardo.
- Troca de e-mail de login do próprio usuário via "Meus Dados" (fora do
  escopo — este ciclo é só a tela ADMIN de gestão de usuários).
```

---

## Observações finais do Analista

- O diff fornecido já resolve boa parte do trabalho de backend — o que
  falta não é "escrever do zero", é (1) corrigir a ordem de validação em
  `perform_create` antes de gerar a migration (RF-01, achado do Analista,
  não estava no pedido), e (2) o frontend completo, que ainda não existe.
- `backend/test_whitelist_pdv.py` (resíduo vazio, já documentado desde a
  Manutenção #22) segue untracked — não faz parte desta manutenção, não
  mexer.
- Nenhum requisito aqui contradiz os padrões obrigatórios Uid (soft
  delete/soft-disable, autenticação por e-mail, paginação padrão,
  `response.data.results`) — confirmado por leitura direta, não por
  suposição.

---

➡️ **Planner: rotear para Pipeline B (manutenção sobre módulo existente) —
Forge (backend/accounts/, backend/rh/ — RF-01/RF-02 e testes) + Loom
(frontend/src/pages/Usuarios.jsx novo, Rh.jsx, ResourceCrud.jsx, routes/
index.jsx, Sidebar.jsx — RF-03 a RF-08) em paralelo → Sentinel (validar
CA-01 a CA-15, com atenção especial a CA-02/CA-03/CA-04 por cobrirem a
RN-CRÍTICA de registro órfão) → Pilot.**
