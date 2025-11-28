# Sécurité du système de paiement par SMS

Ce document décrit les mesures de sécurité mises en place pour le système de vérification des paiements par SMS.

## 1. Protection du Webhook

### Authentification

Pour sécuriser l'endpoint du webhook, plusieurs méthodes sont disponibles :

1. **Token d'authentification**
   - Ajoutez un token dans l'en-tête de la requête
   - Vérifiez-le côté serveur avant de traiter la requête

   ```python
   # Dans webhooks.py
   from django.conf import settings
   from django.http import HttpResponseForbidden
   
   @csrf_exempt
   @require_http_methods(["POST"])
   def sms_webhook(request):
       # Vérification du token
       auth_header = request.headers.get('Authorization')
       if auth_header != f'Token {settings.SMS_WEBHOOK_TOKEN}':
           return HttpResponseForbidden('Accès non autorisé')
       
       # Suite du traitement...
   ```

2. **Vérification de l'IP source**
   - Restreindre les adresses IP autorisées à appeler le webhook
   - À configurer au niveau du serveur web (Nginx/Apache) ou dans le middleware Django

### Chiffrement (HTTPS)

- **Obligatoire** : L'API doit être servie exclusivement en HTTPS
- Configuration recommandée pour Nginx :
  ```nginx
  server {
      listen 443 ssl http2;
      server_name votre-domaine.com;
      
      ssl_certificate /chemin/vers/votre/certificat.crt;
      ssl_certificate_key /chemin/vers/votre/cle.privee.key;
      
      # Configuration SSL recommandée
      ssl_protocols TLSv1.2 TLSv1.3;
      ssl_ciphers 'TLS_AES_128_GCM_SHA256:TLS_AES_256_GCM_SHA384:ECDHE-RSA-AES128-GCM-SHA256';
      ssl_prefer_server_ciphers on;
      
      # ... autres configurations ...
  }
  ```

## 2. Sécurité de l'application Android

### Permissions

L'application demande uniquement les permissions nécessaires :
- `RECEIVE_SMS` : Pour recevoir les SMS entrants
- `READ_SMS` : Pour lire le contenu des SMS
- `INTERNET` : Pour communiquer avec le serveur
- `ACCESS_NETWORK_STATE` : Pour vérifier la connectivité

### Protection des données sensibles

1. **Ne pas stocker d'informations sensibles** en clair
2. **Utiliser Android Keystore** pour le stockage sécurisé des données
3. **Obfuscation du code** avec ProGuard/R8

## 3. Validation des données

### Côté serveur

```python
from django.core.exceptions import ValidationError

def validate_payment_data(amount, phone_number, transaction_id):
    """Valide les données de paiement"""
    # Vérifier le montant
    if not (100 <= amount <= 1000000):  # Exemple: entre 100 et 1,000,000 FCFA
        raise ValidationError("Montant invalide")
    
    # Vérifier le format du numéro de téléphone
    import phonenumbers
    try:
        parsed_number = phonenumbers.parse(phone_number, None)
        if not phonenumbers.is_valid_number(parsed_number):
            raise ValidationError("Numéro de téléphone invalide")
    except:
        raise ValidationError("Format de numéro invalide")
    
    # Vérifier le format de l'ID de transaction
    import re
    if not re.match(r'^(OM|MTN|MOOV|WV)\d{6,}$', transaction_id, re.IGNORECASE):
        raise ValidationError("Format d'ID de transaction invalide")
```

## 4. Journalisation et surveillance

### Configuration de la journalisation

```python
# settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'payment_file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': '/var/log/payments/webhook.log',
            'formatter': 'verbose',
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
        },
    },
    'loggers': {
        'payments.webhooks': {
            'handlers': ['payment_file', 'mail_admins'],
            'level': 'INFO',
            'propagate': True,
        },
    },
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
}
```

### Surveillance

1. **Alertes** : Configurer des alertes pour les erreurs critiques
2. **Métriques** : Suivre le nombre de transactions par période
3. **Audit** : Conserver les logs pour une durée raisonnable

## 5. Tests de sécurité

Avant le déploiement, effectuez :

1. **Test d'intrusion** : Vérifiez les vulnérabilités connues
2. **Analyse statique** : Utilisez des outils comme Bandit pour Python
3. **Revue de code** : Faites relire le code par un tiers

## 6. Mises à jour de sécurité

- Maintenez à jour toutes les dépendances
- Abonnez-vous aux alertes de sécurité pour Django et les autres bibliothèques utilisées
- Ayez un plan de réponse aux incidents

## 7. Conformité

Assurez-vous de respecter :
- RGPD pour la protection des données personnelles
- PCI DSS si vous traitez des données de cartes de crédit
- Législation locale sur les transactions financières

## Contact sécurité

Pour toute question ou vulnérabilité de sécurité, contactez :
- Email : [votre-email@domaine.com](mailto:securite@domaine.com)
- PGP : [votre clé publique PGP]
