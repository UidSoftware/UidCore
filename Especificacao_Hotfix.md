# Especificação Hotfix — Manutenção #64 [NUCLEO 3/5]
## Assinaturas: mensalidade recorrente com contrato ativo

**Sistema:** UidCore (OS #7)
**Data:** 2026-10-12
**Autor:** Analista (modo manutenção)
**Origem:** melhoria de núcleo migrada da análise do NosFluir (PlanosPagamentos +
AlunoPlano + comando `gerar_mensalidades`) — fase única do pacote [NUCLEO] (3/5),
independente das fases #62, #63 e das que ainda virão.

---

## 1. Contexto

### AS-IS (como é hoje)
A recorrência de cobrança no UidCore não existe como conceito próprio. O
padrão atual (`Despesa.recorrente` + `frequencia` + `quantidade`, usado no
módulo financeiro) gera **N parcelas de uma vez no `perform_create`** — um
"estouro" fixo de lançamentos futuros, sem ciclo de vida posterior. Não há
noção de "cliente tem um contrato ativo que gera cobrança todo mês até ser
encerrado". Resultado: qualquer negócio de mensalidade (academia, escola,
clínica, contabilidade, SaaS) não tem como modelar assinatura de verdade —
só pacotes fechados de parcelas.

### Lição real que vira requisito obrigatório
No NosFluir (Studio Fluir), o cron de geração de mensalidades **continuou
gerando cobranças 2 meses depois do contrato do aluno ter sido encerrado**
(27/08 e 27/09/2026) porque a rotina de geração não consultava fim/status
do contrato antes de criar a cobrança do mês. Isso vira **requisito
obrigatório e testável** nesta especificação (RN-03 e RN-04 abaixo) — não é
nice-to-have, é a causa raiz documentada que esta fase existe para fechar
de vez no núcleo.

### TO-BE (como será)
Novo app `assinaturas` com dois models (`Plano`, `Assinatura`) + uma rotina
de geração de cobranças (serviço + management command) que:
- só gera cobrança para assinatura `ATIVA` dentro da janela
  `data_inicio..data_fim`;
- nunca gera para `ENCERRADA` ou `PAUSADA`, nem olhando pra trás nem pra
  frente da data de encerramento;
- é idempotente (rodar o mesmo mês 2x não duplica);
- respeita periodicidade (mensal roda todo mês; trimestral/semestral/anual
  só nos meses de competência a partir de `data_inicio`);
- nunca escreve no `LivroCaixa` diretamente — cria `financeiro.Receita`
  `PENDENTE`, e o signal existente da Receita cuida do caixa quando ela for
  de fato recebida (ADR já em vigor no módulo financeiro, visto em
  `financeiro/services.py` e `financeiro/signals.py`).

---

## 2. Requisitos Funcionais

### Backend — app `assinaturas`

**RF-01** — Novo app Django `assinaturas`, registrado em `INSTALLED_APPS`
(`core/settings.py`) e montado em `core/urls.py` sob
`path('api/v1/assinaturas/', include('assinaturas.urls'))` — mesmo padrão
dos apps `compras`/`marketing` (últimos dois a entrar no núcleo).

**RF-02** — Model `Plano(BaseModel)`:
```
nome            CharField(150)
descricao       TextField(blank=True)
valor           DecimalField(max_digits=12, decimal_places=2)
periodicidade   CharField(choices=Periodicidade: MENSAL/TRIMESTRAL/SEMESTRAL/ANUAL)
categoria       FK financeiro.Categoria (on_delete=PROTECT, limit_choices_to tipo=ENTRADA, is_active=True)
ativo           BooleanField(default=True)   # visível/selecionável em nova Assinatura
```
`ativo` aqui é **campo de negócio distinto de `is_active`** (herdado do
BaseModel) — um Plano pode ficar `is_active=True` (não soft-deletado) mas
`ativo=False` (descontinuado para novas vendas, sem afetar assinaturas já
ativas nele). Precedente já existe no sistema: `Categoria` também separa
soft delete de significado de negócio.

