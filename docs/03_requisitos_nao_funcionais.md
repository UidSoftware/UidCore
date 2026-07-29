# 03 — Requisitos Nao Funcionais
**Sistema:** UidCore — Template Financeiro Multi-Nicho
**Versao:** 1.0 (baseline AS-IS em producao)
**Data:** 2026-07-28
**Referencia:** Levantamento_Requisitos.md / ArquiteturaTecnica#2

---

## Seguranca e Autenticacao

| ID | Requisito |
|---|---|
| RNF01 | Autenticacao via SimpleJWT. Access token com validade de 1 hora. Refresh token com validade de 7 dias e rotacao ativada. |
| RNF02 | Autorizacao por perfil: is_staff=True equivale a ADMIN; usuario autenticado sem is_staff = OPERACIONAL. |
| RNF07 | CORS configuravel via env (CORS_ALLOW_ALL_ORIGINS; default True em dev, False em producao). |

---

## Integridade de Dados

| ID | Requisito |
|---|---|
| RNF03 | Soft delete obrigatorio em todos os models que herdam BaseModel. Proibido chamar .delete() diretamente. |
| RNF04 | Valores monetarios: SEMPRE DecimalField(max_digits=12, decimal_places=2). NUNCA Float ou int para dinheiro. |
| RNF05 | Timestamps created_at e updated_at presentes em todos os models que herdam BaseModel. Gerados automaticamente. |
| RNF08 | Banco de dados: PostgreSQL 16. Advisory lock por conta_id obrigatorio em operacoes de saldo (pg_advisory_xact_lock). |

---

## Performance e Concorrencia

| ID | Requisito |
|---|---|
| RNF06 | Paginacao padrao: StandardPagination com PAGE_SIZE=20. Frontend usa response.data.results para listagens. |
| RNF16 | Race condition em operacoes financeiras prevenida via pg_advisory_xact_lock por conta_id antes de qualquer operacao de saldo. |

---

## Internacionalizacao

| ID | Requisito |
|---|---|
| RNF09 | Idioma: pt-BR. Timezone: America/Sao_Paulo. Configurado em settings.py. |

---

## Frontend

| ID | Requisito |
|---|---|
| RNF10 | Framework: React 18 + Vite + Tailwind CSS. Fontes obrigatorias: Plus Jakarta Sans e DM Sans. NUNCA Inter, Roboto ou Arial. |
| RNF11 | Estado global: Zustand com persistencia em localStorage. |
| RNF12 | HTTP client: Axios com interceptor de refresh automatico. Em 401: dispara POST /api/v1/auth/token/refresh/ e retenta a requisicao original. Em falha do refresh: logout + redirect para /login. |

---

## Infraestrutura e Deploy

| ID | Requisito |
|---|---|
| RNF13 | CI/CD via GitHub Actions. NUNCA deploy manual via SSH. |
| RNF14 | Container: Docker Compose + Gunicorn (3 workers) + Nginx. |

---

## Restricoes Tecnicas de Backend

| ID | Requisito |
|---|---|
| RNF15 | Migrations sempre por app (python manage.py makemigrations <app>). NUNCA makemigrations global. |

---

## Restricoes de Nomenclatura e Codigo

As restricoes abaixo sao mandatorias para todos os derivados do UidCore:

- App chamado 'os' e proibido — usar 'ordens' com URL /api/os/
- LivroCaixa e imutavel — ReadCreateViewSet (sem PUT/PATCH/DELETE)
- Signals de LivroCaixa devem usar transaction.atomic()
- Serializers devem sempre incluir: id = serializers.IntegerField(source='pk', read_only=True)
- Frontend: SEMPRE response.data.results em listagens paginadas, NUNCA response.data direto
- CPF e CNPJ armazenados como String sem mascara (preserva zeros a esquerda)
- ENUMs implementados via choices do Django
- Credenciais SEMPRE em variaveis de ambiente, NUNCA em codigo ou commit

---

## Disponibilidade e Monitoramento

| Aspecto | Padrao |
|---|---|
| Deploy | Docker Compose em VPS Ubuntu 24.04 (IP: 209.50.241.122) |
| Porta | 8006 |
| Dominio | uidcore.uidsoftware.com.br |
| SSL | Let's Encrypt via nginx-proxy |
| Dependencia externa critica | poppler-utils (pdftotext) no container — obrigatorio para conciliacao bancaria |
