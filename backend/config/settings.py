"""
Django settings for VA-Bus project.
"""

from pathlib import Path
from datetime import timedelta
import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

_SECRET_KEY_DEV = 'django-insecure-va-bus-dev-key-change-in-production-2024'
SECRET_KEY = os.getenv('SECRET_KEY', _SECRET_KEY_DEV)

# Seguro por defecto: DEBUG=False salvo que el .env diga lo contrario.
# En LOCAL poné DEBUG=True en backend/.env para el modo desarrollo.
DEBUG = os.getenv('DEBUG', 'False') == 'True'

# En producción NO se permite arrancar con la SECRET_KEY de desarrollo: los JWT se
# firman con SECRET_KEY, y esa clave está en el repo → cualquiera podría falsificar
# tokens de admin. Si falta, fallar ruidosamente en vez de arrancar inseguro.
if not DEBUG and SECRET_KEY == _SECRET_KEY_DEV:
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured(
        'SECRET_KEY no está configurada. Definí SECRET_KEY en backend/.env antes de '
        'correr en producción (DEBUG=False).'
    )

# Local: '*'. En producción se restringe vía .env (ALLOWED_HOSTS=dominio,localhost).
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '*').split(',')

# Application definition
INSTALLED_APPS = [
    # 'daphne' debe ir PRIMERO para que runserver use el server ASGI
    # y soporte WebSockets en desarrollo. No afecta producción si arrancás con daphne directo.
    'daphne',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third party
    'rest_framework',
    'corsheaders',
    'channels',
    # Local apps
    'usuarios',
    'viajes',
    'reservas',
    'pagos',
    'api_externa',
    'r4conecta',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'viajes' / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# ── Channels (WebSockets) ──
# Dev: InMemoryChannelLayer no requiere Redis pero NO sirve para multi-worker.
# Prod: cambiar a channels_redis con 'BACKEND': 'channels_redis.core.RedisChannelLayer'.
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    },
}

# Database
# PostgreSQL si hay DB_HOST en el entorno (producción, p.ej. DigitalOcean
# managed); si no, SQLite (desarrollo local). Solo cambia por variables de .env.
if os.getenv('DB_HOST'):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('DB_NAME', 'defaultdb'),
            'USER': os.getenv('DB_USER', 'doadmin'),
            'PASSWORD': os.getenv('DB_PASSWORD', ''),
            'HOST': os.getenv('DB_HOST'),
            'PORT': os.getenv('DB_PORT', '25060'),
            'OPTIONS': {'sslmode': os.getenv('DB_SSLMODE', 'require')},
            'CONN_MAX_AGE': 60,  # reusa conexiones (la DB administrada limita el total)
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
            'OPTIONS': {
                'timeout': 20,  # Espera hasta 20s si la DB está bloqueada
            },
        }
    }

# Custom User Model
AUTH_USER_MODEL = 'usuarios.Usuario'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'es-ve'
TIME_ZONE = 'America/Caracas'
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Media files (uploads)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ),
    # ── Throttling global (proteccion anti-DDoS) ──
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '60/minute',       # Usuarios no autenticados: 60 req/min
        'user': '120/minute',      # Usuarios autenticados: 120 req/min
        'login': '5/minute',       # Login: maximo 5 intentos/min
        'registro': '3/minute',    # Registro: maximo 3 cuentas/min
        'externo': '30/minute',    # API externa: 30 req/min
        'r4_otp': '10/minute',     # Generacion de OTP de pago: 10 req/min
    },
}

# JWT Settings
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=12),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
}

# CORS
# En local (DEBUG) se permite cualquier origen para comodidad. En producción, el
# frontend se sirve del MISMO dominio que el API (same-origin), así que por defecto
# no se habilita ningún origen cruzado; si hiciera falta, se listan por env.
if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True
else:
    CORS_ALLOW_ALL_ORIGINS = False
    CORS_ALLOWED_ORIGINS = [
        o.strip() for o in os.getenv('CORS_ALLOWED_ORIGINS', '').split(',') if o.strip()
    ]
CORS_ALLOW_CREDENTIALS = True

# CSRF — orígenes confiables para formularios POST (admin, etc.)
CSRF_TRUSTED_ORIGINS = [
    'https://ardvf.aplicacionesdamasco.com',
    'https://ardvb.aplicacionesdamasco.com',
    'https://*.masterslogic.com',
    'https://aerorutasdevenezuela.net',
    'https://*.aerorutasdevenezuela.net',
]

