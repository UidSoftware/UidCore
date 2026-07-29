# 05 — Modelo de Dados
**Sistema:** UidCore — Template Financeiro Multi-Nicho
**Versao:** 1.0 (baseline AS-IS em producao)
**Data:** 2026-07-28
**Referencia:** classes.md / Levantamento_Requisitos.md

---

## BaseModel (common/models.py)

Classe abstrata herdada por todos os models do sistema, exceto AcessoPortalCliente.

| Campo | Tipo | Descricao |
|---|---|---|
| created_at | DateTimeField (auto_now_add) | Data/hora de criacao |
| updated_at | DateTimeField (auto_now) | Data/hora da ultima atualizacao |
| is_active | BooleanField (default=True) | Soft delete — False = excluido logicamente |

Regra: NUNCA chamar .delete() em models que herdam BaseModel. Setar is_active=False.

---

## PessoaBase (common/models.py)

Classe abstrata que estende BaseModel. Herdada por Cliente e Fornecedor.

| Campo | Tipo | Descricao |
|---|---|---|
| tipo_pessoa | CharField | PF ou PJ |
| documento | CharField (unique) | CPF (PF) ou CNPJ (PJ) sem mascara |
| nome_razao_social | CharField | Nome (PF) ou Razao Social (PJ) |
| telefone | CharField | Telefone de contato |
| email | EmailField | Email de contato |
| endereco | CharField | Logradouro e numero |
| cidade | CharField | Cidade |
| estado | CharField (2) | UF |
| cep | CharField | CEP sem mascara |
| observacoes | TextField | Campo livre |

---

## App: accounts

### Model: User (CustomUser)

Estende AbstractBaseUser. Nao herda BaseModel.

| Campo | Tipo | Descricao |
|---|---|---|
| email | EmailField (unique) | Campo de autenticacao — USERNAME_FIELD |
| nome_completo | CharField | Nome completo do usuario |
| telefone | CharField | Telefone |
| is_active | BooleanField | Controle de acesso |
| is_staff | BooleanField | True = perfil ADMIN |
| date_joined | DateTimeField | Data de cadastro |

**Perfis:** is_staff=True -> ADMIN; is_staff=False -> OPERACIONAL.

---

## App: clientes

### Model: Cliente

Herda PessoaBase (que herda BaseModel).

| Campo | Tipo | Descricao |
|---|---|---|
| segmento | CharField | COMERCIO, SERVICOS, INDUSTRIA, SAUDE, EDUCACAO, TECNOLOGIA, ALIMENTACAO, OUTRO |
| data_nascimento | DateField | Data de nascimento (PF) |
| origem | CharField | Como o cliente chegou |
| limite_credito | DecimalField(12,2) | Limite de credito concedido |

**Relacionamentos:**
- Tem muitos: HistoricoCliente
- Tem muitos: Receita (FK opcional)
- Tem muitos: Orcamento (FK opcional)
- Tem muitos: Pedido (FK opcional)
- Tem muitos: Cobranca (FK opcional)
- Tem muitos: Documento (FK opcional)
- Tem muitos: Compromisso (FK opcional)

### Model: HistoricoCliente

Nao herda BaseModel diretamente.

| Campo | Tipo | Descricao |
|---|---|---|
| cliente | FK -> Cliente | Cliente ao qual pertence o historico |
| descricao | TextField | Descricao da interacao |
| data | DateTimeField | Data/hora da interacao |

---

## App: fornecedores

### Model: Fornecedor

Herda PessoaBase (que herda BaseModel).

| Campo | Tipo | Descricao |
|---|---|---|
| categoria | CharField | MATERIA_PRIMA, SERVICOS, TECNOLOGIA, LOGISTICA, MANUTENCAO, ESCRITORIO, MARKETING, OUTRO |
| contato_nome | CharField | Nome do contato |
| contato_telefone | CharField | Telefone do contato |
| website | URLField | Site do fornecedor |
| inscricao_estadual | CharField | IE (opcional) |

---

## App: financeiro

### Model: Conta

Herda BaseModel.

