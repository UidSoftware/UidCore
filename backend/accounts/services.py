import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode


def enviar_primeiro_acesso(usuario):
    """
    Gera o link de "definir senha" (token de uso unico, expira em 24h —
    ver PASSWORD_RESET_TIMEOUT) e envia por email. Reaproveitada pela
    SolicitarAcessoView (API, botao futuro) e pela action do Django admin
    (unico ponto de disparo hoje, ja que o UidCore nao tem tela de
    Usuarios no frontend ainda) -- nunca duplicar essa logica nos dois
    lugares.
    """
    uid = urlsafe_base64_encode(force_bytes(usuario.pk))
    token = default_token_generator.make_token(usuario)
    link = f'{settings.FRONTEND_URL}/definir-senha/?uid={uid}&token={token}'

    corpo_html = f"""
    <div style="font-family:sans-serif;max-width:480px;margin:0 auto;padding:32px;background:#0a0e1a;color:#f1f5f9;border-radius:12px;">
      <h2 style="color:#7c3aed;margin-bottom:8px;">UidCore</h2>
      <p style="margin-bottom:24px;color:#94a3b8;">Acesso ao sistema</p>
      <p>Ola, <strong>{usuario.nome_completo}</strong>!</p>
      <p>Voce recebeu acesso ao sistema da <strong>Uid Software</strong>.<br>
      Clique no botao abaixo para definir sua senha e comecar a usar.</p>
      <a href="{link}" style="display:inline-block;margin:24px 0;padding:12px 28px;background:#7c3aed;color:#fff;border-radius:8px;text-decoration:none;font-weight:600;">
        Definir minha senha
      </a>
      <p style="font-size:12px;color:#64748b;">
        Link valido por 24 horas. Se nao solicitou, ignore este email.<br><br>
        <a href="{link}" style="color:#64748b;word-break:break-all;">{link}</a>
      </p>
    </div>
    """

    enviar_email_sistema(usuario.email, 'Acesso ao UidCore — defina sua senha', corpo_html)


def enviar_email_sistema(destinatario, assunto, corpo_html):
    """Envia email usando a conta de sistema configurada em settings (mesmo padrao do SystemD)."""
    email_conta = settings.SYSTEM_EMAIL_CONTA
    email_senha = settings.SYSTEM_EMAIL_SENHA
    if not email_senha:
        raise Exception('SYSTEM_EMAIL_SENHA nao configurada no .env')

    msg = MIMEMultipart('alternative')
    msg['From'] = email_conta
    msg['To'] = destinatario
    msg['Subject'] = assunto
    msg.attach(MIMEText(corpo_html, 'html', 'utf-8'))

    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    with smtplib.SMTP(settings.SMTP_HOST, int(settings.SMTP_PORT), timeout=10) as server:
        server.ehlo()
        server.starttls(context=context)
        server.login(email_conta, email_senha)
        server.sendmail(email_conta, [destinatario], msg.as_string())
