# 06 — Arquitetura do Sistema
**Sistema:** UidCore — Template Financeiro Multi-Nicho
**Versao:** 1.0 (baseline AS-IS em producao)
**Data:** 2026-07-28
**Referencia:** Levantamento_Requisitos.md / ArquiteturaTecnica#2

---

## Stack Completa

### Backend

| Componente | Versao / Detalhe |
|---|---|
| Linguagem | Python 3.12 |
| Framework | Django 5.x |
| API | Django REST Framework (DRF) |
| Autenticacao | SimpleJWT |
| ORM | Django ORM |
| Banco | PostgreSQL 16 |
| WSGI | Gunicorn (3 workers) |
| Processamento PDF | pdftotext (poppler-utils) |
| Lock de concorrencia | pg_advisory_xact_lock por conta_id |

### Frontend

| Componente | Versao / Detalhe |
|---|---|
| Framework | React 18 |
| Build | Vite |
| Estilo | Tailwind CSS |
| Estado global | Zustand com persistencia em localStorage |
| HTTP client | Axios com interceptor de refresh automatico |
| Queries | TanStack Query |
| Fontes | Plus Jakarta Sans + DM Sans |

### Infraestrutura

| Componente | Detalhe |
|---|---|
| Container | Docker Compose |
| Proxy reverso | Nginx |
| SSL | Let's Encrypt via nginx-proxy |
| VPS | Ubuntu 24.04 — IP 209.50.241.122 |
| Porta | 8006 |
| Dominio | uidcore.uidsoftware.com.br |
| CI/CD | GitHub Actions |

---

## Estrutura de Apps Django

```
common/          BaseModel, PessoaBase
accounts/        CustomUser, autenticacao JWT
clientes/        Cliente, HistoricoCliente
fornecedores/    Fornecedor
financeiro/      Conta, Aporte, Categoria, Receita, Despesa, LivroCaixa,
                 ConciliacaoExtrato, ItemConciliacao, PadraoSeguroConciliacao,
                 relatorios.py (DRE, Balanco, FluxoProjetado, Indicadores),
                 parsers/ (c6.py, btg.py, stubs)
vendas/          Orcamento, Pedido, ItemPedido
pagamentos/      MetodoPagamento, Cobranca, Parcela
administrativo/  TipoDocumento, Documento
rh/              Cargo, Funcionario, FolhaPagamento, RegistroFerias
agendamento/     Agenda, Compromisso
portal/          AcessoPortalCliente
conciliacao/     PASTA NO DISCO - ignorada (DIV01: models migraram para financeiro/)
```

---

## Fluxo de Autenticacao JWT

1. POST /api/v1/auth/token/ com email+senha
2. Frontend armazena access e refresh no Zustand (localStorage)
3. Todas as requisicoes: Authorization: Bearer {access_token}
4. Em 401: interceptor Axios dispara POST /api/v1/auth/token/refresh/
   - Sucesso: novo access_token, retry da requisicao original
   - Falha: logout, limpar Zustand, redirect para /login
5. Refresh token: 7 dias com rotacao ativada

---

## Arquitetura de Dominio

```
uidcore.uidsoftware.com.br/           Frontend React
uidcore.uidsoftware.com.br/api/v1/    Backend DRF
uidcore.uidsoftware.com.br/admin/     Django Admin
```

---

## Padrao de Paginacao

PAGE_SIZE=20. Formato de resposta:

```json
{
  "count": 100,
  "next": "...?page=2",
  "previous": null,
  "results": []
}
```

Frontend: SEMPRE response.data.results. NUNCA response.data direto.

---

## Padrao de Serializers

```python
class MeuSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='pk', read_only=True)
    class Meta:
        fields = ['id', ...]
```

---

## Permissoes

| Permissao | Condicao |
|---|---|
| IsAdmin | is_staff == True |
| IsAuthenticated | usuario autenticado |

Endpoints publicos: /api/v1/auth/token/, /api/v1/auth/token/refresh/, /api/v1/accounts/register/

---

## Configuracoes Criticas

```python
AUTH_USER_MODEL = 'accounts.CustomUser'
LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
ACCESS_TOKEN_LIFETIME = timedelta(hours=1)
REFRESH_TOKEN_LIFETIME = timedelta(days=7)
ROTATE_REFRESH_TOKENS = True
CORS_ALLOW_ALL_ORIGINS = True  # dev; False em prod
```

---

## CI/CD

Fluxo: push main -> GitHub Actions -> testes -> build Docker -> deploy.
NUNCA deploy manual via SSH.

---

## Divergencias Conhecidas

| ID | Descricao | Impacto |
|---|---|---|
| DIV01 | App conciliacao removido; models em financeiro/. Pasta no disco ignorada. | Baixo |
| DIV02 | Dashboard.jsx com placeholders; endpoint funciona, frontend nao consome. | Medio |
| DIV03 | Portal do cliente sem telas para o perfil CLIENTE. | Medio |
| DIV04 | AcessoPortalCliente, Agenda, PadraoSeguroConciliacao: campo ativo proprio em vez de is_active. | Baixo |
| DIV05 | MetodoPagamento: dois booleanos (ativo proprio + is_active herdado). | Baixo |
| DIV06 | Financeiro.jsx: 9 abas no componente principal. | Baixo |