# Detrás del proxy de Cloudflare/nginx: confiar en el header que indica HTTPS,
# para que Django genere URLs https y las cookies seguras funcionen.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Email Configuration (Gmail SMTP)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# Host/puerto/cifrado ajustables desde el .env sin tocar código:
#   587 + STARTTLS (default)  ó  465 + EMAIL_USE_SSL=true
# Diagnóstico en el servidor: venv/bin/python scripts/probar_correos.py correo@destino
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_USE_SSL = os.getenv('EMAIL_USE_SSL', 'False').lower() in ('true', '1', 'yes')
EMAIL_USE_TLS = not EMAIL_USE_SSL  # mutuamente excluyentes
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
# El remitente debe coincidir con la cuenta Gmail que envía (EMAIL_HOST_USER);
# un dominio inexistente (noreply@aerorutas.com) hace que Gmail lo reescriba
# y que los filtros lo marquen como spam.
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'Aerorutas de Venezuela <aerorutasdevenezuela@gmail.com>')
# Si el SMTP no responde (p. ej. el proveedor bloquea el puerto saliente), el
# socket no debe colgar la petición: se corta a los N segundos.
EMAIL_TIMEOUT = int(os.getenv('EMAIL_TIMEOUT', '10'))

# ── Envío por API HTTPS (Brevo) ──
# DigitalOcean bloquea los puertos SMTP salientes del droplet (verificado con
# scripts/probar_correos.py), así que en producción el correo sale por la API
# HTTPS de Brevo (puerto 443, imbloqueable). Con solo definir BREVO_API_KEY en
# el .env se activa; sin ella, se usa el SMTP normal (útil en desarrollo).
BREVO_API_KEY = os.getenv('BREVO_API_KEY', '')
if BREVO_API_KEY:
    EMAIL_BACKEND = 'config.email_backend.BrevoApiEmailBackend'

# Verificación de email por código al registrarse. Hoy está DESACTIVADA porque el
# droplet no puede enviar correos (puerto SMTP saliente bloqueado). Para volver a
# exigirla, poné EMAIL_VERIFICATION_REQUIRED=true en el .env cuando el envío funcione.
EMAIL_VERIFICATION_REQUIRED = os.getenv('EMAIL_VERIFICATION_REQUIRED', 'False').lower() in ('true', '1', 'yes')

# ── Seguridad: Limite de tamaño de archivos (5MB) ──
DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024  # 5MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024   # 5MB

# ── Google OAuth ──
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID', '')

# ── API Externa (Sistema de Control) ──
EXTERNAL_API_KEY = os.getenv('EXTERNAL_API_KEY', '')

# ── R4 Conecta (Pasarela de pagos Mibanco) ──
R4_BASE_URL = os.getenv('R4_BASE_URL', 'https://r4conecta.mibanco.com.ve')
R4_COMMERCE_TOKEN = os.getenv('R4_COMMERCE_TOKEN', '')  # Token del comercio (Commerce)
R4_TIMEOUT = int(os.getenv('R4_TIMEOUT', '20'))

# Logging: que el logger 'r4conecta' escriba a consola (lo captura journalctl).
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'r4': {'format': '[%(asctime)s] R4 %(levelname)s %(message)s'},
    },
    'handlers': {
        'console': {'class': 'logging.StreamHandler', 'formatter': 'r4'},
    },
    'loggers': {
        'r4conecta': {'handlers': ['console'], 'level': 'INFO', 'propagate': False},
    },
}

# ── Aerorutas (Sistema de control externo: oficinas/rutas/puestos) ──
AERORUTAS_API_URL = os.getenv('AERORUTAS_API_URL', 'https://aerorutasdevenezuela.com/server/request.php')
AERORUTAS_API_TOKEN = os.getenv('AERORUTAS_API_TOKEN', '')
# Timeout corto: el backend corre en daphne de 1 hilo para vistas sync, así que una
# llamada externa lenta congela TODA la app. Mejor cortar rápido y mostrar error.
AERORUTAS_TIMEOUT = int(os.getenv('AERORUTAS_TIMEOUT', '8'))

# ── SQLite WAL mode para mejor concurrencia ──
from django.db.backends.signals import connection_created

def _activate_wal(sender, connection, **kwargs):
    if connection.vendor == 'sqlite':
        cursor = connection.cursor()
        cursor.execute('PRAGMA journal_mode=WAL;')
        cursor.execute('PRAGMA busy_timeout=20000;')

connection_created.connect(_activate_wal)