**RF-03** — Model `Assinatura(BaseModel)`:
```
cliente             FK clientes.Cliente (on_delete=PROTECT)
plano               FK assinaturas.Plano (on_delete=PROTECT)
valor               DecimalField(max_digits=12, decimal_places=2)   # copiado do plano no create, editável (desconto negociado)
dia_vencimento      PositiveSmallIntegerField (validators: MinValueValidator(1), MaxValueValidator(28))
data_inicio         DateField
data_fim            DateField(null=True, blank=True)   # null = indeterminado
status              CharField(choices=StatusAssinatura: ATIVA/PAUSADA/ENCERRADA, default=ATIVA)
conta               FK financeiro.Conta (on_delete=PROTECT)   # conta de destino das Receitas geradas
motivo_encerramento TextField(blank=True)
encerrada_em        DateTimeField(null=True, blank=True)
```
- `dia_vencimento` limitado a 1–28 (RN-02) evita o bug clássico de
  vencimento dia 30/31 não existir em fevereiro.
- `valor` não recalcula sozinho se o `Plano.valor` mudar depois — é
  snapshot editável no momento da criação (igual ao padrão
  `Receita.valor_bruto`/`Despesa.valor_bruto`, que também não seguem
  nenhuma tabela de preço "ao vivo").

**RF-04** — Actions no `AssinaturaViewSet`:
- `POST /api/v1/assinaturas/assinaturas/{id}/encerrar/` — body
  `{data_fim, motivo}`. Seta `status=ENCERRADA`, `data_fim` (obrigatório,
  não pode ser anterior a `data_inicio`), `motivo_encerramento`,
  `encerrada_em=now()`. Idempotente: encerrar uma já `ENCERRADA` retorna
  400 (RN-07).
- `POST /api/v1/assinaturas/assinaturas/{id}/pausar/` — seta
  `status=PAUSADA`. Bloqueado se já `ENCERRADA` (RN-07 — status terminal,
  sem retorno).
- `POST /api/v1/assinaturas/assinaturas/{id}/retomar/` — seta
  `status=ATIVA`. Só permitido a partir de `PAUSADA` (RN-07).

**RF-05** — Função de serviço `assinaturas/services.py::gerar_cobrancas_mes(mes, dry_run=False)`:
- `mes`: `date` representando o 1º dia do mês de competência (ex:
  `date(2026, 11, 1)`).
- Itera `Assinatura.objects.filter(status='ATIVA')` elegíveis ao mês
  (RN-03/RN-04/RN-05 abaixo definem elegibilidade).
- Para cada assinatura elegível, em `transaction.atomic()` própria (RN-06):
  cria `financeiro.Receita` com `tipo=MENSALIDADE`, `cliente=assinatura.cliente`,
  `categoria=assinatura.plano.categoria`, `valor_bruto=assinatura.valor`,
  `conta=assinatura.conta`, `vencimento=date(mes.year, mes.month, assinatura.dia_vencimento)`,
  `status=PENDENTE`, `referencia_mes=mes`, `descricao` incluindo nome do
  plano e nº da assinatura.
- Retorna um resumo: `{criadas: N, puladas_idempotencia: N, puladas_elegibilidade: N, erros: [...]}`.
- `dry_run=True`: executa toda a lógica de decisão (o que seria criado/
  pulado) mas não persiste nenhuma `Receita` — nenhuma gravação no banco
  (RN-08).

**RF-06** — Management command `gerar_cobrancas_assinaturas`:
```
python manage.py gerar_cobrancas_assinaturas [--mes AAAA-MM] [--dry-run]
```
- `--mes` default = mês corrente (`date.today()` truncado para dia 1).
- Chama `gerar_cobrancas_mes`, imprime o resumo (`self.stdout.write`) no
  mesmo padrão de `conciliar_extrato.py` (`BaseCommand` + `add_arguments`).
- Log de erro por assinatura não derruba o comando inteiro (RN-06) — ao
  final, se houve erro em alguma assinatura, `CommandError` só é levantado
  se **todas** falharem; erros parciais aparecem no resumo e o exit code
  continua 0 (cron não deve re-tentar o mês inteiro por causa de 1
  assinatura com dado inconsistente).

