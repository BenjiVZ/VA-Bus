"""
Conexión con la pasarela de pagos R4 Conecta (Mibanco).

Implementa el flujo de Débito Inmediato (OTP):
    GenerarOtp -> DebitoInmediato -> (si AC00) ConsultarOperaciones

Autenticación (por cada request):
    - Header `Commerce`: token único del comercio (settings.R4_COMMERCE_TOKEN).
    - Header `Authorization`: HMAC-SHA256 (hex) de una concatenación de campos
      específica por método, usando el token Commerce como llave.

NOTA sobre la firma: el banco define la firma como HMAC de los campos
"concatenados" (ej. "Banco + Monto + Telefono + Cedula"). Aquí se interpreta
como concatenación DIRECTA (sin separadores) y con el `Monto` ya formateado a
"x.xx". Si el banco esperara otro formato, se ajusta en `firmar()` / `_fmt_monto()`.
"""
import hmac
import hashlib
import json
import logging
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

import requests
from django.conf import settings

logger = logging.getLogger('r4conecta')


# ── Helpers para enmascarar datos sensibles en los logs ──

def _mask(valor: str, visibles: int = 2) -> str:
    """Deja visibles los primeros/últimos chars y enmascara el medio."""
    s = str(valor or '')
    if len(s) <= visibles * 2:
        return '***'
    return f'{s[:visibles]}***{s[-visibles:]}'


def _redact_payload(payload: dict) -> dict:
    """Copia del payload con el OTP enmascarado (no se loguea el OTP completo)."""
    d = dict(payload)
    if d.get('OTP'):
        d['OTP'] = _mask(d['OTP'])
    return d


class R4Error(Exception):
    """Error al comunicarse con R4 Conecta o configuración faltante."""

    def __init__(self, message, code=None):
        super().__init__(message)
        self.message = message
        self.code = code


# ── Configuración ──

def _commerce_token() -> str:
    token = getattr(settings, 'R4_COMMERCE_TOKEN', '') or ''
    if not token:
        raise R4Error('R4_COMMERCE_TOKEN no está configurado en el entorno.')
    return token


def _base_url() -> str:
    return getattr(settings, 'R4_BASE_URL', 'https://r4conecta.mibanco.com.ve').rstrip('/')


def _timeout() -> int:
    return int(getattr(settings, 'R4_TIMEOUT', 20))


# ── Helpers de firma / formato ──

def _fmt_monto(value) -> str:
    """Normaliza el monto a string con 2 decimales y punto: '50.00'.

    Acepta coma decimal ('50,00') y espacios. Si no es un número válido o no es
    positivo, lanza R4Error (en vez de reventar con InvalidOperation -> 500).
    """
    try:
        d = Decimal(str(value).strip().replace(',', '.'))
    except (InvalidOperation, ValueError):
        raise R4Error(f'Monto inválido: {value!r}. Escribe un número como 50.00')
    if d <= 0:
        raise R4Error('El monto debe ser mayor que 0.')
    return str(d.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))


def firmar(mensaje: str) -> str:
    """HMAC-SHA256 (hex) del mensaje usando el token Commerce como llave."""
    key = _commerce_token().encode('utf-8')
    return hmac.new(key, mensaje.encode('utf-8'), hashlib.sha256).hexdigest()


# ── Cliente HTTP ──

def _post(path: str, payload: dict, authorization: str) -> dict:
    """POST autenticado a R4 Conecta. Devuelve el JSON o lanza R4Error."""
    url = f'{_base_url()}{path}'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': authorization,
        'Commerce': _commerce_token(),
    }

    # ── Log del request (token y OTP enmascarados) ──
    logger.info('REQUEST  POST %s', url)
    logger.info('  header Commerce: %s', _mask(_commerce_token(), 4))
    logger.info('  header Authorization (HMAC hex): %s', authorization)
    logger.info('  body: %s', json.dumps(_redact_payload(payload), ensure_ascii=False))

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=_timeout())
    except requests.exceptions.RequestException as e:
        logger.error('R4 %s: error de conexión: %s', path, e)
        raise R4Error(f'No se pudo contactar al banco: {e}')

    # El banco puede devolver códigos de negocio con HTTP 200 o con 4xx;
    # intentamos parsear JSON en cualquier caso para no perder el detalle.
    try:
        data = resp.json()
    except ValueError:
        # Respuesta no-JSON (típico de un bloqueo de IP/dominio en el borde/WAF).
        cuerpo = (resp.text or '').strip().replace('\n', ' ')[:300]
        servidor = resp.headers.get('Server', '')
        logger.error('R4 %s: respuesta no-JSON (HTTP %s) Server=%s body=%s',
                     path, resp.status_code, servidor, cuerpo)
        detalle = f' [Server: {servidor}]' if servidor else ''
        raise R4Error(
            f'El banco rechazó la petición (HTTP {resp.status_code}).{detalle} '
            f'Probablemente tu IP/dominio no está autorizado. Respuesta: {cuerpo}',
            code=str(resp.status_code))

    logger.info('RESPONSE %s | HTTP %s | %s', path, resp.status_code,
                json.dumps(data, ensure_ascii=False))

    if resp.status_code >= 500:
        logger.error('R4 %s: HTTP %s %s', path, resp.status_code, data)
        raise R4Error(f'Error del banco (HTTP {resp.status_code}).', code=str(data.get('code', '')))

    return data


# ── Métodos del API ──

def generar_otp(banco: str, monto, telefono: str, cedula: str) -> dict:
    """Solicita al banco que genere y envíe un OTP al cliente. Espera code '202'."""
    monto = _fmt_monto(monto)
    mensaje = f'{banco}{monto}{telefono}{cedula}'
    logger.info('GenerarOtp | firma sobre (Banco+Monto+Telefono+Cedula): %s', mensaje)
    auth = firmar(mensaje)
    payload = {'Banco': banco, 'Monto': monto, 'Telefono': telefono, 'Cedula': cedula}
    return _post('/GenerarOtp', payload, auth)


def debito_inmediato(banco: str, monto, telefono: str, cedula: str,
                     nombre: str, otp: str, concepto: str) -> dict:
    """Completa el débito inmediato con el OTP. Aprobado = code 'ACCP'."""
    monto = _fmt_monto(monto)
    mensaje = f'{banco}{cedula}{telefono}{monto}{otp}'
    logger.info('DebitoInmediato | firma sobre (Banco+Cedula+Telefono+Monto+OTP): %s',
                f'{banco}{cedula}{telefono}{monto}{_mask(otp)}')
    auth = firmar(mensaje)
    payload = {
        'Banco': banco, 'Monto': monto, 'Telefono': telefono, 'Cedula': cedula,
        'Nombre': nombre, 'OTP': otp, 'Concepto': concepto,
    }
    return _post('/DebitoInmediato', payload, auth)


def consultar_operacion(operacion_id: str) -> dict:
    """Consulta el estado final de una operación (cuando débito devolvió AC00)."""
    auth = firmar(operacion_id)
    return _post('/ConsultarOperaciones', {'Id': operacion_id}, auth)
