# ADRs — Decisoes de Arquitetura UidCore
**Sistema:** UidCore — Template Financeiro Multi-Nicho
**Versao:** AS-IS (documentado a partir do codigo em producao)
**Data:** 2026-07-28
**Autor:** Blueprint (arquiteto de software)
**Referencia:** ArquiteturaTecnica#2 / Blueprint.md

---

## ADR-001: Stack Backend

**Status:** Accepted
**Data:** 2026-07-28

### Contexto

O UidCore precisa de um backend robusto, com suporte a ORM maduro, autenticacao JWT,
filtros/paginacao e capacidade de extensao por nicho sem reescritas.

### Decisao

Python 3.12 + Django 5.x + Django REST Framework + SimpleJWT + django-filter + python-decouple.

```
AUTH_USER_MODEL = 'accounts.User'
LANGUAGE_CODE   = 'pt-br'
TIME_ZONE       = 'America/Sao_Paulo'
```

### Consequencias

Facilita: ecosystem maduro, admin Django gratuito, migrações rastreáveis, ORM expressivo.
Compromete: performance em endpoints de alta concorrência (nao e caso de uso do UidCore).

### Alternativas descartadas

FastAPI: menos convencoes, sem admin nativo, requer mais boilerplate para CRUD.
Node.js/NestJS: curva de aprendizado para o time que domina Python.

---

## ADR-002: Stack Frontend

**Status:** Accepted
**Data:** 2026-07-28

### Contexto

Frontend precisa ser SPA com autenticacao JWT, estado global persistido, queries cacheadas
e componentes reutilizaveis entre nichos.

### Decisao

React 18 + Vite + Tailwind CSS + Zustand (estado global + persist) + TanStack Query (cache HTTP).
Fontes: Plus Jakarta Sans + DM Sans (padrao Uid Software).
HTTP client: Axios com interceptor de refresh automatico.

### Consequencias

Facilita: DX rapida, build rapido via Vite, componentes compartilhaveis (ResourceCrud.jsx),
Zustand com persist elimina re-login apos F5.
Compromete: bundle size cresce com TanStack + Zustand juntos (aceitavel para sistema interno).

### Alternativas descartadas

Redux: boilerplate excessivo para o tamanho do projeto.
Context API puro: sem persist nativo, sem devtools.
SvelteKit/Next.js: overhead de SSR desnecessario para sistema SPA autenticado.

---

## ADR-003: Imutabilidade do LivroCaixa

**Status:** Accepted
**Data:** 2026-07-28

### Contexto

O LivroCaixa e o historico financeiro auditavel do sistema. Edicao ou exclusao direta de
lancamentos compromete rastreabilidade e pode tornar o historico inconsistente.

### Decisao

LivroCaixaViewSet herda ReadCreateViewSet (CreateModelMixin + ListModelMixin + RetrieveModelMixin + GenericViewSet).
PUT, PATCH, DELETE retornam 405 Method Not Allowed.
Correcoes ocorrem via estorno: POST /api/v1/financeiro/livro-caixa/{id}/estornar/ — IsAdmin only.
O estorno cria um lancamento de sentido oposto e marca AMBOS como estornado=True.

```python
class ReadCreateViewSet(CreateModelMixin, ListModelMixin, RetrieveModelMixin, GenericViewSet):
    pass
```

### Consequencias

Facilita: trilha de auditoria completa, DRE e Balanco sempre corretos,
comportamento previsivel para o CFO as a Service.
Compromete: ADMIN precisa estornar em vez de editar — 1-2 cliques extras.

### Alternativas descartadas

ModelViewSet com restricao de permissao: dependeria de permissao correta em TODOS os
endpoints — mais facil violar acidentalmente.

---

## ADR-004: Soft Delete Global via BaseModel.is_active

**Status:** Accepted
**Data:** 2026-07-28

### Contexto

Dados financeiros e cadastrais nao podem ser destruidos fisicamente — auditoria exige
historico completo, inclusive de registros "excluidos".

### Decisao

