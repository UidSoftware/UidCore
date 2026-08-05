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

---

## ADR-015: App `pdv` Separado de `vendas`

**Status:** Accepted
**Data:** 2026-08-04
**Referencia:** Manutencao #15 / Blueprint_PDV.md

### Contexto

O app `vendas` ja existe em producao com `Orcamento`/`Pedido`/`ItemPedido` —
fluxo de encomenda/orcamento B2B (`Pedido.status`: PENDENTE→CONFIRMADO→
EM_PRODUCAO→ENTREGUE). Nao debita estoque, nao gera `Receita`/`LivroCaixa`,
nao tem sessao de caixa. O cliente pediu um modulo de frente de caixa/PDV para
venda de balcao a vista, com baixa de estoque sincrona, split de pagamento e
geracao automatica de lancamento financeiro — ciclo de vida e regras de negocio
incompativeis com o de `Pedido`.

### Decisao

Criar app Django novo `pdv`, com models proprios (`SessaoCaixa`,
`MovimentoCaixa`, `Venda`, `ItemVenda`, `PagamentoVenda`, `RecebivelCartao`),
prefixo de tabela `pdv_*`. `vendas` permanece inalterado.

### Consequencias

Facilita: dois dominios de negocio com ciclos de vida diferentes (encomenda
vs. venda instantanea) evoluem independentemente; nenhuma migration cruzada
retroativa em `vendas`.
Compromete: dois conceitos de "venda" no sistema (`vendas.Pedido` e
`pdv.Venda`) — nomenclatura exige atencao do dev para nao confundir; UI/menu
deve deixar claro que sao fluxos diferentes (Sidebar: PDV entre Vendas e
Financeiro, nao dentro do mesmo item de menu).

### Alternativas descartadas

Adicionar models de PDV dentro de `vendas`: misturaria `Pedido.status`
(fluxo de dias/semanas) com `Venda.status` (decidido em minutos no balcao) no
mesmo app, dificultando manutencao e leitura do codigo por dominio.

---

## ADR-016: `EstornoReceita` como Mecanismo Generico do `financeiro`

**Status:** Accepted
**Data:** 2026-08-04
**Referencia:** Manutencao #15 / Blueprint_PDV.md — Ponto 2 da spec

### Contexto

`Despesa.estornar` (ADR-007) so suporta estorno **total e unico** — nao serve
para devolucao parcial de item de venda (devolver 2 de 5 unidades, ou devolver
so 1 item entre varios de uma mesma `Venda`, em momentos diferentes). `Receita`
nao tinha nenhum mecanismo de estorno ate esta manutencao.

### Decisao

Novo model `EstornoReceita` (`fin_estorno_receita`) no app `financeiro` — nao
no `pdv` — com FK obrigatoria para `Receita` e FK **opcional** nullable
`item_venda` para `pdv.ItemVenda` (`on_delete=SET_NULL`). `Receita` ganha
`estornado`/`data_estorno`/`motivo_estorno` (compat de nomenclatura com
`Despesa`, mas semantica diferente: aqui significa "saldo esgotado", nao
"existe estorno") + properties `saldo_disponivel`/`valor_estornado_total`.
Uma `Receita` pode ter **N** `EstornoReceita` (parciais, em datas diferentes).

### Consequencias

Facilita: mecanismo reutilizavel para qualquer estorno parcial de receita no
sistema, nao so PDV (ex.: devolucao de mensalidade futura). Endpoint
`POST /financeiro/receitas/{id}/estornar/` funciona sozinho, sem depender do
app `pdv` existir.
Compromete: a migration de `financeiro` que cria `EstornoReceita.item_venda`
depende do model `pdv.ItemVenda` ja estar declarado no codigo (nao
necessariamente migrado) — gerar `makemigrations pdv` antes de
`makemigrations financeiro` nesta manutencao, unica vez.

### Alternativas descartadas

