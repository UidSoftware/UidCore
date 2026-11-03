# Especificação Hotfix — Manutenção #92

**Sistema:** UidCore
**Módulo:** Agendamento (+ RH, leitura)
**Data:** 2026-11-03
**Analista:** Claude (modo manutenção)

---

## 1. Contexto

Pedido com 3 frentes no módulo Agendamento:

1. `Agenda.profissional` hoje aponta para `accounts.User` (Manutenção #63) — mistura
   "quem tem login" com "quem é o profissional de verdade" (`rh.Colaborador`).
   Um barbeiro/dentista/professor sem acesso ao sistema não aparece como opção,
   e a mesma pessoa física acaba existindo em dois cadastros desencontrados
   (Colaborador no RH, User no Agendamento). Trocar o vínculo para
   `rh.Colaborador` (só ativos).
2. Controle de vagas por horário **já existe no backend** desde a Manutenção #65
   (`HorarioDisponivel.vagas`, trava com `select_for_update` em
   `perform_create` do `CompromissoViewSet`, action `ocupacao/` e o fluxo
   público já mostram `vagas_disponiveis`/`lotado`). O que falta é: (a) expor
   isso na tela interna de "Novo Compromisso" (hoje só aparece depois de criado,
   na coluna da listagem) e (b) fechar um buraco real — a mesma trava de vaga
   **não existe em `perform_update`**, então editar um compromisso trocando
   horário/data passa batido pela validação.
3. A aba "Pendentes" já filtra `origem=PUBLICO, status=AGENDADO` e já confirma/
   recusa — falta só a explicação textual mais clara e mostrar a origem (e,
   opcionalmente, o canal) em cada pedido.

**Investigação de código (antes de desenhar a solução) confirmou:**
- `Agenda.profissional` → FK `User`, nullable, `on_delete=SET_NULL` (migration `0007_agenda_profissional.py`).
- `AgendaSerializer.profissional_nome` lê `profissional.nome_completo` (campo de `User`).
- `AgendaViewSet.get_queryset()` filtra por perfil PROFISSIONAL com `Q(profissional=u) | Q(created_by=u)` — compara `profissional` (hoje User) direto com `self.request.user`.
- `CompromissoViewSet.get_queryset()` tem o mesmo padrão: `Q(created_by=u) | Q(agenda__profissional=u))`.
- `rh.Colaborador` já tem `usuario` (OneToOneField para `accounts.User`, nullable) — é o vínculo que a migration de dados vai usar para mapear quem já tinha profissional setado.
- `CompromissoViewSet.perform_create` já valida vaga com `select_for_update` (RF-04/RN-01 da Manutenção #65) — `perform_update` **não tem equivalente**, é herdado puro do `ModelViewSet`.
- `HorarioDisponivelViewSet.ocupacao` (action `GET .../ocupacao/?data=`) já calcula `vagas`, `vagas_ocupadas`, `vagas_disponiveis` — mas a lógica de contagem (`Compromisso.objects.filter(horario=..., data_horario=..., is_active=True).exclude(status=CANCELADO).count()`) está **duplicada em 4 lugares**: `perform_create`, a action `ocupacao`, `AgendaDisponibilidadePublicaView.get`, e `CompromissoSerializer.get_vagas_restantes`. Nenhuma migration de model é necessária para essa frente, mas a correção de `perform_update` deve reaproveitar a mesma lógica, não duplicar de novo.
- `rh.ColaboradorViewSet` tem `permission_classes = [IsAdmin]` — se o combo de "Profissional" na tela de Agenda passar a buscar em `/api/v1/rh/colaboradores/`, qualquer usuário OPERACIONAL/MARKETING (que hoje gerencia Agenda livremente, conforme comentário explícito em `AgendaViewSet`) vai receber 403 ao tentar carregar a lista. **Isso é regressão real se não for tratado** — ver RN-01.
- Aba Pendentes (`PendentesTab`) já existe, já filtra e já confirma/recusa — falta reforçar a explicação e exibir origem/canal por linha.
- `AgendamentoPublicoView`/`AgendamentoPublicoSerializer` não têm campo `canal` hoje — o pedido pede isso como opcional.

---

## 2. Requisitos Funcionais (RF)

### Frente 1 — Profissional vem do RH

- **RF-01.** `Agenda.profissional` passa a ser `ForeignKey` para `rh.Colaborador`
  (`on_delete=SET_NULL`, `null=True`, `blank=True`, mesmo `related_name`
  `agendas_vinculadas`), em vez de `accounts.User`.
- **RF-02.** Migration de dados (`RunPython`, dentro da mesma migration ou em
  migration separada antes do `RemoveField`): para cada `Agenda` com
  `profissional_id` (User) preenchido, buscar
  `rh.Colaborador.objects.filter(usuario_id=agenda.profissional_id, is_active=True).first()`
  e gravar no novo campo. Se não achar nenhum Colaborador correspondente
  (ex: User era um perfil administrativo sem Colaborador vinculado, ou o
  Colaborador está inativo), o novo campo fica `null` — **não falhar a
  migration**, só coletar e imprimir (via `print()`, aparece no log do
  `migrate`) a lista de `Agenda.id`/`nome` que ficaram sem profissional, para
  o Sentinel reportar explicitamente (ver Critério de Aceite CA-10).
- **RF-03.** Campo de seleção de Profissional (dropdown) só lista
  `Colaborador` com `is_active=True` — tanto no backend (queryset do campo
  no serializer) quanto no frontend (endpoint já filtra; não precisa de
  `filterOptions` adicional).
- **RF-04.** `AgendaSerializer.profissional_nome` passa a ler
  `profissional.nome` (campo de `Colaborador`), não mais `.nome_completo`
  (campo de `User`).
- **RF-05.** `AgendaViewSet.get_queryset()` e `CompromissoViewSet.get_queryset()`
  (filtro por perfil PROFISSIONAL) passam a comparar via
  `profissional__usuario=u` / `agenda__profissional__usuario=u` — como
  `Colaborador` não é mais o próprio `User` logado, a comparação direta
  `profissional=u` não funciona mais (seria sempre `False`, quebrando
  silenciosamente o escopo de dados do perfil PROFISSIONAL).

### Frente 2 — Vagas disponíveis visíveis no Novo Compromisso + trava real

- **RF-06.** Endpoint de listagem `GET /api/v1/agendamento/horarios-disponiveis/`
  aceita parâmetro opcional `?data=YYYY-MM-DD`. Quando presente, cada item
  do resultado ganha `vagas_ocupadas`, `vagas_disponiveis` e `lotado`
  calculados para aquela data específica (mesma lógica de contagem já usada
  em `ocupacao`/`perform_create`/view pública — ver RF-09). Quando `data`
  não é enviado, esses 3 campos vêm `null` (comportamento atual preservado,
  sem quebrar quem já consome o endpoint sem esse parâmetro).
- **RF-07.** Tela "Novo/Editar Compromisso" (`CompromissosResourceCrud` em
  `Agendamento.jsx`) inverte a ordem dos campos: **Data primeiro, Horário
  depois**. Ao escolher Agenda + Data, o frontend calcula o dia da semana
  da data e busca
  `GET /agendamento/horarios-disponiveis/?agenda={id}&dia_semana={d}&ativo=true&data={data}`
  — só oferece no dropdown os horários daquele dia da semana, cada opção
  rotulada `"{hora} — {serviço} (X/Y vagas)"`. Opção com `vagas_disponiveis <= 0`
  aparece **desabilitada** (`disabled` no `<option>`) com rótulo
  `"(Lotado)"` no final.
- **RF-08.** Ao trocar a Data depois de já ter escolhido Horário, o campo
  Horário é limpo (mesmo padrão já existente para "trocar Agenda limpa
  Horário").
- **RF-09.** Centralizar a contagem de ocupação (hoje duplicada em 4 lugares)
  em uma função única, ex. `agendamento/services.py::contar_ocupacao(horario, data) -> (ocupados, disponiveis)`,
  reaproveitada por: `perform_create`, `perform_update` (RF-10),
  a action `ocupacao`, `AgendaDisponibilidadePublicaView.get`,
  `CompromissoSerializer.get_vagas_restantes` e o novo parâmetro `?data=`
  do RF-06. Mesmo princípio já cobrado em outros módulos financeiros do
  projeto: nunca duplicar a mesma regra de cálculo em lugares diferentes.
- **RF-10.** `CompromissoViewSet.perform_update` passa a ter a MESMA
  validação de vaga de `perform_create` (select_for_update no
  `HorarioDisponivel`, contar ocupados, comparar com `vagas`) **sempre que
  o payload do PATCH/PUT alterar `horario` ou `data_horario`** — excluindo
  o próprio compromisso (`pk` atual) da contagem de ocupados, senão um
  compromisso que já está contando como "ocupado" no próprio horário se
  autobloquearia ao ser só confirmado/editado sem trocar de slot.
- **RF-11.** O backend continua sendo a fonte de verdade (nunca confiar só
  na tela) — toda validação de tela do RF-07 é complementar, não substitui
  RF-10/trava existente.

### Frente 3 — Aba Pendentes explicada + origem/canal visível

- **RF-12.** Aba "Pendentes" ganha um texto de explicação mais completo, substituindo a frase atual por algo como:
  > "Pedidos feitos pelo **link público de agendamento** (aberto pelo cliente final, sem login) chegam aqui como pendentes — o estúdio precisa Confirmar ou Recusar cada um. Compromissos criados direto pela equipe (aba Compromissos) não passam por esta etapa."
- **RF-13.** Cada linha da tabela de Pendentes passa a exibir a **origem**
  (hoje sempre "Público", já que a aba filtra `origem=PUBLICO` — mostrar
  mesmo assim, de forma explícita, como badge, igual ao já usado no modal
  de edição de Compromisso) e, se existir, o **canal** (RF-14, opcional).
- **RF-14 (opcional).** Link público aceita querystring `?canal=` (ex.:
  `/agendar/estudio-x?canal=instagram`). A página pública
  (`AgendamentoPublico.jsx`) lê esse parâmetro da própria URL (sem exigir
  nenhuma navegação adicional do visitante) e envia como campo `canal` no
  `POST /api/v1/publico/agenda/{slug}/agendar/`. Backend grava em
  `Compromisso.canal` (novo campo, `CharField` com `choices` livres —
  `SITE`, `INSTAGRAM`, `WHATSAPP`, `OUTRO` — default `''`/`OUTRO` quando
  não vier nada). Aba Pendentes mostra o canal como badge adicional ao
  lado da origem; se vazio, mostra "—".
  **Esta sub-frente é opcional e não bloqueia a aceitação da manutenção**
  — pode ficar para um ciclo futuro se o tempo não permitir nesta rodada,
  mas o Analista recomenda implementar junto por ser de baixo custo
  (1 campo + 1 migration + 1 leitura de querystring).

---

## 3. Regras de Negócio (RN)

- **RN-01 (crítica — regressão a evitar).** `rh.ColaboradorViewSet` hoje é
  `permission_classes = [IsAdmin]` (toda a ação, inclusive `list`/`retrieve`).
  Se o combo "Profissional" da tela de Agenda passar a chamar
  `GET /api/v1/rh/colaboradores/` sem mudar isso, qualquer usuário
  OPERACIONAL/MARKETING que hoje gerencia Agenda livremente (comentário
  explícito no código: *"restringir quebraria OPERACIONAL/MARKETING, que
  hoje gerenciam agendas livremente"*) vai receber 403 ao abrir o formulário
  de Agenda — regressão real, não hipotética. Corrigir com
  `ColaboradorViewSet.get_permissions()` liberando `list`/`retrieve` para
  qualquer autenticado, mantendo `create`/`update`/`partial_update`/`destroy`
  restritos a `IsAdmin` (mesmo padrão de override documentado no CLAUDE.md
  global — `get_permissions()` sempre vence sobre `permission_classes` do
  decorator, então o `if self.action in (...)` tem que estar dentro dele).
- **RN-02.** Só `Colaborador` com `is_active=True` pode ser selecionado como
  profissional de uma Agenda — Colaborador desligado (soft delete) não
  aparece na lista nem é aceito num POST/PATCH direto (validação no
  serializer, queryset do campo FK restrito a `is_active=True`).
- **RN-03.** A migration de dados (RF-02) é **não-destrutiva por design**:
  nunca falha por falta de Colaborador correspondente — só reporta. A
  'Agenda' em si nunca é bloqueada ou apagada por ficar sem profissional.
- **RN-04.** Trava de vaga (RF-10) nunca conta o próprio compromisso sendo
  editado como ocupante do slot — só os outros compromissos ativos
  (`is_active=True`, excluindo `CANCELADO`) daquele `horario`+`data_horario`.
- **RN-05.** Trava de vaga em `perform_update` só precisa rodar quando
  `horario` ou `data_horario` mudam no payload — editar só `titulo`,
  `observacoes`, `status` etc. sem tocar nesses dois campos não deve pagar
  o custo (nem o risco) de uma validação de vaga que não é relevante para
  a mudança.
- **RN-06.** `canal` (RF-14, se implementado) é só um rótulo informativo —
  nunca usado para alterar permissão, preço ou qualquer regra de negócio.
  Não exigir obrigatoriedade: ausência de `canal` (link sem querystring)
  é o caso normal e esperado hoje (link único, sem distinção de canal).
- **RN-07.** Nenhuma mudança nesta manutenção altera o comportamento já
  existente do fluxo público de agendamento (`AgendaDisponibilidadePublicaView`/
  `AgendamentoPublicoView`) quanto a vagas — ele já funciona corretamente
  (Manutenção #65); a única adição ali é o campo opcional `canal`.

---

## 4. Telas (detalhamento para o Loom)

### 4.1 Agendamento → aba Agendas (formulário Nova/Editar Agenda)

Campo "Profissional responsável" (hoje `select-remote` em
`accounts/usuarios` filtrando `perfil=PROFISSIONAL`) passa a ser:

```js
{
  name: 'profissional',
  label: 'Profissional responsável',
  type: 'select-remote',
  endpoint: 'rh/colaboradores',
  labelField: 'nome',
  params: {},              // backend já restringe a is_active=True
}
```

Coluna da tabela de Agendas continua `profissional_nome` (agora vem de
`Colaborador.nome`, sem mudança visual de posição/rótulo).

### 4.2 Agendamento → aba Compromissos (modal Novo/Editar Compromisso)

Reordenar o bloco "Horário disponível" (hoje: Horário → Data) para
Data → Horário:

1. Campo **Data do Compromisso** (`type="date"`) vem antes do Horário.
   Habilitado assim que uma Agenda é escolhida.
2. Ao preencher a Data (e já ter Agenda escolhida), calcular o dia da
   semana (`new Date(data).getDay()`, convertendo para a convenção
   0=Segunda usada pelo backend) e buscar os horários daquele dia via
   `GET /agendamento/horarios-disponiveis/?agenda={id}&dia_semana={d}&ativo=true&data={data}`.
3. Campo **Horário Disponível** (select) só aparece habilitado depois da
   Data preenchida. Cada opção mostra:
   `"{hora_inicio} — {servico || 'Sem rótulo'} ({vagas_ocupadas}/{vagas} vagas)"`
   — opção com `vagas_disponiveis <= 0` vem com `disabled` e sufixo
   `" (Lotado)"`.
4. Trocar a Data limpa o Horário selecionado (mesmo padrão já existente
   para Agenda → Horário).
5. Submissão continua enviando `agenda`, `horario`, `data_horario` como
   hoje — o backend valida de novo (RF-10/RF-11), e se vier 400 com
   `{"erro": "Horário sem vagas disponíveis."}` o toast de erro já existente
   (`extractErrorMessage`) mostra a mensagem; o modal permanece aberto para
   o usuário escolher outro horário/data.

### 4.3 Agendamento → aba Pendentes

- Substituir o texto abaixo do título `"Compromissos recebidos pelo
  agendamento público aguardando confirmação."` pelo texto do RF-12
  (pode manter curto, mas precisa deixar claro a diferença entre
  "vindo do link público" vs "criado pela equipe").
- Nova coluna **Origem** na tabela (entre "Serviço" e "Recebido em"),
  sempre mostrando o badge "🌐 Público" (reaproveitar o mesmo estilo de
  badge já usado no modal de edição de Compromisso, `Globe`/`Shield` da
  lucide-react) — redundante com o filtro da aba, mas pedido explicitamente
  pelo cliente para deixar claro de onde cada pedido vem.
- Se RF-14 (canal) for implementado: badge adicional ao lado, ex.
  `📷 Instagram` / `🌐 Site` / `💬 WhatsApp` / `—` quando vazio.

### 4.4 Página pública `/agendar/{slug}` (só se RF-14 for implementado)

- Ao montar a página, ler `?canal=` da própria URL
  (`new URLSearchParams(window.location.search).get('canal')`), validar
  contra os valores aceitos (`site`, `instagram`, `whatsapp` — case
  insensitive) e guardar em estado local.
- Incluir `canal` no payload do `POST /publico/agenda/{slug}/agendar/`
  (campo opcional — enviar `''`/omitir se não vier nenhum valor reconhecido
  na URL).

---

## 5. Spec Backend (para o Forge)

### 5.1 Models

**`agendamento/models.py` — `Agenda`:**
```python
profissional = models.ForeignKey(
    'rh.Colaborador', verbose_name='profissional responsável',
    null=True, blank=True, on_delete=models.SET_NULL,
    related_name='agendas_vinculadas',
    limit_choices_to={'is_active': True},
)
```
(trocar o `to=settings.AUTH_USER_MODEL` por `'rh.Colaborador'` — atenção à
dependência circular de apps: `agendamento` precisa poder referenciar
`rh` via string `'rh.Colaborador'`, sem import direto no topo do módulo,
igual ao padrão já usado para `'clientes.Cliente'` em `Compromisso`.)

**`agendamento/models.py` — `Compromisso` (só se RF-14 for implementado):**
```python
class CanalCompromisso(models.TextChoices):
    SITE      = 'SITE', 'Site'
    INSTAGRAM = 'INSTAGRAM', 'Instagram'
    WHATSAPP  = 'WHATSAPP', 'WhatsApp'
    OUTRO     = 'OUTRO', 'Outro'

canal = models.CharField(
    max_length=10, choices=CanalCompromisso.choices, blank=True, default='',
)
```

### 5.2 Migrations (agendamento)

Sequência obrigatória (3 migrations, nesta ordem, para nunca perder dado):

1. `0011_agenda_profissional_colaborador.py` — `AddField` de um campo
   temporário `profissional_colaborador` (FK para `rh.Colaborador`, mesmas
   opções do RF-01) **sem tocar no campo `profissional` (User) antigo**.
2. `0012_migra_profissional_para_colaborador.py` — `RunPython` (RF-02):
   ```python
   def migrar(apps, schema_editor):
       Agenda = apps.get_model('agendamento', 'Agenda')
       Colaborador = apps.get_model('rh', 'Colaborador')
       sem_match = []
       for agenda in Agenda.objects.filter(profissional_id__isnull=False):
           colaborador = Colaborador.objects.filter(
               usuario_id=agenda.profissional_id, is_active=True,
           ).first()
           if colaborador:
               agenda.profissional_colaborador = colaborador
               agenda.save(update_fields=['profissional_colaborador'])
           else:
               sem_match.append(f'Agenda#{agenda.id} ({agenda.nome})')
       if sem_match:
           print(
               f'[Manutencao 92] {len(sem_match)} agenda(s) sem Colaborador '
               f'correspondente, profissional ficou vazio: {", ".join(sem_match)}'
           )
       else:
           print('[Manutencao 92] todas as agendas com profissional foram migradas com sucesso.')
   ```
   (função reversa pode ser no-op — `migrations.RunPython.noop` — já que é
   migração de dado derivado, não primário).
3. `0013_agenda_remove_profissional_rename.py` — `RemoveField('profissional')`
   (o antigo, FK para User) seguido de `RenameField('profissional_colaborador',
   'profissional')`.

**Importante para o Sentinel:** rodar a migration 2 em produção e capturar
a saída do `print()` no log do `migrate` — é o relatório pedido no RF-02/RN-03.
Se a lista vier vazia, documentar isso explicitamente ("0 agendas sem
profissional correspondente") em vez de omitir.

Migration adicional (só se RF-14): `0014_compromisso_canal.py` — `AddField`
simples, sem `RunPython` (default `''` cobre todos os registros existentes).

### 5.3 Serializers

**`AgendaSerializer`:**
- `profissional_nome = serializers.CharField(source='profissional.nome', read_only=True, allow_null=True)` (trocar `.nome_completo` por `.nome`).
- Campo `profissional` (gerado automaticamente pelo `ModelSerializer` a
  partir do model) deve restringir o queryset a `Colaborador.objects.filter(is_active=True)`
  — como o manager padrão (`BaseModelManager`) já filtra `deleted_at__isnull=True`
  mas não necessariamente `is_active` sozinho, declarar explicitamente:
  ```python
  profissional = serializers.PrimaryKeyRelatedField(
      queryset=Colaborador.objects.filter(is_active=True), required=False, allow_null=True,
  )
  ```

**`HorarioDisponivelSerializer`** (RF-06): adicionar campos calculados
opcionais:
```python
vagas_ocupadas    = serializers.SerializerMethodField(read_only=True)
vagas_disponiveis = serializers.SerializerMethodField(read_only=True)
lotado            = serializers.SerializerMethodField(read_only=True)

def _data_contexto(self):
    request = self.context.get('request')
    if not request:
        return None
    data_str = request.query_params.get('data')
    if not data_str:
        return None
    try:
        return date.fromisoformat(data_str)
    except ValueError:
        return None

def get_vagas_ocupadas(self, obj):
    data = self._data_contexto()
    if not data:
        return None
    ocupados, _ = contar_ocupacao(obj, data)
    return ocupados

def get_vagas_disponiveis(self, obj):
    data = self._data_contexto()
    if not data:
        return None
    _, disponiveis = contar_ocupacao(obj, data)
    return disponiveis

def get_lotado(self, obj):
    disp = self.get_vagas_disponiveis(obj)
    return disp is not None and disp <= 0
```
(`contar_ocupacao` importado de `agendamento/services.py`, RF-09 —
precisa passar `context={'request': request}` ao serializer na view, que
o `ModelViewSet` já faz por padrão.)

**`CompromissoSerializer.get_vagas_restantes`** passa a chamar
`contar_ocupacao` também, em vez da query inline duplicada.

**(Se RF-14) `AgendamentoPublicoSerializer`:** novo campo opcional
`canal = serializers.ChoiceField(choices=CanalCompromisso.choices, required=False, allow_blank=True, default='')`.

### 5.4 Services (novo)

`agendamento/services.py` (novo arquivo, RF-09):
```python
def contar_ocupacao(horario, data_horario, excluir_pk=None):
    """
    Retorna (ocupados, disponiveis) para um HorarioDisponivel numa data
    especifica. Nao usa select_for_update aqui (leitura) -- quem precisa
    de trava contra corrida (perform_create/perform_update) faz o
    select_for_update no HorarioDisponivel ANTES de chamar esta funcao,
    dentro do proprio transaction.atomic().

    excluir_pk: pk do Compromisso a excluir da contagem (RN-04) -- usado
    na edicao, para o proprio compromisso nao contar como ocupante do
    slot que ele mesmo ja ocupa.
    """
    from .models import Compromisso, StatusCompromisso
    qs = Compromisso.objects.filter(
        horario=horario, data_horario=data_horario, is_active=True,
    ).exclude(status=StatusCompromisso.CANCELADO)
    if excluir_pk:
        qs = qs.exclude(pk=excluir_pk)
    ocupados = qs.count()
    disponiveis = max(0, horario.vagas - ocupados)
    return ocupados, disponiveis
```
Reaproveitar em: `perform_create`, `perform_update` (novo, passando
`excluir_pk=instance.pk`), action `ocupacao`,
`AgendaDisponibilidadePublicaView.get`,
`CompromissoSerializer.get_vagas_restantes` (passando
`excluir_pk=obj.pk`, já que o próprio objeto sempre está na contagem
quando se olha `vagas_restantes` de um compromisso existente — mesmo
raciocínio do RN-04), `HorarioDisponivelSerializer` (RF-06, sem
`excluir_pk`, pois ali não há compromisso de referência).

### 5.5 Views

**`CompromissoViewSet.perform_update`** (RF-10, novo método — hoje não
existe, herda do `AuditMixin`):
```python
def perform_update(self, serializer):
    instance = serializer.instance
    horario_mudou = 'horario' in serializer.validated_data and serializer.validated_data['horario'] != instance.horario
    data_mudou = 'data_horario' in serializer.validated_data and serializer.validated_data['data_horario'] != instance.data_horario

    if not (horario_mudou or data_mudou):
        serializer.save(updated_by=self.request.user)
        return

    horario = serializer.validated_data.get('horario', instance.horario)
    data_horario = serializer.validated_data.get('data_horario', instance.data_horario)

    if horario and data_horario:
        with transaction.atomic():
            h = HorarioDisponivel.objects.select_for_update().get(pk=horario.pk)
            ocupados, _ = contar_ocupacao(h, data_horario, excluir_pk=instance.pk)
            if ocupados >= h.vagas:
                raise ValidationError({'erro': 'Horário sem vagas disponíveis.'})
            serializer.save(updated_by=self.request.user)
    else:
        serializer.save(updated_by=self.request.user)
```

**`AgendaViewSet.get_queryset`** (RF-05):
```python
qs = qs.filter(Q(profissional__usuario=u) | Q(created_by=u))
```

**`CompromissoViewSet.get_queryset`** (RF-05):
```python
qs = qs.filter(Q(created_by=u) | Q(agenda__profissional__usuario=u))
```

**`HorarioDisponivelViewSet.get_queryset`/listagem** (RF-06): garantir que
o `context` passado ao serializer inclui `request` (padrão do DRF já faz
isso automaticamente via `get_serializer_context()` do `ModelViewSet` —
só confirmar que não foi sobrescrito sem repassar `request`).

**`rh/views.py` — `ColaboradorViewSet`** (RN-01):
```python
def get_permissions(self):
    if self.action in ('list', 'retrieve'):
        return [IsAuthenticated()]
    return [IsAdmin()]
```

### 5.6 Testes esperados (Sentinel vai cobrar)

- Agenda com `profissional` setado para Colaborador ativo → aparece
  corretamente no serializer (`profissional_nome`).
- Agenda com `profissional` apontando para Colaborador inativo → rejeitado
  no POST/PATCH (ou nunca chega a essa situação pois o queryset do campo
  já filtra ativos).
- Migration de dados: criar cenário com Agenda.profissional(User) com e
  sem Colaborador correspondente, rodar a migration, confirmar os dois
  resultados.
- `HorarioDisponivel` com 2 vagas: criar 2 Compromissos AGENDADO/CONFIRMADO
  no mesmo horário+data → sucesso; 3º → 400 com `"Horário sem vagas disponíveis."`.
- `GET /horarios-disponiveis/?data=...` retorna `vagas_ocupadas`/
  `vagas_disponiveis`/`lotado` corretos; sem `?data=` retorna `null` nos 3 campos.
- PATCH mudando `horario`/`data_horario` de um compromisso existente para
  um slot lotado → 400; PATCH mudando só `titulo`/`status` sem tocar
  horario/data_horario → sucesso mesmo que o horário já esteja "lotado"
  por outros (não deve re-validar vaga nesse caso, RN-05).
- PATCH re-salvando o MESMO horario+data_horario que o compromisso já tinha
  (ex.: edição que não mexe no slot, mas o campo vem no payload igual)
  → sucesso, não conta o próprio compromisso contra si mesmo (RN-04).
- `ColaboradorViewSet`: usuário OPERACIONAL consegue `GET /rh/colaboradores/`
  (200), mas `POST`/`PATCH`/`DELETE` continuam 403 para ele.
- (Se RF-14) `POST /publico/agenda/{slug}/agendar/` com `?canal=` ou campo
  `canal` no payload grava corretamente; sem `canal` grava `''`/`OUTRO`.

---

## 6. Critérios de Aceite (CA)

- **CA-01.** `Agenda.profissional` é FK para `rh.Colaborador`; dropdown de
  Profissional na tela de Agenda busca em `rh/colaboradores` e só lista
  ativos.
- **CA-02.** Usuário com perfil OPERACIONAL ou MARKETING continua
  conseguindo abrir o formulário de Agenda e escolher um Profissional sem
  erro 403 (RN-01 verificada via API real com usuário não-admin).
- **CA-03.** Migration de dados executada em produção/teste real: toda
  Agenda que tinha `profissional` (User) com Colaborador correspondente
  ativo migrou para esse Colaborador; as que não tinham ficaram com
  `profissional=null` e aparecem listadas no log do `migrate` (conferido
  pelo Sentinel, reportado explicitamente mesmo se a lista for vazia).
- **CA-04.** `HorarioDisponivel` com 2 vagas aceita exatamente 2
  Compromissos (não cancelados) no mesmo horário+data e recusa o 3º via
  API com 400 — testado tanto em `POST` (criação) quanto em `PATCH`
  (edição trocando horário/data de um compromisso existente para um slot
  já com 2 ocupados).
- **CA-05.** Editar um compromisso sem tocar em `horario`/`data_horario`
  (ex.: só mudar `status` de AGENDADO para CONFIRMADO) nunca é bloqueado
  por falta de vaga, mesmo que o horário esteja no limite.
- **CA-06.** Tela "Novo Compromisso": ao escolher Agenda + Data, o dropdown
  de Horário mostra só os horários daquele dia da semana, com contagem
  "X/Y vagas" visível, e horário lotado aparece desabilitado na lista.
- **CA-07.** Aba Pendentes mostra o texto explicativo novo (RF-12) e a
  coluna/badge de Origem em cada linha.
- **CA-08 (se RF-14 implementado).** Link público com `?canal=instagram`
  grava o canal no Compromisso criado e a aba Pendentes mostra o badge
  correspondente; link sem `?canal=` continua funcionando normalmente,
  gravando canal vazio/OUTRO.
- **CA-09.** Nenhuma regressão nos fluxos já existentes do agendamento
  público (`AgendaDisponibilidadePublicaView`/`AgendamentoPublicoView`) —
  continuam calculando vaga corretamente após a centralização em
  `contar_ocupacao` (RF-09).
- **CA-10.** `makemigrations --check --dry-run` limpo (0 pendências) após
  as 3 migrations do RF-01/RF-02 (+ a de `canal`, se aplicável).
- **CA-11.** 100% dos testes existentes do módulo `agendamento` e `rh`
  continuam passando (0 regressão), mais os testes novos listados na
  seção 5.6.

---

## 7. Fora do Escopo

- Qualquer tela de RH (CRUD de Colaborador em si) — só o uso de leitura
  para popular o dropdown de Profissional.
- Qualquer mudança em `Colaborador.usuario` (continua como está).
- Dashboard/relatório agregando agendamentos por canal (RF-14 só grava e
  exibe por linha, não cria relatório novo).
- Qualquer mudança no fluxo de autenticação/perfil PROFISSIONAL além da
  correção pontual do `get_queryset` (RF-05) — já é comportamento
  existente da Manutenção #63, só ajustado para continuar funcionando com
  a troca de FK.

---

## 8. Observações para o Blueprint/Brush (se aplicável)

Esta é uma manutenção de módulo já existente (sem tela nova de ponta a
ponta) — não requer novo design_system nem ADR de arquitetura. Loom deve
seguir os tokens/componentes já usados em `Agendamento.jsx` (`Select`,
`Input`, `Button`, paleta navy/violet) sem introduzir padrão visual novo.

---

ANALISTA CONCLUIDO
