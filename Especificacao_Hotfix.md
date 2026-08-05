# Especificação Hotfix — Manutenção #15 — Módulo PDV (Ponto de Venda)

**Sistema:** UidCore
**Tipo:** `feature_grande` (aprovação comercial já concedida por Luiz Eduardo)
**Modo Analista:** manutenção — re-elicitação de escopo completo, com ênfase nos Pontos 2 e 3
**Data:** 2026-08-03

---

## 1. Contexto

O UidCore já opera com os módulos `financeiro` (Conta, Receita, Despesa, LivroCaixa,
Conciliação Bancária), `produtos` (Produto, ConversaoUnidade, EntradaEstoque),
`clientes` (Cliente) e `pagamentos` (MetodoPagamento, Cobranca, Parcela). O cliente
quer um módulo de **frente de caixa / PDV** para vender balcão com baixa de estoque
e geração automática de Receita/LivroCaixa.

Luiz Eduardo expandiu o escopo original em dois pontos que mudam a arquitetura
financeira do sistema e por isso foram re-elicitados a fundo nesta especificação:

- **Ponto 2** — devolução parcial de item vendido exige que `Receita` (que hoje
  **não tem nenhum mecanismo de estorno**, ao contrário de `Despesa`) ganhe um
  mecanismo de estorno — e, além disso, **parcial** (Despesa só suporta estorno
  total).
- **Ponto 3** — pagamento em cartão de crédito com taxa da maquininha e prazo de
  liquidação exige um novo fluxo de recebível que nasce `PENDENTE` e vira
  `RECEBIDO` só quando o valor líquido cair na conta, integrado à Conciliação
  Bancária já existente.

---

## 2. Achados críticos da leitura de código (antes de especificar)

Lidos: `backend/financeiro/models.py`, `views.py`, `relatorios.py`, `signals.py`,
`serializers.py`; `backend/produtos/models.py`; `backend/clientes/models.py`;
`backend/pagamentos/models.py`; `backend/vendas/models.py`; `backend/common/models.py`;
`backend/common/permissions.py`.

| # | Achado | Impacto no PDV |
|---|---|---|
| A1 | `Receita` **não tem** `estornado`/`data_estorno`/`motivo_estorno` — só `Despesa` tem, com action `estornar` em `DespesaViewSet` (linha 227) que estorna **sempre o valor total**. | Devolução parcial (Ponto 2) não tem onde se apoiar — precisa de mecanismo novo, e não pode ser cópia 1:1 do padrão de Despesa (que é tudo-ou-nada). Detalhado na Seção 5. |
| A2 | `calcular_dre_mes()` em `relatorios.py` filtra `Despesa` por `estornado=False` mas **não filtra `Receita` por nada equivalente** (porque o campo não existe) — todo `Receita.status=RECEBIDO` entra no DRE integralmente. | O DRE vai ficar incorreto assim que existir estorno de Receita, se `calcular_dre_mes` não for atualizado junto (ver Seção 5.5). Forge precisa tocar `relatorios.py`, não só `models.py`/`views.py`. |
| A3 | Já existe um app **`vendas`** em produção com `Orcamento`, `Pedido`, `ItemOrcamento`, `ItemPedido` (tabelas `vnd_*`). `Pedido`/`ItemPedido` **não** debitam estoque, **não** geram `Receita`/`LivroCaixa`, **não** têm sessão de caixa — é fluxo de encomenda/orçamento, propósito diferente do PDV (venda de balcão à vista com caixa aberto). | Não há duplicação funcional, mas é uma decisão de arquitetura em aberto: o PDV deve virar um app novo (`pdv`) ou viver dentro do app `vendas` junto de Orçamento/Pedido? **Repasso essa decisão para o Blueprint** — não decido arquitetura de pastas/apps aqui, só sinalizo o achado para não ser descoberto tarde. |
| A4 | `MetodoPagamento` (app `pagamentos`) é só um `choices` de nome — **não tem FK para `Conta`**. Não existe hoje nenhum "mapeamento forma de pagamento → conta" no sistema, apesar do briefing original pedir reaproveitamento desse mapeamento. | Esse mapeamento **não existe ainda** — é model novo (Seção 4, `PagamentoVenda.conta` resolvido no momento da venda, ou tabela de configuração `MetodoPagamento ↔ Conta` como Should — ver RF-14). |
| A5 | `IsAdmin` (`common/permissions.py`) = `request.user.is_staff`. Não há sistema de perfis dedicado nesta base (diferente do SystemD). O briefing pede "IsAdmin only" pro Relatório de Sessões — mapeia direto pra essa permission já existente, sem criar nada novo. | Confirma RN de permissões (Seção 11) sem necessidade de novo mecanismo. |
| A6 | Padrão de estorno de `Despesa`/`LivroCaixaViewSet.estornar` sempre roda dentro de `transaction.atomic()` + `pg_advisory_xact_lock(conta.id)` e termina com `_reconstruir_cadeia(conta)` — é o padrão de concorrência do sistema todo, inclusive a `transferir` de `ContaViewSet`. | PDV deve seguir **exatamente** esse padrão em: finalizar venda, cancelar venda, estornar item, abrir/fechar sessão (Seção 9). Forge não deve inventar outro mecanismo de lock. |
| A7 | `EntradaEstoque.save()` já resolve conversão de unidade (`ConversaoUnidade`) e faz `Produto.objects.filter(pk=...).update(quantidade_estoque=F('quantidade_estoque') + quantidade_base)` só em criação. | Baixa de estoque do PDV deve ser a operação **inversa** exata dessa lógica (mesma resolução de conversão, `F('quantidade_estoque') - quantidade_base`), não uma reimplementação paralela. Ver RF-06. |

