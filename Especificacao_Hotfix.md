# Especificacao_Hotfix — Manutencao #9 — UidCore
**Data:** 2026-07-29
**Sistema:** UidCore — Template Financeiro Multi-Nicho
**Origem:** Divergencias encontradas na Manutencao #8 (Fluxo 1 retroativo)
**Agente produtor:** Analista

---

## Escopo desta manutencao

### Incluido
- DIV01: app `conciliacao` fantasma — verificado, nao existe no disco nem em INSTALLED_APPS; nenhuma acao necessaria
- DIV02: integrar Dashboard.jsx com endpoint real `GET /api/v1/financeiro/dashboard/`
- DIV04: padronizar `AcessoPortalCliente`, `Agenda` e `PadraoSeguroConciliacao` para herdar `BaseModel`
- DIV05: remover campo `ativo` duplicado de `MetodoPagamento` (ja herda `BaseModel`)
- DIV07: padronizar todos os serializers com `id = serializers.IntegerField(source='pk', read_only=True)`
- DIV08: padronizar `HistoricoCliente` e `ItemConciliacao` para herdar `BaseModel`
- DIV-UI01: adicionar fontes Plus Jakarta Sans e DM Sans ao projeto React
- DIV-UI02: remover `overflow-hidden` do div root do `AppLayout`
- DIV-UI04: lucide-react ja presente no package.json — verificado, nenhuma acao

### Suspenso (NAO implementar)
- DIV03: Portal sem telas para perfil CLIENTE — feature nova, fora do escopo
- DIV10: Endpoint de listagem de usuarios ausente — feature nova, fora do escopo
- DIV-UI03: Emojis na Sidebar — padrao intencional, nao alterar

---

## Requisitos Funcionais — Backend

### RF-B01 — Verificar e registrar DIV01
**Status verificado:** pasta `/var/www/uidcore/backend/conciliacao/` nao existe no disco.
`'conciliacao'` nao aparece em `INSTALLED_APPS` em `core/settings.py`.
**Acao:** nenhuma alteracao de codigo. DIV01 resolvida de fato. Registrar no relatorio Sentinel.

---

### RF-B02 — Padronizar AcessoPortalCliente para herdar BaseModel
**App:** `portal`
**Arquivo:** `backend/portal/models.py`

Estado atual:
```python
class AcessoPortalCliente(models.Model):
    ativo         = models.BooleanField(default=True)
    ultimo_acesso = models.DateTimeField(null=True, blank=True)
    criado_em     = models.DateTimeField(auto_now_add=True)
```

Estado desejado:
```python
from common.models import BaseModel

class AcessoPortalCliente(BaseModel):
    ultimo_acesso = models.DateTimeField(null=True, blank=True)
    # remover: ativo (substituido por is_active do BaseModel)
    # remover: criado_em (substituido por created_at do BaseModel)
```

**Migration:** `portal/migrations/0003_portal_basemodel.py`

Regras de negocio:
- RN-B01: dados de `ativo` migrados para `is_active` via RunPython antes de remover a coluna
- RN-B02: dados de `criado_em` migrados para `created_at` via RunPython antes de remover a coluna

---

### RF-B03 — Remover campo ativo duplicado de Agenda
**App:** `agendamento`
**Arquivo:** `backend/agendamento/models.py`

Estado atual:
```python
class Agenda(BaseModel):        # ja herda BaseModel
    ...
    ativo = models.BooleanField(default=True)  # DUPLICADO
```

Estado desejado:
```python
class Agenda(BaseModel):
    ...
    # ativo removido — usar is_active herdado
```

**Migration:** `agendamento/migrations/0003_agenda_remove_ativo.py`

Regras de negocio:
- RN-B03: dados de `ativo` migrados para `is_active` via RunPython antes de remover
- RN-B04: filtros em views/serializers que usavam `.filter(ativo=True)` atualizados para `.filter(is_active=True)`

---

### RF-B04 — Padronizar PadraoSeguroConciliacao para herdar BaseModel
**App:** `financeiro`
**Arquivo:** `backend/financeiro/models.py` (linha 314)

Estado atual:
```python
class PadraoSeguroConciliacao(models.Model):
    ...
    ativo     = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    criado_por = models.ForeignKey(...)
```

