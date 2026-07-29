# Levantamento de Requisitos — UidCore
**Sistema:** UidCore — Template Financeiro Multi-Nicho
**Versao:** AS-IS (documentado a partir do codigo em producao)
**Data:** 2026-07-28
**Elaborado por:** Analista
**Referencia:** ArquiteturaTecnica#2 / Manutencao#7

---

## 1. Contexto

O UidCore e o nucleo reutilizavel (backbone) para os produtos verticais da Uid Software. Cada nicho atendido (pilates, salao, loja, clinica, etc.) recebe uma instancia do UidCore adaptada com modulos especificos do segmento, evitando reconstrucao do zero a cada novo cliente.

O sistema opera como uma plataforma de gestao financeira e operacional para MEI e pequenas empresas, com modulo de CFO as a Service embutido — fornecendo DRE, Balanco Patrimonial, Fluxo Projetado e indicadores financeiros automaticamente.

**Deploy atual:** porta 8006, dominio uidcore.uidsoftware.com.br
**Stack:** Django 5.x + DRF + SimpleJWT + React 18 + Vite + Tailwind CSS + PostgreSQL + Zustand + TanStack Query

---

## 2. AS-IS (Como o sistema funciona hoje)

Todas as fases estao em producao. O sistema foi construido em 5 fases:

| Fase | Conteudo |
|------|----------|
| A | common/models.py (BaseModel, PessoaBase), clientes, fornecedores |
| B | financeiro completo (Conta, Aporte, Categoria, Receita, Despesa, LivroCaixa, signals, views) |
| C | financeiro/relatorios.py (DRE, Balanco, FluxoProjetado, Indicadores), endpoints de relatorio |
| D | Conciliacao bancaria automatica (ConciliacaoExtrato, ItemConciliacao, PadraoSeguroConciliacao) |
| E | Vendas, Pagamentos, RH, Agendamento, Administrativo, Portal |

---

## 3. TO-BE (Estado atual ja e o alvo)

O sistema esta em producao com todos os modulos implementados. Este documento registra o estado atual como baseline para futuras manutencoes e expansoes de nicho.

---

## 4. Requisitos Funcionais por Modulo

### 4.1 Accounts (autenticacao e usuarios)

RF-ACC01 — O sistema deve autenticar usuarios por email e senha via JWT (POST /api/v1/auth/token/).
RF-ACC02 — O sistema deve emitir access token (validade 1 hora) e refresh token (validade 7 dias).
RF-ACC03 — O sistema deve renovar o access token via refresh token (POST /api/v1/auth/token/refresh/).
RF-ACC04 — O sistema deve permitir cadastro de novos usuarios via endpoint publico (POST /api/v1/accounts/register/).
RF-ACC05 — O sistema deve retornar o perfil do usuario autenticado (GET /api/v1/accounts/me/).
RF-ACC06 — O usuario autenticado deve poder atualizar seu proprio perfil (PATCH /api/v1/accounts/me/).
RF-ACC07 — O campo USERNAME_FIELD e email — autenticacao por username e proibida.
RF-ACC08 — Permissao IsAdmin e concedida a usuarios com is_staff=True.

### 4.2 Clientes

RF-CLI01 — O sistema deve permitir CRUD completo de clientes (PF e PJ).
RF-CLI02 — O cliente pode ser Pessoa Fisica (CPF) ou Pessoa Juridica (CNPJ); campo documento unico.
RF-CLI03 — O cliente possui segmento: COMERCIO, SERVICOS, INDUSTRIA, SAUDE, EDUCACAO, TECNOLOGIA, ALIMENTACAO ou OUTRO.
RF-CLI04 — O sistema deve registrar limite de credito do cliente (DecimalField).
RF-CLI05 — O sistema deve permitir registrar historico de interacoes por cliente (HistoricoCliente).
RF-CLI06 — Exclusao de cliente: soft delete (is_active=False), nunca delete fisico.
RF-CLI07 — Endpoint: /api/v1/clientes/

