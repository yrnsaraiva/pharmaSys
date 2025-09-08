from pathlib import Path
import os
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

# ==========================
# SECURITY
# ==========================
SECRET_KEY = 'django-insecure-o%cf1_-^p95dr-aupdnimbg_-k@xugqx70f79_##63h9&ox1!y'
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
DEBUG = True
ALLOWED_HOSTS = ['*']  # Ajuste para produção

# Permitir o domínio do seu site para POSTs
CSRF_TRUSTED_ORIGINS = [
    'https://pharmasys-production.up.railway.app',
    'http://pharmasys-production.up.railway.app',
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
    'django.contrib.admin',
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
    "usuarios.apps.UsuariosConfig"
]

# ==========================
# MIDDLEWARE
# ==========================
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # <--- WhiteNoise
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
                'core.context_processors.request_is_secure',  # <--- adicionado
            ],
        },
    },
]

WSGI_APPLICATION = 'pharmaSys.wsgi.application'

# ==========================
# DATABASE
# ==========================
DATABASES = {
    'default': dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}"
    )
}
# POSTGRES_LOCALLY = True
# if not DEBUG or POSTGRES_LOCALLY:
#     DATABASES['default'] = dj_database_url.parse(
#         'postgresql://postgres:aasiGbCkQfTCRDfiMXdyQdNfXGHYynTw@maglev.proxy.rlwy.net:41864/railway')

# ==========================
# PASSWORD VALIDATION
# ==========================
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
]

# ==========================
# INTERNATIONALIZATION
# ==========================
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Maputo'
USE_I18N = True
USE_TZ = True

# ==========================
# STATIC FILES
# ==========================
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'  # Pasta para collectstatic
STATICFILES_DIRS = [BASE_DIR / 'static']  # Pasta de arquivos customizados
STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'

# ==========================
# AUTHENTICATION REDIRECTS
# ==========================
LOGIN_URL = '/usuarios/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/usuarios/login/'