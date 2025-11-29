from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Avg
from django.utils.text import slugify
from django.conf import settings
from datetime import timedelta
from django.utils.translation import gettext_lazy as _


class Store(models.Model):
    """Modèle pour les boutiques/magasins"""
    owner = models.OneToOneField(User, on_delete=models.CASCADE, related_name='store')
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, max_length=200)
    description = models.TextField(blank=True)
    whatsapp_number = models.CharField(max_length=20)
    logo = models.ImageField(upload_to="store_logos/", blank=True)
    is_verified = models.BooleanField(default=False, verbose_name="Boutique vérifiée")
    is_featured = models.BooleanField(default=False, verbose_name="Boutique en vedette")
    stripe_account_id = models.CharField(max_length=255, blank=True)
    fedapay_merchant_id = models.CharField(max_length=255, blank=True)
    paystack_subaccount = models.CharField(max_length=255, blank=True)
    # Localisation de la boutique (pour itinéraire clients)
    address = models.TextField(blank=True, help_text="Adresse de la boutique")
    city = models.CharField(max_length=100, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def has_active_subscription(self):
        """Vérifie si la boutique a un abonnement actif"""
        return self.subscriptions.filter(
            is_active=True,
            expires_at__gt=timezone.now()
        ).exists()

    def get_followers_count(self):
        """Nombre de followers"""
        return self.followers.count()

    def get_total_products(self):
        """Nombre total de produits"""
        return self.products.count()

    def get_average_rating(self):
        """Note moyenne de la boutique basée sur les avis produits"""
        from django.db.models import Avg
        return self.products.aggregate(avg_rating=Avg('reviews__rating'))['avg_rating'] or 0

    class Meta:
        verbose_name = "Boutique"
        verbose_name_plural = "Boutiques"
        ordering = ['-is_featured', '-created_at']

    def save(self, *args, **kwargs):
        if not self.slug:  # Only generate slug if it's not set
            base_slug = slugify(self.name)[:200]  # Ensure slug is not too long
            self.slug = base_slug
            
            # Check if slug already exists and make it unique if needed
            counter = 1
            while Store.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{base_slug}-{counter}"
                counter += 1
                
        super().save(*args, **kwargs)


class Formation(models.Model):
    """Modèle pour les formations proposées"""
    NIVEAU_CHOICES = [
        ('debutant', 'Débutant'),
        ('intermediaire', 'Intermédiaire'),
        ('avance', 'Avancé'),
    ]
    description = models.TextField(blank=True)
    whatsapp_number = models.CharField(max_length=20)
    logo = models.ImageField(upload_to="store_logos/", blank=True)
    is_verified = models.BooleanField(default=False, verbose_name="Boutique vérifiée")
    is_featured = models.BooleanField(default=False, verbose_name="Boutique en vedette")
    stripe_account_id = models.CharField(max_length=255, blank=True)
    fedapay_merchant_id = models.CharField(max_length=255, blank=True)
    paystack_subaccount = models.CharField(max_length=255, blank=True)
    # Localisation de la boutique (pour itinéraire clients)
    address = models.TextField(blank=True, help_text="Adresse de la boutique")
    city = models.CharField(max_length=100, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    def has_active_subscription(self):
        """Vérifie si la boutique a un abonnement actif"""
        return self.subscriptions.filter(
            is_active=True,
            expires_at__gt=timezone.now()
        ).exists()

    def get_followers_count(self):
        """Nombre de followers"""
        return self.followers.count()

    def get_total_products(self):
        """Nombre total de produits"""
        return self.products.count()

    def get_average_rating(self):
        """Note moyenne de la boutique basée sur les avis produits"""
        # Import ici pour éviter les références circulaires
        reviews = self.products.all()
        all_reviews = []
        for product in reviews:
            all_reviews.extend(product.reviews.all())
        if all_reviews:
            total = sum(r.rating for r in all_reviews)
            return round(total / len(all_reviews), 1)
        return 0

    class Meta:
        verbose_name = "Boutique"
        verbose_name_plural = "Boutiques"


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    icon = models.CharField(max_length=50, blank=True, help_text="Nom de l'icône Bootstrap")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Catégorie"
        verbose_name_plural = "Catégories"
        ordering = ['name']


class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Tag"
        verbose_name_plural = "Tags"
        ordering = ['name']


class ProductImage(models.Model):
    """Modèle pour stocker les images supplémentaires d'un produit"""
    product = models.ForeignKey('Product', on_delete=models.CASCADE, related_name='additional_images')
    image = models.ImageField(upload_to='products/additional/')
    order = models.PositiveIntegerField(default=0, help_text="Ordre d'affichage")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'created_at']
        verbose_name = "Image supplémentaire"
        verbose_name_plural = "Images supplémentaires"

    def __str__(self):
        return f"Image de {self.product.name}"


class Product(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='products')
    name = models.CharField(max_length=200)
    short_description = models.CharField(max_length=160, blank=True, help_text="Description courte pour les aperçus")
    price = models.DecimalField(max_digits=10, decimal_places=2)
    CURRENCY_CHOICES = [
        ('EUR', '€'),
        ('USD', '$'),
        ('GBP', '£'),
        ('CHF', 'CHF'),
        ('CAD', 'C$'),
        ('AUD', 'A$'),
        ('JPY', '¥'),
        ('CNY', '¥'),
        ('INR', '₹'),
        ('XOF', 'CFA'),
        ('XAF', 'FCFA'),
        ('MGA', 'Ar'),
        ('ZAR', 'R'),
        ('NGN', '₦'),
        ('BRL', 'R$'),
    ]
    currency = models.CharField(max_length=10, choices=CURRENCY_CHOICES, default='EUR', help_text="Choisissez la devise du produit")
    description = models.TextField(blank=True, help_text="Description complète du produit")
    image = models.ImageField(upload_to="products/")
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    tags = models.ManyToManyField(Tag, blank=True, related_name='products')
    is_featured = models.BooleanField(default=False, verbose_name="Produit en vedette")
    is_bestseller = models.BooleanField(default=False, verbose_name="Best-seller")
    featured_until = models.DateTimeField(null=True, blank=True, verbose_name="En vedette jusqu'au")
    views_count = models.IntegerField(default=0, verbose_name="Nombre de vues")
    likes_count = models.IntegerField(default=0, verbose_name="Nombre de likes")
    shares_count = models.IntegerField(default=0, verbose_name="Nombre de partages")
    stock = models.PositiveIntegerField(default=0, verbose_name="Stock disponible")
    sku = models.CharField(max_length=100, blank=True, verbose_name="Référence produit")
    weight = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Poids (kg)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def is_currently_featured(self):
        """Vérifie si le produit est actuellement en vedette"""
        if not self.is_featured:
            return False
        if self.featured_until and self.featured_until < timezone.now():
            return False
        return True

    def get_average_rating(self):
        """Calcule la note moyenne du produit"""
        reviews = self.reviews.all()
        if reviews.exists():
            return round(reviews.aggregate(Avg('rating'))['rating__avg'], 1)
        return 0

    class Meta:
        verbose_name = "Produit"
        verbose_name_plural = "Produits"
        ordering = ['-is_featured', '-created_at']


class Subscription(models.Model):
    SUBSCRIPTION_PLANS = [
        ('verified', 'Vérification (6 mois)'),
    ]
    
    PAYMENT_METHODS = [
        ('orange_money', 'Orange Money'),
        ('moov_money', 'Moov Money'),
        ('mobile_money', 'Mobile Money'),
        ('card', 'Carte Bancaire'),
        ('paypal', 'PayPal'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('completed', 'Complété'),
        ('failed', 'Échoué'),
        ('cancelled', 'Annulé'),
    ]

    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='subscriptions')
    plan_type = models.CharField(max_length=20, choices=SUBSCRIPTION_PLANS, default='verified')
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=50.00)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    transaction_id = models.CharField(max_length=100, blank=True, verbose_name="ID de transaction")
    starts_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.store.name} - {self.get_plan_type_display()}"

    def save(self, *args, **kwargs):
        if not self.expires_at and self.plan_type == 'verified':
            self.expires_at = timezone.now() + timedelta(days=180)  # 6 mois
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Abonnement"
        verbose_name_plural = "Abonnements"
        ordering = ['-created_at']