### 4.3 Fornecedores

RF-FOR01 — O sistema deve permitir CRUD completo de fornecedores (PF e PJ).
RF-FOR02 — Fornecedor possui categoria: MATERIA_PRIMA, SERVICOS, TECNOLOGIA, LOGISTICA, MANUTENCAO, ESCRITORIO, MARKETING ou OUTRO.
RF-FOR03 — Fornecedor possui campos de contato especifico (contato_nome, contato_telefone) e website.
RF-FOR04 — Exclusao de fornecedor: soft delete (is_active=False).
RF-FOR05 — Endpoint: /api/v1/fornecedores/

### 4.4 Financeiro — Contas

RF-FIN-CON01 — O sistema deve permitir CRUD de contas financeiras com tipos: CORRENTE, POUPANCA, CAIXA, CARTEIRA.
RF-FIN-CON02 — Conta possui saldo_inicial para inicializacao do saldo historico.
RF-FIN-CON03 — O sistema deve permitir transferencia entre contas via endpoint dedicado (POST /api/v1/financeiro/contas/{id}/transferir/).
RF-FIN-CON04 — Transferencia cria dois lancamentos no LivroCaixa (SAIDA na origem, ENTRADA no destino) dentro de transaction.atomic().
RF-FIN-CON05 — Exclusao de conta: soft delete (is_active=False).

### 4.5 Financeiro — Aportes

RF-FIN-APO01 — O sistema deve permitir registrar aportes de capital por tipo: CAPITAL_SOCIAL, SOCIO, INVESTIDOR, EMPRESTIMO.
RF-FIN-APO02 — Aporte cria automaticamente um lancamento ENTRADA no LivroCaixa via signal post_save.
RF-FIN-APO03 — Aportes exigem permissao IsAdmin.
RF-FIN-APO04 — EMPRESTIMO vai para Passivo Exigivel LP no Balanco; demais tipos vao para Capital no PL.

### 4.6 Financeiro — Categorias

RF-FIN-CAT01 — O sistema deve permitir CRUD de categorias financeiras tipadas: ENTRADA ou SAIDA.
RF-FIN-CAT02 — Combinacao nome+tipo e unica (unique_together).
RF-FIN-CAT03 — Exclusao de categoria: soft delete (is_active=False).

### 4.7 Financeiro — Receitas

RF-FIN-REC01 — O sistema deve permitir CRUD de receitas com tipos: SERVICO, PRODUTO, MENSALIDADE, RECEITA_FINANCEIRA, OUTRO.
RF-FIN-REC02 — Receita possui valor_bruto, desconto e valor_liquido (calculado no save: bruto - desconto).
RF-FIN-REC03 — Status de receita: PENDENTE, RECEBIDO, CANCELADO, ATRASADO.
RF-FIN-REC04 — Ao marcar receita como RECEBIDO, o sistema deve criar um lancamento ENTRADA no LivroCaixa via signal.
RF-FIN-REC05 — Endpoint de acao: PATCH /api/v1/financeiro/receitas/{id}/receber/.
RF-FIN-REC06 — Exclusao de receita: soft delete (is_active=False).
RF-FIN-REC07 — Receitas com is_active=False nao entram no DRE nem no Balanco.

### 4.8 Financeiro — Despesas

RF-FIN-DES01 — O sistema deve permitir CRUD de despesas com tipos: FIXA, VARIAVEL, PROLABORE, IMPOSTO, OUTRO.
RF-FIN-DES02 — Despesa possui valor_bruto, desconto e valor_liquido (calculado no save).
RF-FIN-DES03 — Status de despesa: PENDENTE, PAGO, CANCELADO, ATRASADO.
RF-FIN-DES04 — Despesa suporta flags de recorrencia: recorrente (bool), frequencia (str), quantidade (int).
RF-FIN-DES05 — Ao marcar despesa como PAGO, o sistema deve criar lancamento SAIDA no LivroCaixa via signal.
RF-FIN-DES06 — Endpoint de acao: PATCH /api/v1/financeiro/despesas/{id}/pagar/.
RF-FIN-DES07 — O sistema deve permitir estornar despesas pagas (POST /api/v1/financeiro/despesas/{id}/estornar/) — restrito a ADMIN.
RF-FIN-DES08 — Estorno marca estornado=True em AMBOS os lancamentos (original e estorno).
RF-FIN-DES09 — Despesa suporta upload de comprovante (FileField upload_to='despesas/').
RF-FIN-DES10 — Exclusao de despesa: soft delete (is_active=False).

