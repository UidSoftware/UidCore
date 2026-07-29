# 08 — Glossario
**Sistema:** UidCore — Template Financeiro Multi-Nicho
**Versao:** 1.0 (baseline AS-IS em producao)
**Data:** 2026-07-28

---

## Termos do Dominio Financeiro

**Aporte**
Entrada de capital externo no negocio. Pode ser de socio, investidor, capital social ou emprestimo. NAO e receita operacional — vai para Patrimonio Liquido ou Passivo Exigivel no Balanco.

**Balanco Patrimonial**
Demonstrativo financeiro que apresenta Ativo, Passivo e Patrimonio Liquido (PL) em um momento especifico. A equacao fundamental: Ativo = Passivo + PL. O UidCore calcula e indica se a equacao fecha (campo equacao_ok).

**CFO as a Service**
Proposta de valor do UidCore: fornecer ao MEI e pequena empresa as funcionalidades de um Chief Financial Officer (diretor financeiro) — DRE, Balanco, Fluxo Projetado e Indicadores — sem precisar contratar um profissional especializado.

**Conciliacao Bancaria**
Processo de comparar os lancamentos registrados no sistema com os lancamentos do extrato bancario real, identificando divergencias (o que esta no banco e nao esta no sistema, e vice-versa).

**DRE (Demonstrativo de Resultado do Exercicio)**
Relatorio que mostra receitas, custos e despesas em um periodo, resultando no lucro ou prejuizo. O UidCore gera o DRE anual com breakdown mensal, separando receita operacional, receita financeira, despesas fixas, variaveis, prolabore e impostos.

**EBITDA**
Earnings Before Interest, Taxes, Depreciation and Amortization — lucro antes de juros, impostos, depreciacao e amortizacao. Indicador de eficiencia operacional calculado nos Indicadores CFO do sistema.

**Estorno**
Operacao que cancela um lancamento financeiro ja efetivado. No UidCore, estorno e sempre em par: o lancamento original e o lancamento de estorno sao AMBOS marcados com estornado=True. Acesso restrito a ADMIN.

**Fluxo de Caixa**
Registro cronologico de todas as entradas e saidas de dinheiro de uma conta. No UidCore, e representado pelo LivroCaixa.

**Fluxo Projetado**
Estimativa de entradas e saidas para os proximos 90 dias, calculada com base em receitas/despesas pendentes e recorrentes cadastradas no sistema.

**FALTANDO_SISTEMA**
Status de um ItemConciliacao que indica que a transacao esta no extrato bancario mas nao tem correspondencia no LivroCaixa do sistema. Requer confirmacao manual do ADMIN.

**Livro Caixa (LivroCaixa)**
Registro imutavel de todos os lancamentos financeiros do sistema. Cada lancamento registra: conta, tipo (ENTRADA/SAIDA), origem, valor, data, saldo_anterior e saldo_atual. Nenhum lancamento pode ser editado ou excluido — apenas estornado via action dedicada.

**MRR (Monthly Recurring Revenue)**
Receita recorrente mensal. Calculado nos Indicadores CFO com base em receitas do tipo MENSALIDADE.

**Padrao Seguro de Conciliacao**
Regra cadastrada pelo ADMIN para automatizar a criacao de lancamentos durante a conciliacao bancaria. Um padrao define: texto de correspondencia, tipo (ENTRADA/SAIDA) e natureza (APORTE ou RECEITA_FINANCEIRA). So e aplicado automaticamente apos aprovacao explicita.

**Patrimonio Liquido (PL)**
Diferenca entre Ativo e Passivo. Representa o valor pertencente aos socios. Aportes de socio, capital social e investidores aumentam o PL.

**Passivo Exigivel LP**
Obrigacoes de longo prazo da empresa, como emprestimos. Aportes do tipo EMPRESTIMO vao para esta categoria no Balanco.

