# Especificação — Manutenção #45
**Elaborado por:** Analista (MODO HOTFIX)
**Data:** 2026-08-19
**Sistema:** UidCore (OS #7)

**Solicitação original (resumida):**
Complemento da Manutenção #44 (já deployada). Permitir criar acesso ao
sistema também ao EDITAR um Colaborador que ainda não tem acesso
(`tem_acesso=false`) — hoje o toggle "Criar acesso ao sistema" só aparece
na criação. Motivo: já existem colaboradores cadastrados sem acesso, que
precisam ganhar acesso depois sem precisar recriar o cadastro.

---

## Classificação

```
tipo: feature_pequena
sistema: UidCore
caminho_afetado: backend/rh/views.py (ColaboradorViewSet — perform_create + novo perform_update)
                 frontend/src/pages/Rh.jsx (aba Colaboradores — fields da tab)
complexidade: baixa
requer_aprovacao_comercial: false
```

---

## Diagnóstico confirmado (leitura direta do código)

Lido `backend/rh/views.py` (`ColaboradorViewSet.perform_create` completo),
`backend/rh/models.py` (`Colaborador`), `backend/rh/serializers.py`
(`ColaboradorSerializer`) e `frontend/src/pages/Rh.jsx` (tab
`colaboradores`) + `frontend/src/components/ui/ResourceCrud.jsx`
(mecânica de `hideOnEdit`, `showIf`, `fieldValue`, `openEdit`,
`buildPayload`).

### O que já existe hoje (confirmado linha a linha)

- `Colaborador.usuario` — `OneToOneField('accounts.User', null=True,
  blank=True, on_delete=SET_NULL)`. Não tem acesso = `usuario_id is None`.
- `ColaboradorSerializer.tem_acesso` — `SerializerMethodField` **read-only**
  (`get_tem_acesso(self, obj): return obj.usuario_id is not None`). Já
  volta em toda resposta da API (list e retrieve), sem precisar de nada
  novo no serializer para o frontend consumir.
- `ColaboradorViewSet.perform_create` (único método hoje) — lê
  `criar_usuario`/`usuario_email`/`usuario_senha` direto de
  `self.request.data` (campos que não existem no model nem no
  serializer, mesmo padrão documentado no docstring do método). Sequência
  atual: `criar_usuario` falsy → `serializer.save()` e retorna. Se truthy:
  1) `IsAdmin` (`self.request.user.is_staff`, senão `PermissionDenied`);
  2) monta `email` = `usuario_email` do request OU
     `serializer.validated_data.get('email')`, `.strip().lower()`;
  3) `ValidationError` se `email` vazio;
  4) `ValidationError` se já existe `User` com esse email
     (`iexact`);
  5) `ValidationError` se `usuario_senha` informada com menos de 6 chars;
  6) tudo dentro de **um único `transaction.atomic()`**: `serializer.save()`
     cria o `Colaborador`, depois cria o `User` (`set_password` ou
     `set_unusable_password`), depois `colaborador.usuario = usuario` +
     `colaborador.save(update_fields=['usuario'])`;
  7) fora do atomic, se não veio senha, chama `enviar_primeiro_acesso(usuario)`
     dentro de `try/except Exception: pass` (silencioso — não derruba a
     criação do colaborador por falha de e-mail).
- Não existe `perform_update` — hoje um `PATCH`/`PUT` em `Colaborador`
  passa direto pelo `ModelViewSet.perform_update` padrão (`serializer.save()`
  puro), então **nenhuma validação de `criar_usuario` roda no update
  hoje** — é por isso que o pedido não funciona: mesmo que o frontend
  mandasse `criar_usuario=true` num PATCH hoje, o backend ignoraria (campo
  não existe no serializer, DRF descarta silenciosamente).
- Frontend (`Rh.jsx`, tab `colaboradores`): os 4 campos relacionados a
  acesso (`acesso_divider`, `criar_usuario`, `usuario_email`,
  `usuario_senha`) têm `hideOnEdit: true` — `ResourceCrud.jsx` linha 300
  (`if (f.hideOnEdit && editingId) return false`) os esconde
  incondicionalmente sempre que `editingId` existe, ou seja, em qualquer
  edição, mesmo de colaborador sem acesso.
