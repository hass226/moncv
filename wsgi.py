"""
WSGI config for moncv project.

It exposes the WSGI callable as a module-level variable named ``application``.
"""

import os
import sys

# Ajouter le chemin du projet au PYTHONPATH
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'moncv.settings_prod')

application = get_wsgi_application()
