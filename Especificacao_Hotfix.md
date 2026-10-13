# Especificação Hotfix — Manutenção #66 [NUCLEO 5/5]
## LGPD: exportação de dados do titular + anonimização

**Sistema:** UidCore (OS #7)
**Data:** 2026-10-13
**Autor:** Analista (modo manutenção)
**Origem:** encerramento do Studio Fluir em 11/10/2026 exigiu, manualmente, um
relatório individual por aluno (cadastro, saúde, histórico, financeiro) +
backup + eliminação dos dados para atender pedido de titular. Esta manutenção
transforma esse procedimento manual em recurso nativo do UidCore. Fase única
do pacote [NUCLEO] (5/5) — última fase da sequência, independente das demais.

---

## 1. Contexto

### AS-IS (como é hoje)
Não existe nenhum mecanismo no UidCore para atender aos direitos do titular
previstos no art. 18 da LGPD (acesso, portabilidade, eliminação). Quando um
cliente de um sistema Uid precisa encerrar o vínculo com um titular (aluno,
paciente, cliente final) e esse titular pede os próprios dados ou pede
eliminação, o único caminho hoje é manual: alguém da Uid entra no banco,
monta um relatório à mão e decide o que apagar — como aconteceu no Studio
Fluir em 11/10/2026. Isso não escala e depende da Uid para cada pedido.

Hoje `Cliente` (app `clientes`) é referenciado por FK em pelo menos seis
apps de negócio (`financeiro.Receita`, `vendas.Orcamento`/`Pedido`,
`pdv.Venda`, `agendamento.Compromisso`, `portal.AcessoPortalCliente`,
`assinaturas.Assinatura`) — os dados pessoais do titular estão espalhados
pelo sistema, não concentrados num único lugar.

### TO-BE (o que esta manutenção entrega)
1. **Registry de exportação** (`common/lgpd.py`): núcleo genérico, cego a
   apps específicos. Cada app se registra sozinho (via `AppConfig.ready()`)
   com uma função `exportar_titular(cliente) -> dict | None`. Núcleo nunca
   precisa saber o nome dos apps — um app novo só se registra, sem tocar em
   `common/`.
2. **Exportação**: `GET /api/v1/clientes/{id}/exportar/?formato=json|pdf` —
   agrega a seção de cada app registrado num relatório único. JSON para
   portabilidade; PDF para entrega formal ao titular (capa + uma seção por
   app + rodapé de confidencialidade). Toda exportação é registrada em
   `ExportacaoTitular` (quem exportou, quando, em qual formato) — é a trilha
   de auditoria exigida antes de qualquer anonimização.
3. **Anonimização**: `POST /api/v1/clientes/{id}/anonimizar/` — irreversível,
   bloqueada (400) se não existir `ExportacaoTitular` prévia do mesmo
   cliente. Substitui dado pessoal direto (nome, documento, telefone,
   e-mail, endereço, observações, históricos, acionistas) por valor
   anonimizado. **Nunca** toca em registros financeiros/fiscais (valor,
   data, status, vínculo) — eles continuam existindo, ligados ao cliente já
   anonimizado, pela obrigação legal de guarda (LGPD art. 16, I).
4. **Frontend**: menu "LGPD" na ficha do Cliente com "Exportar dados
   (PDF/JSON)" e "Anonimizar titular" (modal de confirmação forte — digitar
   o nome atual do cliente).

---

## 2. Requisitos Funcionais — Backend