- `ResourceCrud.openEdit(item)` popula `form` chamando `fieldValue(item, f)`
  para **todo** field da lista `fields` — inclusive um novo field
  `tem_acesso` que não é renderizado (basta declará-lo, sem precisar de
  `type` especial: `fieldValue` só faz `item[field.name]`, e `tem_acesso`
  já vem no payload de list/retrieve da API).
- `ResourceCrud.buildPayload()` envia **todo** o objeto `form` via
  `stripEmptyStrings` (só remove `''`, preserva `true`/`false`) —
  portanto `tem_acesso` vai junto no PATCH, mas como é
  `SerializerMethodField` (sempre read-only, nunca aceito em input), o
  DRF descarta silenciosamente esse valor do payload. Não requer nenhum
  tratamento extra no backend — só citado aqui para não gerar dúvida no
  Sentinel ao ver `tem_acesso` no corpo do request.

---

## Requisitos Funcionais

**RF-01** — `ColaboradorViewSet` deve extrair a lógica de validação de
`criar_usuario` (hoje só dentro de `perform_create`) para um método
privado `_validar_criar_usuario(self, email_fallback)`, reutilizado por
`perform_create` e pelo novo `perform_update`. Retorna a tupla
`(email, senha)` já normalizados (`email` em minúsculo/sem espaços,
`senha` como veio ou `''`). Levanta as mesmas exceções de hoje
(`PermissionDenied` se não-admin; `ValidationError` se email vazio, email
já usado, ou senha < 6 chars quando informada).

**RF-02** — `ColaboradorViewSet` deve extrair a criação efetiva do
`User` + vínculo para um método privado
`_criar_usuario_para_colaborador(self, colaborador, email, senha)`,
reutilizado por `perform_create` e `perform_update`: cria `User`
(`set_password` se `senha`, senão `set_unusable_password()`), salva, seta
`colaborador.usuario = user`, `colaborador.save(update_fields=['usuario'])`,
e — só quando `senha` vazia — dispara `enviar_primeiro_acesso(usuario)`
dentro do mesmo padrão `try/except Exception: pass` já existente hoje.

**RF-03** — `perform_create` deve ser reescrito para usar `RF-01`+`RF-02`
sem mudar nenhum comportamento observável (mesma sequência: valida tudo
antes de salvar, tudo dentro do mesmo `transaction.atomic()`, mesmo
fallback de email = `usuario_email` do request OU `email` do
colaborador sendo criado).

**RF-04** — Novo `perform_update(self, serializer)`: mesmo fluxo do
`perform_create` (ler `criar_usuario` de `self.request.data`; se falsy,
`serializer.save()` e retorna), mas com guarda extra ANTES de validar
qualquer coisa: se `serializer.instance.usuario_id` já estiver
preenchido (colaborador já tem acesso) **e** `criar_usuario` vier truthy
no payload, levantar `ValidationError('Colaborador já tem acesso ao
sistema')` — nada é salvo, nem o `Colaborador`, nem o `User`. Fallback de
email para o update, nesta ordem: `usuario_email` do request →
`serializer.validated_data.get('email')` → `serializer.instance.email`
(diferente do `perform_create`, que não tem `instance.email` para cair
de volta — no update o colaborador já existe, então o e-mail atual dele é
um fallback válido mesmo que não venha no PATCH). Resto do fluxo idêntico
ao `perform_create`: validar tudo antes, `serializer.save()` +
criação/vínculo do `User` dentro do mesmo `transaction.atomic()`.

**RF-05** — Frontend: remover `hideOnEdit: true` dos 4 campos
`acesso_divider`, `criar_usuario`, `usuario_email`, `usuario_senha` na tab
`colaboradores` de `Rh.jsx`.

**RF-06** — Frontend: adicionar um field oculto
`{ name: 'tem_acesso', showIf: () => false }` ao array `fields` da tab
`colaboradores` — nunca renderizado (por isso não precisa de `label`
nem `type`), só existe para que `ResourceCrud.openEdit` popule
`form.tem_acesso` a partir do valor real vindo da API
(`ColaboradorSerializer.tem_acesso`). `emptyForm` da tab deve incluir
`tem_acesso: false`, para que um colaborador **novo** (ainda sem
`editingId`) também tenha `form.tem_acesso === false` e portanto veja a
seção de acesso.

