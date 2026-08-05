# Especificação de Hotfix — UidCore PDV (Manutenção #23)

**Sistema:** UidCore
**Módulo:** PDV (Ponto de Venda) — Frente de Caixa
**Tipo:** `bug`
**Data:** 2026-08-05
**Complexidade:** baixa (fix pontual, 4 ocorrências no mesmo padrão, 1 arquivo)
**Requer aprovação comercial:** não

> Esta especificação **substitui** o conteúdo anterior deste arquivo (que
> era da Especificação da Manutenção #21, já concluída e registrada no
> histórico do `CLAUDE.md` do projeto). O conteúdo antigo permanece
> rastreável via git history — não é necessário mantê-lo aqui.

> **Nota de processo:** levantamento feito de forma retroativa — o fix já
> havia sido identificado, commitado (`262bc31`), pushed e deployado via
> CI/CD antes deste documento ser produzido. Este documento registra a
> especificação formal do que foi corrigido, para rastreabilidade e para
> servir de roteiro de verificação ao Sentinel.

---

## 1. Contexto

Solicitação de manutenção reportando que as buscas de produto e de
cliente na tela **Frente de Caixa** (`/pdv`) retornavam sempre `404`,
impedindo o operador de adicionar produtos ao carrinho ou vincular
cliente à venda — bug crítico, pois a busca é o ponto de entrada
principal do fluxo de venda no PDV.

## 2. AS-IS (confirmado por leitura de código)

A instância Axios central do frontend (`frontend/src/api/client.js`) já
define `baseURL: '/api/v1'`. As chamadas de busca em `FrenteDeCaixa.jsx`
concatenavam o segmento do recurso duas vezes:

```
/api/v1/produtos/produtos/?search=...   → 404
/api/v1/clientes/clientes/?search=...   → 404
```

Como o backend não expõe rotas duplicadas, toda chamada retornava 404 e
os arrays `resultadosBusca`/`resultadosCliente` ficavam sempre vazios. Os
blocos `catch` das buscas por debounce apenas zeram o array de resultado
(sem toast/erro visível), o que mascarava a causa — o sintoma percebido
pelo operador era só "a busca não retorna nada", sem indicação de que se
tratava de um erro de rede.

## 3. TO-BE (confirmado no código já em produção)

Lido `frontend/src/pages/pdv/FrenteDeCaixa.jsx` já deployado — as 4
chamadas usam o path correto, relativo ao `baseURL` já configurado:

```
GET /api/v1/produtos/?search=...   → 200
GET /api/v1/clientes/?search=...   → 200
```

## 4. Requisitos Funcionais afetados