**RF-01** — Novo módulo `common/lgpd.py` com registry em memória:
```python
_REGISTRY = {}  # app_label -> {"titulo": str, "funcao": callable}

def registrar_exportador(app_label: str, titulo: str, funcao):
    """funcao(cliente) -> dict | None. None/‌{} = app não tem dado para esse cliente, omite a seção."""
    _REGISTRY[app_label] = {"titulo": titulo, "funcao": funcao}

def exportar_tudo(cliente) -> list[dict]:
    """Retorna [{"app": app_label, "titulo": ..., "dados": {...}}], só apps com dado real."""

def apps_registrados() -> list[str]:
    """Usado pelos testes do registry — lista os app_labels registrados neste processo."""
```
Sem decorator mágico — registro explícito, uma linha por app, chamado em
`AppConfig.ready()` (mesmo padrão já usado por `signals.py` nos apps
existentes). Núcleo (`common/lgpd.py`) nunca importa `clientes`, `financeiro`
etc. — é o app específico que importa o registry e se anuncia.

**RF-02** — Cada app ganha um `*/lgpd.py` com `exportar_titular(cliente)`:

| App | Seção retornada |
|---|---|
| `clientes` | cadastro completo (`PessoaBase` + `segmento`/`limite_credito`), histórico (`HistoricoCliente`), acionistas (`AcionistaCliente`) |
| `financeiro` | receitas do cliente (`Receita.objects.filter(cliente=cliente)`) — descrição, valores, vencimento/recebimento, status, estornos |
| `vendas` | orçamentos e pedidos do cliente (`Orcamento`, `Pedido` + itens) |
| `pdv` | vendas de balcão do cliente (`Venda` + itens + pagamentos) |
| `agendamento` | compromissos do cliente (`Compromisso`) |
| `portal` | acessos ao portal do cliente (`AcessoPortalCliente` — login vinculado, último acesso) |
| `assinaturas` | planos/assinaturas do cliente (`Assinatura`) |

Cada `exportar_titular` usa apenas `objects` (nunca `all_objects` — dado
soft-deletado não entra na exportação do titular) e devolve estruturas
JSON-serializáveis (decimais como string, datas em ISO 8601) — nunca retorna
o serializer DRF cru, para não vazar FK/PK de outras entidades.

**RF-03** — Novo model `common.ExportacaoTitular(BaseModel)`:
- `cliente`: FK para `clientes.Cliente`, `on_delete=PROTECT`
- `formato`: CharField choices `JSON`/`PDF`
- `conteudo_resumo`: TextField opcional (ex.: contagem de registros por
  seção, para auditoria sem guardar o PDF/JSON inteiro)

`created_by`/`created_at` (herdados de `BaseModel`) já respondem "quem
exportou e quando" — não precisa de campo duplicado. Nunca editável depois
de criado (sem PATCH/PUT — `ReadCreateViewSet` ou view função simples,
mesmo padrão já usado em `LivroCaixa`).

**RF-04** — `Cliente` (app `clientes`) ganha 3 campos novos (migration):
- `anonimizado`: BooleanField default=False
- `anonimizado_em`: DateTimeField null=True, blank=True
- `anonimizado_por`: FK para `accounts.User`, null=True, blank=True,
  `on_delete=SET_NULL`

**RF-05** — `GET /api/v1/clientes/{id}/exportar/?formato=json|pdf`
(`@action(detail=True, methods=['get'], url_path='exportar')` em
`ClienteViewSet`):
- Chama `common.lgpd.exportar_tudo(cliente)`.
- `formato=json` (default se omitido): retorna o dict completo
  (`{"cliente": {...}, "secoes": [...]}`) como JSON.
- `formato=pdf`: renderiza template HTML (capa com nome, documento, data de
  emissão + uma seção por app + rodapé de confidencialidade LGPD) e devolve
  `application/pdf` via WeasyPrint (`HttpResponse(pdf_bytes,
  content_type='application/pdf')`, `Content-Disposition: attachment`).
- Qualquer `formato` fora de `json`/`pdf` → 400.
- Grava `ExportacaoTitular(cliente=cliente, formato=formato)` **antes** de
  devolver a resposta (se a geração do PDF falhar depois de já ter
  registrado, aceitável — é só rastro de tentativa; pior seria registrar
  sem ter de fato gerado o conteúdo).