---

## 3. Reaproveitamento confirmado (não duplicar)

- `produtos.Produto` (busca por nome/`codigo_barras`, `quantidade_estoque`, `unidade_base`, `preco_venda`) + `produtos.ConversaoUnidade` para conversão de unidade na baixa de estoque.
- `clientes.Cliente` — venda com ou sem cliente vinculado (Consumidor Final = `cliente=None`).
- `financeiro.Conta` (tipo `CAIXA`/`CORRENTE`/`CARTEIRA`) como destino dos lançamentos.
- `financeiro.Receita` + signal `receita_para_livro_caixa` — venda finalizada gera `Receita(status=RECEBIDO)` e o `LivroCaixa` nasce sozinho via signal existente, sem código novo de lançamento manual.
- `financeiro.LivroCaixa` + `_gerar_lancamento`/`_reconstruir_cadeia` (via signal, indiretamente).
- `pagamentos.MetodoPagamento` como catálogo de formas de pagamento no split.
- `financeiro.ConciliacaoExtrato`/`ItemConciliacao` — ponto de integração do Ponto 3 (Seção 6.3), não recriar conciliação.
- Padrão `IsAdmin` (`common/permissions.py`) para o Relatório de Sessões de Caixa.

---

## 4. Modelos novos (visão geral — detalhamento de estorno/recebível nas Seções 5 e 6)

### 4.1 `SessaoCaixa` (app a decidir com Blueprint — ver A3)
```
conta                        FK financeiro.Conta (tipo=CAIXA)
operador                     FK settings.AUTH_USER_MODEL
valor_abertura                DecimalField
data_abertura                 DateTimeField (auto_now_add)
data_fechamento               DateTimeField (null=True)
valor_fechamento_informado    DecimalField (null=True — contagem física)
valor_fechamento_calculado    DecimalField (null=True — abertura + vendas dinheiro - sangrias + suprimentos)
diferenca                     DecimalField (null=True — calculado - informado)
status                        CharField choices ABERTA/FECHADA, default ABERTA
observacoes                   TextField blank
(herda BaseModel: created_at, updated_at, is_active)
```
**RN-01:** unicidade de sessão `ABERTA` é **por `conta`**, não global — `UniqueConstraint`
condicional (`status='ABERTA'`) por `conta`, ou validação em `perform_create` +
`select_for_update` para evitar corrida entre dois operadores abrindo a mesma conta
ao mesmo tempo.

### 4.2 `MovimentoCaixa`
```
sessao      FK SessaoCaixa (related_name='movimentos')
tipo        CharField choices SANGRIA/SUPRIMENTO
valor       DecimalField
motivo      CharField/TextField (obrigatório)
operador    FK settings.AUTH_USER_MODEL
data_hora   DateTimeField (auto_now_add)
```
Sangria/Suprimento **não** passam por `Receita`/`Despesa` nem geram `LivroCaixa`
diretamente (são movimentação física de gaveta, não lançamento bancário) — entram
apenas no cálculo de `valor_fechamento_calculado` da sessão. **Confirmar com
Blueprint** se cliente quer isso também refletido no `LivroCaixa` da conta CAIXA
(recomendo que sim, para o CAIXA como `Conta` ficar auditável como qualquer outra —
nesse caso vira `origem=MANUAL` com `criado_por`, seguindo o padrão de lock já usado).