class Promotion(models.Model):
    PROMOTION_TYPES = [
        ('product', 'Promotion Produit'),
        ('store', 'Promotion Boutique'),
    ]
    
    PAYMENT_METHODS = [
        ('orange_money', 'Orange Money'),
        ('moov_money', 'Moov Money'),
        ('mobile_money', 'Mobile Money'),
        ('card', 'Carte Bancaire'),
        ('paypal', 'PayPal'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('active', 'Active'),
        ('expired', 'Expirée'),
        ('cancelled', 'Annulée'),
    ]

    promotion_type = models.CharField(max_length=20, choices=PROMOTION_TYPES)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True, related_name='promotions')
    store = models.ForeignKey(Store, on_delete=models.CASCADE, null=True, blank=True, related_name='promotions')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    transaction_id = models.CharField(max_length=100, blank=True)
    starts_at = models.DateTimeField()
    expires_at = models.DateTimeField()
    metadata = models.JSONField(default=dict, blank=True, help_text="Métadonnées supplémentaires (portée estimée, etc.)")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.product:
            return f"Promotion: {self.product.name}"
        return f"Promotion: {self.store.name}"

    class Meta:
        verbose_name = "Promotion"
        verbose_name_plural = "Promotions"
        ordering = ['-created_at']


class Follow(models.Model):
    """Système de suivi de boutiques (comme suivre un compte)"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='following')
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='followers')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'store']
        verbose_name = "Abonnement"
        verbose_name_plural = "Abonnements"
        ordering = ['-created_at']


class Like(models.Model):
    """Système de likes pour les produits (comme TikTok)"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='likes')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'product']
        verbose_name = "Like"
        verbose_name_plural = "Likes"
        ordering = ['-created_at']


class Comment(models.Model):
    """Système de commentaires pour les produits"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='comments')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Commentaire"
        verbose_name_plural = "Commentaires"
        ordering = ['-created_at']


class Share(models.Model):
    """Système de partages pour les produits"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='shares', null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='shares')
    platform = models.CharField(max_length=50, blank=True, help_text="WhatsApp, Facebook, etc.")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Partage"
        verbose_name_plural = "Partages"
        ordering = ['-created_at']


