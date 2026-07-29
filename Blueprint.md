# Blueprint — Planta Tecnica UidCore
**Sistema:** UidCore — Template Financeiro Multi-Nicho
**Versao:** AS-IS (documentado a partir do codigo em producao)
**Data:** 2026-07-28
**Autor:** Blueprint (arquiteto de software)
**Referencia:** ArquiteturaTecnica#2 / Manutencao#7

---

## 1. Estrutura Real de Pastas

```
/var/www/uidcore/
├── CLAUDE.md
├── README.md
├── classes.md
├── Levantamento_Requisitos.md
├── docs/
│   ├── 02_requisitos_funcionais.md
│   ├── 04_regras_negocio.md
│   ├── 05_modelo_dados.md
│   └── 06_arquitetura_sistema.md
├── docker-compose.yml               ← dev
├── docker-compose.prod.yml          ← producao
│
├── backend/
│   ├── manage.py
│   ├── requirements.txt
│   ├── Dockerfile                   ← python:3.12-slim + poppler-utils
│   ├── media/                       ← uploads (despesas/, comprovantes/, docs/)
│   ├── core/                        ← configuracao Django (NAO e app — sem models)
│   │   ├── settings.py
│   │   ├── urls.py                  ← entry point: /api/v1/, /admin/
│   │   ├── wsgi.py
│   │   └── asgi.py
│   ├── common/                      ← base do sistema (sem migrations)
│   │   ├── models.py                ← BaseModel, PessoaBase, UF_CHOICES
│   │   ├── pagination.py            ← StandardPagination (PAGE_SIZE=20)
│   │   ├── permissions.py           ← IsAdmin, IsOwner
│   │   └── validators.py            ← validar_documento (CPF/CNPJ)
│   ├── accounts/
│   │   ├── models.py                ← CustomUser (USERNAME_FIELD=email)
│   │   ├── managers.py              ← UserManager customizado
│   │   ├── serializers.py
│   │   ├── views.py                 ← RegisterView, UserProfileView
│   │   └── urls.py
│   ├── clientes/
│   │   ├── models.py                ← Cliente, HistoricoCliente
│   │   ├── serializers.py
│   │   ├── views.py                 ← ClienteViewSet + action historico
│   │   └── urls.py
│   ├── fornecedores/
│   │   ├── models.py                ← Fornecedor
│   │   ├── serializers.py
│   │   ├── views.py
│   │   └── urls.py
│   ├── financeiro/                  ← modulo principal — maior e mais complexo
│   │   ├── models.py                ← Conta, Aporte, Categoria, Receita, Despesa,
│   │   │                               LivroCaixa, ConciliacaoExtrato,
│   │   │                               ItemConciliacao, PadraoSeguroConciliacao
│   │   ├── signals.py               ← _gerar_lancamento, _reconstruir_cadeia,
│   │   │                               aporte/receita/despesa_para_livro_caixa
│   │   ├── serializers.py
│   │   ├── views.py                 ← ViewSets + api_view relatorios + ConciliacaoViewSet
│   │   ├── relatorios.py            ← DRE, Balanco, FluxoProjetado, Indicadores CFO
│   │   ├── parsers.py               ← extrair_texto_pdf, get_parser, parse_c6, parse_btg
│   │   ├── conciliacao_service.py   ← criar_conciliacao (matching 3 camadas)
│   │   ├── urls.py
│   │   └── management/
│   │       └── commands/
│   │           └── conciliar_extrato.py
│   ├── vendas/
│   │   ├── models.py                ← Orcamento, Pedido, ItemPedido
│   │   ├── serializers.py
│   │   ├── views.py
│   │   └── urls.py
│   ├── pagamentos/
│   │   ├── models.py                ← MetodoPagamento, Cobranca, Parcela
│   │   ├── serializers.py
│   │   ├── views.py
│   │   └── urls.py
│   ├── administrativo/
│   │   ├── models.py                ← TipoDocumento, Documento
│   │   ├── serializers.py
│   │   ├── views.py
│   │   └── urls.py
│   ├── rh/
│   │   ├── models.py                ← Cargo, Funcionario, FolhaPagamento, RegistroFerias
│   │   ├── serializers.py
│   │   ├── views.py
│   │   └── urls.py
│   ├── agendamento/
│   │   ├── models.py                ← Agenda, Compromisso
│   │   ├── serializers.py
│   │   ├── views.py
│   │   └── urls.py
│   └── portal/
│       ├── models.py                ← AcessoPortalCliente (NAO herda BaseModel)
│       ├── serializers.py
│       ├── views.py
│       └── urls.py
│
├── frontend/
│   ├── index.html
│   ├── vite.config.js               ← proxy /api -> localhost:8000 (sem base/)
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   ├── package.json
│   ├── Dockerfile                   ← dev
│   ├── Dockerfile.prod              ← multi-stage build
│   └── src/
│       ├── main.jsx
│       ├── App.jsx
│       ├── index.css                ← Plus Jakarta Sans + DM Sans via import
│       ├── api/
│       │   └── client.js            ← axios + interceptor refresh automatico
│       ├── stores/
│       │   └── authStore.js         ← Zustand + persist (localStorage)
│       ├── hooks/
│       │   └── useAuth.js
│       ├── routes/
│       │   └── index.jsx            ← ProtectedRoute + rotas declaradas
│       ├── components/
│       │   ├── layout/
│       │   │   ├── AppLayout.jsx
│       │   │   ├── Header.jsx
│       │   │   └── Sidebar.jsx
│       │   └── ui/
│       │       ├── Button.jsx
│       │       ├── Card.jsx
│       │       ├── Input.jsx
│       │       ├── Loading.jsx
│       │       ├── Modal.jsx
│       │       ├── Pagination.jsx
│       │       ├── ResourceCrud.jsx ← componente generico de CRUD reutilizavel
│       │       └── Select.jsx
│       ├── pages/
│       │   ├── Login.jsx
│       │   ├── Dashboard.jsx        ← metricas estaticas (DIV02 — endpoint existe)
│       │   ├── Clientes.jsx
│       │   ├── Fornecedores.jsx
│       │   ├── Financeiro.jsx       ← 9 abas: Contas, Aportes, Categorias,
│       │   │                           Receitas, Despesas, LivroCaixa, DRE,
│       │   │                           Balanco, Conciliacao
│       │   ├── Vendas.jsx
│       │   ├── Pagamentos.jsx
│       │   ├── Administrativo.jsx
│       │   ├── Rh.jsx
│       │   ├── Agendamento.jsx
│       │   └── Portal.jsx           ← gerencia AcessoPortalCliente
│       └── utils/
│           └── errors.js
│
└── nginx/
    └── nginx.conf                   ← /api/ /admin/ -> backend; / -> SPA
```

