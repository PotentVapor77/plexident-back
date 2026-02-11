"""
Django settings for config project.
Configuración optimizada para desarrollo y producción.
"""

from pathlib import Path
import os
from datetime import timedelta
from dotenv import load_dotenv 
from corsheaders.defaults import default_headers
# Build paths
BASE_DIR = Path(__file__).resolve().parent.parent

# Cargar variables de entorno
load_dotenv(BASE_DIR / '.env')

# ============================================================================
# SECURITY SETTINGS
# ============================================================================

SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-CHANGE-THIS-IN-PRODUCTION')

DEBUG = os.getenv('DEBUG', 'False') == 'True'

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')
ALLOWED_HOSTS.append('.awsapprunner.com') 
# ============================================================================
# STORAGE CONFIGURATION
# ============================================================================

STORAGE_BACKEND = os.getenv('STORAGE_BACKEND', 'minio')
# Configuración común
AWS_STORAGE_BUCKET_NAME = os.getenv('AWS_STORAGE_BUCKET_NAME', 'plexident-clinical-files')
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID', 'minioadmin')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY', 'minioadmin')

if STORAGE_BACKEND == 's3':
    # AWS S3 Configuration (Producción)
    AWS_S3_REGION_NAME = os.getenv('AWS_S3_REGION_NAME', 'us-east-1')
    AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'
    AWS_DEFAULT_ACL = 'private'
    AWS_S3_OBJECT_PARAMETERS = {
        'CacheControl': 'max-age=86400',
    }
    AWS_S3_FILE_OVERWRITE = False
    AWS_QUERYSTRING_AUTH = True
    AWS_QUERYSTRING_EXPIRE = 3600  # 1 hora
    # Configurar backend de almacenamiento
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    
elif STORAGE_BACKEND == 'minio':
    # MinIO Configuration (Desarrollo local)
    MINIO_ENDPOINT_URL = os.getenv('MINIO_ENDPOINT_URL', 'http://localhost:9000')
    AWS_S3_ENDPOINT_URL = MINIO_ENDPOINT_URL
    AWS_S3_USE_SSL = False
    AWS_S3_REGION_NAME = 'us-east-1'  # MinIO requiere una región aunque sea fake
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

else:
    # Fallback a sistema de archivos local
    MEDIA_URL = '/media/'
    MEDIA_ROOT = BASE_DIR / 'media'

# ============================================================================
# APPLICATION DEFINITION
# ============================================================================

INSTALLED_APPS = [
    # Django apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    
    # Third party apps
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'django_filters', 
    'django_currentuser',
    'django_extensions',
    
    # Local apps
    'api',
    'authentication',
    'api.users.apps.UsersConfig',
    'api.odontogram.apps.OdontogramConfig',
    'api.patients.apps.PatientsConfig',
    'api.appointment.apps.AppointmentConfig',
    'api.clinical_records.apps.ClinicalRecordsConfig',
    'api.clinical_files.apps.ClinicalFilesConfig',
    # AWS S3 Storage
    'storages',
    'api.dashboard.apps.DashboardConfig',
    'api.parameters.apps.ParametersConfig',
    
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',  
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'authentication.middleware.CSRFExemptMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_currentuser.middleware.ThreadLocalUserMiddleware',
    'authentication.middleware.LoginRateLimitMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / "templates"],
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

# ============================================================================
# DATABASE
# ============================================================================

load_dotenv() 

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST'),
        'PORT': os.getenv('DB_PORT'),
    }
}
# ============================================================================
# PASSWORD VALIDATION
# ============================================================================

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
]

# ============================================================================
# INTERNATIONALIZATION
# ============================================================================

LANGUAGE_CODE = 'es-ec'
TIME_ZONE = 'America/Guayaquil'
USE_I18N = True
USE_TZ = True

# ============================================================================
# STATIC FILES
# ============================================================================

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ============================================================================
# DEFAULT SETTINGS
# ============================================================================

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
AUTH_USER_MODEL = 'users.Usuario'

AUTHENTICATION_BACKENDS = [
    'authentication.backends.UsuarioAuthBackend', 
    'django.contrib.auth.backends.ModelBackend', 
]

# ============================================================================
# REST FRAMEWORK CONFIGURATION
# ============================================================================

REST_FRAMEWORK = {

     # Renderer personalizado - Formatea TODAS las respuestas automáticamente

    'DEFAULT_RENDERER_CLASSES': [
        'api.utils.renderers.StandardizedJSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],

    #  Exception handler personalizado - Maneja TODOS los errores
    'EXCEPTION_HANDLER': 'api.utils.exception_handlers.custom_exception_handler',
     # Autenticación
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.FormParser',
        'rest_framework.parsers.MultiPartParser',
    ],
    
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'authentication.jwt_cookie_authentication.JWTCookieAuthentication',
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        #'rest_framework.authentication.SessionAuthentication',
    ],
    
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    
    'EXCEPTION_HANDLER': 'api.utils.exception_handlers.custom_exception_handler',
    
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
    
    'DATETIME_FORMAT': '%Y-%m-%d %H:%M:%S',
    'DATE_FORMAT': '%Y-%m-%d',
    'TIME_FORMAT': '%H:%M:%S',
    
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour'
    },
}

