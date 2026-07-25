# Especificacao_Hotfix — UidCore
**MANUTENCAO_ID:** 7
**Data:** 2026-07-23
**Sistema:** UidCore — Template Financeiro Multi-Nicho
**Caminho:** /var/www/uidcore
**Elaborado por:** Analista (Hotfix Mode)

---

## Contexto e estado atual

Fases A, B e C ja estao em producao e NAO devem ser tocadas:

| Fase | O que ja existe |
|------|----------------|
| A | common/models.py (BaseModel, PessoaBase), clientes/models.py, fornecedores/models.py |
| B | financeiro/models.py completo (Conta, Aporte, Categoria, Receita, Despesa, LivroCaixa), financeiro/signals.py, financeiro/views.py, financeiro/serializers.py |
| C | financeiro/relatorios.py (DRE, Balanco, FluxoProjetado, Indicadores), endpoints DRE/Balanco/Indicadores/Fluxo, Financeiro.jsx com 8 abas |

Apps stub (models.py vazios com apenas `from common.models import BaseModel`): vendas, pagamentos, administrativo, rh, agendamento, portal.

Existe pasta `backend/conciliacao/` com apenas a pasta migrations vazia — essa pasta deve ser IGNORADA; os models de conciliacao vao dentro de `financeiro/models.py`, conforme pedido.

---

## Regras absolutas (toda a especificacao obedece estas)

- Soft delete: NUNCA `.delete()`, sempre `is_active = False; instance.save()`
- Dinheiro: SEMPRE `DecimalField(max_digits=12, decimal_places=2)`, NUNCA Float
- FK para clientes.Cliente: sempre `on_delete=models.PROTECT`
- Frontend: sempre `response.data.results`, nunca `.data` direto
- Serializadores: sempre `id = serializers.IntegerField(source='pk', read_only=True)` como primeiro campo
- Fontes: Plus Jakarta Sans + DM Sans — nunca Inter/Roboto/Arial
- Migrations: `python manage.py makemigrations <app>` por app, nunca global
- NAO tocar em arquivos das Fases A/B/C

---

## FASE D — Conciliacao Bancaria Automatica

### Visao geral

O usuario faz upload de um extrato bancario em PDF. O sistema extrai as transacoes, bate contra o LivroCaixa existente e classifica cada item como CONCILIADO, FALTANDO_SISTEMA ou FALTANDO_BANCO. Itens nao reconhecidos aguardam revisao humana. Com a flag --auto, o sistema tenta assentar lancamentos pendentes e criar novos apenas quando a descricao bate em um Padrao Seguro pre-aprovado.

---

### RF Fase D

RF-D01 — O sistema deve permitir upload de extrato bancario em PDF via endpoint REST (multipart/form-data).

RF-D02 — O sistema deve extrair texto do PDF usando pdftotext via subprocess e retornar lista estruturada de transacoes (data, descricao, valor, tipo ENTRADA/SAIDA).

RF-D03 — O sistema deve suportar parsers para C6 e BTG (implementados); Nubank, Inter, Caixa e Itau como stubs retornando lista vazia.

RF-D04 — O sistema deve selecionar o parser correto com base no nome da conta (substring case-insensitive: C6 -> parse_c6, BTG -> parse_btg, demais -> stub).

RF-D05 — O sistema deve executar matching em 3 camadas:
  Camada 1 (sempre): bate LivroCaixa por data+valor+tipo com tolerancia +-1 dia -> CONCILIADO
  Camada 2 (--auto): receita/despesa PENDENTE ou ATRASADA com valor_liquido igual e vencimento em +-3 dias da data banco -> assenta automaticamente (status RECEBIDO/PAGO + LivroCaixa via signal)
  Camada 3 (--auto): descricao do extrato contem substring de PadraoSeguroConciliacao ativo -> cria lancamento automaticamente

RF-D06 — O sistema NUNCA deve tomar decisao automatica para transacoes sem padrao aprovado. Ambiguidade = FALTANDO_SISTEMA aguardando revisao humana.

RF-D07 — O sistema deve salvar ConciliacaoExtrato e ItemConciliacao no banco dentro de transaction.atomic().

RF-D08 — O sistema deve expor endpoint GET /api/v1/financeiro/conciliacoes/ com lista de conciliacoes (conta, periodo, status, total_banco, total_sistema, divergencias).

RF-D09 — O sistema deve expor endpoint GET /api/v1/financeiro/conciliacoes/{id}/itens/ com lista de itens da conciliacao.

RF-D10 — O sistema deve expor endpoint POST /api/v1/financeiro/conciliacoes/{id}/confirmar-item/ (body: item_id) que marca um ItemConciliacao como confirmado=True.

RF-D11 — O sistema deve expor CRUD completo de PadraoSeguroConciliacao em /api/v1/financeiro/padroes-conciliacao/.

RF-D12 — O frontend deve exibir 6a aba "Conciliacao" no Financeiro.jsx com sub-abas: Upload, Lista, Detalhe e Padroes Seguros.

RF-D13 — A sub-aba Upload deve ter: select de conta, input date (mes/ano), input file de PDF, botao Enviar que faz POST para /api/v1/financeiro/conciliacoes/upload/.

RF-D14 — A sub-aba Lista deve exibir tabela de conciliacoes com colunas: Conta, Periodo, Status, Total Banco, Total Sistema, Divergencias.

RF-D15 — A sub-aba Detalhe (acessada clicando em uma conciliacao) deve exibir tabela de itens com colunas: Data, Descricao, Valor, Tipo, Status, Acao. Itens com status FALTANDO_SISTEMA exibem botao "Confirmar".

RF-D16 — A sub-aba Padroes Seguros deve exibir tabela CRUD de PadraoSeguroConciliacao com modal de criacao.

---

### RN Fase D

RN-D01 — Um mesmo LivroCaixa nunca pode ser vinculado a mais de um ItemConciliacao confirmado (unicidade de matching).

RN-D02 — Lancamentos estornados (estornado=True) no LivroCaixa sao ignorados no matching.

RN-D03 — O campo arquivo_nome em ConciliacaoExtrato armazena apenas o nome do arquivo, nao o path completo.

RN-D04 — O campo periodo armazena o primeiro dia do mes (ex: 2026-07-01 para julho/2026).

RN-D05 — Status da ConciliacaoExtrato: PENDENTE (recem criada), PROCESSADO (zero divergencias), COM_DIVERGENCIAS (algum FALTANDO_SISTEMA ou FALTANDO_BANCO nao confirmado).

