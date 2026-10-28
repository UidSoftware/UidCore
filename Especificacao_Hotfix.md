# Especificação Hotfix — Manutenção #71

**Sistema:** UidCore (OS #7)
**Título:** Mídia persistente e servida + armazenamento configurável (pré-requisito da foto de perfil)
**Analista:** Modo Manutenção
**Data:** 2026-10-28

---

## 1. Contexto (AS-IS)

Levantamento confirmado por leitura direta dos arquivos do projeto antes de
escrever esta especificação:

1. **`docker-compose.prod.yml`** — o serviço `backend` monta só
   `static_volume:/app/staticfiles`. Não existe volume para `/app/media`.
   Qualquer arquivo recebido via `FileField`/`ImageField` fica gravado na
   camada gravável (writable layer) do container e **é perdido no próximo
   `docker compose ... up -d --remove-orphans backend`** do
   `.github/workflows/deploy.yml` (recria o container a cada deploy).
2. **`nginx/nginx.conf`** — tem `location /static/` (alias pro volume
   `static_volume`), mas **não existe `location /media/`**. Uma requisição
   pra `https://uidcore.uidsoftware.com.br/media/docs/contrato.pdf` cai no
   `location /` genérico (`try_files $uri $uri/ /index.html`), que devolve o
   `index.html` do React com `200 text/html` — silenciosamente errado, sem
   4xx/5xx que alertasse alguém.
3. **`backend/media/`** — contém hoje 282 arquivos em `docs/` e 56 em
   `comprovantes/`, todos de ~13 bytes, confirmados como resíduo de teste
   (`SimpleUploadedFile('doc.pdf', b'fake')` em
   `backend/administrativo/tests.py`, `backend/pagamentos/tests.py`,
   `backend/financeiro/tests.py` — nenhum desses testes usa
   `override_settings(MEDIA_ROOT=...)` ou diretório temporário; gravam
   direto no `MEDIA_ROOT` real definido em `settings.py`). Não existe
   `.dockerignore` no projeto — `backend/media/` entra no contexto de build
   do `docker build ./backend` e é copiado pra dentro da imagem.
4. **`backend/requirements.txt`** — sem `Pillow` (obrigatório pro Django
   aceitar `ImageField`, que a próxima manutenção — foto de perfil — vai
   usar) e sem `django-storages`.
5. **`backend/core/settings.py`** — `MEDIA_URL = '/media/'` e
   `MEDIA_ROOT = BASE_DIR / 'media'` fixos, sem nenhuma variável de
   ambiente controlando backend de armazenamento. Models com `FileField`
   já existentes e confirmados: `financeiro.Despesa.comprovante`
   (`upload_to='despesas/'`), `pagamentos.Cobranca.comprovante`
   (`upload_to='comprovantes/'`), `administrativo.Documento.arquivo`
   (`upload_to='docs/'`).
6. **`.gitignore`** — já ignora `media/` (correto, nada a mudar aqui).

**Conclusão do diagnóstico:** o sistema nunca teve persistência real de
mídia em produção. Qualquer comprovante de pagamento/despesa ou documento
administrativo enviado por um cliente real desde o lançamento do UidCore
pode já ter sido perdido em deploys anteriores (não há como auditar
retroativamente — o volume nunca existiu).

---

## 2. Requisitos Funcionais (RF)

```
RF-01 — O backend deve persistir qualquer arquivo gravado via FileField/
        ImageField num volume Docker nomeado (media_volume), sobrevivendo
        à recriação do container backend em qualquer deploy.

RF-02 — O nginx do projeto deve servir arquivos de /media/ lendo do mesmo
        volume media_volume, montado SOMENTE LEITURA no serviço nginx.
        GET /media/docs/<arquivo real> deve devolver o arquivo com
        Content-Type correto (nunca o index.html do React).

RF-03 — Antes do primeiro deploy que introduz o volume, o conteúdo
        atualmente existente em /app/media dentro do container backend
        de PRODUÇÃO deve ser copiado para o volume novo via `docker cp`,
        para não perder nenhum comprovante/documento já enviado por
        cliente real (distinto dos arquivos de teste — ver RF-06).

RF-04 — O armazenamento de mídia deve ser escolhido por variável de
        ambiente STORAGE_BACKEND, sem exigir mudança de código para
        trocar:
          - STORAGE_BACKEND=local (padrão) → disco da VPS via volume
            media_volume (RF-01).
          - STORAGE_BACKEND=s3 → qualquer serviço compatível com a API
            S3 (Cloudflare R2, Backblaze B2, Wasabi, AWS S3 real),
            configurado via django-storages + STORAGES (Django 5.2,
            já na versão correta desde a Manutenção #69).

RF-05 — Quando STORAGE_BACKEND=s3, o bucket usado para mídia é PRIVADO
        por padrão (comprovantes são documento financeiro/administrativo
        do cliente final, nunca públicos). O backend deve servir a URL
        do arquivo como URL assinada (pre-signed, com expiração), nunca
        uma URL pública direta do bucket.

RF-06 — Os testes automatizados (backend/administrativo/tests.py,
        backend/pagamentos/tests.py, backend/financeiro/tests.py — e
        qualquer teste futuro que grave FileField/ImageField) devem
        gravar em MEDIA_ROOT temporário (override_settings + tempfile ou
        TestCase equivalente), nunca no MEDIA_ROOT real do projeto.

RF-07 — backend/media/ deve ser esvaziado dos 338 arquivos de teste
        (282 em docs/ + 56 em comprovantes/, todos resíduo confirmado de
        execução de teste sem isolamento de MEDIA_ROOT) e passar a ficar
        de fora tanto do contexto de build Docker (.dockerignore) quanto
        do controle de versão (.gitignore já cobre — confirmar que
        continua cobrindo após qualquer ajuste).

RF-08 — Pillow e django-storages[s3] devem ser adicionados a
        backend/requirements.txt, pinados em versão compatível com
        Django 5.2.18 (já instalado desde a Manutenção #69).
```

## 3. Requisitos Não Funcionais (RN)

```
RN-01 — Migração local→bucket deve estar documentada no CLAUDE.md do
        projeto (/var/www/uidcore/CLAUDE.md) como procedimento operacional
        reaproveitável: comando que copia os arquivos existentes do
        volume media_volume local para o bucket S3-compatível configurado,
        a ser executado quando o disco da VPS apertar (motivo: a VPS é
        compartilhada por vários sistemas da fábrica — SystemD, ContratID,
        UidCore, LifeStyle e futuros forks).

RN-02 — A troca de STORAGE_BACKEND=local para STORAGE_BACKEND=s3 deve ser
        possível só com mudança de .env.prod (+ as 5 variáveis de
        configuração do bucket) e recriação do container — nunca exigindo
        alteração de código/settings.py depois desta manutenção.

RN-03 — nginx -t (teste de sintaxe) deve passar antes de qualquer reload
        do nginx do projeto — nunca aplicar um nginx.conf não testado
        (mesma disciplina já documentada no CLAUDE.md global para o
        nginx-proxy compartilhado, aplicada aqui ao nginx do próprio
        projeto).

RN-04 — O volume media_volume montado no serviço nginx deve ser
        explicitamente :ro (read-only) — nginx nunca deve ter permissão
        de escrita em mídia, só o backend grava.

RN-05 — Nenhum teste deve depender da ordem de execução nem deixar
        arquivo residual em disco após rodar (isolamento completo via
        MEDIA_ROOT temporário por teste/suite, limpo automaticamente).

RN-06 — Zero regressão: os 533 testes Django já existentes (confirmados
        passando na Manutenção #69) devem continuar passando após esta
        mudança — a alteração de MEDIA_ROOT nos testes é de infraestrutura
        de teste, não de comportamento de negócio.
```

## 4. Especificação Backend

### 4.1 `backend/requirements.txt`
Adicionar (mantendo o restante intacto):
```
Pillow>=10.0,<11.0
django-storages[s3]>=1.14,<1.15
```

### 4.2 `backend/core/settings.py`
Substituir o bloco fixo de `MEDIA_URL`/`MEDIA_ROOT` por configuração
condicional via `STORAGE_BACKEND`:

```python
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

STORAGE_BACKEND = config('STORAGE_BACKEND', default='local')  # 'local' | 's3'

if STORAGE_BACKEND == 's3':
    AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID', default='')
    AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY', default='')
    AWS_STORAGE_BUCKET_NAME = config('AWS_STORAGE_BUCKET_NAME', default='')
    AWS_S3_ENDPOINT_URL = config('AWS_S3_ENDPOINT_URL', default='')
    AWS_S3_REGION_NAME = config('AWS_S3_REGION_NAME', default='auto')
    AWS_S3_FILE_OVERWRITE = False
    AWS_DEFAULT_ACL = None
    AWS_QUERYSTRING_AUTH = True  # URL assinada (RF-05) — bucket privado
    AWS_QUERYSTRING_EXPIRE = 3600  # 1h — ajustar conforme caso de uso real
    AWS_LOCATION = config('AWS_MEDIA_PREFIX', default='uidcore/media')  # prefixo por projeto (RF-04)

    STORAGES = {
        'default': {
            'BACKEND': 'storages.backends.s3.S3Storage',
        },
        'staticfiles': {
            'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
        },
    }
else:
    STORAGES = {
        'default': {
            'BACKEND': 'django.core.files.storage.FileSystemStorage',
        },
        'staticfiles': {
            'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
        },
    }
```

Nota para o Forge: `STORAGES` é a API nativa do Django 4.2+/5.x (já na
versão correta) — não usar `DEFAULT_FILE_STORAGE` (settei legado,
removido/deprecated). Confirmar compatibilidade exata de
`django-storages` com `STORAGES` dict na versão pinada.

### 4.3 `.env.prod` (variáveis novas — não commitar valores reais)
```
STORAGE_BACKEND=local

# Só usadas quando STORAGE_BACKEND=s3:
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_STORAGE_BUCKET_NAME=
AWS_S3_ENDPOINT_URL=
AWS_S3_REGION_NAME=auto
AWS_MEDIA_PREFIX=uidcore/media
```
Forge/Pilot: seguir o padrão já documentado no CLAUDE.md global de nunca
reescrever `.env.prod` com `sed -i`/redirecionamento se for symlink —
`ls -la .env.prod` antes de editar.

### 4.4 Testes (RF-06 / RN-05)
Em `backend/administrativo/tests.py`, `backend/pagamentos/tests.py`,
`backend/financeiro/tests.py` (e qualquer teste novo com FileField):

```python
import shutil
import tempfile
from django.test import override_settings

_MEDIA_ROOT_TESTE = tempfile.mkdtemp()

@override_settings(MEDIA_ROOT=_MEDIA_ROOT_TESTE)
class ...TestCase(TestCase):
    ...
```
ou usar `setUpClass`/`tearDownClass` com `tempfile.mkdtemp()` +
`shutil.rmtree(..., ignore_errors=True)` por classe de teste, conforme o
padrão que já existir de uso mais comum no projeto — decisão de
implementação do Forge, desde que cumpra RF-06/RN-05 (nunca grava no
`MEDIA_ROOT` real, nunca deixa resíduo).

### 4.5 Limpeza (RF-07)
```
rm -rf backend/media/docs/* backend/media/comprovantes/*
```
(ou remover `backend/media/` por completo — ele é recriado sozinho no
primeiro upload real; confirmar antes que nenhum arquivo ali seja de
cliente real — diagnóstico desta especificação já confirmou que são 338
arquivos de 13 bytes, 100% resíduo de teste).

### 4.6 `.dockerignore` (novo arquivo)
O build do serviço `backend` é `build: ./backend` em
`docker-compose.prod.yml` — contexto de build é `./backend`, então o
arquivo correto é **`backend/.dockerignore`**, com `media/` relativo à
raiz desse contexto (não `backend/media/`):
```
media/
__pycache__/
*.pyc
.env
.env.prod
```

---

## 5. Especificação Infraestrutura

### 5.1 `docker-compose.prod.yml`
```yaml
services:
  backend:
    build: ./backend
    command: gunicorn core.wsgi:application --bind 0.0.0.0:8000 --workers 3
    volumes:
      - static_volume:/app/staticfiles
      - media_volume:/app/media
    env_file:
      - .env.prod
    depends_on:
      db:
        condition: service_healthy
    restart: always

  nginx:
    image: nginx:alpine
    ports:
      - "127.0.0.1:8006:80"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/conf.d/default.conf
      - static_volume:/static
      - media_volume:/media:ro
      - frontend_build:/usr/share/nginx/html
    depends_on:
      - backend
    restart: always

volumes:
  pgdata:
  static_volume:
  media_volume:
  frontend_build:
```
(diff mínimo sobre o arquivo atual: adicionar `media_volume:/app/media` no
`backend`, adicionar `media_volume:/media:ro` no `nginx`, declarar
`media_volume:` na seção `volumes:` top-level.)

### 5.2 `nginx/nginx.conf`
Adicionar, junto do `location /static/` existente:
```nginx
    location /media/ {
        alias /media/;
    }
```
(mesmo padrão já usado para `/static/` — `alias`, não `root`, porque o
path físico dentro do volume não replica o prefixo da URL.)

### 5.3 Migração do volume — passo obrigatório ANTES do deploy desta manutenção (RF-03)
A ser executado pelo Pilot, na VPS, antes de `docker compose up -d` recriar
o `backend` com o volume novo:
```bash
# 1. Conferir o que existe hoje no container backend em produção
docker exec uidcore-backend-1 ls -la /app/media

# 2. Criar o volume nomeado (se docker compose up ainda não tiver criado)
docker volume create uidcore_media_volume

# 3. Copiar o conteúdo real do container pro volume, via container auxiliar
docker run --rm \
  -v uidcore_media_volume:/dest \
  --volumes-from uidcore-backend-1 \
  alpine sh -c "cp -a /app/media/. /dest/ 2>/dev/null; ls -la /dest"

# 4. Só depois disso: docker compose -f docker-compose.prod.yml up -d --remove-orphans backend nginx
```
Nomeação exata do volume (`uidcore_media_volume` vs. outro nome) depende
do nome do projeto Compose resolvido na VPS — Pilot deve confirmar com
`docker volume ls` antes de assumir o nome.

⚠️ Esse passo é sobre dado de PRODUÇÃO real (possível comprovante de
cliente) — seguir a mesma cautela documentada no CLAUDE.md global pra
qualquer ação em estado compartilhado sem staging: confirmar o conteúdo
antes e depois da cópia (contagem de arquivos, alguns nomes), nunca supor
que deu certo sem checar.

### 5.4 `.github/workflows/deploy.yml`
Nenhuma mudança necessária — o volume nomeado sobrevive a
`docker compose ... up -d --remove-orphans backend nginx` por design
(volumes nomeados não são recriados por `up`, só containers). Confirmar
isso no Sentinel (recriar o container backend via `--force-recreate` e
validar que um arquivo gravado antes continua acessível depois).

---

## 6. Especificação de Testes (critérios de aceite para o Sentinel)

```
CA-01 — docker compose config não gera erro de sintaxe após a mudança no
        docker-compose.prod.yml; volumes media_volume aparecem na seção
        volumes: e nos dois serviços (backend rw, nginx ro).

CA-02 — nginx -t passa com o nginx.conf atualizado (RN-03).

CA-03 — Em ambiente de teste isolado (containers próprios, nunca os de
        produção — mesma disciplina já usada pelo Sentinel em manutenções
        anteriores: porta/projeto Compose diferentes), gravar um arquivo
        real via endpoint autenticado que usa FileField/ImageField
        (ex.: POST em administrativo/documentos/ com arquivo multipart),
        depois GET https://<host-teste>/media/docs/<nome-gerado> deve
        devolver o arquivo com Content-Type correto — nunca
        text/html nem 404.

CA-04 — Recriar o container backend do ambiente de teste
        (docker compose up -d --force-recreate backend) e repetir o GET
        do CA-03 — o arquivo deve continuar acessível (prova de que o
        volume persiste através da recriação do container, não só que o
        nginx serve um arquivo que ainda está lá por acaso).

CA-05 — STORAGE_BACKEND=local (padrão, sem a variável setada) grava em
        disco via FileSystemStorage — comportamento idêntico ao de hoje
        para quem não configurar nada.

CA-06 — STORAGE_BACKEND=s3 com credenciais de teste (bucket real de teste
        num provedor S3-compatível, ou mock/moto se disponível) grava no
        bucket e a URL retornada pela API é assinada (contém parâmetros
        de assinatura/expiração), nunca uma URL pública direta.

CA-07 — pip show Pillow e pip show django-storages confirmam instalação
        na versão pinada, dentro do container/ambiente de teste.

CA-08 — makemigrations --check --dry-run: 0 pendências (esta manutenção
        não deve gerar nenhuma migration — não há mudança de model, só de
        storage backend).

CA-09 — Suite completa de testes Django (533 esperados, conforme baseline
        da Manutenção #69) passa com 0 falhas, e ao final da execução
        backend/media/ (ou o MEDIA_ROOT real do projeto) não ganhou
        nenhum arquivo novo — prova de que RF-06/RN-05 realmente isolaram
        os testes do MEDIA_ROOT de produção.

CA-10 — Confirmar 0 arquivos residuais de teste em backend/media/docs e
        backend/media/comprovantes após a limpeza do RF-07, e que
        backend/.dockerignore existe e contém a entrada de media/.

CA-11 (produção, pós-deploy) — Pilot confirma: arquivo pré-existente
        migrado pelo RF-03 continua acessível via /media/ após o deploy
        real; um novo upload real feito após o deploy sobrevive a um
        segundo deploy subsequente (ou pelo menos a um
        --force-recreate manual de verificação).
```

---

## 7. Fora do Escopo (W — Won't, nesta manutenção)

```
- Implementação da foto de perfil em si (ImageField em accounts.User ou
  equivalente) — esta manutenção é só o pré-requisito de infraestrutura;
  a tela/endpoint de foto de perfil é a PRÓXIMA manutenção, já anunciada
  no pedido.
- Migração retroativa de dado real perdido em deploys anteriores a esta
  manutenção — não há como recuperar (nunca houve volume), só proteger
  dali em diante.
- Criação de bucket S3-compatível de produção (Cloudflare R2/B2/Wasabi) —
  esta manutenção entrega a configuração (STORAGE_BACKEND=s3 funcional),
  não a decisão comercial de qual provedor usar nem a criação da conta/
  bucket real — isso é decisão do Luiz Eduardo quando o disco da VPS
  justificar a troca (RN-01).
- CDN/cache de mídia pública — fora de escopo, mídia aqui é privada por
  natureza (comprovantes).
```

---

## 8. Observação para o CLAUDE.md do projeto (Pilot, pós-deploy)

Ao concluir esta manutenção, documentar no `CLAUDE.md` do UidCore, além
do registro padrão de execução:
1. O procedimento de migração local→bucket (comando real usado, não só a
   intenção) — RN-01.
2. O nome exato do volume Docker (`docker volume ls` confirmado) para
   referência de qualquer operação manual futura.
3. Alertar explicitamente: qualquer novo `FileField`/`ImageField`
   adicionado em manutenção futura (ex.: foto de perfil) já herda
   persistência e storage configurável automaticamente — não precisa
   repetir este trabalho de infra, só adicionar o campo no model.

---

**ANALISTA CONCLUIDO**