class Review(models.Model):
    """Système de reviews/avis pour les produits"""
    RATING_CHOICES = [
        (1, '1 étoile'),
        (2, '2 étoiles'),
        (3, '3 étoiles'),
        (4, '4 étoiles'),
        (5, '5 étoiles'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    rating = models.IntegerField(choices=RATING_CHOICES)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'product']
        verbose_name = "Avis"
        verbose_name_plural = "Avis"
        ordering = ['-created_at']


class Favorite(models.Model):
    """Système de favoris/wishlist"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorites')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='favorites')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'product']
        verbose_name = "Favori"
        verbose_name_plural = "Favoris"
        ordering = ['-created_at']


class Notification(models.Model):
    """Système de notifications"""
    NOTIFICATION_TYPES = [
        ('like', 'Nouveau like'),
        ('comment', 'Nouveau commentaire'),
        ('follow', 'Nouveau follower'),
        ('review', 'Nouvel avis'),
        ('order', 'Nouvelle commande'),
        ('job', 'Candidature job'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    message = models.TextField()
    link = models.URLField(blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        ordering = ['-created_at']


class SearchHistory(models.Model):
    """Historique de recherche pour améliorer les recommandations"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='search_history', null=True, blank=True)
    query = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Historique de recherche"
        verbose_name_plural = "Historiques de recherche"
        ordering = ['-created_at']


# Constantes pour les méthodes de paiement (utilisées dans plusieurs modèles)
PAYMENT_METHODS = [
    ('paydunya', 'PayDunya'),
    ('fedapay', 'FedaPay'),
    ('paystack', 'Paystack Mobile Money'),
    ('cinetpay', 'CinetPay'),
    ('stripe', 'Stripe'),
    ('paypal', 'PayPal'),
]

PAYMENT_STATUS_CHOICES = [
    ('pending', 'En attente'),
    ('processing', 'En traitement'),
    ('completed', 'Complété'),
    ('failed', 'Échoué'),
    ('refunded', 'Remboursé'),
    ('cancelled', 'Annulé'),
]


class Payment(models.Model):
    """Système de paiement amélioré"""
    
    # Constantes pour les méthodes de paiement (accessible via Payment.PAYMENT_METHODS)
    PAYMENT_METHODS = PAYMENT_METHODS  # Référence à la constante globale
    
    order = models.ForeignKey('Order', on_delete=models.CASCADE, related_name='payments', null=True, blank=True)
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name='payments', null=True, blank=True)
    promotion = models.ForeignKey(Promotion, on_delete=models.CASCADE, related_name='payments', null=True, blank=True)
    
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    
    # Informations de transaction
    transaction_id = models.CharField(max_length=200, blank=True, unique=True)
    payment_reference = models.CharField(max_length=200, blank=True)
    external_id = models.CharField(max_length=200, blank=True, help_text="ID de transaction externe (Stripe, PayPal, etc.)")
    
    # Informations de paiement
    payer_name = models.CharField(max_length=100, blank=True)
    payer_email = models.EmailField(blank=True)
    payer_phone = models.CharField(max_length=20, blank=True)
    
    # Métadonnées
    metadata = models.JSONField(default=dict, blank=True, help_text="Informations supplémentaires (réponse API, etc.)")
    
    # Dates
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Paiement #{self.id} - {self.amount}€ - {self.get_status_display()}"
    
    class Meta:
        verbose_name = "Paiement"
        verbose_name_plural = "Paiements"
        ordering = ['-created_at']


class Order(models.Model):
    """Système de commande avec localisation"""
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('confirmed', 'Confirmée'),
        ('preparing', 'En préparation'),
        ('ready', 'Prête'),
        ('shipped', 'Expédiée'),
        ('in_transit', 'En transit'),
        ('delivered', 'Livrée'),
        ('cancelled', 'Annulée'),
        ('refunded', 'Remboursée'),
    ]
    
    DELIVERY_METHODS = [
        ('pickup', 'Retrait en magasin'),
        ('delivery', 'Livraison à domicile'),
        ('express', 'Livraison express'),
    ]
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='orders')
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders', null=True, blank=True)
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='orders')
    
    # Informations de localisation
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    address = models.TextField(blank=True, help_text="Adresse de livraison")
    city = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, blank=True)
    
    # Informations de commande
    quantity = models.IntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    delivery_method = models.CharField(max_length=20, choices=DELIVERY_METHODS, default='delivery')
    
    # Informations de contact
    customer_name = models.CharField(max_length=100, blank=True)
    customer_phone = models.CharField(max_length=20, blank=True)
    customer_email = models.EmailField(blank=True)
    
    # Paiement
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, blank=True)
    
    # Livraison
    tracking_number = models.CharField(max_length=100, blank=True)
    estimated_delivery = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    
    # Notes
    notes = models.TextField(blank=True, help_text="Notes du client")
    internal_notes = models.TextField(blank=True, help_text="Notes internes (vendeur)")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Commande #{self.id} - {self.product.name} - {self.get_status_display()}"
    
    def get_google_maps_link(self):
        """Génère un lien Google Maps avec la localisation"""
        if self.latitude and self.longitude:
            return f"https://www.google.com/maps?q={self.latitude},{self.longitude}"
        return None
    
    def get_total_with_delivery(self):
        """Calcule le total avec frais de livraison"""
        return self.total_price + self.delivery_fee
    
    def is_paid(self):
        """Vérifie si la commande est payée"""
        return self.payment_status == 'completed'
    
    class Meta:
        verbose_name = "Commande"
        verbose_name_plural = "Commandes"
        ordering = ['-created_at']


# ============================================================================
# 🔴 LIVE COMMERCE ÉTUDIANT (Comme TikTok Live Shopping)
# ============================================================================