**RF-07** — Frontend: trocar o `showIf` de `acesso_divider` e de
`criar_usuario` para `(form) => !form.tem_acesso` (ambos, mesmo predicado
— hoje nenhum dos dois tem `showIf`, só `hideOnEdit`). `usuario_email` e
`usuario_senha` **não mudam** — continuam com `showIf: (form) =>
!!form.criar_usuario`, sem depender de `tem_acesso` diretamente (eles já
ficam implicitamente escondidos quando a seção some, porque
`criar_usuario` nunca fica `true` nesse caso).

---

## Regras de Negócio

**RN-01** — Um colaborador só pode ganhar acesso uma vez. Se
`Colaborador.usuario_id` já está preenchido, qualquer tentativa de mandar
`criar_usuario=true` num PATCH é rejeitada com `ValidationError`, sem
sobrescrever nem duplicar o vínculo existente. Vale tanto vindo da tela
(que não deveria nem mostrar o toggle nesse caso — RF-07) quanto de um
PATCH direto na API (defesa em profundidade, não só UI).

**RN-02** — Toda validação de `criar_usuario` no update (permissão, email
vazio, email duplicado, senha curta) roda **antes** de qualquer
persistência, e `Colaborador.save()` + `User.save()` ficam dentro do
mesmo `transaction.atomic()` — mesma garantia já aplicada ao
`perform_create` na Manutenção #44 (nenhum `Colaborador` fica com
alteração parcial salva se a criação do `User` falhar no meio).

**RN-03** — Só `IsAdmin` (`request.user.is_staff`) pode criar acesso,
tanto na criação quanto na edição — `PermissionDenied` para qualquer
outro perfil autenticado, mesmo que a rota de `Colaborador` em si seja
aberta para qualquer autenticado.

**RN-04** — O fallback de e-mail é diferente entre criação e edição: na
criação não há e-mail "atual" do colaborador salvo antes (ele está sendo
criado agora), então o fallback é só `usuario_email` do request →
`email` do form. Na edição, o colaborador já existe no banco, então o
fallback final é o `email` já persistido nele (`serializer.instance.email`),
não só o que vier no `validated_data` do PATCH (que pode nem incluir o
campo `email` se o usuário só mexeu no toggle de acesso).

**RN-05** — Colaborador que já tem acesso (`tem_acesso=true`) nunca
mostra a seção de "Criar acesso ao sistema" ao editar — nem o toggle, nem
os campos de e-mail/senha de acesso. Evita o usuário achar que pode
"recriar" ou "trocar" o acesso por ali (fluxo de troca de e-mail/senha do
usuário já existente é responsabilidade da tela de Usuários, Manutenção
#44 — fora de escopo aqui).

---

## Telas / UX (Frontend)

Sem nenhuma tela nova. Mudança de comportamento na tab **Colaboradores**
dentro de `Rh.jsx` (`ResourceCrud` genérico):

- **Criar colaborador novo:** comportamento igual a hoje — seção "Criar
  acesso ao sistema" visível desde o início do form (`tem_acesso` no
  `emptyForm` é `false`).
