from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('SECRET_KEY', 'dev-only-not-for-production')

DEBUG = os.getenv('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

CORS_ALLOW_ALL_ORIGINS = DEBUG
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sitemaps',
    'django.contrib.humanize',
    'rest_framework',
    'rest_framework.authtoken',
    'stores',
    'payments',
]

try:
    import channels  # type: ignore
    INSTALLED_APPS.insert(0, 'channels')
    CHANNELS_AVAILABLE = True
except ImportError:
    CHANNELS_AVAILABLE = False

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'stores.middleware.LanguageCurrencyMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'moncv.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'stores.context_processors.seo_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'moncv.wsgi.application'

if 'CHANNELS_AVAILABLE' in globals() and CHANNELS_AVAILABLE:
    ASGI_APPLICATION = 'moncv.asgi.application'
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {
                'hosts': [('127.0.0.1', 6379)],
            },
        },
    }

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

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

LANGUAGE_CODE = 'fr'

LANGUAGES = [
    ('fr', 'Français'),
    ('en', 'English'),
]

LOCALE_PATHS = [
    BASE_DIR / 'locale',
]

TIME_ZONE = 'UTC'

USE_I18N = True
USE_L10N = True
USE_TZ = True

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'home'

SITE_URL = os.environ.get('SITE_URL', 'http://localhost:8000')

ORANGE_MONEY_API_KEY = os.environ.get('ORANGE_MONEY_API_KEY', '')
ORANGE_MONEY_API_SECRET = os.environ.get('ORANGE_MONEY_API_SECRET', '')
ORANGE_MONEY_MERCHANT_ID = os.environ.get('ORANGE_MONEY_MERCHANT_ID', '')
ORANGE_MONEY_ENVIRONMENT = os.environ.get('ORANGE_MONEY_ENVIRONMENT', 'sandbox')

MOOV_MONEY_API_KEY = os.environ.get('MOOV_MONEY_API_KEY', '')
MOOV_MONEY_API_SECRET = os.environ.get('MOOV_MONEY_API_SECRET', '')
MOOV_MONEY_MERCHANT_ID = os.environ.get('MOOV_MONEY_MERCHANT_ID', '')
MOOV_MONEY_ENVIRONMENT = os.environ.get('MOOV_MONEY_ENVIRONMENT', 'sandbox')

MTN_MONEY_API_KEY = os.environ.get('MTN_MONEY_API_KEY', '')
MTN_MONEY_API_SECRET = os.environ.get('MTN_MONEY_API_SECRET', '')
MTN_MONEY_ENVIRONMENT = os.environ.get('MTN_MONEY_ENVIRONMENT', 'sandbox')

PAYDUNYA_MASTER_KEY = os.environ.get('PAYDUNYA_MASTER_KEY', '')
PAYDUNYA_PRIVATE_KEY = os.environ.get('PAYDUNYA_PRIVATE_KEY', '')
PAYDUNYA_TOKEN = os.environ.get('PAYDUNYA_TOKEN', '')
PAYDUNYA_MODE = os.environ.get('PAYDUNYA_MODE', 'test')

WAVE_API_KEY = os.environ.get('WAVE_API_KEY', '')
WAVE_API_SECRET = os.environ.get('WAVE_API_SECRET', '')
WAVE_ENVIRONMENT = os.environ.get('WAVE_ENVIRONMENT', 'sandbox')

CINETPAY_API_KEY = os.environ.get('CINETPAY_API_KEY', '')
CINETPAY_SITE_ID = os.environ.get('CINETPAY_SITE_ID', '')
CINETPAY_ENVIRONMENT = os.environ.get('CINETPAY_ENVIRONMENT', 'sandbox')

STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', '')
STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY', '')
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET', '')

PAYMENT_ENVIRONMENT = os.environ.get('PAYMENT_ENVIRONMENT', 'sandbox')

OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'payments.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'stores.payment_providers': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'stores.views': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
}