Campo `item_venda` obrigatorio (not null): acoplaria `financeiro` a `pdv` como
dependencia hard, impedindo estorno de receita sem origem em venda de PDV
(ex.: estorno de receita financeira/mensalidade).
Reusar `Despesa.estornar` como está (booleano unico): nao representa estorno
parcial nem multiplos estornos sobre a mesma receita — teria exigido reescrever
`Despesa` tambem, fora do escopo desta manutencao.

---

## ADR-017: DRE Abate Estorno de Receita no Mes da Receita Original

**Status:** Accepted
**Data:** 2026-08-04
**Referencia:** Manutencao #15 / Blueprint_PDV.md Secao 6.9 — spec Secao 5.5

### Contexto

`calcular_dre_mes()` filtra `Despesa` por `estornado=False` (exclui despesa
estornada do DRE do mes original de `pagamento`, retroativamente, toda vez que
o relatorio e recalculado) mas nao tinha filtro equivalente para `Receita`
porque o campo nao existia. Assim que `EstornoReceita` passa a existir, o DRE
fica incorreto se `calcular_dre_mes` nao for atualizado.

Duas opcoes eram possiveis: (1) abater no mes da receita original
(`recebimento`), ou (2) abater como linha separada no mes em que o estorno
aconteceu (`data_estorno`).

### Decisao

**Opcao 1** — abater no mes da receita original. `calcular_dre_mes(ano, mes)`
subtrai `Sum(EstornoReceita.valor)` de `receita_operacional`/
`receita_financeira` filtrando `EstornoReceita.receita.recebimento` no
`ano`/`mes` do parametro, nao `EstornoReceita.data_estorno`. Mantem o mesmo
espirito ja implementado para `Despesa.estornado` (que tambem "desaparece"
retroativamente do mes original quando a query e refeita).

### Consequencias

Facilita: DRE de qualquer mes, mesmo fechado, sempre reflete o resultado real
daquele mes — consistente com o CFO as a Service (visao historica confiavel).
Simetria com o comportamento ja existente de `Despesa`.
Compromete: DRE de um mes ja fechado "muda" quando uma venda antiga e
devolvida meses depois — comportamento aceito e documentado (mesmo trade-off
que ja existe hoje para estorno de `Despesa`).

### Alternativas descartadas

Opcao 2 (linha negativa no mes do estorno): mais simples de implementar mas
diverge do padrao ja em uso para `Despesa`, criando duas semanticas diferentes
de "estorno" dentro do mesmo relatorio.

---

## ADR-018: Mapeamento `MetodoPagamento` → `Conta` via Campo Direto

**Status:** Accepted
**Data:** 2026-08-04
**Referencia:** Manutencao #15 / Blueprint_PDV.md — achado A4

### Contexto

`MetodoPagamento` (app `pagamentos`) e apenas um catalogo de nomes (`choices`)
— nao existe hoje nenhum mapeamento "forma de pagamento → conta de destino".
Sem isso, ao finalizar uma venda no PDV nao ha como saber automaticamente qual
`Conta` creditar por forma de pagamento no split.

### Decisao

Adicionar `MetodoPagamento.conta_padrao` (FK `financeiro.Conta`, null=True,
`on_delete=SET_NULL`) e `MetodoPagamento.taxa_percentual_padrao`
(`DecimalField`, null=True, RF-18 Should). Resolucao em `pdv.services.
finalizar_venda`: usa `conta` do payload se informada, senao
`metodo.conta_padrao`; se nenhum dos dois existir, erro 400 (RF-14 Must =
selecao manual sempre disponivel como fallback).

Pre-requisito puramente tecnico — nao depende de aprovacao comercial, e a
unica forma de o PDV saber o que fazer com cada forma de pagamento.

### Consequencias

