# Especificação — Manutenção #32 (revisão 2)
**Elaborado por:** Analista (MODO HOTFIX — reanálise após rascunho anterior)
**Data:** 2026-08-15
**Sistema:** UidCore (OS #7)
**Solicitação original:** "Em novo orcamento e novo pedido vincular campo produtos aos produtos do banco de dados igual em pdv."

**Contexto adicional do Planner (repassado nesta rodada):**
> Backend: ItemOrcamento e ItemPedido já têm ForeignKey para produtos.Produto.
> Serializers: produto (writable) e produto_nome (read-only) já presentes.
> Frontend Vendas.jsx: ProdutoAutocomplete e SecaoItens já existem, buscam /api/v1/produtos/.
> Manutenção 12 corrigiu race conditions mas usuário reporta que **ainda não funciona
> igual ao PDV**.

---

## ⚠️ Estado encontrado no repositório antes de qualquer trabalho novo

`git status` mostra **alterações não commitadas** em `frontend/src/pages/Vendas.jsx` e
neste mesmo `Especificacao_Hotfix.md` — ou seja, já existia um primeiro ciclo desta
mesma Manutenção #32 que chegou a ser parcialmente executado (Analista + Loom) mas
nunca foi commitado, nunca passou por Sentinel, nunca foi deployado.

O que já está implementado no working tree (não commitado):
- `ProdutoAutocomplete` (usado dentro de cada linha de item) ganhou `position: fixed`
  com coordenadas calculadas via `getBoundingClientRect()` (comentários `// Fix M32`
  no código) — corrige o dropdown sendo cortado pelo `overflow-y-auto` do `Modal`,
  mesmo padrão de bug já visto em PDV nas Manutenções #23 e #24.

**Forge/Loom: revisar `git diff -- frontend/src/pages/Vendas.jsx` antes de começar.**
Esse fix de posicionamento é válido e deve ser **mantido e commitado** junto com o
trabalho desta revisão — não descartar, não refazer do zero.

Esse fix sozinho, porém, **não resolve a reclamação do usuário**. Ele corrige um bug de
CSS, mas o usuário está comparando o *fluxo de uso*, não o CSS. A causa raiz real está
descrita abaixo.

---

## Diagnóstico — por que "ainda não funciona igual ao PDV"

### Backend: confirmado correto, sem alteração necessária
- `ProdutoViewSet.search_fields = ['nome', 'codigo_barras']` — mesmo endpoint usado
  pelo PDV (`GET /api/v1/produtos/?search=<termo>`).
- `ItemOrcamento.produto` / `ItemPedido.produto` são FK `null=True, blank=True` para
  `produtos.Produto`.
- `ItemOrcamentoSerializer` / `ItemPedidoSerializer` expõem `produto` (writable, é o
  FK id) e `produto_nome` (read-only, `source='produto.nome'`).
- `ProdutoSerializer` já retorna `quantidade_estoque`, `codigo_barras`, `preco_venda` —
  os mesmos campos que o PDV consome.

**Conclusão: o vínculo com o banco de dados já funciona tecnicamente.** Um produto
selecionado no autocomplete de Vendas.jsx é salvo com o `produto_id` correto — os
testes de API (CA-03/CA-04 abaixo) confirmam isso. O problema não é "não vincula ao
banco", é "a experiência de buscar/selecionar não é igual ao PDV".

### Comparação estrutural real: Vendas.jsx vs PDV (FrenteDeCaixa.jsx)

| Aspecto | PDV — `FrenteDeCaixa.jsx` | Vendas.jsx (atual) |
|---|---|---|
| Ponto de entrada da busca | Campo único, fixo, sempre visível no topo da tela | É preciso clicar **"+ Adicionar Item" primeiro** para abrir uma linha vazia — só então aparece um campo de busca, um por linha |
| Resultado da busca | Nome + preço + **estoque** (`quantidade_estoque`), badge "Sem estoque" | Nome + preço apenas — sem indicador de estoque |
| Ação ao selecionar | Clique adiciona **direto ao carrinho** (a linha nasce junto com a seleção) | Clique só **preenche os campos de uma linha que já precisava existir antes** |
| Atalho de teclado | Enter com match exato de `codigo_barras` adiciona sem clique (RF-17) | Não existe — só funciona com clique do mouse |
| Tamanho mínimo de busca | Qualquer texto não vazio dispara a busca | Exige 2+ caracteres |

**Causa raiz real:** não é (só) o dropdown cortado — é o **modelo de interação**.
No PDV: *buscar → clicar → já está na lista*. Em Vendas: *criar linha vazia → buscar
dentro dela → clicar*. Um usuário que conhece o PDV e vai usar Orçamento/Pedido sente
que o produto "não vincula direto", porque a busca não é o primeiro passo do fluxo —
é um passo escondido dentro de uma linha que ele precisa saber criar antes.

---

## Escopo da correção

**Tipo de manutenção:** `melhoria_ux` (a funcionalidade existe e tecnicamente
funciona — o problema é o padrão de interação divergente do PDV, já reportado mais de
uma vez pelo mesmo cliente)

**Complexidade:** `media` — um arquivo frontend, sem mudança de contrato de API, mas
com reestruturação de componente (novo ponto de entrada de busca dentro de
`SecaoItens`)

**Aprovação comercial:** não requer

---

## Requisitos Funcionais

### RF-01 (Must) — Commitar e validar o fix de posicionamento já rascunhado
Manter o `position: fixed` + `getBoundingClientRect()` já presente no working tree do
`ProdutoAutocomplete`. Não é trabalho novo — é validar que o rascunho não commitado
está correto e incluí-lo nesta entrega.

**CA-01:** Modal "Novo Orçamento" → dentro de uma linha de item → digitar no campo
Produto → dropdown aparece **completo e clicável**, sem corte pelo Modal.
**CA-02:** Mesmo comportamento em "Novo Pedido".

### RF-02 (Must) — Campo "Buscar produto" no topo da seção Itens
Adicionar, dentro de `SecaoItens`, um campo de busca único acima da lista de itens —
mesmo padrão visual/comportamental do campo de busca do PDV: ícone de lupa, debounce
300ms, **sem mínimo de caracteres** (dispara com qualquer texto não vazio, igual ao
PDV — hoje o `ProdutoAutocomplete` de linha exige 2+ caracteres, mantém assim só para
o autocomplete de linha existente, mas o campo novo segue o padrão do PDV), dropdown
com nome + preço + **estoque** (`quantidade_estoque`), badge "Sem estoque" quando
`quantidade_estoque <= 0` (mesmo texto e classes usadas em `FrenteDeCaixa.jsx`).

**CA-03:** Buscar um produto existente no campo novo retorna resultados com nome,
preço e indicador de estoque.

### RF-03 (Must) — Selecionar no campo novo cria a linha automaticamente
Ao clicar em um resultado do campo de busca do RF-02, uma nova linha de item deve ser
adicionada **automaticamente** a `itens`, já preenchida:
```js
{
  produto: produto.id,
  produto_nome: produto.nome,
  descricao: produto.nome,
  quantidade: 1,
  valor_unitario: String(produto.preco_venda || 0),
  valor_total: (1 * (produto.preco_venda || 0)).toFixed(2),
}
```
Sem precisar clicar em "+ Adicionar Item" antes. Esse é o comportamento que espelha o
PDV: buscar → clicar → item já está na lista.

**CA-04:** Clicar num resultado do campo de busca novo cria uma linha de item
preenchida (produto, nome, quantidade 1, valor unitário do produto, total calculado)
sem nenhuma ação manual adicional.
**CA-05:** Ao salvar o orçamento/pedido, o item criado assim é persistido via API com
`produto` (FK) e `produto_nome` corretos (`GET /api/v1/vendas/orcamentos/{id}/itens/`
e `GET /api/v1/vendas/pedidos/{id}/itens/`).

### RF-04 (Should) — Manter "+ Adicionar Item" para linha manual/avulsa
Não remover o botão "+ Adicionar Item" — ele continua sendo o caminho para criar uma
linha **sem produto vinculado** (item de descrição livre, ex: "Frete", "Serviço
avulso"). O campo de busca do RF-02 é um atalho, não uma substituição.

**CA-06:** Clicar em "+ Adicionar Item" continua criando uma linha vazia editável
manualmente, como hoje.

### RF-05 (Should) — Manter o autocomplete por linha para troca de produto
O `ProdutoAutocomplete` já existente (corrigido pelo RF-01) continua disponível
**dentro de cada linha**, permitindo trocar o produto vinculado de uma linha já
criada — inclusive linhas criadas manualmente pelo RF-04 ou já persistidas (edição de
orçamento/pedido existente).

**CA-07:** Numa linha já criada, buscar e selecionar outro produto pelo autocomplete
da própria linha continua funcionando (fluxo atual preservado).
**CA-08:** Editar um orçamento/pedido já existente (itens com `id`, vindos da API)
continua funcionando sem regressão — nem o RF-02/03 nem o RF-01 alteram esse fluxo.

### RF-06 (Could) — Atalho de teclado (paridade com RF-17 do PDV)
Enter no campo de busca do RF-02, com match exato de `codigo_barras`, adiciona o item
direto — mesmo padrão do RF-17 do PDV (`FrenteDeCaixa.jsx`, `handleBuscaKeyDown`).
Nice-to-have — não bloqueia a entrega desta manutenção se não houver tempo.

---

## Requisitos Não Funcionais

- **RNF-01** — Sem alteração de backend, sem migration, sem endpoint novo. Endpoint
  `/api/v1/produtos/` já é o mesmo consumido pelo PDV — nenhuma mudança de contrato.
- **RNF-02** — Sem regressão nos 182 testes Django (backend intocado).
- **RNF-03** — `npm run build` limpo, 0 erros.
- **RNF-04** — Dark mode preservado — reutilizar os tokens `navy-*`/`violet-*` já
  usados no restante de `Vendas.jsx` e em `FrenteDeCaixa.jsx` (não criar cores novas).
- **RNF-05** — Fluxo de edição de orçamento/pedido já existente (itens já persistidos
  com `id`, carregados via `GET .../itens/`) deve continuar funcionando sem regressão.

---

## Spec técnica frontend — detalhada

**Arquivo único:** `frontend/src/pages/Vendas.jsx`

1. **Manter** o `ProdutoAutocomplete` como está no working tree atual (já com
   `position: fixed`, `calcularPosicao`, `inputRef`, listeners de `scroll`/`resize`) —
   isso resolve RF-01. Não reescrever esse componente além de revisão/validação.

2. **Novo componente** dentro de `SecaoItens`, acima de `{itens.map(...)}` — pode se
   chamar `BuscaProdutoRapida` — inspirado diretamente no bloco de busca de
   `FrenteDeCaixa.jsx` (linhas ~384–454 do arquivo lido nesta análise):
   - `useState` para `busca`, `resultados`, `buscando`
   - `useEffect` com debounce 300ms chamando
     `GET /api/v1/produtos/?search=<termo>&page_size=10` (mesmo endpoint, campos já
     vêm prontos do `ProdutoSerializer` — nenhuma mudança de backend necessária)
   - Dropdown com `nome`, `BRL(preco_venda)`, e bloco de estoque:
     `parseFloat(p.quantidade_estoque || 0) <= 0` → badge vermelho "Sem estoque"
     (mesmas classes Tailwind usadas no PDV); caso contrário mostrar
     `{p.quantidade_estoque} {p.unidade_base}` em cinza — texto apenas informativo,
     **não bloqueia adicionar** (diferente do PDV: orçamento/pedido não debita
     estoque, é só um documento comercial — ver "Fora do escopo").

3. **Callback de seleção:** `onAdicionar(produto)` chamado pelo componente novo deve
   invocar uma função nova em `SecaoItens`, ex. `adicionarItemComProduto(produto)`,
   que faz `setItens(prev => [...prev, { ... })` conforme o objeto especificado no
   RF-03.

4. **Posicionamento do componente novo:** logo abaixo do cabeçalho "Itens" / botão
   "+ Adicionar Item" (que continua existindo, RF-04), acima da lista de linhas já
   adicionadas — mesmo lugar visual que o campo de busca ocupa no topo do PDV.

5. **Reaproveitar** `BRL()` já definido no topo do arquivo — não duplicar.

---

## Fora do escopo (explicitamente)

- Débito/reserva de estoque a partir de Orçamento ou Pedido — isso só acontece no PDV
  (`adicionarProduto` do PDV cria a venda e o item já debitam via backend do módulo
  `pdv`). Orçamento e Pedido são documentos comerciais, não movimentam estoque — o
  indicador "Sem estoque" no RF-02 é só informativo.
- Leitor de câmera / scanner físico em Orçamento/Pedido — fora do escopo. O RF-06
  (Could) cobre apenas o atalho de teclado por match exato, não a câmera.
- Qualquer alteração em `frontend/src/pages/pdv/**` — o PDV está funcionando, é usado
  aqui só como referência de padrão a seguir.
- Persistência incremental por item (POST imediato a cada item, como o PDV faz) —
  fora de escopo nesta rodada. Orçamento/Pedido novos ainda não têm `id` até o
  formulário ser submetido, então os itens continuam sendo acumulados em estado local
  e enviados em lote no `handleSubmit` (comportamento atual mantido, RNF-05).

---

## Riscos e dependências

- **Trabalho não commitado já existe no working tree** (`Vendas.jsx` e este próprio
  `Especificacao_Hotfix.md`) — Forge/Loom deve rodar `git diff -- frontend/src/pages/Vendas.jsx`
  antes de começar, para não perder o fix de posicionamento (RF-01) já rascunhado nem
  duplicar esforço.
- Existe um arquivo **untracked** `backend/test_whitelist_pdv.py` solto no repositório
  (resíduo já documentado da Manutenção #22, no histórico do `CLAUDE.md` do projeto) —
  não faz parte deste escopo, não tocar.
- Esta é a **segunda vez** que este mesmo pedido chega à esteira (o rascunho anterior
  só cobria RF-01) — recomenda-se ao Sentinel validar explicitamente o fluxo completo
  ponta a ponta (criar orçamento novo, buscar produto pelo campo novo, confirmar item
  criado automaticamente, salvar, conferir via API) antes de aprovar, para evitar uma
  terceira rodada pela mesma reclamação.

---

## Critérios de aceite — checklist Sentinel

- [ ] CA-01: dropdown do `ProdutoAutocomplete` (dentro da linha) aparece completo, sem
      corte, em Orçamento
- [ ] CA-02: idem em Pedido
- [ ] CA-03: campo de busca novo (RF-02) retorna nome, preço e estoque
- [ ] CA-04: clicar num resultado do campo novo cria linha de item já preenchida, sem
      precisar de "+ Adicionar Item" antes
- [ ] CA-05: item criado assim é persistido com `produto` (FK) e `produto_nome`
      corretos via API, tanto em Orçamento quanto em Pedido
- [ ] CA-06: "+ Adicionar Item" continua criando linha manual sem produto
- [ ] CA-07: autocomplete de linha (RF-05) continua permitindo trocar produto de uma
      linha já criada
- [ ] CA-08: edição de orçamento/pedido existente sem regressão
- [ ] RNF-01: 182 testes Django passando (backend intocado)
- [ ] RNF-02: `npm run build` limpo
- [ ] RNF-03: dark mode preservado (tokens navy/violet)