Todos os models herdam BaseModel que possui is_active = BooleanField(default=True).
Exclusao via API seta is_active=False (nunca .delete()).
Listagens filtram queryset.filter(is_active=True) por padrao em todos os ViewSets.

```python
def destroy(self, request, *args, **kwargs):
    instance = self.get_object()
    instance.is_active = False
    instance.save(update_fields=['is_active', 'updated_at'])
    return Response(status=status.HTTP_204_NO_CONTENT)
```

Excecoes documentadas:
- AcessoPortalCliente: nao herda BaseModel, usa campo ativo proprio
- Agenda: herda BaseModel mas usa campo ativo adicional (DIV04)
- PadraoSeguroConciliacao: usa campo ativo proprio (nao herda BaseModel)
- HistoricoCliente e ItemConciliacao: sem is_active por design (logs imutaveis)

### Consequencias

Facilita: historico completo, recuperacao de registros, auditoria.
Compromete: banco cresce com registros inativos; queries precisam sempre filtrar is_active=True.

### Alternativas descartadas

django-safedelete: dependencia extra; padrao proprio e mais simples e suficiente.
deleted_at (timestamp): padrao do SystemD/StudioFluir — decidido usar is_active no UidCore
por simplicidade de filtragem ORM.

---

## ADR-005: Autenticacao por Email

**Status:** Accepted
**Data:** 2026-07-28

### Contexto

Usuarios de empresas (MEI, pequenas empresas) nao se lembram de usernames.
Email e o identificador natural e unico.

### Decisao

CustomUser estende AbstractBaseUser com USERNAME_FIELD = 'email'.
UserManager customizado em accounts/managers.py.
Login via email+senha apenas — username proibido por design.

```python
AUTH_USER_MODEL = 'accounts.User'
# accounts/models.py
USERNAME_FIELD = 'email'
```

Perfis: is_staff=True = ADMIN; is_staff=False = OPERACIONAL.
Sem modelo de perfil separado — mantendo simplicidade para o template.

### Consequencias

Facilita: UX natural, sem campo extra para memorizar, email e unico por definicao.
Compromete: troca de email exige cuidado (e o campo de login).

### Alternativas descartadas

username: padrao Django mas nao intuitivo para usuarios finais de PME.
Perfil em tabela separada: desnecessario para 2 perfis simples (ADMIN/OPERACIONAL).

---

## ADR-006: Reconstrucao de Saldo por Cadeia com Advisory Lock

**Status:** Accepted
**Data:** 2026-07-28

### Contexto

O saldo de uma conta e calculado como cadeia: cada lancamento registra saldo_anterior
e saldo_atual. Insercoes retroativas ou concorrentes podem corromper a cadeia se nao
houver controle de concorrencia.

### Decisao

A cada novo lancamento no LivroCaixa, _reconstruir_cadeia(conta) e executada:
- Busca TODOS os lancamentos da conta em ordem cronologica (data, criado_em) com select_for_update()
- Recalcula saldo_anterior e saldo_atual acumulando a partir de conta.saldo_inicial
- Persiste via bulk_update(['saldo_anterior', 'saldo_atual'])

Toda operacao de escrita no LivroCaixa adquire pg_advisory_xact_lock(conta_id) antes
de criar o lancamento, garantindo exclusao mutua por conta.

```python
with transaction.atomic():
    with connection.cursor() as cursor:
        cursor.execute('SELECT pg_advisory_xact_lock(%s)', [conta.id])
    # ... criar lancamento ...
    _reconstruir_cadeia(conta)
```

_saldo_real(conta): calculo por soma agregada (SUM de entradas - SUM de saidas)
para verificacao pontual sem depender da cadeia.

### Consequencias

Facilita: saldo sempre correto mesmo com insercoes retroativas, sem race condition.
Compromete: custo O(n) por conta a cada lancamento (aceitavel para volume de MEI/PME).
Risco documentado (R04): comando reconstruir_saldo nao portado do SystemD — necessario
se insercoes retroativas acumularem.