class LiveStream(models.Model):
    """Live Commerce - Stream en direct pour vendre"""
    STATUS_CHOICES = [
        ('scheduled', 'Programmé'),
        ('live', 'En direct'),
        ('ended', 'Terminé'),
        ('cancelled', 'Annulé'),
    ]
    
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='live_streams')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    thumbnail = models.ImageField(upload_to="live_thumbnails/", blank=True)
    
    # Streaming / Reels vidéo
    stream_key = models.CharField(max_length=100, unique=True, blank=True)
    rtmp_url = models.URLField(blank=True)
    hls_url = models.URLField(blank=True)
    video_file = models.FileField(
        upload_to="live_videos/",
        blank=True,
        null=True,
        help_text="Vidéo du reel (MP4, 2–5 minutes)"
    )
    
    # Statut
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    
    # Statistiques
    viewers_count = models.IntegerField(default=0)
    peak_viewers = models.IntegerField(default=0)
    total_sales = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_orders = models.IntegerField(default=0)
    
    # Dates
    scheduled_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Live: {self.title} - {self.store.name}"
    
    def is_live(self):
        return self.status == 'live'
    
    class Meta:
        verbose_name = "Live Stream"
        verbose_name_plural = "Live Streams"
        ordering = ['-scheduled_at', '-created_at']


class LiveProduct(models.Model):
    """Produits présentés pendant un live"""
    live_stream = models.ForeignKey(LiveStream, on_delete=models.CASCADE, related_name='live_products')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='live_appearances')
    
    # Informations spécifiques au live
    live_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Prix spécial pendant le live")
    is_featured = models.BooleanField(default=False, help_text="Produit mis en avant")
    order = models.IntegerField(default=0, help_text="Ordre d'affichage")
    
    # Statistiques
    views_count = models.IntegerField(default=0)
    purchases_count = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['live_stream', 'product']
        verbose_name = "Produit Live"
        verbose_name_plural = "Produits Live"
        ordering = ['order', '-created_at']


class GeneralProfile(models.Model):
    """
    Modèle pour stocker des informations de profil supplémentaires pour les utilisateurs.
    Étend le modèle User par défaut de Django.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='generalprofile',
        verbose_name='Utilisateur'
    )
    
    # Informations personnelles
    phone = models.CharField(
        'Téléphone',
        max_length=20,
        blank=True,
        help_text='Numéro de téléphone au format international (ex: +2250700000000)'
    )
    
    # Photo de profil
    avatar = models.ImageField(
        'Photo de profil',
        upload_to='avatars/',
        blank=True,
        null=True,
        help_text='Téléchargez une photo de profil (taille recommandée: 200x200px)'
    )
    
    # Localisation
    address = models.TextField('Adresse', blank=True)
    city = models.CharField('Ville', max_length=100, blank=True)
    country = models.CharField('Pays', max_length=100, blank=True, default='Côte d\'Ivoire')
    
    # Paramètres de confidentialité
    is_public = models.BooleanField(
        'Profil public',
        default=True,
        help_text='Si coché, votre profil sera visible par tous les visiteurs du site.'
    )
    
    # Statistiques
    profile_views = models.PositiveIntegerField('Vues du profil', default=0)
    last_seen = models.DateTimeField('Dernière connexion', auto_now=True)
    
    # Bio et informations supplémentaires
    bio = models.TextField('À propos de moi', blank=True, help_text='Décrivez-vous en quelques mots')
    
    # Réseaux sociaux (optionnels)
    facebook_url = models.URLField('Profil Facebook', blank=True)
    twitter_handle = models.CharField('Compte Twitter', max_length=50, blank=True)
    instagram_handle = models.CharField('Compte Instagram', max_length=50, blank=True)
    
    # Préférences
    email_notifications = models.BooleanField('Recevoir les notifications par email', default=True)
    newsletter = models.BooleanField('S\'abonner à la newsletter', default=True)
    
    # Métadonnées
    created_at = models.DateTimeField('Date de création', auto_now_add=True)
    updated_at = models.DateTimeField('Dernière mise à jour', auto_now=True)
    
    class Meta:
        verbose_name = 'Profil utilisateur'
        verbose_name_plural = 'Profils utilisateurs'
        ordering = ['-updated_at']
    
    def __str__(self):
        return f'Profil de {self.user.username}'
    
    def get_full_name(self):
        """Retourne le nom complet de l'utilisateur si disponible, sinon le nom d'utilisateur."""
        if self.user.get_full_name():
            return self.user.get_full_name()
        return self.user.username
    
    def get_absolute_url(self):
        """Retourne l'URL du profil de l'utilisateur."""
        from django.urls import reverse
        return reverse('user_profile', kwargs={'user_id': self.user.id})
    
    def get_avatar_url(self):
        """Retourne l'URL de l'avatar ou une image par défaut si non défini."""
        if self.avatar:
            return self.avatar.url
        return '/static/images/default-avatar.png'


class LiveComment(models.Model):
    """Commentaires pendant le live"""
    live_stream = models.ForeignKey(LiveStream, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='live_comments')
    content = models.TextField()
    is_question = models.BooleanField(default=False, help_text="Est-ce une question?")
    is_pinned = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Commentaire Live"
        verbose_name_plural = "Commentaires Live"
        ordering = ['-is_pinned', '-created_at']


class LivePurchase(models.Model):
    """Achats effectués pendant le live"""
    live_stream = models.ForeignKey(LiveStream, on_delete=models.CASCADE, related_name='purchases')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='live_purchases')
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='live_purchases')
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='live_purchases', null=True, blank=True)
    
    quantity = models.IntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Achat Live"
        verbose_name_plural = "Achats Live"
        ordering = ['-created_at']


# ============================================================================
# 📚 FORMATIONS
# ============================================================================

class Formation(models.Model):
    """Modèle pour les formations proposées"""
    NIVEAU_CHOICES = [
        ('debutant', 'Débutant'),
        ('intermediaire', 'Intermédiaire'),
        ('avance', 'Avancé'),
        ('expert', 'Expert'),
    ]
    
    titre = models.CharField(max_length=200, verbose_name="Titre de la formation")
    slug = models.SlugField(max_length=200, unique=True, help_text="URL de la formation (automatique)")
    description = models.TextField(verbose_name="Description détaillée")
    contenu = models.TextField(help_text="Contenu détaillé de la formation (format HTML)", blank=True)
    duree = models.CharField(max_length=100, help_text="Durée estimée (ex: 6 semaines, 3 mois)")
    niveau = models.CharField(max_length=20, choices=NIVEAU_CHOICES, default='debutant')
    prix = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Prix de la formation")
    image = models.ImageField(upload_to='formations/', blank=True, null=True)
    est_actif = models.BooleanField(default=True, verbose_name="Formation active")
    date_creation = models.DateTimeField(auto_now_add=True)
    date_mise_a_jour = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.titre
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.titre)
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name = "Formation"
        verbose_name_plural = "Formations"
        ordering = ['-date_creation']


class ModuleFormation(models.Model):
    """Modules d'une formation"""
    formation = models.ForeignKey(Formation, on_delete=models.CASCADE, related_name='modules')
    titre = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    ordre = models.PositiveIntegerField(default=0)
    duree = models.CharField(max_length=100, blank=True, help_text="Durée estimée du module")
    
    class Meta:
        ordering = ['ordre', 'titre']
        verbose_name = "Module de formation"
        verbose_name_plural = "Modules de formation"
    
    def __str__(self):
        return f"{self.formation.titre} - {self.titre}"