- Permissão: `common.permissions.IsAdmin` (checa `tem_acesso_total`) —
  **não** usa `BloqueiaEscritaDeProfissional` (permissão padrão da
  viewset), que libera leitura pra qualquer perfil autenticado; dado de
  titular completo não é leitura comum.

**RF-06** — `POST /api/v1/clientes/{id}/anonimizar/`
(`@action(detail=True, methods=['post'], url_path='anonimizar')`):
- Payload exige `{"confirmo": true}` — qualquer outro valor ou campo ausente
  → 400 ("confirmação obrigatória").
- Bloqueia (400, mensagem explícita) se **não existir**
  `ExportacaoTitular.objects.filter(cliente=cliente).exists()`.
- Bloqueia (400) se `cliente.anonimizado` já for `True` — operação não se
  repete (idempotência negativa: segunda tentativa é erro, não no-op
  silencioso, pra deixar claro que já foi feito).
- Dentro de `transaction.atomic()`:
  - `Cliente`: `nome_razao_social = f"Titular anonimizado #{cliente.id}"`,
    `documento=None`, `cpf=''`, `cnpj=''`, `telefone=''`, `email=''`,
    `endereco=''`, `cidade=''`, `estado=''`, `cep=''`, `observacoes=''`,
    `data_nascimento=None`, `anonimizado=True`,
    `anonimizado_em=timezone.now()`, `anonimizado_por=request.user`.
  - `HistoricoCliente` do cliente: `descricao` de cada registro substituída
    por `"[conteúdo removido por anonimização LGPD]"` (mantém a linha —
    contagem/data preservadas, texto livre removido).
  - `AcionistaCliente` do cliente: `nome = f"Acionista anonimizado #{pk}"`,
    `email=''`, `cpf=''`, `telefone=''`, `whatsapp=''`.
  - **Não toca** em `Receita`, `Orcamento`, `Pedido`, `Venda`,
    `Compromisso`, `Assinatura`, `AcessoPortalCliente` — FK pro cliente
    permanece intacta, valores/datas/status intocados (guarda legal).
- Permissão: `IsAdmin` (mesma de exportar).
- Resposta: 200 com o `Cliente` serializado já anonimizado.

**RF-07** — Teste de registry: um app fictício (ou um registro mock dentro
do próprio teste, sem precisar criar app Django novo de verdade) chama
`registrar_exportador('app_teste', 'Seção Teste', lambda c: {'ok': True})`
e o teste confirma que `exportar_tudo(cliente)` inclui essa seção — prova
que o núcleo não precisa saber o nome do app antecipadamente.

---

## 3. Requisitos Funcionais — Frontend

**RF-08** — Ficha do Cliente (`Clientes.jsx` ou tela de detalhe/edição) ganha
menu "LGPD" (visível somente para quem tem `tem_acesso_total` no frontend
também — `selectTemAcessoTotal`, já centralizado desde a Manutenção #60) com
duas ações:

1. **"Exportar dados"** — submenu/dropdown com "PDF" e "JSON". PDF abre/baixa
   o arquivo (`window.open` do blob ou link de download); JSON baixa como
   arquivo `.json` (não precisa render na tela).
2. **"Anonimizar titular"** — abre modal de confirmação forte:
   - Texto de aviso: ação irreversível, remove dados pessoais, mantém
     registros financeiros por obrigação legal.
   - Campo de texto: usuário precisa digitar exatamente o
     `nome_razao_social` atual do cliente para habilitar o botão "Confirmar
     anonimização" (mesmo padrão de fricção usado em ações destrutivas
     críticas — compara string local, não chama API a cada tecla).
   - Se a exportação prévia não existir, backend responde 400 — modal exibe
     a mensagem de erro da API (padrão já usado em todo o projeto:
     `extractErrorMessage`) orientando a exportar antes.
   - Sucesso: fecha modal, atualiza a ficha do cliente (nome agora mostra
     "Titular anonimizado #N"), toast de confirmação.