| Campo | Tipo | Descricao |
|---|---|---|
| nome | CharField | Nome da conta |
| tipo | CharField | CORRENTE, POUPANCA, CAIXA, CARTEIRA |
| banco | CharField | Nome do banco |
| agencia | CharField | Numero da agencia |
| numero | CharField | Numero da conta |
| saldo_inicial | DecimalField(12,2) | Saldo na abertura da conta no sistema |
| criado_por | FK -> User | Usuario que criou |

**Relacionamentos:**
- Tem muitos: Aporte
- Tem muitos: Receita
- Tem muitos: Despesa
- Tem muitos: LivroCaixa
- Tem muitos: ConciliacaoExtrato

### Model: Aporte

Herda BaseModel. Acesso restrito a ADMIN.

| Campo | Tipo | Descricao |
|---|---|---|
| tipo | CharField | CAPITAL_SOCIAL, SOCIO, INVESTIDOR, EMPRESTIMO |
| descricao | CharField | Descricao do aporte |
| valor | DecimalField(12,2) | Valor aportado |
| conta | FK -> Conta | Conta de destino do aporte |
| data | DateField | Data do aporte |
| responsavel | CharField | Nome do responsavel |
| observacoes | TextField | Campo livre |
| criado_por | FK -> User | Usuario que registrou |

Regra: signal post_save cria lancamento ENTRADA no LivroCaixa automaticamente. EMPRESTIMO vai para Passivo Exigivel LP no Balanco; demais vao para PL.

### Model: Categoria

Herda BaseModel.

| Campo | Tipo | Descricao |
|---|---|---|
| nome | CharField | Nome da categoria |
| tipo | CharField | ENTRADA ou SAIDA |

Restricao: unique_together (nome, tipo).

### Model: Receita

Herda BaseModel.

| Campo | Tipo | Descricao |
|---|---|---|
| tipo | CharField | SERVICO, PRODUTO, MENSALIDADE, RECEITA_FINANCEIRA, OUTRO |
| descricao | CharField | Descricao da receita |
| cliente | FK -> Cliente (nullable) | Cliente associado |
| categoria | FK -> Categoria (nullable) | Categoria contabil |
| valor_bruto | DecimalField(12,2) | Valor bruto |
| desconto | DecimalField(12,2) | Desconto concedido |
| valor_liquido | DecimalField(12,2) | Calculado: bruto - desconto (editable=False) |
| conta | FK -> Conta | Conta de recebimento |
| vencimento | DateField | Data de vencimento |
| recebimento | DateField | Data efetiva de recebimento |
| status | CharField | PENDENTE, RECEBIDO, CANCELADO, ATRASADO |
| referencia_mes | DateField | Mes de competencia |
| observacoes | TextField | Campo livre |
| criado_por | FK -> User | Usuario que criou |

Regra: ao mudar status para RECEBIDO via /receber/, signal cria lancamento ENTRADA no LivroCaixa. is_active=False exclui do DRE e Balanco.

### Model: Despesa

Herda BaseModel.

| Campo | Tipo | Descricao |
|---|---|---|
| tipo | CharField | FIXA, VARIAVEL, PROLABORE, IMPOSTO, OUTRO |
| descricao | CharField | Descricao da despesa |
| fornecedor | CharField | Nome do fornecedor (campo texto, nao FK) |
| valor_bruto | DecimalField(12,2) | Valor bruto |
| desconto | DecimalField(12,2) | Desconto |
| valor_liquido | DecimalField(12,2) | Calculado: bruto - desconto (editable=False) |
| conta | FK -> Conta | Conta de pagamento |
| categoria | FK -> Categoria (nullable) | Categoria contabil |
| vencimento | DateField | Data de vencimento |
| pagamento | DateField | Data efetiva de pagamento |
| forma_pagamento | CharField | Forma de pagamento |
| status | CharField | PENDENTE, PAGO, CANCELADO, ATRASADO |
| referencia_mes | DateField | Mes de competencia |
| comprovante | FileField (upload_to='despesas/') | Comprovante de pagamento |
| observacoes | TextField | Campo livre |
| recorrente | BooleanField | Flag de recorrencia |
| frequencia | CharField | MENSAL, ANUAL etc. |
| quantidade | PositiveIntegerField | Numero de recorrencias |
| estornado | BooleanField | True se estornado |
| data_estorno | DateField | Data do estorno |
| motivo_estorno | TextField | Motivo do estorno |
| criado_por | FK -> User | Usuario que criou |

