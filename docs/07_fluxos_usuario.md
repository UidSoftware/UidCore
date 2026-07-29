# 07 — Fluxos de Usuario
**Sistema:** UidCore — Template Financeiro Multi-Nicho
**Versao:** 1.0 (baseline AS-IS em producao)
**Data:** 2026-07-28
**Referencia:** activity.md / usecase.md / Levantamento_Requisitos.md

---

## Perfis de Acesso

| Perfil | Condicao | Capacidades |
|---|---|---|
| ADMIN | is_staff=True | Acesso completo: CRUD de todos os modulos, registrar aportes, estornar despesas e lancamentos do LivroCaixa, gerenciar acesso ao portal |
| OPERACIONAL | Autenticado, is_staff=False | CRUD padrao de todos os modulos. Nao pode acessar aportes nem estornar lancamentos |
| CLIENTE | AcessoPortalCliente.ativo=True | Portal do cliente (telas a implementar por nicho). Pode baixar documentos associados |

---

## Fluxo 01 — Autenticacao (todos os perfis)

```
1. Usuario acessa /login
2. Preenche email e senha
3. POST /api/v1/auth/token/
   - Credenciais invalidas -> exibir erro, voltar ao formulario
   - Credenciais validas -> receber { access, refresh }
4. Frontend salva tokens no Zustand (persistido em localStorage)
5. GET /api/v1/accounts/me/ -> carregar dados do perfil
6. Redirecionar para /dashboard
```

---

## Fluxo 02 — Refresh Automatico de Token

```
Qualquer requisicao retorna 401
   |
   v
Interceptor Axios dispara POST /api/v1/auth/token/refresh/
   |
   +-- Sucesso: novo access_token -> retry da requisicao original
   |
   +-- Falha: logout() -> limpar Zustand -> redirecionar para /login
```

---

## Fluxo 03 — Dashboard (ADMIN e OPERACIONAL)

```
1. GET /api/v1/financeiro/dashboard/
2. Exibir metricas do mes corrente:
   - Receita total do mes
   - Despesa total do mes
   - Saldo total das contas
   - MRR (Monthly Recurring Revenue)
   - Proximos vencimentos (receitas e despesas PENDENTE/ATRASADO)
   - Grafico de 6 meses (entradas vs saidas)
   - Indicadores CFO: margem liquida, runway, ponto de equilibrio

Nota DIV02: Dashboard.jsx atualmente exibe placeholders.
            O endpoint esta implementado e funcionando.
            Integracao frontend pendente.
```

---

## Fluxo 04 — Lancamento de Receita (ADMIN e OPERACIONAL)

```
1. Navegar para Financeiro > Contas a Receber
2. GET /api/v1/financeiro/receitas/ -> listar receitas existentes

3. Criar nova receita:
   POST /api/v1/financeiro/receitas/
   Body: { tipo, descricao, valor_bruto, desconto, conta, vencimento,
           status='PENDENTE', categoria (opcional), cliente (opcional) }
   - Erro de validacao -> exibir mensagens e manter formulario
   - Sucesso -> receita criada com status PENDENTE

4. Marcar como recebida:
   PATCH /api/v1/financeiro/receitas/{id}/receber/
   - Signal post_save dispara
   - Sistema cria lancamento ENTRADA no LivroCaixa
   - _reconstruir_cadeia() executada em transaction.atomic() com advisory lock
   - Receita atualizada para status RECEBIDO

5. Editar receita:
   PATCH /api/v1/financeiro/receitas/{id}/
   Body: campos a alterar

6. Excluir receita (soft delete):
   DELETE /api/v1/financeiro/receitas/{id}/
   -> is_active=False; receita sai do DRE e do Balanco
```

---

## Fluxo 05 — Lancamento de Despesa (ADMIN e OPERACIONAL)