**Ponto de Equilibrio**
Valor de receita necessario para cobrir todas as despesas sem lucro nem prejuizo. Calculado nos Indicadores CFO.

**Runway**
Quantidade de meses que o negocio pode operar sem nova receita, dado o saldo atual e a taxa de queima mensal. Calculado nos Indicadores CFO.

**Ticket Medio**
Valor medio por transacao/venda. Calculado nos Indicadores CFO.

---

## Termos Tecnicos do Sistema

**Advisory Lock (pg_advisory_xact_lock)**
Mecanismo do PostgreSQL para lock a nivel de aplicacao. No UidCore, usado por conta_id em operacoes de LivroCaixa para evitar race conditions quando dois usuarios salvam lancamentos na mesma conta simultaneamente.

**BaseModel**
Classe abstrata Django em common/models.py que adiciona created_at, updated_at e is_active a todos os models do sistema. Todos os models herdam BaseModel, com excecao de AcessoPortalCliente e modelos de conciliacao que possuem campos proprios.

**ISV (Independent Software Vendor)**
Modelo de negocio da Uid Software: desenvolve um produto de software (UidCore) e o revende adaptado para diferentes nichos de mercado, sem precisar reconstruir do zero para cada cliente.

**PessoaBase**
Classe abstrata que estende BaseModel com campos comuns a pessoas fisicas e juridicas (documento, nome_razao_social, telefone, email, endereco, etc.). Herdada por Cliente e Fornecedor.

**ReadCreateViewSet**
ViewSet customizado do DRF que permite apenas GET (listar e detalhar) e POST (criar). Usado no LivroCaixa para garantir imutabilidade dos lancamentos.

**Reconstrucao da Cadeia de Saldos (_reconstruir_cadeia)**
Processo que recalcula saldo_anterior e saldo_atual de TODOS os lancamentos de uma conta em ordem cronologica. Executado a cada nova escrita no LivroCaixa, dentro de transaction.atomic() com advisory lock.

**Soft Delete**
Padrao de exclusao logica: em vez de remover o registro do banco, seta is_active=False. Listagens filtram is_active=True por padrao. Garante historico completo e possibilidade de recuperacao.

**Signal (Django Signals)**
Mecanismo do Django para executar codigo automaticamente apos eventos (ex: post_save). No UidCore, signals em Receita, Despesa e Aporte criam lancamentos no LivroCaixa quando o status muda para RECEBIDO ou PAGO. Os signals sao idempotentes: verificam existencia do lancamento antes de criar.

**Transaction.atomic()**
Contexto do Django que envolve operacoes de banco em uma transacao atomica — ou tudo e executado, ou nada e. Usado em todas as operacoes criticas de LivroCaixa.

---

## Termos dos Perfis de Acesso

**ADMIN**
Usuario com is_staff=True. Acesso completo ao sistema, incluindo aportes, estornos e gerenciamento do portal do cliente.

**OPERACIONAL**
Usuario autenticado com is_staff=False. Acesso a CRUD padrao de todos os modulos, sem aportes ou estornos.

**CLIENTE**
Usuario vinculado a um registro de Cliente via AcessoPortalCliente com ativo=True. Perfil para o portal do cliente. Telas proprias a serem implementadas por nicho.

---

## Abreviacoes

| Abreviacao | Significado |
|---|---|
| CRUD | Create, Read, Update, Delete |
| DRE | Demonstrativo de Resultado do Exercicio |
| DRF | Django REST Framework |
| FK | Foreign Key (chave estrangeira) |
| JWT | JSON Web Token |
| MEI | Microempreendedor Individual |
| MRR | Monthly Recurring Revenue |
| PF | Pessoa Fisica |
| PJ | Pessoa Juridica |
| PL | Patrimonio Liquido |
| RF | Requisito Funcional |
| RN | Regra de Negocio |
| RNF | Requisito Nao Funcional |
| UF | Unidade Federativa (estado brasileiro) |