# ============================================================================
# SIMPLE JWT CONFIGURATION
# ============================================================================

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    
    'AUTH_COOKIE': 'access_token',
    'AUTH_COOKIE_REFRESH': 'refresh_token',
    'AUTH_COOKIE_SECURE': False,
    'AUTH_COOKIE_HTTP_ONLY': True,
    'AUTH_COOKIE_SAMESITE': 'Lax',
    'AUTH_COOKIE_PATH': '/',
    'AUTH_COOKIE_DOMAIN': None,
    
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'TOKEN_TYPE_CLAIM': 'token_type',
    'JTI_CLAIM': 'jti',
    
    'SLIDING_TOKEN_REFRESH_EXP_CLAIM': 'refresh_exp',
    'SLIDING_TOKEN_LIFETIME': timedelta(minutes=5),
    'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=1),
}

# ============================================================================
# CORS Y CSRF CONFIGURATION - ✅ CORREGIDO
# ============================================================================

if DEBUG:
    # ✅ DESARROLLO: Configuración permisiva
    CORS_ALLOWED_ORIGINS = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        
    ]
    
    # ✅ CSRF: Orígenes confiables
    CSRF_TRUSTED_ORIGINS = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    
    CORS_ALLOW_CREDENTIALS = True
    
    # ✅ Cookies en desarrollo (HTTP sin SSL)
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
    SESSION_COOKIE_SAMESITE = 'Lax'
    CSRF_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_HTTPONLY = True
    CSRF_COOKIE_HTTPONLY = False  # ✅ False para que JS pueda leer el token CSRF si es necesario
    
else:
    # ✅ PRODUCCIÓN: Solo dominios específicos
    CORS_ALLOWED_ORIGINS = os.getenv(
        'CORS_ALLOWED_ORIGINS',
        'https://tudominio.com,https://www.tudominio.com'
    ).split(',')
    
    CSRF_TRUSTED_ORIGINS = os.getenv(
        'CSRF_TRUSTED_ORIGINS',
        'https://tudominio.com,https://www.tudominio.com'
    ).split(',')
    
    CORS_ALLOW_CREDENTIALS = True
    
    # ✅ Cookies seguras en producción
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SAMESITE = 'None'  # Para cross-site
    CSRF_COOKIE_SAMESITE = 'None'
    SESSION_COOKIE_HTTPONLY = True
    CSRF_COOKIE_HTTPONLY = True

# ✅ Headers permitidos (común para dev y prod)
CORS_ALLOW_HEADERS = list(default_headers) + [
    'set-cookie',
    'x-csrftoken',
]

CORS_EXPOSE_HEADERS = [
    'set-cookie',
]

# ✅ Métodos HTTP permitidos
CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

# ✅ Cache de preflight requests
CORS_PREFLIGHT_MAX_AGE = 86400  # 24 horas
# ============================================================================
# 🔥 SEPARACIÓN DE COOKIES: ADMIN vs API (NUEVO)
# ============================================================================

# ✅ Cookie de sesión SOLO para Django Admin
SESSION_COOKIE_NAME = 'admin_sessionid'  # Nombre único para admin
SESSION_COOKIE_PATH = '/admin/'          # Solo funciona en /admin

# ✅ CSRF de admin separado
CSRF_COOKIE_NAME = 'admin_csrftoken'    # Nombre único para CSRF de admin
CSRF_COOKIE_PATH = '/admin/'
# En producción, podrías agregar:
# CSRF_COOKIE_PATH = '/admin/'           # Descomentar si tienes problemas

# ============================================================================
# CACHE CONFIGURATION
# ============================================================================

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
        'TIMEOUT': 300,
        'OPTIONS': {
            'MAX_ENTRIES': 1000
        }
    }
}

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '[{levelname}] {message}',
            'style': '{',
        },
    },
    
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
            'stream': 'ext://sys.stdout',
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'django.log',
            'maxBytes': 1024 * 1024 * 10,
            'backupCount': 5,
            'formatter': 'verbose',
            'encoding': 'utf-8',
            'delay': True,
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'errors.log',
            'maxBytes': 1024 * 1024 * 10,
            'backupCount': 5,
            'formatter': 'verbose',
            'encoding': 'utf-8',
        },
    },
    
    'loggers': {
        '': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
        },
        'django': {
            'handlers': ['console', 'file', 'error_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['error_file'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': False,
        },
        'api': {
            'handlers': ['console', 'file', 'error_file'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
        'authentication': {
            'handlers': ['console', 'file', 'error_file'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
        'users': {
            'handlers': ['console', 'file', 'error_file'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
    },
}

# ============================================================================
# SECURITY SETTINGS (Production)
# ============================================================================

if not DEBUG:
    SECURE_SSL_REDIRECT = False
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# ============================================================================
# EMAIL SETTINGS
# ============================================================================

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
# URL del frontend para enlaces en emails
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True") == "True"
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
DEFAULT_FROM_EMAIL = os.getenv(
    "DEFAULT_FROM_EMAIL",
    f"FamySALUD <{EMAIL_HOST_USER}>"
)

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")


# CONFIGURACIÓN DE RECORDATORIOS
RECORDATORIO_TIPO_DEFAULT = "EMAIL" 
RECORDATORIO_HORAS_ANTES = 24
RECORDATORIO_ENVIAR_A = "AMBOS"  

# ============================================================================
# S3 AWS CONFIGURATION
# ============================================================================

