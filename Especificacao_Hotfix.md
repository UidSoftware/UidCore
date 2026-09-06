# Especificação Hotfix — Manutenção #58 (FASE 1)

**Sistema:** UidCore (OS #7)
**Módulo:** `produtos` (estoque)
**Tipo:** `bug` (quantidade_estoque ignorada silenciosamente) + `feature_pequena` (generalização de movimentação de estoque)
**Requer aprovação comercial:** não — correção/evolução de módulo já contratado (Produtos/Estoque)
**Analista:** leitura de código confirmada em `backend/produtos/{models,serializers,views,services}.py`, `backend/pdv/{views,services}.py`, `frontend/src/pages/Produtos.jsx`

---

## 1. Diagnóstico confirmado (causa raiz)

- `ProdutoSerializer.Meta.read_only_fields` inclui `quantidade_estoque` (serializers.py:86). Qualquer `POST`/`PATCH` em `/produtos/` que mande esse campo é **descartado silenciosamente pelo DRF** — sem erro, sem warning.
- `frontend/src/pages/Produtos.jsx` envia `quantidade_estoque` dentro do `payload` tanto na criação quanto na edição (`handleSubmit`, linha 402 `stripEmptyStrings(form)`) — usuário edita o campo "Qtd em Estoque" no modal (linha 789-798), recebe toast de sucesso, mas o valor em banco nunca muda.
- Efeito colateral não citado no relato original, mas confirmado na leitura: isso também afeta a **criação** de produto — o valor digitado em "Qtd em Estoque" ao cadastrar um produto novo também é descartado; todo produto novo nasce com `quantidade_estoque=0`, só corrigível hoje registrando uma "Entrada de Estoque" manual depois de salvar.
- `Produto.quantidade_estoque` já é alterado corretamente em outros dois pontos, ambos via `F()` (atômico, sem race condition): `EntradaEstoque.save()` (models.py:106-125) e `pdv/services.py::_debitar_estoque`/`_reverter_estoque` (linhas 70-83). O padrão correto já existe no sistema — o bug é o único caminho (`ProdutoSerializer`) que tenta (e falha) alterar o campo por overwrite direto em vez de por movimento.

**Compatibilidade com PDV (verificada antes de propor a mudança):** o módulo `pdv` **não usa o model `EntradaEstoque`** em nenhum ponto — `pdv/services.py` só reaproveita a função `produtos.services.fator_para_base` (conversão de unidade) e debita/credita `Produto.quantidade_estoque` diretamente via `F()`, comentando explicitamente que é "a operação INVERSA exata de `EntradaEstoque.save()`". Isso significa que renomear/generalizar `EntradaEstoque` **não quebra nada no PDV** — não há FK, import de model nem serializer compartilhado. Único consumidor do endpoint `/produtos/{id}/entradas/` hoje é o próprio `frontend/src/pages/Produtos.jsx`.

---

## 2. Decisão de arquitetura (Fase 1)

**Generalizar `EntradaEstoque` → `MovimentoEstoque`** (renomear o model, não criar um novo em paralelo). Justificativa:
- Zero consumidor externo além do próprio `Produtos.jsx` (confirmado acima) — não há custo de compatibilidade retroativa a pagar.
- Reaproveita 100% do padrão já correto de `save()` com `F()` e a resolução de cadeia via `fator_para_base` (services.py) — só adiciona a dimensão `tipo` (sinal do efeito) que hoje é implicitamente sempre positivo.
- Evita duas tabelas fazendo a mesma coisa (`EntradaEstoque` + `MovimentoEstoque` novo) — o pedido já cita isso como bug de design a evitar.

Rota `/produtos/{id}/entradas/` é **renomeada** para `/produtos/{id}/movimentos/` (sem alias de compatibilidade — único consumidor é atualizado na mesma manutenção).

---

## 3. Requisitos Funcionais (RF)

- **RF-01** — Renomear model `EntradaEstoque` → `MovimentoEstoque` (migration com `RenameModel` + `db_table` → `prd_movimento_estoque`), adicionando campo `tipo` (choices `TipoMovimento`: `ENTRADA`, `ENTRADA_INICIAL`, `DEVOLUCAO_CLIENTE`, `PERDA`, `AJUSTE`, `SAIDA_MANUAL`). Registros existentes recebem `tipo=ENTRADA` via default do campo na migration (comportamento retroativo correto — todos eram entradas).
- **RF-02** — `Produto.quantidade_estoque` só pode mudar via `MovimentoEstoque.save()` (F() expression) ou via débito/reversão já existentes no `pdv/services.py`. Nenhum outro caminho (serializer/endpoint de Produto) pode escrever nesse campo.
- **RF-03** — `ProdutoSerializer.quantidade_estoque` permanece `read_only`. Frontend remove o input editável do modal de edição de produto e mostra o valor atual como texto informativo + botão "Movimentar Estoque".
- **RF-04** — Criação de produto (`ProdutoSerializer.create()`) aceita campo `write_only` **`estoque_inicial`** (Decimal, opcional, default `0`). Se `estoque_inicial > 0`, o `create()` cria um `MovimentoEstoque` interno `tipo=ENTRADA_INICIAL` na `unidade_base` do produto recém-criado (fator de conversão = 1, é a própria base).
- **RF-05** — Endpoint `GET/POST /produtos/{id}/movimentos/` (renomeado de `/entradas/`) aceita o campo `tipo` no POST. `GET` lista movimentos ativos ordenados por `-created_at`, expondo `tipo`, `tipo_display`, `efeito` (`+`/`-`), `quantidade`, `unidade`, `quantidade_base`, `nota_fiscal`, `observacoes`, `created_at`.
- **RF-06** — Nova seção/aba "Movimentar Estoque" no modal de edição de produto (substitui "Entradas de Estoque"): seletor `tipo` (opções visíveis ao usuário: Entrada, Devolução de Cliente, Perda/Quebra, Ajuste de Inventário, Saída Manual — `ENTRADA_INICIAL` é uso interno, nunca aparece no seletor) + campo motivo obrigatório para todo tipo exceto `ENTRADA`.
- **RF-07** — Backend nunca aplica um movimento que deixaria `quantidade_estoque` negativa sem confirmação explícita do usuário (ver RN-04).

## 4. Regras de Negócio (RN)

- **RN-01** — Efeito de cada `tipo` sobre `quantidade_estoque`:

  | Tipo | Efeito | Quantidade aceita |
  |---|---|---|
  | `ENTRADA` | `+quantidade_base` | > 0 |
  | `ENTRADA_INICIAL` | `+quantidade_base` | > 0 (uso interno, via `ProdutoSerializer.create()`) |
  | `DEVOLUCAO_CLIENTE` | `+quantidade_base` | > 0 |
  | `PERDA` | `-quantidade_base` | > 0 |
  | `SAIDA_MANUAL` | `-quantidade_base` | > 0 |
  | `AJUSTE` | `+quantidade_base` (sinal já embutido) | ≠ 0, pode ser negativo |

  Para todos os tipos exceto `AJUSTE`, `quantidade` deve ser estritamente positiva (validação no serializer) — o sinal do efeito vem do `tipo`, não do valor digitado. Só `AJUSTE` aceita valor negativo diretamente (delta assinado, para corrigir contagem de inventário pra cima ou pra baixo).
- **RN-02** — Campo `observacoes` funciona como "motivo" do movimento. Obrigatório (validação de serializer, não de model — mantém retrocompatibilidade com dados antigos) quando `tipo != ENTRADA`. Continua opcional só para `ENTRADA` (mantém UX atual de entrada simples com nota fiscal).
- **RN-03** — Conversão de unidade continua via `produtos.services.fator_para_base` (RN-01/RN-05 da Manutenção #37, inalteradas) — sem fallback 1:1 silencioso; unidade sem conversão cadastrada levanta 400.
- **RN-04 (estoque negativo — item 7 do pedido)** — Antes de persistir um movimento cujo efeito é negativo (`PERDA`, `SAIDA_MANUAL`, `AJUSTE` com valor negativo), a view calcula `produto.quantidade_estoque + delta`. Se o resultado for `< 0`:
  - sem `forcar_negativo=true` no payload → responde `400` com `{"confirmacao_necessaria": true, "mensagem": "Esta operação deixará o estoque negativo (X). Confirmar mesmo assim?", "quantidade_resultante": "X"}`, **sem** persistir nada;
  - com `forcar_negativo=true` → persiste normalmente, permitindo estoque negativo (cenário real: perda registrada antes da contagem física ser corrigida).
- **RN-05** — `estoque_inicial` do `ProdutoSerializer` é `write_only`, nunca aparece no retorno da API (o retorno usa sempre `quantidade_estoque`, calculado pelo movimento criado).
- **RN-06** — `MovimentoEstoque.save()` preserva o comportamento de só atualizar `Produto.quantidade_estoque` em criação (`is_new`), nunca em edição/update de um movimento já existente (mesma regra herdada de `EntradaEstoque.save()`) — editar um movimento passado não deve re-somar o efeito no estoque atual. Fase 1 não implementa edição de movimento (só criação e leitura); documentado aqui para não regredir se isso for adicionado depois.
- **RN-07** — `nota_fiscal` continua campo livre/opcional, sem obrigatoriedade por tipo (não faz sentido nota fiscal em `PERDA`, mas não é bloqueado — só some da tela quando `tipo != ENTRADA`).

## 5. Fora de escopo (Fase 1)

- Relatório/dashboard de movimentações por tipo/período.
- Permissão por perfil sobre quem pode registrar `PERDA`/`AJUSTE` (Fase 1: qualquer usuário autenticado com acesso a Produtos, igual hoje).
- Edição/estorno de um `MovimentoEstoque` já criado.
- Alias de compatibilidade em `/produtos/{id}/entradas/` (decidido não manter — sem consumidor externo).

---

## 6. Spec Backend

### 6.1 Migration (`backend/produtos/migrations/0004_...py`)
1. `RenameModel('EntradaEstoque', 'MovimentoEstoque')`.
2. `AlterModelTable` → `db_table = 'prd_movimento_estoque'`.
3. `AddField('movimentoestoque', 'tipo', CharField(max_length=20, choices=TipoMovimento.choices, default='ENTRADA'))` — default cobre as linhas existentes automaticamente (todas eram entradas), sem precisar de `RunPython` separado.
4. Atualizar `related_name` de `Produto.entradas` → `Produto.movimentos` — **antes de aplicar**, rodar `grep -rn "\.entradas\b" backend/` para garantir que nenhum outro app usa esse `related_name` (confirmado nesta análise que `pdv` não usa, mas checar de novo no momento da implementação).

### 6.2 `models.py`
```python
class TipoMovimento(models.TextChoices):
    ENTRADA = 'ENTRADA', 'Entrada'
    ENTRADA_INICIAL = 'ENTRADA_INICIAL', 'Estoque Inicial'
    DEVOLUCAO_CLIENTE = 'DEVOLUCAO_CLIENTE', 'Devolução de Cliente'
    PERDA = 'PERDA', 'Perda/Quebra'
    AJUSTE = 'AJUSTE', 'Ajuste de Inventário'
    SAIDA_MANUAL = 'SAIDA_MANUAL', 'Saída Manual'

EFEITO_NEGATIVO = {TipoMovimento.PERDA, TipoMovimento.SAIDA_MANUAL}
# AJUSTE tem sinal embutido na própria quantidade (pode ser negativa).
# Os demais tipos são sempre positivos, validados no serializer.

class MovimentoEstoque(BaseModel):
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE, related_name='movimentos')
    tipo = models.CharField(max_length=20, choices=TipoMovimento.choices, default=TipoMovimento.ENTRADA)
    quantidade = models.DecimalField(max_digits=12, decimal_places=3)  # pode ser negativa só se tipo=AJUSTE
    unidade = models.CharField(max_length=2, choices=UnidadeBase.choices)
    quantidade_base = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    nota_fiscal = models.CharField(max_length=50, blank=True, default='')
    observacoes = models.TextField(blank=True, default='')  # usado como "motivo" fora de ENTRADA
    criado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')

    def save(self, *args, **kwargs):
        from .services import fator_para_base
        if self.unidade == self.produto.unidade_base:
            fator = Decimal('1')
        else:
            fator = fator_para_base(self.produto, self.unidade)
        self.quantidade_base = self.quantidade * fator

        is_new = self.pk is None
        super().save(*args, **kwargs)

        if is_new:
            delta = -self.quantidade_base if self.tipo in EFEITO_NEGATIVO else self.quantidade_base
            Produto.objects.filter(pk=self.produto_id).update(
                quantidade_estoque=models.F('quantidade_estoque') + delta,
            )
```
Manter docstring explicando a herança do padrão de `EntradaEstoque` (Manutenção #37/#58) para o próximo ciclo não reabrir a discussão de fallback 1:1.

### 6.3 `serializers.py`
- `MovimentoEstoqueSerializer` (renomeado de `EntradaEstoqueSerializer`): adiciona `tipo`, `tipo_display` (`get_tipo_display`), `efeito` (`SerializerMethodField` retornando `'+'` ou `'-'` a partir de `tipo`/sinal de `quantidade`).
  - `validate()`: se `tipo != AJUSTE` e `quantidade <= 0` → erro `{'quantidade': 'Deve ser maior que zero para este tipo de movimento.'}`. Se `tipo == AJUSTE` e `quantidade == 0` → erro `{'quantidade': 'Ajuste não pode ser zero.'}`. Se `tipo not in (ENTRADA, ENTRADA_INICIAL)` e `not observacoes.strip()` → erro `{'observacoes': 'Motivo obrigatório para este tipo de movimento.'}`.
  - `ENTRADA_INICIAL` **não** pode ser criado via este serializer quando chamado pelo endpoint público (`/produtos/{id}/movimentos/`) — validar `tipo != ENTRADA_INICIAL` nesse endpoint (retornar 400; é uso exclusivo do `ProdutoSerializer.create()` interno).
- `ProdutoSerializer`:
  - Mantém `quantidade_estoque` em `read_only_fields` (RF-03 — sem mudança de comportamento aqui, só reforça).
  - Adiciona `estoque_inicial = serializers.DecimalField(max_digits=12, decimal_places=3, write_only=True, required=False, default=Decimal('0'))`.
  - `create()`:
    ```python
    def create(self, validated_data):
        estoque_inicial = validated_data.pop('estoque_inicial', Decimal('0'))
        produto = super().create(validated_data)
        if estoque_inicial > 0:
            MovimentoEstoque.objects.create(
                produto=produto, tipo=TipoMovimento.ENTRADA_INICIAL,
                quantidade=estoque_inicial, unidade=produto.unidade_base,
                observacoes='Estoque inicial no cadastro do produto.',
            )
            produto.refresh_from_db(fields=['quantidade_estoque'])
        return produto
    ```
  - `estoque_inicial` não tem efeito em `update()` (não existe update customizado — herda de `ModelSerializer`; campo `write_only` sem tratamento especial em update é simplesmente ignorado, comportamento padrão do DRF — confirmar em teste que um PATCH com `estoque_inicial` não gera erro nem efeito colateral).

### 6.4 `views.py`
- Renomear `action(url_path='entradas')` → `action(url_path='movimentos')`, usando `MovimentoEstoqueSerializer`.
- No `POST`, antes de `serializer.save(...)`:
  ```python
  tipo = serializer.validated_data.get('tipo', TipoMovimento.ENTRADA)
  if tipo == TipoMovimento.ENTRADA_INICIAL:
      return Response({'tipo': ['Não permitido criar este tipo diretamente.']}, status=400)
  quantidade_base = serializer.validated_data['quantidade'] * fator_para_base(produto, serializer.validated_data['unidade'])
  delta = -quantidade_base if tipo in EFEITO_NEGATIVO else quantidade_base
  resultante = produto.quantidade_estoque + delta
  if resultante < 0 and not request.data.get('forcar_negativo'):
      return Response({
          'confirmacao_necessaria': True,
          'mensagem': f'Esta operação deixará o estoque negativo ({resultante}). Confirmar mesmo assim?',
          'quantidade_resultante': str(resultante),
      }, status=400)
  ```
  (O cálculo de `quantidade_base` aqui é só para a checagem prévia de confirmação — o `save()` do model recalcula por conta própria; a conversão é necessariamente feita duas vezes porque a checagem de confirmação precisa acontecer **antes** de persistir — documentar isso no código para não estranhar em revisão futura.)
- Manter tratamento de `DjangoValidationError` (RN-05 herdada da Manutenção #37) igual ao endpoint atual.

### 6.5 Compatibilidade com PDV — checklist de verificação (não deve exigir mudança de código)
- `pdv/views.py` e `pdv/services.py` **não importam** `EntradaEstoque`/`MovimentoEstoque` — só `produtos.services.fator_para_base`, que não muda. Nenhuma alteração necessária no app `pdv`.
- Rodar `grep -rn "EntradaEstoque" backend/` após a migration para garantir que nenhuma referência ficou órfã (docstrings podem ser atualizadas para `MovimentoEstoque` por clareza, não é bloqueante).

---

## 7. Spec Frontend (`frontend/src/pages/Produtos.jsx`)

- **Modal de criar/editar produto:**
  - Campo "Qtd em Estoque" (linhas 789-798) sai do grid editável.
  - **Modo criação** (`!editingId`): input numérico **`estoque_inicial`** (opcional, default vazio = 0, mesmo `step="0.001" min="0"`), label "Estoque Inicial".
  - **Modo edição** (`editingId`): texto somente leitura mostrando `{produto.quantidade_estoque} {produto.unidade_base}` com label "Estoque Atual" (sem input), reaproveitando o valor já carregado em `openEditModal`.
- **Seção "Entradas de Estoque" (linhas 938-1030) → renomear para "Movimentar Estoque":**
  - `novaEntrada` (renomear estado para `novoMovimento`) ganha campo `tipo`, `Select` com opções: Entrada, Devolução de Cliente, Perda/Quebra, Ajuste de Inventário, Saída Manual (sem `ENTRADA_INICIAL`).
  - Campo motivo: reaproveitar o input "Observações" já existente, tornando-o obrigatório (validação client-side + mensagem) quando `tipo !== 'ENTRADA'`.
  - Campo "Nota Fiscal" só aparece quando `tipo === 'ENTRADA'`.
  - Campo Quantidade: aceitar valor negativo (remover `min="0"`) apenas quando `tipo === 'AJUSTE'`; manter `min="0"` para os demais.
  - `handleRegistrarEntrada` → renomear para `handleRegistrarMovimento`, chamando `POST /produtos/{editingId}/movimentos/`.
  - **Fluxo de confirmação (RN-04):** se a resposta vier `400` com `confirmacao_necessaria: true`, exibir `window.confirm(payload.mensagem)`; se o usuário confirmar, reenviar o mesmo POST com `forcar_negativo: true` no body. Se recusar, manter o formulário aberto sem limpar os campos.
  - Listagem de movimentos (linhas 1022-1030): exibir `tipo_display` e sinal (`efeito`) ao lado da quantidade, ex.: `+10 UN — Entrada` / `-2 UN — Perda/Quebra`.
  - Todas as chamadas `api.get/post('/produtos/{id}/entradas/')` → `/produtos/{id}/movimentos/`.

---

## 8. Critérios de Aceite (Sentinel)

**Backend:**
- CA-01: `PATCH /produtos/{id}/` com `quantidade_estoque` no payload **não altera** o valor em banco (continua ignorado — comportamento intencional agora documentado, não é mais bug, é design).
- CA-02: `POST /produtos/` com `estoque_inicial=15` cria o produto com `quantidade_estoque=15` confirmado em banco, e cria 1 `MovimentoEstoque` com `tipo=ENTRADA_INICIAL`.
- CA-03: `POST /produtos/` sem `estoque_inicial` cria produto com `quantidade_estoque=0` e nenhum `MovimentoEstoque`.
- CA-04: `POST /produtos/{id}/movimentos/` com `tipo=ENTRADA` soma corretamente ao estoque (mesmo comportamento herdado de `EntradaEstoque`, incluindo conversão de unidade em cadeia — reaproveitar testes existentes de `EntradaEstoqueModelTest`/`EntradaEstoqueCadeiaTest` adaptados ao novo nome).
- CA-05: `POST .../movimentos/` com `tipo=PERDA` e `quantidade=5` **subtrai** 5 (em base) do estoque.
- CA-06: `POST .../movimentos/` com `tipo=AJUSTE` e `quantidade=-3` subtrai 3; com `quantidade=3` soma 3.
- CA-07: `POST .../movimentos/` com `tipo=PERDA` **sem** `observacoes` → `400` com erro em `observacoes`.
- CA-08: `POST .../movimentos/` com `tipo=ENTRADA` sem `observacoes` → `201` (continua opcional).
- CA-09: `POST .../movimentos/` cujo efeito deixaria estoque negativo, sem `forcar_negativo` → `400` com `confirmacao_necessaria: true`, **sem** alterar o estoque.
- CA-10: mesmo payload do CA-09 + `forcar_negativo: true` → `201`, estoque fica negativo, valor confirmado em banco.
- CA-11: `POST .../movimentos/` com `tipo=ENTRADA_INICIAL` direto pela API → `400` (bloqueado, uso interno).
- CA-12: unidade sem conversão cadastrada em qualquer tipo → `400` (RN-05 da Manutenção #37, herdada sem fallback 1:1 silencioso).
- CA-13: suíte completa do backend passando, 0 falhas, incluindo os testes já existentes de `produtos/tests.py` adaptados ao rename (`EntradaEstoque*` → `MovimentoEstoque*`).
- CA-14: `pdv/tests.py` — 0 regressão (confirma que a generalização não quebrou o módulo PDV, que não depende do model).
- CA-15: `showmigrations` sem pendências pós-deploy; migration de rename aplicada sem erro sobre dado já existente.

**Frontend:**
- CA-16: criar produto novo com "Estoque Inicial" preenchido → produto aparece na listagem já com o valor certo, sem precisar de ação extra.
- CA-17: editar produto existente → campo de estoque aparece como texto informativo, não editável, sem input.
- CA-18: aba "Movimentar Estoque" com seletor de tipo funcional; motivo obrigatório bloqueia envio (client-side) quando tipo ≠ Entrada.
- CA-19: fluxo de confirmação de estoque negativo funcionando (confirmar → aplica; cancelar → não aplica, formulário preservado).
- CA-20: `npm run build` limpo, 0 erros.
- CA-21: nenhuma referência residual a `/produtos/{id}/entradas/` no bundle final.

---

## 9. Observações para o Planner/Sentinel

- Esta especificação cobre **apenas a Fase 1** solicitada. Fases futuras (relatório de movimentações, permissão por perfil sobre `PERDA`/`AJUSTE`) não fazem parte deste ciclo e não devem ser cobradas no critério de aceite.
- Decisão de generalizar em vez de criar `MovimentoEstoque` do zero foi validada lendo `pdv/views.py` e `pdv/services.py` — confirmado que não há acoplamento direto ao model `EntradaEstoque`, só à função de conversão `fator_para_base`, que não muda.
- Ponto de atenção para o Forge: `related_name='entradas'` vira `related_name='movimentos'` — buscar por `.entradas.` no restante do backend antes de aplicar a migration, para não deixar nenhum `AttributeError` órfão fora do módulo `produtos`.
