# Especificação de Hotfix — UidCore (OS #7)

**Manutenção #55 — Módulo Agendamento: visualização em Calendário mensal**

Data: 2026-08-26
Levantado por: Analista (modo manutenção — briefing técnico já qualificado pelo solicitante, contexto de código pré-investigado, sem lacunas)

---

## 1. Contexto

O módulo Agendamento (`frontend/src/pages/Agendamento.jsx`) hoje só oferece
visualização em lista/tabela, via duas abas genéricas `ResourceCrud`:
`Compromissos` e `Agendas`. Para enxergar a agenda de um dia específico ou
ter noção visual de distribuição de compromissos ao longo do mês, o usuário
precisa navegar página a página na tabela paginada (10 itens por página) e
ler a coluna de data — não há nenhuma visão de calendário.

Pedido: adicionar uma terceira aba "Calendário" com grid mensal, navegação
entre meses, indicador colorido por Agenda em cada dia com compromisso, e
possibilidade de ver e editar os compromissos do dia selecionado sem sair
do calendário.

## 2. AS-IS (como é hoje)

```
- Agendamento.jsx: componente com estado `tab` (useState), array TABS =
  [{key:'compromissos'}, {key:'agendas'}], cada aba renderiza um
  <ResourceCrud> parametrizado (schema-driven: columns, fields, emptyForm)
- ResourceCrud (frontend/src/components/ui/ResourceCrud.jsx): componente
  100% autocontido — busca dados (api.get), pagina (page_size=10 fixo),
  mantém o próprio estado de modal (modalOpen/editingId/form) e não expõe
  nenhuma prop, ref ou callback para abrir o modal de edição a partir de
  fora do componente. Hoje é acionado apenas internamente (clique em
  "Editar" na própria tabela)
- Backend agendamento (backend/agendamento/views.py):
  - CompromissoViewSet: filterset_fields = ['agenda','status','cliente']
    (DjangoFilterBackend simples, sem FilterSet customizado) — NÃO existe
    filtro por intervalo de data (inicio__gte/inicio__lte). search_fields
    = ['titulo','descricao']. Paginação padrão do projeto (PageNumberPagination,
    resposta em response.data.results + count)
  - AgendaViewSet: só SearchFilter por nome, sem paginação restritiva
    relevante (poucas agendas por cliente, tipicamente)
  - Compromisso: agenda (FK, null=True), titulo, inicio/fim (DateTimeField,
    ambos null=True), local, cliente (FK opcional), status (choices
    AGENDADO/CONFIRMADO/CANCELADO/CONCLUIDO), descricao, observacoes —
    tudo já exposto no CompromissoSerializer com agenda_nome, cliente_nome
    e status_label calculados (read-only)
  - Agenda: nome, descricao, cor (CharField(7), default '#3B82F6') — cor
    já existe e já é editável via aba Agendas
- Cliente da Uid consome api client `client.js` (baseURL '/api/v1'),
  export default `client`/`api` (mesmo módulo, dois nomes de import usados
  no projeto) com interceptor de refresh de JWT automático
```

## 3. TO-BE (como será)

```
- Nova aba "Calendário" em Agendamento.jsx (terceira entrada em TABS),
  mesmo padrão de estado (useState tab) já existente — zero mudança na
  estrutura de abas atual
- Novo componente frontend/src/pages/agendamento/CalendarioTab.jsx (ou
  frontend/src/components/agendamento/CalendarioTab.jsx — Loom decide o
  caminho seguindo a convenção de pastas já usada no projeto para
  componentes de página vs. componentes de UI compartilhados)
- CalendarioTab busca TODOS os Compromissos do mês corrente + Agendas
  (para resolver cor), sem endpoint novo — usando os mesmos dois
  endpoints já consumidos pela aba Compromissos/Agendas
- ResourceCrud ganha uma pequena extensão de API pública (props novas,
  opcionais, retrocompatíveis — nenhuma aba existente quebra) para permitir
  abrir o modal de edição de um item específico a partir de fora do
  componente — é o mecanismo que permite ao Calendário reaproveitar o
  modal sem duplicar formulário (detalhe em §7)
- Nenhuma mudança de model, serializer, migration ou endpoint no backend
```

## 4. Requisitos Funcionais