### Alternativas descartadas

Calcular saldo somente na leitura (sem gravar na linha): mais simples mas impossibilita
mostrar saldo_anterior/saldo_atual por lancamento (necessario para extrato).
SELECT ... FOR UPDATE sem advisory lock: granularidade por linha, nao por conta —
nao garante exclusao entre insercoes na mesma conta por conexoes diferentes.

---

## ADR-007: Estorno em Par Obrigatorio

**Status:** Accepted
**Data:** 2026-07-28

### Contexto

Quando um lancamento e estornado, o registro de estorno cria um lancamento de sentido
oposto. Se apenas o lancamento de estorno for marcado como estornado=True (e nao o
original), o calculo de saldo conta o efeito duas vezes em vez de neutralizar.

### Decisao

Toda operacao de estorno — seja de Despesa ou de LivroCaixa manual — deve marcar
estornado=True em AMBOS os lancamentos: o original E o de estorno.

```python
# DespesaViewSet.estornar_despesa
lancamento = LivroCaixa.objects.create(..., estornado=True, estorno_de=lancamento_original)
if lancamento_original:
    lancamento_original.estornado = True
    lancamento_original.save(update_fields=['estornado'])
```

O LivroCaixa.estorno_de (FK self nullable) referencia o lancamento original.
Lancamentos com estornado=True sao excluidos dos calculos de saldo e relatorios
(_reconstruir_cadeia os inclui na reconstrucao da posicao, mas DRE/Balanco nao os soma).

### Consequencias

Facilita: neutralizacao correta do efeito, sem duplicidade no DRE.
Compromete: logica de estorno precisa sempre atualizar DOIS registros — nao pode
ser simplificada para um unico update.

### Alternativas descartadas

Excluir fisicamente o lancamento original: violaria imutabilidade do LivroCaixa (ADR-003).
Marcar apenas o estorno como estornado: bug real ja corrigido — causa duplicidade no saldo.

---

## ADR-008: Cartao de Credito como Conta Propria (tipo=CARTEIRA)

**Status:** Accepted
**Data:** 2026-07-28

### Contexto

O cartao de credito nao e uma forma de pagamento — e um instrumento financeiro com
saldo proprio. Lancar compras diretamente na conta bancaria e pagar a fatura depois
resulta em dupla contagem: a despesa entra duas vezes (no lancamento da compra E no
pagamento da fatura).

### Decisao

Cartao de credito deve ser modelado como uma Conta com tipo=CARTEIRA.
Compras no cartao: lancadas nessa conta (aumentam o saldo devedor do cartao).
Pagamento da fatura: transferencia entre contas (banco -> cartao), nao uma Despesa nova.

Variacao para cartao com garantia CDB (ex: C6 Business):
3 contas encadeadas:
- Banco (tipo CORRENTE): saldo operacional
- Aplicacao/CDB (tipo POUPANCA): garantia do limite
- Cartao (tipo CARTEIRA): limite disponivel

Cada movimento entre elas e uma Transferencia, nunca Despesa/Receita.

### Consequencias

Facilita: sem dupla contagem, visibilidade do saldo do cartao, DRE correto.
Compromete: usuario precisa criar conta do tipo CARTEIRA antes de comecar a usar cartao.
A Despesa que representa o pagamento da fatura deve ter is_active=False se criada
genericamente — senão duplica no DRE.

### Alternativas descartadas

Cartao como forma_pagamento na Despesa: intuitivo mas gera dupla contagem inevitavel.
Cartao como campo de metadado sem conta propria: impossibilita rastrear saldo do cartao.

---

## ADR-009: Conciliacao sem Auto-Lancamento para Transacoes Ambiguas

**Status:** Accepted
**Data:** 2026-07-28

### Contexto

Extratos bancarios contem transacoes que o sistema nao reconhece. Criar lancamentos
automaticamente para transacoes desconhecidas resultaria em LivroCaixa com lancamentos
incorretos que sao dificeis de rastrear e corrigir depois.

### Decisao