Estado desejado:
```python
class PadraoSeguroConciliacao(BaseModel):
    ...
    # remover: ativo (substituido por is_active)
    # remover: criado_em (substituido por created_at)
    # manter: criado_por (especifico, nao existe em BaseModel)
```

**Migration:** `financeiro/migrations/0004_financeiro_basemodel.py` (cobre tambem RF-B07)

Regras de negocio:
- RN-B05: dados de `ativo` migrados para `is_active`; dados de `criado_em` migrados para `created_at`
- RN-B06: `PadraoSeguroConciliacaoSerializer` atualizado — remover `ativo` e `criado_em`, substituir por `is_active` e `created_at`

---

### RF-B05 — Remover campo ativo duplicado de MetodoPagamento
**App:** `pagamentos`
**Arquivo:** `backend/pagamentos/models.py` (linha 16-21)

Estado atual:
```python
class MetodoPagamento(BaseModel):  # ja herda BaseModel
    nome = models.CharField(...)
    ativo = models.BooleanField(default=True)  # DUPLICADO
```

Estado desejado:
```python
class MetodoPagamento(BaseModel):
    nome = models.CharField(...)
    # ativo removido — usar is_active herdado
```

**Migration:** `pagamentos/migrations/0003_metodo_pagamento_remove_ativo.py`

Regras de negocio:
- RN-B07: dados de `ativo` migrados para `is_active` antes de remover
- RN-B08: `MetodoPagamentoSerializer` atualizado — remover `ativo` se presente, confirmar `is_active` exposto

---

### RF-B06 — Padronizar HistoricoCliente para herdar BaseModel
**App:** `clientes`
**Arquivo:** `backend/clientes/models.py` (linha 38)

Estado atual:
```python
class HistoricoCliente(models.Model):
    cliente   = models.ForeignKey(Cliente, ...)
    descricao = models.TextField()
    data      = models.DateTimeField(auto_now_add=True)  # sem is_active, sem updated_at
```

Estado desejado:
```python
class HistoricoCliente(BaseModel):
    cliente   = models.ForeignKey(Cliente, ...)
    descricao = models.TextField()
    # remover: data (substituido por created_at herdado)
```

**Migration:** `clientes/migrations/0003_historico_cliente_basemodel.py`

Regras de negocio:
- RN-B09: dados de `data` migrados para `created_at` via RunPython
- RN-B10: `HistoricoClienteSerializer` atualizado — trocar `data` por `created_at`; adicionar `id = IntegerField(source='pk', read_only=True)` como primeiro campo
- RN-B11: `ordering` do model atualizado de `-data` para `-created_at`

---

### RF-B07 — Padronizar ItemConciliacao para herdar BaseModel
**App:** `financeiro`
**Arquivo:** `backend/financeiro/models.py` (linha 286)

Estado atual:
```python
class ItemConciliacao(models.Model):   # sem is_active, created_at, updated_at
    conciliacao = models.ForeignKey(ConciliacaoExtrato, ...)
    data_banco  = models.DateField()
    ...
    confirmado  = models.BooleanField(default=False)
```

Estado desejado:
```python
class ItemConciliacao(BaseModel):      # is_active, created_at, updated_at herdados
    conciliacao = models.ForeignKey(ConciliacaoExtrato, ...)
    data_banco  = models.DateField()
    ...
    confirmado  = models.BooleanField(default=False)
```

**Migration:** parte de `financeiro/migrations/0004_financeiro_basemodel.py` (mesmo arquivo do RF-B04)

Regras de negocio:
- RN-B12: `ItemConciliacaoSerializer` atualizado — adicionar `is_active` e `created_at` nos fields para consistencia

---

### RF-B08 — Padronizar serializers com IntegerField(source='pk')
**Regra Uid obrigatoria:**
```python
class MinhaSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='pk', read_only=True)  # PRIMEIRO campo
    ...
    class Meta:
        read_only_fields = ['created_at', ...]  # id NAO entra aqui
```

**Serializers afetados — identificados por auditoria (ausencia de IntegerField):**