### 4.3 `Venda`
```
numero                CharField (auto: VDA-{ano}-{seq}, mesmo padrão de Orcamento/Pedido em vendas/models.py)
sessao_caixa           FK SessaoCaixa (obrigatório, PROTECT)
cliente                FK clientes.Cliente (null=True — Consumidor Final)
operador               FK settings.AUTH_USER_MODEL
status                 CharField choices ABERTA/FINALIZADA/CANCELADA, default ABERTA
subtotal               DecimalField (soma dos itens antes do desconto)
desconto_total         DecimalField
valor_total            DecimalField (editable=False, calculado no save())
data_hora              DateTimeField (auto_now_add)
cancelada_em           DateTimeField (null=True)
motivo_cancelamento    TextField (blank)
```
Note: não existe FK única `receita` na `Venda` — uma venda pode gerar **mais de uma**
`Receita` (uma por forma de pagamento no split, Seção 4.5), então a relação é
`Receita.origem_venda` (FK reversa, ver 4.5) ou uma tabela de junção implícita via
`PagamentoVenda.receita`.

### 4.4 `ItemVenda`
```
venda            FK Venda (related_name='itens')
produto          FK produtos.Produto (PROTECT)
quantidade       DecimalField (mesma casas decimais de produtos.Produto: max_digits=12, decimal_places=3)
unidade          CharField choices produtos.UnidadeBase
valor_unitario   DecimalField (snapshot — copiado de Produto.preco_venda no momento da venda, nunca lido de Produto depois)
desconto_item    DecimalField default 0
valor_total      DecimalField (editable=False, calculado no save(): quantidade*valor_unitario - desconto_item)
quantidade_estornada  DecimalField default 0   ← NOVO campo pro Ponto 2 (Seção 5.1)
```

### 4.5 `PagamentoVenda`
```
venda      FK Venda (related_name='pagamentos')
metodo     FK pagamentos.MetodoPagamento
valor      DecimalField
conta      FK financeiro.Conta (conta de destino resolvida no momento da venda — ver A4/RF-14)
receita    FK financeiro.Receita (null=True até a Receita ser criada na finalização — ver RF-08)
```
Para `metodo.nome == CARTAO_CREDITO`: relação 1:1 opcional com `RecebivelCartao`
(Seção 6) — **não** colocar os campos de taxa/prazo direto em `PagamentoVenda`
(ficariam `null` para 95% dos pagamentos que não são cartão de crédito). Recomendo
model separado `RecebivelCartao(pagamento=OneToOneField(PagamentoVenda))` — decisão
final de modelagem cabe ao Blueprint, mas a razão de design está registrada aqui.

---

## 5. Ponto 2 — Estorno de Receita (devolução parcial de item) — DETALHADO

### 5.1 Por que não copiar o padrão de `Despesa.estornar` 1:1

`DespesaViewSet.estornar_despesa` (views.py:227) assume estorno **total e único**:
marca `despesa.estornado=True` de uma vez e cria **um** `LivroCaixa` de reversão pelo
`valor_liquido` inteiro. Devolução de item de venda precisa suportar:
- devolver **um item entre vários** da mesma venda (ex.: venda com 3 produtos, cliente
  devolve só 1);
- devolver **parte da quantidade** de um item (ex.: comprou 5un, devolve 2un);
- devolver em **momentos diferentes** (devolve item A hoje, item B semana que vem) —
  ou seja, **múltiplos estornos parciais sobre a mesma `Receita`**.

O campo booleano simples de `Despesa` não representa isso. Por isso o Ponto 2 exige
modelo novo, não reuso direto.

### 5.2 Model novo: `EstornoReceita`

```python
class EstornoReceita(BaseModel):
    receita       = models.ForeignKey(Receita, on_delete=models.PROTECT, related_name='estornos')
    valor         = models.DecimalField(max_digits=12, decimal_places=2)  # > 0
    motivo        = models.TextField()  # obrigatório, mesma regra de Despesa.estornar
    data_estorno  = models.DateField()
    item_venda    = models.ForeignKey('pdv.ItemVenda', null=True, blank=True, on_delete=models.SET_NULL, related_name='estornos')
    criado_por    = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')

    class Meta:
        db_table = 'fin_estorno_receita'
        ordering = ['-data_estorno']
```
`item_venda` é opcional e nullable de propósito: `EstornoReceita` é um mecanismo
**genérico** do módulo `financeiro` (útil para qualquer estorno parcial de receita no
futuro, não só PDV) — o vínculo com PDV é o link opcional, não o contrário. Evita o
financeiro ficar dependente do app do PDV.