class Lecon(models.Model):
    """Leçons d'un module de formation"""
    module = models.ForeignKey(ModuleFormation, on_delete=models.CASCADE, related_name='lecons')
    titre = models.CharField(max_length=200)
    contenu = models.TextField(help_text="Contenu de la leçon (format HTML)")
    video_url = models.URLField(blank=True, help_text="URL de la vidéo (YouTube, Vimeo, etc.)")
    duree = models.PositiveIntegerField(help_text="Durée en minutes", default=0)
    ordre = models.PositiveIntegerField(default=0)
    est_gratuit = models.BooleanField(default=False, help_text="Cette leçon est-elle gratuite ?")
    
    class Meta:
        ordering = ['ordre', 'titre']
        verbose_name = "Leçon"
        verbose_name_plural = "Leçons"
    
    def __str__(self):
        return f"{self.module.titre} - {self.titre}"


class Certification(models.Model):
    """Certifications délivrées après les formations"""
    formation = models.OneToOneField(Formation, on_delete=models.CASCADE, related_name='certification')
    nom = models.CharField(max_length=200, verbose_name="Nom de la certification")
    description = models.TextField(verbose_name="Description de la certification")
    duree_validite = models.PositiveIntegerField(
        help_text="Durée de validité en mois (0 pour illimité)",
        default=0
    )
    cout_certification = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        default=0,
        verbose_name="Coût de la certification (si non incluse)"
    )
    est_incluse_formation = models.BooleanField(
        default=True,
        help_text="La certification est-elle incluse dans le prix de la formation ?"
    )
    image = models.ImageField(upload_to='certifications/', blank=True, null=True)
    
    def __str__(self):
        return f"{self.formation.titre} - {self.nom}"
    
    class Meta:
        verbose_name = "Certification"
        verbose_name_plural = "Certifications"


class InscriptionFormation(models.Model):
    """Inscription d'un utilisateur à une formation"""
    STATUT_CHOIX = [
        ('en_attente', 'En attente de paiement'),
        ('validee', 'Inscription validée'),
        ('en_cours', 'Formation en cours'),
        ('terminee', 'Formation terminée'),
        ('certifiee', 'Certification obtenue'),
        ('annulee', 'Inscription annulée'),
    ]
    
    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name='inscriptions_formation'
    )
    formation = models.ForeignKey(
        Formation, 
        on_delete=models.CASCADE,
        related_name='inscriptions'
    )
    date_inscription = models.DateTimeField(auto_now_add=True)
    statut = models.CharField(
        max_length=20, 
        choices=STATUT_CHOIX, 
        default='en_attente'
    )
    date_debut = models.DateField(null=True, blank=True)
    date_fin = models.DateField(null=True, blank=True)
    
    # Suivi de progression
    progression = models.PositiveIntegerField(default=0, help_text="Pourcentage de progression")
    derniere_lecon_vue = models.ForeignKey(
        'Lecon', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='derniere_lecon_pour_inscriptions'
    )
    
    # Certification
    certification_obtenue = models.BooleanField(default=False)
    date_certification = models.DateField(null=True, blank=True)
    
    # Paiement
    paiement_effectue = models.BooleanField(default=False)
    montant_paye = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    date_paiement = models.DateTimeField(null=True, blank=True)
    reference_paiement = models.CharField(max_length=100, blank=True)
    mode_paiement = models.CharField(max_length=50, blank=True)
    
    # Métadonnées
    notes = models.TextField(blank=True, help_text="Notes internes")
    
    def __str__(self):
        return f"{self.utilisateur.username} - {self.formation.titre}"
    
    def calculer_progression(self):
        """Calcule la progression de l'étudiant dans la formation"""
        total_lecons = Lecon.objects.filter(module__formation=self.formation).count()
        if total_lecons == 0:
            return 0
            
        lecons_terminees = SuiviLecon.objects.filter(
            inscription=self,
            termine=True
        ).count()
        
        return int((lecons_terminees / total_lecons) * 100)
    
    def mettre_a_jour_progression(self):
        """Met à jour la progression de l'étudiant"""
        self.progression = self.calculer_progression()
        self.save(update_fields=['progression'])
        return self.progression
    
    class Meta:
        verbose_name = "Inscription à une formation"
        verbose_name_plural = "Inscriptions aux formations"
        ordering = ['-date_inscription']
        unique_together = ['utilisateur', 'formation']