Nota: existe a pasta `backend/conciliacao/` no disco (DIV01) mas e ignorada.
Os models de conciliacao foram incorporados em `financeiro/models.py`.

---

## 2. Apps Django

| App | Responsabilidade | Models principais |
|---|---|---|
| common | Base abstrata, paginacao, permissoes, validators | BaseModel, PessoaBase |
| accounts | Autenticacao JWT, cadastro e perfil de usuario | User (CustomUser) |
| clientes | CRM basico: clientes PF/PJ e historico | Cliente, HistoricoCliente |
| fornecedores | Cadastro de fornecedores PF/PJ | Fornecedor |
| financeiro | Modulo financeiro completo: contas, lancamentos, relatorios, conciliacao | Conta, Aporte, Categoria, Receita, Despesa, LivroCaixa, ConciliacaoExtrato, ItemConciliacao, PadraoSeguroConciliacao |
| vendas | Orcamentos e pedidos de venda | Orcamento, Pedido, ItemPedido |
| pagamentos | Cobrancas, metodos e parcelas | MetodoPagamento, Cobranca, Parcela |
| administrativo | Gestao de documentos internos | TipoDocumento, Documento |
| rh | Recursos humanos | Cargo, Funcionario, FolhaPagamento, RegistroFerias |
| agendamento | Agendas e compromissos | Agenda, Compromisso |
| portal | Vinculo usuario-cliente para portal | AcessoPortalCliente |

Nota sobre core: nao e um app Django (sem models/views/migrations). E a pasta de
configuracao: settings.py, urls.py, wsgi.py, asgi.py.

---

## 3. Padrao de Models