**RF-07** — Idempotência via constraint de unicidade: `unique_together`
em `Receita` não é viável (model já em produção, mexer lá é risco maior
que o escopo desta fase) — usar `FK Assinatura` **nullable** direto em
`financeiro.Receita` (campo novo `assinatura`, `on_delete=SET_NULL`,
`null=True`, `blank=True`, `related_name='cobrancas'`) + constraint
`UniqueConstraint(fields=['assinatura', 'referencia_mes'], condition=Q(assinatura__isnull=False), name='uniq_assinatura_referencia_mes')`.
Isso cobre o critério de aceite "rodar 2x não duplica" via `get_or_create`
no serviço (lookup por `assinatura` + `referencia_mes`) e via constraint de
banco como segunda camada de proteção contra race condition.

> Alternativa avaliada e descartada: tabela de vínculo separada
> (`CobrancaAssinatura`) em vez de FK direta em `Receita`. Descartada por
> exigir 2 queries/joins em todo lugar que hoje já lista Receita (dashboard,
> relatórios), sem ganho real — FK nullable é aditiva e não quebra nenhum
> código existente que já lê `Receita` sem saber de `assinaturas`.

### Regras de Negócio (elegibilidade de geração — núcleo da lição real)

**RN-01** — Só gera Receita se `Assinatura.status == 'ATIVA'`.
`PAUSADA` e `ENCERRADA` **nunca geram**, em nenhuma circunstância — sem
exceção para "mês de transição" ou "já estava gerado antes de pausar".

**RN-02** — Só gera se `data_inicio <= mes` (não gera cobrança para mês
anterior ao início do contrato).

**RN-03 (requisito obrigatório vindo da lição do NosFluir)** — Só gera se
`data_fim IS NULL OR data_fim >= mes`. Esta é a regra que faltava no
NosFluir e gerou 2 meses de cobrança indevida pós-encerramento — aqui ela
é parte da *query* de elegibilidade, não um filtro aplicado depois (a
assinatura `ENCERRADA` com `data_fim` no passado simplesmente não entra no
`queryset` que o comando itera).

**RN-04** — `RN-01` e `RN-03` são redundantes por design, não
contraditórias: encerrar uma assinatura seta `status=ENCERRADA` (barra
RN-01) **e** `data_fim` (barra RN-03) no mesmo `encerrar()`. As duas
camadas existem porque a lição do NosFluir foi justamente uma rotina que
dependia de só uma dessas condições e a condição que faltava não foi
coberta — aqui nenhuma das duas pode ser removida sem quebrar teste.

**RN-05** — Periodicidade não-mensal só gera cobrança no mês de
competência exato, calculado por diferença de meses inteiros a partir de
`data_inicio`:
```
diferenca_meses = (mes.year - data_inicio.year) * 12 + (mes.month - data_inicio.month)
intervalo = {MENSAL: 1, TRIMESTRAL: 3, SEMESTRAL: 6, ANUAL: 12}[periodicidade]
elegivel_por_periodicidade = diferenca_meses >= 0 and diferenca_meses % intervalo == 0
```
Ex.: `data_inicio=2026-01-15`, `TRIMESTRAL` → gera em jan/2026, abr/2026,
jul/2026, out/2026... nunca em fev, mar, mai etc.

**RN-06** — Cada assinatura processada dentro de sua própria
`transaction.atomic()` — uma assinatura com dado inconsistente (ex: FK de
conta apagada por engano, categoria inativa) registra erro no resumo e
**não** impede as demais de serem processadas no mesmo lote. Nunca uma
`transaction.atomic()` única em volta de todo o laço (isso faria 1 erro
derrubar o mês inteiro).

**RN-07** — Transições de status válidas: `ATIVA ↔ PAUSADA` (via
pausar/retomar), `ATIVA → ENCERRADA`, `PAUSADA → ENCERRADA`. **Nunca**
`ENCERRADA → qualquer coisa` — é estado terminal (criar nova Assinatura
para o mesmo cliente se precisar reativar, nunca reabrir uma encerrada;
preserva o histórico e a auditoria de `encerrada_em`/`motivo_encerramento`
intactos).

**RN-08** — `--dry-run` não grava nenhuma linha no banco — nem `Receita`,
nem efeito colateral de signal (já garantido transitivamente, já que
signal de `Receita` só dispara em `post_save` real).

**RN-09** — `Receita` gerada por assinatura nunca grava `LivroCaixa`
diretamente — ela nasce `status=PENDENTE`; o `LivroCaixa` só é afetado
quando o fluxo normal de "receber" a Receita rodar (endpoint/ação já
existente no `ReceitaViewSet`), exatamente como qualquer outra Receita
manual. Nenhuma lógica nova de caixa nesta fase.