Regra: ao mudar status para PAGO via /pagar/, signal cria lancamento SAIDA no LivroCaixa. Estorno restrito a ADMIN.

### Model: LivroCaixa

Herda BaseModel. Imutavel via API — ReadCreateViewSet.

| Campo | Tipo | Descricao |
|---|---|---|
| conta | FK -> Conta | Conta do lancamento |
| tipo | CharField | ENTRADA ou SAIDA |
| origem | CharField | APORTE, RECEITA, DESPESA, MANUAL, TRANSFER, ESTORNO |
| origem_id | PositiveIntegerField | ID do registro de origem |
| descricao | CharField | Descricao do lancamento |
| valor | DecimalField(12,2) | Valor do lancamento |
| data | DateField | Data do lancamento |
| saldo_anterior | DecimalField(12,2) | Saldo antes do lancamento |
| saldo_atual | DecimalField(12,2) | Saldo apos o lancamento |
| criado_em | DateTimeField | Timestamp de criacao |
| criado_por | FK -> User | Usuario que criou |
| estornado | BooleanField | True se estornado |
| estorno_de | FK -> self (nullable) | Referencia ao lancamento original estornado |

Regra: a cada novo lancamento, _reconstruir_cadeia() e executada com pg_advisory_xact_lock.

### Model: ConciliacaoExtrato

Herda BaseModel.

| Campo | Tipo | Descricao |
|---|---|---|
| conta | FK -> Conta | Conta conciliada |
| arquivo_nome | CharField | Nome do arquivo PDF enviado |
| periodo | DateField | Mes de referencia do extrato |
| processado_em | DateTimeField | Timestamp do processamento |
| status | CharField | PENDENTE, PROCESSADO, COM_DIVERGENCIAS |
| total_banco | DecimalField(12,2) | Total de movimentos no extrato bancario |
| total_sistema | DecimalField(12,2) | Total de movimentos no LivroCaixa |
| divergencias | IntegerField | Numero de itens divergentes |
| criado_por | FK -> User | Usuario que fez o upload |

### Model: ItemConciliacao

Nao herda BaseModel.

| Campo | Tipo | Descricao |
|---|---|---|
| conciliacao | FK -> ConciliacaoExtrato | Conciliacao pai |
| data_banco | DateField | Data da transacao no extrato |
| descricao_banco | CharField | Descricao da transacao no extrato |
| valor | DecimalField(12,2) | Valor da transacao |
| tipo | CharField | ENTRADA ou SAIDA |
| status | CharField | CONCILIADO, FALTANDO_SISTEMA, FALTANDO_BANCO |
| lancamento_lc | FK -> LivroCaixa (nullable) | Lancamento correspondente no sistema |
| confirmado | BooleanField | True se confirmado manualmente pelo ADMIN |

### Model: PadraoSeguroConciliacao

Nao herda BaseModel. Usa campo ativo proprio.

| Campo | Tipo | Descricao |
|---|---|---|
| descricao_padrao | CharField | Padrao de texto para matching |
| tipo | CharField | ENTRADA ou SAIDA |
| natureza | CharField | APORTE ou RECEITA_FINANCEIRA |
| ativo | BooleanField | Padrao ativo ou nao |
| criado_em | DateTimeField | Timestamp de criacao |
| criado_por | FK -> User | Usuario que criou |

---

## App: vendas

### Model: Orcamento

Herda BaseModel.

| Campo | Tipo | Descricao |
|---|---|---|
| numero | CharField | ORC-YYYY-NNNN (gerado no save, imutavel) |
| cliente | FK -> Cliente (nullable) | Cliente associado |
| descricao | TextField | Descricao do orcamento |
| valor_total | DecimalField(12,2) | Valor total |
| status | CharField | RASCUNHO, ENVIADO, APROVADO, REJEITADO, CANCELADO |
| validade | DateField | Data de validade |
| observacoes | TextField | Campo livre |
| criado_por | FK -> User | Usuario que criou |

### Model: Pedido

Herda BaseModel.