### BaseModel (common/models.py)

```python
class BaseModel(models.Model):
    created_at = models.DateTimeField('criado em', auto_now_add=True)
    updated_at = models.DateTimeField('atualizado em', auto_now=True)
    is_active  = models.BooleanField('ativo', default=True)

    class Meta:
        abstract = True
```

Excecoes ao BaseModel:
- AcessoPortalCliente: usa campos proprios (ativo, criado_em)
- HistoricoCliente: campos proprios (cliente, descricao, data)
- ItemConciliacao: campos proprios sem timestamps de auditoria
- PadraoSeguroConciliacao: usa campo ativo proprio (DIV04)
- Agenda: usa campo ativo proprio ALEM de is_active herdado (DIV04)

### PessoaBase (common/models.py)

Classe abstrata que estende BaseModel. Herdada por Cliente e Fornecedor.
Campos: tipo_pessoa, documento (CPF/CNPJ unique null=True validators=[validar_documento]),
nome_razao_social, telefone, email, endereco, cidade, estado (UF choices), cep, observacoes.

### Soft Delete — padrao real implementado

Nao existe mixin centralizado. Cada ViewSet implementa:

```python
def destroy(self, request, *args, **kwargs):
    instance = self.get_object()
    instance.is_active = False
    instance.save(update_fields=['is_active', 'updated_at'])
    return Response(status=status.HTTP_204_NO_CONTENT)
```

### Prefixo de tabela no financeiro

O app financeiro usa db_table com prefixo fin_*:
- fin_conta, fin_aporte — confirmado no codigo
- Demais apps usam o padrao automatico Django: <app>_<model>

---

## 4. Padrao de ViewSets

### ReadCreateViewSet (financeiro/views.py)

Usado exclusivamente pelo LivroCaixaViewSet:

```python
class ReadCreateViewSet(CreateModelMixin, ListModelMixin, RetrieveModelMixin, GenericViewSet):
    pass
```

PUT, PATCH e DELETE retornam 405. Estorno disponivel apenas via:
POST /api/v1/financeiro/livro-caixa/{id}/estornar/ com permission_classes=[IsAdmin]

### ModelViewSet (demais recursos)

Todos os outros ViewSets herdam ModelViewSet. O destroy e sobrescrito para soft delete.

### ReadOnlyModelViewSet

Usado por ConciliacaoViewSet — listagem e somente leitura; operacoes via actions.

---

## 5. Padrao de Serializers

Observacao critica: os serializers do UidCore NAO seguem o padrao Uid de
id = serializers.IntegerField(source='pk', read_only=True).
O campo id e exposto via read_only_fields = ['id', ...] nativamente pelo DRF.
O resultado no payload e identico, mas diverge do padrao documentado nos ADRs da fabrica (DIV07).

Exemplo real (CategoriaSerializer):

```python
class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = ['id', 'nome', 'tipo', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']
```

Campos de leitura extras para relacionamentos (padrão consistente):
- conta_nome (source='conta.nome', read_only=True)
- cliente_nome (source='cliente.nome_razao_social', read_only=True)
- categoria_nome (source='categoria.nome', read_only=True)
- segmento_display (source='get_segmento_display', read_only=True)

FKs no payload: enviadas como ID inteiro (ex: "conta": 1, nao "conta_id": 1).

---

## 6. Padrao de URLs

Todas as rotas seguem o prefixo /api/v1/:

| Prefixo | App |
|---|---|
| /api/v1/auth/token/ | SimpleJWT (TokenObtainPairView) |
| /api/v1/auth/token/refresh/ | SimpleJWT (TokenRefreshView) |
| /api/v1/accounts/register/ | RegisterView (AllowAny) |
| /api/v1/accounts/me/ | UserProfileView (IsAuthenticated) |
| /api/v1/clientes/ | ClienteViewSet |
| /api/v1/fornecedores/ | FornecedorViewSet |
| /api/v1/vendas/orcamentos/ | OrcamentoViewSet |
| /api/v1/vendas/pedidos/ | PedidoViewSet |
| /api/v1/vendas/itens-pedido/ | ItemPedidoViewSet |
| /api/v1/pagamentos/metodos/ | MetodoPagamentoViewSet |
| /api/v1/pagamentos/cobrancas/ | CobrancaViewSet |
| /api/v1/pagamentos/parcelas/ | ParcelaViewSet |
| /api/v1/administrativo/tipos/ | TipoDocumentoViewSet |
| /api/v1/administrativo/documentos/ | DocumentoViewSet |
| /api/v1/rh/cargos/ | CargoViewSet |
| /api/v1/rh/funcionarios/ | FuncionarioViewSet |
| /api/v1/rh/folhas/ | FolhaPagamentoViewSet |
| /api/v1/rh/ferias/ | RegistroFeriasViewSet |
| /api/v1/agendamento/agendas/ | AgendaViewSet |
| /api/v1/agendamento/compromissos/ | CompromissoViewSet |
| /api/v1/portal/acessos/ | AcessoPortalClienteViewSet |
| /api/v1/financeiro/categorias/ | CategoriaViewSet |
| /api/v1/financeiro/contas/ | ContaViewSet |
| /api/v1/financeiro/aportes/ | AporteViewSet |
| /api/v1/financeiro/receitas/ | ReceitaViewSet |
| /api/v1/financeiro/despesas/ | DespesaViewSet |
| /api/v1/financeiro/livro-caixa/ | LivroCaixaViewSet (ReadCreateViewSet) |
| /api/v1/financeiro/conciliacoes/ | ConciliacaoViewSet (ReadOnlyModelViewSet) |
| /api/v1/financeiro/padroes-conciliacao/ | PadraoSeguroConciliacaoViewSet |
| /api/v1/financeiro/fluxo-caixa/ | api_view GET |
| /api/v1/financeiro/dre/ | api_view GET |
| /api/v1/financeiro/dashboard/ | api_view GET |
| /api/v1/financeiro/balanco/ | api_view GET |
| /api/v1/financeiro/fluxo-projetado/ | api_view GET |
| /api/v1/financeiro/indicadores/ | api_view GET |
| /api/v1/financeiro/inferir-categoria/ | api_view POST |

---

## 7. Contrato da API por Modulo

### 7.1 Accounts

| Metodo | URL | Permissao | Descricao |
|---|---|---|---|
| POST | /api/v1/auth/token/ | AllowAny | Login — retorna access + refresh |
| POST | /api/v1/auth/token/refresh/ | AllowAny | Renova access token |
| POST | /api/v1/accounts/register/ | AllowAny | Cadastro de usuario |
| GET | /api/v1/accounts/me/ | IsAuthenticated | Perfil do usuario logado |
| PATCH | /api/v1/accounts/me/ | IsAuthenticated | Atualiza perfil |

### 7.2 Clientes

| Metodo | URL | Permissao | Descricao |
|---|---|---|---|
| GET | /api/v1/clientes/ | IsAuthenticated | Lista paginada |
| POST | /api/v1/clientes/ | IsAuthenticated | Cria cliente |
| GET | /api/v1/clientes/{id}/ | IsAuthenticated | Detalhe |
| PATCH | /api/v1/clientes/{id}/ | IsAuthenticated | Atualiza parcialmente |
| DELETE | /api/v1/clientes/{id}/ | IsAuthenticated | Soft delete |
| POST | /api/v1/clientes/{id}/historico/ | IsAuthenticated | Adiciona historico |

### 7.3 Fornecedores

| Metodo | URL | Permissao | Descricao |
|---|---|---|---|
| GET | /api/v1/fornecedores/ | IsAuthenticated | Lista paginada |
| POST | /api/v1/fornecedores/ | IsAuthenticated | Cria fornecedor |
| GET | /api/v1/fornecedores/{id}/ | IsAuthenticated | Detalhe |
| PATCH | /api/v1/fornecedores/{id}/ | IsAuthenticated | Atualiza parcialmente |
| DELETE | /api/v1/fornecedores/{id}/ | IsAuthenticated | Soft delete |

### 7.4 Financeiro — Contas