**RN-10** — Payload de criação/edição de `Assinatura` ignora tentativa de
setar `status=ENCERRADA` diretamente fora da action `encerrar` (campo
`status` fica fora de `Meta.fields` editáveis no serializer de create/
update padrão — só a action dedicada movimenta esse campo para
`ENCERRADA`, preservando `motivo_encerramento`/`encerrada_em` sempre
preenchidos juntos).

### Frontend

**RF-08** — Novo item no Sidebar: `{ to: '/assinaturas', label: 'Assinaturas', icon: '🔁', requer: 'financeiro' }`,
seguindo exatamente o padrão de `requer: 'financeiro'` já usado por
Compras/Financeiro/Conciliação (reusa `selectPodeAcessarFinanceiro` do
`authStore.js` — nenhuma store nova).

**RF-09** — Rota `/assinaturas` protegida por `FinanceiroRoute` (mesmo
componente já usado em `/compras`, `/financeiro`, `/conciliacao`) em
`routes/index.jsx`.

**RF-10** — Tela `Assinaturas.jsx`:
- Listagem com filtro por `status` (ATIVA/PAUSADA/ENCERRADA) e busca por
  cliente.
- Botão "Nova Assinatura" abre modal (padrão `ResourceCrud`/`Modal.jsx` já
  usado em Clientes/Fornecedores/Produtos) com formulário: cliente
  (autocomplete, reaproveitar componente de busca já usado em
  Vendas/PDV), plano (select, ao escolher pré-preenche `valor` do plano —
  editável), dia de vencimento, data início, data fim (opcional), conta.
- Cada linha com ações: Editar, Pausar/Retomar (toggle conforme status
  atual), Encerrar (abre modal pequeno pedindo data + motivo,
  `window.confirm`-style guard antes de chamar a action — é operação sem
  volta, RN-07).
- Badge de status colorido (ATIVA=verde, PAUSADA=amarelo, ENCERRADA=
  cinza), mesmo padrão visual de badges já usado em Compras (`StatusCompra`)
  e PDV (`StatusDespesa`/`StatusReceita`).

**RF-11** — Nova aba "Assinaturas" na tela/modal de ficha do Cliente
(`Clientes.jsx`), listando: assinaturas do cliente (plano, valor, status,
próximo vencimento) + Receitas já geradas por essas assinaturas
(`GET /api/v1/financeiro/receitas/?assinatura__cliente=<id>` ou endpoint
equivalente filtrando por `cliente` — reaproveitar filtro já existente de
Receita por cliente se houver, senão adicionar `assinatura` a
`filterset_fields` do `ReceitaViewSet`). Somente leitura nesta aba — ações
de editar/encerrar/pausar continuam centralizadas na tela `Assinaturas.jsx`
(evita duplicar lógica de mutação em dois lugares).

**RF-12** — Permissão de UI: `tem_acesso_total` OU `perfil === FINANCEIRO`
— mesmo gate usado por Compras/Conciliação/Financeiro (`IsAdmin | IsFinanceiro`
no backend, `selectPodeAcessarFinanceiro` no frontend). Nenhum perfil novo
criado nesta fase.

### Cron (documentação, sem execução nesta fase)

**RF-13** — Documentar no `CLAUDE.md` do projeto a proposta de cron na VPS:
```
0 6 1 * * cd /var/www/uidcore && docker compose -f docker-compose.prod.yml exec -T backend python manage.py gerar_cobrancas_assinaturas >> /var/log/uidcore-assinaturas.log 2>&1
```
- Dia 1 de cada mês, 06:00 — gera o mês corrente (sem `--mes`, usa default).
- `-f docker-compose.prod.yml` **explícito** (regra global de todos os
  crons Uid — nunca confiar em `docker compose` resolver o compose file
  certo pelo diretório).
- `exec -T` (sem TTY) — padrão de cron não-interativo.
- Instalação do cron em si (`crontab -e` na VPS) é **passo do Pilot no
  deploy**, não do Forge/Loom — a especificação aqui documenta o comando
  exato a ser instalado e o motivo do agendamento (dia 1, início do mês de
  competência, horário de menor uso do sistema).

---

## 3. Requisitos Não Funcionais