class SuiviLecon(models.Model):
    """Suivi de la progression d'un étudiant pour une leçon"""
    inscription = models.ForeignKey(
        InscriptionFormation, 
        on_delete=models.CASCADE,
        related_name='suivi_lecons'
    )
    lecon = models.ForeignKey(
        Lecon,
        on_delete=models.CASCADE,
        related_name='suivis'
    )
    date_debut = models.DateTimeField(auto_now_add=True)
    date_fin = models.DateTimeField(null=True, blank=True)
    duree_totale = models.PositiveIntegerField(
        default=0,
        help_text="Durée totale de visualisation en secondes"
    )
    termine = models.BooleanField(default=False)
    date_derniere_activite = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Suivi de leçon"
        verbose_name_plural = "Suivis de leçons"
        unique_together = ['inscription', 'lecon']
    
    def __str__(self):
        return f"{self.inscription} - {self.lecon.titre}"
    
    def marquer_comme_terminee(self):
        """Marque la leçon comme terminée"""
        self.termine = True
        self.date_fin = timezone.now()
        self.save()
        # Mettre à jour la progression de l'inscription
        self.inscription.mettre_a_jour_progression()


# ============================================================================
# 📄 PROFIL ÉTUDIANT / CV INTÉGRÉ (LinkedIn pour étudiants)
# ============================================================================

class StudentProfile(models.Model):
    """Profil professionnel étudiant"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    
    # Informations académiques
    university = models.CharField(max_length=200, blank=True)
    field_of_study = models.CharField(max_length=200, blank=True, verbose_name="Domaine d'études")
    degree_level = models.CharField(max_length=50, blank=True, help_text="Licence, Master, Doctorat, etc.")
    graduation_year = models.IntegerField(null=True, blank=True)
    gpa = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True, verbose_name="Moyenne")
    
    # Informations professionnelles
    bio = models.TextField(blank=True, verbose_name="Biographie")
    resume_file = models.FileField(upload_to="resumes/", blank=True, null=True, verbose_name="CV PDF")
    profile_picture = models.ImageField(upload_to="student_profiles/", blank=True)
    cover_photo = models.ImageField(upload_to="student_covers/", blank=True)
    
    # Contact
    phone = models.CharField(max_length=20, blank=True)
    email_public = models.EmailField(blank=True, help_text="Email public (optionnel)")
    website = models.URLField(blank=True)
    linkedin_url = models.URLField(blank=True)
    github_url = models.URLField(blank=True)
    portfolio_url = models.URLField(blank=True)
    
    # Localisation
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    # Statut
    is_verified = models.BooleanField(default=False, verbose_name="Profil vérifié")
    is_public = models.BooleanField(default=True, verbose_name="Profil public")
    
    # Statistiques
    profile_views = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Profil: {self.user.username}"
    
    class Meta:
        verbose_name = "Profil Étudiant"
        verbose_name_plural = "Profils Étudiants"
        ordering = ['-created_at']


    phone = models.CharField(max_length=20, blank=True)
    email_public = models.EmailField(blank=True, help_text="Email public (optionnel)")
    website = models.URLField(blank=True)
    linkedin_url = models.URLField(blank=True)
    github_url = models.URLField(blank=True)
    portfolio_url = models.URLField(blank=True)
    
    # Localisation
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    
    # Paramètres de confidentialité
    is_public = models.BooleanField(default=True, verbose_name="Profil public")
    
    # Statistiques
    profile_views = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Profil général: {self.user.username}"
    
    class Meta:
        verbose_name = "Profil Général"
        verbose_name_plural = "Profils Généraux"


class Skill(models.Model):
    """Compétences de l'étudiant"""
    SKILL_LEVELS = [
        ('beginner', 'Débutant'),
        ('intermediate', 'Intermédiaire'),
        ('advanced', 'Avancé'),
        ('expert', 'Expert'),
    ]
    
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='skills')
    name = models.CharField(max_length=100)
    level = models.CharField(max_length=20, choices=SKILL_LEVELS, default='intermediate')
    category = models.CharField(max_length=100, blank=True, help_text="Ex: Programmation, Design, Marketing")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Compétence"
        verbose_name_plural = "Compétences"
        ordering = ['-level', 'name']