```
1. Navegar para Financeiro > Contas a Pagar
2. GET /api/v1/financeiro/despesas/ -> listar despesas

3. Criar nova despesa:
   POST /api/v1/financeiro/despesas/
   Body: { tipo, descricao, valor_bruto, desconto, conta, vencimento,
           status='PENDENTE', categoria (opcional) }
   - Sucesso -> despesa criada com status PENDENTE

4. Marcar como paga:
   PATCH /api/v1/financeiro/despesas/{id}/pagar/
   - Signal post_save dispara
   - Sistema cria lancamento SAIDA no LivroCaixa
   - _reconstruir_cadeia() executada

5. Estornar despesa (somente ADMIN):
   POST /api/v1/financeiro/despesas/{id}/estornar/
   - Verifica permissao IsAdmin
   - Nao-admin: retorna 403
   - Admin: marca estornado=True no lancamento original E no lancamento de estorno
   - _reconstruir_cadeia() executada

6. Excluir (soft delete):
   DELETE /api/v1/financeiro/despesas/{id}/
   -> is_active=False
```

---

## Fluxo 06 — Transferencia entre Contas (ADMIN e OPERACIONAL)

```
1. Navegar para Financeiro > Contas
2. Selecionar conta de origem
3. POST /api/v1/financeiro/contas/{id}/transferir/
   Body: { conta_destino, valor, descricao, data }
4. Sistema executa em transaction.atomic():
   - pg_advisory_xact_lock(conta_origem_id)
   - pg_advisory_xact_lock(conta_destino_id)
   - Cria LivroCaixa SAIDA na conta origem (origem=TRANSFER)
   - Cria LivroCaixa ENTRADA na conta destino (origem=TRANSFER)
   - _reconstruir_cadeia() em cada conta
5. Saldos de ambas as contas atualizados
```

---

## Fluxo 07 — Conciliacao Bancaria (ADMIN e OPERACIONAL)

```
1. Navegar para Financeiro > Conciliacao
2. Selecionar conta e mes de referencia
3. Upload do extrato PDF:
   POST /api/v1/financeiro/conciliacoes/upload/
   multipart: { arquivo, conta_id, periodo, auto }

4. Sistema executa:
   a. pdftotext extrai texto do PDF
   b. Parser selecionado pelo nome da conta (C6 ou BTG por substring)
   c. Parser gera lista de transacoes
   d. Matching Camada 1: data+valor+tipo com tolerancia +-1 dia
   e. Se auto=True:
      - Camada 2: assenta pendentes/atrasados correspondentes
      - Camada 3: cria lancamentos para transacoes com PadraoSeguroConciliacao aprovado
   f. Transacoes sem match e sem padrao -> status FALTANDO_SISTEMA

5. Listar resultado:
   GET /api/v1/financeiro/conciliacoes/
   GET /api/v1/financeiro/conciliacoes/{id}/itens/

6. Admin confirma itens FALTANDO_SISTEMA:
   POST /api/v1/financeiro/conciliacoes/{id}/confirmar-item/
   Body: { item_id, acao (criar lancamento manual ou ignorar) }
```

---

## Fluxo 08 — Relatorios Financeiros (ADMIN e OPERACIONAL)

```
DRE Anual:
  GET /api/v1/financeiro/dre/?ano=2026
  Retorna: receita operacional, receita financeira, descontos,
           despesas fixas, variaveis, prolabore, impostos, EBITDA
           com breakdown mensal

Balanco Patrimonial:
  GET /api/v1/financeiro/balanco/
  Retorna: Ativo (contas, receitas pendentes), Passivo (despesas pendentes,
           emprestimos), Patrimonio Liquido, equacao_ok (bool)

Fluxo Projetado 90 dias:
  GET /api/v1/financeiro/fluxo-projetado/
  Retorna: projecao de entradas e saidas para os proximos 90 dias
           com base em receitas/despesas pendentes e recorrentes

Indicadores CFO:
  GET /api/v1/financeiro/indicadores/
  Retorna: margem_liquida, ponto_equilibrio, ticket_medio, mrr,
           runway_meses, variacao_mes_anterior, variacao_ano_anterior

Fluxo de Caixa Mensal:
  GET /api/v1/financeiro/fluxo-caixa/?mes=2026-07
  Retorna: entradas e saidas do mes agrupadas por dia/semana
```