```
RF01 - O sistema deve exibir uma nova aba "Calendário" em Agendamento,
       posicionada ao lado das abas "Compromissos" e "Agendas", seguindo
       o mesmo componente/estilo visual de aba já usado (TABS array +
       botões com destaque da aba ativa em bg-violet-600/dark)

RF02 - A aba Calendário deve exibir um grid mensal com todos os dias do
       mês corrente, e permitir navegar para o mês anterior e o mês
       seguinte (setas/botões "‹ Mês anterior" e "Mês seguinte ›" + label
       do mês/ano exibido, ex: "Agosto 2026")

RF03 - Os dados do grid devem vir exclusivamente dos endpoints já
       existentes (agendamento/compromissos e agendamento/agendas) — sem
       criar endpoint novo. Cada dia do grid que tiver 1+ Compromisso
       (com is_active=True, já filtrado por padrão pelo ViewSet) deve
       exibir um indicador visual colorido, usando a cor (Agenda.cor,
       hex) da(s) Agenda(s) vinculada(s) aos compromissos daquele dia. Se
       houver mais de uma Agenda no mesmo dia, exibir um indicador por
       Agenda distinta presente naquele dia (ex.: pontos empilhados/lado
       a lado), até um limite razoável de indicadores visíveis por dia
       (Loom define o limite; acima dele, indicar "+N")

RF04 - Ao clicar em um dia do grid, esse dia fica destacado visualmente
       (ex.: borda/preenchimento diferenciado, mesmo padrão de "dia em
       foco" descrito no rascunho de UX) e abaixo do grid aparece a lista
       dos Compromissos daquele dia — título, horário (HH:mm de
       início–fim) e status (mesmo badge de status já usado na tabela de
       Compromissos). Clicar novamente no mesmo dia recolhe a lista
       (toggle)

RF05 - Clicar em um Compromisso — tanto a partir do indicador no grid
       quanto a partir da lista expandida do dia — deve abrir o MESMO
       modal de edição de Compromisso já usado na aba "Compromissos" (o
       modal do ResourceCrud), pré-preenchido com os dados daquele
       compromisso, reaproveitando o mesmo formulário (mesmos campos:
       titulo, agenda, cliente, inicio, fim, local, status, descricao,
       observacoes). Não deve existir um segundo formulário de edição de
       Compromisso no código

RF06 - O dia de hoje deve ter um indicador visual próprio no grid mensal
       (ex.: contorno ou fundo diferenciado), distinto do indicador de
       "dia selecionado/em foco" do RF04, mesmo quando os dois coincidem
       (hoje selecionado deve deixar claro visualmente que é "hoje E
       selecionado")

RF07 - Ao salvar uma edição de Compromisso a partir do modal aberto pelo
       Calendário (RF05), a lista de compromissos do dia selecionado e os
       indicadores do grid devem refletir a mudança sem necessidade de
       recarregar a página (refetch do mês corrente após fechar o modal
       com sucesso)
```

## 5. Requisitos Não Funcionais / Regras de Negócio

```
RNF01 - Zero mudança de backend (ver §6 — justificativa completa).
        Nenhuma migration, nenhum model, serializer, view ou url nova.

RNF02 - Reaproveitar api client (client.js) e o mesmo padrão de tratamento
        de erro (extractErrorMessage) já usado no restante do projeto —
        nenhuma chamada de API direta com fetch() ou axios cru.

RNF03 - Seguir exclusivamente os tokens de cor Tailwind já usados no
        projeto (navy-*, violet-*, gray-*, dark:*) — jamais introduzir
        paleta nova, shadcn/ui ou lucide-react. A cor de cada Agenda (
        Agenda.cor, hex livre cadastrado pelo usuário) é a ÚNICA exceção
        legítima a usar cor arbitrária via style inline (ex.:
        `style={{ backgroundColor: agenda.cor }}`), pois já é um dado do
        usuário e não um token de design do sistema.

RNF04 - NUNCA copiar código de SlotCalendar.jsx (Studio Fluir) — é
        referência de padrão de interação (dia clicável → destaca → lista
        abaixo), não de implementação. UidCore não tem conceito de
        "slot"/"vaga"/"modalidade" — o grid aqui é mensal (não semanal
        como o do Studio Fluir) e os dados vêm de Compromisso, não de
        Slot.

RNF05 - Fontes Plus Jakarta Sans + DM Sans (já configuradas no projeto) —
        nenhuma fonte nova.

RNF06 - Responsivo: grid mensal deve permanecer legível em mobile (a
        Sidebar/AppLayout do projeto já é usado em mobile pelos demais
        módulos — Calendário não pode quebrar esse padrão). Em telas
        estreitas, aceitável reduzir para mostrar só o número do dia +
        pontos de indicador (sem texto de compromisso dentro da célula).

RN01 - O grid mensal deve considerar Compromissos com `inicio` dentro do
       intervalo do mês exibido, mesmo que `fim` caia no mês seguinte (uso
       do campo `inicio` como referência de "em que dia o compromisso
       aparece no calendário" — fim é usado só para exibir o horário de
       término na lista/badge, não para decidir em qual dia o compromisso
       aparece).

RN02 - Compromissos com `inicio` nulo (campo é `null=True, blank=True` no
       model) não podem aparecer no grid mensal (não há como posicioná-los
       em um dia) — devem continuar visíveis normalmente na aba
       "Compromissos" (lista), sem alteração ali.

RN03 - Compromissos com `agenda` nula (FK opcional) devem aparecer no
       grid com um indicador de cor neutra/padrão (ex.: cinza — token já
       usado no projeto, tipo gray-400/slate-500), já que não há
       Agenda.cor para herdar.
```