### 4.9 Financeiro — Livro Caixa

RF-FIN-LC01 — LivroCaixa e imutavel: ReadCreateViewSet (sem PUT/PATCH/DELETE via API padrao).
RF-FIN-LC02 — Cada lancamento registra: conta, tipo, origem, origem_id, valor, data, saldo_anterior, saldo_atual.
RF-FIN-LC03 — Ao criar qualquer lancamento, o sistema reconstroi a cadeia de saldos da conta dentro de transaction.atomic() com advisory lock por conta.
RF-FIN-LC04 — Endpoint de totais: GET /api/v1/financeiro/livro-caixa/totais/.
RF-FIN-LC05 — O sistema deve permitir estornar lancamentos manuais (POST /api/v1/financeiro/livro-caixa/{id}/estornar/) — restrito a ADMIN.
RF-FIN-LC06 — Lancamentos estornados sao excluidos dos calculos de saldo e relatorios.

### 4.10 Financeiro — Relatorios e Dashboard

RF-FIN-REL01 — Fluxo de Caixa mensal: GET /api/v1/financeiro/fluxo-caixa/?mes=YYYY-MM.
RF-FIN-REL02 — DRE anual com breakdown mensal: GET /api/v1/financeiro/dre/?ano=YYYY.
RF-FIN-REL03 — DRE separa: receita operacional, receita financeira, descontos, despesas fixas, variaveis, prolabore, impostos e EBITDA.
RF-FIN-REL04 — Balanco Patrimonial: GET /api/v1/financeiro/balanco/.
RF-FIN-REL05 — Balanco garante equacao Ativo = Passivo + PL; campo equacao_ok indica se fecha.
RF-FIN-REL06 — Fluxo Projetado para 90 dias: GET /api/v1/financeiro/fluxo-projetado/.
RF-FIN-REL07 — Indicadores CFO: GET /api/v1/financeiro/indicadores/ (margem liquida, ponto equilibrio, ticket medio, MRR, runway em meses, variacao vs mes anterior e vs ano anterior).
RF-FIN-REL08 — Dashboard Financeiro consolidado: GET /api/v1/financeiro/dashboard/.
RF-FIN-REL09 — Inferir categoria por descricao: POST /api/v1/financeiro/inferir-categoria/.

### 4.11 Financeiro — Conciliacao Bancaria

RF-FIN-CONC01 — Upload de extrato bancario em PDF: POST /api/v1/financeiro/conciliacoes/upload/ (multipart/form-data).
RF-FIN-CONC02 — Extracao de texto via pdftotext (poppler-utils no container).
RF-FIN-CONC03 — Parsers implementados: C6 e BTG. Stubs: Nubank, Inter, Caixa, Itau.
RF-FIN-CONC04 — Parser selecionado pelo nome da conta (substring case-insensitive).
RF-FIN-CONC05 — Matching em 3 camadas: (1) data+valor+tipo com tolerancia +-1 dia; (2) com flag auto: assenta pendentes/atrasados; (3) com flag auto: cria por PadraoSeguroConciliacao.
RF-FIN-CONC06 — NUNCA criar lancamento automatico sem padrao aprovado — ambiguidade resulta em FALTANDO_SISTEMA.
RF-FIN-CONC07 — Listar conciliacoes: GET /api/v1/financeiro/conciliacoes/.
RF-FIN-CONC08 — Listar itens: GET /api/v1/financeiro/conciliacoes/{id}/itens/.
RF-FIN-CONC09 — Confirmar item: POST /api/v1/financeiro/conciliacoes/{id}/confirmar-item/.
RF-FIN-CONC10 — CRUD de padroes seguros: /api/v1/financeiro/padroes-conciliacao/.