RN-D06 — Natureza do PadraoSeguroConciliacao importa para contabilidade: APORTE vai para Patrimonio Liquido (nao entra no DRE); RECEITA_FINANCEIRA entra no DRE como rendimento.

RN-D07 — O endpoint upload/ aceita apenas Content-Type multipart/form-data. Rejeitar PDFs com senha sem o campo senha informado.

---

### Spec Backend Fase D — Models

Adicionar ao final de financeiro/models.py (nao substituir nada existente):

```python
# --- Conciliacao Bancaria ---

class StatusConciliacao(models.TextChoices):
    PENDENTE         = 'PENDENTE',         'Pendente'
    PROCESSADO       = 'PROCESSADO',       'Processado'
    COM_DIVERGENCIAS = 'COM_DIVERGENCIAS', 'Com Divergencias'

class StatusItemConciliacao(models.TextChoices):
    CONCILIADO       = 'CONCILIADO',       'Conciliado'
    FALTANDO_SISTEMA = 'FALTANDO_SISTEMA', 'Faltando no Sistema'
    FALTANDO_BANCO   = 'FALTANDO_BANCO',   'Faltando no Banco'

class ConciliacaoExtrato(BaseModel):
    # Herda BaseModel: created_at, updated_at, is_active
    conta         = models.ForeignKey(Conta, on_delete=models.PROTECT, related_name='conciliacoes')
    arquivo_nome  = models.CharField(max_length=500)
    periodo       = models.DateField()  # primeiro dia do mes
    processado_em = models.DateTimeField(auto_now_add=True)
    status        = models.CharField(max_length=20, choices=StatusConciliacao.choices, default='PENDENTE')
    total_banco   = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_sistema = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    divergencias  = models.IntegerField(default=0)
    criado_por    = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')

    class Meta:
        db_table = 'fin_conciliacao_extrato'
        ordering = ['-processado_em']

    def __str__(self):
        return f'Conciliacao {self.conta.nome} — {self.periodo.strftime("%m/%Y")}'

class ItemConciliacao(models.Model):
    # NAO herda BaseModel — soft delete via CASCADE com pai
    conciliacao     = models.ForeignKey(ConciliacaoExtrato, on_delete=models.CASCADE, related_name='itens')
    data_banco      = models.DateField()
    descricao_banco = models.CharField(max_length=500)
    valor           = models.DecimalField(max_digits=12, decimal_places=2)
    tipo            = models.CharField(max_length=10, choices=TipoLancamento.choices)
    status          = models.CharField(max_length=20, choices=StatusItemConciliacao.choices)
    lancamento_lc   = models.ForeignKey(LivroCaixa, null=True, blank=True, on_delete=models.SET_NULL, related_name='conciliacoes')
    confirmado      = models.BooleanField(default=False)

    class Meta:
        db_table = 'fin_item_conciliacao'
        ordering = ['data_banco']

    def __str__(self):
        return f'{self.data_banco} {self.tipo} R${self.valor} — {self.status}'

class NaturezaPadraoConciliacao(models.TextChoices):
    APORTE             = 'APORTE',             'Aporte (capital social)'
    RECEITA_FINANCEIRA = 'RECEITA_FINANCEIRA', 'Receita Financeira (rendimento)'

class PadraoSeguroConciliacao(models.Model):
    # NAO herda BaseModel — soft delete via campo ativo
    descricao_padrao = models.CharField(max_length=300)  # substring match case-insensitive
    tipo             = models.CharField(max_length=10, choices=TipoLancamento.choices)
    natureza         = models.CharField(max_length=20, choices=NaturezaPadraoConciliacao.choices, default='APORTE',
                           help_text='Apenas para tipo=ENTRADA: APORTE vai para PL; RECEITA_FINANCEIRA entra no DRE.')
    ativo            = models.BooleanField(default=True)
    criado_em        = models.DateTimeField(auto_now_add=True)
    criado_por       = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')

    class Meta:
        db_table = 'fin_padrao_seguro_conciliacao'
        ordering = ['tipo', 'descricao_padrao']

    def __str__(self):
        return f'[{self.tipo}] {self.descricao_padrao}'
```

---

### Spec Backend Fase D — financeiro/parsers.py (arquivo novo)

Funcoes a implementar:

extrair_texto_pdf(arquivo: str, senha: str | None = None) -> str
  - Chama subprocess: ['pdftotext', '-layout', *(['-upw', senha] if senha else []), arquivo, '-']
  - timeout=30
  - Se returncode != 0: levanta RuntimeError com stderr
  - Retorna stdout (texto completo)

_parse_valor_br(texto: str) -> Decimal
  - Remove tudo exceto digitos e virgula
  - Substitui virgula por ponto
  - Retorna Decimal
  - Em caso de erro: retorna Decimal('0')

parse_c6(texto: str, ano: int) -> list[dict]
  - Regex: r'(\d{2}/\d{2})\s+(.+?)\s+([-+]?\s*[\d.]+,\d{2})\s*$' com re.MULTILINE
  - Captura: DD/MM, descricao, valor com sinal (+ = ENTRADA, - = SAIDA)
  - Filtra valores == 0

parse_btg(texto: str, ano: int) -> list[dict]
  - Regex: r'(\d{2}/\d{2}/\d{4})\s+(.+?)\s+([DC])\s+([\d.]+,\d{2})' com re.MULTILINE
  - D = debito = SAIDA; C = credito = ENTRADA

parse_nubank(texto: str, ano: int) -> list[dict]
  - Stub — retorna []

parse_inter(texto: str, ano: int) -> list[dict]
  - Stub — retorna []

parse_caixa(texto: str, ano: int) -> list[dict]
  - Stub — retorna []

parse_itau(texto: str, ano: int) -> list[dict]
  - Stub — retorna []

get_parser(nome_conta: str) -> callable
  - Mapa: {'C6': parse_c6, 'BTG': parse_btg, 'NUBANK': parse_nubank, 'INTER': parse_inter, 'CAIXA': parse_caixa, 'ITAU': parse_itau}
  - Match por substring: nome_conta.upper() contains key
  - Se nenhum match: levanta ValueError com mensagem descritiva

Convencao de retorno de todos os parsers: list de dict com chaves: data (date), descricao (str), valor (Decimal), tipo ('ENTRADA'|'SAIDA')

---

### Spec Backend Fase D — financeiro/management/commands/conciliar_extrato.py (arquivo novo)