## 6. Especificação de Backend — zero mudança (justificativa)

```
Confirmado por leitura de backend/agendamento/models.py, serializers.py e
views.py:

- Compromisso já expõe todos os campos necessários via CompromissoSerializer:
  id, agenda, agenda_nome, titulo, descricao, inicio, fim, local, cliente,
  cliente_nome, status, status_label, observacoes, is_active, created_at
- Agenda já expõe cor (hex) via AgendaSerializer
- CompromissoViewSet já filtra is_active=True por padrão no queryset — o
  frontend não precisa (nem deve) pedir compromissos inativos
- Não existe filtro de intervalo de data (inicio__gte/inicio__lte) no
  CompromissoViewSet — isso é o único "gap" técnico encontrado, mas NÃO
  justifica mudança de backend: o volume de Compromissos por cliente
  UidCore é baixo (é um sistema-template para MEI/pequena empresa, não
  uma agenda de grande volume), então o Calendário pode buscar uma janela
  ampla de compromissos com paginação alta (ex.: page_size=500,
  ordering=inicio) e filtrar client-side pelo mês exibido — mesma
  estratégia seguida em outras telas do projeto quando a tela precisa de
  "todos os itens" em vez de uma página (ver select-remote no próprio
  ResourceCrud, que já busca page_size=200 sem filtro de servidor)
- Se no futuro o volume de compromissos crescer a ponto de 500 registros
  não cobrirem uma janela razoável de meses, aí sim caberá um filtro
  inicio__gte/inicio__lte no backend — fora do escopo desta manutenção,
  registrado como risco em §9

CONCLUSÃO: RNF01 (zero mudança de backend) é tecnicamente viável e deve
ser respeitado à risca nesta manutenção.
```

## 7. Especificação de Frontend detalhada

### 7.1 Agendamento.jsx

```
- TABS ganha uma terceira entrada: { key: 'calendario', label: 'Calendário' }
- Novo bloco condicional `{tab === 'calendario' && <CalendarioTab />}`,
  no mesmo padrão dos blocos já existentes para 'compromissos'/'agendas'
- Nenhuma outra mudança neste arquivo
```

### 7.2 Extensão do ResourceCrud (mínima, retrocompatível)

```
Problema técnico real encontrado: ResourceCrud hoje não expõe nenhuma
forma de abrir o modal de edição a partir de fora (modalOpen/editingId/
openEdit são estado interno, sem prop nem ref). Para cumprir RF05 sem
duplicar formulário, a forma mais simples e menos arriscada é expor duas
props NOVAS e OPCIONAIS (com default que preserva 100% o comportamento
atual quando não usadas — nenhuma das ~15 telas que já usam ResourceCrud
no projeto pode ter alteração de comportamento):

  - `externalEditItem` (objeto | null): quando um objeto é passado (ex.:
    vindo do CalendarioTab), o ResourceCrud deve abrir o modal de edição
    já preenchido para aquele item, como se "Editar" tivesse sido clicado
    na tabela — reaproveita a função openEdit(item) que já existe
    internamente
  - `onExternalEditClose` (função, opcional): chamada quando o modal
    aberto via `externalEditItem` é fechado (com ou sem sucesso) — permite
    ao CalendarioTab limpar seu próprio estado de "compromisso selecionado"
    e disparar o refetch do mês (RF07)

Efeito colateral aceitável e desejado: a aba "Compromissos" pode
continuar usando <ResourceCrud resource="agendamento/compromissos" .../>
exatamente como hoje. O CalendarioTab vai renderizar esse MESMO componente
(pode ser oculto/sem tabela visível, ou reaproveitado da própria aba
Compromissos — decisão de implementação do Loom) só para ter acesso ao
modal já existente, passando `externalEditItem`.

Alternativa equivalente que Loom pode preferir por ser menos invasiva:
usar `forwardRef` + `useImperativeHandle` no ResourceCrud expondo um
método `openEdit(item)` chamável via ref a partir do CalendarioTab, em vez
de prop controlada. Qualquer uma das duas abordagens satisfaz RF05 — a
exigência inegociável é: UM SÓ formulário/modal de edição de Compromisso
em todo o código, reaproveitado, nunca duplicado.
```

