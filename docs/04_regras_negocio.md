# 04 — Regras de Negocio
**Sistema:** UidCore — Template Financeiro Multi-Nicho
**Versao:** 1.0 (baseline AS-IS em producao)
**Data:** 2026-07-28
**Referencia:** Levantamento_Requisitos.md / CLAUDE.md do projeto

---

## RN001 — LivroCaixa e Imutavel

**Modulo:** Financeiro — Livro Caixa
**Origem:** RF-FIN-LC01
**Descricao:** O LivroCaixa e imutavel via API publica. Nenhum lancamento pode ser editado ou excluido diretamente. A unica forma de correcao e o estorno via action dedicada.
**Condicao:** Toda escrita no LivroCaixa passa por ReadCreateViewSet — PUT, PATCH e DELETE retornam 405.
**Excecoes:** Estorno via POST /api/v1/financeiro/livro-caixa/{id}/estornar/ — disponivel apenas para ADMIN.
**Impacto se violada:** Historico financeiro perde rastreabilidade. Auditorias e relatorios ficam inconsistentes.

---

## RN002 — Reconstrucao da Cadeia de Saldos

**Modulo:** Financeiro — Livro Caixa
**Origem:** RF-FIN-LC03
**Descricao:** A cada novo lancamento no LivroCaixa, o sistema deve recalcular saldo_anterior e saldo_atual de TODOS os lancamentos da conta, em ordem cronologica, via _reconstruir_cadeia().
**Condicao:** Executado dentro de transaction.atomic() com pg_advisory_xact_lock por conta_id, garantindo atomicidade e evitando race conditions.
**Excecoes:** Nenhuma — toda operacao que escreve no LivroCaixa dispara a reconstrucao.
**Impacto se violada:** Saldos divergentes entre lancamentos. Balanco Patrimonial e Fluxo de Caixa incorretos.

---

## RN003 — Estorno em Par Obrigatorio

**Modulo:** Financeiro — Livro Caixa, Despesas
**Origem:** RF-FIN-DES08, RF-FIN-LC05
**Descricao:** Ao estornar um lancamento, DOIS registros devem ser marcados com estornado=True: o lancamento original e o lancamento de estorno criado como contraparte.
**Condicao:** Valido tanto para estorno de Despesa quanto para estorno de lancamento manual no LivroCaixa.
**Excecoes:** Nenhuma.
**Impacto se violada:** O lancamento de estorno dobra o efeito no saldo em vez de neutraliza-lo. DRE e Balanco ficam errados.

---

## RN004 — Cartao de Credito e uma Conta

**Modulo:** Financeiro — Contas
**Origem:** RN04 (Levantamento_Requisitos.md)
**Descricao:** Cartao de credito deve ser modelado como uma Conta com tipo=CARTEIRA, nao como lancamento direto de Despesa. Compras no cartao sao lancadas nessa conta. O pagamento da fatura e uma transferencia entre contas.
**Condicao:** Toda vez que um cliente usar cartao de credito.
**Excecoes:** Nenhuma.
**Impacto se violada:** Gasto lancado diretamente na conta bancaria sem passar pelo cartao resulta em dupla contagem quando a fatura e paga.

---

## RN005 — Cartao com Garantia CDB: 3 Contas Encadeadas

**Modulo:** Financeiro — Contas
**Origem:** CLAUDE.md do projeto (secao Complemento: cartao com garantia)
**Descricao:** Quando o cartao do cliente tem limite por garantia (ex: CDB em banco digital), usar 3 contas encadeadas:
  - Conta Corrente (tipo CORRENTE)
  - Aplicacao/Garantia (tipo POUPANCA)
  - Cartao (tipo CARTEIRA)
Cada movimentacao entre elas e uma Transferencia, nunca uma Despesa.
**Condicao:** Qualquer cliente com cartao cujo limite e garantido por saldo aplicado.
**Excecoes:** Nenhuma.
**Impacto se violada:** O dinheiro aplicado como garantia "some" do sistema — nenhuma tela mostra o saldo disponivel na aplicacao.

---

## RN006 — Transferencia entre Bolsos Nao e Despesa nem Receita

**Modulo:** Financeiro — Contas, Receitas, Despesas
**Origem:** RF-FIN-CON04 / RN06
**Descricao:** Transferencia entre contas do mesmo titular (ex: conta corrente para aplicacao/CDB, liquidez D+0/D+1) NAO e despesa nem receita — nao deve entrar no DRE. O lancamento de LivroCaixa continua registrado (tipo TRANSFER). Se uma Despesa ou Receita for criada para representar esse movimento, ela deve ter is_active=False para nao duplicar no DRE.
**Condicao:** Qualquer movimentacao de saldo entre bolsos sem saida de patrimonio.
**Excecoes:** Nenhuma.
**Impacto se violada:** Saldo total correto, mas DRE mostra despesas/receitas que nao existem.

---

## RN007 — Aporte de Socio Nao e Receita

**Modulo:** Financeiro — Aportes
**Origem:** RF-FIN-APO04 / RN07
**Descricao:** Aporte de socio (tipos CAPITAL_SOCIAL, SOCIO, INVESTIDOR) vai para Patrimonio Liquido no Balanco, nao para o DRE como receita. Rendimento de aplicacao financeira e RECEITA_FINANCEIRA e entra no DRE separado da receita operacional. Aporte do tipo EMPRESTIMO vai para Passivo Exigivel LP.
**Condicao:** Todo novo aporte cadastrado no sistema.
**Excecoes:** EMPRESTIMO segue regra propria (Passivo, nao PL).
**Impacto se violada:** DRE infla receitas com aportes que sao patrimonio, distorcendo margem e EBITDA.

---

## RN008 — Gasto em Moeda Estrangeira Nao Tem Recorrencia