| ID | Descrição | Status pós-fix |
|---|---|---|
| RF-Busca-Produto | O sistema deve permitir buscar produto por nome ou código de barras na Frente de Caixa | ✅ Restaurado |
| RF-Busca-Cliente | O sistema deve permitir buscar e vincular cliente à venda na Frente de Caixa | ✅ Restaurado |
| RF-17 (Manutenção #21) | Enter no campo de busca com match exato de código de barras adiciona produto ao carrinho sem clique (leitor físico) | ✅ Restaurado — dependia da mesma chamada de busca |
| RF-19 (Manutenção #21) | Código escaneado via câmera busca produto direto na API | ✅ Restaurado — dependia da mesma chamada de busca |

> RF-17 e RF-19 já existiam desde a Manutenção #21 — não foram criados
> agora; apenas voltaram a funcionar porque reutilizam a mesma rota
> corrigida por este hotfix.

## 5. Regras de Negócio / detalhe técnico

- **RN-14** — Toda chamada feita pela instância `api` (Axios com
  `baseURL: '/api/v1'`, `frontend/src/api/client.js`) deve começar direto
  pelo nome do recurso (ex.: `/produtos/`, `/clientes/`) e nunca repetir
  o segmento já coberto pelo `baseURL`. Esse é o padrão correto em todo o
  frontend — este bug foi um caso isolado de digitação/copy-paste em 4
  chamadas de um único arquivo, não um padrão sistêmico (as demais
  páginas do projeto já seguem `RN-14` corretamente).
- Os blocos `catch` das buscas por debounce continuam apenas zerando o
  array de resultado em caso de erro — comportamento pré-existente,
  mantido como estava, fora do escopo deste hotfix.

## 6. Root Cause

Path duplicado por engano ao integrar a busca de produto e cliente na
Frente de Caixa (Manutenção #15/#21): o segmento do recurso foi repetido
mesmo já estando coberto pelo `baseURL` global da instância Axios.

## 7. Fix aplicado (já em produção)

**Arquivo alterado:** `frontend/src/pages/pdv/FrenteDeCaixa.jsx`
**Commit:** `262bc31` — `fix(pdv): corrige path duplicado na busca de produto e cliente - Manutencao 23`
**Status:** em `origin/main`, deployado via CI/CD (GitHub Actions), confirmado por leitura direta do arquivo em produção.

| Linha (arquivo atual) | Contexto | Path corrigido |
|---|---|---|
| 125 | Busca de produto por nome/texto (debounce, 300ms) | `/produtos/?search=...` |
| 144 | Busca de cliente por nome (debounce, 300ms) | `/clientes/?search=...` |
| 201 | RF-17 — Enter com match exato de código de barras (busca imediata, cancela debounce pendente) | `/produtos/?search=...` |
| 223 | RF-19 — código escaneado via câmera (busca imediata) | `/produtos/?search=...` |

As 4 ocorrências foram confirmadas lidas diretamente no arquivo já
deployado — nenhuma duplicação de path restante.

## 8. Backend — NÃO alterado

Hotfix **puramente frontend**. Nenhum arquivo do backend foi modificado:

- ❌ Nenhuma `migration` gerada
- ❌ Nenhum `model` alterado
- ❌ Nenhuma `view`/`viewset`/`serializer` alterada
- ❌ Nenhuma rota (`urls.py`) alterada

Os endpoints `GET /api/v1/produtos/?search=...` e
`GET /api/v1/clientes/?search=...` já existiam e funcionavam
corretamente — o defeito estava exclusivamente na URL montada pelo
frontend.

## 9. Fora do Escopo

- Tratamento de erro explícito na UI quando a busca falha por outro
  motivo (hoje o `catch` só zera o array, sem toast) — não fazia parte
  do pedido, não alterado.
- Qualquer alteração de backend — endpoints já estavam corretos.
- Auditoria das demais páginas do frontend em busca do mesmo padrão de
  erro — não solicitado; recomendação abaixo (seção 11).

## 10. Riscos e Dependências

- Nenhuma migration nova, nenhuma dependência nova.
- Como o bug era silencioso (sem erro visível ao operador, apenas
  ausência de resultado), recomenda-se ao Sentinel testar com dado real
  no banco (produto e cliente existentes) para confirmar retorno
  populado, não apenas o status HTTP 200 de um payload vazio.

## 11. Sentinel — Roteiro de Teste

1. `GET /api/v1/produtos/?search=<termo existente>` → 200, produto real
   retornado (não apenas array vazio).
2. `GET /api/v1/clientes/?search=<termo existente>` → 200, cliente real
   retornado.
3. Na Frente de Caixa, digitar nome de produto existente → dropdown
   populado com o(s) resultado(s) (RF-Busca-Produto).
4. Digitar código de barras exato de 1 produto existente + Enter →
   produto adicionado ao carrinho sem clique (RF-17).
5. Vincular cliente pela busca por nome na Frente de Caixa → cliente
   vinculado à venda (RF-Busca-Cliente).
6. Suíte de testes Django completa permanece verde — backend não foi
   tocado, mas deve ser confirmado íntegro pós-deploy (182/182 esperado,
   conforme já reportado pelo Sentinel).
7. 0 falhas obrigatório, conforme regra global do Sentinel (CLAUDE.md).

**Recomendação para o Planner (fora do escopo deste hotfix, não bloqueia
a entrega):** considerar uma varredura pontual por outras chamadas Axios
no frontend que possam repetir o mesmo padrão de path duplicado
(`RN-14`), já que este bug ficou 3 manutenções (#15→#21→#23) sem ser
percebido por não gerar erro visível na UI.

## 12. Rastreabilidade

- **Manutenção:** #23 (SystemD)
- **Commit:** `262bc31`
- **Deploy:** 2026-08-05 19:01:05 UTC (16:01 -03) — container
  `uidcore-backend-1` recriado, bundle `index-CSDFwmdx.js`
- **Sentinel:** APROVADO — 182/182 testes, endpoints validados com dado
  real (`search=Rel` → produto retornado, `search=Maria` → cliente
  retornado)
- **Detalhe completo do ciclo:** ver `CLAUDE.md` do projeto, seção
  "Histórico de execuções → Manutencao #23"

---

## 13. Observações finais do Analista

Fix simples e de causa única (path duplicado por engano de digitação),
já corrigido, commitado e deployado no momento deste levantamento. Este
documento existe para fechar a rastreabilidade formal do ciclo — Especi­
ficação → Sentinel (roteiro de verificação) — mesmo com o trabalho de
código já concluído fora da esteira formal de Especificação-antes-do-fix.

➡️ **Planner:** ciclo já concluído e deployado (Manutenção #23 marcada
`feito=True`). Nenhuma ação adicional necessária além do registro deste
documento. Recomendação da seção 11 fica disponível para priorização
futura, sem bloquear nada em aberto.