Facilita: configuracao opcional (Tela 7, Should) reduz cliques no dia a dia do
operador sem bloquear a entrega — sem a config, o operador so escolhe a conta
manualmente no split, PDV continua funcional.
Compromete: campo `null=True` significa que, sem configuracao, TODA venda com
aquele metodo exige selecao manual — UX pior ate o cliente configurar.

### Alternativas descartadas

Tabela de mapeamento separada (`ConfiguracaoMetodoPagamento`): mais "correto"
para representar 1:N (metodo pode ter contas diferentes por regra), mas
nenhum requisito da spec pede 1:N — campo direto e a solucao minima suficiente
(YAGNI), condizente com "Should" (RF-14/RF-18) e nao "Must" complexo.

---

## ADR-019: `RecebivelCartao` Acoplado a Conciliacao Existente, Sem Sistema Paralelo

**Status:** Accepted
**Data:** 2026-08-04
**Referencia:** Manutencao #15 / Blueprint_PDV.md Secao 6.6 — spec Secao 6 (Ponto 3)

### Contexto

Pagamento em cartao de credito tem taxa de maquininha e prazo de liquidacao —
o dinheiro nao cai na conta na hora da venda. O sistema ja tem
`ConciliacaoExtrato`/`ItemConciliacao` (ADR-009) para reconciliar extrato
bancario com o sistema; a tentacao seria criar um fluxo de recebivel
paralelo com sua propria tela de "confirmar recebimento".

### Decisao

`RecebivelCartao` (`pdv_recebivel_cartao`) nasce `PREVISTO` junto com uma
`Receita status=PENDENTE` na finalizacao da venda — nenhum `LivroCaixa` nasce
ainda (o signal `receita_para_livro_caixa` so dispara com `status=RECEBIDO`,
comportamento ja existente, zero codigo novo). A liquidacao acontece
**exclusivamente** via `ConciliacaoViewSet.confirmar_item` — estendida para
aceitar `recebivel_cartao_id` opcional no payload: quando presente, marca
`Receita.status=RECEBIDO` (dispara o signal existente → `LivroCaixa` nasce
sozinho) e `RecebivelCartao.status=LIQUIDADO`. Reaproveita `Receita.desconto`
existente para representar a taxa da maquininha — sem campo novo em `Receita`.

### Consequencias

Facilita: um unico fluxo de conciliacao no sistema todo, auditavel, sem
duplicidade de UI/logica. `RecebivelCartao` nunca vira `RECEBIDO` sozinho por
data (RN-06) — sempre exige confirmacao humana via conciliacao, evitando
marcar como recebido algo que nao caiu de fato.
Compromete: liquidacao de cartao de credito fica dependente do fluxo de
Conciliacao Bancaria ja existente — se o cliente nao fizer upload de extrato
regularmente, `RecebivelCartao` fica `PREVISTO` indefinidamente (aceitavel,
e o comportamento correto ate o extrato confirmar).

### Alternativas descartadas

Tela/endpoint dedicado para "confirmar recebimento de cartao" sem depender do
extrato bancario: mais rapido para o operador mas reintroduz o risco que
ADR-009 ja eliminou (marcar como recebido sem confirmacao real do banco).

---

## ADR-020: Lock de Concorrencia por Conta E por Produto na Finalizacao de Venda

**Status:** Accepted
**Data:** 2026-08-04
**Referencia:** Manutencao #15 / Blueprint_PDV.md Secao 6.2 — spec Secao 13 (Riscos)

### Contexto

ADR-006 ja garante exclusao mutua por `Conta` via `pg_advisory_xact_lock`. O
PDV introduz um recurso concorrente novo que o financeiro nao tinha:
`Produto.quantidade_estoque`, debitado por vendas em caixas/sessoes
diferentes ao mesmo tempo. Duas vendas simultaneas do mesmo produto em caixas
diferentes podem gerar race condition sem lock adicional.

### Decisao