| Arquivo | Serializer |
|---|---|
| `clientes/serializers.py` | `HistoricoClienteSerializer` |
| `clientes/serializers.py` | `ClienteSerializer` |
| `financeiro/serializers.py` | `CategoriaSerializer` |
| `financeiro/serializers.py` | `ContaSerializer` |
| `financeiro/serializers.py` | `AporteSerializer` |
| `financeiro/serializers.py` | `ReceitaSerializer` |
| `financeiro/serializers.py` | `DespesaSerializer` |
| `financeiro/serializers.py` | `LivroCaixaSerializer` |
| `fornecedores/serializers.py` | `FornecedorSerializer` |

**Ja conformes (nao alterar):**
`administrativo`, `agendamento`, `pagamentos`, `rh`, `vendas`, `portal`,
`financeiro` (ConciliacaoExtratoSerializer, ItemConciliacaoSerializer, PadraoSeguroConciliacaoSerializer)

Regras de negocio:
- RN-B13: `id = IntegerField(source='pk', read_only=True)` como PRIMEIRO campo declarado na classe
- RN-B14: `id` NAO aparece em `read_only_fields` quando ja declarado explicitamente
- RN-B15: nenhuma migration necessaria — alteracao apenas de serializer

---

## Contrato JSON — Endpoint Dashboard

**Endpoint:** `GET /api/v1/financeiro/dashboard/`
**Autenticacao:** JWT Bearer (IsAuthenticated)
**Parametros:** nenhum

**Response 200 OK (campos e tipos):**
```json
{
  "receita_mes": "5000.00",
  "despesa_mes": "2300.00",
  "resultado_mes": "2700.00",
  "saldo_total_contas": "12450.00",
  "mrr": "3500.00",
  "receitas_vencer": [
    {
      "id": 42,
      "descricao": "Mensalidade Studio Fluir",
      "valor_liquido": "1200.00",
      "vencimento": "2026-08-05",
      "cliente__nome_razao_social": "Studio Fluir Ltda"
    }
  ],
  "despesas_vencer": [
    {
      "id": 17,
      "descricao": "Aluguel sala",
      "valor_liquido": "800.00",
      "vencimento": "2026-08-10",
      "fornecedor": "Imobiliaria ABC"
    }
  ],
  "grafico_6_meses": [
    {
      "mes": "2026-02",
      "label": "Fev",
      "receita": "4200.00",
      "despesa": "1900.00",
      "resultado": "2300.00"
    }
  ],
  "receitas_atrasadas": 3,
  "despesas_atrasadas": 1,
  "indicadores": {},
  "balanco_resumo": {
    "pl_total": "9000.00",
    "ativo_total": "15000.00",
    "passivo_total": "6000.00"
  }
}
```

**Notas para o Loom:**
- Valores monetarios chegam como string decimal — usar `parseFloat()` antes de formatar
- `receitas_vencer` / `despesas_vencer`: ate 8 itens, ordenados por `vencimento` ASC
- `grafico_6_meses`: 6 objetos, indice 0 = 5 meses atras, indice 5 = mes atual
- `indicadores`: pode vir vazio `{}` — renderizar gracefully
- `receitas_atrasadas` e `despesas_atrasadas`: inteiros (count)
- Endpoint sem dados retorna campos zerados, nao 404

---

## Requisitos Funcionais — Frontend

### RF-F01 — Adicionar fontes Uid ao projeto React
**Arquivos:** `frontend/index.html`, `frontend/tailwind.config.js`, `frontend/src/index.css`

Em `frontend/index.html` (dentro de `<head>`, antes de `</head>`):
```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:ital,wght@0,200..800;1,200..800&family=DM+Sans:ital,opsz,wght@0,9..40,100..1000;1,9..40,100..1000&display=swap" rel="stylesheet">
```

Em `frontend/tailwind.config.js` (dentro de `theme.extend`):
```js
fontFamily: {
  sans: ['Plus Jakarta Sans', 'sans-serif'],
  body: ['DM Sans', 'sans-serif'],
},
```

Em `frontend/src/index.css` (apos as diretivas `@tailwind`):
```css
body {
  font-family: 'Plus Jakarta Sans', sans-serif;
}
```

