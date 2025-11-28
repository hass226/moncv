# 🚀 Démarrage Rapide

## Installation en 5 étapes

```bash
# 1. Installer les dépendances
pip install -r requirements.txt

# 2. Créer les migrations
python manage.py makemigrations

# 3. Appliquer les migrations
python manage.py migrate

# 4. Créer un superutilisateur (optionnel)
python manage.py createsuperuser

# 5. Lancer le serveur
python manage.py runserver
```

## Accès

- **Site web** : http://127.0.0.1:8000/
- **Admin Django** : http://127.0.0.1:8000/admin/

## Première utilisation

1. Allez sur http://127.0.0.1:8000/register/
2. Créez un compte
3. Créez votre boutique
4. Ajoutez vos premiers produits !

## Structure des URLs

- `/` - Page d'accueil (feed de produits)
- `/register/` - Inscription
- `/login/` - Connexion
- `/dashboard/` - Tableau de bord (nécessite connexion)
- `/create-store/` - Créer une boutique
- `/add-product/` - Ajouter un produit
- `/store/<id>/` - Page publique d'une boutique

## Notes importantes

- Les images sont stockées dans le dossier `media/`
- Le numéro WhatsApp doit être au format international (ex: +33612345678)
- Chaque utilisateur ne peut avoir qu'une seule boutique