### 5.3 Campos novos em `Receita`

```python
# Receita ganha:
estornado       = models.BooleanField(default=False)       # True quando saldo_disponivel <= 0
data_estorno    = models.DateField(null=True, blank=True)  # data do último estorno (compat com filtros existentes)
motivo_estorno  = models.TextField(blank=True)              # motivo do último estorno (compat)

# Property (não persistida):
@property
def valor_estornado_total(self):
    return self.estornos.aggregate(v=Sum('valor'))['v'] or Decimal('0')

@property
def saldo_disponivel(self):
    return self.valor_liquido - self.valor_estornado_total
```
Os 3 campos flat (`estornado`/`data_estorno`/`motivo_estorno`) são mantidos por
**compatibilidade de padrão** com `Despesa` (mesmos nomes, mesmo uso em
`filterset_fields`, mesmo hábito de leitura de quem já mexeu no financeiro) — mas
aqui `estornado=True` significa "saldo esgotado", não "existe estorno". Isso deve
ficar em `docstring` explícita no model para não confundir o próximo dev.

### 5.4 Action nova: `POST /api/v1/financeiro/receitas/{id}/estornar/`

Espelha `estornar_despesa` na estrutura de lock/transação, mas com a lógica de
parcial:

1. `permission_classes=[IsAdmin]` (mesmo padrão de Despesa).
2. Body: `{valor?, motivo, data_estorno?, item_venda_id?}`. Se `valor` omitido,
   assume `saldo_disponivel` inteiro (estorno total, comportamento equivalente ao de
   Despesa).
3. Validações: `receita.status == 'RECEBIDO'`; `motivo` não vazio; `0 < valor <=
   saldo_disponivel` (nunca deixar `saldo_disponivel` negativo).
4. Dentro de `transaction.atomic()` + `pg_advisory_xact_lock(conta.id)`:
   - cria `EstornoReceita(receita, valor, motivo, data_estorno, item_venda)`;
   - cria `LivroCaixa(tipo='SAIDA', origem='ESTORNO', origem_id=receita.id, valor=valor, descricao=f'Estorno receita: {receita.descricao} — {motivo}', estorno_de=<lançamento ENTRADA original, se o estorno esgota o saldo>, estornado=True)` — **tipo SAIDA**, pois a `Receita` original gerou `ENTRADA`; o estorno é o dinheiro saindo de volta;
   - só marca o `LivroCaixa` **original** (`origem='RECEITA', origem_id=receita.id`) como `estornado=True` quando o estorno **esgota** o saldo (estorno total) — em estorno parcial o lançamento original continua válido pelo que sobrou, análogo a "reduzir", não "anular";
   - atualiza `receita.estornado` (`True` se `saldo_disponivel <= 0` após o estorno), `data_estorno`, `motivo_estorno`;
   - `_reconstruir_cadeia(conta)`.
5. Retorna o `EstornoReceita` criado (serializer novo `EstornoReceitaSerializer`).

### 5.5 Impacto obrigatório em `relatorios.py::calcular_dre_mes` (achado A2)

Hoje `rec_qs` soma `valor_bruto`/`valor_liquido` de toda `Receita status=RECEBIDO`
sem excluir nada. Duas opções — **decisão a confirmar com Blueprint antes do Forge
codar**, registrando aqui as duas para não perder o raciocínio:

- **Opção 1 (recomendada):** abater o estorno no **mês da receita original**
  (`recebimento`), subtraindo `Sum(EstornoReceita.valor)` das receitas do
  período do agregado de `receita_operacional`/`receita_bruta`. Mantém DRE do mês da
  venda coerente com o resultado real daquele mês.
- **Opção 2:** abater no **mês em que o estorno aconteceu** (`data_estorno`), como
  uma linha negativa separada — mais simples de implementar (análogo a como
  `Despesa` já filtra `estornado=False` no próprio mês do estorno), mas pode fazer
  o DRE de um mês fechado "mudar depois" quando uma venda antiga é devolvida.

Registrado como pendência explícita para o Blueprint decidir — **não decido
arquitetura de relatório aqui**, só aponto que sem uma das duas o DRE fica errado a
partir do momento em que `EstornoReceita` existir.

### 5.6 Efeito no PDV (`ItemVenda`)

Ação `POST /api/v1/pdv/vendas/{id}/itens/{item_id}/devolver/`:
1. Recebe `{quantidade, motivo}` (`quantidade <= item.quantidade -
   item.quantidade_estornada`).
