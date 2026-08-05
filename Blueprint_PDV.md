# Blueprint — Módulo PDV (Ponto de Venda) — UidCore — Manutenção #15

**Sistema:** UidCore — Template Financeiro Multi-Nicho
**Autor:** Blueprint (arquiteto de software)
**Data:** 2026-08-04
**Referência:** Especificacao_Hotfix.md (492 linhas) + Especificacao_UI_Hotfix.md (390 linhas)
**Complementa:** Blueprint.md (planta AS-IS existente) e ADRs.md (ADR-001 a ADR-014)

Este documento **não redefine** nada já decidido em Blueprint.md/ADRs.md — assume
ADR-003 (imutabilidade de ledger), ADR-004 (soft delete via `is_active`), ADR-006
(reconstrução de cadeia + advisory lock), ADR-007 (estorno em par), ADR-008 (cartão
como Conta), ADR-010 (Decimal), ADR-011 (migração por app) como base obrigatória
para tudo que segue.

---

## 0. As 3 decisões resolvidas nesta planta

| # | Pergunta em aberto (Seção 15 da spec) | Decisão | ADR |
|---|---|---|---|
| 1 | App `pdv` novo vs. dentro de `vendas` | **App novo `pdv`** | ADR-015 |
| 2 | DRE abate estorno no mês da receita original ou no mês do estorno | **Mês da receita original** (`recebimento`) | ADR-017 |
| 3 | Mapeamento `MetodoPagamento` ↔ `Conta` | **Campo direto `MetodoPagamento.conta_padrao`** (FK `financeiro.Conta`, null=True) — pré-requisito técnico, sem aprovação comercial pendente | ADR-018 |

