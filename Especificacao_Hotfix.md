# Especificação Hotfix — Manutenção #58 (FASE 2)

**Sistema:** UidCore (OS #7)
**Módulo novo:** `compras` (depende de `fornecedores`, `produtos`, `financeiro`)
**Tipo:** `feature_grande` (novo módulo + integração de 3 apps existentes — Compras entra no escopo de Fase 2 da Manutenção #58, não é módulo pago à parte)
**Requer aprovação comercial:** não — evolução do módulo Estoque/Financeiro já contratado, dentro do ciclo de Manutenção #58 já aberto
**Analista:** leitura de código confirmada em `backend/fornecedores/models.py`, `backend/financeiro/{models,signals,serializers,views,services}.py`, `backend/produtos/{models,serializers,views,services}.py`, `backend/core/urls.py`

---

## 1. Diagnóstico confirmado (gap real, não suposição)

- `fornecedores.Fornecedor` existe como cadastro completo (`PessoaBase` — CPF/CNPJ, contato, categoria) mas **não é referenciado por nenhuma FK em nenhum outro app** (`grep -rn "fornecedores.Fornecedor\|ForeignKey(Fornecedor" backend/` só retorna o próprio app `fornecedores`).
- `financeiro.Despesa.fornecedor` é `CharField(max_length=150)` — texto livre, sem vínculo com o cadastro real. Uma compra registrada como Despesa hoje não sabe "qual" fornecedor foi, só um texto digitado à mão.
- `produtos.MovimentoEstoque` (Fase 1, em produção) não tem nenhum campo de origem financeira — `nota_fiscal` é `CharField` livre, sem custo, sem fornecedor, sem vínculo com uma compra real.
- Não existe, em lugar nenhum do backend, um model que amarre as três pontas: **fornecedor → itens comprados com custo → lançamento financeiro → entrada de estoque**. Hoje o fluxo real de "comprei mercadoria" exige 2 ações manuais desconectadas: lançar uma Despesa avulsa (fornecedor em texto livre) e lançar um `MovimentoEstoque` tipo `ENTRADA` (sem custo, sem fornecedor) — sem nenhuma garantia de que os dois batem.

**Compatibilidade verificada antes de propor a mudança:**
- `produtos.MovimentoEstoque.save()` (Fase 1) já resolve conversão de unidade via `produtos.services.fator_para_base` e atualiza `Produto.quantidade_estoque` via `F()` de forma atômica — **reaproveitado integralmente**, Fase 2 não duplica essa lógica em lugar nenhum.
- `financeiro.signals.despesa_para_livro_caixa` já cria o `LivroCaixa` automaticamente quando `Despesa.status == 'PAGO' and despesa.pagamento` — **reaproveitado integralmente**, Compra nunca escreve em `LivroCaixa` diretamente (regra absoluta do projeto, `financeiro/signals.py` é o único ponto de escrita em `LivroCaixa` fora de estornos manuais).
- `financeiro.views.DespesaViewSet.estornar_despesa` (linha 262) já contém a lógica de reversão (cria `LivroCaixa` de estorno em par, marca `despesa.estornado=True`) — Fase 2 **extrai** essa lógica para `financeiro/services.py::estornar_despesa()` (mesmo padrão de `estornar_receita()`, que já existe nesse arquivo) para ser reaproveitada tanto pelo endpoint existente quanto pelo cancelamento de Compra, sem duplicar o bloco de `pg_advisory_xact_lock` + criação de `LivroCaixa` de estorno.

---

## 2. Decisões de arquitetura (fechadas nesta especificação)

| Decisão em aberto no pedido | Escolha | Justificativa |
|---|---|---|
| App novo `compras` vs. dentro de `produtos` | **App novo `compras`** | SRP — Compra depende de 3 apps (`fornecedores`, `produtos`, `financeiro`); colocar dentro de `produtos` criaria dependência de `produtos` → `financeiro` (hoje `produtos` não importa `financeiro` em lugar nenhum) e inverteria a direção natural de dependência do domínio (Compras é o processo, Produtos e Financeiro são os efeitos). |
| Endpoint | **`/api/v1/compras/`** (top-level, mesmo padrão de `pdv`, `marketing`) | Compra não é sub-recurso de Produto nem de Fornecedor — é uma entidade de primeira classe com fluxo próprio (confirmar, cancelar). |
| Gerar Despesa em qualquer status ou só quando PAGO | **Em qualquer status, espelhando `Compra.status` 1:1 na `Despesa` criada** | Reaproveita o mecanismo já existente: `Despesa` já tem ciclo de vida `PENDENTE → PAGO` e o signal `despesa_para_livro_caixa` já só cria `LivroCaixa` quando `status=PAGO`. Criar a Despesa sempre (com status espelhado) evita um segundo caminho de código pra "criar Despesa depois, na hora que a Compra virar PAGO" — a transição de status da Compra apenas atualiza a Despesa já existente, e o `LivroCaixa` nasce sozinho pelo signal que já está em produção. Se a Despesa só nascesse em PAGO, uma Compra PENDENTE ficaria sem nenhum registro financeiro visível no módulo Financeiro, quebrando a rastreabilidade "tenho uma nota fiscal a pagar" que o pedido menciona no campo `status`. |
| FK reversa Compra→Despesa | **`Compra.despesa` — `OneToOneField` nullable para `financeiro.Despesa`, `on_delete=SET_NULL`** | Rastreabilidade direta sem tocar no model `Despesa` (que seria compartilhado com Despesas avulsas não vinda de Compra — não pode ganhar uma FK obrigatória para Compra). `SET_NULL` porque `Despesa` é soft-delete (`is_active=False`), nunca apagada de fato — mas a referência não deve travar exclusão lógica futura da Despesa se algum dia isso for permitido fora deste fluxo. |
| Tela frontend | **Página separada `Compras.jsx`** com modal "Nova Compra" em formato carrinho (reaproveita o padrão já validado de `BuscaProdutoRapida` — Manutenção #32 — para adicionar itens por busca, em vez de criar componente novo do zero) | Compra tem ciclo de vida próprio (listar, filtrar por fornecedor/status, cancelar) que não cabe bem dentro de um modal de outra tela, mas a *criação* de uma compra é conceitualmente um carrinho (fornecedor + N itens + total), igual ao PDV e ao padrão já usado em Orçamento/Pedido. |

---

## 3. Requisitos Funcionais (RF)

- **RF-01** — Novo app `compras` com models `Compra` e `ItemCompra`, registrado em `INSTALLED_APPS` e roteado em `core/urls.py` como `path('api/v1/compras/', include('compras.urls'))`.
- **RF-02** — `Compra`: `fornecedor` (FK `fornecedores.Fornecedor`, `PROTECT` — não pode excluir fornecedor com compra vinculada), `conta` (FK `financeiro.Conta`, `PROTECT` — de onde sai o dinheiro), `numero_nota_fiscal` (CharField, opcional), `data_emissao` (DateField, obrigatório), `forma_pagamento` (reaproveita `financeiro.FormaPagamento.choices`), `status` (`PENDENTE`/`PAGO`/`CANCELADO` — novo `TextChoices` `StatusCompra` no app `compras`, não reaproveita `financeiro.StatusDespesa` diretamente para não acoplar os dois apps num único enum, mas os valores `PENDENTE`/`PAGO` são espelhados 1:1 na Despesa gerada), `valor_total` (DecimalField, calculado no `create()` do serializer a partir da soma dos itens — nunca editável via payload direto), `observacoes` (TextField, opcional), `despesa` (OneToOneField nullable, ver decisão acima), `criado_por`.
- **RF-03** — `ItemCompra`: `compra` (FK `CASCADE`), `produto` (FK `produtos.Produto`, `PROTECT`), `quantidade` (Decimal, > 0), `unidade` (choices `produtos.UnidadeBase`, resolvida via `fator_para_base` — mesma cadeia de conversão da Fase 1, `RN-01`/`RN-05` da Manutenção #37 continuam valendo sem exceção), `valor_unitario_custo` (Decimal, > 0), `movimento_estoque` (OneToOneField nullable para `produtos.MovimentoEstoque`, populado na criação).
- **RF-04** — Ao criar um `ItemCompra`, o `save()` cria automaticamente 1 `MovimentoEstoque` com `tipo=ENTRADA`, `quantidade`/`unidade` do item, `nota_fiscal=compra.numero_nota_fiscal`, `observacoes=f'Compra #{compra.id} — {fornecedor.nome_razao_social}'` — reaproveitando 100% do `MovimentoEstoque.save()` da Fase 1 (conversão de unidade + `F()` atômico em `Produto.quantidade_estoque`). **Nenhuma lógica de estoque é duplicada em `compras`.**
- **RF-05** — Ao criar um `ItemCompra`, `Produto.valor_unitario` (campo de custo, já existente desde antes da Manutenção #58) é sobrescrito com `valor_unitario_custo` do item — regra "último custo sobrescreve" (item 4 do pedido). Feito via `Produto.objects.filter(pk=...).update(...)`, mesmo padrão atômico do `F()` já usado em `MovimentoEstoque.save()` (sem race condition com outra escrita concorrente de estoque).
- **RF-06** — Ao criar uma `Compra` (`POST /api/v1/compras/`), o `create()` do serializer:
  1. calcula `valor_total = Σ (quantidade × valor_unitario_custo)` de todos os itens do payload;
  2. cria `Compra` já com `valor_total` correto (dispara o signal que gera a `Despesa` — ver RF-07 — com o valor certo já na primeira escrita, sem necessidade de recalcular/resalvar depois);
  3. cria cada `ItemCompra` em loop (dispara RF-04/RF-05 por item).

  Tudo dentro de uma única `transaction.atomic()` — se qualquer item falhar (produto sem conversão de unidade cadastrada, RN-05 da Manutenção #37), a Compra inteira é revertida, nenhuma Despesa nem MovimentoEstoque órfão fica no banco.
- **RF-07** — Signal `post_save` em `Compra` (`compras/signals.py`):
  - **Na criação (`created=True`)**: cria 1 `financeiro.Despesa` com `categoria` = "Compra de Mercadoria" (RF-09), `descricao` gerada automaticamente, `fornecedor` (CharField) preenchido com `compra.fornecedor.nome_razao_social` (Despesa continua sem FK — RN-04), `valor_bruto=compra.valor_total`, `conta=compra.conta`, `forma_pagamento=compra.forma_pagamento`, `status` espelhado de `compra.status`, `vencimento=compra.data_emissao`, `pagamento=compra.data_emissao` **somente se** `compra.status == 'PAGO'` (caso contrário `None` — Despesa nasce pendente, sem lançamento no Livro Caixa, exatamente como qualquer outra Despesa `PENDENTE` do sistema hoje). Vincula a Despesa criada de volta em `Compra.despesa` via `update()` (evita re-disparar o próprio signal).
  - **Na atualização (`created=False`)**: se `compra.despesa_id` existe e `despesa.status != compra.status`, sincroniza `despesa.status` (e `despesa.pagamento = hoje` se virou `PAGO` e ainda não tinha data) e chama `despesa.save()` — isso **re-dispara o signal `despesa_para_livro_caixa` já existente em produção**, que cria o `LivroCaixa` sozinho quando `status` vira `PAGO`. Nenhum código novo escreve em `LivroCaixa`.
- **RF-08** — Endpoint `PATCH /api/v1/compras/{id}/` aceita **apenas** os campos `status` (transição `PENDENTE → PAGO`, ver RN-06 sobre imutabilidade dos itens) e `observacoes`. Qualquer tentativa de alterar `itens`, `valor_total`, `fornecedor` ou `conta` via PATCH é ignorada (campos `read_only` no serializer de update).
- **RF-09** — Data migration (`compras/migrations/0002_categoria_compra_mercadoria.py`, `RunPython`) cria (via `get_or_create`, idempotente) a `financeiro.Categoria(nome='Compra de Mercadoria', tipo='SAIDA')` usada em RF-07. Primeira `RunPython` de seed de dado do projeto — documentar no código o motivo (evita depender de fixture manual ou de alguém criar a categoria certa via admin antes do primeiro uso).
- **RF-10** — Ação `POST /api/v1/compras/{id}/cancelar/`:
  1. Bloqueia se `compra.status == 'CANCELADO'` (`400`, já cancelada).
  2. Para cada `ItemCompra`, cria 1 `MovimentoEstoque` `tipo=AJUSTE`, `quantidade=-item.quantidade` (mesma `unidade` do item original), `observacoes=f'Cancelamento Compra #{compra.id}'` — reverte o estoque exatamente pela função de conversão já existente (RN-03), sem duplicar cálculo.
  3. Se `compra.despesa` existe:
     - `despesa.status == 'PAGO'` → chama `financeiro.services.estornar_despesa(despesa, motivo=f'Compra #{compra.id} cancelada', data_estorno=hoje, usuario=request.user)` (função **extraída** de `DespesaViewSet.estornar_despesa`, ver seção 6.3);
     - `despesa.status == 'PENDENTE'` → `despesa.is_active = False` (soft delete simples, nunca existiu `LivroCaixa` pra essa Despesa).
  4. `compra.status = 'CANCELADO'`, `save()`.
  Tudo em `transaction.atomic()`.
- **RF-11** — Tela frontend `Compras.jsx`: listagem (fornecedor, NF, data, valor total, status com badge colorido, ação Cancelar) + modal "Nova Compra" em formato carrinho (fornecedor + conta + NF + data + forma de pagamento + status inicial + busca de produto estilo `BuscaProdutoRapida` para adicionar itens com quantidade/unidade/valor unitário de custo + total ao vivo) + confirmar cria tudo de uma vez via `POST /api/v1/compras/`.

## 4. Regras de Negócio (RN)

- **RN-01** — `ItemCompra.unidade` segue a mesma cadeia de conversão de `MovimentoEstoque` (herdada da Manutenção #37/#58): sem fallback 1:1 silencioso, unidade sem `ConversaoUnidade` cadastrada levanta `400` **antes** de persistir qualquer coisa (a checagem acontece no `validate()` do serializer, chamando `fator_para_base`, do mesmo jeito que o endpoint de movimentos da Fase 1 já faz).
- **RN-02** — Compra precisa ter **pelo menos 1 item** (mesma regra de `ComboSerializer.validate_itens`, RN-01 do Combo — Manutenção #53). `quantidade` e `valor_unitario_custo` de cada item devem ser `> 0`.
- **RN-03** — Reversão de estoque no cancelamento (RF-10.2) recalcula o fator de conversão **no momento do cancelamento**, não reusa o fator gravado na compra original. Se a tabela de conversão do produto mudar entre a compra e o cancelamento, a reversão pode não ser bit-a-bit simétrica — risco aceito e documentado (cenário raro: produto mudando conversão de unidade justamente entre compra e cancelamento). Não bloqueante para esta fase.
- **RN-04** — `financeiro.Despesa.fornecedor` **continua `CharField`** (não vira FK nesta fase) — Despesas avulsas não vindas de Compra continuam existindo e usam texto livre normalmente. A Compra só *preenche* esse texto a partir do cadastro real de Fornecedor; não há migração de dado histórico (Despesas antigas mantêm o texto que já tinham).
- **RN-05** — `Compra` e `ItemCompra` são **imutáveis após criação**, exceto a transição de `status` (RF-08) — mesmo espírito da regra absoluta de `LivroCaixa` (`ReadCreateViewSet`, sem PUT/PATCH/DELETE de itens) já em vigor no projeto. Para "corrigir" uma compra lançada errada, o fluxo é **cancelar (RF-10) e lançar uma nova** — nunca editar itens de uma compra existente. Evita duplicidade/inconsistência entre `MovimentoEstoque` já aplicado e um novo valor de item editado.
- **RN-06** — A transição de status só é permitida `PENDENTE → PAGO` (nunca o contrário, e nunca direto para `CANCELADO` via PATCH — cancelamento é sempre via ação dedicada RF-10, que tem efeitos colaterais de reversão que um PATCH simples de `status` não deve disparar por engano).
- **RN-07** — `Categoria` "Compra de Mercadoria" (RF-09) é a única categoria usada pelo signal de RF-07 — não há mapeamento por `CategoriaFornecedor` (ex.: `MATERIA_PRIMA` → categoria financeira diferente) nesta fase. Fica documentado como possível refinamento futuro, fora de escopo agora.
- **RN-08** — Todos os endpoints de `compras` exigem `IsAdmin` (mesmo padrão de `DespesaViewSet`/`ReceitaViewSet` pós-Manutenção #54 — RN08 daquela manutenção), não `IsAuthenticated` genérico — Compra tem efeito financeiro direto.

## 5. Fora de escopo (Fase 2)

- Mapear `CategoriaFornecedor` → categoria financeira específica por tipo de compra (RN-07).
- Edição de itens de uma compra já criada (RN-05) — só cancelar e recriar.
- Parcelamento de compra (uma Compra gera sempre exatamente 1 Despesa) — parcelamento fica para uma fase futura, se necessário (reaproveitaria `pagamentos.Parcela`, já existente no sistema para outro fluxo).
- Anexo de PDF/XML da nota fiscal (`Despesa.comprovante` já existe como `FileField` — poderia ser reaproveitado depois, não faz parte desta especificação).
- Relatório de compras por fornecedor/período.

---

## 6. Spec Backend

### 6.1 Novo app `compras`

```
backend/compras/
├── __init__.py
├── apps.py           # ComprasConfig, default_auto_field, name='compras'
├── models.py
├── signals.py
├── serializers.py
├── views.py
├── urls.py
├── admin.py
├── tests.py
└── migrations/
    ├── 0001_initial.py
    └── 0002_categoria_compra_mercadoria.py   # RunPython, RF-09
```

`compras/apps.py` precisa de `ready()` importando `signals` (mesmo padrão de `financeiro/apps.py`, confirmar antes de implementar).

`config/settings.py` (ou `core/settings.py` — confirmar nome exato no momento da implementação): adicionar `'compras'` em `INSTALLED_APPS`.

`core/urls.py`:
```python
path('api/v1/compras/', include('compras.urls')),
```

### 6.2 `compras/models.py`

```python
from decimal import Decimal

from django.conf import settings
from django.db import models

from common.models import BaseModel
from fornecedores.models import Fornecedor
from financeiro.models import Conta, FormaPagamento, Despesa
from produtos.models import Produto, UnidadeBase, MovimentoEstoque, TipoMovimento


class StatusCompra(models.TextChoices):
    PENDENTE = 'PENDENTE', 'Pendente'
    PAGO = 'PAGO', 'Pago'
    CANCELADO = 'CANCELADO', 'Cancelado'


class Compra(BaseModel):
    fornecedor = models.ForeignKey(Fornecedor, on_delete=models.PROTECT, related_name='compras')
    conta = models.ForeignKey(Conta, on_delete=models.PROTECT, related_name='compras')
    numero_nota_fiscal = models.CharField(max_length=50, blank=True, default='')
    data_emissao = models.DateField()
    forma_pagamento = models.CharField(max_length=20, choices=FormaPagamento.choices, blank=True)
    status = models.CharField(max_length=20, choices=StatusCompra.choices, default=StatusCompra.PENDENTE)
    valor_total = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)
    observacoes = models.TextField(blank=True, default='')
    despesa = models.OneToOneField(
        Despesa, null=True, blank=True, on_delete=models.SET_NULL, related_name='compra',
    )
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='+',
    )

    class Meta:
        db_table = 'cmp_compra'
        ordering = ['-data_emissao', '-created_at']
        verbose_name = 'Compra'
        verbose_name_plural = 'Compras'

    def __str__(self):
        return f'Compra #{self.pk} — {self.fornecedor.nome_razao_social} — R$ {self.valor_total}'


class ItemCompra(models.Model):
    # Sem BaseModel, mesmo racional de ItemCombo (Manutencao 53): filho de
    # Compra, ciclo de vida atrelado ao pai, imutavel apos criacao (RN-05).
    compra = models.ForeignKey(Compra, on_delete=models.CASCADE, related_name='itens')
    produto = models.ForeignKey(Produto, on_delete=models.PROTECT, related_name='compra_itens')
    quantidade = models.DecimalField(max_digits=12, decimal_places=3)
    unidade = models.CharField(max_length=2, choices=UnidadeBase.choices)
    valor_unitario_custo = models.DecimalField(max_digits=12, decimal_places=2)
    movimento_estoque = models.OneToOneField(
        MovimentoEstoque, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='item_compra',
    )

    class Meta:
        db_table = 'cmp_item_compra'
        verbose_name = 'Item da Compra'
        verbose_name_plural = 'Itens da Compra'

    @property
    def subtotal(self):
        return self.quantidade * self.valor_unitario_custo

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            movimento = MovimentoEstoque.objects.create(
                produto=self.produto,
                tipo=TipoMovimento.ENTRADA,
                quantidade=self.quantidade,
                unidade=self.unidade,
                nota_fiscal=self.compra.numero_nota_fiscal,
                observacoes=f'Compra #{self.compra_id} — {self.compra.fornecedor.nome_razao_social}',
            )
            ItemCompra.objects.filter(pk=self.pk).update(movimento_estoque=movimento)
            # RF-05: ultimo custo sobrescreve Produto.valor_unitario
            Produto.objects.filter(pk=self.produto_id).update(
                valor_unitario=self.valor_unitario_custo,
            )

    def __str__(self):
        return f'{self.compra} — {self.produto.nome} x{self.quantidade}'
```

> Atenção Forge: `MovimentoEstoque.save()` (Fase 1) já roda dentro de `ItemCompra.save()` acima — **não** reimplementar a resolução de `fator_para_base` nem o `F()` de estoque aqui. Se `fator_para_base` levantar `ValidationError` (unidade sem conversão), ela precisa borbulhar até o serializer/view para virar `400` — não capturar silenciosamente dentro do `save()` do model.

### 6.3 `financeiro/services.py` — extrair `estornar_despesa()`

Mover o bloco de `DespesaViewSet.estornar_despesa` (views.py:262-322) para uma função nova em `financeiro/services.py`, mesmo padrão de `estornar_receita()` já existente no arquivo:

```python
def estornar_despesa(despesa, motivo, data_estorno=None, usuario=None):
    if despesa.status != 'PAGO':
        raise ValidationError({'detail': 'Somente despesas com status PAGO podem ser estornadas.'})
    if despesa.estornado:
        raise ValidationError({'detail': 'Despesa já foi estornada.'})
    if not motivo or not str(motivo).strip():
        raise ValidationError({'motivo': 'Motivo do estorno é obrigatório.'})

    data_estorno = data_estorno or _date.today()
    conta = despesa.conta
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute('SELECT pg_advisory_xact_lock(%s)', [conta.id])
        # ... resto do bloco já existente, sem alteração de comportamento ...
    return lancamento
```

`DespesaViewSet.estornar_despesa` (view) passa a só validar o request (parse de data/motivo) e chamar `estornar_despesa(...)`, devolvendo `400` em `ValidationError` — **mesmo comportamento observável de hoje**, só reorganização para reaproveitar em `compras`. Cobrir com o mesmo teste que já existe para o endpoint (regressão zero).

### 6.4 `compras/signals.py`

```python
from datetime import date

from django.db.models.signals import post_save
from django.dispatch import receiver

from financeiro.models import Categoria, Despesa

from .models import Compra


@receiver(post_save, sender=Compra)
def compra_sincroniza_despesa(sender, instance, created, **kwargs):
    if created:
        categoria = Categoria.objects.filter(
            nome='Compra de Mercadoria', tipo='SAIDA', is_active=True,
        ).first()
        despesa = Despesa.objects.create(
            tipo='VARIAVEL',
            descricao=f'Compra #{instance.pk} — NF {instance.numero_nota_fiscal or "s/n"} — '
                      f'{instance.fornecedor.nome_razao_social}',
            fornecedor=instance.fornecedor.nome_razao_social,
            valor_bruto=instance.valor_total,
            conta=instance.conta,
            categoria=categoria,
            forma_pagamento=instance.forma_pagamento,
            status=instance.status,
            vencimento=instance.data_emissao,
            pagamento=instance.data_emissao if instance.status == 'PAGO' else None,
            observacoes=instance.observacoes,
            criado_por=instance.criado_por,
        )
        Compra.objects.filter(pk=instance.pk).update(despesa=despesa)
        return

    if instance.despesa_id and instance.despesa.status != instance.status:
        despesa = instance.despesa
        despesa.status = instance.status
        if instance.status == 'PAGO' and not despesa.pagamento:
            despesa.pagamento = date.today()
        despesa.save()  # re-dispara financeiro.signals.despesa_para_livro_caixa
```

> Ponto de atenção para o Forge: o `update()` em `Compra.objects.filter(pk=...).update(despesa=despesa)` dentro do próprio handler de `post_save` **não** dispara o signal de novo (`update()` de queryset não chama `save()`/signals) — é o mesmo truque já usado em `ProdutoSerializer.create()` da Fase 1 (`produto.refresh_from_db(...)` depois de um `MovimentoEstoque` criado à parte). Confirmar em teste que `instance.despesa` (em memória, no restante da request) não fica desatualizado — usar `instance.refresh_from_db()` se necessário antes de serializar a resposta do `POST`.

### 6.5 `compras/serializers.py`

```python
class ItemCompraSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='pk', read_only=True)
    produto_nome = serializers.CharField(source='produto.nome', read_only=True)
    subtotal = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = ItemCompra
        fields = ['id', 'produto', 'produto_nome', 'quantidade', 'unidade', 'valor_unitario_custo', 'subtotal']

    def validate(self, data):
        from produtos.services import fator_para_base
        from django.core.exceptions import ValidationError as DjangoValidationError
        if data['quantidade'] <= 0:
            raise serializers.ValidationError({'quantidade': 'Deve ser maior que zero.'})
        if data['valor_unitario_custo'] <= 0:
            raise serializers.ValidationError({'valor_unitario_custo': 'Deve ser maior que zero.'})
        try:
            fator_para_base(data['produto'], data['unidade'])  # RN-01 — só valida, não usa o retorno aqui
        except DjangoValidationError as exc:
            raise serializers.ValidationError({'unidade': exc.messages})
        return data


class CompraSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='pk', read_only=True)
    itens = ItemCompraSerializer(many=True)
    fornecedor_nome = serializers.CharField(source='fornecedor.nome_razao_social', read_only=True)
    conta_nome = serializers.CharField(source='conta.nome', read_only=True)

    class Meta:
        model = Compra
        fields = [
            'id', 'fornecedor', 'fornecedor_nome', 'conta', 'conta_nome',
            'numero_nota_fiscal', 'data_emissao', 'forma_pagamento', 'status',
            'valor_total', 'observacoes', 'itens', 'despesa',
            'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['valor_total', 'despesa', 'is_active', 'created_at', 'updated_at']

    def validate_itens(self, value):
        if not value:
            raise serializers.ValidationError('A compra precisa ter pelo menos 1 item.')  # RN-02
        return value

    def create(self, validated_data):
        itens_data = validated_data.pop('itens')
        valor_total = sum(
            (i['quantidade'] * i['valor_unitario_custo'] for i in itens_data), Decimal('0.00'),
        )
        compra = Compra.objects.create(valor_total=valor_total, **validated_data)
        for item in itens_data:
            ItemCompra.objects.create(compra=compra, **item)
        return compra


class CompraStatusUpdateSerializer(serializers.ModelSerializer):
    """RF-08: PATCH só aceita status (PENDENTE->PAGO, RN-06) e observacoes."""
    class Meta:
        model = Compra
        fields = ['status', 'observacoes']

    def validate_status(self, value):
        if self.instance.status != 'PENDENTE' or value != 'PAGO':
            raise serializers.ValidationError('Única transição permitida via PATCH é PENDENTE -> PAGO.')
        return value
```

### 6.6 `compras/views.py`

```python
class CompraViewSet(viewsets.ModelViewSet):
    queryset = Compra.objects.filter(is_active=True).select_related(
        'fornecedor', 'conta', 'despesa',
    ).prefetch_related('itens__produto')
    permission_classes = [IsAdmin]  # RN-08
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'fornecedor', 'conta']
    search_fields = ['numero_nota_fiscal', 'fornecedor__nome_razao_social']
    ordering_fields = ['data_emissao', 'valor_total', 'status']
    http_method_names = ['get', 'post', 'patch', 'head', 'options']  # RN-05: sem put/delete

    def get_serializer_class(self):
        return CompraStatusUpdateSerializer if self.request.method == 'PATCH' else CompraSerializer

    def perform_create(self, serializer):
        serializer.save(criado_por=self.request.user)

    @action(detail=True, methods=['post'])
    def cancelar(self, request, pk=None):
        # RF-10 — ver spec completa na secao 3
        ...
```

### 6.7 `compras/urls.py`

```python
from rest_framework.routers import DefaultRouter
from .views import CompraViewSet

router = DefaultRouter()
router.register(r'', CompraViewSet, basename='compra')

urlpatterns = router.urls
```
Endpoint final: `/api/v1/compras/`, ação de cancelar em `/api/v1/compras/{id}/cancelar/`.

---

## 7. Spec Frontend (`frontend/src/pages/Compras.jsx`, novo arquivo)

- Nova página, registrada em `frontend/src/routes/index.jsx` (`/compras`) e item de menu na `Sidebar.jsx` (seção próxima de Produtos/Fornecedores).
- **Listagem:** tabela com Fornecedor, NF, Data Emissão, Valor Total (BRL), Status (badge: cinza=Pendente, verde=Pago, vermelho=Cancelado), ação "Cancelar" (ícone lixeira, `window.confirm` + prompt de motivo, some se já `CANCELADO`). Filtro por status e busca por fornecedor/NF (`SearchFilter` do backend).
- **Modal "Nova Compra":**
  - Cabeçalho: `Select` de Fornecedor (busca por nome, reaproveitando padrão de autocomplete já usado em Vendas/PDV), `Select` de Conta, input NF, input Data de Emissão, `Select` Forma de Pagamento, `Select` Status inicial (Pendente/Pago).
  - Seção de itens (carrinho): campo de busca de produto igual `BuscaProdutoRapida` (Manutenção #32) — buscar → clicar → linha criada com produto, quantidade padrão 1, unidade padrão = `unidade_base` do produto (com `Select` para trocar, populado com `unidade_base` + `conversoes` do produto, mesmo padrão do modal `MovimentarEstoque` da Fase 1), campo Valor Unitário de Custo.
  - Total ao vivo calculado no frontend (soma de `quantidade × valor_unitario_custo`) — **só exibição**, o backend recalcula por conta própria e é o valor que efetivamente persiste (RF-06).
  - Botão remover item da lista antes de confirmar.
  - Confirmar → `POST /api/v1/compras/` com `{fornecedor, conta, numero_nota_fiscal, data_emissao, forma_pagamento, status, observacoes, itens: [...]}`. Erro de unidade sem conversão (`400` em `itens[i].unidade`) exibido inline na linha do item correspondente (mesmo padrão de erro por campo já usado no formulário de Produto).
  - Após sucesso: fecha modal, refetch da listagem, toast de sucesso mencionando se a Despesa foi criada como Pendente ou Paga.
- Sem edição de compra existente (RN-05) — só visualização (modal read-only ao clicar na linha, mostrando itens e o link para a Despesa gerada) e cancelamento.

---

## 8. Critérios de Aceite (Sentinel)

**Backend:**
- CA-01: `POST /api/v1/compras/` com fornecedor, conta, 2 itens válidos → `201`; `Compra.valor_total` em banco bate exatamente com a soma dos subtotais dos itens enviados.
- CA-02: Mesma criação do CA-01 → confirmar em banco: 2 `MovimentoEstoque` criados (`tipo=ENTRADA`), `Produto.quantidade_estoque` de cada produto envolvido incrementado corretamente (com conversão de unidade quando aplicável).
- CA-03: Mesma criação do CA-01 → `Produto.valor_unitario` de cada produto atualizado para o `valor_unitario_custo` do respectivo item (RF-05).
- CA-04: Mesma criação do CA-01 → 1 `financeiro.Despesa` criada, `categoria.nome == 'Compra de Mercadoria'`, `valor_bruto == compra.valor_total`, `fornecedor` (texto) == `compra.fornecedor.nome_razao_social`, `status` == `compra.status` enviado no payload.
- CA-05: Criar Compra com `status=PENDENTE` → Despesa criada com `status=PENDENTE`, `pagamento=None`, **nenhum** `LivroCaixa` criado (confirmar ausência via query `LivroCaixa.objects.filter(origem='DESPESA', origem_id=despesa.id)`).
- CA-06: Criar Compra com `status=PAGO` → Despesa criada com `status=PAGO`, `pagamento=data_emissao`, e **1** `LivroCaixa` criado automaticamente pelo signal já existente (`despesa_para_livro_caixa`), valor batendo com `valor_liquido` da Despesa.
- CA-07: `PATCH /api/v1/compras/{id}/` com `{status: 'PAGO'}` numa Compra `PENDENTE` → `200`; Despesa vinculada atualizada para `PAGO`; `LivroCaixa` criado nesse momento (não antes).
- CA-08: `PATCH` tentando mudar `fornecedor`, `conta` ou enviar `itens` → esses campos são ignorados (não alteram o registro em banco); resposta `200` reflete só `status`/`observacoes` alterados.
- CA-09: `PATCH` com `status=CANCELADO` → `400` (RN-06, transição não permitida via PATCH).
- CA-10: `POST /api/v1/compras/{id}/cancelar/` numa Compra `PAGO` (com `LivroCaixa` já criado) → `200`; `Compra.status='CANCELADO'`; estoque de cada produto revertido (movimento `AJUSTE` negativo confirmado em banco); `Despesa.estornado=True`; novo `LivroCaixa` de estorno criado em par com o original (mesmo padrão de `estornar_despesa`, `saldo_atual` da conta recalculado corretamente).
- CA-11: `POST .../cancelar/` numa Compra `PENDENTE` (sem `LivroCaixa`) → `200`; estoque revertido; `Despesa.is_active=False`; **nenhum** `LivroCaixa` de estorno criado (nunca existiu o original).
- CA-12: `POST .../cancelar/` numa Compra já `CANCELADO` → `400`.
- CA-13: `POST /api/v1/compras/` com item cuja `unidade` não tem `ConversaoUnidade` cadastrada para o produto → `400` em `itens[i].unidade`; **nenhuma** Compra, Despesa ou MovimentoEstoque persistido (rollback completo da transação).
- CA-14: `POST /api/v1/compras/` sem nenhum item (`itens: []`) → `400` (RN-02).
- CA-15: `POST /api/v1/compras/` com `quantidade` ou `valor_unitario_custo` ≤ 0 em algum item → `400`.
- CA-16: Endpoint `/api/v1/compras/` retorna `401` sem autenticação e `403` para usuário autenticado sem perfil ADMIN (RN-08).
- CA-17: `DespesaViewSet.estornar_despesa` (endpoint já existente, Manutenção anterior) continua funcionando **sem nenhuma regressão** após a extração para `financeiro/services.py::estornar_despesa()` — mesmo teste que já cobre esse endpoint hoje passando sem alteração de asserts.
- CA-18: `showmigrations` sem pendências pós-deploy; migration `0002_categoria_compra_mercadoria` idempotente (rodar `migrate` duas vezes não duplica a Categoria).
- CA-19: Suíte completa do backend passando, 0 falhas, incluindo os testes novos de `compras/tests.py` e os já existentes de `produtos`/`financeiro` sem regressão.

**Frontend:**
- CA-20: Criar compra pelo modal, com 2+ itens buscados via campo de produto → aparece na listagem com valor total correto, sem reload manual.
- CA-21: Trocar unidade de um item no carrinho para uma sem conversão cadastrada e confirmar → erro exibido inline na linha certa, compra não é criada, carrinho preservado (usuário não perde o que já preencheu).
- CA-22: Cancelar uma compra da listagem → prompt de motivo, badge muda para "Cancelado", linha não permite mais a ação Cancelar.
- CA-23: `npm run build` limpo, 0 erros.

---

## 9. Observações para o Planner/Sentinel

- Esta especificação cobre **apenas a Fase 2** (módulo Compras). Fase 1 (`MovimentoEstoque` genérico) já está em produção e não é alterada — só reaproveitada via import direto (`produtos.services.fator_para_base`, `produtos.models.MovimentoEstoque`).
- Ponto de atenção principal para o Forge: a extração de `estornar_despesa()` para `financeiro/services.py` (seção 6.3) **toca um endpoint já em produção** (`DespesaViewSet.estornar_despesa`) — rodar a suíte de testes de `financeiro` inteira antes e depois da extração para garantir 0 regressão de comportamento observável (mesmo status code, mesmo payload de resposta, mesmo efeito em `LivroCaixa`).
- `compras` depende de `fornecedores`, `produtos` e `financeiro` — nenhum desses três apps deve precisar importar `compras` de volta (evitar dependência circular). Confirmar com `grep -rn "import compras\|from compras" backend/{fornecedores,produtos,financeiro}/` retornando vazio antes de considerar a Fase 2 concluída.
- `Categoria.objects.filter(nome='Compra de Mercadoria', ...).first()` no signal (RF-07) pode retornar `None` se a migration de seed (RF-09) não tiver rodado ainda em algum ambiente — nesse caso a Despesa é criada com `categoria=None`, sem erro, mas sem categorização (`limit_choices_to` do campo é só validação de formulário, não bloqueia `create()` direto via ORM). Documentar isso no teste do signal para não ser surpresa depois.