O motor de conciliacao opera em 3 camadas:
- Camada 1: matching direto por data+valor+tipo com tolerancia de +-1 dia (sempre executada)
- Camada 2 (flag auto=True): assenta Receitas/Despesas com status PENDENTE/ATRASADO encontradas
- Camada 3 (flag auto=True): cria lancamento via PadraoSeguroConciliacao aprovado pelo ADMIN

Transacoes sem match em nenhuma camada ficam com status FALTANDO_SISTEMA e aguardam
confirmacao manual via POST /conciliacoes/{id}/confirmar-item/.

NUNCA criar lancamento automatico sem padrao aprovado — ambiguidade = FALTANDO_SISTEMA.

Parser selecionado por nome da conta (substring case-insensitive no campo Conta.nome):
- "c6" ou "c6 bank" -> parse_c6
- "btg" -> parse_btg
- Outros bancos: stubs que retornam [] (a implementar por demanda)

### Consequencias

Facilita: LivroCaixa sempre confiavel, ADMIN tem controle sobre o que entra automaticamente.
Compromete: usuario precisa confirmar manualmente itens FALTANDO_SISTEMA.
Risco (R02): parsers de regex especificos para C6/BTG — mudanca de layout do extrato
quebra o parser.

### Alternativas descartadas

Criar lancamento automatico para tudo: rapido mas gera saldo falso e DRE incorreto.
OCR/ML para classificacao: custo e complexidade desnecessarios para o escopo atual.

---

## ADR-010: DecimalField para Valores Monetarios

**Status:** Accepted
**Data:** 2026-07-28

### Contexto

Valores monetarios precisam de precisao exata. Float/double em ponto flutuante IEEE 754
causa erros de arredondamento (ex: 0.1 + 0.2 != 0.3) que sao inaceitaveis em contexto
financeiro.

### Decisao

TODOS os campos de valor monetario usam DecimalField(max_digits=12, decimal_places=2).
No Python: Decimal do modulo decimal para calculos, nunca float.

Campos monetarios no sistema:
- Conta.saldo_inicial, Aporte.valor, Receita.valor_bruto/desconto/valor_liquido
- Despesa.valor_bruto/desconto/valor_liquido, LivroCaixa.valor/saldo_anterior/saldo_atual
- Orcamento.valor_total, Pedido.valor_total, ItemPedido.valor_unitario/valor_total
- Cobranca.valor, Parcela.valor, Cargo.salario_base, Funcionario.salario_atual
- FolhaPagamento.salario_bruto/descontos/salario_liquido, Cliente.limite_credito
- ConciliacaoExtrato.total_banco/total_sistema, ItemConciliacao.valor

max_digits=12 suporta valores ate 9.999.999.999,99 — suficiente para MEI/PME.

### Consequencias

Facilita: precisao exata, sem erro de arredondamento, compativel com PostgreSQL NUMERIC.
Compromete: JSON serializa como string em alguns contextos — frontend deve usar parseFloat
ou Decimal.js para operacoes matematicas.

### Alternativas descartadas

FloatField: erro de arredondamento inaceitavel em contexto financeiro.
IntegerField (centavos): convencao comum mas confusa para o usuario final e para o DRE.

---

## ADR-011: Migracao por App, Nunca Global

**Status:** Accepted
**Data:** 2026-07-28

### Contexto

Migrações globais (makemigrations sem app especificado) podem criar dependências cruzadas
entre apps e dificultar rastreamento de mudancas por modulo.

### Decisao

Toda migration deve ser gerada por app:
```
python manage.py makemigrations <app>
```

Nunca:
```
python manage.py makemigrations   # proibido em producao
```

Migrations sao geradas no ambiente de desenvolvimento e commitadas no repositorio.
Na VPS: apenas `python manage.py migrate` — nunca `makemigrations` em producao.

### Consequencias

Facilita: historico de migrations rastreavel por modulo, sem dependencias cruzadas acidentais.
Compromete: dev precisa especificar o app em cada geracao — nao pode usar o atalho global.