### 4.12 Vendas

RF-VEN01 — CRUD de Orcamentos com numeracao automatica ORC-YYYY-NNNN.
RF-VEN02 — Status de orcamento: RASCUNHO, ENVIADO, APROVADO, REJEITADO, CANCELADO.
RF-VEN03 — CRUD de Pedidos com numeracao automatica PED-YYYY-NNNN.
RF-VEN04 — Pedido pode ser vinculado a um Orcamento (FK opcional).
RF-VEN05 — Status de pedido: PENDENTE, CONFIRMADO, EM_PRODUCAO, ENTREGUE, CANCELADO.
RF-VEN06 — CRUD de ItemPedido com valor_total = quantidade * valor_unitario (calculado no save).
RF-VEN07 — Exclusao: soft delete (is_active=False).
RF-VEN08 — Endpoint base: /api/v1/vendas/

### 4.13 Pagamentos

RF-PAG01 — CRUD de MetodoPagamento com tipos: PIX, BOLETO, CARTAO_CREDITO, CARTAO_DEBITO, DINHEIRO, OUTRO.
RF-PAG02 — CRUD de Cobrancas vinculadas a clientes.
RF-PAG03 — Status de cobranca: PENDENTE, PAGO, CANCELADO, ATRASADO.
RF-PAG04 — Cobranca suporta upload de comprovante (FileField upload_to='comprovantes/').
RF-PAG05 — CRUD de Parcelas vinculadas a Cobrancas.
RF-PAG06 — Status de parcela: PENDENTE, PAGO, CANCELADO.
RF-PAG07 — Exclusao: soft delete (is_active=False).
RF-PAG08 — Endpoint base: /api/v1/pagamentos/

### 4.14 Administrativo

RF-ADM01 — CRUD de TipoDocumento.
RF-ADM02 — CRUD de Documento com upload de arquivo (FileField upload_to='docs/').
RF-ADM03 — Documento pode ser associado opcionalmente a um cliente.
RF-ADM04 — Status de documento: RASCUNHO, VIGENTE, EXPIRADO, CANCELADO.
RF-ADM05 — Exclusao: soft delete (is_active=False).
RF-ADM06 — Endpoint base: /api/v1/administrativo/

### 4.15 RH

RF-RH01 — CRUD de Cargos com salario base.
RF-RH02 — CRUD de Funcionarios com CPF unico (sem mascara, apenas digitos).
RF-RH03 — Funcionario possui regime: CLT, PJ, ESTAGIO, SOCIO.
RF-RH04 — CRUD de FolhaPagamento com salario_liquido = bruto - descontos (calculado no save).
RF-RH05 — Status de folha: ABERTA, FECHADA, PAGA.
RF-RH06 — mes_referencia armazena o primeiro dia do mes.
RF-RH07 — CRUD de RegistroFerias com dias = (data_fim - data_inicio).days (calculado no save).
RF-RH08 — Status de ferias: AGENDADO, EM_ANDAMENTO, CONCLUIDO.
RF-RH09 — Exclusao: soft delete (is_active=False).
RF-RH10 — Endpoint base: /api/v1/rh/

### 4.16 Agendamento

