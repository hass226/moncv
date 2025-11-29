import os
from decouple import config

# Déterminer l'environnement (production ou développement)
ENVIRONMENT = config('DJANGO_ENV', default='development')

if ENVIRONMENT == 'production':
    from .settings_prod import *
else:
    try:
        from .settings_dev import *
    except ImportError:
        from .settings_prod import *