### 7.3 CalendarioTab — estrutura e estado

```
Estado local (useState):
  - mesAtual: Date (ou {ano, mes}) — mês exibido no grid, inicializado no
    mês corrente
  - diaSelecionado: string ISO ('YYYY-MM-DD') | null — dia em foco (RF04)
  - compromissos: array — resultado do fetch do mês corrente
  - agendas: array — resultado do fetch de agendamento/agendas (para
    resolver cor por id)
  - loading: boolean
  - compromissoEditando: objeto | null — item passado como
    `externalEditItem` para o ResourceCrud/modal reaproveitado (RF05)

Fetch (useEffect disparado por mudança de mesAtual):
  - GET /agendamento/compromissos/ com params { page_size: 500,
    ordering: 'inicio' } — filtro do mês feito client-side comparando
    o campo `inicio` (parseado) contra o intervalo [primeiro dia do mês,
    último dia do mês] (RN01)
  - GET /agendamento/agendas/ com params { page_size: 200 } (mesmo padrão
    já usado pelo select-remote do ResourceCrud) — usado só para montar um
    mapa id → cor, já que compromisso já traz agenda_nome mas não a cor
    (CompromissoSerializer não expõe agenda.cor) — resolvido no frontend
    cruzando compromisso.agenda (id) com o mapa de agendas

Agrupamento:
  - Compromissos agrupados por dia (chave 'YYYY-MM-DD' extraída de
    `inicio`) num objeto/Map, calculado via useMemo a partir de
    `compromissos` — compromissos com `inicio` nulo são excluídos do
    agrupamento (RN02), mas nunca removidos do estado bruto

Rendering do grid:
  - Cabeçalho com nome do mês/ano + botões ‹ › (RF02)
  - Grid CSS (grid-cols-7, dom-sáb, ou grid-cols-5 útil se o projeto
    preferir seg-sex — seguir o que fizer mais sentido para um sistema de
    agendamento genérico multi-nicho: recomendação é 7 dias, domingo a
    sábado, já que Compromisso não é restrito a dia útil como o exemplo
    de referência do Studio Fluir)
  - Células vazias de preenchimento para alinhar o dia 1 do mês no dia da
    semana correto (mesmo padrão comum de calendário mensal)
  - Cada célula de dia: número do dia + até N pontos/indicadores coloridos
    (RF03) + destaque se for hoje (RF06) + destaque se for o dia
    selecionado (RF04) — célula clicável (onClick alterna diaSelecionado)

Lista expandida do dia (abaixo do grid, RF04):
  - Renderiza só quando diaSelecionado !== null
  - Lista os compromissos daquele dia (do agrupamento) — título, horário
    "HH:mm–HH:mm", badge de status (mesmo componente/estilo de badge já
    usado em ResourceCrud.renderCell para status_label)
  - Cada item da lista é clicável → seta compromissoEditando (RF05)

Edição (RF05/RF07):
  - Quando compromissoEditando !== null, renderiza o ResourceCrud (ou o
    modal reaproveitado via ref, conforme §7.2) passando
    externalEditItem={compromissoEditando}
  - onExternalEditClose limpa compromissoEditando e refaz o fetch de
    compromissos do mesAtual (RF07)
```

## 8. Atores e Perfis

```
Nenhuma mudança de perfil/permissão — a aba Calendário é visível para
qualquer usuário que já acessa o módulo Agendamento hoje (mesma regra de
acesso da aba Compromissos/Agendas, sem restrição adicional).
```

## 9. Fora do Escopo