Regras de negocio:
- RN-F01: Plus Jakarta Sans = fonte primaria = `font-sans` no Tailwind = padrao do body
- RN-F02: DM Sans = fonte secundaria = `font-body` no Tailwind = textos de apoio/labels
- RN-F03: `display=swap` obrigatorio no link do Google Fonts
- RN-F04: `preconnect` para `fonts.googleapis.com` e `fonts.gstatic.com` obrigatorio

---

### RF-F02 — Remover overflow-hidden do root do AppLayout
**Arquivo:** `frontend/src/components/layout/AppLayout.jsx`

Linha 11 — estado atual:
```jsx
<div className="flex h-screen bg-gray-50 overflow-hidden">
```

Linha 11 — estado desejado:
```jsx
<div className="flex h-screen bg-gray-50">
```

Regra global Uid violada: `Overflow-hidden NUNCA no SistemaLayout root`

Regras de negocio:
- RN-F05: remover apenas `overflow-hidden` do div root — nenhuma outra alteracao no componente
- RN-F06: `<main className="flex-1 overflow-y-auto p-6">` (linha 34) DEVE ser mantido intocado
- RN-F07: validar sem regressao visual em modais e dropdowns apos remocao

---

### RF-F03 — Integrar Dashboard.jsx com endpoint real
**Arquivo:** `frontend/src/pages/Dashboard.jsx`

Estado atual: 4 cards hard-coded com `'R$ -'`.
Estado desejado: busca dados de `GET /api/v1/financeiro/dashboard/` na montagem.

**Cards — 4 metricas principais:**

| Card | Campo da API | Label |
|---|---|---|
| Receitas do Mes | `receita_mes` | formatCurrency |
| Despesas do Mes | `despesa_mes` | formatCurrency |
| Saldo Atual | `saldo_total_contas` | formatCurrency |
| MRR | `mrr` | formatCurrency (substitui "Agendamentos Hoje" do mock) |

Funcao de formatacao:
```js
function formatCurrency(value) {
  return parseFloat(value).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
}
```

**Alertas (exibir se valor > 0):**
- `receitas_atrasadas`: badge "X receita(s) atrasada(s)"
- `despesas_atrasadas`: badge "X despesa(s) atrasada(s)"

**Grafico 6 meses (sem biblioteca externa):**
- Tabela/lista com 6 linhas: label do mes, receita, despesa, resultado
- Resultado positivo: texto verde; negativo: texto vermelho

**Cards de listas (substituem os dois cards de mock):**
- "Receitas a Vencer (30 dias)": lista de `receitas_vencer` — descricao, valor, vencimento, cliente
- "Despesas a Vencer (30 dias)": lista de `despesas_vencer` — descricao, valor, vencimento, fornecedor
- Se array vazio: "Nenhum item nos proximos 30 dias"

Regras de negocio:
- RN-F08: usar cliente axios existente no projeto, nao criar nova instancia
- RN-F09: JWT via interceptor/cliente ja configurado no projeto
- RN-F10: sem bibliotecas de grafico externas (recharts, chart.js etc. nao estao no projeto)
- RN-F11: estado de loading visivel (nao mostrar '0' ou null enquanto carrega)
- RN-F12: erro de fetch: mensagem amigavel, sem crash

---

### RF-F04 — Verificar lucide-react (DIV-UI04)
`"lucide-react": "^1.27.0"` confirmado em `dependencies` do `package.json`.
Nenhuma acao necessaria. Registrar como verificado.

---

## Resumo de migrations

| App | Arquivo | Motivo |
|---|---|---|
| `portal` | `0003_portal_basemodel.py` | AcessoPortalCliente para BaseModel; remover ativo, criado_em |
| `agendamento` | `0003_agenda_remove_ativo.py` | Agenda: remover campo ativo duplicado |
| `financeiro` | `0004_financeiro_basemodel.py` | PadraoSeguroConciliacao + ItemConciliacao para BaseModel |
| `clientes` | `0003_historico_cliente_basemodel.py` | HistoricoCliente para BaseModel; remover campo data |
| `pagamentos` | `0003_metodo_pagamento_remove_ativo.py` | MetodoPagamento: remover campo ativo duplicado |

Total: 5 migrations.

