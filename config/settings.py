import os, secrets
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
STATE = Path(os.environ.get('RFA_STATE', BASE_DIR / '.local')).absolute()
STATE.mkdir(mode=0o700, parents=True, exist_ok=True)
key = STATE / 'secret.key'
try:
    with key.open('x', encoding='ascii') as f:
        os.chmod(key, 0o600)
        f.write(secrets.token_urlsafe(64))
except FileExistsError:
    pass
SECRET_KEY = key.read_text(encoding='ascii')
DEBUG = False
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '[::1]']
INSTALLED_APPS = ['django.contrib.auth', 'django.contrib.contenttypes', 'django.contrib.sessions', 'axes', 'assistant']
MIDDLEWARE = ['django.middleware.security.SecurityMiddleware', 'django.contrib.sessions.middleware.SessionMiddleware', 'django.middleware.common.CommonMiddleware', 'django.middleware.csrf.CsrfViewMiddleware', 'django.contrib.auth.middleware.AuthenticationMiddleware', 'assistant.middleware.Access', 'axes.middleware.AxesMiddleware']
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': STATE / 'db.sqlite3', 'OPTIONS': {'timeout': 20}}}
TEMPLATES = [{'BACKEND': 'django.template.backends.django.DjangoTemplates', 'DIRS': [BASE_DIR / 'assistant/templates'], 'APP_DIRS': True, 'OPTIONS': {'context_processors': ['django.template.context_processors.csrf']}}]
ROOT_URLCONF = 'config.urls'
AUTHENTICATION_BACKENDS = ['axes.backends.AxesStandaloneBackend', 'django.contrib.auth.backends.ModelBackend']
AUTH_PASSWORD_VALIDATORS = [{'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 12}}, {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'}, {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'}]
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Strict'
SESSION_COOKIE_AGE = 1800
SESSION_SAVE_EVERY_REQUEST = True
CSRF_COOKIE_SAMESITE = 'Strict'
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 0.25
AXES_LOCKOUT_PARAMETERS = [['username'], ['ip_address']]
AXES_RESET_ON_SUCCESS = True
AXES_VERBOSE = False
AXES_SENSITIVE_PARAMETERS = ['username', 'password']
LANGUAGE_CODE = 'zh-hant'
TIME_ZONE = 'UTC'
USE_TZ = True
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
SECURE_CONTENT_TYPE_NOSNIFF = True
DATA_UPLOAD_MAX_MEMORY_SIZE = 16384
LOGGING = {'version': 1, 'disable_existing_loggers': False, 'handlers': {'audit': {'class': 'logging.handlers.RotatingFileHandler', 'filename': str(STATE / 'audit.log'), 'maxBytes': 2000000, 'backupCount': 3}}, 'loggers': {'audit': {'handlers': ['audit'], 'level': 'INFO', 'propagate': False}, 'django.request': {'handlers': ['audit'], 'level': 'ERROR', 'propagate': False}}}

SECURE_REFERRER_POLICY = 'same-origin'
AXES_LOCKOUT_TEMPLATE = 'locked.html'
LOGGING['formatters'] = {'audit': {'format': '%(asctime)s %(levelname)s %(message)s'}}
LOGGING['handlers']['audit']['formatter'] = 'audit'