2. Reverte estoque: `Produto.objects.filter(pk=produto_id).update(quantidade_estoque=F('quantidade_estoque') + quantidade_base)` (mesma resolução de `ConversaoUnidade` usada em `EntradaEstoque`, ver A7) — soma de volta, nunca deixa negativo por causa da devolução.
3. Calcula `valor_proporcional = (quantidade / item.quantidade) * item.valor_total`.
4. Chama a lógica de estorno de Receita (5.4) pelo `valor_proporcional`, vinculado
   à(s) `Receita`(s) da `Venda` via `PagamentoVenda.receita` — se a venda teve split
   (dinheiro + pix), a devolução deve **ratear proporcionalmente** entre as Receitas
   do split, ou (mais simples) sempre devolver primeiro da forma de pagamento que o
   operador escolher na tela — **UX a decidir com Loom/Blueprint**, mas a regra de
   negócio (nunca devolver mais do que o item vale) é a mesma nos dois casos.
5. Atualiza `item.quantidade_estornada += quantidade`; recalcula
   `Venda.valor_total`.

---

## 6. Ponto 3 — Cartão de crédito com taxa e prazo (`RecebivelCartao`) — DETALHADO

### 6.1 Por que reaproveitar `Receita.desconto` em vez de criar campo de taxa nela

`Receita` já tem `valor_bruto`, `desconto` e `valor_liquido = valor_bruto - desconto`
calculado no `save()` (models.py, `Receita.save()`). A taxa da maquininha **é
exatamente esse desconto** — não precisa de campo novo em `Receita`:

- `Receita.valor_bruto` = valor total pago no cartão pelo cliente;
- `Receita.desconto` = `valor_bruto * (taxa_percentual / 100)` (a taxa da maquininha);
- `Receita.valor_liquido` = o que realmente vai cair na conta — calculado sozinho,
  reaproveitando o `save()` que já existe, zero mudança em `Receita` para isso.

### 6.2 Model novo: `RecebivelCartao`

```python
class RecebivelCartao(BaseModel):
    pagamento                  = models.OneToOneField('pdv.PagamentoVenda', on_delete=models.PROTECT, related_name='recebivel_cartao')
    receita                    = models.OneToOneField(Receita, on_delete=models.PROTECT, related_name='recebivel_cartao')
    taxa_percentual            = models.DecimalField(max_digits=5, decimal_places=2)
    valor_bruto                = models.DecimalField(max_digits=12, decimal_places=2)   # = pagamento.valor, snapshot
    valor_liquido_previsto     = models.DecimalField(max_digits=12, decimal_places=2, editable=False)  # = receita.valor_liquido, snapshot no momento da criação
    data_prevista_liquidacao   = models.DateField()   # = data da venda + prazo (dias) informado no momento do pagamento
    data_liquidacao            = models.DateField(null=True, blank=True)  # preenchida quando concilia
    status                     = models.CharField(max_length=15, choices=[('PREVISTO','Previsto'),('LIQUIDADO','Liquidado'),('CANCELADO','Cancelado')], default='PREVISTO')
    criado_por                 = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')

    class Meta:
        db_table = 'pdv_recebivel_cartao'
        ordering = ['data_prevista_liquidacao']
```
`taxa_percentual` e o prazo (em dias, usado só para calcular
`data_prevista_liquidacao`, não persistido isoladamente) são **informados pelo
operador no momento do split de pagamento** — não existe hoje nenhuma tabela de taxa
por maquininha/bandeira no sistema (achado A4). Proponho como **RF Should** (não
Must, para não travar a entrega) um cadastro simples de "taxas padrão por método"
que só pré-preenche o campo na tela, editável — ver RF-14.

### 6.3 Fluxo completo: nascimento → liquidação

**Na finalização da venda** (RF-08), para cada `PagamentoVenda` com
`metodo.nome == CARTAO_CREDITO`:
1. Cria `Receita` com `status=PENDENTE` (não `RECEBIDO` — dinheiro ainda não caiu),
   `valor_bruto` = valor do pagamento, `desconto` = valor da taxa, `vencimento` =
   `data_prevista_liquidacao`, `conta` = conta mapeada para recebimento de cartão
   (RF-14), `tipo=PRODUTO`.
2. Cria `RecebivelCartao` vinculado a essa `Receita` e ao `PagamentoVenda`.
3. **Nenhum `LivroCaixa` nasce ainda** — o signal `receita_para_livro_caixa` só
   dispara quando `status == 'RECEBIDO'` (confirmado em `signals.py`), então uma
   `Receita PENDENTE` já é automaticamente "invisível" no caixa até liquidar — zero
   código novo de lock aqui, o mecanismo existente já faz o que precisa.