Padrao obrigatorio para migrations com remocao de coluna com dados:
```python
def migrar_ativo_para_is_active(apps, schema_editor):
    Model = apps.get_model('app_name', 'ModelName')
    Model.objects.filter(ativo=True).update(is_active=True)
    Model.objects.filter(ativo=False).update(is_active=False)

operations = [
    migrations.RunPython(migrar_ativo_para_is_active, migrations.RunPython.noop),
    migrations.RemoveField(model_name='modelname', name='ativo'),
]
```

---

## Criterios de Aceite

### Backend
- [ ] CA-B01: `AcessoPortalCliente` herda `BaseModel`; `ativo` e `criado_em` removidos; dados migrados
- [ ] CA-B02: `Agenda` sem campo `ativo` proprio; filtros usam `is_active`
- [ ] CA-B03: `PadraoSeguroConciliacao` herda `BaseModel`; `ativo` e `criado_em` removidos; dados migrados
- [ ] CA-B04: `MetodoPagamento` sem campo `ativo` proprio; `is_active` herdado assume
- [ ] CA-B05: `HistoricoCliente` herda `BaseModel`; campo `data` removido; dados em `created_at`
- [ ] CA-B06: `ItemConciliacao` herda `BaseModel`; `created_at`, `updated_at`, `is_active` no schema
- [ ] CA-B07: 9 serializers com `id = IntegerField(source='pk', read_only=True)` como primeiro campo
- [ ] CA-B08: `id` ausente de `read_only_fields` nos serializers corrigidos
- [ ] CA-B09: `python manage.py makemigrations --check` sem novas migrations apos as 5 aplicadas
- [ ] CA-B10: `python manage.py migrate` sem erro em banco limpo e com dados
- [ ] CA-B11: `GET /api/v1/financeiro/dashboard/` retorna 200 com todos os campos do contrato (sem alteracao de backend necessaria)
- [ ] CA-B12: DIV01 confirmada — `conciliacao` ausente de INSTALLED_APPS e do disco

### Frontend
- [ ] CA-F01: Plus Jakarta Sans aplicada no body (verificavel em DevTools > Computed)
- [ ] CA-F02: DM Sans disponivel via `font-body` no Tailwind
- [ ] CA-F03: `AppLayout.jsx` div root sem `overflow-hidden`
- [ ] CA-F04: scroll de pagina funciona normalmente; `overflow-y-auto` em `<main>` mantido
- [ ] CA-F05: Dashboard exibe valores reais apos autenticacao
- [ ] CA-F06: Dashboard com loading visivel durante fetch
- [ ] CA-F07: Dashboard com mensagem de erro graceful
- [ ] CA-F08: cards "Receitas a Vencer" e "Despesas a Vencer" substituem cards de mock
- [ ] CA-F09: grafico 6 meses com 6 linhas, resultado colorido
- [ ] CA-F10: alertas de atrasados aparecem quando > 0
- [ ] CA-F11: lucide-react confirmado — nenhuma acao necessaria

---

## Ordem de execucao recomendada

**Forge:**
1. RF-B02, RF-B03, RF-B04, RF-B05 em paralelo (migrations por app, sem dependencias cruzadas)
2. RF-B06, RF-B07 em paralelo
3. RF-B08 (serializers, sem migration, pode rodar em paralelo com migrations)
4. RF-B01 (apenas registrar verificacao)

**Loom:**
1. RF-F01 (fontes — independente)
2. RF-F02 (overflow-hidden — 1 linha, independente)
3. RF-F03 (Dashboard — depende do contrato JSON, nao das migrations)
4. RF-F04 (registrar verificacao)

---

## Notas tecnicas

**HistoricoClienteSerializer pos-RF-B06:**
```python
class HistoricoClienteSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='pk', read_only=True)

    class Meta:
        model = HistoricoCliente
        fields = ['id', 'descricao', 'created_at']
        read_only_fields = ['created_at']
```

**AppLayout pos-RF-F02:**
O `h-screen` no root deve ser mantido. O `overflow-y-auto` no `<main>` cuida do scroll da area de conteudo. A remocao do `overflow-hidden` do root nao causa scroll duplo.

**Dashboard fetch (RF-F03):**
Verificar instancia axios em `src/api/` ou `src/services/` antes de criar nova. Usar instancia existente com interceptor JWT ja configurado.