**RNF-01** — Testes cobrindo obrigatoriamente (critério de aceite do
pedido): cada periodicidade (MENSAL/TRIMESTRAL/SEMESTRAL/ANUAL) gerando no
mês certo e pulando os errados; idempotência (rodar 2x no mesmo mês =
1 Receita); `PAUSADA` não gera; `ENCERRADA` não gera mesmo com `data_fim`
no passado (teste direto da lição do NosFluir — nome do teste deve
referenciar o bug real, ex:
`test_assinatura_encerrada_nao_gera_cobranca_mes_seguinte`); `--dry-run`
não persiste nada; erro em 1 assinatura não derruba o lote (RN-06).

**RNF-02** — Soft delete: `Plano` e `Assinatura` herdam `BaseModel` — nunca
hard delete. "Excluir" um Plano/Assinatura no frontend chama o DELETE
padrão do DRF, que o `AuditMixin.perform_destroy` já converte em soft
delete (`deleted_at`/`deleted_by`/`is_active=False`) — nenhum código novo
de delete necessário além de registrar o ViewSet com `AuditMixin`.

**RNF-03** — `AuditMixin` aplicado em `PlanoViewSet` e
`AssinaturaViewSet` (padrão de todos os ViewSets desde a Manutenção #62) —
`created_by`/`updated_by` preenchidos automaticamente.

**RNF-04** — `id = serializers.IntegerField(source='pk', read_only=True)`
como primeiro campo de `PlanoSerializer` e `AssinaturaSerializer` (regra
absoluta de toda serializer no projeto).

**RNF-05** — `response.data.results` no frontend (paginação padrão DRF) —
nunca `.data` direto.

**RNF-06** — Autenticação via JWT existente — nenhuma rota nova sem
`permission_classes` explícito (`IsAdmin | IsFinanceiro`, mesmo padrão do
`CompraViewSet`).

**RNF-07** — `makemigrations --check --dry-run` limpo antes do deploy —
migration da FK nova em `Receita` (`assinatura`) incluída no mesmo PR do
app `assinaturas` ou em migration separada dentro do app `financeiro`
(decisão do Forge — ambas as opções são aceitáveis, mas a migration de
`financeiro` precisa rodar depois da criação do app `assinaturas`, por
causa da FK cruzada).

**RNF-08** — Build frontend limpo (`npm run build`) sem novos erros/
warnings de import não usado.

---

## 4. Atores e Perfis

| Ator | Permissão |
|---|---|
| ADMIN / SUPERADMIN (`tem_acesso_total`) | Acesso total a Planos e Assinaturas |
| FINANCEIRO | Acesso total a Planos e Assinaturas (mesmo nível de ADMIN neste módulo) |
| Demais perfis (OPERACIONAL, MARKETING, PROFISSIONAL) | Sem acesso — item de menu oculto, rota redireciona para `/dashboard` |

---

## 5. Fora do Escopo (explícito no pedido)

- Cobrança automática por gateway (boleto/PIX/cartão) — a Receita gerada
  fica `PENDENTE`, recebimento continua manual via fluxo já existente de
  `ReceitaViewSet`.
- Reajuste anual automático de valor.
- Pró-rata (assinatura iniciada no meio do mês cobra valor cheio no 1º
  mês, ou só começa a gerar no mês seguinte conforme RN-02 — comportamento
  atual já cobre isso sem lógica extra: `data_inicio` no meio do mês X
  ainda é `<= mes X`, então já gera cheio nesse mês; se o negócio quiser
  pró-rata de verdade, é fase futura).
- Notificação ao cliente (WhatsApp/email) de cobrança gerada — mencionado
  como futuro no CLAUDE.md global (item "Adicionar n8n ao pipeline"), não
  nesta fase.

---

## 6. Riscos e Dependências

- **Dependência cruzada de app**: `financeiro.Receita` ganha FK para
  `assinaturas.Assinatura`. Como `assinaturas` é o app novo e `financeiro`
  já existe, a ordem de migration importa — `assinaturas` precisa ser
  criado e migrado antes da migration que adiciona o campo em
  `financeiro.Receita` (ou usar string de referência `'assinaturas.Assinatura'`
  no FK, que o Django resolve em qualquer ordem de `INSTALLED_APPS` desde
  que as migrations rodem na ordem certa — Forge deve conferir dependency
  graph gerado por `makemigrations`).
- **Risco de regressão em relatórios existentes**: dashboards que somam
  `Receita` por `tipo=MENSALIDADE` (se já existir uso desse `TipoReceita`
  em algum fluxo manual anterior) passam a incluir também as geradas por
  assinatura — comportamento esperado e desejado, mas vale conferir no
  Sentinel que nenhum teste existente assume `TipoReceita.MENSALIDADE`
  como "nunca usado automaticamente".
- **Risco operacional do cron**: só é instalado pelo Pilot após aprovação
  do Sentinel — até lá, geração de cobrança só acontece via comando manual
  (`python manage.py gerar_cobrancas_assinaturas`), o que é aceitável para
  este ciclo (fase 3/5 do pacote [NUCLEO], outras fases ainda virão).
- **Pendência técnica conhecida** (mesma classe da já documentada na
  Manutenção #62 sobre `ComboSerializer`): nenhuma identificada nesta fase
  — modelo novo, sem dívida técnica herdada.

---

## 7. Spec técnica resumida para Forge

```
backend/assinaturas/
├── models.py          Plano, Periodicidade, Assinatura, StatusAssinatura
├── serializers.py      PlanoSerializer, AssinaturaSerializer (id=IntegerField(source='pk'))
├── views.py             PlanoViewSet, AssinaturaViewSet (AuditMixin, IsAdmin|IsFinanceiro)
│                         actions: encerrar, pausar, retomar
├── services.py          gerar_cobrancas_mes(mes, dry_run=False)
├── urls.py              router DRF: planos, assinaturas
├── admin.py             AuditModelAdmin (padrão common/admin.py)
├── migrations/          0001_initial
└── management/
    └── commands/
        └── gerar_cobrancas_assinaturas.py

backend/financeiro/
└── migrations/          nova migration: Receita.assinatura (FK nullable, SET_NULL)
                          + UniqueConstraint(assinatura, referencia_mes) condicional
```

```
frontend/src/
├── pages/Assinaturas.jsx                novo
├── pages/Clientes.jsx                   + aba Assinaturas na ficha
├── components/layout/Sidebar.jsx        + item Assinaturas (requer: financeiro)
└── routes/index.jsx                     + rota /assinaturas (FinanceiroRoute)
```

---

## 8. Critério de Aceite (consolidado)

- [ ] CA-01: criar `Assinatura` MENSAL → rodar `gerar_cobrancas_assinaturas` → 1 `Receita PENDENTE` com `referencia_mes` correto.
- [ ] CA-02: rodar o command de novo no mesmo mês → continua existindo exatamente 1 `Receita` para essa assinatura/mês.
- [ ] CA-03: encerrar a assinatura (`POST .../encerrar/`) → rodar o command do mês seguinte → 0 Receitas novas para essa assinatura.
- [ ] CA-04: `--dry-run` não grava nenhuma `Receita` no banco.
- [ ] CA-05: `PAUSADA` não gera cobrança em nenhum mês enquanto permanecer pausada.
- [ ] CA-06: `TRIMESTRAL`/`SEMESTRAL`/`ANUAL` geram só nos meses de competência corretos a partir de `data_inicio` (testado com pelo menos 2 ciclos de cada).
- [ ] CA-07: `data_fim` no passado bloqueia geração mesmo que `status` ainda não tenha sido movido para `ENCERRADA` manualmente (defesa em profundidade da RN-03).
- [ ] CA-08: erro em 1 assinatura (ex: conta inválida) não impede geração das demais no mesmo lote — resumo final reporta o erro.
- [ ] CA-09: usuário `OPERACIONAL` sem `tem_acesso_total` não vê o menu Assinaturas nem acessa a rota/API.
- [ ] CA-10: aba Assinaturas na ficha do Cliente lista corretamente as assinaturas e cobranças geradas daquele cliente.
- [ ] CA-11: 100% dos RFs com teste — nenhum `@skip`/`@xfail`.

---

**Próximo agente:** Planner → rotear para Pipeline (manutenção com fase de
núcleo) → Forge (backend app `assinaturas` + migration `financeiro`) e Loom
(frontend `Assinaturas.jsx` + aba na ficha de Cliente), em paralelo →
Sentinel → Pilot (deploy + documentação do cron no CLAUDE.md do projeto).