Razões detalhadas em cada ADR (Seção 5). Forge não deve iniciar sem ler os 7 ADRs
novos (ADR-015 a ADR-021) — mesma regra já vigente no CLAUDE.md ("Ler TODOS os
ADRs do Blueprint antes de escrever qualquer linha de código").

---

## 1. Por que app novo `pdv` (justificativa técnica do ADR-015)

`vendas.Pedido`/`vendas.ItemPedido` são fluxo de **encomenda B2B**: não debitam
estoque, não geram `Receita`/`LivroCaixa`, não têm sessão de caixa (achado A3 do
Analista, confirmado lendo `vendas/models.py`). O PDV é **venda de balcão à vista**
com caixa físico, split de pagamento, baixa de estoque síncrona e geração
automática de lançamento financeiro — um domínio de negócio genuinamente diferente,
mesmo padrão de separação já usado no sistema entre `financeiro` (ledger) e
`pagamentos` (cobrança/parcelamento a prazo). Colocar PDV dentro de `vendas`
misturaria dois ciclos de vida incompatíveis (`Pedido.status` é
PENDENTE→CONFIRMADO→EM_PRODUCAO→ENTREGUE; `Venda.status` do PDV é
ABERTA→FINALIZADA/CANCELADA, decidido em minutos no balcão) no mesmo app,
dificultando manutenção futura. App novo `pdv`, seguindo exatamente o padrão de
pastas já usado por todo módulo do UidCore.

---

## 2. Estrutura de Pastas — Novo App `pdv`

```
backend/
├── core/
│   └── settings.py                 ← LOCAL_APPS: adicionar 'pdv' ao final da lista
│   └── urls.py                     ← adicionar: path('api/v1/pdv/', include('pdv.urls'))
├── pdv/                             ← APP NOVO
│   ├── __init__.py
│   ├── apps.py
│   ├── models.py                    ← SessaoCaixa, MovimentoCaixa, Venda, ItemVenda,
│   │                                    PagamentoVenda, RecebivelCartao
│   ├── serializers.py
│   ├── services.py                  ← finalizar_venda, cancelar_venda, devolver_item,
│   │                                    abrir_sessao, fechar_sessao (Seção 8 — hooks)
│   ├── views.py                     ← SessaoCaixaViewSet, VendaViewSet
│   ├── permissions.py               ← (se necessário: reexporta IsAdmin de common)
│   ├── urls.py
│   ├── admin.py
│   ├── tests.py
│   └── migrations/
│
├── financeiro/                      ← ALTERADO (não novo app)
│   ├── models.py                    ← Receita ganha 3 campos + properties;
│   │                                    NOVO model EstornoReceita
│   ├── services.py                  ← NOVO ARQUIVO — estornar_receita() compartilhada
│   │                                    entre ReceitaViewSet.estornar e pdv/services.py
│   │                                    (mesmo padrão de conciliacao_service.py já existente)
│   ├── views.py                     ← ReceitaViewSet ganha action `estornar`;
│   │                                    ConciliacaoViewSet.confirmar_item estendida (RF-17)
│   ├── serializers.py               ← +EstornoReceitaSerializer; ReceitaSerializer +3 campos
│   ├── relatorios.py                ← calcular_dre_mes() abate EstornoReceita (ADR-017)
│   ├── urls.py                      ← +estornos-receita/ (auditoria, GET only)
│   └── migrations/                  ← nova migration financeiro
│
└── pagamentos/                      ← ALTERADO (não novo app)
    ├── models.py                    ← MetodoPagamento +conta_padrao +taxa_percentual_padrao
    └── migrations/                  ← nova migration pagamentos
```

```
frontend/src/
├── pages/
│   └── pdv/                         ← pasta nova (múltiplos arquivos — módulo grande)
│       ├── AberturaCaixa.jsx
│       ├── FrenteDeCaixa.jsx
│       ├── FechamentoCaixa.jsx
│       ├── HistoricoVendas.jsx
│       ├── RelatorioSessoes.jsx
│       └── components/
│           ├── ModalSangriaSuprimento.jsx
│           ├── CarrinhoItem.jsx
│           ├── SplitPagamento.jsx
│           └── ResumoSessao.jsx      ← compartilhado entre Fechamento e Relatório
├── routes/index.jsx                 ← +6 rotas /pdv/*
└── components/layout/Sidebar.jsx    ← +item "PDV" entre Vendas e Financeiro
```
Nota de organização (Loom decide o resto): pasta `pages/pdv/` com múltiplos
arquivos, não um `Pdv.jsx` único com tabs — módulo tem 6 telas com fluxos e
estados independentes (diferente de `Financeiro.jsx`, que são 9 abas do mesmo
recurso). `Especificacao_UI_Hotfix.md` deixou essa escolha para o Loom; a
recomendação registrada lá era tabs único — **diverge aqui intencionalmente**:
Abertura/Frente de Caixa/Fechamento são telas de fluxo sequencial com rotas
próprias (`/pdv/abertura`, `/pdv/venda`, `/pdv/fechamento`), não abas de um
mesmo recurso CRUD. Histórico e Relatório de Sessões são as duas únicas telas
"tipo Financeiro.jsx" (lista+filtro+detalhe).

---

## 3. Models — Esboço Completo

### 3.1 App `pdv` — `SessaoCaixa`

```python
# pdv/models.py
from decimal import Decimal
from datetime import date

from django.conf import settings
from django.db import models

from common.models import BaseModel
from produtos.models import UnidadeBase


class StatusSessaoCaixa(models.TextChoices):
    ABERTA = 'ABERTA', 'Aberta'
    FECHADA = 'FECHADA', 'Fechada'


class SessaoCaixa(BaseModel):
    """Sessão de caixa físico. RN-01: no máximo 1 ABERTA por conta (não global)."""
    conta = models.ForeignKey(
        'financeiro.Conta', on_delete=models.PROTECT, related_name='sessoes_caixa',
    )
    operador = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='sessoes_caixa',
    )
    valor_abertura = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    data_abertura = models.DateTimeField(auto_now_add=True)
    data_fechamento = models.DateTimeField(null=True, blank=True)
    valor_fechamento_informado = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
    )
    valor_fechamento_calculado = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
    )
    diferenca = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=10, choices=StatusSessaoCaixa.choices, default='ABERTA')
    observacoes = models.TextField(blank=True)

    class Meta:
        db_table = 'pdv_sessao_caixa'
        ordering = ['-data_abertura']
        constraints = [
            models.UniqueConstraint(
                fields=['conta'], condition=models.Q(status='ABERTA'),
                name='uniq_sessao_aberta_por_conta',
            ),
        ]

    def __str__(self):
        return f'Sessão #{self.pk} — {self.conta.nome} ({self.status})'
```
**Nota de implementação (RN-01):** a `UniqueConstraint` condicional é a garantia
de última linha contra race condition — mas para retornar erro 400 legível (em
vez de `IntegrityError` 500), `services.abrir_sessao()` faz o check com
`select_for_update()` dentro de `transaction.atomic()` **antes** do `create()`,
igual ao espírito de `pg_advisory_xact_lock` já usado no financeiro. A
constraint é o cinto de segurança, não a validação primária.

### 3.2 `MovimentoCaixa`

```python
class TipoMovimentoCaixa(models.TextChoices):
    SANGRIA = 'SANGRIA', 'Sangria'
    SUPRIMENTO = 'SUPRIMENTO', 'Suprimento'


class MovimentoCaixa(BaseModel):
    """Sangria/suprimento de gaveta. NÃO gera Receita/Despesa/LivroCaixa (Seção 4.2
    da spec) — é movimentação física, entra só no cálculo de fechamento da sessão."""
    sessao = models.ForeignKey(SessaoCaixa, on_delete=models.PROTECT, related_name='movimentos')
    tipo = models.CharField(max_length=10, choices=TipoMovimentoCaixa.choices)
    valor = models.DecimalField(max_digits=12, decimal_places=2)
    motivo = models.TextField()
    operador = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    data_hora = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'pdv_movimento_caixa'
        ordering = ['-data_hora']

    def __str__(self):
        return f'{self.tipo} R$ {self.valor} — sessão #{self.sessao_id}'
```

### 3.3 `Venda` e `ItemVenda`

```python
class StatusVenda(models.TextChoices):
    ABERTA = 'ABERTA', 'Aberta'
    FINALIZADA = 'FINALIZADA', 'Finalizada'
    CANCELADA = 'CANCELADA', 'Cancelada'


class Venda(BaseModel):
    numero = models.CharField(max_length=20, unique=True, blank=True)  # VDA-YYYY-NNNN
    sessao_caixa = models.ForeignKey(SessaoCaixa, on_delete=models.PROTECT, related_name='vendas')
    cliente = models.ForeignKey(
        'clientes.Cliente', null=True, blank=True,
        on_delete=models.PROTECT, related_name='vendas_pdv',
    )
    operador = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='vendas_pdv')
    status = models.CharField(max_length=12, choices=StatusVenda.choices, default='ABERTA')
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    desconto_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    valor_total = models.DecimalField(max_digits=12, decimal_places=2, editable=False, default=0)
    data_hora = models.DateTimeField(auto_now_add=True)
    cancelada_em = models.DateTimeField(null=True, blank=True)
    motivo_cancelamento = models.TextField(blank=True)

    class Meta:
        db_table = 'pdv_venda'
        ordering = ['-data_hora']

    def save(self, *args, **kwargs):
        if not self.numero:
            ano = date.today().year
            ultimo = (
                Venda.objects.filter(numero__startswith=f'VDA-{ano}-')
                .order_by('-numero').first()
            )
            seq = 1
            if ultimo:
                try:
                    seq = int(ultimo.numero.split('-')[-1]) + 1
                except (ValueError, IndexError):
                    seq = 1
            self.numero = f'VDA-{ano}-{seq:04d}'
        super().save(*args, **kwargs)

    def recalcular_total(self):
        agregado = self.itens.filter(is_active=True).aggregate(v=models.Sum('valor_total'))
        self.subtotal = agregado['v'] or Decimal('0')
        self.valor_total = self.subtotal - self.desconto_total
        self.save(update_fields=['subtotal', 'valor_total'])

    def __str__(self):
        return f'{self.numero} — {self.status}'


class ItemVenda(BaseModel):
    venda = models.ForeignKey(Venda, on_delete=models.CASCADE, related_name='itens')
    produto = models.ForeignKey(
        'produtos.Produto', on_delete=models.PROTECT, related_name='itens_venda_pdv',
    )
    quantidade = models.DecimalField(max_digits=12, decimal_places=3)
    unidade = models.CharField(max_length=2, choices=UnidadeBase.choices)
    valor_unitario = models.DecimalField(max_digits=12, decimal_places=2)  # snapshot — RN-03
    desconto_item = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    valor_total = models.DecimalField(max_digits=12, decimal_places=2, editable=False, default=0)
    quantidade_estornada = models.DecimalField(max_digits=12, decimal_places=3, default=0)

    class Meta:
        db_table = 'pdv_item_venda'
        ordering = ['id']

    def save(self, *args, **kwargs):
        self.valor_total = (self.quantidade * self.valor_unitario) - self.desconto_item
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.produto.nome} x{self.quantidade}'
```

### 3.4 `PagamentoVenda` e `RecebivelCartao`

```python
class PagamentoVenda(BaseModel):
    venda = models.ForeignKey(Venda, on_delete=models.CASCADE, related_name='pagamentos')
    metodo = models.ForeignKey(
        'pagamentos.MetodoPagamento', on_delete=models.PROTECT, related_name='pagamentos_venda',
    )
    valor = models.DecimalField(max_digits=12, decimal_places=2)
    conta = models.ForeignKey(
        'financeiro.Conta', on_delete=models.PROTECT, related_name='pagamentos_venda',
    )  # resolvida em services.finalizar_venda — ver RF-14/ADR-018
    receita = models.ForeignKey(
        'financeiro.Receita', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='pagamento_venda_origem',
    )

    class Meta:
        db_table = 'pdv_pagamento_venda'
        ordering = ['id']

    def __str__(self):
        return f'{self.metodo} R$ {self.valor} — venda {self.venda_id}'


class StatusRecebivelCartao(models.TextChoices):
    PREVISTO = 'PREVISTO', 'Previsto'
    LIQUIDADO = 'LIQUIDADO', 'Liquidado'
    CANCELADO = 'CANCELADO', 'Cancelado'


class RecebivelCartao(BaseModel):
    pagamento = models.OneToOneField(
        PagamentoVenda, on_delete=models.PROTECT, related_name='recebivel_cartao',
    )
    receita = models.OneToOneField(
        'financeiro.Receita', on_delete=models.PROTECT, related_name='recebivel_cartao',
    )
    taxa_percentual = models.DecimalField(max_digits=5, decimal_places=2)
    valor_bruto = models.DecimalField(max_digits=12, decimal_places=2)
    valor_liquido_previsto = models.DecimalField(max_digits=12, decimal_places=2, editable=False)
    data_prevista_liquidacao = models.DateField()
    data_liquidacao = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=StatusRecebivelCartao.choices, default='PREVISTO')
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='+',
    )

    class Meta:
        db_table = 'pdv_recebivel_cartao'
        ordering = ['data_prevista_liquidacao']

    def __str__(self):
        return f'Recebível cartão R$ {self.valor_liquido_previsto} — {self.status}'
```

### 3.5 App `financeiro` — alterações em `Receita` + novo `EstornoReceita`

```python
# financeiro/models.py — adicionar em Receita (não remover nada existente):

class Receita(BaseModel):
    # ... campos existentes inalterados ...
    estornado = models.BooleanField(default=False)       # True quando saldo_disponivel <= 0
    data_estorno = models.DateField(null=True, blank=True)
    motivo_estorno = models.TextField(blank=True)
    # docstring obrigatória (evitar confusão com Despesa.estornado, que é booleano
    # de "existe estorno" — aqui significa "saldo esgotado", pode haver >1 estorno)

    @property
    def valor_estornado_total(self):
        from django.db.models import Sum
        return self.estornos.aggregate(v=Sum('valor'))['v'] or Decimal('0')

    @property
    def saldo_disponivel(self):
        return self.valor_liquido - self.valor_estornado_total


class EstornoReceita(BaseModel):
    """Estorno parcial/total de Receita. Mecanismo genérico do financeiro — o vínculo
    com PDV (item_venda) é opcional, para não acoplar o financeiro ao app pdv em
    lógica de negócio (só em migration graph, ver ADR-016). NUNCA editável/deletável
    via API — ReadCreateViewSet, mesmo espírito de LivroCaixa (ADR-003)."""
    receita = models.ForeignKey(
        Receita, on_delete=models.PROTECT, related_name='estornos',
    )
    valor = models.DecimalField(max_digits=12, decimal_places=2)  # > 0
    motivo = models.TextField()
    data_estorno = models.DateField()
    item_venda = models.ForeignKey(
        'pdv.ItemVenda', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='estornos',
    )
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='+',
    )

    class Meta:
        db_table = 'fin_estorno_receita'
        ordering = ['-data_estorno']

    def __str__(self):
        return f'Estorno R$ {self.valor} — receita {self.receita_id}'
```

### 3.6 App `pagamentos` — alteração em `MetodoPagamento`

```python
# pagamentos/models.py — adicionar em MetodoPagamento:

class MetodoPagamento(BaseModel):
    nome = models.CharField(...)  # inalterado
    conta_padrao = models.ForeignKey(
        'financeiro.Conta', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='metodos_pagamento_padrao',
        help_text='Conta creditada por padrão ao finalizar venda no PDV (RF-14). '
                   'Se ausente, operador escolhe manualmente no split.',
    )
    taxa_percentual_padrao = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text='Pré-preenche taxa da maquininha no split (RF-18, Should). '
                   'Só relevante quando nome=CARTAO_CREDITO.',
    )
```

---

## 4. Contrato da API — Módulo PDV

Todas as rotas sob `/api/v1/pdv/`, seguindo `StandardPagination` (PAGE_SIZE=20),
`id = serializers.IntegerField(source='pk', read_only=True)` (RNF-04), FKs no
payload como ID puro (não `_id`), soft delete via `is_active` onde aplicável
(RNF-05).

### 4.1 Sessão de Caixa

| Método | URL | Permissão | Descrição |
|---|---|---|---|
| GET | `/api/v1/pdv/sessoes/` | IsAuthenticated | Lista — operador comum vê só as próprias; `is_staff` vê todas (RF-16). Filtros: `?conta ?operador ?status ?data_abertura_after ?data_abertura_before` |
| POST | `/api/v1/pdv/sessoes/` | IsAuthenticated | Abre sessão — RF-01/RF-02 |
| GET | `/api/v1/pdv/sessoes/{id}/` | IsAuthenticated | Detalhe |
| GET | `/api/v1/pdv/sessoes/atual/` | IsAuthenticated | Sessão `ABERTA` do operador logado (qualquer conta) — usado pelo gate de rota do Loom |
| POST | `/api/v1/pdv/sessoes/{id}/movimento/` | IsAuthenticated | Sangria/Suprimento — RF-10. Payload: `{"tipo": "SANGRIA\|SUPRIMENTO", "valor": "50.00", "motivo": "troco"}` |
| POST | `/api/v1/pdv/sessoes/{id}/fechar/` | IsAuthenticated | Fecha sessão — RF-11. Payload: `{"valor_fechamento_informado": "530.00", "observacoes": "..."}`. **Nunca bloqueia por diferença (RN-07).** |

Payload POST abrir: `{"conta": 1, "valor_abertura": "100.00"}`
Erros: `400 {"conta": "Já existe sessão aberta nesta conta."}` (RN-01, não 500).

Response detalhe de sessão inclui `movimentos` (nested read-only) e campos
calculados só após fechamento: `valor_fechamento_calculado`, `diferenca`.

### 4.2 Venda

| Método | URL | Permissão | Descrição |
|---|---|---|---|
| GET | `/api/v1/pdv/vendas/` | IsAuthenticated | Lista — RF-15. Filtros: `?data_hora_after ?data_hora_before ?operador ?status ?cliente ?sessao_caixa`. Search: `numero` |
| POST | `/api/v1/pdv/vendas/` | IsAuthenticated | Abre `Venda` vazia (status=ABERTA) vinculada à sessão do operador — RN-02 valida sessão ABERTA |
| GET | `/api/v1/pdv/vendas/{id}/` | IsAuthenticated | Detalhe (itens + pagamentos nested) |
| POST | `/api/v1/pdv/vendas/{id}/itens/` | IsAuthenticated | Adiciona item ao carrinho — RF-03/RF-04. Payload: `{"produto": 5, "quantidade": "2.000", "unidade": "UN", "desconto_item": "0.00"}` (`valor_unitario` é resolvido no backend a partir de `Produto.preco_venda`, nunca aceito do cliente — RN-03) |
| PATCH | `/api/v1/pdv/vendas/{id}/itens/{item_id}/` | IsAuthenticated | Edita quantidade/desconto de item ainda no carrinho (venda ABERTA) |
| DELETE | `/api/v1/pdv/vendas/{id}/itens/{item_id}/` | IsAuthenticated | Remove item do carrinho (venda ABERTA) — soft delete |
| POST | `/api/v1/pdv/vendas/{id}/finalizar/` | IsAuthenticated | Finaliza — RF-06/RF-07/RF-08/RF-09 (Seção 8.2) |
| POST | `/api/v1/pdv/vendas/{id}/cancelar/` | IsAuthenticated | Cancela venda inteira — RF-12/RN-08 (Seção 8.3) |
| POST | `/api/v1/pdv/vendas/{id}/itens/{item_id}/devolver/` | IsAuthenticated | Devolução parcial — RF-13 (Seção 8.4) |

Payload finalizar:
```json
{
  "pagamentos": [
    {"metodo": 1, "valor": "40.00", "conta": 2},
    {"metodo": 3, "valor": "80.00", "taxa_percentual": "3.50", "prazo_dias": 30}
  ]
}
```
`conta` no item de pagamento é opcional se `MetodoPagamento.conta_padrao` estiver
configurado (RF-14) — se ausente nos dois lugares, erro 400.
`taxa_percentual`/`prazo_dias` obrigatórios apenas quando `metodo.nome ==
CARTAO_CREDITO` (Ponto 3).

Payload devolver: `{"quantidade": "1.000", "motivo": "produto com defeito", "pagamento_id": 7}`
(`pagamento_id` = de qual `PagamentoVenda`/`Receita` da venda sai o estorno —
recomendação do Brush, UX simples sem rateio automático na v1).

Payload cancelar: `{"motivo": "venda duplicada por engano"}`

Erros de negócio sempre 400 com corpo legível, nunca 500 — mesmo padrão de
`transferir`/`estornar_despesa`:
- RF-07: `{"itens_sem_estoque": [{"item_id": 3, "produto": "Coca-Cola 350ml", "disponivel": "1.000", "solicitado": "3.000"}]}`
- RF-09: `{"pagamentos": "Soma dos pagamentos (R$ 100,00) difere do total da venda (R$ 120,00)."}`
- RN-02: `{"sessao_caixa": "Sessão de caixa não está aberta."}`

### 4.3 Financeiro — endpoints alterados/novos (Ponto 2 e Ponto 3)

| Método | URL | Permissão | Descrição |
|---|---|---|---|
| POST | `/api/v1/financeiro/receitas/{id}/estornar/` | IsAdmin | Estorno parcial/total — Seção 5.4 da spec |
| GET | `/api/v1/financeiro/estornos-receita/` | IsAuthenticated | Auditoria, somente leitura — `?receita ?item_venda` |
| POST | `/api/v1/financeiro/conciliacoes/{id}/confirmar-item/` | IsAuthenticated | **Estendido** — payload ganha `recebivel_cartao_id` opcional (Seção 8.5) |
| GET | `/api/v1/financeiro/conciliacoes/{id}/itens/{item_id}/recebiveis-sugeridos/` | IsAuthenticated | RF-17 (Should) — sugestão de vínculo por valor/data |

Payload estornar: `{"valor": "20.00", "motivo": "devolução parcial", "data_estorno": "2026-08-04", "item_venda_id": 12}`
(`valor` omitido = estorno total do `saldo_disponivel`, mesmo comportamento
equivalente ao de `Despesa`).

Payload confirmar-item estendido: `{"item_id": 9, "recebivel_cartao_id": 4}` (se
ausente, comportamento atual inalterado — cria `LivroCaixa origem=MANUAL`).

`ReceitaViewSet.filterset_fields` ganha `'estornado'` (paridade com `Despesa`,
já citada como padrão em Blueprint.md Seção 10).

### 4.4 Pagamentos — endpoint alterado

`MetodoPagamentoSerializer` ganha `conta_padrao` e `taxa_percentual_padrao`
(read/write). Sem endpoint novo — reaproveita `PATCH /api/v1/pagamentos/metodos/{id}/`
já existente. A "Tela 7" (Should) do Brush é um `ResourceCrud.jsx` apontando
para esse endpoint já existente, sem rota nova no backend.

---

## 5. ADRs Novos (ADR-015 a ADR-021)

> Adicionados a `ADRs.md` na íntegra — replicados aqui em resumo para leitura
> em contexto. Ver arquivo `ADRs.md` para o texto completo Contexto/Decisão/
> Consequências/Alternativas de cada um.

| ADR | Título | Resolve |
|---|---|---|
| ADR-015 | App `pdv` separado de `vendas` | Achado A3 |
| ADR-016 | `EstornoReceita` como mecanismo genérico do `financeiro`, vínculo opcional com `pdv` | Ponto 2 |
| ADR-017 | DRE abate estorno de Receita no mês da receita original | Seção 5.5 |
| ADR-018 | Mapeamento `MetodoPagamento.conta_padrao` como campo direto | Achado A4 |
| ADR-019 | `RecebivelCartao` acoplado à Conciliação existente, sem sistema paralelo | Ponto 3 |
| ADR-020 | Lock de concorrência por Conta **e** por Produto na finalização de venda | Risco de estoque (Seção 13 da spec) |
| ADR-021 | Orquestração de finalização de venda via `services.py` procedural, não via signal Django | Design dos hooks (Seção 8) |

---

## 6. Signals / Hooks — Especificação Completa

O sistema já tem **dois estilos** de efeito colateral, e cada operação do PDV
usa o estilo certo — não force tudo em um só:

1. **Signal Django `post_save`** — usado quando o efeito é *sempre* o mesmo,
   sem dado externo ao próprio objeto que está sendo salvo (padrão já existente:
   `aporte_para_livro_caixa`, `receita_para_livro_caixa`, `despesa_para_livro_caixa`
   em `financeiro/signals.py`).
2. **Função de serviço procedural dentro de `transaction.atomic()`** — usada
   quando a operação precisa de: (a) dados do payload da requisição que não
   pertencem a nenhum model persistido isoladamente, (b) validação com abort
   antes do commit, ou (c) múltiplos passos coordenados sobre vários registros.
   Padrão já existente: `ContaViewSet.transferir`, `DespesaViewSet.estornar_despesa`,
   `ConciliacaoViewSet.confirmar_item` — **nenhum desses é um signal**, e o PDV
   segue a mesma linha (ADR-021).

### 6.1 Baixa de estoque na finalização da venda

**Não é um signal.** É o passo 4 de `services.finalizar_venda()` (Seção 6.2
abaixo). Motivo: precisa abortar com erro 400 legível **antes** de debitar
qualquer coisa se **qualquer** item da venda tiver estoque insuficiente (RF-07)
— um `post_save` de `ItemVenda` já teria sido persistido quando o signal
disparasse, tarde demais para abortar a operação inteira de forma limpa.

```python
# pdv/services.py — baixa de estoque, inversa exata de EntradaEstoque.save() (achado A7)
from django.db.models import F
from produtos.models import ConversaoUnidade, Produto

def _quantidade_base(item):
    if item.unidade == item.produto.unidade_base:
        return item.quantidade
    try:
        conv = ConversaoUnidade.objects.get(produto=item.produto, unidade=item.unidade)
        return item.quantidade * conv.quantidade_por_base
    except ConversaoUnidade.DoesNotExist:
        return item.quantidade  # mesmo fallback 1:1 de EntradaEstoque

def _debitar_estoque(item):
    qtd_base = _quantidade_base(item)
    Produto.objects.filter(pk=item.produto_id).update(
        quantidade_estoque=F('quantidade_estoque') - qtd_base,
    )

def _reverter_estoque(item, quantidade_devolvida):
    # usa a MESMA resolução de conversão, aplicada só à quantidade devolvida
    if item.unidade == item.produto.unidade_base:
        qtd_base = quantidade_devolvida
    else:
        try:
            conv = ConversaoUnidade.objects.get(produto=item.produto, unidade=item.unidade)
            qtd_base = quantidade_devolvida * conv.quantidade_por_base
        except ConversaoUnidade.DoesNotExist:
            qtd_base = quantidade_devolvida
    Produto.objects.filter(pk=item.produto_id).update(
        quantidade_estoque=F('quantidade_estoque') + qtd_base,
    )
```

### 6.2 `finalizar_venda` — orquestração completa

```python
# pdv/services.py
from datetime import date, timedelta
from decimal import Decimal
from django.db import connection, transaction

from financeiro.models import Conta, Receita
from pagamentos.models import NomeMetodoPagamento
from .models import PagamentoVenda, RecebivelCartao


def finalizar_venda(venda, pagamentos_payload, usuario):
    if venda.status != 'ABERTA':
        raise ValidationError({'status': 'Venda não está aberta.'})
    if venda.sessao_caixa.status != 'ABERTA':
        raise ValidationError({'sessao_caixa': 'Sessão de caixa não está aberta.'})

    itens = list(venda.itens.filter(is_active=True).select_related('produto'))
    if not itens:
        raise ValidationError({'itens': 'Venda sem itens.'})

    soma_pagamentos = sum(Decimal(str(p['valor'])) for p in pagamentos_payload)
    if soma_pagamentos != venda.valor_total:
        raise ValidationError({
            'pagamentos': f'Soma dos pagamentos (R$ {soma_pagamentos}) difere '
                           f'do total da venda (R$ {venda.valor_total}).',
        })

    with transaction.atomic():
        # ADR-020: lock por conta (sessão) + por produto, ordem crescente de id
        # (sempre a MESMA ordem entre transações concorrentes — evita deadlock)
        produto_ids = sorted({item.produto_id for item in itens})
        with connection.cursor() as cursor:
            cursor.execute(
                'SELECT pg_advisory_xact_lock(%s)', [venda.sessao_caixa.conta_id],
            )
            for pid in produto_ids:
                cursor.execute('SELECT pg_advisory_xact_lock(%s)', [pid])

        # RF-07: valida estoque de TODOS os itens antes de debitar qualquer um
        itens_sem_estoque = []
        for item in itens:
            produto = Produto.objects.select_for_update().get(pk=item.produto_id)
            qtd_base = _quantidade_base(item)
            if produto.quantidade_estoque < qtd_base:
                itens_sem_estoque.append({
                    'item_id': item.id, 'produto': produto.nome,
                    'disponivel': str(produto.quantidade_estoque),
                    'solicitado': str(qtd_base),
                })
        if itens_sem_estoque:
            raise ValidationError({'itens_sem_estoque': itens_sem_estoque})

        for item in itens:
            _debitar_estoque(item)

        for dados in pagamentos_payload:
            metodo = MetodoPagamento.objects.get(pk=dados['metodo'])
            conta = _resolver_conta(dados, metodo)  # RF-14 — Seção 6.3

            pagamento = PagamentoVenda.objects.create(
                venda=venda, metodo=metodo, valor=dados['valor'], conta=conta,
            )

            if metodo.nome == NomeMetodoPagamento.CARTAO_CREDITO:
                receita = _criar_receita_cartao(venda, pagamento, dados, usuario)
            else:
                receita = _criar_receita_a_vista(venda, pagamento, usuario)
                # signal receita_para_livro_caixa dispara sozinho no save() acima
                # (status=RECEBIDO + recebimento preenchido) — zero código novo aqui

            pagamento.receita = receita
            pagamento.save(update_fields=['receita'])

        venda.status = 'FINALIZADA'
        venda.save(update_fields=['status'])

    return venda
```

### 6.3 Resolução de conta por forma de pagamento (RF-14 / ADR-018)

```python
def _resolver_conta(dados_pagamento, metodo):
    conta_id = dados_pagamento.get('conta')
    if conta_id:
        return Conta.objects.get(pk=conta_id, is_active=True)
    if metodo.conta_padrao_id:
        return metodo.conta_padrao
    raise ValidationError({
        'conta': f'Nenhuma conta informada e {metodo.get_nome_display()} '
                 f'não tem conta_padrao configurada.',
    })
```

### 6.4 Geração de `Receita` por `PagamentoVenda` (RF-08)

```python
def _criar_receita_a_vista(venda, pagamento, usuario):
    return Receita.objects.create(
        tipo='PRODUTO',
        descricao=f'Venda {venda.numero} — {pagamento.metodo.get_nome_display()}',
        cliente=venda.cliente,
        valor_bruto=pagamento.valor,
        conta=pagamento.conta,
        status='RECEBIDO',
        recebimento=date.today(),
        criado_por=usuario,
    )
    # post_save de Receita (financeiro/signals.py) detecta status=RECEBIDO
    # + recebimento preenchido → _gerar_lancamento() cria LivroCaixa sozinho.
    # ESTE É O ÚNICO PONTO ONDE UM SIGNAL DJANGO JÁ EXISTENTE FAZ TODO O TRABALHO.
```

### 6.5 Geração de `RecebivelCartao` para pagamento CREDITO (Ponto 3)

```python
def _criar_receita_cartao(venda, pagamento, dados, usuario):
    taxa = Decimal(str(dados['taxa_percentual']))
    prazo_dias = int(dados.get('prazo_dias', 0))
    valor_bruto = pagamento.valor
    desconto = (valor_bruto * taxa / Decimal('100')).quantize(Decimal('0.01'))
    data_prevista = date.today() + timedelta(days=prazo_dias)

    receita = Receita.objects.create(
        tipo='PRODUTO',
        descricao=f'Venda {venda.numero} — Cartão de Crédito',
        cliente=venda.cliente,
        valor_bruto=valor_bruto,
        desconto=desconto,           # ADR-019: reaproveita Receita.save() —
        conta=pagamento.conta,       # valor_liquido calculado sozinho, zero campo novo
        status='PENDENTE',           # dinheiro ainda não caiu — signal NÃO dispara
        vencimento=data_prevista,
        criado_por=usuario,
    )
    RecebivelCartao.objects.create(
        pagamento=pagamento,
        receita=receita,
        taxa_percentual=taxa,
        valor_bruto=valor_bruto,
        valor_liquido_previsto=receita.valor_liquido,
        data_prevista_liquidacao=data_prevista,
        criado_por=usuario,
    )
    return receita
```

### 6.6 Liquidação via Conciliação (RF-17, `ConciliacaoViewSet.confirmar_item` estendida)

```python
# financeiro/views.py — dentro de confirmar_item(), ANTES do fluxo atual:
recebivel_id = request.data.get('recebivel_cartao_id')
if recebivel_id:
    from pdv.models import RecebivelCartao
    recebivel = get_object_or_404(RecebivelCartao, pk=recebivel_id, status='PREVISTO')
    receita = recebivel.receita
    receita.status = 'RECEBIDO'
    receita.recebimento = item.data_banco
    receita.save(update_fields=['status', 'recebimento'])
    # signal receita_para_livro_caixa dispara sozinho — cria LivroCaixa ENTRADA

    lancamento = LivroCaixa.objects.filter(origem='RECEITA', origem_id=receita.id).first()
    item.lancamento_lc = lancamento
    item.confirmado = True
    item.save(update_fields=['lancamento_lc', 'confirmado'])

    recebivel.status = 'LIQUIDADO'
    recebivel.data_liquidacao = item.data_banco
    recebivel.save(update_fields=['status', 'data_liquidacao'])
    # ... segue fluxo comum de atualizar divergencias/status da conciliacao
    return Response({'ok': True, ...})
# else: fluxo MANUAL atual, inalterado
```
**Não fazer:** criar mecanismo de conciliação paralelo — este é o **único**
ponto de código tocado em `confirmar_item`, tudo antes disso permanece igual
(ADR-019).

### 6.7 Estorno de item (`devolver_item`, RF-13) e cancelamento (`cancelar_venda`, RF-12)

```python
# pdv/services.py
from financeiro.services import estornar_receita  # NOVO — Seção 6.8

def devolver_item(item, quantidade, motivo, pagamento_id, usuario):
    if quantidade <= 0 or quantidade > (item.quantidade - item.quantidade_estornada):
        raise ValidationError({'quantidade': 'Quantidade inválida para devolução.'})

    pagamento = get_object_or_404(PagamentoVenda, pk=pagamento_id, venda=item.venda)
    if not pagamento.receita_id:
        raise ValidationError({'pagamento_id': 'Pagamento sem receita associada.'})

    valor_proporcional = (quantidade / item.quantidade) * item.valor_total

    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute(
                'SELECT pg_advisory_xact_lock(%s)', [pagamento.conta_id],
            )
        _reverter_estoque(item, quantidade)
        estornar_receita(
            receita=pagamento.receita, valor=valor_proporcional, motivo=motivo,
            item_venda=item, usuario=usuario,
        )
        item.quantidade_estornada += quantidade
        item.save(update_fields=['quantidade_estornada'])
        item.venda.valor_total = models.F('valor_total') - valor_proporcional
        item.venda.save(update_fields=['valor_total'])


def cancelar_venda(venda, motivo, usuario):
    if venda.status not in ('ABERTA', 'FINALIZADA'):
        raise ValidationError({'status': 'Venda já cancelada.'})

    with transaction.atomic():
        itens = list(venda.itens.filter(is_active=True))
        produto_ids = sorted({i.produto_id for i in itens})
        with connection.cursor() as cursor:
            cursor.execute(
                'SELECT pg_advisory_xact_lock(%s)', [venda.sessao_caixa.conta_id],
            )
            for pid in produto_ids:
                cursor.execute('SELECT pg_advisory_xact_lock(%s)', [pid])

        for item in itens:
            restante = item.quantidade - item.quantidade_estornada
            if restante > 0:
                _reverter_estoque(item, restante)

        for pagamento in venda.pagamentos.filter(receita__isnull=False):
            saldo = pagamento.receita.saldo_disponivel
            if saldo > 0:
                estornar_receita(
                    receita=pagamento.receita, valor=saldo,
                    motivo=f'Cancelamento venda {venda.numero}: {motivo}',
                    usuario=usuario,
                )

        venda.status = 'CANCELADA'
        venda.cancelada_em = timezone.now()
        venda.motivo_cancelamento = motivo
        venda.save(update_fields=['status', 'cancelada_em', 'motivo_cancelamento'])
```

### 6.8 `estornar_receita` — compartilhada entre `financeiro` e `pdv`

```python
# financeiro/services.py — NOVO ARQUIVO (mesmo padrão de conciliacao_service.py)
from django.db import connection, transaction
from .models import EstornoReceita, LivroCaixa
from .signals import _reconstruir_cadeia

def estornar_receita(receita, valor, motivo, data_estorno=None, item_venda=None, usuario=None):
    if receita.status != 'RECEBIDO':
        raise ValidationError({'receita': 'Somente receitas RECEBIDO podem ser estornadas.'})
    if not motivo or not motivo.strip():
        raise ValidationError({'motivo': 'Motivo do estorno é obrigatório.'})  # RN-05
    saldo = receita.saldo_disponivel
    if valor <= 0 or valor > saldo:
        raise ValidationError({'valor': f'Valor deve ser > 0 e <= saldo disponível (R$ {saldo}).'})  # RN-04

    data_estorno = data_estorno or date.today()
    conta = receita.conta

    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute('SELECT pg_advisory_xact_lock(%s)', [conta.id])

        estorno = EstornoReceita.objects.create(
            receita=receita, valor=valor, motivo=motivo,
            data_estorno=data_estorno, item_venda=item_venda, criado_por=usuario,
        )

        lancamento_original = (
            LivroCaixa.objects.select_for_update()
            .filter(origem='RECEITA', origem_id=receita.id, estornado=False)
            .first()
        )
        esgota_saldo = (saldo - valor) <= 0

        LivroCaixa.objects.create(
            conta=conta, tipo='SAIDA', origem='ESTORNO', origem_id=receita.id,
            descricao=f'Estorno receita: {receita.descricao} — {motivo}',
            valor=valor, data=data_estorno,
            saldo_anterior=Decimal('0'), saldo_atual=Decimal('0'),
            criado_por=usuario,
            estorno_de=lancamento_original if esgota_saldo else None,
            estornado=True,
        )
        # ADR-007 (estorno em par): só marca o ORIGINAL como estornado=True
        # quando o estorno ESGOTA o saldo — estorno parcial reduz, não anula.
        if esgota_saldo and lancamento_original:
            lancamento_original.estornado = True
            lancamento_original.save(update_fields=['estornado'])

        receita.estornado = esgota_saldo
        receita.data_estorno = data_estorno
        receita.motivo_estorno = motivo
        receita.save(update_fields=['estornado', 'data_estorno', 'motivo_estorno'])

        _reconstruir_cadeia(conta)

    return estorno
```
`ReceitaViewSet.estornar` (action `IsAdmin`, mesma permissão de
`estornar_despesa`) é uma casca fina que chama esta função com os dados do
`request.data` — reuso real, não duplicação, entre o endpoint financeiro e o
fluxo interno do PDV (`devolver_item`/`cancelar_venda`).

### 6.9 `calcular_dre_mes` — ajuste obrigatório (ADR-017, achado A2)

```python
# financeiro/relatorios.py — calcular_dre_mes(), adicionar:
from .models import EstornoReceita

estornos_do_mes_original = EstornoReceita.objects.filter(
    receita__recebimento__year=ano, receita__recebimento__month=mes,
    receita__is_active=True,
).aggregate(v=Sum('valor'))['v'] or Decimal('0')

# subtrair de receita_operacional OU receita_bruta conforme o tipo da receita
# estornada (Receita.tipo != RECEITA_FINANCEIRA -> operacional; senão financeira)
# — replicar o mesmo padrão de exclude(tipo='RECEITA_FINANCEIRA') já usado
# duas linhas acima no mesmo método, para não quebrar a separação existente.
```
**Critério de aceite do Sentinel (RF-13/item 7 do roteiro):** devolver um item
de uma venda de um mês fechado deve reduzir `receita_operacional`/`receita_bruta`
**daquele mês**, mesmo que a consulta seja feita hoje — não criar linha
separada no mês do estorno (Opção 2 rejeitada, ver ADR-017).

---

## 7. Permissões (RF-16/Seção 11 da spec)

Sem sistema de perfis novo — reaproveita `IsAdmin`/`IsAuthenticated` já
existentes (`common/permissions.py`), confirmado no achado A5.

| Ação | Permissão |
|---|---|
| Abrir/vender/sangria/suprimento/fechar caixa, devolver item | `IsAuthenticated` |
| `ReceitaViewSet.estornar` | `IsAdmin` (mesmo padrão de `estornar_despesa`) |
| `SessaoCaixaViewSet.list` completo (todas as sessões, não só as próprias) | `IsAdmin` — implementado via `get_queryset()` condicional, não `permission_classes` fixo (operador comum ainda precisa `GET` da própria sessão) |

---

## 8. Plano de Execução por Fase

### Fase 1 — Backend (Forge)

- [ ] Ler os 21 ADRs (`ADRs.md`) — 14 existentes + 7 novos (ADR-015 a ADR-021) — **bloqueante**
- [ ] `pagamentos`: migration `MetodoPagamento.conta_padrao` + `taxa_percentual_padrao`
- [ ] App `pdv`: `apps.py`, registrar em `LOCAL_APPS` (settings.py) e `core/urls.py`
- [ ] `pdv/models.py`: `SessaoCaixa`, `MovimentoCaixa`, `Venda`, `ItemVenda`, `PagamentoVenda`, `RecebivelCartao` → `makemigrations pdv`
- [ ] `financeiro/models.py`: 3 campos + properties em `Receita`, model `EstornoReceita` → `makemigrations financeiro` (depende do model `pdv.ItemVenda` já declarado no código — gerar migration do `pdv` primeiro)
- [ ] `financeiro/services.py` (novo arquivo): `estornar_receita()`
- [ ] `financeiro/views.py`: `ReceitaViewSet.estornar` (action `IsAdmin`); `ConciliacaoViewSet.confirmar_item` estendida; nova action/endpoint `recebiveis-sugeridos` (RF-17, Should)
- [ ] `financeiro/serializers.py`: `EstornoReceitaSerializer`; `ReceitaSerializer` +3 campos + `saldo_disponivel`/`valor_estornado_total` read-only
- [ ] `financeiro/relatorios.py`: `calcular_dre_mes` abate `EstornoReceita` (ADR-017)
- [ ] `financeiro/urls.py`: `+estornos-receita/` (GET only)
- [ ] `pdv/services.py`: `abrir_sessao`, `fechar_sessao`, `finalizar_venda`, `cancelar_venda`, `devolver_item` (Seção 6, completo)
- [ ] `pdv/serializers.py`, `pdv/views.py`, `pdv/urls.py` conforme contrato (Seção 4)
- [ ] Testes: 100% dos RF Must (Seção 7 da spec) + roteiro completo de 12 itens do Sentinel (Seção 14 da spec) — 0 falhas, sem `@skip`/`@xfail`

### Fase 2 — Frontend (Loom, paralelo após contrato de API travado)

- [ ] `pages/pdv/AberturaCaixa.jsx` — Tela 1
- [ ] `pages/pdv/FrenteDeCaixa.jsx` + `SplitPagamento.jsx` + `CarrinhoItem.jsx` — Tela 2 (barra fixa mobile — único padrão genuinamente novo)
- [ ] `components/ModalSangriaSuprimento.jsx` — Tela 3
- [ ] `pages/pdv/FechamentoCaixa.jsx` + `ResumoSessao.jsx` — Tela 4
- [ ] `pages/pdv/HistoricoVendas.jsx` — Tela 5 (padrão dual Conciliacao.jsx/Financeiro.jsx)
- [ ] `pages/pdv/RelatorioSessoes.jsx` — Tela 6 (`IsAdmin`, reaproveita `ResumoSessao.jsx`)
- [ ] Tela 7 (Should) via `ResourceCrud.jsx` apontando para `pagamentos/metodos/` — sem componente novo
- [ ] `routes/index.jsx`: 6 rotas + guard de sessão aberta (redirect `/pdv/abertura`)
- [ ] `Sidebar.jsx`: item "PDV" entre Vendas e Financeiro
- [ ] Badges/ícones conforme `Especificacao_UI_Hotfix.md` (mapas já prontos, copiar 1:1)
- [ ] `response.data.results` em toda listagem paginada — regra global

### Fase 3 — QA (Sentinel)

- [ ] Roteiro de 12 itens da Seção 14 da spec, ponta a ponta
- [ ] Confirmar RF-13/item 7: DRE do mês reflete estorno de receita corretamente (ADR-017)
- [ ] Confirmar lock por produto (ADR-020): teste de concorrência de 2 vendas simultâneas no mesmo produto
- [ ] Confirmar `RecebivelCartao`: nenhum `LivroCaixa` nasce antes da liquidação (Ponto 3, item 4)

### Fase 4 — Deploy (Pilot)

- [ ] Migrations aplicadas: `pagamentos`, `pdv`, `financeiro` (nessa ordem de geração)
- [ ] `git push origin main` → CI/CD → confirmar timestamp do container pós-deploy
- [ ] Atualizar `CLAUDE.md` do projeto (histórico de execuções, padrão já em uso)

---

## 9. Armadilhas Específicas Desta Manutenção (além das globais do CLAUDE.md)

```
❌ NUNCA debitar estoque via signal post_save de ItemVenda — precisa abortar
   ANTES de persistir se estoque insuficiente (RF-07). Use services.finalizar_venda.
❌ NUNCA criar LivroCaixa manualmente para pagamento em Cartão de Crédito na
   finalização — Receita nasce PENDENTE, o signal existente cuida disso na
   liquidação via conciliação (ADR-019).
❌ NUNCA marcar EstornoReceita.receita.estornado=True em estorno PARCIAL — só
   quando o estorno ESGOTA saldo_disponivel (RN-04, ADR-016).
❌ NUNCA aceitar valor_unitario do payload de POST itens/ — sempre resolvido de
   Produto.preco_venda no backend (RN-03, snapshot imutável).
❌ NUNCA lockar produtos em ordem de inserção do carrinho — sempre id crescente
   (ADR-020), senão duas vendas concorrentes com itens em ordem diferente
   podem deadlockar.
❌ NUNCA esquecer o filtro is_active=True em EstornoReceita.objects.filter ao
   contar valor_estornado_total se algum dia soft-delete for exposto nela —
   por ora ViewSet não expõe DELETE (RNF-05), mas o property deve ser defensivo.
```

---

## Passagem de bastão

```
✅ Arquitetura definida — Módulo PDV (UidCore, Manutenção #15)

Entregáveis:
- Blueprint_PDV.md (este arquivo) + 7 ADRs novos em ADRs.md (ADR-015 a ADR-021)
- 1 app novo (pdv, 6 models) + alterações em financeiro (2 campos+1 model) e
  pagamentos (2 campos)
- 15 endpoints REST novos/alterados
- 3 decisões de arquitetura pendentes RESOLVIDAS (app pdv, DRE, mapeamento conta)
- Plano de execução em 4 fases

➡️  Forge executa Fase 1 — Backend
➡️  Loom executa Fase 2 — Frontend (paralelo, após contrato de API travado)
➡️  Sentinel executa Fase 3 — 0 falhas obrigatório, roteiro de 12 itens da spec
➡️  Pilot executa Fase 4 — somente após Sentinel = APROVADO
```