RF-AGE01 — CRUD de Agendas com cor hex customizavel (default #3B82F6).
RF-AGE02 — CRUD de Compromissos com inicio e fim (DateTimeField).
RF-AGE03 — Compromisso pode ser vinculado opcionalmente a um cliente.
RF-AGE04 — Status de compromisso: AGENDADO, CONFIRMADO, CANCELADO, CONCLUIDO.
RF-AGE05 — Validacao no serializer: fim deve ser >= inicio.
RF-AGE06 — Exclusao: soft delete (is_active=False).
RF-AGE07 — Endpoint base: /api/v1/agendamento/

### 4.17 Portal do Cliente

RF-POR01 — Vincular accounts.User a clientes.Cliente via AcessoPortalCliente (OneToOneField).
RF-POR02 — Acesso pode ser desativado (ativo=False) sem exclusao do registro.
RF-POR03 — ultimo_acesso e somente leitura, atualizado pelo sistema.
RF-POR04 — AcessoPortalCliente nao herda BaseModel — usa campos proprios (ativo, criado_em).
RF-POR05 — Endpoint base: /api/v1/portal/

---

## 5. Requisitos Nao Funcionais

RNF01 — Autenticacao: JWT via SimpleJWT. Access token: 1h. Refresh token: 7 dias com rotacao.
RNF02 — Autorizacao por perfil: is_staff=True equivale a ADMIN; usuarios comuns = OPERACIONAL.
RNF03 — Soft delete obrigatorio em todos os models com BaseModel — nunca .delete() direto.
RNF04 — Valores monetarios: SEMPRE DecimalField(max_digits=12, decimal_places=2) — NUNCA Float.
RNF05 — Timestamps: todos os models com BaseModel possuem created_at e updated_at automaticos.
RNF06 — Paginacao: StandardPagination com PAGE_SIZE=20; resposta frontend usa response.data.results.
RNF07 — CORS: CORS_ALLOW_ALL_ORIGINS configuravel via env (default True em dev).
RNF08 — Banco: PostgreSQL 16. Advisory lock por conta_id para operacoes de LivroCaixa.
RNF09 — Idioma: pt-BR. Timezone: America/Sao_Paulo.
RNF10 — Frontend: React 18 + Vite + Tailwind CSS. Fontes: Plus Jakarta Sans + DM Sans.
RNF11 — Estado global frontend: Zustand com persistencia em localStorage.
RNF12 — HTTP client frontend: Axios com interceptor de refresh automatico.
RNF13 — CI/CD: GitHub Actions. NUNCA deploy manual via SSH.
RNF14 — Container: Docker Compose + Gunicorn + Nginx.
RNF15 — Migrations: sempre por app (makemigrations <app>), nunca global.
RNF16 — Concorrencia financeira: pg_advisory_xact_lock por conta_id antes de qualquer operacao de saldo.

---

## 6. Atores e Perfis de Acesso

**ADMIN (is_staff=True):** acesso completo. Pode registrar aportes, estornar despesas e lancamentos do LivroCaixa.
**OPERACIONAL (autenticado, is_staff=False):** acesso a CRUD padrao. NAO pode acessar AporteViewSet nem estornar lancamentos.
**CLIENTE (AcessoPortalCliente.ativo=True):** vinculado a um cliente. Portal do cliente ainda sem telas proprias — a ser expandido por nicho.

---

## 7. Regras de Negocio Criticas

RN01 — LivroCaixa e imutavel via API publica: ReadCreateViewSet. Estorno so via action dedicada restrita a ADMIN.
RN02 — Cadeia de saldos: toda escrita no LivroCaixa executa _reconstruir_cadeia() recalculando saldo_anterior e saldo_atual de todos os lancamentos da conta em ordem cronologica.
RN03 — Estorno em par obrigatorio: lancamento original E lancamento de estorno devem ter estornado=True.
RN04 — Cartao de credito: modelar como Conta com tipo=CARTEIRA, nao como lancamento direto.
RN05 — Cartao com garantia CDB: usar 3 contas encadeadas (Banco -> Aplicacao/CDB -> Cartao).
RN06 — Transferencia entre bolsos: criar lancamento de TRANSFER; Despesa/Receita correspondente com is_active=False para nao duplicar no DRE.
RN07 — Aporte de socio NAO e receita: vai para PL. Rendimento de aplicacao e RECEITA_FINANCEIRA (entra no DRE).
RN08 — Gasto em moeda estrangeira: NUNCA usar recorrente/frequencia/quantidade. Lancar com o valor real da fatura.
RN09 — Signals de LivroCaixa sao idempotentes: verificam existencia de lancamento com mesmo origem+origem_id antes de criar.
RN10 — Numeracao de orcamentos e pedidos: gerada automaticamente no save(). Imutavel apos criacao.
RN11 — Conciliacao bancaria: NUNCA tomar decisao automatica para transacoes sem padrao aprovado.
RN12 — NaturezaPadraoConciliacao: APORTE vai para PL; RECEITA_FINANCEIRA entra no DRE.
RN13 — Saldo calculado por soma agregada via _saldo_real(). Lancamentos retroativos exigem _reconstruir_cadeia().

---

## 8. Fluxos Principais

### Login -> Dashboard
1. POST /api/v1/auth/token/ com email+senha
2. Frontend armazena tokens no Zustand (persistido em localStorage)
3. Todas as requisicoes incluem Authorization: Bearer {access_token}
4. Em 401: interceptor Axios dispara refresh automatico

### Lancamento Financeiro
1. Criar Conta (se nao existir)
2. Criar Categoria ENTRADA ou SAIDA
3. Criar Receita (PENDENTE) ou Despesa (PENDENTE)
4. Chamar /receber/ ou /pagar/ quando efetivado
5. Signal post_save gera lancamento no LivroCaixa automaticamente

### Conciliacao Bancaria
1. Selecionar conta e mes
2. Upload do extrato PDF
3. Sistema extrai e faz matching com LivroCaixa
4. Com flag auto: assenta pendentes e cria por padrao seguro
5. Admin confirma itens FALTANDO_SISTEMA restantes

---

## 9. Fora do Escopo

- Emissao de NF-e ou NFS-e
- Modulo de estoque/inventario
- Integracao com gateway de pagamento (PIX via API, boleto bancario)
- Integracao n8n/WhatsApp (previsto, nao implementado)
- Logica especifica de nicho (a ser adicionada por cima do UidCore)
- Portal do cliente com telas proprias para o usuario CLIENTE

---

## 10. Riscos e Dependencias

R01 — poppler-utils: necessario no container para conciliacao bancaria.
R02 — Parsers de extrato: C6 e BTG com regex especifico; stubs para outros bancos sao intencionais.
R03 — Race condition em numeracao ORC/PED: suficiente para MEI; para alto volume usar sequence PostgreSQL.
R04 — Saldo retroativo: comando reconstruir_saldo nao portado do SystemD. Risco em insercoes retroativas.
R05 — Portal do cliente: estrutura existe mas telas de portal nao implementadas.
R06 — Endpoint de listagem de usuarios: ausente em /api/v1/accounts/. Necessario para select no Portal.jsx.

---

## 11. Divergencias observadas (codigo real vs ArquiteturaTecnica#2)

DIV01 — App 'conciliacao' removido: a Arquitetura previa pasta backend/conciliacao/. No codigo final, os models foram incorporados em financeiro/models.py. A pasta existe no disco mas e ignorada.
DIV02 — Dashboard.jsx exibe metricas estaticas: o endpoint /api/v1/financeiro/dashboard/ existe e funciona, mas o frontend ainda nao consome esses dados (placeholders).
DIV03 — Portal do cliente sem telas proprias: estrutura de vinculo existe, mas as telas que o usuario CLIENTE ve apos autenticar nao foram implementadas.
DIV04 — is_active vs ativo: AcessoPortalCliente, Agenda e PadraoSeguroConciliacao usam campo ativo proprio em vez de is_active herdado do BaseModel. Soft delete funciona mas nao e uniforme.
DIV05 — MetodoPagamento possui dois campos booleanos (ativo proprio + is_active do BaseModel). ViewSet filtra por is_active=True.
DIV06 — Financeiro.jsx: 8 abas no modulo financeiro + 1 aba de conciliacao (total 9 abas no componente mais complexo do frontend).