| Metodo | URL | Permissao | Descricao |
|---|---|---|---|
| GET | /api/v1/financeiro/contas/ | IsAuthenticated | Lista contas ativas |
| POST | /api/v1/financeiro/contas/ | IsAuthenticated | Cria conta |
| GET | /api/v1/financeiro/contas/{id}/ | IsAuthenticated | Detalhe |
| PATCH | /api/v1/financeiro/contas/{id}/ | IsAuthenticated | Atualiza |
| DELETE | /api/v1/financeiro/contas/{id}/ | IsAuthenticated | Soft delete |
| POST | /api/v1/financeiro/contas/{id}/transferir/ | IsAuthenticated | Transferencia entre contas |

Payload transferir: { "conta_destino": 2, "valor": "500.00", "descricao": "...", "data": "2026-07-28" }

### 7.5 Financeiro — Aportes

| Metodo | URL | Permissao | Descricao |
|---|---|---|---|
| GET | /api/v1/financeiro/aportes/ | IsAdmin | Lista aportes ativos |
| POST | /api/v1/financeiro/aportes/ | IsAdmin | Registra aporte |
| GET | /api/v1/financeiro/aportes/{id}/ | IsAdmin | Detalhe |
| PATCH | /api/v1/financeiro/aportes/{id}/ | IsAdmin | Atualiza |
| DELETE | /api/v1/financeiro/aportes/{id}/ | IsAdmin | Soft delete |

### 7.6 Financeiro — Categorias

| Metodo | URL | Permissao | Descricao |
|---|---|---|---|
| GET | /api/v1/financeiro/categorias/ | IsAuthenticated | Lista (filtro: ?tipo=ENTRADA|SAIDA) |
| POST | /api/v1/financeiro/categorias/ | IsAuthenticated | Cria |
| PATCH | /api/v1/financeiro/categorias/{id}/ | IsAuthenticated | Atualiza |
| DELETE | /api/v1/financeiro/categorias/{id}/ | IsAuthenticated | Soft delete |

### 7.7 Financeiro — Receitas

| Metodo | URL | Permissao | Descricao |
|---|---|---|---|
| GET | /api/v1/financeiro/receitas/ | IsAuthenticated | Lista (?tipo ?status ?cliente ?conta) |
| POST | /api/v1/financeiro/receitas/ | IsAuthenticated | Cria receita PENDENTE |
| GET | /api/v1/financeiro/receitas/{id}/ | IsAuthenticated | Detalhe |
| PATCH | /api/v1/financeiro/receitas/{id}/ | IsAuthenticated | Atualiza |
| DELETE | /api/v1/financeiro/receitas/{id}/ | IsAuthenticated | Soft delete |
| PATCH | /api/v1/financeiro/receitas/{id}/receber/ | IsAuthenticated | Marca RECEBIDO — gera lancamento LC |

Payload receber: { "recebimento": "2026-07-28", "conta": 1 }

### 7.8 Financeiro — Despesas

| Metodo | URL | Permissao | Descricao |
|---|---|---|---|
| GET | /api/v1/financeiro/despesas/ | IsAuthenticated | Lista (?tipo ?status ?conta ?estornado) |
| POST | /api/v1/financeiro/despesas/ | IsAuthenticated | Cria despesa PENDENTE |
| PATCH | /api/v1/financeiro/despesas/{id}/ | IsAuthenticated | Atualiza |
| DELETE | /api/v1/financeiro/despesas/{id}/ | IsAuthenticated | Soft delete |
| PATCH | /api/v1/financeiro/despesas/{id}/pagar/ | IsAuthenticated | Marca PAGO — gera lancamento LC |
| POST | /api/v1/financeiro/despesas/{id}/estornar/ | IsAdmin | Estorna despesa paga |

Payload pagar: { "pagamento": "2026-07-28", "conta": 1, "forma_pagamento": "PIX" }
Payload estornar: { "motivo": "texto obrigatorio", "data_estorno": "2026-07-28" }

### 7.9 Financeiro — Livro Caixa

| Metodo | URL | Permissao | Descricao |
|---|---|---|---|
| GET | /api/v1/financeiro/livro-caixa/ | IsAuthenticated | Lista (?conta ?tipo ?origem ?estornado) |
| POST | /api/v1/financeiro/livro-caixa/ | IsAuthenticated | Cria lancamento manual |
| GET | /api/v1/financeiro/livro-caixa/{id}/ | IsAuthenticated | Detalhe |
| GET | /api/v1/financeiro/livro-caixa/totais/ | IsAuthenticated | Totais entradas/saidas/saldo |
| POST | /api/v1/financeiro/livro-caixa/{id}/estornar/ | IsAdmin | Estorna lancamento |