Argumentos:
  --arquivo (required): caminho para o PDF
  --conta   (required): nome da conta (usado em Conta.objects.get(nome__iexact=nome, is_active=True))
  --mes     (opcional): periodo YYYY-MM; se omitido, infere do nome do arquivo com regex r'(\d{4})-(\d{2})'
  --auto    (flag): habilita camadas 2 e 3
  --senha   (default='609393'): senha do PDF

Fluxo principal:
  1. Resolve Conta pelo nome (CommandError se nao encontrada)
  2. Determina periodo (CommandError se nao for possivel inferir)
  3. extrair_texto_pdf(arquivo, senha)
  4. get_parser(conta.nome) -> parser; parser(texto, ano=periodo.year)
  5. Filtra transacoes pelo mes do periodo
  6. Busca LivroCaixa do periodo (data >= primeiro_dia, < primeiro_dia_mes_seguinte, estornado=False)
  7. Matching Camada 1: para cada transacao banco, busca LivroCaixa com diff_dias<=1 e valor==transacao.valor e tipo==transacao.tipo
     - Match encontrado: status=CONCILIADO, lancamento_lc=match, marca indice como usado
     - Sem match: status=FALTANDO_SISTEMA
  8. LivroCaixa sem match: status=FALTANDO_BANCO
  9. Calcula total_banco (entradas - saidas do extrato) e total_sistema (entradas - saidas do LivroCaixa)
  10. transaction.atomic():
      - ConciliacaoExtrato.objects.create(...)
      - ItemConciliacao.objects.create(...) para cada item
      - Se --auto: _auto_processar(faltando_sistema, conta, conc)
  11. Imprime relatorio no stdout (sem emojis, texto puro)

Metodo _auto_processar(faltando, conta, conc):
  Passo 1 — Assentar Pendentes:
    Para cada item FALTANDO_SISTEMA:
      tipo ENTRADA: Receita.objects.filter(conta=conta, status__in=['PENDENTE','ATRASADO'], valor_liquido=valor, vencimento__range=(data-3dias, data+3dias), is_active=True).order_by('vencimento').first()
        Se encontrada: receita.status='RECEBIDO', receita.recebimento=data_banco, receita.save()
        Recupera LivroCaixa criado pelo signal, vincula ao ItemConciliacao, confirmado=True, status=CONCILIADO
      tipo SAIDA: mesmo fluxo com Despesa (status PAGO, pagamento=data_banco)
  Passo 2 — Criar por Padrao Seguro:
    Para os restantes (nao assentados no Passo 1):
      Busca PadraoSeguroConciliacao ativos; verifica descricao_banco.lower() contains padrao.descricao_padrao.lower()
      Se encontrado:
        ENTRADA + natureza=RECEITA_FINANCEIRA: Receita.objects.create(tipo='RECEITA_FINANCEIRA', status='RECEBIDO', ...)
        ENTRADA + natureza=APORTE: Aporte.objects.create(tipo='CAPITAL_SOCIAL', ...)
        SAIDA: Despesa.objects.create(tipo='VARIAVEL', status='PAGO', ...)
      Se nao encontrado: log "Sem padrao — aguarda revisao humana: {descricao}" — NAO criar nada
  Atualiza ConciliacaoExtrato.divergencias e status no final

---

### Spec Backend Fase D — financeiro/serializers.py (adicionar ao existente)

ConciliacaoExtratoSerializer:
  - id = serializers.IntegerField(source='pk', read_only=True)
  - conta_nome = serializers.CharField(source='conta.nome', read_only=True)
  - status_label = serializers.CharField(source='get_status_display', read_only=True)
  - Meta.model = ConciliacaoExtrato
  - fields: id, conta, conta_nome, arquivo_nome, periodo, processado_em, status, status_label, total_banco, total_sistema, divergencias
  - read_only_fields: id, conta_nome, processado_em, status, status_label, total_banco, total_sistema, divergencias

ItemConciliacaoSerializer:
  - id = serializers.IntegerField(source='pk', read_only=True)
  - tipo_label = serializers.CharField(source='get_tipo_display', read_only=True)
  - status_label = serializers.CharField(source='get_status_display', read_only=True)
  - Meta.model = ItemConciliacao
  - fields: id, conciliacao, data_banco, descricao_banco, valor, tipo, tipo_label, status, status_label, lancamento_lc, confirmado

PadraoSeguroConciliacaoSerializer:
  - id = serializers.IntegerField(source='pk', read_only=True)
  - tipo_label = serializers.CharField(source='get_tipo_display', read_only=True)
  - natureza_label = serializers.CharField(source='get_natureza_display', read_only=True)
  - Meta.model = PadraoSeguroConciliacao
  - fields: id, descricao_padrao, tipo, tipo_label, natureza, natureza_label, ativo, criado_em

---

### Spec Backend Fase D — financeiro/views.py (adicionar ao existente)

ConciliacaoViewSet(viewsets.ReadOnlyModelViewSet):
  queryset = ConciliacaoExtrato.objects.filter(is_active=True)
  serializer_class = ConciliacaoExtratoSerializer
  permission_classes = [IsAuthenticated]

  @action detail=False, methods=['post'], url_path='upload', parser_classes=[MultiPartParser]
  def upload(self, request):
    Campos esperados no multipart: arquivo (file), conta_id (int), periodo (str YYYY-MM), senha (str opcional), auto (bool opcional)
    Fluxo:
      1. Valida conta_id (404 se nao existir)
      2. Valida periodo (400 se formato invalido)
      3. Salva arquivo em tempfile
      4. extrair_texto_pdf(path_temp, senha)
      5. get_parser(conta.nome) -> parser
      6. parser(texto, ano=periodo.year) -> transacoes
      7. Executa matching (reutilizar logica do management command — extrair para funcao auxiliar financeiro/conciliacao_service.py ou implementar inline)
      8. Salva ConciliacaoExtrato + itens
      9. Se auto=True: _auto_processar
      10. Retorna ConciliacaoExtratoSerializer(instance).data com status 201

  @action detail=True, methods=['get'], url_path='itens'
  def itens(self, request, pk=None):
    conciliacao = self.get_object()
    return Response(ItemConciliacaoSerializer(conciliacao.itens.all(), many=True).data)

  @action detail=True, methods=['post'], url_path='confirmar-item'
  def confirmar_item(self, request, pk=None):
    conciliacao = self.get_object()
    item_id = request.data.get('item_id')
    item = get_object_or_404(ItemConciliacao, pk=item_id, conciliacao=conciliacao)
    item.confirmado = True
    item.save(update_fields=['confirmado'])
    divergencias = conciliacao.itens.filter(status='FALTANDO_SISTEMA', confirmado=False).count()
    conciliacao.divergencias = divergencias
    conciliacao.status = 'PROCESSADO' if divergencias == 0 else 'COM_DIVERGENCIAS'
    conciliacao.save(update_fields=['divergencias', 'status'])
    return Response({'ok': True, 'divergencias_restantes': divergencias})

