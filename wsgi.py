"""
WSGI config for moncv project.

It exposes the WSGI callable as a module-level variable named ``application``.
"""

import os
import sys

# Ajouter le chemin du projet au PYTHONPATH
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)
sys.path.append(os.path.join(project_root, 'moncv'))

# Importer l'application WSGI de Django
from django.core.wsgi import get_wsgi_application

# Définir le module de paramètres par défaut
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'moncv.settings_prod')

# Obtenir l'application WSGI
application = get_wsgi_application()