PUT, PATCH, DELETE retornam 405 (ReadCreateViewSet — imutabilidade por design).

### 7.10 Financeiro — Relatorios

| Metodo | URL | Permissao | Params |
|---|---|---|---|
| GET | /api/v1/financeiro/fluxo-caixa/ | IsAuthenticated | ?mes=YYYY-MM &conta=id |
| GET | /api/v1/financeiro/dre/ | IsAuthenticated | ?ano=YYYY &mes=M |
| GET | /api/v1/financeiro/balanco/ | IsAuthenticated | ?data=YYYY-MM-DD |
| GET | /api/v1/financeiro/fluxo-projetado/ | IsAuthenticated | — |
| GET | /api/v1/financeiro/indicadores/ | IsAuthenticated | — |
| GET | /api/v1/financeiro/dashboard/ | IsAuthenticated | — |
| POST | /api/v1/financeiro/inferir-categoria/ | IsAuthenticated | { "descricao": "texto" } |

### 7.11 Financeiro — Conciliacao Bancaria

| Metodo | URL | Permissao | Descricao |
|---|---|---|---|
| GET | /api/v1/financeiro/conciliacoes/ | IsAuthenticated | Lista conciliacoes |
| GET | /api/v1/financeiro/conciliacoes/{id}/ | IsAuthenticated | Detalhe |
| POST | /api/v1/financeiro/conciliacoes/upload/ | IsAuthenticated | Upload PDF (multipart) |
| GET | /api/v1/financeiro/conciliacoes/{id}/itens/ | IsAuthenticated | Itens da conciliacao |
| POST | /api/v1/financeiro/conciliacoes/{id}/confirmar-item/ | IsAuthenticated | Confirma item |
| GET | /api/v1/financeiro/padroes-conciliacao/ | IsAuthenticated | Lista padroes ativos |
| POST | /api/v1/financeiro/padroes-conciliacao/ | IsAuthenticated | Cria padrao |
| PATCH | /api/v1/financeiro/padroes-conciliacao/{id}/ | IsAuthenticated | Atualiza padrao |
| DELETE | /api/v1/financeiro/padroes-conciliacao/{id}/ | IsAuthenticated | Desativa (ativo=False) |

Payload upload: multipart/form-data com arquivo, conta_id, periodo (YYYY-MM), senha (opcional), auto (bool).

### 7.12 Vendas

| Metodo | URL | Permissao | Descricao |
|---|---|---|---|
| GET/POST | /api/v1/vendas/orcamentos/ | IsAuthenticated | CRUD orcamentos (numero auto ORC-YYYY-NNNN) |
| GET/POST | /api/v1/vendas/pedidos/ | IsAuthenticated | CRUD pedidos (numero auto PED-YYYY-NNNN) |
| GET/POST | /api/v1/vendas/itens-pedido/ | IsAuthenticated | CRUD itens de pedido |

### 7.13 Pagamentos

| Metodo | URL | Permissao | Descricao |
|---|---|---|---|
| GET/POST | /api/v1/pagamentos/metodos/ | IsAuthenticated | CRUD MetodoPagamento |
| GET/POST | /api/v1/pagamentos/cobrancas/ | IsAuthenticated | CRUD Cobrancas (multipart para comprovante) |
| GET/POST | /api/v1/pagamentos/parcelas/ | IsAuthenticated | CRUD Parcelas |

### 7.14 Administrativo

| Metodo | URL | Permissao | Descricao |
|---|---|---|---|
| GET/POST | /api/v1/administrativo/tipos/ | IsAuthenticated | CRUD TipoDocumento |
| GET/POST | /api/v1/administrativo/documentos/ | IsAuthenticated | CRUD Documento (multipart para arquivo) |

### 7.15 RH

| Metodo | URL | Permissao | Descricao |
|---|---|---|---|
| GET/POST | /api/v1/rh/cargos/ | IsAuthenticated | CRUD Cargo |
| GET/POST | /api/v1/rh/funcionarios/ | IsAuthenticated | CRUD Funcionario (CPF unique) |
| GET/POST | /api/v1/rh/folhas/ | IsAuthenticated | CRUD FolhaPagamento |
| GET/POST | /api/v1/rh/ferias/ | IsAuthenticated | CRUD RegistroFerias |

