# 02 — Requisitos Funcionais
**Sistema:** UidCore — Template Financeiro Multi-Nicho
**Versao:** 1.0 (baseline AS-IS em producao)
**Data:** 2026-07-28
**Referencia:** Levantamento_Requisitos.md / ArquiteturaTecnica#2

---

## Convencao de Prioridade

| Prioridade | Criterio |
|---|---|
| Alta | Nucleo do sistema — sem isso o sistema nao funciona |
| Media | Funcionalidade importante — impacta experiencia significativamente |
| Baixa | Complementar — pode ser postergada sem bloquear operacao |

---

## Modulo: Accounts

| ID | Requisito | Prioridade |
|---|---|---|
| RF-ACC01 | Autenticar usuarios por email e senha via JWT (POST /api/v1/auth/token/). | Alta |
| RF-ACC02 | Emitir access token (validade 1h) e refresh token (validade 7 dias). | Alta |
| RF-ACC03 | Renovar access token via refresh token (POST /api/v1/auth/token/refresh/). | Alta |
| RF-ACC04 | Permitir cadastro de usuarios via endpoint publico (POST /api/v1/accounts/register/). | Alta |
| RF-ACC05 | Retornar perfil do usuario autenticado (GET /api/v1/accounts/me/). | Alta |
| RF-ACC06 | Usuario autenticado pode atualizar proprio perfil (PATCH /api/v1/accounts/me/). | Media |
| RF-ACC07 | USERNAME_FIELD = email. Autenticacao por username e proibida. | Alta |
| RF-ACC08 | Permissao IsAdmin concedida a usuarios com is_staff=True. | Alta |

---

## Modulo: Clientes

| ID | Requisito | Prioridade |
|---|---|---|
| RF-CLI01 | CRUD completo de clientes suportando Pessoa Fisica (CPF) e Pessoa Juridica (CNPJ). | Alta |
| RF-CLI02 | Campo documento unico; armazena CPF ou CNPJ sem mascara. | Alta |
| RF-CLI03 | Segmento do cliente: COMERCIO, SERVICOS, INDUSTRIA, SAUDE, EDUCACAO, TECNOLOGIA, ALIMENTACAO, OUTRO. | Media |
| RF-CLI04 | Limite de credito do cliente como DecimalField(12,2). | Media |
| RF-CLI05 | Historico de interacoes por cliente (HistoricoCliente). Endpoint: POST /api/v1/clientes/{id}/historico/. | Media |
| RF-CLI06 | Exclusao: soft delete (is_active=False). | Alta |

---

## Modulo: Fornecedores

| ID | Requisito | Prioridade |
|---|---|---|
| RF-FOR01 | CRUD completo de fornecedores (PF e PJ). | Alta |
| RF-FOR02 | Categoria: MATERIA_PRIMA, SERVICOS, TECNOLOGIA, LOGISTICA, MANUTENCAO, ESCRITORIO, MARKETING, OUTRO. | Media |
| RF-FOR03 | Campos: contato_nome, contato_telefone, website, inscricao_estadual. | Baixa |
| RF-FOR04 | Exclusao: soft delete (is_active=False). | Alta |

---

## Modulo: Financeiro — Contas

| ID | Requisito | Prioridade |
|---|---|---|
| RF-FIN-CON01 | CRUD de contas com tipos: CORRENTE, POUPANCA, CAIXA, CARTEIRA. | Alta |
| RF-FIN-CON02 | Conta possui saldo_inicial para inicializacao do historico. | Alta |
| RF-FIN-CON03 | Transferencia entre contas via POST /api/v1/financeiro/contas/{id}/transferir/. | Alta |
| RF-FIN-CON04 | Transferencia cria dois lancamentos no LivroCaixa (SAIDA na origem, ENTRADA no destino) em transaction.atomic(). | Alta |
| RF-FIN-CON05 | Exclusao: soft delete (is_active=False). | Alta |

---

## Modulo: Financeiro — Aportes

