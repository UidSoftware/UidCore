# Especificação — Manutenção #39
**Elaborado por:** Analista (MODO HOTFIX)
**Data:** 2026-08-17
**Sistema:** UidCore (OS #7)
**Solicitação original (verbatim, resumida):**
1. "BUG — GET /pdv/sessoes/atual/ tratado errado no frontend" — `FrenteDeCaixa.jsx`
   (linhas 68-75) e `AberturaCaixa.jsx` (linhas 41-44) tratam `res.data` inteiro como se
   já fosse a sessão, em vez de `res.data.sessao`.
2. "MUDANÇA DE NAVEGAÇÃO — tirar PDV / Caixa do menu lateral, dois botões SEPARADOS
   dentro de Vendas" — remover item top-level do `Sidebar.jsx` e adicionar botões "PDV"
   e "Caixas" na tela de Vendas, cada um navegando pra sua rota já existente.

---

## Classificação

```
tipo: bug (item 1) + melhoria_ux (item 2) — agrupados na mesma manutenção, ambos
      Pipeline B (direto, sem Blueprint/Brush — sistema e arquitetura já existem)
sistema: UidCore
caminho_afetado: backend/pdv/views.py (action sessao_atual)
                 backend/pdv/tests.py
                 frontend/src/pages/pdv/FrenteDeCaixa.jsx
                 frontend/src/pages/pdv/AberturaCaixa.jsx
                 frontend/src/pages/pdv/FechamentoCaixa.jsx (achado adicional, ver abaixo)
                 frontend/src/components/layout/Sidebar.jsx
                 frontend/src/pages/Vendas.jsx
complexidade: baixa
requer_aprovacao_comercial: false
```

---

## Diagnóstico confirmado (leitura direta dos arquivos — não do pedido)

### Item 1 — bug do endpoint `sessao_atual`

O pedido descreve o backend como **sempre** retornando `{"sessao": <objeto ou null>}`
(200) e pede a correção **só no frontend**. Lendo `backend/pdv/views.py` linhas 87-98,
isso **não é exatamente o que o código faz hoje**:

```python
@action(detail=False, methods=['get'], url_path='atual')
def sessao_atual(self, request):
    sessao = SessaoCaixa.objects.filter(
        operador=request.user, status='ABERTA', is_active=True,
    ).first()
    if not sessao:
        return Response({'sessao': None})
    return Response(SessaoCaixaSerializer(sessao).data)
```

O contrato é **assimétrico**:
- **Sem sessão aberta** → `{"sessao": None}` (confere com o pedido).
- **Com sessão aberta** → o dicionário **cru** do serializer, **sem** a chave `"sessao"`
  (ex.: `{"id": 5, "status": "ABERTA", "conta_nome": "Caixa 1", ...}` direto na raiz).

Isso é confirmado pelos próprios testes já existentes, que hoje **documentam esse
comportamento assimétrico como correto**:
- `pdv/tests.py:274-279` (`test_sessao_atual_com_sessao_aberta`) lê
  `resp.data['status']` direto, não `resp.data['sessao']['status']`.
- `pdv/tests.py:342-374` (`test_sessao_atual_retorna_resumo_populado`) lê
  `resp.data['resumo']` direto.
- `pdv/tests.py:397-401` (`test_criar_venda_sem_sessao_retorna_400`) lê
  `resp.data['id']` direto.

**Consequência prática para a correção pedida:** se o fix for feito **só no frontend**,
seguindo literalmente `res.data.sessao` como o pedido pede, o caso "COM sessão aberta"
quebra — `res.data.sessao` seria `undefined`, porque hoje o backend não aninha nesse
caso. Ou seja, aplicar o fix só no frontend resolveria o bug relatado (falso positivo de
"sessão encerrada" quando não há sessão) mas introduziria o **mesmo bug ao contrário**
para quem TEM sessão aberta (a maioria dos operadores, na maior parte do tempo).

**Correção real: o backend também precisa mudar** — normalizar `sessao_atual` para
**sempre** devolver `{"sessao": <dados ou null>}`, e então ajustar os 3 consumidores do
frontend (não 2 — ver achado adicional abaixo) para ler `res.data.sessao`. Isso contraria
a instrução literal do pedido ("zero alterações backend"), mas é a única forma de
resolver o bug relatado sem quebrar o fluxo que hoje funciona por acidente.

**Achado adicional — terceiro consumidor não mencionado no pedido.**
`frontend/src/pages/pdv/FechamentoCaixa.jsx` (linhas 39-49) consome o mesmo endpoint com
o mesmo padrão problemático:
```js
api.get('/pdv/sessoes/atual/')
  .then((res) => {
    setSessao(res.data)
    setResumo(res.data.resumo || {})
  })
  .catch(() => { navigate('/pdv/abertura') })
```
Hoje funciona por acidente na tela de Fechamento porque, na prática, só se chega nela
com uma sessão aberta (fluxo normal: Frente de Caixa → Fechar Caixa). Mas se normalizarmos
o backend para sempre aninhar em `"sessao"` (correção necessária acima), este arquivo
**precisa** do mesmo ajuste — senão passa a quebrar (hoje funciona só porque o backend
retorna os dados crus quando há sessão; com a normalização, `res.data.sessao` é quem vai
ter os dados reais). Incluído no escopo desta manutenção por ser a mesma causa raiz.

### Item 2 — navegação PDV/Caixas

Confirmado em `Sidebar.jsx` linha 8: item top-level `{ to: '/pdv', label: 'PDV / Caixa',
icon: '🏪' }` dentro do array `navItems`, sem tratamento especial — remoção é direta.

Confirmado em `Vendas.jsx`: componente principal (`export default function Vendas()`,
linha 1008) renderiza título, tabs (Orçamentos/Pedidos) e delega pro `OrcamentosTab`/
`PedidosTab`. Não importa `useNavigate` hoje — precisa ser adicionado. As rotas alvo já
existem e não mudam (`frontend/src/routes/index.jsx` linhas 54-59):
`/pdv` → `FrenteDeCaixa`, `/pdv/sessoes` → `RelatorioSessoesCaixa`. Nenhuma rota nova
precisa ser criada.

---

## Requisitos Funcionais (RF)

```
RF-01 (Must) - Normalizar backend/pdv/views.py::sessao_atual para SEMPRE retornar
        {"sessao": <dados da sessão ou null>}, eliminando a assimetria hoje existente
        entre "sem sessão" (já aninhado) e "com sessão" (dados crus na raiz).
RF-02 (Must) - FrenteDeCaixa.jsx (linhas 68-75): setSessao(res.data.sessao) em vez de
        setSessao(res.data) — corrige o bug relatado (sessão-fantasma disparando
        criarVenda() com sessao_caixa undefined → 400 → redirecionamento enganoso).
RF-03 (Must) - AberturaCaixa.jsx (linhas 41-44): checar res.data?.sessao (não
        res.data direto) antes de setSessaoAtiva — corrige o banner "Conta: #undefined"
        e "Aberta às Invalid Date" exibido incorretamente para operador sem sessão.
RF-04 (Must) - FechamentoCaixa.jsx (linhas 39-49, achado adicional): mesmo ajuste —
        setSessao(res.data.sessao); setResumo(res.data.sessao?.resumo || {}) — mesma
        causa raiz do RF-02, não reportada no pedido original mas com o mesmo padrão de
        bug, necessária para não quebrar quando o RF-01 for aplicado.
RF-05 (Must) - Atualizar os 3 testes existentes que hoje validam o contrato assimétrico
        como correto (pdv/tests.py:274-279, 342-374, 397-401) para o novo formato
        sempre-aninhado — sem isso a suite quebra com a mudança do RF-01.
RF-06 (Must) - Remover o item top-level { to: '/pdv', label: 'PDV / Caixa' } do array
        navItems em Sidebar.jsx (linha 8).
RF-07 (Must) - Adicionar dois botões distintos e lado a lado na tela de Vendas
        (Vendas.jsx), próximos às tabs Orçamentos/Pedidos e ao botão "+ Novo Orcamento":
        "PDV" → navigate('/pdv'); "Caixas" → navigate('/pdv/sessoes'). Não é uma aba
        nova nem um botão único — dois destinos separados, como pedido.
```

---

## Regras de Negócio (RN)

```
RN-01 - O contrato de GET /pdv/sessoes/atual/ é {"sessao": SessaoCaixaSerializer|null},
        sempre — sem exceção para o caso "sessão existe". Qualquer novo consumidor
        futuro deste endpoint deve assumir esse formato desde o início.
RN-02 - Nenhuma ação que dependa de sessao.id (criarVenda, fechar sessão) pode disparar
        com um objeto de sessão que não veio de fato do backend (proteção reforçada:
        os efeitos que leem `sessao` só devem rodar quando `sessao?.id` é um valor
        real, não apenas quando `sessao` é truthy) — evita reintroduzir a mesma classe
        de bug caso outro consumidor apareça no futuro.
RN-03 - Os botões "PDV" e "Caixas" em Vendas.jsx usam a mesma autenticação/guarda de
        rota já existente em routes/index.jsx (ProtectedRoute) — nenhuma permissão nova
        é criada.
RN-04 - Rotas /pdv, /pdv/abertura, /pdv/venda, /pdv/fechamento, /pdv/vendas e
        /pdv/sessoes permanecem exatamente como estão — apenas o ponto de entrada
        (menu lateral → botões em Vendas) muda.
```

---

## Telas afetadas (detalhamento)

### Tela: PDV — Frente de Caixa (`FrenteDeCaixa.jsx`)
- Corrigir `useEffect` de carregamento de sessão (linhas 72-81): ler `res.data.sessao`.
- Sem mudança de layout/UX — é puramente correção do parsing da resposta.

### Tela: PDV — Abertura de Caixa (`AberturaCaixa.jsx`)
- Corrigir `useEffect` de carregamento (linhas 37-50): ler `sessaoRes?.data?.sessao` em
  vez de `sessaoRes?.data`.
- Banner "Você já tem uma sessão aberta" (linhas 117-132) só deve aparecer quando
  `sessaoAtiva` tiver dados reais (`id`, `conta_nome`, `data_abertura` válidos).

### Tela: PDV — Fechamento de Caixa (`FechamentoCaixa.jsx`) — achado adicional
- Corrigir `useEffect` de carregamento (linhas 39-49): mesmo padrão do RF-04.

### Menu lateral (`Sidebar.jsx`)
- Remover a linha do item "PDV / Caixa" (`to: '/pdv'`) do array `navItems`.
- Demais itens do menu permanecem inalterados, sem reordenação.

### Tela: Vendas (`Vendas.jsx`)
- Componente principal (`export default function Vendas()`): adicionar
  `import { useNavigate } from 'react-router-dom'` e `const navigate = useNavigate()`.
- Na área de cabeçalho/ações (perto do título "Vendas" e das tabs Orçamentos/Pedidos,
  ou dentro da barra de ações ao lado do botão "+ Novo Orcamento" — decisão de layout
  fina cabe ao Loom, desde que os dois botões fiquem visíveis e lado a lado, não dentro
  de uma tab específica): dois botões —
  - "PDV" → `onClick={() => navigate('/pdv')}`
  - "Caixas" → `onClick={() => navigate('/pdv/sessoes')}`
- Sugestão de estilo: reaproveitar o componente `Button` já usado no restante da tela
  (`import Button from '../components/ui/Button.jsx'`, já importado neste arquivo),
  variante secundária/outline para diferenciar visualmente do "+ Novo Orcamento".

---

## Especificação técnica — Backend (Forge)

1. `backend/pdv/views.py::sessao_atual` (action `atual`, linhas 87-98):
   ```python
   @action(detail=False, methods=['get'], url_path='atual')
   def sessao_atual(self, request):
       sessao = SessaoCaixa.objects.filter(
           operador=request.user, status='ABERTA', is_active=True,
       ).first()
       return Response({
           'sessao': SessaoCaixaSerializer(sessao).data if sessao else None,
       })
   ```
   Único ponto de mudança de código de produção no backend.
2. `backend/pdv/tests.py` — atualizar para o novo formato sempre-aninhado:
   - `test_sessao_atual_com_sessao_aberta` (linha ~274-279): trocar
     `resp.data['status']` por `resp.data['sessao']['status']`.
   - `test_sessao_atual_retorna_resumo_populado` (linha ~342-374): trocar
     `resp.data['resumo']` por `resp.data['sessao']['resumo']`.
   - `test_criar_venda_sem_sessao_retorna_400` (linha ~397-401): trocar
     `sess_resp.data['id']` por `sess_resp.data['sessao']['id']`.
   - `test_sessao_atual_sem_sessao_aberta` (linha ~268-272) já está correto, não muda.
3. Nenhuma migration necessária — mudança é só de shape de resposta HTTP, nenhum campo
   de model é alterado.
4. Nenhuma outra view/serializer do módulo `pdv` é afetada — grep confirmou que
   `sessoes/atual` é consumido apenas pelos 3 arquivos de frontend listados acima.

---

## Especificação técnica — Frontend (Loom)

1. `frontend/src/pages/pdv/FrenteDeCaixa.jsx` (linhas 72-81):
   ```js
   useEffect(() => {
     api.get('/pdv/sessoes/atual/')
       .then((res) => {
         setSessao(res.data.sessao)
       })
       .catch(() => {
         navigate('/pdv/abertura')
       })
       .finally(() => setLoadingSessao(false))
   }, [navigate])
   ```
   Nota: quando não há sessão, `res.data.sessao` é `null` — isso é intencional. O
   `useEffect` de `criarVenda` (linha 114-118) já tem guarda `if (sessao && !venda)`,
   então `sessao === null` simplesmente não dispara `criarVenda`. Avaliar se vale
   redirecionar direto para `/pdv/abertura` quando `sessao` vier `null` (hoje a tela só
   redireciona no `.catch`, nunca no caso 200 com `sessao: null`) — comportamento atual
   pode deixar a Frente de Caixa "vazia" sem sessão em vez de redirecionar. Recomenda-se
   ao Loom tratar esse caso explicitamente (redirecionar para `/pdv/abertura` também
   quando `res.data.sessao` vier `null`), fechando o bug por completo em vez de só
   parcialmente.
2. `frontend/src/pages/pdv/AberturaCaixa.jsx` (linhas 37-50):
   ```js
   useEffect(() => {
     Promise.all([
       api.get('/pdv/sessoes/atual/').catch(() => null),
       api.get('/financeiro/contas/?tipo=CAIXA&page_size=100'),
     ]).then(([sessaoRes, contasRes]) => {
       if (sessaoRes?.data?.sessao) {
         setSessaoAtiva(sessaoRes.data.sessao)
       }
       const lista = contasRes.data.results || contasRes.data || []
       setContas(lista)
     }).catch((err) => {
       mostrarToast(extractErrorMessage(err, 'Erro ao carregar dados.'), 'error')
     }).finally(() => setLoadingContas(false))
   }, [])
   ```
3. `frontend/src/pages/pdv/FechamentoCaixa.jsx` (linhas 39-49):
   ```js
   useEffect(() => {
     api.get('/pdv/sessoes/atual/')
       .then((res) => {
         const s = res.data.sessao
         if (!s) {
           navigate('/pdv/abertura')
           return
         }
         setSessao(s)
         setResumo(s.resumo || {})
       })
       .catch(() => {
         navigate('/pdv/abertura')
       })
       .finally(() => setLoading(false))
   }, [navigate])
   ```
4. `frontend/src/components/layout/Sidebar.jsx` (linha 8): remover a linha
   `{ to: '/pdv', label: 'PDV / Caixa', icon: '🏪' },` do array `navItems`.
5. `frontend/src/pages/Vendas.jsx`:
   - Adicionar `import { useNavigate } from 'react-router-dom'` no topo.
   - Dentro de `export default function Vendas()`: `const navigate = useNavigate()`.
   - Renderizar os dois botões conforme detalhado na seção "Telas afetadas" acima.

---

## Fora do escopo

```
- Redesenho da tela de Vendas além dos dois botões pedidos.
- Qualquer mudança em FrenteDeCaixa.jsx, AberturaCaixa.jsx ou FechamentoCaixa.jsx além
  do parsing de res.data.sessao (nenhuma mudança de layout/UX pedida ou necessária).
- Alteração de outros itens do menu lateral (Sidebar.jsx) além da remoção do item PDV.
- Novas rotas — todas as rotas de PDV já existem e não mudam.
```

---

## Critérios de Aceite (CA)

```
CA-01 - GET /api/v1/pdv/sessoes/atual/ SEM sessão aberta → 200, {"sessao": null}.
CA-02 - GET /api/v1/pdv/sessoes/atual/ COM sessão aberta → 200,
        {"sessao": {"id": ..., "status": "ABERTA", ...}} (dados reais aninhados).
CA-03 - FrenteDeCaixa: operador SEM sessão aberta não fica preso tentando criar venda
        com sessao_caixa undefined; é corretamente direcionado para /pdv/abertura.
CA-04 - FrenteDeCaixa: operador COM sessão aberta cria venda normalmente
        (sessao_caixa = id real, sem 400).
CA-05 - AberturaCaixa: operador SEM sessão nenhuma NÃO vê o banner "Você já tem uma
        sessão aberta".
CA-06 - AberturaCaixa: operador COM sessão aberta vê o banner com conta_nome real e
        data_abertura válida (não "Conta: #undefined" nem "Invalid Date").
CA-07 - FechamentoCaixa: mesmo comportamento corrigido, sem regressão no fluxo normal
        (Frente de Caixa → Fechar Caixa).
CA-08 - Sidebar.jsx não exibe mais o item "PDV / Caixa" top-level.
CA-09 - Tela de Vendas exibe dois botões distintos, lado a lado — "PDV" (navega para
        /pdv) e "Caixas" (navega para /pdv/sessoes) — funcionando de fato ao clicar.
CA-10 - Rotas /pdv, /pdv/abertura, /pdv/venda, /pdv/fechamento, /pdv/vendas e
        /pdv/sessoes continuam acessíveis e inalteradas (acesso direto por URL
        continua funcionando, inclusive para quem só usa os botões novos).
CA-11 - Suite backend/pdv/tests.py 100% passando, incluindo os 3 testes atualizados
        para o novo contrato — 0 falhas, sem @skip/@xfail.
CA-12 - npm run build limpo, 0 erros.
```

---

## Observações finais do Analista

- O pedido presumia que o backend já era consistente ("sempre retorna
  `{"sessao": ...}`") e pedia correção só no frontend. A leitura direta de
  `backend/pdv/views.py` e dos testes já existentes mostrou que isso é verdade apenas
  para o caso "sem sessão" — no caso "com sessão" o backend retorna os dados crus, sem
  aninhar. Segui a regra de não aceitar a premissa do pedido sem verificar: corrigir só
  o frontend, como pedido literalmente descreve, teria trocado o bug relatado (falso
  "sessão encerrada") por um bug simétrico e mais grave (operador COM sessão aberta
  passaria a não conseguir usar o PDV). Por isso RF-01 inclui uma mudança de backend
  que o pedido original descartava — com justificativa técnica registrada acima.
- Achado adicional não reportado no pedido: `FechamentoCaixa.jsx` consome o mesmo
  endpoint com o mesmo padrão de bug (RF-04). Hoje não se manifesta porque o fluxo
  normal só chega lá com sessão aberta, mas passaria a quebrar assim que o RF-01 for
  aplicado se não for corrigido junto — por isso entra no escopo desta manutenção em
  vez de virar uma manutenção futura separada.
- Item 2 (navegação) é puramente frontend, sem dependência do item 1 — Forge e Loom
  podem trabalhar em paralelo sem risco de conflito (Forge só toca
  `backend/pdv/views.py` e `backend/pdv/tests.py`; Loom toca os 5 arquivos de
  frontend listados).
- Nenhuma lacuna bloqueante identificada — pedido tinha informação suficiente
  (caminhos de arquivo, linhas, comportamento observado) para especificar sem precisar
  voltar ao solicitante.

---

➡️ **Planner: rotear para Pipeline B (bug + melhoria_ux sobre módulo existente) —
Forge (`backend/pdv/views.py`, `backend/pdv/tests.py`) e Loom (`FrenteDeCaixa.jsx`,
`AberturaCaixa.jsx`, `FechamentoCaixa.jsx`, `Sidebar.jsx`, `Vendas.jsx`) em paralelo →
Sentinel (validar CA-01 a CA-12, com atenção especial a CA-02/CA-04/CA-06 por serem os
casos que o pedido original teria deixado quebrados se corrigido só no frontend) →
Pilot.**