class Portfolio(models.Model):
    """Portfolio de projets"""
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='portfolio_items')
    title = models.CharField(max_length=200)
    description = models.TextField()
    image = models.ImageField(upload_to="portfolio/", blank=True)
    url = models.URLField(blank=True)
    github_url = models.URLField(blank=True)
    technologies = models.CharField(max_length=500, blank=True, help_text="Technologies utilisées (séparées par des virgules)")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Portfolio"
        verbose_name_plural = "Portfolios"
        ordering = ['-created_at']


class Project(models.Model):
    """Projets scolaires"""
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='projects')
    title = models.CharField(max_length=200)
    description = models.TextField()
    course = models.CharField(max_length=200, blank=True, help_text="Nom du cours")
    grade = models.CharField(max_length=20, blank=True, help_text="Note obtenue")
    file = models.FileField(upload_to="projects/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Projet Scolaire"
        verbose_name_plural = "Projets Scolaires"
        ordering = ['-created_at']


class Recommendation(models.Model):
    """Recommandations (témoignages)"""
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='recommendations')
    recommender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='given_recommendations')
    recommender_name = models.CharField(max_length=100, blank=True, help_text="Nom du recommandeur (si pas utilisateur)")
    recommender_title = models.CharField(max_length=200, blank=True, help_text="Titre/fonction du recommandeur")
    content = models.TextField()
    rating = models.IntegerField(default=5, help_text="Note de 1 à 5")
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Recommandation"
        verbose_name_plural = "Recommandations"
        ordering = ['-created_at']


# ============================================================================
# 💼 CAMPUS JOBS (Petits jobs entre étudiants)
# ============================================================================

class JobCategory(models.Model):
    """Catégories de jobs"""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    icon = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Catégorie de Job"
        verbose_name_plural = "Catégories de Jobs"
        ordering = ['name']


class Job(models.Model):
    """Offres d'emploi/jobs entre étudiants"""
    STATUS_CHOICES = [
        ('open', 'Ouvert'),
        ('in_progress', 'En cours'),
        ('completed', 'Terminé'),
        ('cancelled', 'Annulé'),
    ]
    
    PAYMENT_TYPES = [
        ('fixed', 'Prix fixe'),
        ('hourly', 'À l\'heure'),
        ('negotiable', 'Négociable'),
    ]
    
    # Informations de base
    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.ForeignKey(JobCategory, on_delete=models.SET_NULL, null=True, related_name='jobs')
    
    # Posteur
    posted_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posted_jobs')
    student_profile = models.ForeignKey(StudentProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='jobs')
    
    # Localisation
    location = models.CharField(max_length=200, blank=True)
    is_remote = models.BooleanField(default=False, verbose_name="Travail à distance")
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    # Rémunération
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPES, default='fixed')
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    amount_max = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Pour prix négociable")
    currency = models.CharField(max_length=10, default='XOF', help_text="XOF, EUR, USD, etc.")
    
    # Statut
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    
    # Dates
    deadline = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Statistiques
    views_count = models.IntegerField(default=0)
    applications_count = models.IntegerField(default=0)
    
    def __str__(self):
        return self.title
    
    class Meta:
        verbose_name = "Job"
        verbose_name_plural = "Jobs"
        ordering = ['-created_at']


class JobApplication(models.Model):
    """Candidatures aux jobs"""
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('accepted', 'Acceptée'),
        ('rejected', 'Refusée'),
        ('withdrawn', 'Retirée'),
    ]
    
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='applications')
    applicant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='job_applications')
    student_profile = models.ForeignKey(StudentProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='applications')
    
    cover_letter = models.TextField(blank=True, verbose_name="Lettre de motivation")
    proposed_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    estimated_duration = models.CharField(max_length=100, blank=True, help_text="Ex: 2 semaines, 1 mois")
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['job', 'applicant']
        verbose_name = "Candidature"
        verbose_name_plural = "Candidatures"
        ordering = ['-created_at']


# ============================================================================
# 🎓 CLASSROOM (Étudier ensemble)
# ============================================================================

class Classroom(models.Model):
    """Classes virtuelles pour étudier ensemble"""
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    course_code = models.CharField(max_length=50, blank=True, help_text="Code du cours (ex: INFO101)")
    university = models.CharField(max_length=200, blank=True)
    
    # Créateur
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_classrooms')
    
    # Membres
    members = models.ManyToManyField(User, related_name='classrooms', blank=True)
    is_public = models.BooleanField(default=True, verbose_name="Classe publique")
    invite_code = models.CharField(max_length=20, unique=True, blank=True, help_text="Code d'invitation")
    
    # Statistiques
    members_count = models.IntegerField(default=0)
    posts_count = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Classe"
        verbose_name_plural = "Classes"
        ordering = ['-created_at']


class ClassPost(models.Model):
    """Posts dans une classe"""
    POST_TYPES = [
        ('question', 'Question'),
        ('note', 'Note'),
        ('resource', 'Ressource'),
        ('announcement', 'Annonce'),
        ('discussion', 'Discussion'),
    ]
    
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name='posts')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='class_posts')
    post_type = models.CharField(max_length=20, choices=POST_TYPES, default='discussion')
    
    title = models.CharField(max_length=200, blank=True)
    content = models.TextField()
    file = models.FileField(upload_to="class_posts/", blank=True, null=True)
    
    # Interactions
    likes = models.ManyToManyField(
        User, 
        related_name='liked_class_posts',
        blank=True
    )
    likes_count = models.IntegerField(default=0)
    comments_count = models.IntegerField(default=0)
    is_pinned = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Post de Classe"
        verbose_name_plural = "Posts de Classe"
        ordering = ['-is_pinned', '-created_at']