---

## 4. Requisitos Não Funcionais

**RNF-01** — PDF gerado no backend (WeasyPrint) — build do container deve
ser testado de ponta a ponta antes do deploy (ver Riscos, seção 7).

**RNF-02** — Exportação e anonimização nunca disparam para clientes
soft-deletados (`is_active=False`) — ação só faz sentido em cliente ativo;
`get_object()` da viewset já filtra isso.

**RNF-03** — Resposta de erro sempre com mensagem legível (padrão
`extractErrorMessage` do frontend já usado em todo o projeto).

**RNF-04** — Nenhuma seção do export deve vazar PK/FK de outra entidade
(ex.: ID interno de usuário do sistema, token) — somente dado pertencente ao
titular.

---

## 5. Regras de Negócio

**RN-01** — Exportar e anonimizar exigem `tem_acesso_total` — mesma regra
usada nos demais pontos sensíveis do núcleo (ex.: `IsAdmin` já usada em
`UserViewSet`).

**RN-02** — Anonimização é irreversível e bloqueada sem exportação prévia do
mesmo cliente — a exportação é o "backup" exigido pelo pedido antes da
eliminação.

**RN-03** — Registros financeiros/fiscais (Receita, Venda, Orçamento,
Pedido, Assinatura) **nunca** são apagados, nunca têm valor/data/status
alterado por esta funcionalidade — permanecem vinculados ao cliente já
anonimizado (LGPD art. 16, I: guarda para cumprimento de obrigação legal).

**RN-04** — App novo que queira aparecer na exportação só precisa registrar
sua função em `common/lgpd.py` via `AppConfig.ready()` — núcleo não é
alterado para isso.

**RN-05** — Anonimização exige confirmação explícita no payload
(`confirmo: true`) — a confirmação de UI (digitar o nome) é fricção do
frontend, não substitui a trava do backend (igual ao padrão
`AcionistaCliente`/exclusões já existentes no projeto).

**RN-06** — PDF e JSON vêm da mesma função `exportar_tudo` — nunca duas
fontes de verdade divergentes; só a apresentação muda.

**RN-07** — Cliente anonimizado não tem endpoint de reversão — não existe
"desanonimizar".

**RN-08** — Depois de anonimizado, o cliente deixa de aparecer em buscas por
nome/documento antigos (já é consequência natural de `nome_razao_social` e
`documento` terem sido substituídos — `search_fields` da viewset não muda).

---

## 6. Modelagem de Dados

```
Cliente (clientes, já existe)
  + anonimizado: bool (default False)
  + anonimizado_em: datetime (null)
  + anonimizado_por: FK accounts.User (null, SET_NULL)

ExportacaoTitular (common, novo)
  cliente: FK clientes.Cliente (PROTECT)
  formato: choices JSON/PDF
  conteudo_resumo: text (opcional)
  + created_at/created_by (BaseModel) = "quando/quem exportou"
```

Migrations: `clientes.000X_cliente_anonimizado_*` + `common.000X_exportacaotitular`.

---

## 7. Riscos e Dependências

- **WeasyPrint não está no `requirements.txt`** nem no `Dockerfile` — exige
  libs de sistema (`libpango-1.0-0`, `libpangocairo-1.0-0`,
  `libgdk-pixbuf2.0-0`, `libffi-dev`, `shared-mime-info`, fontes). O
  `Dockerfile` atual só tem `libpq-dev gcc ca-certificates poppler-utils`
  (usado pelo parser de extrato bancário com `pikepdf`). **Forge precisa
  atualizar o `Dockerfile` e testar o build real do container** antes de
  considerar a fase pronta — risco explícito citado no pedido original.
  Alternativa mais leve se o build travar: `xhtml2pdf` ou `reportlab`
  (sem dependência nativa) — decisão técnica final cabe ao Forge/Blueprint
  se WeasyPrint inviabilizar o build em tempo hábil.