---

## Fluxo 09 — Aporte de Capital (somente ADMIN)

```
1. ADMIN navega para Financeiro > Aportes
2. POST /api/v1/financeiro/aportes/
   Body: { tipo, descricao, valor, conta, data, responsavel }
3. Sistema cria Aporte
4. Signal post_save dispara automaticamente:
   - Cria lancamento ENTRADA no LivroCaixa (origem=APORTE)
   - _reconstruir_cadeia() executada
5. Balanco atualizado:
   - EMPRESTIMO vai para Passivo Exigivel LP
   - CAPITAL_SOCIAL, SOCIO, INVESTIDOR vao para Patrimonio Liquido

OPERACIONAL tentando acessar -> retorna 403
```

---

## Fluxo 10 — Gestao de Clientes (ADMIN e OPERACIONAL)

```
1. GET /api/v1/clientes/ -> listar clientes (paginado)
2. Criar: POST /api/v1/clientes/
   Body: { tipo_pessoa, documento, nome_razao_social, telefone,
           email, endereco, cidade, estado, cep, segmento,
           limite_credito (opcional) }
3. Editar: PATCH /api/v1/clientes/{id}/
4. Registrar historico: POST /api/v1/clientes/{id}/historico/
   Body: { descricao, data }
5. Excluir: DELETE /api/v1/clientes/{id}/ -> is_active=False
```

---

## Fluxo 11 — Portal do Cliente (somente ADMIN cria/desativa)

```
1. ADMIN navega para Portal
2. GET /api/v1/portal/acessos/ -> listar vinculos existentes
3. Criar acesso:
   POST /api/v1/portal/acessos/
   Body: { usuario (ID do User), cliente (ID do Cliente) }
   -> AcessoPortalCliente criado com ativo=True

4. Desativar acesso:
   PATCH /api/v1/portal/acessos/{id}/
   Body: { ativo: false }
   -> AcessoPortalCliente.ativo=False (usuario CLIENTE perde acesso)

Nota DIV03: telas proprias para o perfil CLIENTE ainda nao implementadas.
            A ser desenvolvido por nicho sobre o UidCore.
```

---

## Fluxo 12 — Vendas (ADMIN e OPERACIONAL)

```
Orcamentos:
  GET  /api/v1/vendas/orcamentos/
  POST /api/v1/vendas/orcamentos/
       Body: { cliente (opcional), descricao, valor_total, validade }
       -> numero ORC-YYYY-NNNN gerado automaticamente
  Progresso de status: RASCUNHO -> ENVIADO -> APROVADO

Pedidos:
  GET  /api/v1/vendas/pedidos/
  POST /api/v1/vendas/pedidos/
       Body: { cliente (opcional), orcamento (opcional), valor_total, data_pedido }
       -> numero PED-YYYY-NNNN gerado automaticamente
  Progresso de status: PENDENTE -> CONFIRMADO -> EM_PRODUCAO -> ENTREGUE

Itens do Pedido:
  POST /api/v1/vendas/itens/
       Body: { pedido, descricao, quantidade, valor_unitario }
       -> valor_total calculado automaticamente: quantidade * valor_unitario
```

---

## Fluxo 13 — Livro Caixa (leitura geral; estorno somente ADMIN)

```
1. Visualizar lancamentos:
   GET /api/v1/financeiro/livro-caixa/
   GET /api/v1/financeiro/livro-caixa/totais/

2. LivroCaixa e READ-ONLY via API:
   PUT, PATCH, DELETE retornam 405

3. Estorno de lancamento manual (somente ADMIN):
   POST /api/v1/financeiro/livro-caixa/{id}/estornar/
   - Marca original com estornado=True
   - Cria lancamento inverso com estornado=True
   - _reconstruir_cadeia() executada

Lancamentos com estornado=True excluidos de todos os calculos de saldo.
```
