"""Altas de cuentas del personal del back office.

Aquí NO se dan de alta pasajeros: esos se registran solos desde la web o la
app, y la taquilla vende sin abrirles cuenta (ver `pagos/caja_views.py`). Esta
pantalla existe para darle acceso al personal sin tener que entrar al admin de
Django.

La validación devuelve un diccionario campo → mensaje en vez de lanzar: así la
pantalla puede pintar el error al lado de cada casilla y devolver lo que la
persona ya había escrito, que rellenar el formulario dos veces molesta.
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email

Usuario = get_user_model()

# Qué puede hacer cada rol. `super` da acceso al admin de Django y a esta
# misma pantalla, así que un administrador puede crear más administradores.
ROLES = {
    'taquilla': {
        'etiqueta': 'Personal (taquilla)',
        'staff': True, 'super': False,
        'detalle': 'Entra al back office: caja, viajes, boletos, comprobantes y rutas.',
    },
    'admin': {
        'etiqueta': 'Administrador',
        'staff': True, 'super': True,
        'detalle': 'Todo lo anterior, más el admin de Django y dar de alta usuarios.',
    },
}

CAMPOS = ('usuario', 'nombre', 'apellido', 'email', 'cedula', 'telefono', 'rol')


def limpiar(post):
    """Los valores del formulario, sin espacios sobrantes. Sin contraseñas."""
    datos = {c: (post.get(c) or '').strip() for c in CAMPOS}
    datos['rol'] = datos['rol'] or 'taquilla'
    return datos


def validar(datos, clave, clave2):
    """Devuelve {campo: mensaje}. Vacío = se puede crear."""
    e = {}

    usuario = datos['usuario']
    if not usuario:
        e['usuario'] = 'Hace falta un nombre de usuario.'
    elif ' ' in usuario:
        e['usuario'] = 'El nombre de usuario no puede llevar espacios.'
    elif Usuario.objects.filter(username__iexact=usuario).exists():
        # iexact a propósito: en PostgreSQL «Maria» y «maria» son dos cuentas
        # distintas, y a la hora de entrar nadie recuerda cómo la escribió.
        e['usuario'] = 'Ya existe una cuenta con ese nombre de usuario.'

    if not datos['nombre']:
        e['nombre'] = 'Hace falta el nombre de la persona.'

    email = datos['email']
    if email:
        try:
            validate_email(email)
        except ValidationError:
            e['email'] = 'Ese correo no tiene forma de correo.'
        else:
            otro = Usuario.objects.filter(email__iexact=email).first()
            if otro:
                e['email'] = ('Ese correo ya lo usa la cuenta «%s». Los correos '
                              'repetidos rompen la recuperación de contraseña.'
                              % otro.username)

    if datos['rol'] not in ROLES:
        e['rol'] = 'Elige un rol de la lista.'

    if not clave:
        e['clave'] = 'Hace falta una contraseña.'
    elif clave != clave2:
        e['clave2'] = 'Las dos contraseñas no coinciden.'
    else:
        # Los mismos requisitos que el resto del sistema (settings).
        provisional = Usuario(username=usuario, first_name=datos['nombre'],
                              email=email)
        try:
            validate_password(clave, provisional)
        except ValidationError as err:
            e['clave'] = ' '.join(err.messages)

    return e


def crear(datos, clave):
    """Crea la cuenta. Asume que `validar` ya dio el visto bueno."""
    rol = ROLES[datos['rol']]
    usuario = Usuario(
        username=datos['usuario'],
        first_name=datos['nombre'],
        last_name=datos['apellido'],
        email=datos['email'],
        cedula=datos['cedula'] or None,
        telefono=datos['telefono'] or None,
        is_staff=rol['staff'],
        is_superuser=rol['super'],
        is_active=True,
        # La crea el personal, no hay que mandarle código de verificación.
        email_verificado=bool(datos['email']),
    )
    usuario.set_password(clave)
    usuario.save()
    return usuario


def rol_de(usuario):
    """Etiqueta del rol que tiene una cuenta ya creada."""
    if usuario.is_superuser:
        return ROLES['admin']['etiqueta']
    if usuario.is_staff:
        return ROLES['taquilla']['etiqueta']
    return 'Pasajero'


def listado():
    """Las cuentas del personal, las de siempre arriba del todo."""
    return (Usuario.objects
            .filter(is_staff=True)
            .order_by('-is_superuser', 'first_name', 'username'))