class ClassNote(models.Model):
    """Notes collaboratives"""
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name='notes')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='class_notes')
    
    title = models.CharField(max_length=200)
    content = models.TextField()
    topic = models.CharField(max_length=200, blank=True, help_text="Sujet/chapitre")
    
    # Collaboration
    is_shared = models.BooleanField(default=True, verbose_name="Partagé avec la classe")
    contributors = models.ManyToManyField(User, related_name='contributed_notes', blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Note de Classe"
        verbose_name_plural = "Notes de Classe"
        ordering = ['-updated_at']


class Tutorial(models.Model):
    """Tutoriels partagés"""
    TUTORIAL_TYPES = [
        ('video', 'Vidéo'),
        ('article', 'Article'),
        ('pdf', 'PDF'),
        ('link', 'Lien externe'),
    ]
    
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name='tutorials', null=True, blank=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tutorials')
    
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    tutorial_type = models.CharField(max_length=20, choices=TUTORIAL_TYPES, default='video')
    
    # Contenu
    video_url = models.URLField(blank=True)
    article_content = models.TextField(blank=True)
    file = models.FileField(upload_to="tutorials/", blank=True, null=True)
    external_url = models.URLField(blank=True)
    
    # Statistiques
    views_count = models.IntegerField(default=0)
    likes_count = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Tutoriel"
        verbose_name_plural = "Tutoriels"
        ordering = ['-created_at']


# ============================================================================
# 🤖 ASSISTANT IA (Pour aider à vendre)
# ============================================================================

class AIRequest(models.Model):
    """Requêtes à l'assistant IA"""
    REQUEST_TYPES = [
        ('product_description', 'Description de produit'),
        ('image_generation', 'Génération d\'image'),
        ('translation', 'Traduction'),
        ('pricing', 'Prix optimal'),
        ('tags', 'Étiquettes automatiques'),
        ('title', 'Titre optimisé'),
        ('marketing_text', 'Texte marketing'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('processing', 'En traitement'),
        ('completed', 'Terminé'),
        ('failed', 'Échoué'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ai_requests')
    request_type = models.CharField(max_length=30, choices=REQUEST_TYPES)
    
    # Contexte
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True, related_name='ai_requests')
    store = models.ForeignKey(Store, on_delete=models.CASCADE, null=True, blank=True, related_name='ai_requests')
    
    # Input
    input_text = models.TextField(blank=True, help_text="Texte d'entrée")
    input_language = models.CharField(max_length=10, default='fr')
    target_language = models.CharField(max_length=10, blank=True, help_text="Pour traduction")
    
    # Output
    output_text = models.TextField(blank=True, help_text="Résultat généré")
    output_image = models.ImageField(upload_to="ai_generated/", blank=True, null=True)
    metadata = models.JSONField(default=dict, blank=True, help_text="Métadonnées (tags, prix suggéré, etc.)")
    
    # Statut
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    error_message = models.TextField(blank=True)
    
    # Coût (si applicable)
    tokens_used = models.IntegerField(default=0)
    cost = models.DecimalField(max_digits=10, decimal_places=4, default=0.0000)
    
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Requête IA"
        verbose_name_plural = "Requêtes IA"
        ordering = ['-created_at']


# ============================================================================
# 🔒 SYSTÈME ANTI-ARNaque
# ============================================================================

class FraudReport(models.Model):
    """Signalements d'arnaque"""
    REPORT_TYPES = [
        ('fake_account', 'Compte faux'),
        ('scam_product', 'Produit arnaque'),
        ('fake_review', 'Avis faux'),
        ('payment_fraud', 'Fraude de paiement'),
        ('other', 'Autre'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('under_review', 'En cours d\'examen'),
        ('resolved', 'Résolu'),
        ('dismissed', 'Rejeté'),
    ]
    
    reported_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='fraud_reports')
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES)
    
    # Cible du signalement
    reported_user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='reports_against')
    reported_store = models.ForeignKey(Store, on_delete=models.CASCADE, null=True, blank=True, related_name='reports')
    reported_product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True, related_name='reports')
    
    # Détails
    description = models.TextField()
    evidence = models.FileField(upload_to="fraud_evidence/", blank=True, null=True)
    
    # Statut
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    admin_notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Signalement"
        verbose_name_plural = "Signalements"
        ordering = ['-created_at']


class AccountVerification(models.Model):
    """Vérification d'identité"""
    VERIFICATION_TYPES = [
        ('student_id', 'Carte étudiante'),
        ('national_id', 'Carte nationale'),
        ('phone', 'Vérification téléphone'),
        ('email', 'Vérification email'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('approved', 'Approuvé'),
        ('rejected', 'Rejeté'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='verifications')
    verification_type = models.CharField(max_length=20, choices=VERIFICATION_TYPES)
    
    # Documents
    document_file = models.FileField(upload_to="verifications/", blank=True, null=True)
    document_number = models.CharField(max_length=100, blank=True)
    
    # Statut
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    admin_notes = models.TextField(blank=True)
    
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Vérification"
        verbose_name_plural = "Vérifications"
        ordering = ['-submitted_at']