**Na liquidação (Conciliação Bancária, já existente em `financeiro`):**
`ConciliacaoViewSet.confirmar-item` (views.py:797) hoje, ao confirmar um item
`FALTANDO_SISTEMA`, cria um `LivroCaixa` novo do zero (`origem=MANUAL`) — **não sabe
vincular a uma `Receita PENDENTE` já existente**. Isso precisa ser estendido:

4. Ao confirmar um `ItemConciliacao`, se houver `RecebivelCartao(status=PREVISTO)`
   com `data_prevista_liquidacao` próxima e `valor_liquido_previsto` batendo (ou
   próximo, considerando pequenas variações de taxa real vs prevista) com o valor do
   item do banco, **sugerir o vínculo** ao operador (dropdown/autocomplete na tela de
   conciliação — UX do Loom) em vez de forçar preenchimento manual.
5. Ao confirmar o vínculo: `receita.status = 'RECEBIDO'`, `receita.recebimento =
   data_banco` → dispara o signal existente → `LivroCaixa ENTRADA` nasce sozinho,
   **sem duplicar lógica de lock**; `RecebivelCartao.status = 'LIQUIDADO'`,
   `data_liquidacao = data_banco`.
6. Se o valor real do banco for diferente do `valor_liquido_previsto` (taxa real
   cobrada pela operadora divergiu da prevista), **ajustar `Receita.desconto`** antes
   de marcar `RECEBIDO`, para o valor líquido bater exatamente com o extrato — regra
   de negócio a confirmar com Luiz Eduardo se deve gerar alerta/aprovação ou ajustar
   silenciosamente (proponho alerta visual, não bloqueio).

**Não fazer:** criar um sistema de conciliação paralelo para `RecebivelCartao` — o
objetivo explícito desta especificação é acoplar no que já existe
(`ConciliacaoExtrato`/`ItemConciliacao`), só ensinando o endpoint já existente a
reconhecer um recebível pendente em vez de sempre criar lançamento manual do zero.

---

## 7. Requisitos Funcionais (RF)

| ID | Descrição | MoSCoW |
|---|---|---|
| RF-01 | Operador deve poder abrir `SessaoCaixa` informando `conta` (tipo CAIXA) e `valor_abertura` | Must |
| RF-02 | Sistema deve bloquear abertura de nova sessão se já existir `SessaoCaixa status=ABERTA` para a mesma `conta` | Must |
| RF-03 | Sistema deve permitir buscar `Produto` por nome ou `codigo_barras` na tela de venda | Must |
| RF-04 | Operador deve poder montar carrinho (`ItemVenda`) editável antes de finalizar | Must |
| RF-05 | Venda deve poder ser feita sem cliente (Consumidor Final) ou vinculada a `Cliente` existente | Must |
| RF-06 | Ao finalizar venda, sistema deve debitar `Produto.quantidade_estoque` usando a mesma resolução de conversão de unidade de `EntradaEstoque` (inversa) | Must |
| RF-07 | Sistema deve bloquear finalização se estoque insuficiente para qualquer item (nunca deixar negativo sem aviso explícito) | Must |
| RF-08 | Ao finalizar venda, sistema deve criar uma `Receita` por `PagamentoVenda` (split), `status=RECEBIDO` para métodos à vista, `status=PENDENTE` + `RecebivelCartao` para cartão de crédito (Seção 6) | Must |
| RF-09 | Sistema deve permitir split de pagamento (múltiplos `PagamentoVenda` por `Venda`, soma = `valor_total`) | Must |
| RF-10 | Sistema deve permitir sangria e suprimento durante sessão aberta (`MovimentoCaixa`) | Must |
| RF-11 | Sistema deve permitir fechar `SessaoCaixa` com contagem física, calculando `diferenca`, **sem travar** o fechamento se houver diferença | Must |
| RF-12 | Sistema deve permitir cancelar `Venda` inteira (reverte estoque de todos os itens + estorna todas as `Receita`s associadas) | Must |
| RF-13 | Sistema deve permitir devolução parcial de item (`EstornoReceita`, Seção 5) | Must |
| RF-14 | Sistema deve resolver a `Conta` de destino de cada forma de pagamento no momento da venda — Should ter tela de configuração `MetodoPagamento ↔ Conta padrão`; Must ter pelo menos seleção manual da conta no split se a config não existir | Should (config) / Must (seleção manual) |
| RF-15 | Sistema deve mostrar Histórico de Vendas com filtro por período/operador/status, com detalhe e ação de cancelar/devolver | Must |
| RF-16 | Sistema deve mostrar Relatório de Sessões de Caixa (auditoria de diferenças), acesso `IsAdmin` | Must |
| RF-17 | Conciliação Bancária deve sugerir vínculo de `ItemConciliacao` com `RecebivelCartao PREVISTO` compatível em valor/data (Seção 6.3) | Should |
| RF-18 | Cadastro de taxa padrão por `MetodoPagamento` para pré-preencher `taxa_percentual` no split | Could |

