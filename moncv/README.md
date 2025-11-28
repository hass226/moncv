# 🚀 MYMEDAGA - Là où les jeunes deviennent vendeurs

**MYMEDAGA** est une plateforme e-commerce futuriste conçue pour la jeunesse africaine. Chaque jeune entrepreneur peut créer sa boutique et poster ses produits. Les clients peuvent parcourir les produits et contacter les vendeurs directement via WhatsApp.

🎯 **Notre mission** : Rivaliser avec Alibaba en offrant une plateforme moderne, attrayante et accessible à tous les jeunes entrepreneurs africains.

## ✨ Fonctionnalités

### 🎯 Fonctionnalités Principales
- ✅ **Design Futuriste** - Interface moderne avec animations et couleurs vives inspirées de l'Afrique
- ✅ **Création de compte** - Inscription rapide et intuitive
- ✅ **Création de boutique** - Chaque utilisateur peut créer sa boutique (nom, logo, description, WhatsApp)
- ✅ **Gestion de produits** - Ajout, modification et suppression de produits facilement
- ✅ **Page boutique publique** - Page dédiée et attrayante pour chaque boutique
- ✅ **Feed de produits** - Page d'accueil avec tous les produits (pagination)
- ✅ **Intégration WhatsApp** - Bouton direct pour contacter le vendeur
- ✅ **Responsive Design** - Optimisé pour mobile, tablette et desktop

### 🚀 Fonctionnalités Avancées (Nouvelles)
- ✅ **📍 Géolocalisation Automatique** - Envoi automatique de la localisation du client au vendeur via WhatsApp
- ✅ **🛒 Système de Commande Intelligent** - Messages WhatsApp professionnels avec localisation et détails de commande
- ✅ **🗺️ Intégration Google Maps** - Lien direct vers la carte avec la position du client
- ✅ **📱 Interface Améliorée** - Animations et notifications pour une meilleure expérience utilisateur
- ✅ **🔔 Système de Notifications** - Notifications en temps réel pour les interactions
- ✅ **⭐ Système de Likes/Commentaires** - Interactions sociales comme TikTok
- ✅ **🔍 Recherche Avancée** - Filtres par catégorie, prix, popularité
- ✅ **📊 Dashboard Analytique** - Statistiques détaillées pour les vendeurs
- ✅ **🏆 Hall of Fame** - Classement des meilleures boutiques
- ✅ **💾 Favoris** - Sauvegarder vos produits préférés

## 🛠️ Technologies

- **Backend**: Django 5.2+
- **Frontend**: Bootstrap 5, Django Templates, CSS3 Animations
- **Design**: Glassmorphism, Gradients, Animations CSS
- **Typographie**: Orbitron (futuriste), Poppins (moderne)
- **Base de données**: SQLite (par défaut)
- **Upload d'images**: Django + Pillow

## 📦 Installation

### 1. Cloner ou télécharger le projet

```bash
cd moncv
```

### 2. Créer un environnement virtuel (recommandé)

```bash
python -m venv venv
```

**Windows:**
```bash
venv\Scripts\activate
```

**Linux/Mac:**
```bash
source venv/bin/activate
```

### 3. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 4. Appliquer les migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 5. Créer un superutilisateur (optionnel, pour l'admin)

```bash
python manage.py createsuperuser
```

### 6. Lancer le serveur de développement

```bash
python manage.py runserver
```

Le site sera accessible sur `http://127.0.0.1:8000/`

## 🚀 Utilisation

### Pour les vendeurs

1. **S'inscrire** : Créer un compte via `/register/`
2. **Créer sa boutique** : Après l'inscription, créer une boutique avec nom, description, logo et numéro WhatsApp
3. **Ajouter des produits** : Depuis le dashboard, ajouter des produits avec photo, prix et description
4. **Gérer sa boutique** : Modifier les informations de la boutique et les produits depuis le dashboard

### Pour les clients