PadraoSeguroConciliacaoViewSet(viewsets.ModelViewSet):
  queryset = PadraoSeguroConciliacao.objects.filter(ativo=True)
  serializer_class = PadraoSeguroConciliacaoSerializer
  permission_classes = [IsAuthenticated]

  def perform_destroy(self, instance):
    instance.ativo = False
    instance.save(update_fields=['ativo'])

---

### Spec Backend Fase D — financeiro/urls.py (adicionar ao router existente)

router.register(r'conciliacoes',        ConciliacaoViewSet,              basename='conciliacao')
router.register(r'padroes-conciliacao', PadraoSeguroConciliacaoViewSet,  basename='padrao-conciliacao')

---

### Spec Backend Fase D — Migration

python manage.py makemigrations financeiro --name="add_conciliacao_bancaria"

Tabelas criadas:
- fin_conciliacao_extrato
- fin_item_conciliacao
- fin_padrao_seguro_conciliacao

---

### Spec Backend Fase D — Dockerfile

Adicionar ao backend/Dockerfile (verificar se ja existe poppler-utils antes de adicionar):

RUN apt-get update && apt-get install -y poppler-utils && rm -rf /var/lib/apt/lists/*

---

### Spec Frontend Fase D — Financeiro.jsx

Adicionar ao array TABS (linha ~20):
  { key: 'conciliacao', label: 'Conciliacao' }

Adicionar no return do componente Financeiro (apos o ultimo tab renderizado):
  {tab === 'conciliacao' && <ConciliacaoTab showToast={showToast} contasOptions={contasOptions} />}

Componente ConciliacaoTab — sub-abas internas: upload | lista | detalhe | padroes

Sub-aba upload:
  State: contaId, periodo (YYYY-MM), arquivo (File), senha, autoMode (bool), uploading
  Formulario:
    - Select "Conta" (options de contasOptions, required)
    - Input type=month "Mes/Ano" (required) -> envia como YYYY-MM
    - Input type=file accept=".pdf" "Extrato PDF" (required)
    - Input type=text "Senha do PDF" placeholder="Deixar vazio se sem senha"
    - Checkbox "Modo automatico" default desmarcado
  Submit: POST /api/v1/financeiro/conciliacoes/upload/ com FormData
    formData.append('conta_id', contaId)
    formData.append('periodo', periodo)
    formData.append('arquivo', arquivo)
    formData.append('senha', senha)
    formData.append('auto', autoMode)
  Apos sucesso: navegar para sub-aba 'lista'

Sub-aba lista:
  State: conciliacoes[], loading, page, totalPages
  Fetch: GET /api/v1/financeiro/conciliacoes/ -> response.data.results
  Tabela colunas: Conta | Periodo | Status | Total Banco | Total Sistema | Divergencias | Acao
  Status como Badge:
    PENDENTE='bg-gray-100 text-gray-600'
    PROCESSADO='bg-green-100 text-green-800'
    COM_DIVERGENCIAS='bg-yellow-100 text-yellow-800'
  Botao "Ver Itens" por linha -> navega para sub-aba 'detalhe' salvando conciliacaoId selecionado

Sub-aba detalhe (so aparece quando conciliacaoId != null):
  Header: Conciliacao #{id} — {conta_nome} — {periodo formatado mm/aaaa} — Badge status
  KPIs 3 cards: Total Banco | Total Sistema | Divergencias
  Fetch itens: GET /api/v1/financeiro/conciliacoes/{id}/itens/ -> array (sem paginacao)
  Tabela itens: Data | Descricao | Valor | Tipo | Status | Acao
    Tipo badge: ENTRADA='bg-green-100 text-green-800', SAIDA='bg-red-100 text-red-800'
    Status badge: CONCILIADO='bg-green-100', FALTANDO_SISTEMA='bg-yellow-100', FALTANDO_BANCO='bg-gray-100'
    Acao: botao "Confirmar" so para status=FALTANDO_SISTEMA e confirmado=false
      -> POST /api/v1/financeiro/conciliacoes/{id}/confirmar-item/ com body {item_id: item.id}
      Apos sucesso: refetch itens + showToast

Sub-aba padroes:
  State: padroes[], loading, modalOpen, editingId, form, saving
  Fetch: GET /api/v1/financeiro/padroes-conciliacao/ -> response.data.results
  Tabela: Descricao | Tipo | Natureza | Ativo | Acoes
  Botao "+ Novo Padrao" abre modal
  Modal campos:
    - Input "Descricao do Padrao" (substring que aparece no extrato bancario)
    - Select Tipo: ENTRADA | SAIDA
    - Select Natureza (visible apenas quando Tipo=ENTRADA): APORTE | RECEITA_FINANCEIRA
    - Checkbox "Ativo" (default marcado)
  CRUD: POST para criar, PATCH para editar, DELETE para desativar (backend faz ativo=False)

---

## FASE E — Demais Modulos (stub funcional)

Convencao aplicada a todos os apps da Fase E:
- Todos os models herdam BaseModel (exceto AcessoPortalCliente que tem campo proprio)
- Todos os serializers tem id = serializers.IntegerField(source='pk', read_only=True) como primeiro campo
- Todos os ViewSets tem destroy() que faz is_active=False (ou ativo=False para modelos sem BaseModel)
- Todas as paginas JSX seguem o padrao de Clientes.jsx: tabela responsiva (mobile cards + desktop table) + modal

---

## FASE E.1 — Vendas (vendas/)

### RF Vendas

RF-V01 — CRUD de Orcamentos com numeracao automatica ORC-YYYY-NNNN.
RF-V02 — CRUD de Pedidos com numeracao automatica PED-YYYY-NNNN.
RF-V03 — CRUD de ItemPedido com valor_total = quantidade * valor_unitario (calculado no save).
RF-V04 — Frontend Vendas.jsx com sub-abas Orcamentos e Pedidos.

### RN Vendas

RN-V01 — Numero do orcamento/pedido e imutavel: so gerar se self.numero estiver vazio no save().
RN-V02 — ItemPedido.valor_total e editable=False e calculado no save.
RN-V03 — FK para clientes.Cliente: on_delete=PROTECT.

### Modelos vendas/models.py

Orcamento (BaseModel):
  numero (CharField max=20, unique, blank) — gerado no save: ORC-{ano}-{seq:04d}
  cliente (FK clientes.Cliente PROTECT, related_name='orcamentos')
  descricao (TextField)
  valor_total (Decimal default=0)
  status (choices: RASCUNHO/ENVIADO/APROVADO/REJEITADO/CANCELADO, default=RASCUNHO)
  validade (DateField null blank)
  observacoes (TextField blank)
  criado_por (FK User null blank SET_NULL)
  db_table = 'vnd_orcamento'

  save(): se not self.numero -> busca ultimo ORC-{ano}-* ordenado por numero decrescente -> incrementa seq ou inicia em 1 -> self.numero = f'ORC-{ano}-{seq:04d}'

Pedido (BaseModel):
  numero (CharField max=20, unique, blank) — gerado no save: PED-{ano}-{seq:04d}
  cliente (FK clientes.Cliente PROTECT, related_name='pedidos')
  orcamento (FK Orcamento null blank SET_NULL, related_name='pedidos')
  status (choices: PENDENTE/CONFIRMADO/EM_PRODUCAO/ENTREGUE/CANCELADO, default=PENDENTE)
  valor_total (Decimal default=0)
  data_pedido (DateField)
  data_entrega_prevista (DateField null blank)
  observacoes (TextField blank)
  criado_por (FK User null blank SET_NULL)
  db_table = 'vnd_pedido'

  save(): mesma logica de numeracao com PED-

ItemPedido (BaseModel):
  pedido (FK Pedido CASCADE, related_name='itens')
  descricao (CharField max=255)
  quantidade (IntegerField default=1)
  valor_unitario (Decimal)
  valor_total (Decimal editable=False)
  db_table = 'vnd_item_pedido'

  save(): self.valor_total = self.quantidade * self.valor_unitario; super().save()

### Serializers vendas/serializers.py

OrcamentoSerializer:
  id (source='pk', read_only)
  cliente_nome = CharField(source='cliente.nome_razao_social', read_only=True)
  status_label = CharField(source='get_status_display', read_only=True)
  todos os campos de Orcamento

PedidoSerializer:
  id (source='pk', read_only)
  cliente_nome = CharField(source='cliente.nome_razao_social', read_only=True)
  status_label = CharField(source='get_status_display', read_only=True)
  orcamento_numero = CharField(source='orcamento.numero', read_only=True, allow_null=True)
  todos os campos de Pedido

ItemPedidoSerializer:
  id (source='pk', read_only)
  todos os campos de ItemPedido

### Views vendas/views.py

OrcamentoViewSet(ModelViewSet):
  queryset = Orcamento.objects.filter(is_active=True)
  destroy: instance.is_active=False; instance.save()

PedidoViewSet(ModelViewSet):
  queryset = Pedido.objects.filter(is_active=True)
  destroy: is_active=False

ItemPedidoViewSet(ModelViewSet):
  queryset = ItemPedido.objects.filter(is_active=True)
  destroy: is_active=False

### URLs vendas/urls.py

router.register(r'orcamentos',   OrcamentoViewSet,  basename='orcamento')
router.register(r'pedidos',      PedidoViewSet,     basename='pedido')
router.register(r'itens-pedido', ItemPedidoViewSet, basename='item-pedido')

core/urls.py: path('api/v1/vendas/', include('vendas.urls'))

### Migration vendas

python manage.py makemigrations vendas --name="init_vendas"

### Frontend Vendas.jsx

Sub-abas: orcamentos | pedidos

Aba orcamentos:
  Tabela: Numero | Cliente | Descricao (truncada) | Valor Total | Status | Validade | Acoes
  Modal: cliente (select via /api/v1/clientes/?page_size=200), descricao (textarea), valor_total, status (select), validade (date), observacoes

Aba pedidos:
  Tabela: Numero | Cliente | Status | Valor Total | Data Pedido | Entrega Prevista | Acoes
  Modal: cliente (select), orcamento (select opcional via /api/v1/vendas/orcamentos/?page_size=200), status, valor_total, data_pedido (date), data_entrega_prevista (date), observacoes

---

## FASE E.2 — Pagamentos (pagamentos/)

### RF Pagamentos

RF-P01 — CRUD de MetodoPagamento (choices fixos: PIX/BOLETO/CARTAO_CREDITO/CARTAO_DEBITO/DINHEIRO/OUTRO).
RF-P02 — CRUD de Cobrancas com FK para cliente e metodo de pagamento.
RF-P03 — CRUD de Parcelas vinculadas a Cobranca.
RF-P04 — Frontend Pagamentos.jsx com sub-abas Cobrancas, Parcelas e Metodos.

### RN Pagamentos

RN-P01 — Comprovante e FileField, endpoint usa MultiPartParser + FormParser.
RN-P02 — FK para clientes.Cliente: on_delete=PROTECT.
RN-P03 — destroy() em todos: is_active=False.

### Modelos pagamentos/models.py

MetodoPagamento (BaseModel):
  nome (CharField max=20, choices: PIX/BOLETO/CARTAO_CREDITO/CARTAO_DEBITO/DINHEIRO/OUTRO, unique)
  ativo (BooleanField default=True)
  db_table = 'pag_metodo_pagamento'

Cobranca (BaseModel):
  cliente (FK clientes.Cliente PROTECT, related_name='cobrancas')
  descricao (CharField max=255)
  valor (Decimal)
  vencimento (DateField)
  status (choices: PENDENTE/PAGO/CANCELADO/ATRASADO, default=PENDENTE)
  metodo (FK MetodoPagamento null blank SET_NULL, related_name='cobrancas')
  data_pagamento (DateField null blank)
  comprovante (FileField upload_to='comprovantes/', blank)
  observacoes (TextField blank)
  criado_por (FK User null blank SET_NULL)
  db_table = 'pag_cobranca'

Parcela (BaseModel):
  cobranca (FK Cobranca CASCADE, related_name='parcelas')
  numero (IntegerField)
  valor (Decimal)
  vencimento (DateField)
  status (choices: PENDENTE/PAGO/CANCELADO, default=PENDENTE)
  data_pagamento (DateField null blank)
  db_table = 'pag_parcela'

### Serializers pagamentos/serializers.py

MetodoPagamentoSerializer: id, nome, nome_display=CharField(source='get_nome_display', read_only), ativo
CobrancaSerializer: id + todos + cliente_nome + metodo_nome=CharField(source='metodo.get_nome_display', read_only, allow_null) + status_label
ParcelaSerializer: id + todos + status_label

### Views pagamentos/views.py

MetodoPagamentoViewSet(ModelViewSet): destroy -> is_active=False
CobrancaViewSet(ModelViewSet): destroy -> is_active=False; parser_classes=[MultiPartParser, FormParser] para upload de comprovante
ParcelaViewSet(ModelViewSet): destroy -> is_active=False

### URLs pagamentos/urls.py

router.register(r'metodos',   MetodoPagamentoViewSet, basename='metodo-pagamento')
router.register(r'cobrancas', CobrancaViewSet,        basename='cobranca')
router.register(r'parcelas',  ParcelaViewSet,         basename='parcela')

core/urls.py: path('api/v1/pagamentos/', include('pagamentos.urls'))

### Migration pagamentos

python manage.py makemigrations pagamentos --name="init_pagamentos"

### Frontend Pagamentos.jsx

Sub-abas: cobrancas | parcelas | metodos

Aba cobrancas:
  Tabela: Cliente | Descricao | Valor | Vencimento | Status | Metodo | Acoes
  Modal: cliente (select), descricao, valor, vencimento (date), status, metodo (select), data_pagamento (date), comprovante (file input), observacoes

Aba parcelas:
  Tabela: Cobranca (descricao) | Numero | Valor | Vencimento | Status | Acoes
  Modal: cobranca (select via /api/v1/pagamentos/cobrancas/?page_size=200), numero, valor, vencimento, status

Aba metodos:
  Lista de cards com nome_display e badge ativo/inativo
  Botao "Adicionar" abre modal com select de nome (choices) + checkbox ativo
  Botao "Desativar" faz is_active=False

---

## FASE E.3 — Administrativo (administrativo/)

### RF Administrativo

RF-A01 — CRUD de TipoDocumento.
RF-A02 — CRUD de Documento com upload de arquivo (FileField).
RF-A03 — Frontend Administrativo.jsx com sub-abas Documentos e Tipos.

### RN Administrativo

RN-A01 — Documento.arquivo: FileField upload_to='docs/', suporta qualquer tipo.
RN-A02 — FK para cliente e opcional (null=True) — documento pode ser geral.
RN-A03 — destroy(): is_active=False para ambos os models.

### Modelos administrativo/models.py

TipoDocumento (BaseModel):
  nome (CharField max=100, unique)
  descricao (TextField blank)
  db_table = 'adm_tipo_documento'

Documento (BaseModel):
  titulo (CharField max=255)
  tipo (FK TipoDocumento PROTECT, related_name='documentos')
  arquivo (FileField upload_to='docs/')
  cliente (FK clientes.Cliente null blank PROTECT, related_name='documentos')
  descricao (TextField blank)
  status (choices: RASCUNHO/VIGENTE/EXPIRADO/CANCELADO, default=RASCUNHO)
  validade (DateField null blank)
  criado_por (FK User null blank SET_NULL)
  db_table = 'adm_documento'

### Serializers administrativo/serializers.py

TipoDocumentoSerializer: id, nome, descricao
DocumentoSerializer: id + todos + tipo_nome=CharField(source='tipo.nome', read_only) + cliente_nome + status_label

### Views administrativo/views.py

TipoDocumentoViewSet(ModelViewSet): destroy -> is_active=False
DocumentoViewSet(ModelViewSet): destroy -> is_active=False; parser_classes=[MultiPartParser, FormParser]

### URLs administrativo/urls.py

router.register(r'tipos',      TipoDocumentoViewSet, basename='tipo-documento')
router.register(r'documentos', DocumentoViewSet,     basename='documento')

core/urls.py: path('api/v1/administrativo/', include('administrativo.urls'))

### Migration administrativo

python manage.py makemigrations administrativo --name="init_administrativo"

### Frontend Administrativo.jsx

Sub-abas: documentos | tipos

Aba documentos:
  Tabela: Titulo | Tipo | Cliente | Status | Validade | Acoes
  Modal: titulo, tipo (select via GET tipos), arquivo (file), cliente (select opcional), descricao (textarea), status, validade

Aba tipos:
  Tabela: Nome | Descricao | Acoes
  Modal: nome, descricao

---

## FASE E.4 — RH (rh/)

### RF RH

RF-R01 — CRUD de Cargos.
RF-R02 — CRUD de Funcionarios (is_active = ativo do cargo).
RF-R03 — CRUD de FolhaPagamento com salario_liquido = bruto - descontos (calculado no save).
RF-R04 — CRUD de RegistroFerias com dias = (fim - inicio).days (calculado no save).
RF-R05 — Frontend RH.jsx com sub-abas Funcionarios, Folhas, Ferias e Cargos.

### RN RH

RN-R01 — Funcionario.cpf e unique max_length=11 (so digitos, sem mascara).
RN-R02 — FolhaPagamento.mes_referencia armazena o primeiro dia do mes de referencia.
RN-R03 — destroy() em todos: is_active=False.

### Modelos rh/models.py

Cargo (BaseModel):
  nome (CharField max=100, unique)
  descricao (TextField blank)
  salario_base (Decimal default=0)
  db_table = 'rh_cargo'

Funcionario (BaseModel):
  nome (CharField max=255)
  cpf (CharField max=11, unique)
  email (EmailField blank)
  cargo (FK Cargo PROTECT, related_name='funcionarios')
  data_admissao (DateField)
  data_demissao (DateField null blank)
  salario_atual (Decimal)
  regime (choices: CLT/PJ/ESTAGIO/SOCIO, default=CLT)
  observacoes (TextField blank)
  db_table = 'rh_funcionario'

FolhaPagamento (BaseModel):
  funcionario (FK Funcionario PROTECT, related_name='folhas')
  mes_referencia (DateField) — primeiro dia do mes
  salario_bruto (Decimal)
  descontos (Decimal default=0)
  salario_liquido (Decimal editable=False)
  status (choices: ABERTA/FECHADA/PAGA, default=ABERTA)
  observacoes (TextField blank)
  db_table = 'rh_folha_pagamento'

  save(): self.salario_liquido = self.salario_bruto - (self.descontos or Decimal('0')); super().save()

RegistroFerias (BaseModel):
  funcionario (FK Funcionario PROTECT, related_name='ferias')
  data_inicio (DateField)
  data_fim (DateField)
  dias (IntegerField editable=False)
  status (choices: AGENDADO/EM_ANDAMENTO/CONCLUIDO, default=AGENDADO)
  db_table = 'rh_registro_ferias'

  save(): self.dias = (self.data_fim - self.data_inicio).days; super().save()

### Serializers rh/serializers.py

CargoSerializer: id, nome, descricao, salario_base
FuncionarioSerializer: id + todos + cargo_nome=CharField(source='cargo.nome', read_only) + regime_label
FolhaPagamentoSerializer: id + todos + funcionario_nome + status_label
RegistroFeriasSerializer: id + todos + funcionario_nome + status_label

### Views rh/views.py

Todos ModelViewSet com destroy -> is_active=False:
CargoViewSet, FuncionarioViewSet, FolhaPagamentoViewSet, RegistroFeriasViewSet

### URLs rh/urls.py

router.register(r'cargos',       CargoViewSet,          basename='cargo')
router.register(r'funcionarios', FuncionarioViewSet,    basename='funcionario')
router.register(r'folhas',       FolhaPagamentoViewSet, basename='folha-pagamento')
router.register(r'ferias',       RegistroFeriasViewSet, basename='registro-ferias')

core/urls.py: path('api/v1/rh/', include('rh.urls'))

### Migration rh

python manage.py makemigrations rh --name="init_rh"

### Frontend RH.jsx

Sub-abas: funcionarios | folhas | ferias | cargos

Aba funcionarios:
  Tabela: Nome | CPF | Cargo | Regime | Data Admissao | Salario Atual | Acoes
  Modal: nome, cpf, email, cargo (select), data_admissao (date), data_demissao (date), salario_atual, regime (select), observacoes

Aba folhas:
  Tabela: Funcionario | Mes Referencia | Salario Bruto | Descontos | Liquido | Status | Acoes
  Modal: funcionario (select), mes_referencia (type=month -> enviar como YYYY-MM-01), salario_bruto, descontos, status, observacoes

Aba ferias:
  Tabela: Funcionario | Data Inicio | Data Fim | Dias | Status | Acoes
  Modal: funcionario (select), data_inicio (date), data_fim (date), status

Aba cargos:
  Tabela: Nome | Salario Base | Acoes
  Modal: nome, descricao, salario_base

---

## FASE E.5 — Agendamento (agendamento/)

### RF Agendamento

RF-AG01 — CRUD de Agendas com cor hex customizavel.
RF-AG02 — CRUD de Compromissos com inicio e fim (DateTimeField) e associacao opcional a cliente.
RF-AG03 — Frontend Agendamento.jsx com sub-abas Compromissos e Agendas.

### RN Agendamento

RN-AG01 — Compromisso.fim >= Compromisso.inicio: validacao no serializer (validate()).
RN-AG02 — Agenda.cor: CharField max=7, default='#3B82F6'.
RN-AG03 — destroy(): is_active=False para Agenda e Compromisso.

### Modelos agendamento/models.py

Agenda (BaseModel):
  nome (CharField max=100)
  descricao (TextField blank)
  cor (CharField max=7, default='#3B82F6')
  ativo (BooleanField default=True)
  db_table = 'age_agenda'

Compromisso (BaseModel):
  agenda (FK Agenda PROTECT, related_name='compromissos')
  titulo (CharField max=255)
  descricao (TextField blank)
  inicio (DateTimeField)
  fim (DateTimeField)
  local (CharField max=255, blank)
  cliente (FK clientes.Cliente null blank PROTECT, related_name='compromissos')
  status (choices: AGENDADO/CONFIRMADO/CANCELADO/CONCLUIDO, default=AGENDADO)
  observacoes (TextField blank)
  criado_por (FK User null blank SET_NULL)
  db_table = 'age_compromisso'

### Serializers agendamento/serializers.py

AgendaSerializer: id, nome, descricao, cor, ativo
CompromissoSerializer: id + todos + agenda_nome + cliente_nome (allow_null) + status_label

  def validate(self, attrs):
    if attrs.get('fim') and attrs.get('inicio') and attrs['fim'] < attrs['inicio']:
      raise serializers.ValidationError({'fim': 'Fim deve ser maior ou igual ao inicio.'})
    return attrs

### Views agendamento/views.py

AgendaViewSet(ModelViewSet): destroy -> is_active=False
CompromissoViewSet(ModelViewSet): destroy -> is_active=False
  Filtros recomendados: agenda, status, inicio__date (via filterset_fields ou get_queryset)

### URLs agendamento/urls.py

router.register(r'agendas',      AgendaViewSet,      basename='agenda')
router.register(r'compromissos', CompromissoViewSet, basename='compromisso')

core/urls.py: path('api/v1/agendamento/', include('agendamento.urls'))

### Migration agendamento

python manage.py makemigrations agendamento --name="init_agendamento"

### Frontend Agendamento.jsx

Sub-abas: compromissos | agendas

Aba compromissos:
  Tabela: Titulo | Agenda | Cliente | Inicio | Fim | Status | Acoes
  Modal: titulo, agenda (select), descricao (textarea), inicio (datetime-local), fim (datetime-local), local, cliente (select opcional), status, observacoes

Aba agendas:
  Lista de cards com bolinha colorida (cor) + nome + descricao
  Modal: nome, descricao, cor (input type=color), ativo (checkbox)

---

## FASE E.6 — Portal (portal/)

### RF Portal

RF-PO01 — CRUD de AcessoPortalCliente: vincula accounts.User a clientes.Cliente.
RF-PO02 — Soft delete via ativo=False (campo proprio, nao is_active do BaseModel).
RF-PO03 — Frontend Portal.jsx com tabela de acessos e modal de criacao.

### RN Portal

RN-PO01 — AcessoPortalCliente.usuario e OneToOneField: um usuario so pode ser vinculado a um cliente.
RN-PO02 — ultimo_acesso: somente leitura, atualizado pelo sistema.
RN-PO03 — NAO herda BaseModel — tem campos proprios: ativo, criado_em.

### Modelo portal/models.py

AcessoPortalCliente (NAO herda BaseModel):
  usuario (OneToOneField settings.AUTH_USER_MODEL CASCADE, related_name='acesso_portal')
  cliente (FK clientes.Cliente PROTECT, related_name='acessos_portal')
  ativo (BooleanField default=True)
  ultimo_acesso (DateTimeField null blank)
  criado_em (DateTimeField auto_now_add=True)
  db_table = 'portal_acesso_cliente'

### Serializers portal/serializers.py

AcessoPortalClienteSerializer:
  id = serializers.IntegerField(source='pk', read_only=True)
  usuario_email = serializers.EmailField(source='usuario.email', read_only=True)
  cliente_nome = serializers.CharField(source='cliente.nome_razao_social', read_only=True)
  todos os campos: usuario, cliente, ativo, ultimo_acesso, criado_em
  read_only_fields: id, usuario_email, cliente_nome, ultimo_acesso, criado_em

### Views portal/views.py

AcessoPortalClienteViewSet(ModelViewSet):
  queryset = AcessoPortalCliente.objects.filter(ativo=True)
  serializer_class = AcessoPortalClienteSerializer

  def perform_destroy(self, instance):
    instance.ativo = False
    instance.save(update_fields=['ativo'])

### URLs portal/urls.py

router.register(r'acessos', AcessoPortalClienteViewSet, basename='acesso-portal')

core/urls.py: path('api/v1/portal/', include('portal.urls'))

### Migration portal

python manage.py makemigrations portal --name="init_portal"

### Frontend Portal.jsx

Tabela unica: Usuario (email) | Cliente | Ativo | Ultimo Acesso | Acoes
Botao "+ Novo Acesso" -> modal: usuario (select via /api/v1/accounts/usuarios/?page_size=200), cliente (select), ativo (checkbox default marcado)
  Nota para Loom: verificar endpoint correto para listar usuarios (pode ser /api/v1/accounts/ — confirmar com o que existe em core/urls.py)
Botao "Desativar" por linha -> PATCH /api/v1/portal/acessos/{id}/ com body {ativo: false}

---

## Checklist completo de entregas

### Forge (Backend) — 34 arquivos

FINANCEIRO (adicionar ao existente):
  [ ] backend/financeiro/models.py — adicionar 3 models ao final (ConciliacaoExtrato, ItemConciliacao, PadraoSeguroConciliacao)
  [ ] backend/financeiro/parsers.py — novo arquivo
  [ ] backend/financeiro/management/__init__.py — criar se nao existir
  [ ] backend/financeiro/management/commands/__init__.py — criar se nao existir
  [ ] backend/financeiro/management/commands/conciliar_extrato.py — novo arquivo
  [ ] backend/financeiro/serializers.py — adicionar 3 serializers ao final
  [ ] backend/financeiro/views.py — adicionar 2 ViewSets ao final
  [ ] backend/financeiro/urls.py — adicionar 2 registros ao router
  [ ] backend/Dockerfile — adicionar poppler-utils

VENDAS (substituir stub):
  [ ] backend/vendas/models.py
  [ ] backend/vendas/serializers.py — novo arquivo
  [ ] backend/vendas/views.py — novo arquivo
  [ ] backend/vendas/urls.py — novo arquivo
  [ ] backend/vendas/apps.py — verificar/criar se necessario

PAGAMENTOS (substituir stub):
  [ ] backend/pagamentos/models.py
  [ ] backend/pagamentos/serializers.py — novo arquivo
  [ ] backend/pagamentos/views.py — novo arquivo
  [ ] backend/pagamentos/urls.py — novo arquivo

ADMINISTRATIVO (substituir stub):
  [ ] backend/administrativo/models.py
  [ ] backend/administrativo/serializers.py — novo arquivo
  [ ] backend/administrativo/views.py — novo arquivo
  [ ] backend/administrativo/urls.py — novo arquivo

RH (substituir stub):
  [ ] backend/rh/models.py
  [ ] backend/rh/serializers.py — novo arquivo
  [ ] backend/rh/views.py — novo arquivo
  [ ] backend/rh/urls.py — novo arquivo

AGENDAMENTO (substituir stub):
  [ ] backend/agendamento/models.py
  [ ] backend/agendamento/serializers.py — novo arquivo
  [ ] backend/agendamento/views.py — novo arquivo
  [ ] backend/agendamento/urls.py — novo arquivo

PORTAL (substituir stub):
  [ ] backend/portal/models.py
  [ ] backend/portal/serializers.py — novo arquivo
  [ ] backend/portal/views.py — novo arquivo
  [ ] backend/portal/urls.py — novo arquivo

CORE:
  [ ] backend/core/urls.py — adicionar 6 novos includes (vendas, pagamentos, administrativo, rh, agendamento, portal)
    Nota: conciliacoes ja vai dentro do router do financeiro existente

MIGRATIONS (7 comandos, na ordem):
  [ ] python manage.py makemigrations financeiro --name="add_conciliacao_bancaria"
  [ ] python manage.py makemigrations vendas --name="init_vendas"
  [ ] python manage.py makemigrations pagamentos --name="init_pagamentos"
  [ ] python manage.py makemigrations administrativo --name="init_administrativo"
  [ ] python manage.py makemigrations rh --name="init_rh"
  [ ] python manage.py makemigrations agendamento --name="init_agendamento"
  [ ] python manage.py makemigrations portal --name="init_portal"
  NUNCA: python manage.py makemigrations (sem app — pode falhar silenciosamente)

### Loom (Frontend) — 8 arquivos

  [ ] frontend/src/pages/Financeiro.jsx — adicionar aba + ConciliacaoTab (NAO criar arquivo novo)
  [ ] frontend/src/pages/Vendas.jsx — novo arquivo
  [ ] frontend/src/pages/Pagamentos.jsx — novo arquivo
  [ ] frontend/src/pages/Administrativo.jsx — novo arquivo
  [ ] frontend/src/pages/RH.jsx — novo arquivo
  [ ] frontend/src/pages/Agendamento.jsx — novo arquivo
  [ ] frontend/src/pages/Portal.jsx — novo arquivo
  [ ] frontend/src/App.jsx (ou routes equivalente) — adicionar 6 novas rotas
  [ ] Sidebar/menu lateral — adicionar links para novas paginas (verificar arquivo existente)

---

## Riscos e dependencias

1. poppler-utils no container: sem esse pacote, parse_c6 e parse_btg falham em runtime. O Dockerfile deve ser atualizado antes do deploy.

2. Regex dos parsers C6 e BTG: os layouts de PDF podem variar entre versoes do extrato. Se o parser retornar lista vazia para um extrato valido, o Forge deve ajustar o regex com base em uma amostra real. Os stubs (Nubank, Inter, Caixa, Itau) sao intencionais — nao implementar sem amostra real.

3. FK de accounts.User no Portal: verificar como listar usuarios para o select do frontend. Pode ser necessario um endpoint simples em accounts/views.py ou usar o admin DRF.

4. Numeracao de Orcamento/Pedido: a logica de seq no save() pode ter race condition em ambiente com multiplos workers. Para producao com alto volume, considerar uma sequence do PostgreSQL. Para o escopo atual (MEI/pequena empresa), a logica por filtro e suficiente.

5. conciliacao/ pasta vazia: a pasta backend/conciliacao/ tem apenas a pasta migrations. Ignorar completamente — os models vao em financeiro/models.py conforme especificado.
