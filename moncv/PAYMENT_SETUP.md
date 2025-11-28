# 💳 Guide de Configuration des Paiements - MYMEDAGA

## 🔐 Configuration en Production

### 1. Obtenir les Clés API Officielles

#### Orange Money
1. Créer un compte sur [Orange Developer Portal](https://developer.orange.com/)
2. Créer une application
3. Obtenir:
   - `API Key`
   - `API Secret`
   - `Merchant ID`

#### Moov Money
1. Créer un compte sur [Moov Developer Portal](https://developer.moov-africa.com/)
2. Créer une application
3. Obtenir:
   - `API Key`
   - `API Secret`
   - `Merchant ID`

#### MTN Mobile Money
1. Créer un compte sur [MTN Developer Portal](https://momodeveloper.mtn.com/)
2. Créer une application
3. Obtenir:
   - `API Key` (Subscription Key)
   - `API Secret` (API User/Password)

#### Wave
1. Créer un compte sur [Wave Developer Portal](https://developer.wave.com/)
2. Créer une application
3. Obtenir:
   - `API Key`
   - `API Secret`

### 2. Configuration des Variables d'Environnement

**⚠️ IMPORTANT: Ne JAMAIS commiter les clés API dans le code source**

#### Option 1: Fichier .env (Recommandé)

1. Créer un fichier `.env` à la racine du projet
2. Copier le contenu de `.env.example`
3. Remplir avec vos vraies clés:

```bash
# Production
PAYMENT_ENVIRONMENT=production
ORANGE_MONEY_API_KEY=votre_vraie_cle
ORANGE_MONEY_API_SECRET=votre_vrai_secret
# ... etc
```

4. Installer `python-decouple` ou `django-environ`:

```bash
pip install python-decouple
```

5. Modifier `settings.py` pour charger depuis `.env`:

```python
from decouple import config

ORANGE_MONEY_API_KEY = config('ORANGE_MONEY_API_KEY', default='')
ORANGE_MONEY_API_SECRET = config('ORANGE_MONEY_API_SECRET', default='')
```

#### Option 2: Variables d'Environnement Système

**Linux/Mac:**
```bash
export ORANGE_MONEY_API_KEY="votre_cle"
export ORANGE_MONEY_API_SECRET="votre_secret"
```

**Windows (PowerShell):**
```powershell
$env:ORANGE_MONEY_API_KEY="votre_cle"
$env:ORANGE_MONEY_API_SECRET="votre_secret"
```

**Windows (CMD):**
```cmd
set ORANGE_MONEY_API_KEY=votre_cle
set ORANGE_MONEY_API_SECRET=votre_secret
```

### 3. Configuration du Webhook

Les fournisseurs de paiement enverront des notifications à votre serveur via webhook.

1. **Configurer l'URL du webhook dans votre compte développeur:**
   - Orange Money: `https://votre-domaine.com/payment/webhook/orange/`
   - Moov Money: `https://votre-domaine.com/payment/webhook/moov/`
   - MTN: `https://votre-domaine.com/payment/webhook/mtn/`
   - Wave: `https://votre-domaine.com/payment/webhook/wave/`

2. **Vérifier que votre serveur est accessible publiquement** (HTTPS requis en production)

3. **Tester le webhook** avec les outils de test des fournisseurs

### 4. Validation Côté Serveur

Le système valide automatiquement les paiements:

1. **Lors de l'initiation:** Vérification avec l'API du fournisseur
2. **Via webhook:** Notification automatique du fournisseur
3. **Vérification manuelle:** Possibilité de vérifier le statut à tout moment

### 5. Journalisation

Toutes les transactions sont journalisées dans:
- `logs/payements.log` - Fichier de log
- Base de données - Table `Payment` avec métadonnées complètes

### 6. Sécurité

✅ **Bonnes pratiques implémentées:**
- Validation de signature des webhooks
- Journalisation de toutes les transactions
- Validation côté serveur uniquement
- Pas de validation côté client pour les paiements
- Clés API stockées dans variables d'environnement

### 7. Test en Mode Sandbox

Avant de passer en production:

1. Tester avec les clés sandbox
2. Vérifier que les webhooks fonctionnent
3. Tester tous les scénarios (succès, échec, annulation)
4. Vérifier les logs

### 8. Passage en Production

1. Obtenir les clés API de production
2. Changer `PAYMENT_ENVIRONMENT=production` dans `.env`
3. Configurer les webhooks avec les URLs de production
4. Tester avec un petit montant
5. Monitorer les logs

## 📋 Checklist Production

- [ ] Clés API de production obtenues
- [ ] Variables d'environnement configurées
- [ ] Webhooks configurés et testés
- [ ] HTTPS activé sur le serveur
- [ ] Logs configurés et accessibles
- [ ] Tests effectués avec vrais comptes
- [ ] Monitoring des transactions en place
- [ ] Plan de rollback préparé

## 🆘 Support

En cas de problème:
1. Vérifier les logs: `logs/payments.log`
2. Vérifier les métadonnées dans la table `Payment`
3. Contacter le support du fournisseur de paiement
4. Vérifier la documentation officielle de l'API

