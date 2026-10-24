# Especificação Hotfix — Manutenção #69

**Sistema:** UidCore (OS #7)
**Projeto:** /var/www/uidcore
**Tipo:** `melhoria_ux`/infra — upgrade de dependência crítica de segurança (sem tela nova, sem endpoint novo)
**Data:** 2026-10-24
**Analista:** Claude (modo manutenção)

---

## 1. Contexto

A série Django 4.2 LTS saiu do período de correções de segurança em
**abril/2026**. O UidCore está hoje em `Django>=4.2,<5.0` (resolvido em
produção para 4.2.30, confirmado em `backend/requirements.txt`). A
série **5.2 LTS** recebe correções de segurança até **abril/2028** — é o
próximo LTS, não uma versão intermediária (4.2 → 5.0 → 5.1 → 5.2).

Esta manutenção **não altera nenhuma tela nem contrato de API** — é
100% backend/infraestrutura. Por isso não há `Especificacao_UI_Hotfix.md`
nesta manutenção (sem trabalho de Brush/Loom).

**Achado do Analista, divergente do pedido original:** o pedido descreve
o `unique_together` revisado como estando em `financeiro.models.Conta`
(nome+tipo). Leitura real do código mostra que `Conta` não tem
`unique_together` (só `db_table`/`ordering`) — o model com
`unique_together = [['nome', 'tipo']]` é **`financeiro.models.Categoria`**
(linha 67), não `Conta`. O outro ponto citado, `produtos.models.
ConversaoUnidade` (produto+unidade, linha 74), está correto. RN-02 abaixo
já reflete o escopo real (`Categoria`, não `Conta`).

---

## 2. AS-IS (como é hoje)

```
backend/requirements.txt:
  Django>=4.2,<5.0                  → resolvido hoje em 4.2.30 (fim do suporte: abril/2026)
  djangorestframework>=3.14
  djangorestframework-simplejwt>=5.3  → resolvido hoje em 5.5.1
  django-cors-headers>=4.3            → resolvido hoje em 4.9.0
  django-filter>=23.5
  psycopg2-binary>=2.9
  python-decouple>=3.8
  gunicorn>=21.2
  pikepdf>=8.0
  weasyprint>=60.0

Dockerfile: FROM python:3.12-slim (Python 3.12.14 confirmado no container)
backend/core/settings.py:
  USE_TZ = True                      (já presente, Django 5.0+ só mudou o DEFAULT, sem impacto aqui)
  ASGI_APPLICATION + WSGI_APPLICATION configurados juntos (padrão Django 5.x, sem ação)
  AUTH_USER_MODEL = 'accounts.User'
  DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

Uso de unique_together fora de migrations/testes (grep confirmado, 2 ocorrências):
  - financeiro/models.py:67  → class Categoria(BaseModel): unique_together = [['nome', 'tipo']]
  - produtos/models.py:74    → class ConversaoUnidade(BaseModel): unique_together = [('produto', 'unidade')]

APIs/padrões legados que o Django 5.x removeu (grep confirmado, 0 ocorrências de cada):
  - django.conf.urls.url()
  - django.utils.encoding.force_text / smart_text
  - django.utils.http.is_safe_url
  - format_html() sem placeholders correspondentes aos args
```

---

## 3. TO-BE (como será)

```
backend/requirements.txt:
  Django==5.2.18                      ← versão exata pinada, último patch 5.2.x publicado no PyPI (LTS, suporte até abril/2028)
  djangorestframework==3.18.0         ← pin exato, conforme já usado no SystemD (consistência de stack da fábrica)
  djangorestframework-simplejwt==5.5.1  ← mantém (já pinada/resolvida na versão pedida)
  django-cors-headers==4.9.0          ← mantém (já pinada/resolvida na versão pedida)
  django-filter==25.1                 ← pin exato, versão já em uso em produção
  psycopg2-binary>=2.9                ← mantém intervalo aberto (sem major bump)
  python-decouple>=3.8                ← mantém intervalo aberto
  gunicorn>=21.2                      ← mantém intervalo aberto
  pikepdf>=8.0                        ← mantém intervalo aberto
  weasyprint>=60.0                    ← mantém intervalo aberto
```

**Observação do Analista (registrar, não decidir sozinho):** no momento
da análise, a versão mais recente publicada no PyPI é
`djangorestframework==3.18.3` e `django-filter==26.2` — mais novas do que
as versões pinadas pedidas (3.18.0 e 25.1). O pedido pede explicitamente
essas versões exatas por consistência com o que já está em produção no
SystemD/UidCore — Forge deve seguir o pedido como está (pin em 3.18.0 e
25.1), não atualizar sozinho para o mais recente. Se Luiz Eduardo quiser
ir direto para as versões mais novas, isso é uma decisão de escopo
separada, fora desta manutenção.

**Nenhuma mudança de código funcional (model/serializer/viewset) é
obrigatória para o Django 5.2 funcionar** — os pontos de atenção do
Django 5.0/5.1/5.2 já foram varridos e o único item com uso real no
código é o `unique_together` (RN-02, abaixo), que é um `DeprecationWarning`
não bloqueante, não um erro.

---

## 4. Requisitos Funcionais

```
RF-01 — Atualizar backend/requirements.txt para pinar:
  Django==5.2.18
  djangorestframework==3.18.0
  django-filter==25.1
  (djangorestframework-simplejwt e django-cors-headers permanecem como já
  estão especificados hoje — 5.5.1 e 4.9.0 — sem mudança de versão)

RF-02 — Rebuildar a imagem Docker do backend (Dockerfile já usa
  python:3.12-slim, compatível com Django 5.2 que exige Python 3.10+ —
  sem mudança no Dockerfile) e confirmar que `pip install -r
  requirements.txt` resolve sem conflito de versão entre Django 5.2,
  DRF 3.18.0, django-filter 25.1 e djangorestframework-simplejwt 5.5.1.

RF-03 — Rodar `python manage.py migrate --check` / `makemigrations
  --check --dry-run` pós-upgrade para confirmar que a troca de versão do
  Django não gera nenhuma migration nova inesperada (troca de versão de
  framework não deve alterar estado de schema).

RF-04 — Rodar a suíte de testes Django completa do projeto com
  `-W error::DeprecationWarning` (ou equivalente — ex:
  `python -We::DeprecationWarning manage.py test`) para capturar
  qualquer DeprecationWarning introduzido pelo upgrade, incluindo o
  `unique_together` de RN-02. Não é obrigatório que o warning vire erro
  bloqueante nesta manutenção (ver RN-02) — é obrigatório que ele seja
  **visível e documentado** no relatório do Sentinel, não silenciado.
```

---

## 5. Requisitos Não Funcionais

```
RNF-01 — Zero downtime perceptível além do já esperado em qualquer
  deploy via CI/CD (rebuild de imagem + recreate do container backend) —
  não introduzir passo manual, não pular o pipeline GitHub Actions já
  existente (.github/workflows/deploy.yml).

RNF-02 — Nenhuma migration de dados (RunPython) é esperada nesta
  manutenção — é upgrade de framework/dependências, não mudança de
  model. Se o autodetector do Django gerar qualquer AlterField/migration
  de ruído por drift de versão (padrão já documentado no CLAUDE.md
  global da fábrica), isso deve ser revisado manualmente antes de
  aplicar — nunca aplicar automaticamente sem revisão.

RNF-03 — A suíte de testes Django do projeto deve continuar em 0 falhas
  após o upgrade — mesmo princípio de "0 falhas obrigatório" do Sentinel
  (CLAUDE.md global), sem exceção por ser upgrade de dependência.
```

---

## 6. Regras de Negócio / Técnicas

```
RN-01 — Django==5.2.18 é a versão exata a pinar (último patch 5.2.x
  publicado no PyPI no momento desta análise — confirmado via
  https://pypi.org/pypi/django/json). Se, no momento em que o Forge for
  executar, já existir um patch 5.2.x mais novo publicado, usar o mais
  novo da série 5.2 (LTS) — nunca pular para 6.x, que é série não-LTS e
  fora do escopo deste pedido.

RN-02 — unique_together é deprecated em favor de UniqueConstraint desde
  Django 4.1/5.1, mas continua funcional em Django 5.2 (não é breaking
  change, só gera DeprecationWarning). Forge NÃO deve remover ou converter
  `unique_together` para `UniqueConstraint` nesta manutenção — está fora
  do escopo do pedido original ("documentar, não remover"). Os dois
  pontos reais no código (confirmados por grep, excluindo migrations e
  arquivos de teste) são:
    - financeiro/models.py:67 — class Categoria(BaseModel):
      unique_together = [['nome', 'tipo']]
      (o pedido original citava "Conta: nome+tipo" — achado do Analista:
      isso está incorreto, Conta não tem unique_together; o model real é
      Categoria. Forge deve usar Categoria como referência ao documentar/
      confirmar o warning, não procurar em Conta.)
    - produtos/models.py:74 — class ConversaoUnidade(BaseModel):
      unique_together = [('produto', 'unidade')]
  Recomendação a registrar no relatório do Sentinel/Pilot (não implementar
  agora): migração futura trocando os dois para UniqueConstraint
  equivalente, sem mudança de comportamento, só para eliminar o warning
  antes da próxima LTS.

RN-03 — Meta.ordering não é mais aplicada automaticamente em alguns
  querysets de agregação a partir do Django 5.x. Forge deve, ao rodar a
  suíte de testes completa pós-upgrade, prestar atenção a qualquer teste
  que dependa implicitamente de ordem de resultado sem `.order_by()`
  explícito (sintoma: teste que comparava lista por índice passa a falhar
  ou fica flaky) — se achar algum caso real, adicionar `.order_by()`
  explícito no queryset afetado (fix pontual, não refatoração ampla).
  Se nenhum teste quebrar por isso, não há ação — não inventar um
  problema que não se manifestou.

RN-04 — django.conf.urls.url(), force_text/smart_text e is_safe_url
  (removidos em versões anteriores ao 5.2, ou já deprecated há mais
  tempo) foram confirmados ausentes do código via grep nesta análise —
  Forge não precisa procurar de novo, mas se encontrar algum durante a
  implementação (ex: em código gerado dinamicamente ou vendor/), tratar
  como bloqueante e substituir pela API atual (django.urls.re_path,
  str(), url_has_allowed_host_and_scheme).

RN-05 — format_html() sem placeholders correspondentes aos argumentos
  passados (passa a lançar TypeError em Django 5.1+) foi confirmado
  ausente do código via grep — sem ação necessária, só registrar que foi
  checado.

RN-06 — psycopg2-binary, python-decouple, gunicorn, pikepdf e weasyprint
  permanecem com intervalo aberto (`>=`) — não pinar nem subir versão
  major nesta manutenção. WeasyPrint já tem precedente confirmado
  funcionando em produção com as libs de sistema do Dockerfile atual
  (Manutenção #66) — não alterar o Dockerfile.
```

---

## 7. Fora do Escopo

```
❌ Converter unique_together para UniqueConstraint (ver RN-02 — documentar,
   não implementar agora)
❌ Subir para Django 6.x (não-LTS) ou qualquer versão além de 5.2.x
❌ Atualizar djangorestframework-simplejwt e django-cors-headers além das
   versões já especificadas (5.5.1 e 4.9.0) — já estão nas versões pedidas
❌ Subir psycopg2-binary, python-decouple, gunicorn, pikepdf ou weasyprint
   para versão major nova
❌ Qualquer mudança de tela, componente ou contrato de API visível ao
   frontend — esta manutenção não tem Especificacao_UI_Hotfix.md
❌ Qualquer refatoração de querysets/ordering não motivada por uma falha
   de teste real observada (RN-03 é reativo, não preventivo)
```

---

## 8. Riscos e Dependências

```
⚠️ djangorestframework==3.18.0 exige Django >=4.2 e DRF 3.15+ é o mínimo
   documentado para suportar Django 5.x — 3.18.0 já está bem acima desse
   mínimo, risco baixo de incompatibilidade.
⚠️ django-filter==25.1 já está em produção no mesmo projeto segundo o
   pedido — risco baixo, é só re-pinar a versão exata no requirements.txt
   em vez de deixar o intervalo aberto resolver para ela.
⚠️ Rebuild de imagem Docker consome tempo de CI maior que um deploy comum
   (reinstala todas as dependências Python do zero) — não é um risco de
   correção, só de tempo de pipeline; não é motivo para pular etapa do
   Sentinel.
⚠️ Se o autodetector do Django gerar qualquer migration de ruído ao correr
   makemigrations pós-upgrade (drift de estado pré-existente, padrão já
   documentado no CLAUDE.md global da fábrica), Forge deve revisar
   manualmente antes de decidir se aplica ou descarta — nunca aplicar uma
   migration gerada sem entender o que ela faz.
```

---

## 9. Critérios de Aceite do Sentinel

```
CA-01 — pip list (ou equivalente dentro do container) ANTES do upgrade
  documentado, e DEPOIS do upgrade documentado, com diff explícito
  mostrando: Django 4.2.30 → 5.2.18 (ou patch mais novo da 5.2, ver RN-01),
  djangorestframework → 3.18.0, django-filter → 25.1, demais pacotes
  inalterados em versão major.

CA-02 — Suíte de testes Django completa do projeto rodada com
  DeprecationWarning habilitado (-W error::DeprecationWarning ou
  equivalente que torne os warnings visíveis no output, não
  necessariamente bloqueante) — resultado deve ser 0 falhas, e o
  DeprecationWarning esperado de unique_together (Categoria e
  ConversaoUnidade, RN-02) deve aparecer no log e ser citado no
  relatório do Sentinel como "esperado, não bloqueante".

CA-03 — makemigrations --check --dry-run pós-upgrade: 0 pendências
  inesperadas. Se aparecer alguma migration de ruído, ela deve estar
  documentada e revisada (aplicada ou descartada conscientemente), nunca
  ignorada silenciosamente.

CA-04 — Login com credencial válida (usuário real de teste, endpoint real
  de obtenção de token JWT) retorna HTTP 200 com access/refresh token —
  confirma que djangorestframework-simplejwt 5.5.1 continua funcionando
  normalmente sob Django 5.2.

CA-05 — Login com senha incorreta (mesmo usuário, senha errada) retorna
  HTTP 401.

CA-06 — Chamada a um endpoint protegido (ex: /api/v1/financeiro/dashboard/
  ou /api/v1/accounts/usuarios/) sem token de autenticação retorna
  HTTP 401 — confirma que DEFAULT_PERMISSION_CLASSES=IsAuthenticated e
  JWTAuthentication continuam funcionando sob DRF 3.18.0 + Django 5.2.

CA-07 — Build da imagem Docker do backend conclui sem erro de resolução
  de dependência (pip install -r requirements.txt não gera conflito entre
  Django 5.2.18, DRF 3.18.0, django-filter 25.1, simplejwt 5.5.1,
  cors-headers 4.9.0).

CA-08 — gunicorn sobe os workers normalmente pós-rebuild, sem crash no
  log (mesmo padrão de verificação já usado em todas as manutenções
  anteriores documentadas no CLAUDE.md do projeto).

CA-09 — WeasyPrint (usado na exportação LGPD da Manutenção #66) e
  pikepdf continuam funcionais na imagem rebuildada — reexecutar ao menos
  um teste real que gere PDF (ex: exportar/ de ClienteViewSet) e confirmar
  que não houve regressão por causa do upgrade de Django/DRF.

CA-10 — Nenhuma tela do frontend quebra por mudança de contrato de API —
  como não há mudança de serializer/endpoint nesta manutenção, basta
  confirmar que o frontend já em produção continua consumindo a API sem
  erro novo (smoke test básico: health check HTTP 200 na raiz + alguns
  endpoints autenticados retornando o formato de resposta esperado,
  paginação `response.data.results` inclusa).
```

---

## 10. Observações Finais do Analista

- Esta é uma manutenção de **infraestrutura/segurança**, sem impacto
  visível ao usuário final — não há tela nova, não há endpoint novo, não
  há RF de negócio. O valor é manter o sistema dentro do período de
  correções de segurança do framework.
- `requer_aprovacao_comercial: false` — é manutenção técnica interna, não
  expansão de escopo contratual.
- Pipeline a seguir: **Forge** (único agente de código necessário — não
  há trabalho de Loom/Brush nesta manutenção, é 100% backend/infra) →
  **Sentinel** (critérios de aceite acima) → **Pilot** (deploy via CI/CD
  já existente, sem alteração no `.github/workflows/deploy.yml` nem no
  `Dockerfile`).
- Recomendação para ciclo futuro (fora do escopo desta manutenção):
  converter `unique_together` (Categoria, ConversaoUnidade) para
  `UniqueConstraint` explícita, eliminando o DeprecationWarning antes da
  próxima major do Django.