| Campo | Tipo | Descricao |
|---|---|---|
| numero | CharField | PED-YYYY-NNNN (gerado no save, imutavel) |
| cliente | FK -> Cliente (nullable) | Cliente associado |
| orcamento | FK -> Orcamento (nullable) | Orcamento de origem |
| status | CharField | PENDENTE, CONFIRMADO, EM_PRODUCAO, ENTREGUE, CANCELADO |
| valor_total | DecimalField(12,2) | Valor total |
| data_pedido | DateField | Data do pedido |
| data_entrega_prevista | DateField | Data prevista de entrega |
| observacoes | TextField | Campo livre |
| criado_por | FK -> User | Usuario que criou |

### Model: ItemPedido

Herda BaseModel.

| Campo | Tipo | Descricao |
|---|---|---|
| pedido | FK -> Pedido (nullable) | Pedido ao qual pertence |
| descricao | CharField | Descricao do item |
| quantidade | IntegerField | Quantidade |
| valor_unitario | DecimalField(12,2) | Valor unitario |
| valor_total | DecimalField(12,2) | Calculado: quantidade * valor_unitario (editable=False) |

---

## App: pagamentos

### Model: MetodoPagamento

Herda BaseModel.

| Campo | Tipo | Descricao |
|---|---|---|
| nome | CharField | PIX, BOLETO, CARTAO_CREDITO, CARTAO_DEBITO, DINHEIRO, OUTRO |
| ativo | BooleanField | Controle proprio (divergencia DIV05: dois booleanos) |

Observacao: MetodoPagamento possui campo ativo proprio ALEM do is_active herdado do BaseModel.

### Model: Cobranca

Herda BaseModel.

| Campo | Tipo | Descricao |
|---|---|---|
| cliente | FK -> Cliente (nullable) | Cliente cobrado |
| descricao | CharField | Descricao da cobranca |
| valor | DecimalField(12,2) | Valor total |
| vencimento | DateField | Data de vencimento |
| status | CharField | PENDENTE, PAGO, CANCELADO, ATRASADO |
| metodo | FK -> MetodoPagamento (nullable) | Metodo de pagamento |
| data_pagamento | DateField | Data efetiva de pagamento |
| comprovante | FileField (upload_to='comprovantes/') | Comprovante |
| observacoes | TextField | Campo livre |
| criado_por | FK -> User | Usuario que criou |

### Model: Parcela

Herda BaseModel.

| Campo | Tipo | Descricao |
|---|---|---|
| cobranca | FK -> Cobranca (nullable) | Cobranca pai |
| numero | IntegerField | Numero da parcela |
| valor | DecimalField(12,2) | Valor da parcela |
| vencimento | DateField | Data de vencimento |
| status | CharField | PENDENTE, PAGO, CANCELADO |
| data_pagamento | DateField | Data efetiva de pagamento |

---

## App: administrativo

### Model: TipoDocumento

Herda BaseModel.

| Campo | Tipo | Descricao |
|---|---|---|
| nome | CharField (unique) | Nome do tipo |
| descricao | TextField | Descricao do tipo |

### Model: Documento

Herda BaseModel.

| Campo | Tipo | Descricao |
|---|---|---|
| titulo | CharField | Titulo do documento |
| tipo | FK -> TipoDocumento (nullable) | Tipo do documento |
| arquivo | FileField (upload_to='docs/') | Arquivo em anexo |
| cliente | FK -> Cliente (nullable) | Cliente associado |
| descricao | TextField | Descricao |
| status | CharField | RASCUNHO, VIGENTE, EXPIRADO, CANCELADO |
| validade | DateField | Data de validade |
| criado_por | FK -> User | Usuario que criou |

---

## App: rh

### Model: Cargo

Herda BaseModel.

| Campo | Tipo | Descricao |
|---|---|---|
| nome | CharField (unique) | Nome do cargo |
| descricao | TextField | Descricao do cargo |
| salario_base | DecimalField(12,2) | Salario base da funcao |

### Model: Funcionario

Herda BaseModel.

