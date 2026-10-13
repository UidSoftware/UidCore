# Especificação Hotfix — Manutenção #65 [NUCLEO 4/5]
## Agenda com capacidade (vagas) + agendamento público

**Sistema:** UidCore (OS #7)
**Data:** 2026-10-13
**Autor:** Analista (modo manutenção)
**Origem:** melhoria de núcleo migrada da análise do NosFluir (SlotExperimental +
AgendamentoExperimental vindo do site) — fase única do pacote [NUCLEO] (4/5),
independente das outras fases.

---

## 1. Contexto

### AS-IS (como é hoje)
O app `agendamento` do UidCore é um calendário de CRM básico. Modelos existentes:

- `Agenda`: nome, descrição, cor, profissional (FK User), is_active — sem slug,
  sem controle de vagas, sem acesso público.
- `Compromisso`: agenda (FK), título, descrição, início, fim, local, cliente (FK),
  status (AGENDADO/CONFIRMADO/CANCELADO/CONCLUÍDO), observações — sem vínculo
  a horários padronizados, sem origem interna/pública, sem dados de contato
  avulso (para quem não é cliente cadastrado).

Não existe verificação de capacidade. Qualquer número de compromissos pode ser
criado para o mesmo horário. Não há endpoint público (sem autenticação).

### Lição real que vira requisito obrigatório
No NosFluir, a validação de vagas do agendamento público (RN-AGE-01) foi
**documentada mas nunca implementada**. Resultado: um horário com capacidade 2
aceitava o 3º, o 4º e qualquer número subsequente de agendamentos. Esta
especificação transforma essa falha em critério de aceite com **teste de
concorrência obrigatório** (CA-03).

### TO-BE (o que esta manutenção entrega)
1. Novo model `HorarioDisponivel` — grade de horários por agenda com vagas,
   rótulo, flag público e ativo.
2. `Compromisso` ampliado — FK para `HorarioDisponivel` (opcional), origem
   INTERNO/PÚBLICO, campos de contato para agendamento sem cliente cadastrado.
3. Validação de vaga atômica com `select_for_update` + `transaction.atomic()`
   — bloqueio real em concorrência, não só checagem soft.
4. Aviso de conflito (não bloqueio) — se o mesmo cliente já tem compromisso
   sobreposto, retorna aviso no response mas não impede o agendamento.
5. API pública sem autenticação:
   - `GET /api/v1/publico/agenda/{slug}/disponibilidade/`
   - `POST /api/v1/publico/agenda/{slug}/agendar/`
   - Throttle por IP (10 req/h) + validação de telefone.
6. Frontend interno: cadastro de horários disponíveis + painel de ocupação
   "X/Y vagas" + lista de pendentes por agenda.
7. Frontend público: página `/agendar/{slug}` (sem login, mobile-first 375px).

---

## 2. Requisitos Funcionais

### Backend

**RF-01** — `Agenda` ganha dois campos novos:
- `slug`: CharField único, gerado automaticamente a partir do nome (slugify),
  editável pelo operador. Usado na URL pública.
- `permite_agendamento_publico`: BooleanField, default=False.

**RF-02** — Novo model `HorarioDisponivel(BaseModel)`:
- `agenda`: FK para Agenda, on_delete=PROTECT
- `dia_semana`: IntegerField com choices 0=Seg … 6=Dom
- `hora_inicio`: TimeField
- `duracao_minutos`: PositiveIntegerField (mínimo 5)
- `vagas`: PositiveIntegerField (mínimo 1)
- `servico`: CharField (rótulo livre, ex: "Avaliação" / "Consulta 30min")
- `publico`: BooleanField default=True
- `ativo`: BooleanField default=True (campo próprio de negócio — distinto do
  `is_active` de `BaseModel` que é o soft delete; aqui "ativo" significa
  "este horário está sendo ofertado", pode ser desativado temporariamente
  sem apagar o registro)

**RF-03** — `Compromisso` ganha cinco campos novos (todos opcionais para
compatibilidade retroativa):
- `horario`: FK para HorarioDisponivel, null=True, blank=True
- `data_horario`: DateField, null=True, blank=True — data concreta do horário
  (necessária pois `HorarioDisponivel` define dia da semana + hora, não uma
  data absoluta; o Compromisso precisa saber em qual data específica o slot
  foi ocupado para contagem de vagas)
- `origem`: CharField choices INTERNO/PUBLICO, default=INTERNO
- `nome_contato`: CharField max_length=255, blank=True
- `telefone_contato`: CharField max_length=20, blank=True
- `email_contato`: EmailField, blank=True

**RF-04** — Validação de vaga (BLOQUEANTE):
Ao criar um Compromisso vinculado a um `HorarioDisponivel`, o sistema deve:
1. Entrar em `transaction.atomic()`.
2. Fazer `select_for_update()` no `HorarioDisponivel` relacionado.
3. Contar compromissos não cancelados para o mesmo `horario` + `data_horario`
   (status != CANCELADO, is_active=True).
4. Se contagem >= vagas → retornar HTTP 400 com `{"erro": "Horário sem vagas disponíveis."}`.
5. Caso contrário → criar o compromisso dentro da mesma transação.

Esta validação se aplica tanto à criação interna (autenticada) quanto ao
endpoint público.

**RF-05** — Aviso de conflito de horário para o mesmo cliente (NÃO BLOQUEANTE):
Se `cliente` for informado e já existir compromisso ativo (não cancelado) com
`inicio <= novo_fim` e `fim >= novo_inicio`, retornar HTTP 201 normalmente com
campo extra `{"aviso": "Cliente já possui compromisso no mesmo período."}` no
response.

**RF-06** — Endpoint público de disponibilidade:
`GET /api/v1/publico/agenda/{slug}/disponibilidade/?de=AAAA-MM-DD&ate=AAAA-MM-DD`
- Acesso: AllowAny.
- Requer que `Agenda.permite_agendamento_publico = True`; caso contrário 404.
- Retorna apenas horários com `publico=True` e `ativo=True`.
- Para cada dia no intervalo, calcula os slots do dia da semana correspondente
  e retorna: `{data, dia_semana, hora_inicio, duracao_minutos, servico, vagas,
  vagas_ocupadas, vagas_disponiveis}`.
- Vagas ocupadas = compromissos com status != CANCELADO para aquele
  `horario` + `data_horario`.
- Slots com `vagas_disponiveis == 0` são retornados com flag `lotado: true`
  (cliente vê, mas não pode agendar).
- Limite de intervalo: máximo 60 dias. Se `ate - de > 60` → 400.

**RF-07** — Endpoint público de agendamento:
`POST /api/v1/publico/agenda/{slug}/agendar/`
- Acesso: AllowAny.
- Throttle por IP: 10 requisições por hora (AnonRateThrottle).
- Payload obrigatório:
  ```json
  {
    "horario_id": <int>,
    "data_horario": "AAAA-MM-DD",
    "nome_contato": "<string>",
    "telefone_contato": "<string>",
    "email_contato": "<string, opcional>"
  }
  ```
- Validações:
  - `horario_id` deve pertencer à agenda do slug e ter `publico=True` e `ativo=True`.
  - `data_horario` deve corresponder ao `dia_semana` do horário.
  - `telefone_contato` obrigatório, mínimo 8 dígitos (apenas dígitos após strip de
    caracteres não numéricos).
  - Aplica RF-04 (validação de vaga com lock).
- Response 201: `{"id": <int>, "mensagem": "Agendamento confirmado."}`.
- Response 400 com vaga esgotada: `{"erro": "Horário sem vagas disponíveis."}`.
- Não vaza dados de outros clientes: resposta não inclui nome/telefone de
  quem já agendou, apenas contagem de vagas.

**RF-08** — Throttle configurado via `DEFAULT_THROTTLE_CLASSES` e
`DEFAULT_THROTTLE_RATES` no settings (ou `throttle_classes` na view
pública). Rate: `anon: "10/hour"`.

**RF-09** — `Agenda` endpoint interno (`/api/v1/agendamento/agendas/`) atualizado:
- Serializer passa a incluir `slug` e `permite_agendamento_publico`.
- Slug deve ser validado como único no `validate_slug` do serializer.
- Se slug não for enviado no POST, gerar automaticamente a partir do `nome`
  (usando `django.utils.text.slugify`).

**RF-10** — Endpoint interno de horários disponíveis:
`/api/v1/agendamento/horarios-disponiveis/` — CRUD completo (ModelViewSet),
autenticado. Filtros por `agenda`, `dia_semana`, `publico`, `ativo`.

**RF-11** — Endpoint interno de ocupação:
`GET /api/v1/agendamento/horarios-disponiveis/{id}/ocupacao/?data=AAAA-MM-DD`
— retorna `{vagas, vagas_ocupadas, vagas_disponiveis, compromissos: [...]}`.
Action extra no ViewSet (não rota separada).

### Frontend Interno

**RF-12** — Tela Agendamento.jsx ganha aba "Horários" (ao lado de "Agenda" e
"Calendário" já existentes):
- Lista os `HorarioDisponivel` da agenda selecionada.
- Permite criar/editar/desativar horários.
- Cada linha exibe: dia da semana, hora início, duração, serviço, vagas,
  badge "Público" ou "Privado", toggle ativo/inativo.

**RF-13** — Na aba "Calendário" (ou na lista de compromissos), cada slot de
horário exibe badge de ocupação "X/Y vagas" calculado para o dia sendo
visualizado.

**RF-14** — Painel "Pendentes" (lista de compromissos com `origem=PUBLICO` e
`status=AGENDADO`): nome_contato, telefone_contato, data_horario, serviço.
Botões: Confirmar (→ CONFIRMADO) e Cancelar (→ CANCELADO).

**RF-15** — Formulário de Compromisso interno atualizado para incluir:
- Campo select de `HorarioDisponivel` (filtrado pela agenda selecionada).
- Campo `data_horario` (date picker, obrigatório quando horario for selecionado).
- Campo `origem` (read-only na edição, exibe INTERNO ou PÚBLICO).
- Campos `nome_contato` / `telefone_contato` / `email_contato` (visíveis
  quando `cliente` não estiver preenchido).

### Frontend Público

**RF-16** — Página `/agendar/{slug}` (rota pública, sem ProtectedRoute):
- Mobile-first: viewport alvo 375px, testado até 1280px.
- Header com nome e descrição da agenda.
- Seletor de data (calendário inline ou navegação semana a semana).
- Lista de horários disponíveis do dia: serviço, hora início, duração,
  vagas disponíveis. Slots lotados exibidos como indisponíveis (cinza).
- Ao clicar num slot disponível → formulário de dados de contato:
  nome (obrigatório), telefone (obrigatório), email (opcional).
- Botão "Confirmar Agendamento" → POST para o endpoint público.
- Feedback de sucesso: mensagem "Agendamento confirmado!" com data e hora.
- Feedback de erro de vaga esgotada: "Este horário foi preenchido.
  Escolha outro." (sem expor detalhes técnicos).
- Feedback de throttle (429): "Muitas tentativas. Aguarde antes de tentar
  novamente."
- Sem autenticação, sem JWT.

---

## 3. Regras de Negócio

**RN-01** — Validação de vaga é ATÔMICA com `select_for_update` dentro de
`transaction.atomic()`. Não existe "checar antes e criar depois" — essa
janela de race condition foi a causa do bug no NosFluir. A contagem e a
criação acontecem dentro da mesma transação com lock no row do
`HorarioDisponivel`.

**RN-02** — Compromisso sem `horario` (agendamentos avulsos, estilo CRM antigo)
continua funcionando exatamente como antes. A validação de vagas só se aplica
quando `horario` for informado. Compatibilidade retroativa total.

**RN-03** — Slug da Agenda deve ser único no banco (unique=True no model).
Dois slugs iguais — mesmo que em agendas de clientes diferentes do mesmo
UidCore — não são permitidos. O endpoint público usa apenas o slug para
localizar a agenda.

**RN-04** — `data_horario` deve coincidir com o `dia_semana` do
`HorarioDisponivel` referenciado. Ex.: se o horário é `dia_semana=0` (segunda),
a data informada deve ser uma segunda-feira. Validação no serializer público
e no serializer interno.

**RN-05** — O endpoint público não retorna dados pessoais de outros
agendamentos. A resposta de disponibilidade só traz contagens agregadas
(`vagas_ocupadas`, `vagas_disponiveis`), nunca nomes ou telefones.

**RN-06** — Throttle do endpoint público é por IP (`REMOTE_ADDR`). Ao atingir
o limite, retornar HTTP 429 com body `{"erro": "Limite de agendamentos atingido.
Tente novamente em 1 hora."}`.

**RN-07** — Agendamento público cria um `Compromisso` com `origem=PUBLICO`,
`status=AGENDADO`, `cliente=None`. O operador interno pode posteriormente
vincular a um cliente cadastrado editando o compromisso.

**RN-08** — `HorarioDisponivel.ativo=False` impede novos agendamentos para
aquele slot (tanto interno quanto público), mas não cancela compromissos já
existentes.

**RN-09** — O aviso de conflito (RF-05) só é emitido quando `cliente` for
preenchido. Agendamentos públicos (sem cliente) não recebem esse aviso.

**RN-10** — O intervalo máximo de consulta na disponibilidade pública é 60
dias. Intervalos maiores retornam 400 com mensagem explicativa.

---

## 4. Spec Técnica Backend

### 4.1 Migrations

**Migration `agendamento.0008_agenda_slug_publico`:**
- Adiciona `Agenda.slug` (varchar, unique, null inicialmente para rodar em
  produção sem travar — preencher com RunPython para registros existentes
  antes de colocar NOT NULL, ou simplesmente `blank=True, null=True` e
  deixar obrigatório só na UI).
- Adiciona `Agenda.permite_agendamento_publico` (boolean, default=False).

**Migration `agendamento.0009_horariodisponivel`:**
- Cria a tabela `age_horario_disponivel`.

**Migration `agendamento.0010_compromisso_horario_origem_contato`:**
- Adiciona os 5 campos novos em `Compromisso` (horario FK, data_horario,
  origem, nome_contato, telefone_contato, email_contato).

### 4.2 Models

```
class OrigemCompromisso(models.TextChoices):
    INTERNO = 'INTERNO', 'Interno'
    PUBLICO = 'PUBLICO', 'Público'

class DiaSemana(models.IntegerChoices):
    SEG = 0, 'Segunda'
    TER = 1, 'Terça'
    QUA = 2, 'Quarta'
    QUI = 3, 'Quinta'
    SEX = 4, 'Sexta'
    SAB = 5, 'Sábado'
    DOM = 6, 'Domingo'

class HorarioDisponivel(BaseModel):
    agenda          = FK(Agenda, PROTECT, related_name='horarios')
    dia_semana      = IntegerField(choices=DiaSemana.choices)
    hora_inicio     = TimeField()
    duracao_minutos = PositiveIntegerField(validators=[MinValueValidator(5)])
    vagas           = PositiveIntegerField(validators=[MinValueValidator(1)])
    servico         = CharField(max_length=255, blank=True)
    publico         = BooleanField(default=True)
    ativo           = BooleanField(default=True)

    class Meta:
        db_table = 'age_horario_disponivel'
        ordering = ['dia_semana', 'hora_inicio']
```

Campos adicionados em `Agenda`:
```
slug                        = SlugField(max_length=100, unique=True, blank=True)
permite_agendamento_publico = BooleanField(default=False)
```

Campos adicionados em `Compromisso`:
```
horario          = FK(HorarioDisponivel, null=True, blank=True, SET_NULL)
data_horario     = DateField(null=True, blank=True)
origem           = CharField(choices=OrigemCompromisso.choices, default='INTERNO')
nome_contato     = CharField(max_length=255, blank=True)
telefone_contato = CharField(max_length=20, blank=True)
email_contato    = EmailField(blank=True)
```

### 4.3 Serializers

**`HorarioDisponivelSerializer(AuditFieldsMixin, ModelSerializer)`:**
- Campos: id, agenda, agenda_nome (read_only), dia_semana, dia_semana_label
  (source=get_dia_semana_display), hora_inicio, duracao_minutos, vagas,
  servico, publico, ativo, is_active, created_at, created_by_nome,
  updated_by_nome.
- `validate`: `duracao_minutos >= 5`, `vagas >= 1`.

**`AgendaSerializer`** atualizado para incluir `slug` e
`permite_agendamento_publico`. No `validate_slug`: se vazio e
`self.instance is None`, gerar slug a partir do `nome` via `slugify`.
Verificar unicidade manualmente (ou via `UniqueValidator`).

**`CompromissoSerializer`** atualizado para incluir os 5 campos novos.
Adicionar `validate`:
- Se `horario` informado: obrigar `data_horario`.
- Chamar `_validar_dia_semana(horario, data_horario)`.
- Aviso de conflito: verificar sobreposição e adicionar `aviso` ao response
  via `to_representation` (não levantar ValidationError).

**`AgendamentoPublicoSerializer(Serializer)`** (sem ModelSerializer):
- Campos de entrada: horario_id, data_horario, nome_contato,
  telefone_contato, email_contato (opcional).
- `validate_telefone_contato`: strip de não-dígitos, mínimo 8 dígitos.
- `validate`: verifica que `horario_id` existe, pertence ao slug da agenda,
  tem `publico=True`, `ativo=True`; verifica `data_horario` vs `dia_semana`.

### 4.4 Views / ViewSets

**`HorarioDisponivelViewSet(AuditMixin, ModelViewSet)`:**
- `filter_backends`: DjangoFilterBackend, OrderingFilter.
- `filterset_fields`: ['agenda', 'dia_semana', 'publico', 'ativo'].
- Action extra `@action(detail=True, methods=['get']) def ocupacao(...)`:
  recebe `?data=AAAA-MM-DD`, retorna `{vagas, vagas_ocupadas,
  vagas_disponiveis, compromissos: [id, titulo, nome_contato, status]}`.

**`AgendaDisponibilidadePublicaView(APIView)`:**
- `permission_classes = [AllowAny]`
- `throttle_classes = [AnonRateThrottle]`
- URL: `/api/v1/publico/agenda/{slug}/disponibilidade/`
- Parâmetros: `de` e `ate` (AAAA-MM-DD). Valida `ate - de <= 60 dias`.
- Itera dias no intervalo, filtra horários com `dia_semana` correspondente,
  `publico=True`, `ativo=True`. Retorna contagens agregadas.

**`AgendamentoPublicoView(APIView)`:**
- `permission_classes = [AllowAny]`
- `throttle_classes = [AnonRateThrottle]`
- URL: `/api/v1/publico/agenda/{slug}/agendar/`
- Lógica de criação atômica (RF-04):
  ```python
  with transaction.atomic():
      horario = HorarioDisponivel.objects.select_for_update().get(pk=horario_id)
      ocupados = Compromisso.objects.filter(
          horario=horario,
          data_horario=data_horario,
          is_active=True,
      ).exclude(status=StatusCompromisso.CANCELADO).count()
      if ocupados >= horario.vagas:
          raise ValidationError("Horário sem vagas disponíveis.")
      Compromisso.objects.create(
          agenda=horario.agenda,
          horario=horario,
          data_horario=data_horario,
          inicio=datetime.combine(data_horario, horario.hora_inicio),
          fim=datetime.combine(data_horario, horario.hora_inicio)
              + timedelta(minutes=horario.duracao_minutos),
          origem='PUBLICO',
          nome_contato=nome_contato,
          telefone_contato=telefone_contato,
          email_contato=email_contato,
          status='AGENDADO',
      )
  ```

**`CompromissoViewSet.perform_create`** — chamar a mesma lógica atômica
quando `horario` for informado. Pode ser extraída para uma função utilitária
`_criar_compromisso_com_validacao_vaga(horario_id, data_horario, **kwargs)`.

### 4.5 URLs

Adicionar em `agendamento/urls.py`:
```python
router.register(r'horarios-disponiveis', views.HorarioDisponivelViewSet, basename='horario-disponivel')
```

Adicionar em `core/urls.py` (novo prefixo):
```python
path('api/v1/publico/', include('agendamento.urls_publico')),
```

Criar `agendamento/urls_publico.py`:
```python
urlpatterns = [
    path('agenda/<slug:slug>/disponibilidade/', AgendaDisponibilidadePublicaView.as_view()),
    path('agenda/<slug:slug>/agendar/', AgendamentoPublicoView.as_view()),
]
```

### 4.6 Settings

Adicionar (ou confirmar presença) em `settings.py` / `settings_base.py`:
```python
REST_FRAMEWORK = {
    ...
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '10/hour',
        'user': '1000/day',
    },
}
```

---

## 5. Spec Técnica Frontend

### 5.1 Tela interna — Agendamento.jsx

A tela já possui abas (a de Calendário foi adicionada na Manutenção #55).
Adicionar nova aba "Horários" e expandir a aba de formulário de compromisso.

**Aba "Horários":**
- Dropdown de seleção de agenda no topo (reutilizar o existente).
- Tabela com colunas: Dia, Hora Início, Duração, Serviço, Vagas, Público,
  Ativo (toggle), Ações (editar / desativar).
- Botão "+ Novo Horário" abre modal com campos do `HorarioDisponivel`.
- POST `GET /api/v1/agendamento/horarios-disponiveis/?agenda={id}`.
- Criar/editar via modal. Desativar via PATCH `{ativo: false}`.

**Painel "Pendentes"** (nova sub-aba ou seção separada):
- `GET /api/v1/agendamento/compromissos/?origem=PUBLICO&status=AGENDADO`.
- Tabela com: nome_contato, telefone_contato, data_horario, serviço (via
  horario.servico), criado_em.
- Botões: "Confirmar" → PATCH `{status: "CONFIRMADO"}`, "Cancelar" → PATCH
  `{status: "CANCELADO"}`.

**Indicador de vagas** na aba Calendário:
- Ao exibir um evento ou slot de horário, buscar ocupação via
  `/api/v1/agendamento/horarios-disponiveis/{id}/ocupacao/?data={date}`.
- Exibir badge "X/Y" ao lado do nome do serviço.
- Cor: verde se vagas_disponiveis > 0, vermelho se lotado.

**Formulário de Compromisso** atualizado:
- Campo "Horário Disponível" (select, opcional): `GET /api/v1/agendamento/
  horarios-disponiveis/?agenda={id}&ativo=true`. Ao selecionar, preencher
  automaticamente `inicio` e `fim` calculados a partir de `hora_inicio` +
  `duracao_minutos` e da `data_horario` escolhida.
- Campo "Data do Horário" (date picker, aparece quando horário for selecionado).
- Campos nome_contato / telefone_contato / email_contato (aparecem quando
  campo "Cliente" estiver vazio).
- Badge "PÚBLICO" ou "INTERNO" read-only na edição de compromisso com origem
  já definida.
- Ao receber `aviso` no response 201, exibir toast de aviso amarelo:
  "Cliente já possui compromisso no mesmo período."

### 5.2 Página pública — /agendar/{slug}

**Rota:** adicionar em `routes/index.jsx` como rota pública (fora de
`ProtectedRoute`):
```jsx
<Route path="/agendar/:slug" element={<AgendamentoPublico />} />
```

**Componente `AgendamentoPublico.jsx`** (novo arquivo em
`src/pages/AgendamentoPublico.jsx`):

Estrutura geral:
```
<header>     Nome e descrição da agenda
<section>    Seletor de data (semana corrente + navegação anterior/próxima)
<section>    Lista de horários do dia selecionado
<section>    Formulário de contato (aparece ao clicar num horário disponível)
<footer>     Mensagem de confirmação ou erro
```

Estados:
- `loading`: spinner enquanto carrega disponibilidade.
- `dataSelecionada`: Date — padrão hoje.
- `slotSelecionado`: objeto do horário clicado.
- `confirmado`: boolean — controla exibição do estado de sucesso.
- `erro`: string — exibição de erros de API.

Chamadas de API (sem auth, sem tokenRef):
- `GET /api/v1/publico/agenda/{slug}/disponibilidade/?de={data}&ate={data}`
  (um dia de cada vez, ou a semana — a critério do Loom, desde que respeitado
  o limite de 60 dias).
- `POST /api/v1/publico/agenda/{slug}/agendar/`.

Paleta dark mode (tokens existentes):
- Background: `bg-navy-950`.
- Cards de slot disponível: `bg-navy-800 hover:bg-violet-700 cursor-pointer`.
- Slots lotados: `bg-navy-900 opacity-50 cursor-not-allowed`.
- Botão primário: `bg-violet-600 hover:bg-violet-500`.
- Texto principal: `text-white`.
- Texto secundário: `text-navy-400`.

Mobile-first breakpoints:
- 375px: layout de coluna única.
- 768px: pode expandir para 2 colunas (seletor | detalhes).

Não usa `tokenRef`. Não usa `authStore`. Não requer autenticação.

---

## 6. Spec de Concorrência — Como Testar `select_for_update`

### Por que o teste de concorrência é obrigatório
O bug original do NosFluir aconteceu porque a checagem de vagas era
"ler e depois criar" — duas threads podiam ler "0 de 2 ocupados", ambas
passarem na checagem e criarem o 2º e 3º compromisso simultaneamente,
violando a capacidade. O `select_for_update` elimina isso colocando um
lock no row do `HorarioDisponivel` antes de contar, garantindo que só uma
thread por vez entra na seção crítica.

### Padrão de teste com threading no Django TestCase

```python
import threading
from django.test import TransactionTestCase  # NÃO TestCase comum
from django.db import connection

class VagaConcorrentesTest(TransactionTestCase):
    """
    TransactionTestCase é obrigatório — TestCase envolve tudo em um
    rollback global que impede que múltiplas threads vejam as mesmas
    mudanças no banco. TransactionTestCase commita de verdade.
    """

    def setUp(self):
        self.agenda = Agenda.objects.create(nome='Agenda Conc', slug='agenda-conc')
        self.horario = HorarioDisponivel.objects.create(
            agenda=self.agenda,
            dia_semana=0,  # Segunda
            hora_inicio='09:00',
            duracao_minutos=30,
            vagas=2,
            servico='Consulta',
        )
        self.data = date(2026, 10, 19)  # Uma segunda-feira

    def _tentar_agendar(self, nome, resultados, idx):
        """Executado por cada thread. Guarda o status_code no array."""
        from django.test import RequestFactory
        # Usar APIClient direto é mais simples:
        from rest_framework.test import APIClient
        client = APIClient()
        resp = client.post(
            f'/api/v1/publico/agenda/agenda-conc/agendar/',
            {
                'horario_id': self.horario.id,
                'data_horario': str(self.data),
                'nome_contato': nome,
                'telefone_contato': '34991349194',
            },
            format='json',
        )
        resultados[idx] = resp.status_code
        connection.close()  # Fechar conexão da thread (boa prática)

    def test_concorrencia_max_vagas_ca03(self):
        """
        Dispara 3 threads simultaneamente para um horário com 2 vagas.
        Resultado esperado: exatamente 2 com status 201, 1 com status 400.
        Qualquer outro resultado indica race condition.
        """
        resultados = [None, None, None]
        threads = [
            threading.Thread(target=self._tentar_agendar, args=(f'Contato {i}', resultados, i))
            for i in range(3)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        criados = resultados.count(201)
        rejeitados = resultados.count(400)
        self.assertEqual(criados, 2, f'Esperado 2 criados, obteve {resultados}')
        self.assertEqual(rejeitados, 1, f'Esperado 1 rejeitado, obteve {resultados}')

        # Confirmar no banco
        total = Compromisso.objects.filter(
            horario=self.horario,
            data_horario=self.data,
            is_active=True,
        ).exclude(status='CANCELADO').count()
        self.assertEqual(total, 2)
```

### Por que `TransactionTestCase` e não `TestCase`
`TestCase` do Django envolve cada teste em uma transação de banco que é
revertida ao final — mas como `select_for_update` e `transaction.atomic()`
operam dentro de transações aninhadas, e múltiplas threads precisam de
conexões independentes que se vejam mutuamente, `TestCase` não funciona
para isso. `TransactionTestCase` commita de verdade, limpa o banco ao final
por truncate, e permite que as threads se vejam. Desempenho é um pouco
mais lento — aceitável pois é apenas 1 teste de concorrência.

---

## 7. Critérios de Aceite (CA)

**CA-01** — `POST /api/v1/agendamento/horarios-disponiveis/` com
`{agenda, dia_semana, hora_inicio, duracao_minutos, vagas, servico}` retorna
201 e o registro aparece em `GET /api/v1/agendamento/horarios-disponiveis/`.

**CA-02** — Criação do 1º e 2º compromisso num horário de 2 vagas retorna
201. O 3º retorna 400 com `{"erro": "Horário sem vagas disponíveis."}`.

**CA-03** — Teste de concorrência (threading) com 3 threads simultâneas em
horário de 2 vagas: exatamente 2 retornam 201 e 1 retorna 400. O banco
contém exatamente 2 compromissos não cancelados para o slot. (Usa
`TransactionTestCase`.)

**CA-04** — `GET /api/v1/publico/agenda/{slug}/disponibilidade/?de=...&ate=...`
retorna 200 sem autenticação e não inclui nome/telefone de agendamentos
existentes, apenas contagens.

**CA-05** — `POST /api/v1/publico/agenda/{slug}/agendar/` sem token retorna
201 (novo compromisso com `origem=PUBLICO`). Payload com `telefone_contato`
com menos de 8 dígitos retorna 400.

**CA-06** — Endpoint público retorna 429 após 11ª requisição do mesmo IP na
mesma hora (throttle). Body: `{"erro": "Limite de agendamentos atingido..."}`.

**CA-07** — `GET /api/v1/publico/agenda/{slug}/disponibilidade/` para agenda
com `permite_agendamento_publico=False` retorna 404.

**CA-08** — `POST /api/v1/publico/agenda/{slug}/agendar/` com `data_horario`
em dia da semana diferente do `horario.dia_semana` retorna 400 com mensagem
explicativa.

**CA-09** — Compromisso avulso (sem `horario`) criado via API interna continua
retornando 201 normalmente — compatibilidade retroativa confirmada.

**CA-10** — Aviso de conflito: criar dois compromissos para o mesmo cliente
no mesmo período retorna 201 para ambos, mas o segundo traz `{"aviso":
"Cliente já possui compromisso no mesmo período."}` no response.

**CA-11** — `DELETE /api/v1/agendamento/horarios-disponiveis/{id}/` faz soft
delete (is_active=False + deleted_at preenchido), compromissos existentes
vinculados não são afetados.

**CA-12** — Tela `/agendar/{slug}` carrega sem autenticação. Slot disponível
pode ser clicado. Formulário de contato é exibido. Submit chama o endpoint
público. Mensagem de sucesso é exibida após 201.

**CA-13** — Tela `/agendar/{slug}` exibe slot lotado como indisponível (cinza,
não clicável) quando `vagas_disponiveis == 0`.

**CA-14** — `GET /api/v1/agendamento/horarios-disponiveis/{id}/ocupacao/?data=2026-10-20`
retorna `{vagas, vagas_ocupadas, vagas_disponiveis, compromissos: [...]}` com
valores corretos para aquela data.

**CA-15** — `npm run build` sem erros após as mudanças (incluindo nova rota
pública e novo componente).

**CA-16** — 0 migrations pendentes após aplicar as 3 novas migrations
(`makemigrations --check --dry-run`).

---

## 8. Fora do Escopo

- Notificação por WhatsApp ou email (confirmação de agendamento).
- Pagamento antecipado ou cobrança vinculada ao agendamento público.
- Integração com Google Calendar / iCal.
- Cancelamento pelo próprio cliente (via link público).
- Recorrência automática de horários (ex.: todo segundo terça do mês).
- Múltiplos fusos horários.

---

## 9. Arquivos a Criar / Modificar

### Criar
- `backend/agendamento/migrations/0008_agenda_slug_publico.py`
- `backend/agendamento/migrations/0009_horariodisponivel.py`
- `backend/agendamento/migrations/0010_compromisso_horario_origem_contato.py`
- `backend/agendamento/urls_publico.py`
- `frontend/src/pages/AgendamentoPublico.jsx`

### Modificar
- `backend/agendamento/models.py` — novos campos em Agenda e Compromisso, novo model HorarioDisponivel
- `backend/agendamento/serializers.py` — novos serializers e atualização dos existentes
- `backend/agendamento/views.py` — HorarioDisponivelViewSet + views públicas
- `backend/agendamento/urls.py` — registrar HorarioDisponivelViewSet
- `backend/agendamento/tests.py` — novos testes (incluindo TransactionTestCase)
- `backend/core/urls.py` — incluir `agendamento.urls_publico` sob `/api/v1/publico/`
- `backend/core/settings.py` (ou equivalente) — throttle rates
- `frontend/src/pages/Agendamento.jsx` — aba Horários, painel Pendentes, indicador de vagas
- `frontend/src/routes/index.jsx` — rota pública `/agendar/:slug`

---

## 10. Dependências e Riscos

**Dependência:** `Agenda.slug` precisa ser gerado para registros já
existentes no banco antes de tornar o campo NOT NULL. A migration deve
usar `RunPython` para popular slugs de agendas existentes a partir do nome
(ou definir o campo como `null=True, blank=True` e exigir via serializer).

**Risco:** banco de dados de produção provavelmente tem menos de 10 agendas
— risco baixo. Verificar com `Agenda.objects.count()` antes do deploy.

**Throttle em testes:** ao rodar os testes de throttle (CA-06), é necessário
usar `override_settings(DEFAULT_THROTTLE_RATES={'anon': '10/hour'})` e
resetar o cache de throttle entre testes. DRF usa o cache padrão do Django
para contagem; em testes usar `from django.core.cache import cache;
cache.clear()` no `setUp`.

**TransactionTestCase limpa o banco:** ao usar `TransactionTestCase` para o
teste de concorrência (CA-03), os dados criados por outros testes `TestCase`
não estarão visíveis — cada classe é independente. O `setUp` de
`VagaConcorrentesTest` cria seus próprios fixtures.

**select_for_update e SQLite:** o banco de testes padrão do Django usa SQLite.
`select_for_update()` no SQLite não faz lock real (é ignorado silenciosamente).
Para o teste de concorrência ter validade real, o ambiente de CI deve usar
PostgreSQL. Se o projeto roda os testes com PostgreSQL (o que é o caso em
produção via docker-compose), o teste é válido. Se usar SQLite no CI, o
Sentinel deve documentar essa limitação e o teste de concorrência deve ser
marcado com `@skipIf(connection.vendor == 'sqlite', 'SQLite não suporta lock real')`.