`services.finalizar_venda` (e `cancelar_venda`) adquirem
`pg_advisory_xact_lock` da `Conta` da sessao de caixa **e**, em seguida, um
lock por `Produto.id` de cada item da venda — sempre em **ordem crescente de
id**, nunca na ordem em que os itens foram adicionados ao carrinho. Mesma
transacao, mesmo padrao de `cursor.execute('SELECT pg_advisory_xact_lock(%s)',
[id])` ja usado em `ContaViewSet.transferir` (que ja lockava 2 contas em
sequencia).

### Consequencias

Facilita: zero race condition de estoque entre vendas concorrentes no mesmo
produto, mesmo em caixas diferentes.
Compromete: custo adicional de N locks por venda (N = produtos distintos no
carrinho) — aceitavel para volume de PDV de MEI/PME. Ordem crescente de id e
**obrigatoria** — lock em ordem arbitraria entre duas transacoes concorrentes
com itens sobrepostos em ordem diferente pode deadlockar.

### Alternativas descartadas

`select_for_update()` simples sem advisory lock: protege a leitura mas nao
serializa as duas transacoes completas (uma pode ler estoque valido antes da
outra commitar seu debito) — mesmo raciocinio ja registrado em ADR-006 para
contas, aplicado agora a produtos.

---

## ADR-021: Finalizacao de Venda via `services.py` Procedural, Nao via Signal Django

**Status:** Accepted
**Data:** 2026-08-04
**Referencia:** Manutencao #15 / Blueprint_PDV.md Secao 6 — spec Secao 4/6

### Contexto

O sistema ja tem dois estilos de efeito colateral: signals `post_save`
(`aporte_para_livro_caixa`, `receita_para_livro_caixa`, `despesa_para_livro_caixa`
— efeito sempre igual, sem dado externo ao objeto salvo) e funcoes
procedurais dentro de `transaction.atomic()` em actions de ViewSet
(`ContaViewSet.transferir`, `DespesaViewSet.estornar_despesa`,
`ConciliacaoViewSet.confirmar_item` — quando o efeito depende de dado do
payload da requisicao ou precisa abortar antes do commit). A finalizacao de
venda do PDV precisa: (a) taxa/prazo do cartao vindos do payload, que nao sao
campo persistido em `PagamentoVenda`; (b) abortar com erro 400 legivel se
qualquer item nao tiver estoque, antes de debitar qualquer coisa.

### Decisao

`pdv.services.finalizar_venda/cancelar_venda/devolver_item` sao funcoes
procedurais chamadas pelas actions do `VendaViewSet`, dentro de
`transaction.atomic()` com advisory lock (ADR-020) — **nao** signals
`post_save` em `PagamentoVenda`/`ItemVenda`. O unico ponto onde um signal
Django ja existente participa e passivo: `receita_para_livro_caixa`
(`financeiro/signals.py`), que dispara sozinho quando a `Receita` criada pelo
service tem `status=RECEBIDO` — nenhum codigo novo de geracao de `LivroCaixa`
foi escrito para o PDV.

### Consequencias

Facilita: validacao com abort limpo antes do commit (RF-07); dados do payload
(taxa/prazo) ficam disponiveis onde sao usados, sem gambiarra de atributo
transiente em instancia de model; consistente com o padrao ja dominante no
sistema para operacoes financeiras multi-passo.
Compromete: mais codigo explicito em `services.py` em vez de "magico" via
signal — decisao consciente de legibilidade sobre concisao, mesmo trade-off
ja aceito em `transferir`/`estornar_despesa`.

### Alternativas descartadas

`post_save` em `PagamentoVenda` para criar `Receita`/`RecebivelCartao`:
exigiria armazenar taxa/prazo em campos nullable de `PagamentoVenda` so para
o signal ler (rejeitado pela propria spec do Analista, Secao 4.5) ou atributo
transiente nao persistido (fragil, quebra se o save() vier de outro caminho
como admin do Django ou fixture de teste).