| Campo | Tipo | Descricao |
|---|---|---|
| nome | CharField | Nome completo |
| cpf | CharField (unique) | CPF sem mascara |
| email | EmailField | Email do funcionario |
| cargo | FK -> Cargo (nullable) | Cargo atual |
| data_admissao | DateField | Data de admissao |
| data_demissao | DateField | Data de demissao (nullable) |
| salario_atual | DecimalField(12,2) | Salario atual |
| regime | CharField | CLT, PJ, ESTAGIO, SOCIO |
| observacoes | TextField | Campo livre |

### Model: FolhaPagamento

Herda BaseModel.

| Campo | Tipo | Descricao |
|---|---|---|
| funcionario | FK -> Funcionario (nullable) | Funcionario |
| mes_referencia | DateField | Primeiro dia do mes de referencia |
| salario_bruto | DecimalField(12,2) | Salario bruto do mes |
| descontos | DecimalField(12,2) | Total de descontos |
| salario_liquido | DecimalField(12,2) | Calculado: bruto - descontos (editable=False) |
| status | CharField | ABERTA, FECHADA, PAGA |
| observacoes | TextField | Campo livre |

### Model: RegistroFerias

Herda BaseModel.

| Campo | Tipo | Descricao |
|---|---|---|
| funcionario | FK -> Funcionario (nullable) | Funcionario |
| data_inicio | DateField | Inicio das ferias |
| data_fim | DateField | Fim das ferias |
| dias | IntegerField | Calculado: (data_fim - data_inicio).days (editable=False) |
| status | CharField | AGENDADO, EM_ANDAMENTO, CONCLUIDO |

---

## App: agendamento

### Model: Agenda

Herda BaseModel. Usa campo ativo proprio (divergencia DIV04).

| Campo | Tipo | Descricao |
|---|---|---|
| nome | CharField | Nome da agenda |
| descricao | TextField | Descricao |
| cor | CharField(7) | Cor em hex (default: #3B82F6) |
| ativo | BooleanField | Controle proprio |

### Model: Compromisso

Herda BaseModel.

| Campo | Tipo | Descricao |
|---|---|---|
| agenda | FK -> Agenda (nullable) | Agenda pai |
| titulo | CharField | Titulo do compromisso |
| descricao | TextField | Descricao |
| inicio | DateTimeField | Data/hora de inicio |
| fim | DateTimeField | Data/hora de fim |
| local | CharField | Local do compromisso |
| cliente | FK -> Cliente (nullable) | Cliente associado |
| status | CharField | AGENDADO, CONFIRMADO, CANCELADO, CONCLUIDO |
| observacoes | TextField | Campo livre |
| criado_por | FK -> User | Usuario que criou |

Restricao: serializer valida fim >= inicio.

---

## App: portal

### Model: AcessoPortalCliente

NAO herda BaseModel. Possui campos proprios.

| Campo | Tipo | Descricao |
|---|---|---|
| usuario | OneToOneField -> User | Usuario do sistema |
| cliente | FK -> Cliente (nullable) | Cliente vinculado |
| ativo | BooleanField | Controle de acesso (nao usa is_active) |
| ultimo_acesso | DateTimeField | Somente leitura, atualizado pelo sistema |
| criado_em | DateTimeField | Data de criacao do vinculo |

---

## Mapa de Relacionamentos (resumo)

```
User
  +-- (criado_por) --> Conta, Receita, Despesa, LivroCaixa, Aporte, Orcamento,
                        Pedido, Cobranca, Documento, ConciliacaoExtrato,
                        PadraoSeguroConciliacao, Compromisso
  +-- (OneToOne) --> AcessoPortalCliente

PessoaBase (abstrata)
  +-- Cliente
  +-- Fornecedor

Cliente --> HistoricoCliente, Receita, Orcamento, Pedido, Cobranca,
             Documento, Compromisso, AcessoPortalCliente

Conta --> Aporte, Receita, Despesa, LivroCaixa, ConciliacaoExtrato
Categoria --> Receita, Despesa
ConciliacaoExtrato --> ItemConciliacao
LivroCaixa --> ItemConciliacao, LivroCaixa (self — estorno_de)
Orcamento --> Pedido
Pedido --> ItemPedido
Cobranca --> Parcela
MetodoPagamento --> Cobranca
TipoDocumento --> Documento
Cargo --> Funcionario
Funcionario --> FolhaPagamento, RegistroFerias
Agenda --> Compromisso
```
