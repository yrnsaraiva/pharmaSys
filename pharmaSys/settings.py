from pathlib import Path
import os
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

# ==========================
# SECURITY
# ==========================
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-o%cf1_-^p95dr-aupdnimbg_-k@xugqx70f79_##63h9&ox1!y')
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# DEBUG deve ser False em produção
DEBUG = os.environ.get('DEBUG', 'True').lower() == 'true'

# Hosts permitidos - mais seguro para produção
ALLOWED_HOSTS = [
    'pharmasys-production.up.railway.app',
    'localhost',
    '127.0.0.1',
]

# Se DEBUG=True, permite todos os hosts para desenvolvimento
if DEBUG:
    ALLOWED_HOSTS = ['*']

# Permitir o domínio do seu site para POSTs
CSRF_TRUSTED_ORIGINS = [
    'https://pharmasys-production.up.railway.app',
    'https://*.railway.app',
]

# ==========================
# SESSION SETTINGS
# ==========================
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_AGE = 900  # 15 minutos
SESSION_SAVE_EVERY_REQUEST = True

# ==========================
# INSTALLED APPS
# ==========================
INSTALLED_APPS = [
    #'import_export',
    'django.contrib.admin',
    'django.contrib.humanize',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    "core.apps.CoreConfig",
    "estoque.apps.EstoqueConfig",
    "clientes.apps.ClientesConfig",
    "vendas.apps.VendasConfig",
    "productos.apps.ProductosConfig",
    "fornecedores.apps.FornecedoresConfig",
    "usuarios.apps.UsuariosConfig",
    'relatorios.apps.RelatoriosConfig',
]

# ==========================
# MIDDLEWARE
# ==========================
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'pharmaSys.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.request_is_secure',
            ],
        },
    },
]

WSGI_APPLICATION = 'pharmaSys.wsgi.application'

# ==========================
# DATABASE CONFIGURATION
# ==========================
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Configuração do PostgreSQL para Railway
POSTGRES_LOCALLY = False  # Mude para True se quiser PostgreSQL local

# No Railway, sempre usa PostgreSQL
if os.environ.get('RAILWAY_ENVIRONMENT') or not DEBUG or POSTGRES_LOCALLY:
    DATABASES['default'] = dj_database_url.parse(
        'postgresql://postgres:aasiGbCkQfTCRDfiMXdyQdNfXGHYynTw@maglev.proxy.rlwy.net:41864/railway'
    )
    
    # Otimizações para PostgreSQL
    DATABASES['default']['CONN_MAX_AGE'] = 600
    DATABASES['default']['ENGINE'] = 'django.db.backends.postgresql'

# ==========================
# PASSWORD VALIDATION
# ==========================
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# ==========================
# INTERNATIONALIZATION
# ==========================
LANGUAGE_CODE = 'pt-pt'  # Mudado para português
TIME_ZONE = 'Africa/Maputo'
USE_I18N = True
USE_TZ = True

# ==========================
# STATIC FILES
# ==========================
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# WhiteNoise configuration
STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'

# ==========================
# MEDIA FILES (se necessário)
# ==========================
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ==========================
# AUTHENTICATION REDIRECTS
# ==========================
LOGIN_URL = '/usuarios/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/usuarios/login/'

# ==========================
# SECURITY SETTINGS FOR PRODUCTION
# ==========================
if not DEBUG:
    # Security settings para produção
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    X_FRAME_OPTIONS = 'DENY'