1. **Parcourir les produits** : Voir tous les produits sur la page d'accueil
2. **Visiter une boutique** : Cliquer sur "Voir la boutique" pour voir tous les produits d'un vendeur
3. **Commander avec localisation** : 
   - Cliquer sur "Commander avec localisation" 
   - Autoriser l'accès à votre position (si demandé)
   - Votre localisation sera automatiquement envoyée au vendeur via WhatsApp avec un message professionnel
   - Un lien Google Maps est inclus pour faciliter la livraison
4. **Interagir** : Liker, commenter, partager et ajouter aux favoris
5. **Rechercher** : Utiliser la recherche avancée avec filtres

## 📁 Structure du projet

```
moncv/
├── manage.py
├── requirements.txt
├── README.md
├── moncv/              # Configuration du projet
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── stores/             # Application principale
│   ├── __init__.py
│   ├── models.py       # Modèles Store et Product
│   ├── views.py        # Vues (CRUD)
│   ├── urls.py         # URLs de l'app
│   ├── forms.py        # Formulaires
│   ├── admin.py        # Configuration admin
│   └── apps.py
├── templates/          # Templates HTML
│   ├── base.html
│   └── stores/
│       ├── home.html
│       ├── store_detail.html
│       ├── dashboard.html
│       ├── register.html
│       ├── login.html
│       ├── create_store.html
│       ├── edit_store.html
│       ├── add_product.html
│       ├── edit_product.html
│       └── delete_product.html
├── media/              # Fichiers uploadés (créé automatiquement)
│   ├── store_logos/
│   └── products/
└── static/             # Fichiers statiques (CSS, JS)
```

## 🗄️ Modèles

### Store (Boutique)
- `owner` : Propriétaire (OneToOne avec User)
- `name` : Nom de la boutique
- `description` : Description
- `whatsapp_number` : Numéro WhatsApp
- `logo` : Logo de la boutique
- `is_verified` : Boutique vérifiée
- `is_featured` : Boutique en vedette
- `created_at` : Date de création

### Product (Produit)
- `store` : Boutique propriétaire (ForeignKey)
- `name` : Nom du produit
- `price` : Prix
- `description` : Description
- `image` : Image du produit
- `category` : Catégorie du produit
- `tags` : Tags du produit
- `is_featured` : Produit en vedette
- `views_count` : Nombre de vues
- `likes_count` : Nombre de likes
- `created_at` : Date de création

### Order (Commande) - Nouveau
- `product` : Produit commandé
- `customer` : Client (User)
- `store` : Boutique
- `latitude` : Latitude de la localisation
- `longitude` : Longitude de la localisation
- `address` : Adresse de livraison
- `quantity` : Quantité
- `total_price` : Prix total
- `status` : Statut de la commande
- `customer_name` : Nom du client
- `customer_phone` : Téléphone du client
- `notes` : Notes du client
- `created_at` : Date de création

## 🔐 Sécurité

⚠️ **Important pour la production** :
- Changer `SECRET_KEY` dans `settings.py`
- Mettre `DEBUG = False`
- Configurer `ALLOWED_HOSTS`
- Utiliser une base de données PostgreSQL
- Configurer HTTPS
- Utiliser un service cloud pour les médias (Cloudinary, AWS S3, etc.)

## 📝 Notes

- Le format du numéro WhatsApp doit inclure le code pays (ex: +33612345678)
- Les images sont stockées localement dans le dossier `media/`
- Pour la production, considérez l'utilisation de Cloudinary ou AWS S3 pour les images
- **Géolocalisation** : La fonctionnalité de géolocalisation nécessite l'autorisation du navigateur. Si l'utilisateur refuse, le message WhatsApp sera envoyé sans localisation.
- **WhatsApp** : Les messages incluent automatiquement la localisation du client avec un lien Google Maps pour faciliter la livraison.

## 🎨 Personnalisation

Les templates utilisent Bootstrap 5. Vous pouvez facilement personnaliser :
- Les couleurs dans `base.html` (variables CSS)
- Le design des cartes produits
- Les icônes Bootstrap Icons

## 📞 Support

Pour toute question ou problème, n'hésitez pas à ouvrir une issue.

---

**Bon développement ! 🚀**