| ID | Requisito | Prioridade |
|---|---|---|
| RF-FIN-APO01 | Registrar aportes de capital: CAPITAL_SOCIAL, SOCIO, INVESTIDOR, EMPRESTIMO. | Alta |
| RF-FIN-APO02 | Aporte cria automaticamente lancamento ENTRADA no LivroCaixa via signal post_save. | Alta |
| RF-FIN-APO03 | Aportes exigem permissao IsAdmin. | Alta |
| RF-FIN-APO04 | EMPRESTIMO vai para Passivo Exigivel LP no Balanco; demais tipos vao para Capital no PL. | Alta |

---

## Modulo: Financeiro — Categorias

| ID | Requisito | Prioridade |
|---|---|---|
| RF-FIN-CAT01 | CRUD de categorias com tipo: ENTRADA ou SAIDA. | Alta |
| RF-FIN-CAT02 | Combinacao nome+tipo deve ser unica (unique_together). | Alta |
| RF-FIN-CAT03 | Exclusao: soft delete (is_active=False). | Alta |

---

## Modulo: Financeiro — Receitas

| ID | Requisito | Prioridade |
|---|---|---|
| RF-FIN-REC01 | CRUD de receitas com tipos: SERVICO, PRODUTO, MENSALIDADE, RECEITA_FINANCEIRA, OUTRO. | Alta |
| RF-FIN-REC02 | Receita possui valor_bruto, desconto e valor_liquido (calculado: bruto - desconto). | Alta |
| RF-FIN-REC03 | Status: PENDENTE, RECEBIDO, CANCELADO, ATRASADO. | Alta |
| RF-FIN-REC04 | Ao marcar RECEBIDO: criar lancamento ENTRADA no LivroCaixa via signal post_save. | Alta |
| RF-FIN-REC05 | Endpoint de acao: PATCH /api/v1/financeiro/receitas/{id}/receber/. | Alta |
| RF-FIN-REC06 | Exclusao: soft delete (is_active=False). | Alta |
| RF-FIN-REC07 | Receitas com is_active=False excluidas do DRE e do Balanco. | Alta |

---

## Modulo: Financeiro — Despesas

| ID | Requisito | Prioridade |
|---|---|---|
| RF-FIN-DES01 | CRUD de despesas com tipos: FIXA, VARIAVEL, PROLABORE, IMPOSTO, OUTRO. | Alta |
| RF-FIN-DES02 | Despesa possui valor_bruto, desconto e valor_liquido (calculado: bruto - desconto). | Alta |
| RF-FIN-DES03 | Status: PENDENTE, PAGO, CANCELADO, ATRASADO. | Alta |
| RF-FIN-DES04 | Flags de recorrencia: recorrente (bool), frequencia (str), quantidade (int). | Media |
| RF-FIN-DES05 | Ao marcar PAGO: criar lancamento SAIDA no LivroCaixa via signal post_save. | Alta |
| RF-FIN-DES06 | Endpoint de acao: PATCH /api/v1/financeiro/despesas/{id}/pagar/. | Alta |
| RF-FIN-DES07 | Estorno de despesa paga: POST /api/v1/financeiro/despesas/{id}/estornar/ — restrito a ADMIN. | Alta |
| RF-FIN-DES08 | Estorno marca estornado=True em AMBOS os lancamentos: original e estorno. | Alta |
| RF-FIN-DES09 | Upload de comprovante (FileField, upload_to='despesas/'). | Media |
| RF-FIN-DES10 | Exclusao: soft delete (is_active=False). | Alta |

---

## Modulo: Financeiro — Livro Caixa

| ID | Requisito | Prioridade |
|---|---|---|
| RF-FIN-LC01 | LivroCaixa e imutavel via API publica: ReadCreateViewSet (sem PUT/PATCH/DELETE). | Alta |
| RF-FIN-LC02 | Cada lancamento registra: conta, tipo, origem, origem_id, valor, data, saldo_anterior, saldo_atual. | Alta |
| RF-FIN-LC03 | A cada novo lancamento: reconstruir cadeia de saldos da conta em transaction.atomic() com pg_advisory_xact_lock. | Alta |
| RF-FIN-LC04 | Endpoint de totais: GET /api/v1/financeiro/livro-caixa/totais/. | Alta |
| RF-FIN-LC05 | Estorno de lancamento manual: POST /api/v1/financeiro/livro-caixa/{id}/estornar/ — restrito a ADMIN. | Alta |
| RF-FIN-LC06 | Lancamentos com estornado=True excluidos dos calculos de saldo e relatorios. | Alta |

