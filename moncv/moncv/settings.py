"""
Django settings for moncv project.
"""

from pathlib import Path
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-change-this-in-production-!@#$%^&*()'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True



ALLOWED_HOSTS = ["*", "192.168.1.69", "127.0.0.1"]
 # En production, spécifier les domaines exacts

# CORS Configuration (pour accessibilité globale)
CORS_ALLOW_ALL_ORIGINS = True  # En production, spécifier les origines autorisées
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

# Configuration CSP (Content Security Policy)
CSP_DEFAULT_SRC = ["'self'"]
CSP_SCRIPT_SRC = [
    "'self'",
    "'unsafe-inline'",
    "'unsafe-eval'",
    "https://code.jquery.com",
    "https://cdn.jsdelivr.net",
    "https://www.google.com",
    "https://www.gstatic.com"
]
CSP_STYLE_SRC = [
    "'self'",
    "'unsafe-inline'",
    "https://cdn.jsdelivr.net",
    "https://stackpath.bootstrapcdn.com"
]
CSP_IMG_SRC = ["'self'", "data:", "https: http:"]
CSP_FONT_SRC = ["'self'", "https://cdn.jsdelivr.net", "https://fonts.gstatic.com"]
CSP_CONNECT_SRC = ["'self'", "https://www.google.com"]
CSP_FRAME_SRC = ["'self'", "https://www.google.com"]
CSP_INCLUDE_NONCE_IN = ['script-src']

# Désactiver CSP en mode debug pour faciliter le développement
CSP_REPORT_ONLY = DEBUG


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'csp',
    'django.contrib.sitemaps',  # Pour le SEO
    'django.contrib.humanize',  # Pour le formatage des nombres
    'stores',
    'payments',  # Application de gestion des paiements
]

# Channels (optionnel - pour Live Commerce avec WebSocket)
try:
    import channels
    INSTALLED_APPS.insert(0, 'channels')
    CHANNELS_AVAILABLE = True
except ImportError:
    CHANNELS_AVAILABLE = False

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'csp.middleware.CSPMiddleware',  # Middleware CSP
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',  # Ajout pour i18n
    'stores.middleware.LanguageCurrencyMiddleware',  # Notre middleware personnalisé
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
                'stores.context_processors.seo_context',  # SEO context
                'stores.context_processors.global_language_currency',
            ],
        },
    },
]

WSGI_APPLICATION = 'moncv.wsgi.application'

# Channels configuration (optionnel - pour Live Commerce avec WebSocket)
if CHANNELS_AVAILABLE:
    ASGI_APPLICATION = 'moncv.asgi.application'
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {
                "hosts": [('127.0.0.1', 6379)],
            },
        },
    }


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

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


# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

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


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Login URLs
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'home'

# Site URL (pour les callbacks de paiement)
SITE_URL = os.environ.get('SITE_URL', 'http://localhost:8000')

# Configuration WhatsApp
WHATSAPP_API_KEY = os.environ.get('WHATSAPP_API_KEY', '')
ADMIN_WHATSAPP_NUMBER = '22601256984'  # Numéro de téléphone sans le signe +

# Configuration des API de paiement
# ⚠️ IMPORTANT: En production, utilisez des variables d'environnement sécurisées
# Ne JAMAIS commiter ces clés dans le code source

# Orange Money API
ORANGE_MONEY_API_KEY = os.environ.get('ORANGE_MONEY_API_KEY', '')
ORANGE_MONEY_API_SECRET = os.environ.get('ORANGE_MONEY_API_SECRET', '')
ORANGE_MONEY_MERCHANT_ID = os.environ.get('ORANGE_MONEY_MERCHANT_ID', '')
ORANGE_MONEY_ENVIRONMENT = os.environ.get('ORANGE_MONEY_ENVIRONMENT', 'sandbox')  # 'sandbox' ou 'production'

# Moov Money API
MOOV_MONEY_API_KEY = os.environ.get('MOOV_MONEY_API_KEY', '')
MOOV_MONEY_API_SECRET = os.environ.get('MOOV_MONEY_API_SECRET', '')
MOOV_MONEY_MERCHANT_ID = os.environ.get('MOOV_MONEY_MERCHANT_ID', '')
MOOV_MONEY_ENVIRONMENT = os.environ.get('MOOV_MONEY_ENVIRONMENT', 'sandbox')

# Configuration des emails
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'  # En développement
# En production, utilisez :
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_HOST = 'smtp.your-email-provider.com'
# EMAIL_PORT = 587
# EMAIL_USE_TLS = True
# EMAIL_HOST_USER = 'your-email@example.com'
# EMAIL_HOST_PASSWORD = 'your-email-password'
DEFAULT_FROM_EMAIL = 'noreply@example.com'  # Email d'expéditeur par défaut
CONTACT_EMAIL = 'contact@example.com'  # Email de réception des messages de contact

# Mobile Money SMS Gateway
SMS_GATEWAY_API_KEY = os.environ.get('SMS_GATEWAY_API_KEY', 'votre_cle_secrete_ici')
SMS_GATEWAY_ALLOWED_IPS = ['127.0.0.1']  # Ajoutez les IPs autorisées

# MTN Mobile Money API
MTN_MONEY_API_KEY = os.environ.get('MTN_MONEY_API_KEY', '')
MTN_MONEY_API_SECRET = os.environ.get('MTN_MONEY_API_SECRET', '')
MTN_MONEY_ENVIRONMENT = os.environ.get('MTN_MONEY_ENVIRONMENT', 'sandbox')

# PayDunya API
PAYDUNYA_MASTER_KEY = os.environ.get('PAYDUNYA_MASTER_KEY', '')
PAYDUNYA_PRIVATE_KEY = os.environ.get('PAYDUNYA_PRIVATE_KEY', '')
PAYDUNYA_TOKEN = os.environ.get('PAYDUNYA_TOKEN', '')
PAYDUNYA_MODE = os.environ.get('PAYDUNYA_MODE', 'test')  # 'test' ou 'live'

# Wave API
WAVE_API_KEY = os.environ.get('WAVE_API_KEY', '')
WAVE_API_SECRET = os.environ.get('WAVE_API_SECRET', '')
WAVE_ENVIRONMENT = os.environ.get('WAVE_ENVIRONMENT', 'sandbox')

# CinetPay API (intégration future)
CINETPAY_API_KEY = os.environ.get('CINETPAY_API_KEY', '')
CINETPAY_SITE_ID = os.environ.get('CINETPAY_SITE_ID', '')
CINETPAY_ENVIRONMENT = os.environ.get('CINETPAY_ENVIRONMENT', 'sandbox')


# Stripe API (intégration future)
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', '')
STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY', '')
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET', '')

# Environnement de paiement global
PAYMENT_ENVIRONMENT = os.environ.get('PAYMENT_ENVIRONMENT', 'sandbox')  # 'sandbox' ou 'production'

# Configuration IA (OpenAI, Anthropic)
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
# PayPal API (Checkout v2)
PAYPAL_CLIENT_ID = "TON_CLIENT_ID_SANDBOX"
PAYPAL_SECRET_KEY = "TON_SECRET_SANDBOX"

# Logging pour les transactions
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
        'payments': {
            'handlers': ['file', 'console'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}

