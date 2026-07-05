"""
Email backend que envía por la API HTTPS de Brevo (puerto 443).

Por qué existe: DigitalOcean bloquea los puertos SMTP salientes (25/465/587)
del droplet — comprobado con scripts/probar_correos.py (Errno 101 en los 3).
La API HTTPS no puede ser bloqueada porque viaja por el mismo puerto que
cualquier página web.

Es un reemplazo transparente del backend SMTP: send_mail(), html_message,
EmailMessage con adjuntos (boleto PDF), cc/bcc… todo el código de la app
funciona sin cambios.

Activación (en el .env):
    BREVO_API_KEY=xkeysib-...
Si la clave no está definida, settings.py deja el backend SMTP normal.
"""
import base64
from email.utils import parseaddr

import requests
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

API_URL = 'https://api.brevo.com/v3/smtp/email'


class BrevoApiEmailBackend(BaseEmailBackend):

    def send_messages(self, email_messages):
        api_key = getattr(settings, 'BREVO_API_KEY', '')
        if not api_key:
            if not self.fail_silently:
                raise RuntimeError('BREVO_API_KEY no está configurada en el .env')
            return 0

        enviados = 0
        for msg in email_messages:
            try:
                resp = requests.post(
                    API_URL,
                    json=self._payload(msg),
                    headers={'api-key': api_key, 'content-type': 'application/json'},
                    timeout=getattr(settings, 'EMAIL_TIMEOUT', 15),
                )
                if resp.status_code in (200, 201):
                    enviados += 1
                elif not self.fail_silently:
                    raise RuntimeError(f'Brevo respondió {resp.status_code}: {resp.text[:300]}')
            except Exception:
                if not self.fail_silently:
                    raise
        return enviados

    @staticmethod
    def _payload(msg):
        nombre, direccion = parseaddr(msg.from_email or settings.DEFAULT_FROM_EMAIL)
        payload = {
            'sender': {'email': direccion} | ({'name': nombre} if nombre else {}),
            'to': [{'email': e} for e in msg.to],
            'subject': msg.subject,
            'textContent': msg.body or ' ',
        }

        # html_message de send_mail llega como "alternative" text/html
        for contenido, mimetype in getattr(msg, 'alternatives', []):
            if mimetype == 'text/html':
                payload['htmlContent'] = contenido

        adjuntos = []
        for att in msg.attachments:
            if isinstance(att, (tuple, list)) and len(att) == 3:
                nombre_arch, contenido, _mime = att
                if isinstance(contenido, str):
                    contenido = contenido.encode('utf-8')
                adjuntos.append({
                    'name': nombre_arch,
                    'content': base64.b64encode(contenido).decode('ascii'),
                })
        if adjuntos:
            payload['attachment'] = adjuntos

        if msg.cc:
            payload['cc'] = [{'email': e} for e in msg.cc]
        if msg.bcc:
            payload['bcc'] = [{'email': e} for e in msg.bcc]
        return payload