### 7.16 Agendamento

| Metodo | URL | Permissao | Descricao |
|---|---|---|---|
| GET/POST | /api/v1/agendamento/agendas/ | IsAuthenticated | CRUD Agenda |
| GET/POST | /api/v1/agendamento/compromissos/ | IsAuthenticated | CRUD Compromisso (valida fim >= inicio) |

### 7.17 Portal

| Metodo | URL | Permissao | Descricao |
|---|---|---|---|
| GET | /api/v1/portal/acessos/ | IsAuthenticated | Lista acessos |
| POST | /api/v1/portal/acessos/ | IsAuthenticated | Vincula usuario a cliente |
| PATCH | /api/v1/portal/acessos/{id}/ | IsAuthenticated | Ativa/desativa acesso |

---

## 8. Permissoes por Perfil

| Permissao | Implementacao | Quem tem |
|---|---|---|
| IsAdmin | common/permissions.py — is_staff == True | Somente usuarios ADMIN |
| IsAuthenticated | DRF nativa | Qualquer usuario logado |
| AllowAny | DRF nativa | Endpoints publicos |

DEFAULT_PERMISSION_CLASSES: IsAuthenticated — todos os endpoints protegidos por padrao.

Permissoes especificas por endpoint:
- AporteViewSet: permission_classes = [IsAdmin]
- DespesaViewSet.estornar_despesa: permission_classes=[IsAdmin]
- LivroCaixaViewSet.estornar: permission_classes=[IsAdmin]
- ConciliacaoViewSet: permission_classes=[IsAuthenticated]
- RegisterView: permission_classes = [AllowAny]

---

## 9. Padrao de Paginacao

```python
class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100
```

Formato de resposta de lista:
```json
{
  "count": 100,
  "next": "https://uidcore.uidsoftware.com.br/api/v1/clientes/?page=2",
  "previous": null,
  "results": []
}
```

Frontend: SEMPRE response.data.results. NUNCA response.data direto.

---

## 10. Padrao de Filtros e Ordenacao

| ViewSet | Filtros DjangoFilter | Search | Ordering |
|---|---|---|---|
| Aporte | tipo, conta | — | data, valor |
| Receita | tipo, status, cliente, conta | descricao | vencimento, valor_liquido, status |
| Despesa | tipo, status, conta, estornado | descricao, fornecedor | vencimento, valor_liquido, status |
| LivroCaixa | conta, tipo, origem, estornado | — | data, valor |
| Conta | — | nome | — |
| Categoria | tipo | — | — |

---

## 11. Fluxo JWT

```
1. POST /api/v1/auth/token/ → { "email": "...", "password": "..." }
   Response: { "access": "...", "refresh": "..." }

2. authStore (Zustand) → persist em localStorage como 'uidcore-auth'
   { accessToken, refreshToken, user, isAuthenticated }

3. client.js (axios) → interceptor de request:
   Authorization: Bearer {accessToken}

4. Em 401: interceptor de response:
   - Se nao esta renovando: POST /api/v1/auth/token/refresh/ com { refresh }
   - Sucesso: atualiza accessToken no store, repete requisicao original
   - Falha: logout() limpa store, redirect para /login
   - Fila pendente (pendingRequests) resolve apos renovacao — evita multiplos refreshes simultaneos

5. Tokens:
   ACCESS_TOKEN_LIFETIME  = 1 hora
   REFRESH_TOKEN_LIFETIME = 7 dias
   ROTATE_REFRESH_TOKENS  = True
   BLACKLIST_AFTER_ROTATION = False
```

---

## 12. Infraestrutura

```
uidcore.uidsoftware.com.br          → nginx-proxy global (SSL Let's Encrypt)
    ↓
127.0.0.1:8006                      → nginx interno (docker-compose.prod.yml)
    ↓
/api/*  /admin/*                    → backend:8000 (Gunicorn 3 workers)
/static/*                           → volume static_volume
/                                   → frontend build (volume frontend_build, SPA)
```

