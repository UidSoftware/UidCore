# Especificação Hotfix — Manutenção #72

**Sistema:** UidCore (OS #7)
**Título:** Foto de perfil do usuário (accounts.User) + helper reaproveitável de processamento de imagem
**Analista:** Modo Manutenção
**Data:** 2026-10-28

---

## 1. Contexto (AS-IS)

Levantamento confirmado por leitura direta dos arquivos do projeto antes de escrever esta especificação:

1. **Manutenção #71 (concluída, deployada)** já deixou o terreno pronto: `/app/media` vive num volume Docker nomeado (`uidcore_media_volume`) que sobrevive a `docker compose up`/recriação de container, e `STORAGE_BACKEND` (`local`|`s3`) já é configurável via `.env` em `backend/core/settings.py` (`STORAGES` dict), sem precisar tocar em código pra trocar de backend. `Pillow>=10.0,<11.0` já está em `backend/requirements.txt` desde aquela manutenção — nenhuma dependência nova a adicionar para esta.
2. **`accounts.User`** (`backend/accounts/models.py`) é `AbstractBaseUser` puro — **não** herda `common.models.BaseModel` (não tem `deleted_at`/soft delete; isso já é um padrão documentado no código, ver comentário em `UserViewSet.perform_destroy`). Hoje não tem nenhum `ImageField`/`FileField`.
3. **`UserSerializer`** (`backend/accounts/serializers.py`) é o serializer de `GET/PATCH /api/v1/accounts/me/` (`UserProfileView`, `RetrieveUpdateAPIView`) — é ele que povoa `useAuthStore.user` no login (`frontend/src/stores/authStore.js`, linha ~19: `GET /accounts/me/`) e é persistido em `localStorage` pelo `persist` do zustand.
4. **Padrão de endpoint de ação simples sobre o usuário logado**: `AlterarSenhaView` (`backend/accounts/views.py`) — `APIView`, `permission_classes = [IsAuthenticated]`, sem serializer formal, valida `request.data`/`request.FILES` manualmente, devolve `{"mensagem"|"erro": ...}` com status 200/400. É o modelo a seguir para a view de foto (adaptado pra multipart no POST).
5. **Prefixo de rota real**: não existe app `auth` no projeto — o pedido menciona `/api/v1/auth/me/foto/`, mas o prefixo real (confirmado em `backend/core/urls.py`, linha 13: `path('api/v1/accounts/', include('accounts.urls'))`) é **`/api/v1/accounts/`**, igual a `/api/v1/accounts/me/` e `/api/v1/accounts/alterar-senha/` já existentes. **Esta especificação usa `/api/v1/accounts/me/foto/` como caminho real** — "auth" no pedido é referência de domínio (rotas de autenticação/perfil), não um app/prefixo literal. Registrado aqui para o Forge não procurar um app `auth` inexistente.
6. **Padrão de storage API-agnóstica**: `pagamentos.Comprovante.comprovante` e `financeiro.Despesa.comprovante` (`FileField(upload_to='...')`) e `administrativo.Documento.arquivo` são os 3 `FileField`/`ImageField` existentes no projeto (todos da Manutenção #71) — nenhum tem hoje lógica de "apagar o arquivo antigo ao substituir". Esta manutenção introduz esse padrão pela primeira vez (`campo.delete(save=False)`), que deve ficar isolado no helper novo pra ser reaproveitado quando Cliente/Colaborador ganharem foto depois.
7. **LGPD (Manutenção #66)** — `common/lgpd.py` é um registry (`registrar_exportador(app_label, titulo, funcao)`), chamado no `AppConfig.ready()` de cada app (`clientes/apps.py`, `portal/apps.py`). A exportação é sempre por **`cliente` (titular = `clientes.Cliente`)**, nunca por `User` diretamente — `accounts.User` é conta de sistema (staff/operador), não o titular de dados do LGPD. A ponte existente entre os dois mundos é `portal.AcessoPortalCliente` (`OneToOneField` pra `User`, `ForeignKey` pra `Cliente`) — é o Portal do Cliente (cliente final loga com uma conta `User` vinculada ao próprio cadastro de `Cliente`). `portal/lgpd.py::exportar_titular(cliente)` já lista esses acessos (e-mail + último acesso, nunca o PK cru — RNF-04 da Especificacao daquela manutenção). **"a exportação passa a incluir a foto" (pedido) = incluir `foto_url` dentro de cada item de `acessos` em `portal/lgpd.py`, quando o `User` vinculado tiver foto** — não cria nenhum vínculo novo nem exporta foto de `rh.Colaborador` (fora de escopo, ver seção 8).
8. **Header.jsx** (`frontend/src/components/layout/Header.jsx`) hoje mostra só a inicial do nome/e-mail num círculo (linhas 76-80) e tem o botão "Senha" que abre modal de alterar senha (`AlterarSenhaView`) — é o padrão exato a replicar pro botão "Alterar foto".
9. **`Usuarios.jsx`** usa `ResourceCrud` genérico (`frontend/src/components/ui/ResourceCrud.jsx`) — colunas hoje suportam `boolean`, `date`, `badge`, mas **não existe tipo de coluna pra imagem/avatar**. Precisa de uma extensão pequena no `ResourceCrud` (não em `Usuarios.jsx` sozinho, pra qualquer tela futura reaproveitar).
10. `request.FILES` multipart já tem precedente de uso manual fora do `ResourceCrud` (ex.: upload de extrato em Conciliação) — não é um padrão novo a inventar.

---

## 2. TO-BE

- `accounts.User` ganha campo `foto` (`ImageField`, nome aleatório, nunca o id do usuário nem o nome original do arquivo).
- Endpoint dedicado `POST`/`DELETE /api/v1/accounts/me/foto/` (padrão `AlterarSenhaView`) processa e grava/remove a foto do usuário autenticado.
- Processamento de imagem (validação real de conteúdo, remoção de EXIF, recorte quadrado, conversão pra WebP) vive num helper único em `common/`, pensado desde já pra `clientes.Cliente` e `rh.Colaborador` reaproveitarem sem duplicar lógica (mesma filosofia dos mixins/validators já centralizados em `common/`).
- `UserSerializer` expõe `foto_url` (read-only, URL completa/assinada conforme o storage).
- Trocar/remover foto sempre libera o arquivo antigo do storage (local ou S3), sem acumular lixo.
- `Header.jsx` ganha avatar real (foto ou iniciais) e o fluxo "Alterar foto" ao lado de "Alterar senha".
- `Usuarios.jsx` mostra o avatar na listagem (via extensão no `ResourceCrud`).
- `portal/lgpd.py` passa a incluir `foto_url` do usuário vinculado na exportação LGPD do titular (`Cliente`).

---

## 3. Requisitos Funcionais

```
RF-01 - accounts.User.foto (ImageField, null=True, blank=True) — nome do arquivo
        sempre gerado como avatars/<uuid4>.webp, nunca derivado do id do
        usuario nem do nome original enviado pelo cliente.

RF-02 - POST /api/v1/accounts/me/foto/ (multipart, campo "foto",
        IsAuthenticated) processa o arquivo enviado via helper comum,
        salva em User.foto do usuario logado (request.user — nunca outro
        usuario) e devolve {"foto_url": "<url>"} (200). Erro de validacao
        devolve {"erro": "<mensagem amigavel>"} (400), nunca stacktrace
        cru.

RF-03 - DELETE /api/v1/accounts/me/foto/ (IsAuthenticated) remove a foto do
        usuario logado: apaga o arquivo do storage E limpa User.foto.
        Devolve {"foto_url": null} (200). Chamar sem ter foto cadastrada
        tambem devolve 200 com foto_url: null (idempotente, sem erro).

RF-04 - UserSerializer ganha foto_url (SerializerMethodField, read-only) —
        None quando o usuario nao tem foto; URL completa (absoluta no
        local, assinada no S3 - reaproveita Field.url, que ja resolve os
        dois casos sem logica condicional no serializer) quando tem.

RF-05 - Helper comum/media.py::processar_foto(arquivo_upload) -> ContentFile
        pronto para FileField.save(): abre com Pillow de verdade (nunca
        confia em content_type/extensao), corrige orientacao via EXIF
        (ImageOps.exif_transpose), descarta todo EXIF restante (inclusive
        GPS), recorta quadrado central e redimensiona para 256x256, salva
        como WEBP com nome aleatorio (uuid4().webp). Levanta
        django.core.exceptions.ValidationError com mensagem amigavel
        quando: arquivo > 5 MB, ou conteudo nao decodifica como imagem
        (ex.: PDF renomeado .jpg). Esta funcao e generica o bastante para
        clientes.Cliente e rh.Colaborador reaproveitarem quando a foto
        deles for implementada (fora do escopo desta manutencao) — nao
        deve ter nenhuma referencia a accounts.User dentro dela.

RF-06 - Trocar a foto (RF-02 com usuario que ja tinha foto) ou remover
        (RF-03) sempre apaga o arquivo antigo do storage configurado
        (local ou S3) via API de storage do Django (campo.delete(save=
        False) ou default_storage.delete(nome)) — nunca deixa arquivo
        orfao. O registro do accounts.User em si NUNCA e soft/hard
        deletado por essa operacao (accounts.User nao tem soft delete,
        ver contexto item 2 — isso aqui e so o arquivo de midia).

RF-07 - portal/lgpd.py::exportar_titular(cliente) passa a incluir
        foto_url (mesma logica de Field.url) de cada acesso, quando
        a.usuario existir e tiver foto. None quando nao houver foto ou
        nao houver usuario vinculado (acesso ainda pendente de ativacao).
        Nao altera o formato das chaves ja existentes
        (usuario_email, ultimo_acesso).

RF-08 - common/Avatar.jsx (frontend) renderiza foto (se foto_url existir)
        ou iniciais num circulo com cores do design system (mesmo padrao
        de cor hoje hardcoded no Header — bg-primary-100/dark:bg-violet-
        900/40 + texto bg-primary-700/dark:text-violet-300) — sem
        biblioteca de componente, inline styles/Tailwind, consistente com
        o restante do projeto.

RF-09 - Header.jsx usa <Avatar> no lugar do circulo de iniciais hardcoded,
        e ganha item "Alterar foto" (botao proprio, ao lado de "Alterar
        senha") que abre modal com: preview da imagem escolhida antes de
        enviar, botao "Salvar", botao "Remover foto" (so aparece se o
        usuario logado ja tiver foto_url). Erro do backend (ex.: "Arquivo
        maior que 5 MB", "Arquivo enviado nao e uma imagem valida")
        aparece como toast/mensagem amigavel dentro do modal — nunca a
        mensagem crua de excecao JS/Axios.

RF-10 - Apos salvar/remover a foto com sucesso, o useAuthStore e
        atualizado na hora (setUser com o foto_url novo) — o Header
        reflete sem precisar de reload. Reload tambem deve funcionar (a
        foto persiste via GET /accounts/me/ no proximo login/refresh),
        ja que e o cenario minimo exigido na validacao do pedido.

RF-11 - ResourceCrud (frontend/src/components/ui/ResourceCrud.jsx) ganha
        suporte a coluna tipo avatar (ex.: { key: 'foto_url', avatar:
        true, nomeField: 'nome_completo' }) que renderiza <Avatar> em vez
        de texto cru — usado por Usuarios.jsx. Extensao no componente
        generico, nao logica isolada dentro de Usuarios.jsx, para
        qualquer tela futura (ex.: Colaboradores) reaproveitar sem
        duplicar.
```

---

## 4. Regras de Negócio

```
RN-01 - Upload/remocao de foto SEMPRE opera sobre request.user (usuario do
        token JWT) — a rota nao recebe id de usuario na URL nem no body;
        ninguem altera foto de outra conta por esse endpoint (diferente
        da tela de Usuarios/IsAdmin, que e outro endpoint, outro
        proposito). Admin que precisar remover foto de terceiro usa a
        tela de Usuarios (UserAdminSerializer) — fora do escopo desta
        manutencao, nao implementar agora.

RN-02 - Limite de tamanho (5 MB) e checado ANTES de abrir o arquivo com
        Pillow (request.FILES['foto'].size), evitando decodificar/alocar
        memoria para um arquivo gigante so para descobrir depois que ele
        sera rejeitado.

RN-03 - Validacao de "e imagem de verdade" nunca confia em content_type
        do multipart nem na extensao do nome do arquivo — so decodificar
        com Pillow (Image.open + load()/transpose real) determina isso.
        Um PDF renomeado para .jpg deve ser rejeitado com 400, nunca
        salvo como se fosse imagem corrompida.

RN-04 - EXIF e sempre descartado do arquivo final (Pillow nao grava EXIF
        no save() se o parametro exif não for passado explicitamente) —
        inclusive dados de geolocalizacao (GPS), que podem existir no
        EXIF de fotos tiradas por celular. A UNICA informacao do EXIF
        aproveitada antes de descartar o resto e a orientacao (via
        ImageOps.exif_transpose), para a foto nao salvar de lado/invertida.

RN-05 - Nome de arquivo final e SEMPRE avatars/<uuid4>.webp, independente
        do nome/extensao original enviado pelo navegador — nunca usar
        User.id, User.email nem o filename do upload (evita enumeracao de
        usuario por URL de arquivo e colisao de nome).

RN-06 - Trocar a foto so apaga o arquivo antigo DEPOIS que o novo foi
        processado e salvo com sucesso (nunca apagar o antigo e so depois
        descobrir que o processamento do novo falhou — janela sem foto
        nenhuma por erro de validacao e uma regressao de UX, mesmo que
        pequena).

RN-07 - accounts.User NAO herda common.models.BaseModel (ver contexto
        item 2) — o campo foto fica solto no model (sem deleted_at
        proprio). Isso e esperado e nao deve ser "corrigido" nesta
        manutencao (fora de escopo, e um padrao de arquitetura jah
        documentado no proprio codigo-fonte).

RN-08 - common/media.py (helper) nao importa nada de accounts/clientes/rh
        — recebe so o arquivo e devolve o ContentFile pronto (ou levanta
        ValidationError). Zero acoplamento com o model que vai usar. Isso
        e o que garante reaproveitamento real nas manutencoes futuras de
        foto de Cliente/Colaborador, em vez de "reaproveitamento de
        intencao" que na pratica cada app reimplementa.

RN-09 - Portal/LGPD (RF-07): foto_url exposta ali e a mesma URL que o
        proprio usuario veria no seu /accounts/me/ — nao gera um link
        novo nem copia o arquivo; e so o campo computado a mais no JSON/
        PDF de exportacao do titular.

RN-10 - Fora de escopo nesta manutencao (explicito no pedido): foto de
        clientes.Cliente e rh.Colaborador. O helper (RF-05/RN-08) fica
        pronto para isso, mas NENHUM campo novo em Cliente/Colaborador e
        criado agora. Quando vier, a propria spec futura precisa decidir
        o endpoint autenticado com X-Accel-Redirect (dado pessoal de
        terceiro, nao pode ficar atras de /media/ aberto como a foto do
        proprio usuario fica agora) — nao e decisao desta manutencao, so
        registrada aqui para o proximo ciclo nao esquecer a premissa.
```

---

## 5. Telas (detalhamento funcional — Brush/Loom)

### 5.1 Header — menu do usuário logado

Estado atual: círculo de iniciais (não clicável) + botão "Senha" + botão "Sair".

Novo:
- Círculo de iniciais vira `<Avatar foto={user.foto_url} nome={user.nome_completo || user.email} size="sm" />` — mesma posição, mesmo tamanho (`w-8 h-8`), clicável (abre o modal de foto, igual ao botão "Senha" abre o modal de senha hoje).
- Botão novo "Alterar foto" (ícone de câmera ou similar, mesmo estilo visual dos botões "Senha"/"Sair" já existentes — `text-gray-500 hover:bg-gray-100 ...`), posicionado ao lado do botão "Senha", antes dele (ordem: Avatar clicável → tema → Alterar foto → Senha → Sair, ou Avatar e "Alterar foto" podem ser a mesma ação — decisão de UX do Loom/Brush, ambos os gatilhos abrindo o mesmo modal é aceitável).
- Modal "Alterar foto":
  - Se `user.foto_url` existir: mostra a foto atual grande (preview) + botão "Remover foto" (secundário/destrutivo).
  - Input de arquivo (`accept="image/*"`) — ao selecionar, mostra preview local (via `URL.createObjectURL`) ANTES de enviar, com botões "Salvar" e "Cancelar".
  - Erro do backend (400: arquivo grande, não é imagem) aparece como mensagem no mesmo padrão do modal de senha (`senhaErro` — bloco vermelho acima do form).
  - Sucesso: fecha modal (ou mostra confirmação breve, mesmo padrão do modal de senha) e atualiza `useAuthStore.user.foto_url` na hora.

### 5.2 Usuários (`Usuarios.jsx` / `ResourceCrud`)

- Nova coluna "Foto" (primeira coluna, antes de "Nome") renderizando `<Avatar>` pequeno a partir de `item.foto_url` + `item.nome_completo`. Não é editável nessa tela (upload de foto de outro usuário não é RF desta manutenção — RN-01) — é só visualização.

---

## 6. Especificação Backend (Forge)

### 6.1 Migration — `accounts.User`

```python
# accounts/migrations/0006_user_foto.py
foto = models.ImageField('foto de perfil', upload_to=avatar_upload_path, null=True, blank=True)
```
`avatar_upload_path(instance, filename)` é função de módulo (não lambda — migrations precisam poder serializar a referência), em `accounts/models.py`, simplesmente retornando `f'avatars/{filename}'` — o nome aleatório em si é gerado pelo helper `common/media.py::processar_foto`, não pelo `upload_to` (o `ContentFile` devolvido pelo helper já chega com `.name = '<uuid4>.webp'`).

### 6.2 `common/media.py` (novo arquivo)

```python
import uuid
from io import BytesIO
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image, ImageOps

TAMANHO_MAX_BYTES = 5 * 1024 * 1024
LADO_PADRAO = 256


def processar_foto(arquivo, lado=LADO_PADRAO):
    """
    Reaproveitavel por qualquer model com campo de foto (User hoje;
    Cliente/Colaborador no futuro — RN-08, zero import de app de negocio
    aqui). Recebe o UploadedFile do multipart, devolve ContentFile pronto
    para campo.save(conteudo.name, conteudo). Levanta ValidationError
    (mensagem amigavel) se o arquivo passar de 5 MB ou nao for uma imagem
    de verdade.
    """
    if arquivo.size > TAMANHO_MAX_BYTES:
        raise ValidationError('Arquivo maior que 5 MB.')

    try:
        imagem = Image.open(arquivo)
        imagem = ImageOps.exif_transpose(imagem)  # corrige rotacao, ANTES do EXIF ser descartado
        imagem.load()  # forca decodificacao completa — rejeita arquivo que nao e imagem de verdade
    except Exception:
        raise ValidationError('Arquivo enviado não é uma imagem válida.')

    imagem = imagem.convert('RGB')
    largura, altura = imagem.size
    lado_corte = min(largura, altura)
    esquerda = (largura - lado_corte) // 2
    topo = (altura - lado_corte) // 2
    imagem = imagem.crop((esquerda, topo, esquerda + lado_corte, topo + lado_corte))
    imagem = imagem.resize((lado, lado), Image.LANCZOS)

    buffer = BytesIO()
    imagem.save(buffer, format='WEBP')  # sem passar exif= -> EXIF (inclusive GPS) nao vai pro arquivo final
    return ContentFile(buffer.getvalue(), name=f'{uuid.uuid4()}.webp')
```

Observação para o Forge: capturar `Exception` genérica no `Image.open`/`load()` é intencional aqui — Pillow levanta tipos diferentes dependendo do que o arquivo realmente é (`UnidentifiedImageError`, `OSError`, etc.), e o objetivo é sempre o mesmo 400 amigável, nunca distinguir o tipo de erro pro usuário final.

### 6.3 `accounts/views.py` — `FotoPerfilView`

```python
class FotoPerfilView(APIView):
    """Usuario logado troca ou remove a propria foto de perfil (RF-02/RF-03)."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        from django.core.exceptions import ValidationError
        from common.media import processar_foto

        arquivo = request.FILES.get('foto')
        if not arquivo:
            return Response({'erro': 'Envie o arquivo no campo "foto".'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            conteudo = processar_foto(arquivo)
        except ValidationError as e:
            return Response({'erro': e.messages[0] if hasattr(e, 'messages') else str(e)},
                             status=status.HTTP_400_BAD_REQUEST)

        usuario = request.user
        foto_antiga = usuario.foto if usuario.foto else None  # RN-06: so apaga depois do novo salvar
        usuario.foto.save(conteudo.name, conteudo, save=True)
        if foto_antiga:
            foto_antiga.delete(save=False)

        return Response({'foto_url': UserSerializer(usuario, context={'request': request}).data['foto_url']})

    def delete(self, request):
        usuario = request.user
        if usuario.foto:
            usuario.foto.delete(save=False)
            usuario.foto = None
            usuario.save(update_fields=['foto'])
        return Response({'foto_url': None})
```

### 6.4 `accounts/urls.py`

```python
path('me/foto/', FotoPerfilView.as_view(), name='foto_perfil'),
```
Rota real: `POST`/`DELETE /api/v1/accounts/me/foto/` (ver contexto item 5 sobre o prefixo).

### 6.5 `accounts/serializers.py` — `UserSerializer`

```python
class UserSerializer(serializers.ModelSerializer):
    tem_acesso_total = serializers.BooleanField(read_only=True)
    foto_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'email', 'nome_completo', 'telefone', 'is_active', 'is_staff',
                   'perfil', 'tem_acesso_total', 'foto_url', 'date_joined']
        read_only_fields = ['id', 'is_active', 'is_staff', 'perfil', 'tem_acesso_total', 'foto_url', 'date_joined']

    def get_foto_url(self, obj):
        if not obj.foto:
            return None
        return obj.foto.url
```
Nota: `ImageFieldFile.url` já resolve path local (relativo a `MEDIA_URL`) ou URL assinada S3 (via `django-storages`, que não precisa de `request` para gerar a assinatura) — por isso não é necessário `request.build_absolute_uri()` aqui; confirmar durante Sentinel que o frontend (`axios` com `baseURL`) resolve corretamente uma URL relativa (`/media/avatars/...`) vindo da API quando `STORAGE_BACKEND=local` (deve funcionar, mesmo padrão de qualquer outro `FileField` do projeto — ver `comprovante`/`arquivo` já em produção).

`UserAdminSerializer` (tela de Usuários, admin) **não precisa expor `foto_url`** nesta manutenção — RF-11 usa o mesmo serializer (`UserAdminSerializer` é quem alimenta `ResourceCrud` em `Usuarios.jsx` via `/accounts/usuarios/`), então **adicionar `foto_url` (read-only, mesmo método) também em `UserAdminSerializer`** é necessário para a coluna de avatar da tela de Usuários funcionar — ajustar ambos os serializers.

### 6.6 `portal/lgpd.py` (RF-07)

```python
def exportar_titular(cliente):
    from .models import AcessoPortalCliente

    acessos = AcessoPortalCliente.objects.filter(cliente=cliente)
    if not acessos.exists():
        return None

    return {
        'acessos': [
            {
                'usuario_email': a.usuario.email if a.usuario else None,
                'foto_url': (a.usuario.foto.url if (a.usuario and a.usuario.foto) else None),
                'ultimo_acesso': a.ultimo_acesso.isoformat() if a.ultimo_acesso else None,
            }
            for a in acessos
        ]
    }
```

### 6.7 Testes esperados (Sentinel vai cobrar isso — adiantando pro Forge)

- `POST /me/foto/` com JPEG real com EXIF de rotação (fixture) → 200, `foto_url` presente, imagem salva tem 256x256 e **sem** bloco EXIF (`Image.open(caminho).getexif()` vazio/ausente).
- `POST /me/foto/` com PDF renomeado `.jpg` → 400, `User.foto` continua vazio.
- `POST /me/foto/` com arquivo > 5 MB → 400, sem nem tentar decodificar (pode validar via mock/contagem de chamadas ao Pillow, se o Sentinel quiser ser rigoroso — não obrigatório).
- `POST /me/foto/` duas vezes (trocar foto) → arquivo antigo não existe mais no storage (`default_storage.exists(caminho_antigo) is False`), arquivo novo existe.
- `DELETE /me/foto/` → `foto_url: null`, arquivo removido do storage; chamar de novo sem foto → ainda 200, sem erro.
- `GET /accounts/me/` reflete `foto_url` depois do upload.
- `GET /accounts/usuarios/` (admin) reflete `foto_url` de outro usuário.
- `portal` LGPD: `exportar_titular(cliente)` com acesso vinculado a usuário com foto → `foto_url` presente; usuário sem foto → `None`; sem acesso vinculado → função já devolve `None` (comportamento preexistente, não regride).
- Sem token → 401 em `POST`/`DELETE /me/foto/` (padrão de qualquer endpoint `IsAuthenticated`).
- `makemigrations --check --dry-run` limpo após a migration 0006.

---

## 7. Especificação Frontend (Loom)

### 7.1 `frontend/src/components/ui/Avatar.jsx` (novo)

```jsx
export default function Avatar({ foto, nome, size = 'md' }) {
  const tamanhos = { sm: 'w-8 h-8 text-xs', md: 'w-10 h-10 text-sm', lg: 'w-24 h-24 text-2xl' }
  const inicial = (nome || '?')[0].toUpperCase()

  if (foto) {
    return (
      <img
        src={foto}
        alt={nome || 'Avatar'}
        className={`${tamanhos[size]} rounded-full object-cover bg-primary-100 dark:bg-violet-900/40`}
      />
    )
  }
  return (
    <div className={`${tamanhos[size]} rounded-full bg-primary-100 dark:bg-violet-900/40 flex items-center justify-center`}>
      <span className="font-semibold text-primary-700 dark:text-violet-300">{inicial}</span>
    </div>
  )
}
```
(Paleta/tokens exatamente os já usados no círculo de iniciais atual do `Header.jsx` — nenhuma cor nova.)

### 7.2 `Header.jsx`

- Importa `Avatar` e troca o bloco de iniciais hardcoded (linhas 76-80 atuais) por `<Avatar foto={user.foto_url} nome={user.nome_completo || user.email} size="sm" />`, clicável (`onClick={abrirModalFoto}`).
- Novo estado: `modalFoto`, `arquivoFoto` (File escolhido), `previewFoto` (URL do `createObjectURL`), `fotoErro`, `salvandoFoto`.
- Novo botão "Alterar foto" ao lado do botão "Senha" existente, mesmo estilo (`className` idêntico ao botão "Senha", troca só o ícone/label).
- Função `enviarFoto`:
  ```js
  const enviarFoto = async () => {
    setFotoErro('')
    setSalvandoFoto(true)
    try {
      const form = new FormData()
      form.append('foto', arquivoFoto)
      const { data } = await api.post('/accounts/me/foto/', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      useAuthStore.getState().setUser({ ...user, foto_url: data.foto_url })  // RF-10
      setModalFoto(false)
    } catch (error) {
      setFotoErro(error?.response?.data?.erro || extractErrorMessage(error, 'Erro ao enviar foto.'))
    } finally {
      setSalvandoFoto(false)
    }
  }
  ```
- Função `removerFoto` (só visível/chamável se `user.foto_url` existir):
  ```js
  const removerFoto = async () => {
    setSalvandoFoto(true)
    try {
      const { data } = await api.delete('/accounts/me/foto/')
      useAuthStore.getState().setUser({ ...user, foto_url: data.foto_url })
      setModalFoto(false)
    } catch (error) {
      setFotoErro(extractErrorMessage(error, 'Erro ao remover foto.'))
    } finally {
      setSalvandoFoto(false)
    }
  }
  ```
- Preview local: `onChange` do `<input type="file" accept="image/*">` seta `arquivoFoto` e `previewFoto = URL.createObjectURL(file)` — mostrado num `<img>` dentro do modal antes do usuário confirmar "Salvar" (`enviarFoto` só roda no clique do botão, nunca automático no `onChange`, para o usuário poder cancelar).
- Fechar o modal (`closeModalFoto`) deve revogar o preview (`URL.revokeObjectURL(previewFoto)`) para não acumular memória.
- `useAuthStore` já expõe `setUser` (confirmado em `authStore.js`, linha ~39) — usar ele, nunca escrever direto no `localStorage` (o `persist` do zustand já cuida disso ao chamar `setUser`).

### 7.3 `ResourceCrud.jsx` (RF-11)

Adicionar suporte a `col.avatar` no renderizador de célula de coluna (próximo de onde hoje trata `col.boolean`/`col.date`/`col.badge`, por volta da linha 219-232):

```js
if (col.avatar) {
  return <Avatar foto={item[col.key]} nome={item[col.nomeField || 'nome_completo'] ?? item.nome} size="sm" />
}
```
(Importar `Avatar` no topo do arquivo, junto dos demais imports de `./`.)

### 7.4 `Usuarios.jsx`

Adicionar como primeira entrada do array `columns`:
```js
{ key: 'foto_url', label: '', avatar: true, nomeField: 'nome_completo' },
```

---

## 8. Fora do Escopo (explícito no pedido)

```
- Foto de clientes.Cliente e rh.Colaborador — helper (common/media.py) fica
  pronto, mas nenhum campo/endpoint novo nesses apps agora.
- Endpoint autenticado com X-Accel-Redirect para servir foto de terceiro
  (dado pessoal protegido) — só relevante quando Cliente/Colaborador
  ganharem foto; a foto do próprio usuário logado (escopo desta
  manutenção) segue servida por /media/ aberto, igual aos demais
  FileField já em produção (comprovante, arquivo).
- Admin remover/trocar foto de OUTRO usuário pela tela de Usuários — hoje
  só o próprio usuário altera a própria foto (RN-01).
- Upload de foto arrastando (drag-and-drop) — só input de arquivo padrão.
```

---

## 9. Critérios de Aceite (mapeando a validação pedida)

```
CA-01 - Enviar JPG de celular com EXIF de rotação + GPS → arquivo salvo
        sai "em pé" (orientação correta), 256x256, sem bloco EXIF algum.
CA-02 - Enviar PDF renomeado .jpg → 400, com mensagem amigável, User.foto
        permanece vazio (ou com o valor anterior, se já tinha um).
CA-03 - Trocar a foto apaga o arquivo antigo do storage configurado
        (local ou S3) — confirmar via default_storage.exists().
CA-04 - Recriar o container do backend (docker compose ... --force-
        recreate backend) e a foto enviada antes continua acessível
        (volume media_volume da Manutenção #71 — zero trabalho adicional
        de infra aqui, só confirmar que não regride).
CA-05 - Avatar aparece no Header após recarregar a página (GET /me/
        trazendo foto_url) E imediatamente após salvar/remover, sem
        precisar recarregar (RF-10).
CA-06 - Enviar arquivo > 5 MB → 400 antes de qualquer tentativa de
        decodificação Pillow.
CA-07 - DELETE em usuário sem foto → 200, sem erro, foto_url: null.
CA-08 - Tela de Usuários mostra avatar (foto ou inicial) de cada usuário
        na listagem.
CA-09 - Exportação LGPD (Manutenção 66, /clientes/{id}/exportar/) de um
        Cliente com Portal vinculado a um User com foto → JSON/PDF
        contém foto_url na seção do Portal.
CA-10 - Sem token (Authorization ausente) → 401 em POST/DELETE
        /me/foto/.
CA-11 - 0 migrations pendentes pós-deploy (makemigrations --check
        --dry-run limpo) e 0 regressão nos testes já existentes (533+
        testes da Manutenção #69/#71 continuam passando).
```

---

## 10. Observações para Forge/Loom/Sentinel/Pilot

- **Não repetir o padrão de bug encontrado na Manutenção #71** (achado crítico pré-deploy do Pilot): antes de QUALQUER `docker compose ... up --force-recreate backend` em produção durante esta manutenção, confirmar se já existe foto de usuário real gravada na camada do container atual (não deveria, já que `/app/media` já é volume desde #71 — mas é o tipo de checagem que vale repetir sempre que a entidade de mídia mudar).
- Rota correta é **`/api/v1/accounts/me/foto/`**, não `/api/v1/auth/...` (ver contexto item 5) — isso é correção de nomenclatura do pedido, não uma pergunta em aberto; não é necessário parar e perguntar ao cliente/Luiz Eduardo por isso.
- `UserAdminSerializer` também precisa de `foto_url` (ver seção 6.5) — o pedido só citou `UserSerializer` explicitamente, mas sem isso o CA-08 (avatar na tela de Usuários) não fecha, porque aquela tela consome o endpoint de admin, não o `/me/`.
- Pillow, Pillow-related imports e `STORAGES`/`STORAGE_BACKEND` já existem (Manutenção #71) — nenhuma variável de ambiente nova, nenhuma dependência nova a adicionar em `requirements.txt`.
