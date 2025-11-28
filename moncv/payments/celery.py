from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from django.conf import settings

# Définir le module de paramètres Django par défaut pour 'celery'.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'moncv.settings')

app = Celery('payments')

# Utiliser une chaîne ici signifie que le worker n'aura pas à sérialiser
# l'objet de configuration aux processus enfants.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Découvrir automatiquement les tâches dans les applications installées
app.autodiscover_tasks()

# Configuration des tâches périodiques
app.conf.beat_schedule = {
    'clean-expired-codes-daily': {
        'task': 'payments.tasks.clean_expired_codes',
        'schedule': 86400.0,  # Tous les jours
    },
}

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
