"""
WSGI config for moncv project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

# Utilisation de 'moncv.settings' comme module de paramètres par défaut
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'moncv.settings')

application = get_wsgi_application()