**Modulo:** Financeiro — Despesas
**Origem:** RN08 (Levantamento_Requisitos.md)
**Descricao:** Despesas pagas em moeda estrangeira (ex: USD em SaaS internacional) NUNCA devem usar os campos recorrente/frequencia/quantidade. O cambio varia a cada mes; o lancamento deve ser feito com o valor real da fatura em BRL quando ela chegar.
**Condicao:** Toda despesa cujo valor depende de cotacao de cambio.
**Excecoes:** Nenhuma.
**Impacto se violada:** Sistema projeta valor errado no Fluxo Projetado de 90 dias, causando planejamento incorreto.

---

## RN009 — Idempotencia dos Signals de LivroCaixa

**Modulo:** Financeiro — Livro Caixa
**Origem:** RN09 (Levantamento_Requisitos.md)
**Descricao:** Os signals que criam lancamentos no LivroCaixa devem verificar existencia de lancamento com mesmo origem+origem_id antes de criar. Isso previne duplicatas em casos de retry ou reexecucao de signal.
**Condicao:** Toda vez que post_save dispara para Receita (status RECEBIDO), Despesa (status PAGO) ou Aporte.
**Excecoes:** Nenhuma.
**Impacto se violada:** Duplicatas no LivroCaixa resultam em saldo dobrado e DRE incorreto.

---

## RN010 — Numeracao de Orcamentos e Pedidos e Imutavel

**Modulo:** Vendas
**Origem:** RF-VEN01, RF-VEN03
**Descricao:** O numero do orcamento (ORC-YYYY-NNNN) e do pedido (PED-YYYY-NNNN) e gerado automaticamente no primeiro save(). Uma vez gerado, e imutavel — nao pode ser alterado.
**Condicao:** save() sem numero gerado dispara geracao automatica.
**Excecoes:** Nenhuma.
**Impacto se violada:** Numeros duplicados ou inconsistentes causam problemas em referencias comerciais com clientes.

---

## RN011 — Conciliacao Bancaria Nunca e Automatica sem Padrao Aprovado

**Modulo:** Financeiro — Conciliacao Bancaria
**Origem:** RF-FIN-CONC06
**Descricao:** O sistema NUNCA deve criar lancamento no LivroCaixa automaticamente para transacoes do extrato que nao possuem correspondencia direta E nao tem PadraoSeguroConciliacao aprovado. Transacoes sem padrao ficam com status FALTANDO_SISTEMA para revisao manual do ADMIN.
**Condicao:** Flag auto=True no upload do extrato. Mesmo com auto=True, ambiguidade = FALTANDO_SISTEMA.
**Excecoes:** Nenhuma.
**Impacto se violada:** Lancamentos incorretos no LivroCaixa que podem ser dificeis de rastrear e corrigir.

---

## RN012 — Natureza dos Padroes Seguros de Conciliacao

**Modulo:** Financeiro — Conciliacao Bancaria
**Origem:** RN12 (Levantamento_Requisitos.md)
**Descricao:** O campo natureza do PadraoSeguroConciliacao determina onde o lancamento automatico vai: APORTE vai para Patrimonio Liquido no Balanco; RECEITA_FINANCEIRA entra no DRE.
**Condicao:** Toda vez que a Camada 3 do matching cria um lancamento via padrao seguro.
**Excecoes:** Nenhuma.
**Impacto se violada:** Rendimentos de aplicacao classificados como aporte inflam o PL sem passar pelo DRE.

---

## RN013 — Saldo Calculado por Soma Agregada

**Modulo:** Financeiro — Livro Caixa
**Origem:** RN13 (Levantamento_Requisitos.md)
**Descricao:** O saldo real de uma conta e calculado via _saldo_real() por soma agregada de todos os lancamentos nao estornados. Lancamentos inseridos retroativamente (data passada) exigem execucao de _reconstruir_cadeia() para corrigir saldo_anterior e saldo_atual de todos os lancamentos posteriores.
**Condicao:** Qualquer insercao de lancamento com data anterior ao ultimo lancamento da conta.
**Excecoes:** Nenhuma.
**Impacto se violada:** saldo_anterior e saldo_atual exibidos na tela de LivroCaixa ficam incorretos ate a proxima reconstrucao.

---

## RN014 — Perfis de Acesso por Operacao

**Modulo:** Todos
**Origem:** Secao 6 do Levantamento_Requisitos.md
**Descricao:**
- ADMIN (is_staff=True): acesso completo, incluindo registrar aportes, estornar despesas e lancamentos do LivroCaixa, gerenciar acesso ao portal.
- OPERACIONAL (autenticado, is_staff=False): acesso a CRUD padrao de todos os modulos. NAO pode acessar AporteViewSet nem acoes de estorno.
- CLIENTE (AcessoPortalCliente.ativo=True): vinculado a um cliente. Acesso apenas ao portal do cliente (telas a serem implementadas por nicho).
**Condicao:** Toda requisicao autenticada.
**Excecoes:** Endpoints publicos: /api/v1/auth/token/, /api/v1/auth/token/refresh/, /api/v1/accounts/register/.
**Impacto se violada:** Usuario OPERACIONAL consegue estornar lancamentos ou registrar aportes indevidamente.

---

## RN015 — Soft Delete Obrigatorio

**Modulo:** Todos
**Origem:** RNF03
**Descricao:** Nenhum registro deve ser excluido fisicamente do banco. A exclusao sempre seta is_active=False. Listagens filtram is_active=True por padrao.
**Condicao:** Toda operacao DELETE via API.
**Excecoes:** AcessoPortalCliente usa campo proprio ativo=False (divergencia DIV04 conhecida).
**Impacto se violada:** Perda permanente de dados historicos. Violacao de trilha de auditoria.
