# Especificacao_Hotfix — Manutencao #10 — UidCore
**Data:** 2026-07-30
**Sistema:** UidCore (OS #7) — Template Financeiro Multi-Nicho
**Origem:** Solicitacao direta — paridade de tela com o SystemD
**Agente produtor:** Analista
**Tipo:** `feature_pequena` (gap 100% frontend — backend ja implementado e em producao)
**Requer aprovacao comercial:** nao (dentro do escopo do contrato UidCore/financeiro)

---

## 1. Classificacao

| Campo | Valor |
|---|---|
| Sistema | UidCore |
| Caminho do projeto | `/var/www/uidcore` |
| Tipo | `feature_pequena` |
| Caminho afetado | `frontend/src/pages/`, `frontend/src/routes/`, `frontend/src/components/layout/Sidebar.jsx` |
| Complexidade | baixa — sem mudanca de contrato de API, sem migration, sem model novo |
| Backend | ja existe e ja esta em producao (ver secao 3) — **nao mexer** |

---

## 2. Escopo desta manutencao

### Incluido
- **RF-F01** — Pagina `Conciliacao.jsx` com listagem de historico de conciliacoes
- **RF-F02** — Modal de upload de novo extrato (arquivo PDF + conta + periodo + senha opcional + auto)
- **RF-F03** — Tela de detalhe de uma conciliacao com lista de itens
- **RF-F04** — Acao de confirmar item divergente (`FALTANDO_SISTEMA` + `confirmado=false`)
- **RF-F05** — Aba de Padroes Seguros de Conciliacao (listagem + CRUD)
- **RF-F06** — Rota `/conciliacao` registrada no router
- **RF-F07** — Item de menu "Conciliacao" na Sidebar

### Fora do escopo (nao implementar nesta manutencao)
- Qualquer alteracao em `views.py`, `parsers.py`, `conciliacao_service.py`, `serializers.py`, `models.py` do app `financeiro`
- `destroy`/`delete` em `ConciliacaoViewSet` — ele e `ReadOnlyModelViewSet` de proposito (extrato processado e imutavel; se um dia for pedido soft-delete, e mudanca de backend fora desta manutencao — **nao pedido agora**)
- Sistema de perfis/roles no `User` — usar `IsAuthenticated` como o resto do UidCore
- Re-processamento/replay de um extrato ja enviado (nao existe endpoint para isso)

---

## 3. Backend — JA EXISTE (somente leitura/consumo, nao alterar)

Confirmado em `backend/financeiro/views.py`, `urls.py`, `serializers.py`, `models.py`.

### 3.1 Endpoints

| Metodo | Path | Descricao |
|---|---|---|
| `POST` | `/api/v1/financeiro/conciliacoes/upload/` | multipart: `arquivo` (PDF), `conta_id`, `periodo` (`YYYY-MM`), `senha` (opcional), `auto` (opcional, boolean-like string) |
| `GET` | `/api/v1/financeiro/conciliacoes/` | lista historico (paginado — `response.data.results`) |
| `GET` | `/api/v1/financeiro/conciliacoes/{id}/itens/` | lista itens de uma conciliacao |
| `POST` | `/api/v1/financeiro/conciliacoes/{id}/confirmar-item/` | body `{ item_id }` — marca `confirmado=true`, recalcula `divergencias`/`status` da conciliacao |
| `GET/POST/PUT/PATCH/DELETE` | `/api/v1/financeiro/padroes-conciliacao/` | CRUD completo (`ModelViewSet`) — `DELETE` faz soft delete (`is_active=False`) |
| `GET` | `/api/v1/financeiro/contas/` | lista contas (ja usado em `Financeiro.jsx` — reaproveitar mesmo padrao) |

`ConciliacaoViewSet` e `ReadOnlyModelViewSet` — so tem `list`, `retrieve` + as 2 actions acima. **Nao ha e nao deve ser criado** `create`/`update`/`destroy` padrao nele.

### 3.2 Campos retornados — `ConciliacaoExtratoSerializer`

```
id, conta, conta_nome, arquivo_nome, periodo,
processado_em, status, status_label,
total_banco, total_sistema, divergencias
```
Todos os campos exceto `conta` (write) sao `read_only` — a tela so exibe, nunca edita a conciliacao em si.

**Status possiveis** (`StatusConciliacao`): `PROCESSADO` | `COM_DIVERGENCIAS` | `PENDENTE`

Cores sugeridas (reaproveitar padrao `STATUS_BADGES` de `Financeiro.jsx`):
```
PROCESSADO        -> verde  (bg-green-100 text-green-800)
COM_DIVERGENCIAS  -> vermelho (bg-red-100 text-red-800)
PENDENTE          -> amarelo (bg-yellow-100 text-yellow-800)
```

### 3.3 Campos retornados — `ItemConciliacaoSerializer`

```
id, conciliacao, data_banco, descricao_banco,
valor, tipo, tipo_label, status, status_label,
lancamento_lc, confirmado, is_active, created_at
```

**Tipo** (`TipoLancamento`): `ENTRADA` | `SAIDA`
**Status do item** (`StatusItemConciliacao`): `CONCILIADO` | `FALTANDO_SISTEMA` | `FALTANDO_BANCO`

**Regra de exibicao do botao "Confirmar":** so aparece quando `status === 'FALTANDO_SISTEMA' && confirmado === false`. Os outros dois status (`CONCILIADO`, `FALTANDO_BANCO`) sao so informativos nesta tela — `FALTANDO_BANCO` significa que o sistema tem um lancamento que nao apareceu no extrato do banco, e a resolucao disso e manual, fora do escopo desta tela (fica so como alerta visual).

### 3.4 Campos retornados — `PadraoSeguroConciliacaoSerializer`

```
id, descricao_padrao, tipo, tipo_label,
natureza, natureza_label, is_active, created_at
```

**IMPORTANTE — correcao em relacao ao pedido original:** o pedido descreveu o CRUD como "descricao, tipo ENTRADA|SAIDA", mas o model real (`PadraoSeguroConciliacao`) tem **3 campos editaveis**, nao 2:

- `descricao_padrao` (texto — trecho do extrato que casa com esse padrao)
- `tipo`: `ENTRADA` | `SAIDA` (mesmo `TipoLancamento` do item de conciliacao)
- `natureza`: `APORTE` | `RECEITA_FINANCEIRA` — **so faz sentido quando `tipo=ENTRADA`** (help_text do model: "Apenas para tipo=ENTRADA: APORTE vai para PL; RECEITA_FINANCEIRA entra no DRE"). Default `APORTE`.

**RN-01:** o formulario de Padrao Seguro deve esconder/desabilitar o campo `natureza` quando `tipo=SAIDA` (nao faz sentido semantico e o backend nao valida isso — a UI e a unica barreira).

---

## 4. Requisitos Funcionais — Frontend (o que sera criado)

### RF-F01 — Listagem de historico
- Tabela (padrao desktop) / cards (padrao mobile) igual ao estilo de `LivroCaixaTab` em `Financeiro.jsx`
- Colunas: Periodo (formatado `MM/YYYY`), Conta, Status (badge), Total Banco, Total Sistema, Divergencias, Processado em
- Clique na linha/card abre o detalhe (RF-F03)
- `GET /financeiro/conciliacoes/` — usar `response.data.results` (PageNumberPagination), com `Pagination` component existente

### RF-F02 — Modal "Nova Conciliacao"
- Botao no topo da pagina, ao lado do titulo (mesmo padrao de `+ Nova Receita` em `Financeiro.jsx`)
- Campos:
  - `arquivo`: `<input type="file" accept="application/pdf">` — obrigatorio
  - `conta_id`: `Select` populado via `GET /financeiro/contas/` (mesmo padrao do `useEffect` em `Financeiro.jsx` linha 102-109) — obrigatorio
  - `periodo`: `<input type="month">` (nativo do HTML, gera `YYYY-MM` direto) — obrigatorio
  - `senha`: `Input` type password, opcional (label "Senha do PDF (se protegido)")
  - `auto`: checkbox, opcional (label "Conciliar automaticamente por padroes seguros")
- Submit: `FormData` + `POST /financeiro/conciliacoes/upload/` com header `multipart/form-data` (o `client.js` axios default e `application/json` — sobrescrever `Content-Type` nesta chamada especifica, igual qualquer upload de arquivo)
- Erro de validacao (400: "arquivo, conta_id e periodo sao obrigatorios" ou "Conta nao encontrada" ou "Formato de periodo invalido") -> `extractErrorMessage()` + toast, igual ao resto da pagina Financeiro
- Sucesso: fecha modal, mostra toast, recarrega a listagem (RF-F01) — se o backend retornar o objeto criado no payload de resposta, abrir o detalhe direto e opcional ("nice to have"); senao, so recarregar a lista e o usuario clica

### RF-F03 — Detalhe da conciliacao
- Acessado clicando numa linha da listagem (estado local `selecionada` na pagina, sem rota propria — decisao de implementacao do Loom entre aba interna ou `Modal` maxW="max-w-4xl", ambos atendem o RF)
- Header do detalhe: conta, periodo, status (badge), total banco, total sistema, divergencias
- `GET /financeiro/conciliacoes/{id}/itens/` — lista de itens
- Tabela: Data, Descricao (do banco), Valor, Tipo (ENTRADA/SAIDA com cor verde/vermelho igual `LivroCaixaTab`), Status (badge), Acao
- Linha com `status=CONCILIADO` -> visual neutro, sem acao
- Linha com `status=FALTANDO_BANCO` -> visual de alerta (amarelo/laranja), sem acao (fora do escopo resolver aqui)
- Linha com `status=FALTANDO_SISTEMA && confirmado=false` -> visual de alerta (vermelho) + botao "Confirmar"
- Linha com `status=FALTANDO_SISTEMA && confirmado=true` -> visual neutro (ja resolvido), sem acao

### RF-F04 — Confirmar item
- Botao "Confirmar" -> `POST /financeiro/conciliacoes/{id}/confirmar-item/` com body `{ item_id }`
- Resposta: `{ ok: true, divergencias_restantes: N }`
- Apos sucesso: atualizar o item na lista local para `confirmado=true` (ou re-fetch dos itens) + atualizar contador de divergencias no header do detalhe + toast de sucesso
- Erro: toast com `extractErrorMessage()`

### RF-F05 — Aba "Padroes Seguros"
- Segunda aba/secao dentro da mesma pagina `Conciliacao.jsx` (padrao de abas igual `TABS` em `Financeiro.jsx`: `[{key:'historico', label:'Historico'}, {key:'padroes', label:'Padroes Seguros'}]`)
- Listagem: Descricao, Tipo (badge ENTRADA/SAIDA), Natureza (so exibe quando tipo=ENTRADA)
- Botao "+ Novo Padrao" -> abre modal com `descricao_padrao` (Input), `tipo` (Select ENTRADA/SAIDA), `natureza` (Select APORTE/RECEITA_FINANCEIRA, visivel/habilitado somente quando `tipo=ENTRADA` — RN-01)
- Editar (abre mesmo modal preenchido) e Excluir (confirm + `DELETE`, soft delete no backend) — mesmo padrao de `ContasTab`/`ReceitasTab` em `Financeiro.jsx`
- Considerar usar o componente `ResourceCrud.jsx` existente se ele cobrir esse CRUD simples (verificar antes de recriar do zero — instrucao do CLAUDE.md do projeto: "usar componentes UI existentes em vez de recriar estilo")

### RF-F06 — Rota
- `frontend/src/routes/index.jsx`: importar `Conciliacao` de `../pages/Conciliacao.jsx` e adicionar `<Route path="/conciliacao" element={<Conciliacao />} />` dentro do bloco `ProtectedRoute` (mesmo nivel de `/financeiro`)

### RF-F07 — Menu lateral
- `frontend/src/components/layout/Sidebar.jsx`: adicionar em `navItems`, logo apos o item `financeiro` (ordem sugerida por ser sub-modulo do financeiro):
  ```js
  { to: '/conciliacao', label: 'Conciliação', icon: '🔄' }
  ```
  **Atencao:** o restante da Sidebar hoje usa emoji puro (`📊`, `👥` etc. — mesmo com `lucide-react` disponivel no `package.json`). Essa e uma divergencia ja identificada e suspensa na Manutencao #9 (DIV-UI03: "padrao intencional, nao alterar"). Ou seja: **manter emoji `🔄` para consistencia com o padrao atual da Sidebar**, nao migrar so este item para Lucide.

---

## 5. Requisitos Nao Funcionais

- **RNF-01** — Upload de PDF deve mostrar estado de loading/disabled no botao de submit durante o processamento (arquivo pode levar alguns segundos para o parser processar)
- **RNF-02** — Fontes: Plus Jakarta Sans + DM Sans (ja configuradas globalmente desde a Manutencao #9 — nao precisa reconfigurar, so nao usar classe/estilo que quebre isso)
- **RNF-03** — Responsivo: padrao mobile (cards) / desktop (tabela) igual ao resto do Financeiro
- **RNF-04** — Nenhuma chamada de API sem tratamento de erro (toda promise com `.catch` + `extractErrorMessage`)
- **RNF-05** — `vite build` deve terminar sem warnings novos (nem sobre imports nao usados, nem sobre chunks)

---

## 6. Regras de Negocio

- **RN-01** — Campo `natureza` do Padrao Seguro so e relevante/editavel quando `tipo=ENTRADA` (ver secao 3.4)
- **RN-02** — Botao "Confirmar" so aparece para item com `status=FALTANDO_SISTEMA` e `confirmado=false` — nunca para `CONCILIADO` ou `FALTANDO_BANCO` (esses dois nao tem acao disponivel nesta tela)
- **RN-03** — `ConciliacaoViewSet` nao tem `create` nem `destroy` — a tela nunca deve tentar `DELETE` ou `POST` direto em `/conciliacoes/{id}/`, so nas actions `upload/`, `itens/` e `confirmar-item/`

---

## 7. Telas (resumo visual)

```
/conciliacao
├── [Aba: Historico] (default)
│   ├── Header: "Conciliação Bancária" + botao "+ Nova Conciliação"
│   ├── Lista/tabela de conciliacoes (RF-F01)
│   │   └── clique -> abre Detalhe (RF-F03) com itens + acao confirmar (RF-F04)
│   └── Modal "Nova Conciliação" (RF-F02)
│
└── [Aba: Padrões Seguros]
    ├── Header: "Padrões Seguros" + botao "+ Novo Padrão"
    ├── Lista de padroes (RF-F05)
    └── Modal criar/editar padrao
```

---

## 8. Especificacao Frontend — arquivos a criar/alterar

| Arquivo | Acao |
|---|---|
| `frontend/src/pages/Conciliacao.jsx` | **criar** — pagina completa (RF-F01 a RF-F05) |
| `frontend/src/routes/index.jsx` | **editar** — import + rota `/conciliacao` (RF-F06) |
| `frontend/src/components/layout/Sidebar.jsx` | **editar** — item de menu (RF-F07) |

Componentes UI a reaproveitar (nao recriar): `Card`, `Button`, `Input`, `Select`, `Modal`, `Pagination` (todos em `frontend/src/components/ui/`), `extractErrorMessage`/`stripEmptyStrings` (`frontend/src/utils/errors.js`), `api` client (`frontend/src/api/client.js`).

Padrao de referencia direta para a estrutura da pagina: `frontend/src/pages/Financeiro.jsx` (abas via `useState` + array `TABS`, toast local, `contasOptions` via `useEffect` + `GET /financeiro/contas/`, tabelas desktop/cards mobile, badges de status).

---

## 9. Criterios de Aceite (para o Sentinel)

- CA-01 — `GET /conciliacoes/` exibido em lista paginada, badge de status correta para os 3 valores
- CA-02 — Upload real de um PDF (ambiente `docker compose -p uidcore-test`) cria uma nova conciliacao e ela aparece na listagem
- CA-03 — Upload com campos obrigatorios faltando mostra erro legivel (nao generico) vindo do backend
- CA-04 — Detalhe de uma conciliacao lista os itens com tipo/status corretos
- CA-05 — Confirmar um item `FALTANDO_SISTEMA` chama `confirmar-item/`, o item muda de estado na tela sem reload manual, e o contador de divergencias atualiza
- CA-06 — Botao "Confirmar" **nao aparece** para itens `CONCILIADO` ou `FALTANDO_BANCO`
- CA-07 — CRUD de Padroes Seguros funcional (criar, editar, listar, excluir) com os 3 campos (`descricao_padrao`, `tipo`, `natureza`)
- CA-08 — Campo `natureza` escondido/desabilitado quando `tipo=SAIDA` no formulario de Padrao Seguro
- CA-09 — Rota `/conciliacao` acessivel via Sidebar, protegida por `ProtectedRoute` (redireciona pra `/login` se nao autenticado)
- CA-10 — `vite build` sem warnings novos
- CA-11 — Nenhuma chamada `DELETE`/`POST create` direta em `/conciliacoes/{id}/` (so as actions documentadas)

---

## 10. Validacao obrigatoria (antes do Sentinel aprovar)

- Testar upload real com PDF em ambiente de teste (`docker compose -p uidcore-test`)
- `vite build` limpo, sem warnings novos
- Confirmar item `FALTANDO_SISTEMA` e ver o lancamento (`LivroCaixa` referenciado via `lancamento_lc`) refletido corretamente na tela — ou ao menos o item saindo do estado pendente

---

## 11. Passagem de bastao

```
✅ Solicitacao classificada — UidCore (OS #7)
   tipo: feature_pequena
   descricao_tecnica: Tela de Conciliacao Bancaria no frontend (paridade SystemD) —
     backend 100% pronto, gap e so frontend (pagina + rota + menu)
   caminho_afetado: frontend/src/pages/Conciliacao.jsx (novo),
     frontend/src/routes/index.jsx, frontend/src/components/layout/Sidebar.jsx
   requer_aprovacao_comercial: false
➡️  Planner: rotear para Pipeline C (feature_pequena) — Loom implementa,
   Forge nao tem trabalho nesta manutencao (backend ja pronto e nao deve ser tocado),
   Sentinel valida os 11 CAs acima, Pilot so libera com Sentinel = APROVADO explicito.
```
