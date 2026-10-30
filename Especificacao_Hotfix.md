# Especificação Hotfix — Manutenção #87

**Sistema:** UidCore (OS #7)
**Tipo:** `feature_pequena` (configuração/infra de template — sem tela nova, sem endpoint de negócio novo)
**Requer aprovação comercial:** não
**Caminho afetado:** `frontend/index.html`, `frontend/vite.config.js`, `frontend/src/utils/appConfig.js` (novo), `frontend/.env`/`.env.example`, 7 arquivos `.jsx`; `backend/core/settings.py`, `backend/accounts/services.py`, `backend/accounts/admin.py`, `backend/.env.example`

---

## 1. Contexto

O UidCore é o sistema-template (núcleo/backbone) da Uid Software, replicado
via fork para cada cliente/nicho (pilates, salão, loja, clínica etc. — ver
`CLAUDE.md`, seção "Fluxo 1"). Hoje o nome do produto está escrito à mão
("UidCore") em pelo menos 13 pontos do código (7 arquivos de frontend + 2
pontos de backend), porque o template nunca teve esse nome parametrizado
desde a criação. Cada novo fork precisaria de um `sed`/find-replace manual
e arriscado para rebatizar o sistema para o cliente, em vez de trocar uma
única variável de ambiente.

## 2. AS-IS (como é hoje)

Confirmado via leitura direta dos arquivos (`grep -rn "UidCore" frontend/src
frontend/index.html backend/accounts/services.py`):

| Arquivo | Linha(s) | Conteúdo hardcoded |
|---|---|---|
| `frontend/index.html` | 13, 14 | `<meta name="description" content="UidCore — Template Financeiro Multi-Nicho">` e `<title>UidCore</title>` |
| `frontend/src/components/layout/Sidebar.jsx` | 47 | `<span ...>UidCore</span>` (logo expandida da sidebar) |
| `frontend/src/components/layout/Header.jsx` | 127 | `<span ...>UidCore</span>` (nome no header desktop) |
| `frontend/src/pages/Login.jsx` | 42, 83 | título da tela de login + rodapé `UidCore &copy; {ano} — Uid Software` |
| `frontend/src/pages/DefinirSenha.jsx` | 63, 106 | título da tela + rodapé `UidCore &copy; {ano} — Uid Software` |
| `frontend/src/pages/Dashboard.jsx` | 40, 56, 101 | `Bem-vindo ao UidCore, {firstName}!` (3 variantes de saudação/estado) |
| `frontend/src/pages/AgendamentoPublico.jsx` | 513 | `Powered by UidCore` (rodapé da página pública de agendamento, Manutenção #65) |
| `backend/accounts/services.py` | 27, 42 | `<h2>UidCore</h2>` no corpo HTML do email de primeiro acesso + assunto `'Acesso ao UidCore — defina sua senha'` |

⚠️ **Nota de rota (mesmo padrão já documentado nas Manutenções #44/#72):** o
pedido citou "Sidebar.jsx linha 47 **e 127**". A linha 47 do Sidebar.jsx
está correta (confirmado). A linha 127 com texto `UidCore` pertence, na
verdade, a **`Header.jsx`** (`<span className="hidden md:block ...">UidCore</span>`)
— `Sidebar.jsx` tem só 86 linhas no total e uma única ocorrência do texto
("UidCore"). Tratado nesta especificação como os dois pontos reais
(Sidebar.jsx:47 e Header.jsx:127), não como duas ocorrências em Sidebar.jsx.

Django admin (`backend/accounts/admin.py`, `backend/core/urls.py`) não tem
`site_header`/`site_title` customizado hoje — usa o default do Django
("Django administration").

Não existe `frontend/.env` nem variável `VITE_APP_NAME` hoje — só
`frontend/.env.example` com `VITE_API_URL=/api/v1`. `backend/core/settings.py`
não tem `APP_NAME`. Todas as outras configurações do projeto (DB, SMTP,
STORAGE_BACKEND, CORS) já seguem o padrão `config('VAR', default=...)` via
`python-decouple` (backend) — nenhum precedente de variável de ambiente
exposta ao Vite via `import.meta.env` ainda existe no frontend.

## 3. TO-BE (como será)

Nome e descrição do sistema passam a ser configuráveis por variável de
ambiente, com fallback para `UidCore`/a descrição atual quando a variável
não estiver definida — nenhum comportamento muda para o UidCore em produção
hoje (continua aparecendo "UidCore" em todo lugar, só que agora vindo de
config, não mais de string literal). Isso é o que destrava o próximo fork
do template (ex.: LifeStyle, ou um cliente futuro) a só setar uma variável
no `.env`/`.env.prod` em vez de caçar 13 ocorrências em 10 arquivos.

### Frontend

- `frontend/src/utils/appConfig.js` (**novo arquivo**): único ponto de
  leitura de `import.meta.env.VITE_APP_NAME` e `import.meta.env.VITE_APP_DESCRIPTION`,
  exportando `APP_NAME` e `APP_DESCRIPTION` com fallback `'UidCore'` e
  `'UidCore — Template Financeiro Multi-Nicho'` respectivamente.
- Todos os 7 arquivos `.jsx` listados no AS-IS passam a importar `APP_NAME`
  de `../utils/appConfig.js` (ajustar o caminho relativo conforme a pasta
  de cada arquivo) em vez de ter a string `'UidCore'` escrita à mão.
  `AgendamentoPublico.jsx` (`Powered by UidCore`) também usa `APP_NAME`.
- `frontend/vite.config.js` ganha `transformIndexHtml` (hook do plugin,
  dentro de `defineConfig`) que lê `process.env.VITE_APP_NAME` /
  `process.env.VITE_APP_DESCRIPTION` (com os mesmos fallbacks) e substitui
  o conteúdo de `<title>` e da `<meta name="description">` no
  `frontend/index.html` em build/dev — **sem precisar de template
  `%VITE_APP_NAME%` manual no HTML**, já que o `index.html` atual continua
  com `UidCore` literal como fallback visível em `view-source` antes do JS
  rodar (comportamento aceitável: é só o flash inicial do `<title>` estático,
  o mesmo padrão que o app já tem com o anti-FOUC do tema escuro).
- `frontend/.env.example` (**atualizado**): documentar
  `VITE_APP_NAME=UidCore` e `VITE_APP_DESCRIPTION=UidCore — Template Financeiro Multi-Nicho`
  comentados/com exemplo, junto da `VITE_API_URL` já existente.
- `frontend/.env` (se existir na VPS/dev local, **não versionado** — ver
  regra global ".env sempre no .gitignore") não é tocado pelo Forge/Loom;
  cabe ao Pilot confirmar/criar conforme padrão de outras variáveis.

### Backend

- `backend/core/settings.py`: nova linha
  `APP_NAME = config('APP_NAME', default='UidCore')`, no mesmo bloco de
  outras configs simples (próximo a `FRONTEND_URL`, linha ~191).
- `backend/accounts/services.py`: `enviar_primeiro_acesso()` passa a usar
  `settings.APP_NAME` em vez de `'UidCore'` literal — tanto no `<h2>` do
  corpo HTML (linha 27) quanto no assunto do email (linha 42,
  `f'Acesso ao {settings.APP_NAME} — defina sua senha'`). Precisa de
  `from django.conf import settings` — já importado no arquivo.
- Django admin: `admin.site.site_header` e `admin.site.site_title`
  configurados com `settings.APP_NAME`. Local recomendado: `backend/core/urls.py`
  (onde `admin.site.urls` já é importado/registrado, logo após o import de
  `admin`) ou `backend/accounts/admin.py` (onde `UserAdmin` já vive) — Forge
  decide o local mais natural sem duplicar a configuração nos dois lugares.
- `backend/.env.example` (**atualizado**): adicionar `APP_NAME=UidCore`
  junto das demais variáveis já documentadas.

### Fora do escopo desta manutenção (confirmado pelo pedido)

- `manifest.json`/PWA: não existe ainda, não criar agora.
- Comentários e docstrings que mencionam "UidCore" (ex.:
  `backend/accounts/services.py:17`, `frontend/src/hooks/useTheme.js:10`)
  **não são alterados** — são documentação de código, não texto exibido ao
  usuário.
- Nome de banco de dados (`DB_NAME=uidcore`), domínio
  (`uidcore.uidsoftware.com.br`), nome do repositório/projeto
  (`/var/www/uidcore`), chaves de `localStorage` (`uidcore-theme`) e
  qualquer identificador técnico/infra — fora de escopo; o pedido é só
  sobre texto exibido ao usuário final (UI + email).

## 4. Requisitos Funcionais

```
RF-01 - O sistema deve exibir o nome do produto (título da aba, sidebar,
        header, telas de Login/DefinirSenha, saudação do Dashboard, rodapé
        da página pública de agendamento e emails de acesso) a partir de
        uma única fonte de configuração, nunca de string hardcoded
        duplicada em múltiplos arquivos.
RF-02 - Com VITE_APP_NAME e APP_NAME ausentes do .env (ou .env vazio), o
        sistema deve continuar exibindo "UidCore" em todos os pontos
        listados no AS-IS — fallback idêntico ao comportamento atual.
RF-03 - Alterar VITE_APP_NAME=OutroNome no frontend deve refletir em TODOS
        os 8 pontos de UI listados (index.html title/description, Sidebar,
        Header, Login, DefinirSenha, Dashboard x3, AgendamentoPublico) após
        rebuild do frontend, sem precisar editar nenhum .jsx.
RF-04 - Alterar APP_NAME=OutroNome no backend deve refletir no corpo HTML e
        assunto do email de primeiro acesso (accounts/services.py) e no
        cabeçalho do Django admin (site_header/site_title), sem precisar
        editar services.py nem admin.py.
RF-05 - frontend/.env.example e backend/.env.example devem documentar as
        novas variáveis (VITE_APP_NAME, VITE_APP_DESCRIPTION, APP_NAME) com
        valor de exemplo, para o próximo fork saber que elas existem sem
        precisar ler o código.
```

## 5. Requisitos Não Funcionais

```
RNF-01 - Nenhuma mudança visual ou de comportamento no UidCore em produção
         hoje — com .env atual (sem as variáveis novas), toda tela deve
         renderizar exatamente "UidCore" como renderiza hoje (validação
         manual do Sentinel: comparar screenshot/HTML renderizado antes x
         depois nas 5 páginas afetadas).
RNF-02 - APP_NAME (backend) e VITE_APP_NAME/VITE_APP_DESCRIPTION (frontend)
         seguem o padrão já existente no projeto: python-decouple
         (config('VAR', default=...)) no backend, import.meta.env no
         frontend — nenhum padrão novo de leitura de env introduzido.
RNF-03 - appConfig.js é o ÚNICO arquivo do frontend que lê
         import.meta.env.VITE_APP_NAME/VITE_APP_DESCRIPTION diretamente —
         todo .jsx consome via import, nunca lendo import.meta.env direto
         (evita duplicar a lógica de fallback em cada arquivo, mesmo
         princípio já aplicado a selectTemAcessoTotal no authStore.js,
         Manutenção #60).
RNF-04 - Comentários/docstrings preservados literalmente — nenhuma edição
         cosmética fora do escopo (grep "UidCore" pós-implementação deve
         retornar SÓ ocorrências em comentários/docstrings e nos arquivos
         .env.example/fallbacks, nunca mais em string de UI/template literal
         fora do fallback).
```

## 6. Atores e Perfis

Não há mudança de ator/perfil nesta manutenção — é configuração de
infraestrutura de template, sem regra de negócio ou permissão nova. Afeta
visualmente qualquer usuário autenticado (todas as telas) e visitante não
autenticado (Login, DefinirSenha, AgendamentoPublico).

## 7. Regras de Negócio

```
RN-01 - Fallback sempre que a env var estiver ausente OU vazia (string
        vazia), nunca só "ausente" — .env com VITE_APP_NAME= (vazio) deve
        cair no fallback 'UidCore', mesmo comportamento de config()/
        import.meta.env de resolver string vazia como valor "falso" para
        esse propósito (usar `|| 'UidCore'` no JS, equivalente ao
        default= do decouple no Python).
RN-02 - transformIndexHtml do vite.config.js só substitui <title> e a
        <meta name="description">, nunca introduz novo texto nem remove
        outras tags existentes do index.html (preconnect de fontes, script
        anti-FOUC do tema, favicon) — edição cirúrgica, não reescrita do
        arquivo.
RN-03 - site_header/site_title do Django admin são lidos 1x na definição
        (admin.site.site_header = settings.APP_NAME), não por request —
        comportamento padrão do Django admin, sem necessidade de
        middleware ou context processor.
```

## 8. Fora do Escopo

```
- manifest.json / ícones PWA (não existe ainda — explicitamente não criar)
- Comentários e docstrings mencionando "UidCore" no código-fonte
- Identificadores técnicos: nome do banco (DB_NAME), domínio, path do
  projeto na VPS, chave de localStorage (uidcore-theme), nome do repo
  GitHub
- Qualquer fork/rebranding de verdade (ex.: criar o próximo cliente com
  nome configurado) — esta manutenção só entrega a capacidade de
  configurar, não executa nenhum rebranding
```

## 9. Riscos e Dependências

```
- Risco baixo: transformIndexHtml mal configurado pode quebrar o build do
  Vite (index.html malformado) — Sentinel deve confirmar `npm run build`
  limpo E inspecionar o index.html gerado em dist/ antes de aprovar.
- Dependência: nenhuma lib nova — import.meta.env é nativo do Vite,
  python-decouple já é dependência do backend.
- Nenhuma migration de banco — mudança é só de configuração/texto, nenhum
  model/campo novo.
- Validação funcional esperada pelo cliente (explicitada no pedido): com
  VITE_APP_NAME=OutroNome / APP_NAME=OutroNome setados, TODOS os 8 pontos
  de UI + email + admin devem mudar juntos; com .env vazio, tudo volta a
  "UidCore". Sentinel deve testar os dois cenários (variável setada E
  variável ausente), não só um dos dois.
```

---

## Observação para o Planner

Fase única (sem fases múltiplas) — Forge (backend: settings.py, services.py,
admin.py/urls.py, .env.example) e Loom (frontend: appConfig.js, vite.config.js,
7 arquivos .jsx, .env.example) podem rodar em paralelo, sem dependência
cruzada real entre as duas frentes (nenhum contrato de API novo). Sentinel
deve validar os dois cenários de RN-01/RNF-01 antes de aprovar.