Servicos docker-compose.prod.yml:
- db: postgres:16-alpine, healthcheck pg_isready
- backend: python:3.12-slim + poppler-utils, gunicorn 3 workers
- frontend-builder: build multi-stage, copia dist para volume (sem npm na VPS)
- nginx: porta 127.0.0.1:8006:80, proxy backend + serve SPA

---

## 13. Signals do LivroCaixa

```
financeiro/signals.py:

_ultimo_saldo(conta)           → retorna saldo_atual do ultimo lancamento

_reconstruir_cadeia(conta)     → recalcula saldo_anterior e saldo_atual
                                  de TODOS os lancamentos da conta em ordem
                                  cronologica (data, criado_em) via select_for_update()
                                  + bulk_update — chamado dentro de transaction.atomic()
                                  com pg_advisory_xact_lock

_gerar_lancamento(...)         → verifica idempotencia (origem+origem_id existente),
                                  atualiza se mudou (data/valor/descricao),
                                  cria lancamento e chama _reconstruir_cadeia()

@receiver(post_save, Aporte)   → aporte_para_livro_caixa — created=True only
@receiver(post_save, Receita)  → receita_para_livro_caixa — status=='RECEBIDO' and recebimento
@receiver(post_save, Despesa)  → despesa_para_livro_caixa — status=='PAGO' and pagamento
```

---

## 14. Conciliacao Bancaria — Arquitetura

```
financeiro/parsers.py
  extrair_texto_pdf(caminho, senha=None)  → chama pdftotext via subprocess
  get_parser(nome_conta)                 → case-insensitive substring match no nome da conta
  parse_c6(texto, ano)                   → parser regex C6 Bank
  parse_btg(texto, ano)                  → parser regex BTG
  stubs: nubank, inter, caixa, itau     → retornam [] (a implementar por demanda)

financeiro/conciliacao_service.py → criar_conciliacao(conta, transacoes_banco, ...)
  Camada 1: data+valor+tipo +-1 dia → marca CONCILIADO
  Camada 2 (auto=True): assenta pendentes/atrasados encontrados
  Camada 3 (auto=True): cria por PadraoSeguroConciliacao.ativo=True
  Sem match: FALTANDO_SISTEMA → aguarda confirmacao manual do ADMIN

ConciliacaoViewSet.confirmar_item
  → seta item.confirmado=True
  → recalcula divergencias
  → atualiza status da conciliacao (PROCESSADO ou COM_DIVERGENCIAS)
```

---

## 15. Divergencias Encontradas

| ID | Descricao | Impacto | Recomendacao |
|---|---|---|---|
| DIV01 | Pasta backend/conciliacao/ no disco; models em financeiro/. | Baixo | Remover pasta vazia em proximo ciclo |
| DIV02 | Dashboard.jsx exibe metricas estaticas; endpoint /dashboard/ funciona mas nao e consumido. | Medio | Integrar endpoint real na proxima sprint |
| DIV03 | Portal do cliente sem telas para o perfil CLIENTE. | Medio | Implementar por nicho — fora do escopo do core |
| DIV04 | AcessoPortalCliente, Agenda, PadraoSeguroConciliacao: campo ativo proprio em vez de is_active herdado. | Baixo | Padronizar em migracao futura |
| DIV05 | MetodoPagamento: dois booleanos (ativo proprio + is_active herdado). | Baixo | Consolidar em campo unico |
| DIV06 | Financeiro.jsx: 9 abas no componente principal. | Baixo | Considerar split em sub-rotas |
| DIV07 | Serializers nao usam id = IntegerField(source='pk'). Usam read_only_fields=['id'] nativamente. | Muito baixo | Padronizar na proxima refatoracao |
| DIV08 | HistoricoCliente e ItemConciliacao nao herdam BaseModel. | Baixo | Decisao intencional — sem timestamps necessarios |
| DIV09 | core/ e pasta de configuracao, nao app Django. Padrao diferente de outros projetos Uid que usam config/. | Baixo | Aceitar como padrao do UidCore |
| DIV10 | Endpoint de listagem de usuarios ausente. Portal pode precisar de /api/v1/accounts/users/ para select. | Medio | Implementar se Portal for expandido |
