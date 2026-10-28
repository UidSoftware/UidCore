"""
common/media.py — Manutencao #72.

Helper reaproveitavel de processamento de imagem de avatar/foto de perfil.
Hoje usado so por accounts.User (RF-02/RF-03), mas desenhado para
clientes.Cliente e rh.Colaborador reaproveitarem no futuro sem duplicar
logica (RN-08) — por isso esta funcao NUNCA importa nada de apps de
negocio (accounts, clientes, rh etc.), so bibliotecas (Pillow, Django
core).
"""
import uuid
from io import BytesIO

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image, ImageOps

TAMANHO_MAX_BYTES = 5 * 1024 * 1024  # 5 MB (RN-02)
LADO_PADRAO = 256


def processar_foto(arquivo, lado=LADO_PADRAO):
    """
    Recebe o UploadedFile do multipart (``request.FILES['foto']``) e
    devolve um ``ContentFile`` pronto para ``campo.save(conteudo.name,
    conteudo)``.

    Levanta ``django.core.exceptions.ValidationError`` (mensagem amigavel)
    quando:
    - o arquivo passa de 5 MB (RN-02 — checado ANTES de abrir com Pillow,
      para nao decodificar/alocar memoria de um arquivo que sera
      rejeitado de qualquer forma);
    - o conteudo nao decodifica como imagem de verdade (RN-03 — nunca
      confia em content_type nem na extensao do nome do arquivo; um PDF
      renomeado para .jpg cai aqui).

    O arquivo final:
    - tem a orientacao corrigida via EXIF (``ImageOps.exif_transpose``)
      ANTES do EXIF ser descartado (RN-04 — a unica informacao do EXIF
      aproveitada e a orientacao; GPS e qualquer outro dado some);
    - e recortado em quadrado central e redimensionado para
      ``lado``x``lado`` pixels;
    - e salvo em WEBP, com nome aleatorio (``<uuid4>.webp`` — RN-05, nunca
      derivado do id do usuario, email ou nome original do arquivo
      enviado).
    """
    if arquivo.size > TAMANHO_MAX_BYTES:
        raise ValidationError('Arquivo maior que 5 MB.')

    try:
        imagem = Image.open(arquivo)
        imagem = ImageOps.exif_transpose(imagem)
        imagem.load()  # forca decodificacao completa — rejeita arquivo que nao e imagem de verdade
    except Exception:
        # Pillow levanta tipos diferentes dependendo do que o arquivo
        # realmente e (UnidentifiedImageError, OSError, etc.) — o
        # resultado pro usuario final e sempre o mesmo 400 amigavel,
        # nunca distinguir o tipo de erro.
        raise ValidationError('Arquivo enviado não é uma imagem válida.')

    imagem = imagem.convert('RGB')
    largura, altura = imagem.size
    lado_corte = min(largura, altura)
    esquerda = (largura - lado_corte) // 2
    topo = (altura - lado_corte) // 2
    imagem = imagem.crop((esquerda, topo, esquerda + lado_corte, topo + lado_corte))
    imagem = imagem.resize((lado, lado), Image.LANCZOS)

    buffer = BytesIO()
    imagem.save(buffer, format='WEBP')  # sem exif= -> EXIF (inclusive GPS) nao vai pro arquivo final
    return ContentFile(buffer.getvalue(), name=f'{uuid.uuid4()}.webp')