## 8. Requisitos Não Funcionais (RNF)

- **RNF-01** Finalizar/cancelar venda e estornar item devem rodar em
  `transaction.atomic()` + `pg_advisory_xact_lock(conta.id)`, mesmo padrão de
  `transferir`/`estornar_despesa`/`estornar` já usados no `financeiro` (achado A6).
- **RNF-02** Toda tela do PDV responsiva mobile/desktop (padrão já usado em
  Conciliação, Manutenção #10).
- **RNF-03** Erros de API tratados com mensagem legível (`.catch` +
  `extractErrorMessage`, padrão já usado no frontend — Manutenção #9/#10).
- **RNF-04** `id = serializers.IntegerField(source='pk', read_only=True)` em todos os
  serializers novos (padrão Uid, já confirmado em uso em todo `financeiro/serializers.py`).
- **RNF-05** Soft delete (`is_active`) em todos os models novos que herdam `BaseModel`
  — exceto `EstornoReceita`, que **não deve ter delete** (é registro contábil
  imutável, mesmo espírito de `LivroCaixa` já ser append-only no sistema).

## 9. Regras de Negócio (consolidado)

- RN-01: 1 sessão `ABERTA` por `Conta` (não global).
- RN-02: Venda só finaliza com `SessaoCaixa.status=ABERTA` vinculada.
- RN-03: Preço do item = snapshot de `Produto.preco_venda` no momento da venda —
  nunca recalculado depois se `Produto.preco_venda` mudar.
- RN-04: Estorno de `Receita` nunca deixa `saldo_disponivel` negativo.
- RN-05: `EstornoReceita` sempre exige `motivo` não vazio (mesma regra de
  `estornar_despesa`).
- RN-06: `RecebivelCartao` só vira `RECEBIDO`/`LIQUIDADO` via confirmação de
  conciliação — nunca automaticamente por data (evita marcar como recebido algo que
  não caiu de fato).
- RN-07: Fechamento de caixa registra `diferenca` mas nunca bloqueia o fechamento.
- RN-08: Cancelamento de venda reverte 100% do estoque e estorna 100% das Receitas —
  devolução parcial de item é uma operação diferente (RF-13), não uma variação do
  cancelamento total.

## 10. Telas

1. **Abertura de Caixa** — redireciona para cá se operador não tem `SessaoCaixa
   ABERTA` na conta selecionada.
2. **Frente de Caixa / Nova Venda** — busca produto (nome/código de barras),
   carrinho editável, cliente opcional, split de pagamento (com campos de
   taxa/prazo quando método = cartão de crédito), confirmação.
3. **Sangria / Suprimento** — modal rápido, motivo obrigatório.
4. **Fechamento de Caixa** — resumo (vendas por forma de pagamento, sangrias,
   suprimentos), input de contagem física, mostra diferença sem bloquear.
5. **Histórico de Vendas** — filtros período/operador/status, detalhe, ação
   cancelar/devolver parcial (por item, com input de quantidade).
6. **Relatório de Sessões de Caixa** — auditoria de diferenças, `IsAdmin` only.
7. **(Should) Configuração Método de Pagamento → Conta / Taxa padrão** — tela
   simples de cadastro, referenciada em RF-14/RF-18.

## 11. Permissões

- `IsAuthenticated`: abrir/vender/sangria/suprimento/fechar caixa, devolver item.
- `IsAdmin` (`request.user.is_staff`, já existente): Relatório de Sessões de Caixa,
  ação `estornar` em `Receita` (mesmo padrão de `estornar_despesa`, que já é
  `IsAdmin`).
- Nenhum sistema de perfis novo — reaproveita `IsAdmin`/`IsAuthenticated` já em uso.

## 12. Fora de Escopo (nesta manutenção)

- Emissão fiscal (NFC-e/SAT/cupom fiscal) — não mencionado no briefing, não incluído.
- Cadastro de bandeiras/adquirentes específicas — taxa é informada manualmente
  (RF-18 é Could, não Must).
- Parcelamento de venda em cartão de crédito com liquidação escalonada por parcela
  (ex.: 3x com 3 datas de liquidação diferentes) — o desenho atual assume 1
  `RecebivelCartao` por `PagamentoVenda` com **uma** data de liquidação. Se o cliente
  precisar de recebível parcelado, é uma expansão futura da Seção 6, não coberta
  aqui — **sinalizar para Luiz Eduardo confirmar se isso é necessário já nesta
  entrega ou fica para depois.**

## 13. Riscos e Dependências

- **Decisão de arquitetura pendente (A3):** app novo `pdv` vs. dentro de `vendas` —
  bloqueia o Blueprint definir estrutura de pastas; não bloqueia esta especificação.
- **Decisão pendente (5.5):** DRE abate estorno no mês da receita original ou no mês
  do estorno — Blueprint decide antes do Forge tocar `relatorios.py`.
- **Dependência de dado real:** RF-17 (sugestão automática de vínculo na
  conciliação) depende de `valor_liquido_previsto` estar correto — se a taxa real
  informada no split divergir muito da taxa real cobrada pela operadora, o
  auto-match pode falhar e cair para vínculo manual (aceitável, não é regressão).
- **Risco de concorrência:** duas vendas simultâneas debitando o mesmo produto —
  mitigado pelo mesmo padrão de `pg_advisory_xact_lock`, mas nesse caso o lock deve
  ser por `conta` (já decidido) **e também por `produto`** durante a baixa de
  estoque, para não haver race condition de estoque entre vendas em caixas
  diferentes vendendo o mesmo produto ao mesmo tempo — **sinalizo esse ponto extra
  para o Forge**, não estava no briefing original mas é decorrência direta de RF-07.

## 14. Sentinel — Roteiro de Teste (conforme solicitado no briefing)

1. Abrir caixa → vender produto com estoque conhecido → conferir baixa de estoque
   (valor exato, considerando conversão de unidade se aplicável).
2. Conferir `Receita`/`LivroCaixa` criados na conta certa, valor certo.
3. Split dinheiro+pix → conferir dois `PagamentoVenda`, duas `Receita`, dois
   lançamentos de `LivroCaixa` (ou um por conta, se ambos forem pra mesma conta).
4. Split com cartão de crédito → conferir `Receita PENDENTE` + `RecebivelCartao
   PREVISTO`, **nenhum** `LivroCaixa` criado ainda.
5. Simular conciliação confirmando o item → conferir `Receita.status=RECEBIDO`,
   `RecebivelCartao.status=LIQUIDADO`, `LivroCaixa ENTRADA` nascido via signal.
6. Cancelar venda → conferir estoque volta (todos os itens) + todas as Receitas
   estornadas (não deletadas) + `LivroCaixa` de estorno criado.
7. Devolver parcialmente 1 item de uma venda com outros itens intactos → conferir
   estoque volta só daquele item/quantidade, `EstornoReceita` criado pelo valor
   proporcional, `Receita.saldo_disponivel` reduzido corretamente, `Venda.valor_total`
   recalculado, **DRE do mês reflete o ajuste** conforme a opção decidida em 5.5.
8. Fechar caixa com diferença proposital (contagem física ≠ calculado) → conferir
   que registra a diferença sem travar o fechamento.
9. Tentar abrir 2ª sessão na mesma conta com uma já `ABERTA` → deve bloquear.
10. Tentar vender com `SessaoCaixa` fechada → deve bloquear.
11. Tentar estornar `Receita` além do `saldo_disponivel` → deve bloquear com erro
    claro.
12. 0 falhas obrigatório, 100% dos RFs Must com teste — conforme regra global do
    Sentinel (CLAUDE.md).

---

## 15. Observações finais do Analista

- Este documento **não implementa nada** — é levantamento e re-elicitação. Toda
  decisão de estrutura de pastas/apps, nomes finais de models e contratos de API
  fica com o **Blueprint**.
- Dois pontos ficam marcados **[CONFIRMAR COM BLUEPRINT]** antes do Forge iniciar:
  (a) app `pdv` novo vs. dentro de `vendas` (Seção 2, A3); (b) mês de abatimento do
  estorno no DRE (Seção 5.5).
- Um ponto fica marcado **[CONFIRMAR COM LUIZ EDUARDO]**: se recebível de cartão
  parcelado (múltiplas datas de liquidação por venda) é necessário já nesta entrega
  (Seção 12).

➡️ **Planner:** rotear para Pipeline D (feature grande, aprovação comercial já
concedida) — Blueprint deve ler esta especificação e as duas decisões de
arquitetura pendentes antes de gerar a planta para Forge + Loom.