```
- Criar/editar Compromisso diretamente clicando num dia vazio do grid
  (ex.: "+ Novo" ao clicar num dia sem compromisso) — não foi pedido;
  criação continua exclusivamente pela aba Compromissos ("+ Novo
  Compromisso"). Pode ser proposto como melhoria futura.
- Drag-and-drop de compromisso entre dias.
- Visualização semanal ou diária (só mensal nesta manutenção).
- Filtro por Agenda específica dentro do Calendário (ex.: esconder
  agendas desmarcadas) — pode ser melhoria futura, não pedido aqui.
- Filtro de data no backend (inicio__gte/inicio__lte) — ver risco em
  Riscos e Dependências; só necessário se o volume de compromissos
  crescer muito.
```

## 10. Riscos e Dependências

```
- RISCO BAIXO: se um cliente UidCore acumular centenas de compromissos
  ativos, o fetch com page_size=500 (RNF01/§6) pode não cobrir todo o
  histórico relevante numa única chamada — mitigação futura: filtro de
  data no backend (fora do escopo agora, ver §9).
- DEPENDÊNCIA: RF05 depende da extensão do ResourceCrud (§7.2) ser
  implementada de forma retrocompatível — Sentinel deve validar
  explicitamente que as abas Compromissos e Agendas (e qualquer outra
  tela do projeto que já usa ResourceCrud) continuam funcionando
  IDÊNTICO ao comportamento atual após a mudança (nenhuma regressão).
- Sem dependência de bibliotecas novas — grid de calendário é construído
  com Tailwind (grid-cols-7) + JS nativo de data, sem lib de calendário
  externa (evita inflar bundle e foge do escopo "sem shadcn/lucide").
```

## 11. Critérios de Aceite

```
CA-01 - Aba "Calendário" aparece em Agendamento, ao lado de Compromissos
        e Agendas, com o mesmo estilo visual das demais abas.

CA-02 - Grid mensal exibe todos os dias do mês corrente ao abrir a aba,
        com o nome do mês/ano correto.

CA-03 - Botões de mês anterior/seguinte navegam corretamente (inclusive
        virada de ano, ex.: dezembro → janeiro do ano seguinte e
        vice-versa) e refazem o fetch/recalculam o grid para o novo mês.

CA-04 - Um Compromisso com `inicio` em um dia do mês exibido aparece com
        indicador colorido nesse dia, usando a cor da Agenda vinculada
        (testável criando um Compromisso com Agenda de cor conhecida via
        aba Compromissos e conferindo no Calendário).

CA-05 - Compromisso sem Agenda vinculada aparece com indicador de cor
        neutra (não quebra, não fica sem indicador).

CA-06 - Compromisso com `inicio` nulo não aparece no grid (não causa erro
        de renderização) mas continua visível na aba Compromissos.

CA-07 - Clicar em um dia com compromisso(s) expande a lista abaixo do
        grid com título, horário e status de cada compromisso daquele
        dia; clicar novamente recolhe.

CA-08 - O dia de hoje tem indicador visual distinto, mesmo quando não é
        o dia selecionado.

CA-09 - Clicar em um compromisso (no grid ou na lista expandida) abre o
        modal de edição já existente (mesmos campos da aba Compromissos),
        pré-preenchido com os dados corretos.

CA-10 - Editar e salvar um compromisso a partir do modal aberto pelo
        Calendário persiste via API (mesmo endpoint PATCH já usado pela
        aba Compromissos) e reflete a mudança no grid/lista sem precisar
        recarregar a página.

CA-11 - Nenhuma regressão nas abas Compromissos e Agendas, nem em
        nenhuma outra tela do projeto que usa ResourceCrud (verificação
        obrigatória do Sentinel, dado que ResourceCrud é compartilhado).

CA-12 - Zero migration nova, zero mudança em models/serializers/views do
        backend agendamento (nem de qualquer outro app) — `git diff`
        do backend desta manutenção deve conter no máximo testes novos,
        nunca código de produção do backend.

CA-13 - npm run build limpo (0 erros), sem nenhuma dependência nova
        adicionada ao package.json além do que já existe hoje.
```

---

**Observação para o Planner:** esta manutenção é 100% frontend
(`feature_pequena`/`melhoria_ux` — não requer aprovação comercial,
não há mudança de contrato de API, não há risco de dado). O único ponto
de atenção para o roteamento é que a extensão do ResourceCrud (§7.2) é um
componente COMPARTILHADO por praticamente todos os módulos do sistema —
Sentinel precisa necessariamente rodar os testes/fluxos das demais telas
que usam ResourceCrud, não só do Agendamento, antes de aprovar.
