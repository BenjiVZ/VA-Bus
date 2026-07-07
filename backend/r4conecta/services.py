import hashlib
import hmac
import logging
import requests
from decimal import Decimal
from django.conf import settings

logger = logging.getLogger("r4conecta")


class R4Error(Exception):
    """Excepción para errores de R4 Conecta."""
    def __init__(self, code, message):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


def _mask(value, prefix_len=2, suffix_len=2):
    """Enmascara un valor mostrando solo los primeros y últimos caracteres."""
    s = str(value)
    if len(s) <= prefix_len + suffix_len:
        return "*" * len(s)
    return s[:prefix_len] + "*" * (len(s) - prefix_len - suffix_len) + s[-suffix_len:]


def firmar(mensaje):
    """Genera un HMAC-SHA256 hex con el token Commerce como clave."""
    token = settings.R4_COMMERCE_TOKEN
    if not token:
        raise ValueError("R4_COMMERCE_TOKEN no está configurado")
    return hmac.new(
        token.encode(),
        mensaje.encode(),
        hashlib.sha256
    ).hexdigest()


def _fmt_monto(v):
    """Formatea un Decimal o número a 'x.xx' para la firma y request."""
    if isinstance(v, Decimal):
        return f"{v:.2f}"
    return f"{float(v):.2f}"


def _post(path, payload, authorization):
    """
    POST a R4 Conecta con manejo de excepciones.
    
    Returns:
        dict: La respuesta JSON del banco
    
    Raises:
        R4Error: Si hay error de conexión o respuesta del banco
    """
    url = f"{settings.R4_BASE_URL}{path}"
    headers = {
        "Content-Type": "application/json",
        "Commerce": settings.R4_COMMERCE_TOKEN,
        "Authorization": authorization,
    }
    
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=settings.R4_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"R4 request error to {path}: {str(e)}")
        raise R4Error("999", f"Error de conexión: {str(e)}")


def generar_otp(banco, monto, telefono, cedula):
    """
    Genera un OTP en Mibanco.
    
    Args:
        banco: Código de 4 dígitos (ej: "0192")
        monto: Decimal (ej: Decimal("50.00"))
        telefono: Teléfono en formato 11 dígitos
        cedula: Cédula (ej: "V12345678")
    
    Returns:
        dict: {"code", "message", "id", ...}
    
    Raises:
        R4Error
    """
    monto_str = _fmt_monto(monto)
    mensaje = f"{banco}{monto_str}{telefono}{cedula}"
    firma = firmar(mensaje)
    
    payload = {
        "Banco": banco,
        "Monto": monto_str,
        "Telefono": telefono,
        "Cedula": cedula,
    }
    
    logger.info(f"GenerarOtp: banco={banco}, monto={monto_str}, telefono={_mask(telefono)}, cedula={_mask(cedula)}")
    
    respuesta = _post("/GenerarOtp", payload, firma)
    logger.info(f"GenerarOtp respuesta: code={respuesta.get('code')}, message={respuesta.get('message')}")
    return respuesta


def debito_inmediato(banco, cedula, telefono, monto, otp, nombre, concepto="pago"):
    """
    Realiza el débito inmediato en Mibanco.
    
    Args:
        banco: Código de 4 dígitos
        cedula: Cédula
        telefono: Teléfono
        monto: Decimal
        otp: Código OTP (8 dígitos)
        nombre: Nombre del titular
        concepto: Concepto de la transacción (máx 30 chars)
    
    Returns:
        dict: {"code", "message", "id", ...}
    
    Raises:
        R4Error
    """
    monto_str = _fmt_monto(monto)
    mensaje = f"{banco}{cedula}{telefono}{monto_str}{otp}"
    firma = firmar(mensaje)
    
    payload = {
        "Banco": banco,
        "Cedula": cedula,
        "Telefono": telefono,
        "Monto": monto_str,
        "OTP": otp,
        "Nombre": nombre,
        "Concepto": concepto[:30],
    }
    
    logger.info(f"DebitoInmediato: banco={banco}, cedula={_mask(cedula)}, telefono={_mask(telefono)}, monto={monto_str}, otp={_mask(otp)}")
    
    respuesta = _post("/DebitoInmediato", payload, firma)
    logger.info(f"DebitoInmediato respuesta: code={respuesta.get('code')}, message={respuesta.get('message')}, id={respuesta.get('id')}")
    return respuesta


def consultar_operacion(operacion_id):
    """
    Consulta el estado de una operación (AC00 → ACCP).
    
    Args:
        operacion_id: ID de operación del banco (numérico o string)
    
    Returns:
        dict: {"code", "message", "estado", ...}
    
    Raises:
        R4Error
    """
    mensaje = str(operacion_id)
    firma = firmar(mensaje)
    
    payload = {"Id": operacion_id}
    
    logger.info(f"ConsultarOperacion: id={operacion_id}")
    
    respuesta = _post("/ConsultarOperaciones", payload, firma)
    logger.info(f"ConsultarOperacion respuesta: code={respuesta.get('code')}, message={respuesta.get('message')}, estado={respuesta.get('estado')}")
    return respuesta
