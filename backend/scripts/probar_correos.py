"""
Diagnóstico completo del envío de correos — VA-Bus.

Prueba CADA método/capa por separado para ubicar exactamente dónde falla:
  1. Configuración cargada (.env)
  2. DNS del host SMTP
  3. Conectividad TCP a los puertos 587 / 465 / 25
  4. Handshake SMTP + STARTTLS + login (587)
  5. Handshake SMTP sobre SSL + login (465)
  6. send_mail simple      (como los códigos de verificación/reset)
  7. send_mail con HTML    (como el email de aprobación de pago)
  8. EmailMessage + adjunto (como el boleto PDF)
  9. Envío alternativo por 465/SSL (para saber si cambiar de puerto arregla)

Uso (desde backend/, con el venv activado o con su python directo):
    python scripts/probar_correos.py destino@correo.com

En el servidor:
    cd /opt/va-bus/backend && venv/bin/python scripts/probar_correos.py destino@correo.com
"""
import os
import smtplib
import socket
import ssl
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django  # noqa: E402
django.setup()

from django.conf import settings  # noqa: E402
from django.core.mail import EmailMessage, get_connection, send_mail  # noqa: E402

VERDE, ROJO, AMARILLO, FIN = '\033[92m', '\033[91m', '\033[93m', '\033[0m'
resultados = []  # (nombre, ok:bool|None, detalle)


def registrar(nombre, ok, detalle=''):
    resultados.append((nombre, ok, detalle))
    tag = f'{VERDE}PASS{FIN}' if ok else (f'{AMARILLO}SKIP{FIN}' if ok is None else f'{ROJO}FAIL{FIN}')
    print(f'  [{tag}] {nombre}' + (f' — {detalle}' if detalle else ''))


