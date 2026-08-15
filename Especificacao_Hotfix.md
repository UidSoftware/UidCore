# Especificação — Manutenção #33
**Elaborado por:** Analista (MODO HOTFIX)
**Data:** 2026-08-15
**Sistema:** UidCore (OS #7)
**Solicitação original:** "Dentro do módulo RH, trocar tudo que é 'Funcionarios'/'Funcionário' por 'Colaboradores'/'Colaborador' — tanto no backend quanto no frontend."

**Contexto adicional do Planner (repassado nesta rodada, usado como base — não
re-investigado do zero):** backend já renomeado (model, serializer, viewset, url,
migration), apenas o frontend (`Rh.jsx`) ainda usa os nomes antigos.

---

## Classificação

```
tipo: melhoria_ux (rename de nomenclatura de domínio — sem mudança de regra de negócio)
sistema: UidCore
caminho_afetado: módulo RH — backend/rh/* (já concluído) + frontend/src/pages/Rh.jsx (pendente)
complexidade: baixa
requer_aprovacao_comercial: false
```

---

## Diagnóstico confirmado (leitura direta dos arquivos)

### Backend — 100% renomeado, nenhuma ação necessária nesta manutenção

Confirmado lendo `backend/rh/serializers.py`, `backend/rh/urls.py`,
`backend/rh/migrations/0003_rename_funcionario_to_colaborador.py` e
`backend/rh/tests.py`:

- Model: `Colaborador` (não mais `Funcionario`)
- `ColaboradorSerializer` expõe `cargo_nome`, `regime_label` — sem qualquer traço de
  `funcionario`
- `FolhaPagamentoSerializer` e `RegistroFeriasSerializer` expõem o campo FK como
  `colaborador` (writable) e `colaborador_nome` (read-only, `source='colaborador.nome'`)
  — **não** `funcionario`/`funcionario_nome`
- `ColaboradorViewSet` registrado em `backend/rh/urls.py` na rota
  `router.register(r'colaboradores', views.ColaboradorViewSet, basename='colaborador')`
  → endpoint real: **`/api/v1/rh/colaboradores/`**
- Migration `0003_rename_funcionario_to_colaborador.py` presente com `RenameModel`,
  `AlterModelTable` (`rh_funcionario` → `rh_colaborador`), `AlterField` do
  `related_name` (`funcionarios` → `colaboradores`) e `RenameField` em
  `FolhaPagamento.funcionario` → `colaborador` e `RegistroFerias.funcionario` →
  `colaborador` — sem perda de dados (rename puro de tabela/coluna)
- `backend/rh/tests.py` já usa `Colaborador`, `_make_colaborador()`,
  `ColaboradorModelTest`, `ColaboradorAPITest`, e chama
  `/api/v1/rh/colaboradores/` nos testes de API — nenhuma referência residual a
  `funcionario`/`Funcionario` encontrada no arquivo

**Ação do Forge nesta manutenção:** apenas confirmar que a migration
`0003_rename_funcionario_to_colaborador.py` foi de fato **aplicada** no banco de
produção (`python manage.py showmigrations rh` ou equivalente via container) antes do
Sentinel validar. Não escrever código novo de backend — o rename já está completo.

### Frontend — pendente, único arquivo afetado: `frontend/src/pages/Rh.jsx`

Lido o arquivo inteiro (160 linhas). Todas as ocorrências de nomenclatura antiga estão
concentradas neste arquivo, na aba de Colaboradores e nas duas telas dependentes
(Folha de Pagamento e Férias, que referenciam colaborador via FK).

---

## Requisitos Funcionais

```
RF-01 (Must) - A aba do módulo RH atualmente rotulada "Funcionários" deve passar a
               se chamar "Colaboradores" — label visível e key interna do TABS.
RF-02 (Must) - O card/listagem de Colaboradores deve usar resource, título, texto do
               botão de criação e texto de lista vazia com "Colaborador(es)" em vez
               de "Funcionário(s)".
RF-03 (Must) - O endpoint consumido pelo frontend para CRUD de colaboradores deve
               apontar para /api/v1/rh/colaboradores/ (não mais /rh/funcionarios).
RF-04 (Must) - As telas de Folha de Pagamento e Férias devem exibir a coluna/campo
               relacionado ao colaborador com label "Colaborador" (não
               "Funcionário"), consumindo o campo colaborador_nome do backend
               (não mais funcionario_nome).
RF-05 (Must) - Os formulários de criação/edição de Folha de Pagamento e Férias devem
               enviar o campo colaborador (não funcionario) ao backend, com o
               select-remote apontando para o endpoint rh/colaboradores.
RF-06 (Should) - Nenhuma string visível ao usuário no módulo RH deve conter
                 "Funcionário"/"Funcionários" após a mudança (varredura completa do
                 arquivo, não só os campos citados no diagnóstico).
```

## Regras de Negócio

```
RN-01 - Rename é puramente de apresentação e de payload (label + nome de campo) —
        nenhuma regra de cálculo, validação ou fluxo existente pode mudar de
        comportamento (salário líquido, cálculo de dias de férias, soft delete,
        unicidade de CPF permanecem exatamente como estão).
RN-02 - O `key` interno da aba pode ser renomeado (ex.: 'funcionarios' →
        'colaboradores') desde que a condição de renderização (`tab === '...'`) seja
        atualizada de forma consistente — não há persistência de estado de aba entre
        sessões, então não há risco de migração de dado de UI.
```

---

## Especificação técnica — Frontend (Loom)

Arquivo único: `frontend/src/pages/Rh.jsx`. Trocar **todas** as ocorrências abaixo
(varredura RF-06 — não limitar aos pontos listados se houver outra ocorrência de
"funcionario"/"Funcionário" no arquivo):

### 1. Array `TABS` (linha 5)
```diff
- { key: 'funcionarios', label: 'Funcionários' },
+ { key: 'colaboradores', label: 'Colaboradores' },
```

### 2. Estado inicial da aba (linha 31)
```diff
- const [tab, setTab] = useState('funcionarios')
+ const [tab, setTab] = useState('colaboradores')
```

### 3. Condição de renderização da aba (linha 56)
```diff
- {tab === 'funcionarios' && (
+ {tab === 'colaboradores' && (
```

### 4. Bloco `ResourceCrud` de Colaboradores (linhas 57–83)
```diff
  <ResourceCrud
-   resource="rh/funcionarios"
-   title="Funcionários"
-   createLabel="+ Novo Funcionário"
+   resource="rh/colaboradores"
+   title="Colaboradores"
+   createLabel="+ Novo Colaborador"
    emptyIcon="👔"
-   emptyText="Nenhum funcionário encontrado."
+   emptyText="Nenhum colaborador encontrado."
    titleField="nome"
    ...
```
(campos internos deste bloco — `nome`, `cpf`, `email`, `cargo`, `regime`,
`salario_atual`, `data_admissao`, `data_demissao`, `observacoes` — **não mudam**,
já são neutros em relação ao nome da entidade)

### 5. Bloco `ResourceCrud` de Folha de Pagamento (linhas 107–132)
```diff
  columns={[
-   { key: 'funcionario_nome', label: 'Funcionário' },
+   { key: 'colaborador_nome', label: 'Colaborador' },
    ...
  ]}
  fields={[
-   { name: 'funcionario', label: 'Funcionário', type: 'select-remote', endpoint: 'rh/funcionarios', labelField: 'nome' },
+   { name: 'colaborador', label: 'Colaborador', type: 'select-remote', endpoint: 'rh/colaboradores', labelField: 'nome' },
    ...
  ]}
- emptyForm={{ funcionario: '', mes_referencia: '', salario_bruto: '', descontos: '0', status: 'ABERTA', observacoes: '' }}
+ emptyForm={{ colaborador: '', mes_referencia: '', salario_bruto: '', descontos: '0', status: 'ABERTA', observacoes: '' }}
```
```diff
- titleField="funcionario_nome"
+ titleField="colaborador_nome"
```

### 6. Bloco `ResourceCrud` de Férias (linhas 134–157)
```diff
- titleField="funcionario_nome"
+ titleField="colaborador_nome"
  columns={[
-   { key: 'funcionario_nome', label: 'Funcionário' },
+   { key: 'colaborador_nome', label: 'Colaborador' },
    ...
  ]}
  fields={[
-   { name: 'funcionario', label: 'Funcionário', type: 'select-remote', endpoint: 'rh/funcionarios', labelField: 'nome' },
+   { name: 'colaborador', label: 'Colaborador', type: 'select-remote', endpoint: 'rh/colaboradores', labelField: 'nome' },
    ...
  ]}
- emptyForm={{ funcionario: '', data_inicio: '', data_fim: '', status: 'AGENDADO' }}
+ emptyForm={{ colaborador: '', data_inicio: '', data_fim: '', status: 'AGENDADO' }}
```

### Fora do escopo (não tocar)
- `emptyIcon="👔"` (emoji da aba de Colaboradores) — mantido, é decisão de projeto já
  documentada (DIV-UI03, ver histórico de Manutenção #9/#10), não faz parte do pedido
- Título e subtítulo da página ("Recursos Humanos", "Cadastro, folha de pagamento,
  férias, admissão/demissão") — não mencionam "Funcionário", não precisam mudar
- Abas "Cargos" e demais campos de `Cargo` — não referenciam colaborador, sem alteração
- Qualquer outro arquivo do projeto — a busca do Planner e a leitura do Analista
  confirmaram que `Rh.jsx` é o único ponto do frontend com nomenclatura antiga
  relacionada a este módulo

---

## Especificação técnica — Backend (Forge)

Nenhum código a escrever. Única verificação obrigatória antes do Sentinel:

```
FORGE-01 - Confirmar que a migration 0003_rename_funcionario_to_colaborador.py
           está aplicada no banco (ambiente de teste e, após deploy, produção).
           Se estiver pendente, aplicar (`python manage.py migrate rh`) — não
           editar o arquivo de migration, ele já está correto.
```

---

## Critérios de Aceite (para o Sentinel)

```
CA-01 - Aba do módulo RH exibe "Colaboradores" (não "Funcionários")
CA-02 - Botão de criação exibe "+ Novo Colaborador"
CA-03 - Lista vazia exibe "Nenhum colaborador encontrado."
CA-04 - Listagem/criação/edição/exclusão de colaborador funciona via
        GET/POST/PATCH/DELETE em /api/v1/rh/colaboradores/ (sem 404, sem chamada
        residual a /rh/funcionarios/)
CA-05 - Tela de Folha de Pagamento exibe coluna "Colaborador" e o formulário de
        criação usa select-remote apontando para rh/colaboradores, salvando
        corretamente o campo colaborador (FK)
CA-06 - Tela de Férias exibe coluna "Colaborador" e o formulário de criação usa
        select-remote apontando para rh/colaboradores, salvando corretamente o
        campo colaborador (FK)
CA-07 - grep -in "funcionario" em frontend/src/pages/Rh.jsx retorna vazio após a
        alteração (varredura completa, RF-06)
CA-08 - Suite backend/rh/tests.py continua 100% passando (já usa nomenclatura
        Colaborador — não deve haver regressão, backend não é alterado nesta
        manutenção além da verificação FORGE-01)
CA-09 - Nenhuma regressão em Cargo (aba e CRUD não tocados por esta manutenção)
```

---

## Observações finais do Analista

- Este é um rename simples de UI + payload, sem risco de regra de negócio — mas o
  pipeline completo (Forge confirma migration → Loom altera `Rh.jsx` → Sentinel roda
  suite + valida CA-01 a CA-09 → Pilot deploya) deve ser seguido normalmente. Tamanho
  pequeno não dispensa nenhuma etapa da esteira.
- Não há lacuna a confirmar com o cliente — o pedido é objetivo e o diagnóstico do
  Planner already cobre 100% dos pontos de mudança necessários no frontend.

---

➡️ **Planner: rotear para Pipeline C (feature/rename pequena) — Forge (verificação de
migration) + Loom (Rh.jsx) em paralelo → Sentinel → Pilot.**