### Alternativas descartadas

makemigrations global: conveniente mas cria squash migration unica e dificulta rastreamento.

---

## ADR-012: CORS Configuravel via Env

**Status:** Accepted
**Data:** 2026-07-28

### Contexto

Em desenvolvimento o frontend roda em localhost:3000 e o backend em localhost:8000.
Em producao ambos sao servidos pelo mesmo dominio (nginx como proxy reverso), eliminando
CORS. A configuracao precisa ser flexivel entre ambientes.

### Decisao

```python
CORS_ALLOW_ALL_ORIGINS = config('CORS_ALLOW_ALL_ORIGINS', default=True, cast=bool)
```

Em producao: CORS_ALLOW_ALL_ORIGINS=False (sem CORS necessario — mesmo dominio via nginx).
Em desenvolvimento: True (frontend em localhost:3000 acessa backend em localhost:8000).
django-cors-headers middleware antes de SessionMiddleware na ordem de MIDDLEWARE.

### Consequencias

Facilita: dev local sem configuracao extra, producao segura sem CORS aberto.
Compromete: deve-se garantir CORS_ALLOW_ALL_ORIGINS=False no .env.prod sempre.

### Alternativas descartadas

CORS hardcoded como True: inseguro em producao.
Proxy Vite sempre (sem CORS no backend): funciona em dev mas nao em testes de integracao.

---

## ADR-013: Numeracao Automatica de Orcamentos e Pedidos

**Status:** Accepted
**Data:** 2026-07-28

### Contexto

Orcamentos e pedidos precisam de numeracao sequencial amigavel para referencias
comerciais com clientes (ex: "orc 2026/0042").

### Decisao

Numeracao gerada no save() do model, somente se o campo estiver vazio:
- Orcamento: ORC-YYYY-NNNN (contagem de orcamentos do ano + 1)
- Pedido: PED-YYYY-NNNN (contagem de pedidos do ano + 1)

Numero e imutavel apos criacao (serializer: read_only).

```python
def save(self, *args, **kwargs):
    if not self.numero:
        ano = date.today().year
        count = Orcamento.objects.filter(numero__startswith=f'ORC-{ano}').count()
        self.numero = f'ORC-{ano}-{count + 1:04d}'
    super().save(*args, **kwargs)
```

### Consequencias

Facilita: numeracao amigavel, sequencial por ano, sem configuracao extra.
Compromete (R03): race condition possivel em alto volume — para MEI e suficiente.
Para escalar: usar sequence PostgreSQL com select nextval().

### Alternativas descartadas

UUID como numero: nao e legivel para referencia comercial.
Numeracao global (sem ano): numeros grandes rapidamente para sistemas com historico.

---

## ADR-014: Frontend SPA com Proxy Nginx (Sem Base Path)

**Status:** Accepted
**Data:** 2026-07-28

### Contexto

O frontend e uma SPA React servida pelo Nginx. Em desenvolvimento usa Vite dev server
com proxy para o backend. Em producao o Nginx serve os arquivos estaticos do build e
roteia /api/* para o backend.

### Decisao

vite.config.js sem `base` configurado (default '/') — SPA na raiz do dominio.
Nginx: try_files $uri $uri/ /index.html para suporte a client-side routing.
Proxy em dev: /api/* -> localhost:8000.
VITE_API_URL: variavel de ambiente para apontar para o backend (default '/api/v1').

```js
export default defineConfig({
  server: {
    port: 3000,
    proxy: { '/api': { target: 'http://localhost:8000', changeOrigin: true } },
  },
})
```

### Consequencias

Facilita: URL limpa sem prefixo, build multi-stage sem npm na VPS.
Compromete: se base for alterado apos o primeiro deploy, o PWA e os links internos quebram.
Nota: UidCore nao implementa PWA — diferente de outros projetos Uid.

### Alternativas descartadas

Next.js SSR: overhead desnecessario para sistema interno autenticado.
base: '/<rota>/' no Vite: necessario apenas se o sistema nao for servido na raiz.
