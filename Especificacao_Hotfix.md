# Especificação — Manutenção #53
**Elaborado por:** Analista (MODO HOTFIX)
**Data:** 2026-08-25
**Sistema:** UidCore (OS #7)

**Solicitação original (resumida):**
Implementar no UidCore o sistema de **Combos de produtos**, portado do
SystemD (`/root/SystemD/backend/produtos/` — models `Combo`/`ItemCombo`,
`ComboViewSet`, `ComboSerializer`, seção Combos em `ProdutosPage.jsx`).
Não é bug — é feature nova que já existe validada em produção em outro
projeto Uid, precisa ser adaptada às convenções do UidCore (BaseModel,
serializer com `id=IntegerField(source='pk')`, dark mode navy/violet,
ausência de campo `tipo`/`criado_por` em `Produto`).

---

## Classificação

```
tipo: feature_pequena
sistema: UidCore
caminho_afetado: backend/produtos/ (models.py, serializers.py, views.py, urls.py, migrations/0003)
                 frontend/src/pages/Produtos.jsx (nova seção Combos abaixo da tabela)
complexidade: media
requer_aprovacao_comercial: false
```

---

## Diagnóstico confirmado (leitura direta do código)

Lido lado a lado:
- Origem (SystemD): `produtos/models.py`, `produtos/serializers.py`, `produtos/views.py`
- Destino (UidCore): `backend/produtos/models.py`, `serializers.py`, `views.py`, `urls.py`, `services.py`, `common/models.py` (`BaseModel`), `accounts/models.py` (`User`), `common/permissions.py`, `core/settings.py` (`REST_FRAMEWORK`)
- Frontend destino: `frontend/src/pages/Produtos.jsx` (805 linhas — já tem seções Produto + Conversões + Entradas de Estoque, dark mode navy/violet aplicado desde a Manutenção #31)

### Diferenças estruturais confirmadas entre origem e destino

| Aspecto | SystemD (origem) | UidCore (destino) | Decisão de adaptação |
|---|---|---|---|
| Base de auditoria | `ativo`, `criado_em`, `atualizado_em` soltos em cada model | `BaseModel` abstrato (`is_active`, `created_at`, `updated_at`) em `common/models.py` | `Combo` herda `BaseModel` — **não** redeclarar `ativo`/`criado_em`/`atualizado_em` |
| `Produto.tipo` | Existe (`PRODUTO`/`SERVICO`), Combo não depende dele | **Não existe** no UidCore (`Produto` só tem nome, codigo_barras, quantidade_estoque, estoque_minimo, unidade_base, valor_unitario, preco_venda, observacoes) | Nenhum ajuste necessário — Combo/ItemCombo do SystemD já não usa `Produto.tipo` em nenhum lugar (verificado: nem `views.py` nem `serializers.py` do Combo referenciam `tipo`) |
| Serializer `id` | `ComboSerializer` de origem já tinha `id=IntegerField(source='pk')`, mas `ProdutoSerializer` de lá usa `fields='__all__'` | Regra global Uid: todo serializer novo do UidCore declara `id = serializers.IntegerField(source='pk', read_only=True)` como primeiro campo (já é o padrão em `ConversaoUnidadeSerializer`, `EntradaEstoqueSerializer`, `ProdutoSerializer` do destino) | `ComboSerializer` e `ItemComboSerializer` seguem o padrão já usado no arquivo — SystemD já fazia isso no Combo por acaso, mantém |
| Autor do registro | `Combo.criado_por` FK `usuarios.Usuario` (SET_NULL) | `Produto` do UidCore **não tem** `criado_por`; mas `EntradaEstoque` do UidCore **tem** `criado_por` FK `settings.AUTH_USER_MODEL` (SET_NULL, `related_name='+'`) — precedente já existe no próprio app | `Combo.criado_por` FK `settings.AUTH_USER_MODEL`, null=True, blank=True, `on_delete=SET_NULL`, seguindo o padrão de `EntradaEstoque` (não o de `Produto`, que não rastreia autor) — decisão: manter rastreabilidade de quem criou o combo, é dado de auditoria útil e barato |
| Nome de usuário exibido | `criado_por.nome` (`Usuario.nome`) | `User` do UidCore usa `nome_completo` (não `nome` — `accounts/models.py` linha 8) | `criado_por_nome = serializers.CharField(source='criado_por.nome_completo', read_only=True, default='')` |
| Permissão | `IsAdminOrOperacional` (`usuarios.permissions`) — classe não existe no UidCore | UidCore usa `DEFAULT_PERMISSION_CLASSES = (IsAuthenticated,)` global (`core/settings.py`); `ProdutoViewSet` não sobrescreve `get_permissions` | `ComboViewSet` **não sobrescreve** `get_permissions` — segue o mesmo padrão de `ProdutoViewSet` (qualquer usuário autenticado do sistema acessa; não existe distinção Admin/Operacional no UidCore hoje) |
| Filtro de listagem | `DjangoFilterBackend + SearchFilter + OrderingFilter`, `filterset_fields` | `ProdutoViewSet` usa só `SearchFilter + OrderingFilter` (sem `filterset_fields`); `DjangoFilterBackend` está no `DEFAULT_FILTER_BACKENDS` global mas os ViewSets do app produtos não declaram `filterset_fields` | `ComboViewSet` usa `filter_backends = [filters.SearchFilter, filters.OrderingFilter]`, `search_fields = ['nome']`, `ordering_fields = ['nome', 'created_at']` — mesmo padrão de `ProdutoViewSet` |
| Soft delete | `instance.ativo = False; instance.save()` | Padrão UidCore já em uso: `instance.is_active = False; instance.save(update_fields=['is_active', 'updated_at'])` (ver `ProdutoViewSet.destroy`) | `ComboViewSet.destroy` replica exatamente o padrão de `ProdutoViewSet.destroy` |
| App de destino | App `produtos` própria do SystemD | App `produtos` **já existe** em `backend/produtos/` no UidCore, com `ConversaoUnidade`/`EntradaEstoque`/`services.py` (cadeia de conversão de unidade, Manutenção #37/#40) | Adicionar `Combo`/`ItemCombo` no `models.py` existente — **não criar app nova** |
| Migration | N/A (projeto próprio) | Última migration do app: `0002_conversaounidade_converte_para_and_more.py` | Nova migration `0003_combo_itemcombo.py` |
| `Produto` referenciado em `ItemCombo` | `on_delete=PROTECT` | Mesmo padrão adotado — `Produto` do UidCore não deve poder ser excluído fisicamente enquanto usado em um combo (soft delete de Produto não afeta isso: `ItemCombo.produto` continua apontando pro registro, mesmo se `Produto.is_active=False`) | Mantém `on_delete=models.PROTECT` |

### Confirmação: nenhuma colisão de nomes

`backend/produtos/models.py` atual não tem `Combo` nem `ItemCombo`.
`urls.py` atual só registra `ProdutoViewSet` na raiz do router
(`router.register(r'', ProdutoViewSet, basename='produto')`) — precisa de
um segundo `register` para `combos`.

---

## Requisitos Funcionais

```
RF-01 - O sistema deve permitir cadastrar um Combo com nome, descrição
        (opcional) e uma lista de itens (produto + quantidade + valor
        unitário)
RF-02 - O sistema deve calcular o valor_total do combo como a soma de
        (quantidade × valor_unitario) de cada item — property calculada,
        não persistida
RF-03 - O sistema deve permitir editar um Combo existente, incluindo
        substituir por completo a lista de itens (delete-and-recreate,
        igual ao comportamento de origem — SystemD já valida esse
        comportamento em produção)
RF-04 - O sistema deve permitir excluir (soft delete) um Combo — mesmo
        padrão de Produto: is_active=False, nunca DELETE físico
RF-05 - O sistema deve listar Combos ativos com busca por nome e
        paginação (mesmo padrão de Produtos — response.data.results)
RF-06 - A tela de Produtos deve exibir uma seção "Combos" abaixo da
        tabela/lista de produtos, com botão "🎁 Combo" no header para
        abrir o modal de criação
RF-07 - O modal de Combo deve permitir adicionar/remover linhas de item
        (produto via Select + quantidade + valor unitário), com valor
        total recalculado em tempo real no cliente
RF-08 - Desktop: tabela de Combos. Mobile: cards — mesmo padrão
        responsivo já usado na tabela de Produtos (breakpoint md)
```

## Requisitos Não Funcionais

```
RNF-01 - Segue os tokens de dark mode navy/violet já estabelecidos no
         projeto (Manutenção #31) — nada de inline style ao estilo
         SystemD original
RNF-02 - id = serializers.IntegerField(source='pk', read_only=True) como
         primeiro campo em ComboSerializer e ItemComboSerializer
         (regra global Uid)
RNF-03 - Soft delete via is_active — nunca .delete() físico em Combo
RNF-04 - DecimalField para todo valor monetário/quantidade (nunca Float)
RNF-05 - Erros de validação exibidos via extractErrorMessage (padrão já
         usado em todo Produtos.jsx)
```

## Regras de Negócio

```
RN-01 - Um Combo precisa ter pelo menos 1 item (validate_itens rejeita
        lista vazia) — igual à origem
RN-02 - Quantidade de cada item deve ser maior que zero — igual à origem
RN-03 - valor_unitario de ItemCombo é um SNAPSHOT no momento de salvar —
        não referencia Produto.preco_venda/valor_unitario dinamicamente.
        Se o preço do produto mudar depois, o combo já criado mantém o
        valor congelado (mesma decisão documentada no comentário da
        origem: "não referencia Produto.preco_padrao dinamicamente")
RN-04 - Ao editar um Combo (PATCH/PUT com itens), o backend deleta todos
        os ItemCombo antigos e recria os novos a partir do payload —
        comportamento idempotente vindo da origem, mantido
RN-05 - Produto referenciado por ItemCombo não pode ser excluído
        fisicamente (on_delete=PROTECT) — soft delete de Produto
        (is_active=False) não impede a exclusão, só o delete físico
```

---

## Spec Backend

### `backend/produtos/models.py` — adicionar ao final do arquivo

```python
class Combo(BaseModel):
    nome = models.CharField('nome', max_length=200)
    descricao = models.TextField('descrição', blank=True, default='')
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='combos_criados',
    )

    class Meta:
        db_table = 'prd_combo'
        ordering = ['-created_at']
        verbose_name = 'Combo'
        verbose_name_plural = 'Combos'

    @property
    def valor_total(self):
        return sum((item.subtotal for item in self.itens.all()), Decimal('0.00'))

    def __str__(self):
        return self.nome


class ItemCombo(models.Model):
    # Sem BaseModel proposital: item filho de Combo, ciclo de vida
    # atrelado 1:1 ao pai (delete-and-recreate no update — RN-04);
    # não precisa de is_active/soft delete próprio, mesma decisão da
    # origem (SystemD ItemCombo também não herda soft delete próprio).
    combo = models.ForeignKey(Combo, on_delete=models.CASCADE, related_name='itens')
    produto = models.ForeignKey(Produto, on_delete=models.PROTECT, related_name='combo_itens')
    quantidade = models.DecimalField('quantidade', max_digits=12, decimal_places=3, default=1)
    valor_unitario = models.DecimalField(
        'valor unitário', max_digits=12, decimal_places=2, default=Decimal('0.00'),
        help_text='Snapshot no momento de salvar — não referencia Produto '
                   'dinamicamente (RN-03).',
    )

    class Meta:
        db_table = 'prd_item_combo'
        verbose_name = 'Item do Combo'
        verbose_name_plural = 'Itens do Combo'

    @property
    def subtotal(self):
        return self.quantidade * self.valor_unitario

    def __str__(self):
        return f'{self.combo.nome} — {self.produto.nome} x{self.quantidade}'
```

**Atenção Forge:** `models.py` atual do UidCore já importa `Decimal`
(linha 1) e `from django.conf import settings` (linha 3) — não duplicar
imports.

### `backend/produtos/serializers.py` — adicionar

```python
from .models import Combo, ItemCombo  # adicionar aos imports existentes


class ItemComboSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='pk', read_only=True)
    produto_nome = serializers.CharField(source='produto.nome', read_only=True)
    subtotal = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = ItemCombo
        fields = ['id', 'produto', 'produto_nome', 'quantidade', 'valor_unitario', 'subtotal']


class ComboSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='pk', read_only=True)
    itens = ItemComboSerializer(many=True)
    valor_total = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    criado_por_nome = serializers.CharField(source='criado_por.nome_completo', read_only=True, default='')

    class Meta:
        model = Combo
        fields = [
            'id', 'nome', 'descricao', 'itens', 'valor_total', 'is_active',
            'criado_por', 'criado_por_nome', 'created_at', 'updated_at',
        ]
        read_only_fields = ['is_active', 'criado_por', 'created_at', 'updated_at']

    def validate_itens(self, value):
        if not value:
            raise serializers.ValidationError('O combo precisa ter pelo menos 1 item.')  # RN-01
        for item in value:
            if item.get('quantidade', 0) <= 0:
                raise serializers.ValidationError('Quantidade de cada item deve ser maior que zero.')  # RN-02
        return value

    def create(self, validated_data):
        itens_data = validated_data.pop('itens')
        combo = Combo.objects.create(**validated_data)
        for item in itens_data:
            ItemCombo.objects.create(combo=combo, **item)
        return combo

    def update(self, instance, validated_data):
        itens_data = validated_data.pop('itens', None)
        instance.nome = validated_data.get('nome', instance.nome)
        instance.descricao = validated_data.get('descricao', instance.descricao)
        instance.save()
        if itens_data is not None:
            instance.itens.all().delete()
            for item in itens_data:
                ItemCombo.objects.create(combo=instance, **item)
        return instance
```

### `backend/produtos/views.py` — adicionar

```python
from .models import Combo, ItemCombo  # adicionar aos imports existentes (Prefetch já importado)
from .serializers import ComboSerializer  # adicionar


class ComboViewSet(ModelViewSet):
    serializer_class = ComboSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['nome']
    ordering_fields = ['nome', 'created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        return Combo.objects.filter(is_active=True).prefetch_related(
            Prefetch('itens', queryset=ItemCombo.objects.select_related('produto')),
        )

    def perform_create(self, serializer):
        serializer.save(criado_por=self.request.user)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = False
        instance.save(update_fields=['is_active', 'updated_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)
```

Sem `get_permissions` — segue o padrão de `ProdutoViewSet` (nenhum
override), herda `IsAuthenticated` global.

### `backend/produtos/urls.py` — alterar

```python
from rest_framework.routers import DefaultRouter

from .views import ComboViewSet, ProdutoViewSet

router = DefaultRouter()
router.register(r'combos', ComboViewSet, basename='combo')
router.register(r'', ProdutoViewSet, basename='produto')

urlpatterns = router.urls
```

**Atenção Forge — ordem de registro importa:** `ProdutoViewSet` está
registrado na raiz (`r''`). Se `combos` for registrado DEPOIS de `r''`
no `DefaultRouter`, o router pode tentar resolver `/produtos/combos/`
como se `combos` fosse um `pk` de produto, dependendo da ordem interna de
matching de URLs do DRF. Registrar `combos` **antes** da rota raiz evita
esse conflito — endpoint final esperado: `/api/v1/produtos/combos/`.
Confirmar com teste real (`GET /api/v1/produtos/combos/` → 200, não 404
nem tentativa de resolver como detail de produto) antes de considerar
concluído.

### Migration — `backend/produtos/migrations/0003_combo_itemcombo.py`

Gerar via `python manage.py makemigrations produtos` (Forge executa no
ambiente de dev, nunca na VPS — regra global). Estrutura esperada:
CreateModel `Combo` (herda campos de `BaseModel` via abstract — `id`,
`created_at`, `updated_at`, `is_active`, `nome`, `descricao`,
`criado_por` FK) + CreateModel `ItemCombo` (`id`, `combo` FK, `produto`
FK PROTECT, `quantidade`, `valor_unitario`). Dependência:
`0002_conversaounidade_converte_para_and_more`.

---

## Spec Frontend — `frontend/src/pages/Produtos.jsx`

Arquivo atual tem 805 linhas, já com seções Produto + Conversões +
Entradas de Estoque dentro do modal de Produto. A seção Combos é
**separada**, fora desse modal — nova seção na página principal, abaixo
da tabela/cards de Produtos (RF-06).

### Novo estado (topo do componente, junto dos existentes)

```jsx
const [combos, setCombos] = useState([])
const [loadingCombos, setLoadingCombos] = useState(false)
const [comboModalOpen, setComboModalOpen] = useState(false)
const [comboForm, setComboForm] = useState({ nome: '', descricao: '' })
const [comboItens, setComboItens] = useState([])
const [editingComboId, setEditingComboId] = useState(null)
const [savingCombo, setSavingCombo] = useState(false)
```

### Fetch de combos

```jsx
const fetchCombos = useCallback(async () => {
  setLoadingCombos(true)
  try {
    const response = await api.get('/produtos/combos/')
    setCombos(response.data.results)
  } catch {
    showToast('Erro ao carregar combos.', 'error')
  } finally {
    setLoadingCombos(false)
  }
}, [])

useEffect(() => { fetchCombos() }, [fetchCombos])
```

### Header — botão "🎁 Combo" ao lado de "+ Novo Produto" (RF-06)

```jsx
<div className="flex items-center gap-2">
  <Button onClick={openNew}>+ Novo Produto</Button>
  <Button variant="secondary" onClick={openNewCombo}>🎁 Combo</Button>
</div>
```

### Modal de Combo (RF-01, RF-03, RF-07)

- `openNewCombo()`: reseta `comboForm`/`comboItens`/`editingComboId=null`, abre `comboModalOpen`
- `openEditCombo(combo)`: popula `comboForm` (nome, descricao), `comboItens`
  a partir de `combo.itens` (mapear `{produto, quantidade, valor_unitario}`
  — usar os já existentes na resposta, sem novo GET), `editingComboId=combo.id`
- Lista de itens dentro do modal: cada linha com `Select` de produto
  (reaproveitar a lista de produtos carregada — buscar via
  `api.get('/produtos/', { params: { page_size: 200 } })` uma vez ao
  abrir o modal, MVP; se o catálogo crescer além disso, Loom decide se
  troca por busca incremental como já existe em outros pontos do
  projeto), `Input` de quantidade (step 0.001), `Input` de valor unitário
  (step 0.01, pré-preenchido com `produto.preco_venda` ao selecionar —
  RF-07, ajustável pelo usuário depois pois é snapshot RN-03)
- Botão "+ Adicionar Item" (mesmo ícone/estilo de `addConversao`)
- Botão remover linha (Trash2, mesmo estilo de `removeConversao` — mas
  sem chamada de API própria: itens de combo só são persistidos no
  submit do combo inteiro, não têm endpoint próprio de item)
- Valor total exibido em tempo real:
  `comboItens.reduce((acc, i) => acc + (Number(i.quantidade||0) * Number(i.valor_unitario||0)), 0)`,
  formatado com `BRL()` (já existe no arquivo)

### Submit do Combo (RF-01, RF-03)

```jsx
const handleSubmitCombo = async (e) => {
  e.preventDefault()
  const itensValidos = comboItens.filter((i) => i.produto && i.quantidade)
  if (itensValidos.length === 0) {
    showToast('O combo precisa ter pelo menos 1 item.', 'error')  // espelha RN-01
    return
  }
  if (itensValidos.some((i) => Number(i.quantidade) <= 0)) {
    showToast('Quantidade de cada item deve ser maior que zero.', 'error')  // espelha RN-02
    return
  }
  setSavingCombo(true)
  try {
    const payload = {
      ...comboForm,
      itens: itensValidos.map((i) => ({
        produto: i.produto, quantidade: i.quantidade, valor_unitario: i.valor_unitario || 0,
      })),
    }
    if (editingComboId) {
      await api.patch(`/produtos/combos/${editingComboId}/`, payload)
      showToast('Combo atualizado com sucesso.')
    } else {
      await api.post('/produtos/combos/', payload)
      showToast('Combo cadastrado com sucesso.')
    }
    setComboModalOpen(false)
    fetchCombos()
  } catch (error) {
    showToast(extractErrorMessage(error, 'Erro ao salvar combo.'), 'error')
  } finally {
    setSavingCombo(false)
  }
}
```

Validação client-side espelha RN-01/RN-02 antes de submeter — o servidor
continua sendo a fonte da verdade (mesma dupla camada já usada nas
Conversões de Unidade da própria página).

### Exclusão de Combo (RF-04)

```jsx
const handleDeleteCombo = async (combo) => {
  if (!window.confirm(`Excluir o combo "${combo.nome}"?`)) return
  try {
    await api.delete(`/produtos/combos/${combo.id}/`)
    showToast('Combo removido.')
    fetchCombos()
  } catch (error) {
    showToast(extractErrorMessage(error, 'Erro ao remover combo.'), 'error')
  }
}
```

### Seção Combos na página (RF-06, RF-08) — abaixo da `<Pagination>` de Produtos

- Título "Combos" + contador
- Desktop: tabela (colunas: Nome, Qtd. Itens, Valor Total, Ações) com
  `overflow-x-auto -mx-6 -my-4` e classes dark mode idênticas à tabela de
  Produtos (`bg-gray-50 dark:bg-navy-900`, `divide-gray-100
  dark:divide-navy-700`, hover `dark:hover:bg-navy-700/60`)
- Mobile (`md:hidden`): cards no mesmo padrão dos cards de Produto
  (`Card` component, badge de qtd. de itens, botões Editar/Excluir)
- Estado vazio: mesmo padrão visual do estado vazio de Produtos (emoji +
  texto cinza — sugestão de emoji: 🎁)

### Padrões de dark mode a reaproveitar (RNF-01)

Todas as classes `dark:*` já usadas em `Produtos.jsx` — não introduzir
nova paleta. Nenhum `style={{...}}` inline (regra global Uid — nunca
inline styles, sempre Tailwind).

---

## Atores e Perfis

```
Qualquer usuário autenticado do UidCore (IsAuthenticated global) pode
criar, editar, excluir (soft) e listar Combos — mesmo nível de acesso já
aplicado a Produtos, Conversões e Entradas de Estoque. Não há
diferenciação Admin/Operacional no UidCore hoje (diferente do SystemD,
que tinha IsAdminOrOperacional) — fora do escopo desta manutenção propor
granularidade de permissão nova.
```

---

## Fora do Escopo (Won't — MoSCoW)

```
- Endpoint dedicado de item de combo (POST/PATCH/DELETE individual em
  ItemCombo) — segue o padrão delete-and-recreate da origem, sem CRUD
  granular por item
- Cálculo de estoque/baixa automática ao vender um combo (módulo Vendas/
  PDV não foi mencionado no pedido — combo aqui é só cadastro/catálogo)
- Desconto percentual automático no valor_total do combo (SystemD
  também não tem — valor_total é soma simples dos subtotais)
- Permissão diferenciada por perfil (Admin vs Operacional) — UidCore não
  tem essa distinção hoje, fora de escopo criar
```

## Riscos e Dependências

```
- RISCO: ordem de registro de rotas no DefaultRouter (`combos` vs raiz
  `r''` de ProdutoViewSet) — documentado acima, Forge deve testar
  GET /api/v1/produtos/combos/ manualmente antes de considerar pronto
- RISCO: catálogo de produtos grande (>200) pode não caber no page_size
  usado para popular o Select de produto dentro do modal de Combo —
  Loom decide se implementa busca incremental (debounce, como já existe
  em outros pontos do projeto) ou aumenta o page_size; fora do escopo
  bloquear a entrega por isso, mas documentar a limitação se o page_size
  fixo for a escolha do MVP
- DEPENDÊNCIA: nenhuma migration pendente hoje no app produtos além da
  0002 já aplicada em produção (confirmado por histórico das
  Manutenções #37/#40) — 0003 desta manutenção não conflita
```

---

## Critérios de Aceite (para o Sentinel)

```
CA-01 - POST /api/v1/produtos/combos/ com nome + itens válidos → 201,
        valor_total calculado corretamente
CA-02 - POST sem itens (lista vazia) → 400 com mensagem RN-01
CA-03 - POST com item de quantidade <= 0 → 400 com mensagem RN-02
CA-04 - PATCH em combo existente trocando os itens → itens antigos
        deletados, novos criados, valor_total recalculado (RN-04)
CA-05 - DELETE em combo → 204, is_active=False no banco, some da
        listagem padrão (GET sem filtro)
CA-06 - GET /api/v1/produtos/combos/ retorna response.data.results
        (paginação padrão), itens aninhados com produto_nome e subtotal
CA-07 - criado_por preenchido automaticamente com o usuário autenticado
        no POST; criado_por_nome retorna nome_completo do usuário
CA-08 - Produto usado em algum ItemCombo não pode ser excluído
        fisicamente (comportamento de PROTECT — não é exposto via API
        hoje, mas não deve gerar erro 500 caso alguma rotina tente)
CA-09 - Frontend: seção Combos visível abaixo da tabela de Produtos,
        botão "🎁 Combo" abre modal, criar/editar/excluir funcionando
        ponta a ponta contra a API real, dark mode consistente
CA-10 - npm run build limpo (0 erros) após as mudanças em Produtos.jsx
CA-11 - Testes Django cobrindo RN-01 a RN-05 e CA-01 a CA-08 (mínimo)
```

---

## Passagem de bastão

```
✅ Solicitação classificada — UidCore (OS #7)
   tipo: feature_pequena
   descricao_tecnica: portar sistema de Combos de produtos do SystemD,
     adaptado a BaseModel/serializer padrão/permissão global do UidCore
   caminho_afetado: backend/produtos/ (models, serializers, views, urls,
     migration 0003) + frontend/src/pages/Produtos.jsx
   requer_aprovacao_comercial: false
➡️  Planner: rotear para Forge (backend) + Loom (frontend) em paralelo,
    Sentinel valida com os 11 critérios de aceite acima antes do Pilot.
```