- **`Compromisso.nome_contato`/`telefone_contato`/`email_contato`**
  (Manutenção #65, agendamento público) guardam dado pessoal de contato
  avulso mesmo sem `cliente` vinculado — fora do escopo desta fase (só
  processa titular já cadastrado como `Cliente`), mas registrar como débito
  técnico conhecido para uma fase futura de LGPD sobre contato público
  sem conta.
- **`documento` tem `unique=True`** em `PessoaBase` — múltiplos clientes
  anonimizados com `documento=None` não conflitam (PostgreSQL trata `NULL`
  como valores distintos em constraint unique) — confirmar com teste
  dedicado mesmo assim (2º cliente anonimizado não pode falhar ao salvar).
- **Pacote [NUCLEO] (5/5) fecha a sequência** — diferente das fases 1 a 4,
  esta pode ser marcada `feito=True` no SystemD ao final, pois é a última
  fase do pacote.

---

## 8. Fora de Escopo

- Portal self-service para o titular pedir exportação/eliminação sozinho
  (fica para o módulo "Área do Usuário/Portal do Cliente" do UidCore, numa
  manutenção futura).
- Exportação em massa de todos os clientes de uma vez.
- Anonimização automática por prazo (retenção programada) — esta fase é só
  o endpoint sob demanda, acionado por um operador com `tem_acesso_total`.

---

## 9. Critérios de Aceite

- **CA-01** — Exportar um cliente com receitas, vendas (PDV) e compromissos
  cadastrados: PDF abre normalmente, todas as seções presentes (clientes,
  financeiro, vendas/pdv, agendamento — e portal/assinaturas se houver
  dado), valores batendo com o que as telas de cada módulo mostram.
- **CA-02** — Exportar o mesmo cliente em `formato=json`: estrutura
  equivalente ao PDF, parseável, sem vazar PK/FK de outras entidades.
- **CA-03** — `ExportacaoTitular` é criado a cada exportação (JSON ou PDF),
  com `created_by`/`created_at` corretos.
- **CA-04** — Anonimizar sem exportação prévia → `400` com mensagem clara.
- **CA-05** — Anonimizar com exportação prévia e `confirmo: true` → `200`;
  cliente some das buscas por nome/documento antigos
  (`GET /api/v1/clientes/?search=<nome antigo>` não retorna mais o
  registro).
- **CA-06** — Anonimizar sem `confirmo: true` (ausente ou `false`) → `400`.
- **CA-07** — Anonimizar duas vezes o mesmo cliente → `400` na segunda
  tentativa (já anonimizado).
- **CA-08** — Antes e depois da anonimização: DRE e Livro Caixa do período
  continuam com os mesmos totais (valores de `Receita`/`LivroCaixa`
  inalterados; só o cadastro do `Cliente` muda).
- **CA-09** — Teste do registry: app registra `exportar_titular` e aparece
  na saída de `exportar_tudo` sem qualquer alteração em `common/`.
- **CA-10** — Exportar/anonimizar sem `tem_acesso_total` → `403`.
- **CA-11** — Build do container com WeasyPrint (ou alternativa escolhida)
  concluído sem erro — confirmado antes do deploy, não só em ambiente local.

---

## 10. Observações para o Blueprint/Forge/Loom

- Seguir o padrão já consolidado no projeto: `AuditMixin` na viewset onde
  fizer sentido (mas as actions `exportar`/`anonimizar` são operações
  pontuais, não CRUD — tratar `created_by`/`anonimizado_por` manualmente
  dentro da action, não via `perform_create`/`perform_update` padrão).
- `common/lgpd.py` é núcleo **genérico** — resistir à tentação de já
  deixá-lo conhecendo os app_labels de negócio; a lista de apps registrados
  é um detalhe de cada app, não do registry.
- Reaproveitar `extractErrorMessage` e os componentes de modal de
  confirmação já existentes no frontend — não criar um padrão de modal
  novo só para esta tela.