---

## Modulo: Financeiro — Relatorios e Dashboard

| ID | Requisito | Prioridade |
|---|---|---|
| RF-FIN-REL01 | Fluxo de Caixa mensal: GET /api/v1/financeiro/fluxo-caixa/?mes=YYYY-MM. | Alta |
| RF-FIN-REL02 | DRE anual com breakdown mensal: GET /api/v1/financeiro/dre/?ano=YYYY. | Alta |
| RF-FIN-REL03 | DRE separa: receita operacional, receita financeira, descontos, despesas fixas, variaveis, prolabore, impostos, EBITDA. | Alta |
| RF-FIN-REL04 | Balanco Patrimonial: GET /api/v1/financeiro/balanco/. | Alta |
| RF-FIN-REL05 | Balanco garante equacao Ativo = Passivo + PL com campo equacao_ok. | Alta |
| RF-FIN-REL06 | Fluxo Projetado 90 dias: GET /api/v1/financeiro/fluxo-projetado/. | Alta |
| RF-FIN-REL07 | Indicadores CFO: GET /api/v1/financeiro/indicadores/ — margem liquida, ponto de equilibrio, ticket medio, MRR, runway em meses, variacao mensal e anual. | Alta |
| RF-FIN-REL08 | Dashboard consolidado: GET /api/v1/financeiro/dashboard/. | Alta |
| RF-FIN-REL09 | Inferencia de categoria por descricao: POST /api/v1/financeiro/inferir-categoria/. | Media |

---

## Modulo: Financeiro — Conciliacao Bancaria

| ID | Requisito | Prioridade |
|---|---|---|
| RF-FIN-CONC01 | Upload de extrato PDF via multipart/form-data: POST /api/v1/financeiro/conciliacoes/upload/. | Alta |
| RF-FIN-CONC02 | Extracao de texto via pdftotext (poppler-utils no container). | Alta |
| RF-FIN-CONC03 | Parsers implementados: C6 e BTG. Stubs: Nubank, Inter, Caixa, Itau. | Alta |
| RF-FIN-CONC04 | Parser selecionado pelo nome da conta (substring, case-insensitive). | Alta |
| RF-FIN-CONC05 | Matching em 3 camadas: (1) data+valor+tipo +-1 dia; (2) auto: assenta pendentes/atrasados; (3) auto: cria por PadraoSeguroConciliacao. | Alta |
| RF-FIN-CONC06 | NUNCA criar lancamento automatico sem padrao aprovado. Ambiguidade resulta em FALTANDO_SISTEMA. | Alta |
| RF-FIN-CONC07 | Listar conciliacoes: GET /api/v1/financeiro/conciliacoes/. | Alta |
| RF-FIN-CONC08 | Listar itens: GET /api/v1/financeiro/conciliacoes/{id}/itens/. | Alta |
| RF-FIN-CONC09 | Confirmar item: POST /api/v1/financeiro/conciliacoes/{id}/confirmar-item/. | Alta |
| RF-FIN-CONC10 | CRUD de padroes seguros: /api/v1/financeiro/padroes-conciliacao/. | Alta |

---

## Modulo: Vendas

| ID | Requisito | Prioridade |
|---|---|---|
| RF-VEN01 | CRUD de Orcamentos com numeracao ORC-YYYY-NNNN gerada automaticamente no save(). | Alta |
| RF-VEN02 | Status de orcamento: RASCUNHO, ENVIADO, APROVADO, REJEITADO, CANCELADO. | Alta |
| RF-VEN03 | CRUD de Pedidos com numeracao PED-YYYY-NNNN gerada automaticamente no save(). | Alta |
| RF-VEN04 | Pedido pode ser vinculado a um Orcamento (FK opcional). | Media |
| RF-VEN05 | Status de pedido: PENDENTE, CONFIRMADO, EM_PRODUCAO, ENTREGUE, CANCELADO. | Alta |
| RF-VEN06 | CRUD de ItemPedido com valor_total = quantidade * valor_unitario (calculado no save). | Alta |
| RF-VEN07 | Exclusao: soft delete (is_active=False). | Alta |