def main():
    if len(sys.argv) < 2 or '@' not in sys.argv[1]:
        print('Uso: python scripts/probar_correos.py destino@correo.com')
        sys.exit(1)
    destino = sys.argv[1]

    host = settings.EMAIL_HOST
    user = settings.EMAIL_HOST_USER
    pwd = settings.EMAIL_HOST_PASSWORD
    timeout = getattr(settings, 'EMAIL_TIMEOUT', 10)

    brevo_key = getattr(settings, 'BREVO_API_KEY', '')

    # ── 1. Configuración ─────────────────────────────────────────────
    print('\n═══ 1. Configuración cargada ═══')
    print(f'  EMAIL_BACKEND      = {settings.EMAIL_BACKEND}')
    print(f'  BREVO_API_KEY      = {"**** (" + str(len(brevo_key)) + " chars) → envío por API HTTPS" if brevo_key else "(no configurada → envío por SMTP)"}')
    print(f'  EMAIL_HOST         = {host}')
    print(f'  EMAIL_PORT         = {settings.EMAIL_PORT}')
    print(f'  EMAIL_USE_TLS      = {settings.EMAIL_USE_TLS}')
    print(f'  EMAIL_USE_SSL      = {getattr(settings, "EMAIL_USE_SSL", False)}')
    print(f'  EMAIL_HOST_USER    = {user or "(VACÍO ⚠️)"}')
    print(f'  EMAIL_HOST_PASSWORD= {"*" * 4 + f" ({len(pwd)} chars)" if pwd else "(VACÍA ⚠️)"}')
    print(f'  DEFAULT_FROM_EMAIL = {settings.DEFAULT_FROM_EMAIL}')
    print(f'  EMAIL_TIMEOUT      = {timeout}s')
    if brevo_key:
        registrar('Credenciales presentes (API Brevo)', True)
    else:
        registrar('Credenciales presentes en .env', bool(user and pwd),
                  '' if (user and pwd) else 'faltan EMAIL_HOST_USER/EMAIL_HOST_PASSWORD')
    if user and user not in settings.DEFAULT_FROM_EMAIL:
        print(f'  {AMARILLO}⚠️  DEFAULT_FROM_EMAIL no coincide con la cuenta Gmail; Gmail lo '
              f'reescribe y algunos filtros lo marcan como spam.{FIN}')

    # ── 2. DNS ───────────────────────────────────────────────────────
    print('\n═══ 2. Resolución DNS ═══')
    try:
        ip = socket.gethostbyname(host)
        registrar(f'DNS {host}', True, ip)
    except Exception as e:
        registrar(f'DNS {host}', False, str(e))
        return  # sin DNS no tiene sentido seguir

    # ── 3. TCP a cada puerto ─────────────────────────────────────────
    print('\n═══ 3. Conectividad TCP saliente ═══')
    puertos_ok = {}
    for puerto in (587, 465, 25):
        try:
            with socket.create_connection((host, puerto), timeout=8):
                puertos_ok[puerto] = True
                registrar(f'TCP {host}:{puerto}', True)
        except Exception as e:
            puertos_ok[puerto] = False
            registrar(f'TCP {host}:{puerto}', False, type(e).__name__)

    # ── 4. SMTP + STARTTLS + login (587) ─────────────────────────────
    print('\n═══ 4. SMTP 587 (STARTTLS + login) ═══')
    if puertos_ok.get(587) and user and pwd:
        try:
            with smtplib.SMTP(host, 587, timeout=timeout) as s:
                s.ehlo()
                s.starttls(context=ssl.create_default_context())
                s.ehlo()
                s.login(user, pwd)
            registrar('Login SMTP 587', True)
        except smtplib.SMTPAuthenticationError as e:
            registrar('Login SMTP 587', False,
                      f'AUTH rechazada ({e.smtp_code}): revisa que sea una App Password de Gmail')
        except Exception as e:
            registrar('Login SMTP 587', False, f'{type(e).__name__}: {e}')
    else:
        registrar('Login SMTP 587', None, 'sin TCP 587 o sin credenciales')

    # ── 5. SMTP sobre SSL + login (465) ──────────────────────────────
    print('\n═══ 5. SMTP 465 (SSL + login) ═══')
    if puertos_ok.get(465) and user and pwd:
        try:
            with smtplib.SMTP_SSL(host, 465, timeout=timeout,
                                  context=ssl.create_default_context()) as s:
                s.login(user, pwd)
            registrar('Login SMTP 465', True)
        except smtplib.SMTPAuthenticationError as e:
            registrar('Login SMTP 465', False,
                      f'AUTH rechazada ({e.smtp_code}): revisa que sea una App Password de Gmail')
        except Exception as e:
            registrar('Login SMTP 465', False, f'{type(e).__name__}: {e}')
    else:
        registrar('Login SMTP 465', None, 'sin TCP 465 o sin credenciales')

    # ── 6-8. Los tres métodos reales de la app ───────────────────────
    print(f'\n═══ 6. send_mail simple (códigos verificación/reset) → {destino} ═══')
    try:
        n = send_mail(
            subject='[QA VA-Bus] 1/3 send_mail simple',
            message='Prueba del método usado por los códigos de verificación y reset. Código de ejemplo: 123456',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[destino],
            fail_silently=False,
        )
        registrar('send_mail simple', n == 1)
    except Exception as e:
        registrar('send_mail simple', False, f'{type(e).__name__}: {e}')

    print(f'\n═══ 7. send_mail con HTML (aprobación de pago) → {destino} ═══')
    try:
        n = send_mail(
            subject='[QA VA-Bus] 2/3 send_mail HTML',
            message='Versión texto plano.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[destino],
            html_message='<div style="font-family:Arial"><h2>Prueba HTML ✅</h2>'
                         '<p>Método usado por el email de aprobación de pago.</p></div>',
            fail_silently=False,
        )
        registrar('send_mail HTML', n == 1)
    except Exception as e:
        registrar('send_mail HTML', False, f'{type(e).__name__}: {e}')

    print(f'\n═══ 8. EmailMessage + adjunto (boleto PDF) → {destino} ═══')
    try:
        em = EmailMessage(
            subject='[QA VA-Bus] 3/3 EmailMessage con adjunto',
            body='Método usado por el boleto PDF. Va un adjunto de prueba.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[destino],
        )
        em.attach('prueba.txt', b'Adjunto de prueba VA-Bus', 'text/plain')
        registrar('EmailMessage + adjunto', em.send() == 1)
    except Exception as e:
        registrar('EmailMessage + adjunto', False, f'{type(e).__name__}: {e}')

    # ── 9. Envío alternativo por 465/SSL ─────────────────────────────
    print(f'\n═══ 9. Envío alternativo por 465/SSL → {destino} ═══')
    if puertos_ok.get(465) and user and pwd:
        try:
            conn = get_connection(
                host=host, port=465, username=user, password=pwd,
                use_ssl=True, use_tls=False, timeout=timeout,
            )
            n = send_mail(
                subject='[QA VA-Bus] alt: envío por puerto 465/SSL',
                message='Si este llegó y los anteriores no, hay que cambiar EMAIL_PORT=465 y EMAIL_USE_SSL=true en el .env.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[destino],
                connection=conn,
                fail_silently=False,
            )
            registrar('Envío por 465/SSL', n == 1)
        except Exception as e:
            registrar('Envío por 465/SSL', False, f'{type(e).__name__}: {e}')
    else:
        registrar('Envío por 465/SSL', None, 'sin TCP 465 o sin credenciales')

    # ── Resumen + diagnóstico ────────────────────────────────────────
    print('\n' + '═' * 60)
    print('RESUMEN')
    print('═' * 60)
    for nombre, ok, detalle in resultados:
        tag = 'PASS' if ok else ('SKIP' if ok is None else 'FAIL')
        print(f'  {tag:4} | {nombre}' + (f' — {detalle}' if detalle else ''))

    print('\nDIAGNÓSTICO:')
    fallo = {n: ok for n, ok, _ in resultados}
    # Si los 3 métodos reales de la app enviaron, el correo FUNCIONA — los
    # tests TCP/SMTP solo importan para el backend SMTP.
    if all(fallo.get(k) for k in ('send_mail simple', 'send_mail HTML', 'EmailMessage + adjunto')):
        via = 'API HTTPS de Brevo' if brevo_key else 'SMTP'
        print(f'  → ✅ TODOS los métodos de envío funcionan (vía {via}). Revisa la bandeja')
        print(f'    (y spam) de {destino}: deben haber llegado 3 correos [QA VA-Bus].')
        print('    Si el problema era la verificación de registro, ya se puede activar:')
        print('       EMAIL_VERIFICATION_REQUIRED=true  en el .env + restart.')
    elif brevo_key:
        print('  → BREVO_API_KEY está configurada pero el envío falló. Revisa el detalle de')
        print('    los FAIL de arriba: 401 = clave inválida; 400 con "sender" = el remitente')
        print('    no está verificado en Brevo (Senders & IP → añade y confirma la cuenta).')
    elif not (user and pwd):
        print('  → Faltan credenciales en el .env. Configura EMAIL_HOST_USER y')
        print('    EMAIL_HOST_PASSWORD (App Password de Gmail, no la contraseña normal).')
    elif not puertos_ok.get(587) and not puertos_ok.get(465):
        print('  → El proveedor BLOQUEA los puertos SMTP salientes (587 y 465).')
        print('    Opciones: (a) pedir a DigitalOcean el desbloqueo SMTP (ticket de soporte),')
        print('    (b) migrar a un servicio de email por API HTTPS (Brevo/Resend/SendGrid),')
        print('        que nunca es bloqueado porque usa el puerto 443.')
    elif fallo.get('Login SMTP 587') is False and fallo.get('Login SMTP 465') is False:
        print('  → Hay red pero Gmail RECHAZA el login: la EMAIL_HOST_PASSWORD debe ser una')
        print('    App Password (Google Account → Seguridad → Verificación en 2 pasos →')
        print('    Contraseñas de aplicaciones). La contraseña normal de la cuenta NO sirve.')
    elif fallo.get('send_mail simple') is False and fallo.get('Envío por 465/SSL'):
        print('  → El 587 falla pero el 465/SSL funciona. En el .env del servidor pon:')
        print('       EMAIL_PORT=465')
        print('       EMAIL_USE_SSL=true')
        print('    y reinicia: systemctl restart vabus-backend')
    else:
        print('  → Falla parcial: revisa los FAIL de arriba (el detalle indica la capa exacta).')
    print()


if __name__ == '__main__':
    main()