- **Editar colaborador SEM acesso:** antes (Manutenção #44) a seção
  inteira sumia ao entrar em modo edição. Agora aparece igual à criação:
  divider + toggle "Criar acesso ao sistema"; marcando o toggle, aparecem
  "E-mail de acesso" (pré-preenchido com `next.email` se vazio, via
  `onToggle` já existente) e "Senha (opcional)".
- **Editar colaborador COM acesso:** nenhuma mudança visível — a seção
  continua completamente oculta (mesmo resultado visual de hoje, agora
  garantido por `showIf` em vez de `hideOnEdit`).
- Nenhuma mudança de layout, cores, textos ou labels — reaproveita 100%
  dos componentes/strings já existentes (`divider`, `checkbox`, `email`,
  `password`, `helpText`).

---

## Spec Backend

`backend/rh/views.py`, dentro de `ColaboradorViewSet`:

```python
def _validar_criar_usuario(self, email_fallback):
    if not self.request.user.is_staff:
        raise PermissionDenied('Somente administradores podem criar acesso ao sistema.')

    from accounts.models import User

    email = (
        self.request.data.get('usuario_email')
        or email_fallback
        or ''
    ).strip().lower()
    if not email:
        raise ValidationError({'usuario_email': 'Informe um email (do colaborador ou de acesso) para criar o usuario.'})
    if User.objects.filter(email__iexact=email).exists():
        raise ValidationError({'usuario_email': 'Ja existe um usuario com esse email.'})

    senha = self.request.data.get('usuario_senha') or ''
    if senha and len(senha) < 6:
        raise ValidationError({'usuario_senha': 'A senha deve ter pelo menos 6 caracteres.'})

    return email, senha

def _criar_usuario_para_colaborador(self, colaborador, email, senha):
    from accounts.models import User
    from accounts.services import enviar_primeiro_acesso

    usuario = User(email=email, nome_completo=colaborador.nome or email)
    if senha:
        usuario.set_password(senha)
    else:
        usuario.set_unusable_password()
    usuario.save()

    colaborador.usuario = usuario
    colaborador.save(update_fields=['usuario'])

    if not senha:
        try:
            enviar_primeiro_acesso(usuario)
        except Exception:
            pass

def perform_create(self, serializer):
    criar_usuario = str(self.request.data.get('criar_usuario', '')).lower() in ('1', 'true', 'on')
    if not criar_usuario:
        serializer.save()
        return

    email_fallback = serializer.validated_data.get('email') or ''
    email, senha = self._validar_criar_usuario(email_fallback)

    with transaction.atomic():
        colaborador = serializer.save()
        self._criar_usuario_para_colaborador(colaborador, email, senha)

def perform_update(self, serializer):
    criar_usuario = str(self.request.data.get('criar_usuario', '')).lower() in ('1', 'true', 'on')
    if not criar_usuario:
        serializer.save()
        return

    if serializer.instance.usuario_id:
        raise ValidationError('Colaborador ja tem acesso ao sistema.')

    email_fallback = (
        serializer.validated_data.get('email')
        or serializer.instance.email
        or ''
    )
    email, senha = self._validar_criar_usuario(email_fallback)

    with transaction.atomic():
        colaborador = serializer.save()
        self._criar_usuario_para_colaborador(colaborador, email, senha)
```

Observações para o Forge:
- `_validar_criar_usuario` recebe o fallback já resolvido pelo chamador
  (create vs update têm fontes de fallback diferentes — RN-04) em vez de
  decidir isso internamente, para não duplicar `if` de create/update
  dentro do método compartilhado.
- Guarda de `RN-01` (`serializer.instance.usuario_id`) fica **dentro** de
  `perform_update`, antes de chamar `_validar_criar_usuario` — não faz
  sentido validar e-mail/senha se a operação vai ser rejeitada de
  qualquer forma por já ter acesso.
- Import de `User`/`enviar_primeiro_acesso` mantido local (dentro dos
  métodos), igual ao padrão já existente no arquivo — não subir para o
  topo do módulo.

---

## Spec Frontend

`frontend/src/pages/Rh.jsx`, tab `colaboradores`, dentro de `fields`:

```jsx
{ name: 'acesso_divider', type: 'divider', showIf: (form) => !form.tem_acesso },
{
  name: 'criar_usuario',
  label: 'Criar acesso ao sistema',
  type: 'checkbox',
  colSpan2: true,
  showIf: (form) => !form.tem_acesso,
  onToggle: (checked, next) => (checked && !next.usuario_email ? { ...next, usuario_email: next.email } : next),
},
{
  name: 'usuario_email',
  label: 'E-mail de acesso',
  type: 'email',
  colSpan2: true,
  showIf: (form) => !!form.criar_usuario,
},
{
  name: 'usuario_senha',
  label: 'Senha (opcional)',
  type: 'password',
  colSpan2: true,
  showIf: (form) => !!form.criar_usuario,
  helpText: 'Deixe em branco para enviar link de definição de senha por e-mail.',
},
{ name: 'tem_acesso', showIf: () => false },
```

`emptyForm` da tab passa a incluir `tem_acesso: false`:

```jsx
emptyForm={{
  nome: '', cpf: '', email: '', cargo: '', regime: 'CLT', salario_atual: '', data_admissao: '', data_demissao: '', observacoes: '',
  criar_usuario: false, usuario_email: '', usuario_senha: '', tem_acesso: false,
}}
```

`onBeforeSubmit` não muda — a validação de e-mail obrigatório ao marcar
`criar_usuario` já é genérica (`!editingId && ...` hoje só cobre
criação; não é necessário estender para edição porque o backend já
valida e retorna erro legível via `extractErrorMessage`, e o
`onBeforeSubmit` atual não bloqueia incorretamente o novo fluxo de edição
— só adiciona uma validação a mais na criação, que continua correta).
Não é obrigatório mexer nele nesta manutenção; citado aqui só para o Loom
não achar que esqueceu algo.

Observação sobre o field `tem_acesso` oculto: não precisa de `type` —
`fieldValue()` em `ResourceCrud.jsx` só lê `item[field.name]` quando o
`type` não é `'file'`/`'datetime-local'`, então o valor booleano vindo da
API (`item.tem_acesso`) é copiado para o form sem transformação.

---

## Fora do Escopo

- Trocar e-mail/senha de um usuário que já tem acesso (fluxo já existe na
  tela de Usuários, Manutenção #44).
- Revogar/desvincular acesso de um colaborador (não pedido).
- Qualquer mudança visual/design system — reaproveita componentes
  existentes sem alteração de estilo.

---

## Riscos e Dependências

- Depende 100% da Manutenção #44 já estar em produção (está — deploy
  confirmado em 2026-08-19, commit `e346f45`). `tem_acesso` e
  `usuario_email` no serializer, e o padrão de campos extras via
  `self.request.data`, já existem e não precisam ser recriados.
- Risco baixo: mudança é aditiva (`perform_update` novo + refactor DRY de
  `perform_create` sem alterar seu comportamento) — não deveria haver
  regressão no fluxo de criação (RF-03 é justamente a garantia de
  paridade comportamental via extração de método, e é o critério de
  aceite #5 do Sentinel).

---

## Critérios de Aceite (para o Sentinel validar de verdade — não só leitura de código)

**CA-01** — Editar colaborador existente **sem** acesso, marcar "Criar
acesso ao sistema" com senha informada (≥6 chars): PATCH retorna sucesso,
`Colaborador.usuario_id` passa a apontar para um `User` novo com a senha
setada (login funciona com essa senha), `tem_acesso` no retorno da API
vira `true`.

**CA-02** — Mesmo fluxo do CA-01, mas sem informar senha: `User` criado
com `set_unusable_password()`, `enviar_primeiro_acesso` disparado
(confirmar e-mail enviado ou, no mínimo, que a chamada não lança exceção
e não impede a criação — checar log/mailhog se disponível no ambiente de
teste).

**CA-03** — Colaborador que já tem acesso (`tem_acesso=true`) não mostra
mais o toggle "Criar acesso ao sistema" ao abrir o modal de edição —
verificar via teste de frontend (ou inspeção do form renderizado) que os
4 campos (`acesso_divider`, `criar_usuario`, `usuario_email`,
`usuario_senha`) não aparecem no DOM.

**CA-04** — PATCH direto na API (sem passar pelo frontend) com
`criar_usuario=true` para um colaborador cujo `usuario_id` já está
preenchido: resposta `400` com `ValidationError` (`'Colaborador ja tem
acesso ao sistema.'` ou equivalente), e confirmar no banco que **nada**
mudou — nem o `Colaborador.usuario_id` foi sobrescrito, nem um `User`
novo foi criado (checar `User.objects.count()` antes/depois).

**CA-05** — Fluxo de criação (`perform_create`) sem regressão: criar
colaborador novo com `criar_usuario=true` (com e sem senha) continua
funcionando exatamente como antes da Manutenção #45 — mesmo
comportamento validado na Manutenção #44 (validação prévia, atomic,
e-mail duplicado rejeitado, senha curta rejeitada, `PermissionDenied`
para não-admin).

**CA-06** — Criar colaborador novo **sem** marcar "Criar acesso" (fluxo
mais comum) continua funcionando sem nenhum campo extra sendo exigido —
`Colaborador` salvo com `usuario_id=None`, `tem_acesso=false` no retorno.

**CA-07** — Editar colaborador sem acesso e **não** marcar o toggle
(só alterar outro campo, ex. salário): PATCH funciona normalmente, sem
nenhuma tentativa de criar `User`, `usuario_id` continua `None`.

---

**Complexidade estimada:** baixa (extensão pontual de um `ViewSet` já
existente + remoção de 4 flags `hideOnEdit` e adição de `showIf` no
frontend — sem models novos, sem migration, sem tela nova).

---
✅ Análise concluída — UidCore
   tipo: feature_pequena
   - 7 RFs levantados | 0 entidades novas | Complexidade: baixa
➡️  Planner: rotear conforme tipo (Pipeline C — lite: Forge + Loom direto, sem Blueprint/Brush, com Sentinel obrigatório antes do Pilot)
