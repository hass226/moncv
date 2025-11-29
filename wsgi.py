"""
WSGI config for the Flask application.
"""
import os
from app import app as application

# Ce fichier est nécessaire pour le déploiement sur Render
# Il est utilisé par gunicorn pour démarrer l'application

# La variable d'application est requise par WSGI
app = application

if __name__ == "__main__":
    # Cette partie est utilisée pour le développement local
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=os.environ.get('FLASK_DEBUG', 'false').lower() == 'true')