---

## Modulo: Pagamentos

| ID | Requisito | Prioridade |
|---|---|---|
| RF-PAG01 | CRUD de MetodoPagamento: PIX, BOLETO, CARTAO_CREDITO, CARTAO_DEBITO, DINHEIRO, OUTRO. | Alta |
| RF-PAG02 | CRUD de Cobrancas vinculadas a clientes. | Alta |
| RF-PAG03 | Status de cobranca: PENDENTE, PAGO, CANCELADO, ATRASADO. | Alta |
| RF-PAG04 | Cobranca suporta upload de comprovante (FileField, upload_to='comprovantes/'). | Media |
| RF-PAG05 | CRUD de Parcelas vinculadas a Cobrancas. | Alta |
| RF-PAG06 | Status de parcela: PENDENTE, PAGO, CANCELADO. | Alta |
| RF-PAG07 | Exclusao: soft delete (is_active=False). | Alta |

---

## Modulo: Administrativo

| ID | Requisito | Prioridade |
|---|---|---|
| RF-ADM01 | CRUD de TipoDocumento com nome unico. | Media |
| RF-ADM02 | CRUD de Documento com upload de arquivo (FileField, upload_to='docs/'). | Alta |
| RF-ADM03 | Documento pode ser associado opcionalmente a um cliente. | Media |
| RF-ADM04 | Status de documento: RASCUNHO, VIGENTE, EXPIRADO, CANCELADO. | Alta |
| RF-ADM05 | Exclusao: soft delete (is_active=False). | Alta |

---

## Modulo: RH

| ID | Requisito | Prioridade |
|---|---|---|
| RF-RH01 | CRUD de Cargos com salario_base (DecimalField). | Alta |
| RF-RH02 | CRUD de Funcionarios com CPF unico (apenas digitos, sem mascara). | Alta |
| RF-RH03 | Regime do funcionario: CLT, PJ, ESTAGIO, SOCIO. | Alta |
| RF-RH04 | CRUD de FolhaPagamento com salario_liquido = bruto - descontos (calculado no save). | Alta |
| RF-RH05 | Status de folha: ABERTA, FECHADA, PAGA. | Alta |
| RF-RH06 | mes_referencia armazena o primeiro dia do mes. | Alta |
| RF-RH07 | CRUD de RegistroFerias com dias = (data_fim - data_inicio).days (calculado no save). | Alta |
| RF-RH08 | Status de ferias: AGENDADO, EM_ANDAMENTO, CONCLUIDO. | Alta |
| RF-RH09 | Exclusao: soft delete (is_active=False). | Alta |

---

## Modulo: Agendamento

| ID | Requisito | Prioridade |
|---|---|---|
| RF-AGE01 | CRUD de Agendas com cor hex customizavel (default #3B82F6). | Alta |
| RF-AGE02 | CRUD de Compromissos com campos inicio e fim (DateTimeField). | Alta |
| RF-AGE03 | Compromisso pode ser vinculado opcionalmente a um cliente. | Media |
| RF-AGE04 | Status: AGENDADO, CONFIRMADO, CANCELADO, CONCLUIDO. | Alta |
| RF-AGE05 | Validacao no serializer: fim deve ser >= inicio. | Alta |
| RF-AGE06 | Exclusao: soft delete (is_active=False). | Alta |

---

## Modulo: Portal do Cliente

| ID | Requisito | Prioridade |
|---|---|---|
| RF-POR01 | Vincular accounts.User a clientes.Cliente via AcessoPortalCliente (OneToOneField por usuario). | Alta |
| RF-POR02 | Acesso pode ser desativado (ativo=False) sem exclusao do registro. | Alta |
| RF-POR03 | Campo ultimo_acesso somente leitura, atualizado pelo sistema. | Media |
| RF-POR04 | AcessoPortalCliente nao herda BaseModel. Possui campos proprios: ativo, criado_em. | Alta |
