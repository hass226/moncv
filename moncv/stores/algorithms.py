"""
🧠 Algorithmes Intelligents pour MYMEDAGA
Recommandations personnalisées, géo-découverte, anti-arnaque
"""

from django.db.models import Q, Count, Avg, F, Case, When, IntegerField, Sum, Max
from datetime import timedelta
from django.utils import timezone
import math

# Géolocalisation avec geopy (plus simple que django.contrib.gis)
try:
    from geopy.distance import geodesic
    GEOPY_AVAILABLE = True
except ImportError:
    GEOPY_AVAILABLE = False
    # Fonction factice si geopy n'est pas disponible
    def geodesic(point1, point2):
        class Distance:
            kilometers = 0
        return Distance()


def calculate_product_score(product, user=None):
    """
    Calcule un score algorithmique pour un produit
    Utilisé pour le feed intelligent (comme TikTok)
    """
    score = 0
    
    # Likes (poids: 3)
    score += product.likes_count * 3
    
    # Commentaires (poids: 2)
    score += product.comments.count() * 2
    
    # Partages (poids: 5 - très important)
    score += product.shares_count * 5
    
    # Vues (poids: 0.1)
    score += product.views_count * 0.1
    
    # Produit en vedette (poids: 10)
    if product.is_currently_featured():
        score += 10
    
    # Boutique vérifiée (poids: 5)
    if product.store.is_verified:
        score += 5
    
    # Fraîcheur (produits récents ont un bonus)
    days_old = (timezone.now() - product.created_at).days
    freshness_bonus = max(0, 10 - days_old * 0.5)
    score += freshness_bonus
    
    # Note moyenne (poids: 2)
    avg_rating = product.get_average_rating()
    score += avg_rating * 2
    
    # Personnalisation si utilisateur connecté
    if user and user.is_authenticated:
        # Bonus si l'utilisateur suit la boutique
        if product.store.followers.filter(user=user).exists():
            score += 15
        
        # Bonus si l'utilisateur a liké des produits similaires
        user_liked_categories = product.__class__.objects.filter(
            likes__user=user
        ).values_list('category_id', flat=True).distinct()
        
        if product.category_id in user_liked_categories:
            score += 8
    
    return score


def get_personalized_recommendations(user, limit=20):
    """
    Recommandations personnalisées basées sur:
    - Historique de likes
    - Boutiques suivies
    - Catégories préférées
    - Produits similaires
    """
    from .models import Product, Like, Follow, Favorite
    
    if not user.is_authenticated:
        # Pour non-connectés: produits populaires
        return Product.objects.annotate(
            score=Count('likes') * 3 + Count('comments') * 2
        ).order_by('-score', '-created_at')
    
    # Catégories préférées de l'utilisateur
    liked_products = Like.objects.filter(user=user).values_list('product_id', flat=True)
    liked_categories = Product.objects.filter(
        id__in=liked_products
    ).values_list('category_id', flat=True).distinct()
    
    # Boutiques suivies
    followed_stores = Follow.objects.filter(user=user).values_list('store_id', flat=True)
    
    # Produits favoris (pour trouver des produits similaires)
    favorite_products = Favorite.objects.filter(user=user).values_list('product_id', flat=True)
    
    # Construire la requête (sans slice pour permettre les filtres supplémentaires)
    recommendations = Product.objects.annotate(
        score=Case(
            # Produits des boutiques suivies (très prioritaire)
            When(store_id__in=followed_stores, then=20),
            default=0,
            output_field=IntegerField()
        ) +
        Case(
            # Produits des catégories préférées
            When(category_id__in=liked_categories, then=10),
            default=0,
            output_field=IntegerField()
        ) +
        # Score algorithmique de base
        Count('likes') * 3 +
        Count('comments') * 2 +
        Count('shares') * 5 +
        F('views_count') * 0.1 +
        Case(
            When(is_featured=True, then=10),
            default=0,
            output_field=IntegerField()
        ) +
        Case(
            When(store__is_verified=True, then=5),
            default=0,
            output_field=IntegerField()
        )
    ).exclude(
        id__in=liked_products  # Exclure les produits déjà likés
    ).order_by('-score', '-created_at')
    
    # Appliquer la limite seulement à la fin si nécessaire
    if limit:
        return recommendations[:limit]
    return recommendations


def get_geo_products(user_lat, user_lng, radius_km=50, limit=20):
    """
    Découverte géographique: produits proches de la position
    """
    from .models import Product, Store, Order
    
    if not GEOPY_AVAILABLE:
        # Si geopy n'est pas disponible, retourner les produits récents
        return Product.objects.order_by('-created_at')[:limit]
    
    if not user_lat or not user_lng:
        return Product.objects.none()
    
    user_location = (float(user_lat), float(user_lng))
    
    # Récupérer tous les produits avec leurs boutiques
    products = Product.objects.select_related('store').all()
    
    nearby_products = []
    
    for product in products:
        # Si la boutique a une localisation
        if hasattr(product.store, 'latitude') and hasattr(product.store, 'longitude'):
            if product.store.latitude and product.store.longitude:
                store_location = (float(product.store.latitude), float(product.store.longitude))
                distance = geodesic(user_location, store_location).kilometers
                
                if distance <= radius_km:
                    product.distance_km = round(distance, 2)
                    nearby_products.append(product)
        
        # Sinon, utiliser les commandes récentes pour estimer la localisation
        # (si des commandes ont été passées depuis cette zone)
        recent_orders = Order.objects.filter(
            product=product,
            latitude__isnull=False,
            longitude__isnull=False
        ).exclude(latitude=0, longitude=0)[:5]
        
        if recent_orders.exists():
            for order in recent_orders:
                order_location = (float(order.latitude), float(order.longitude))
                distance = geodesic(user_location, order_location).kilometers
                
                if distance <= radius_km:
                    product.distance_km = round(distance, 2)
                    if product not in nearby_products:
                        nearby_products.append(product)
                    break
    
    # Trier par distance
    nearby_products.sort(key=lambda x: getattr(x, 'distance_km', 999))
    
    return nearby_products[:limit]


def detect_fraud_risk(user, store=None, product=None):
    """
    Détection d'arnaque intelligente
    Retourne un score de risque (0-100)
    """
    from .models import FraudReport, Review, Order, AccountVerification
    
    risk_score = 0
    
    # Vérifications de base
    if user:
        # Compte récent (moins de 7 jours)
        days_since_join = (timezone.now() - user.date_joined).days
        if days_since_join < 7:
            risk_score += 20
        
        # Pas de vérification
        if not AccountVerification.objects.filter(user=user, status='approved').exists():
            risk_score += 15
        
        # Signalements contre cet utilisateur
        reports_count = FraudReport.objects.filter(
            reported_user=user,
            status__in=['pending', 'under_review']
        ).count()
        risk_score += reports_count * 10
        
        # Avis suspects (tous 5 étoiles, très courts, même pattern)
        if store:
            reviews = Review.objects.filter(product__store=store)
            if reviews.count() > 0:
                avg_rating = reviews.aggregate(Avg('rating'))['rating__avg']
                if avg_rating == 5.0 and reviews.count() < 3:
                    risk_score += 15
                
                # Avis très courts (spam)
                short_reviews = reviews.filter(comment__length__lt=10).count()
                if short_reviews > reviews.count() * 0.5:
                    risk_score += 10
    
    if store:
        # Boutique sans produits
        if store.products.count() == 0:
            risk_score += 10
        
        # Boutique récente avec beaucoup de commandes (suspect)
        days_since_creation = (timezone.now() - store.created_at).days
        orders_count = Order.objects.filter(store=store).count()
        if days_since_creation < 3 and orders_count > 10:
            risk_score += 25
    
    if product:
        # Prix suspect (trop bas ou trop haut)
        avg_price = Product.objects.filter(
            category=product.category
        ).aggregate(Avg('price'))['price__avg']
        
        if avg_price:
            price_ratio = float(product.price) / float(avg_price)
            if price_ratio < 0.3 or price_ratio > 3.0:
                risk_score += 15
        
        # Produit sans image ou description très courte
        if not product.image or len(product.description) < 20:
            risk_score += 10
    
    return min(100, risk_score)


def get_recommended_stores(user, limit=10):
    """
    Recommandations de boutiques à suivre
    """
    from .models import Store, Follow
    
    if not user.is_authenticated:
        return Store.objects.filter(
            is_verified=True,
            is_featured=True
        )[:limit]
    
    # Exclure les boutiques déjà suivies
    followed_stores = Follow.objects.filter(user=user).values_list('store_id', flat=True)
    
    # Recommandations basées sur:
    # - Boutiques vérifiées
    # - Popularité (followers, produits, ventes)
    # - Similarité avec les boutiques suivies
    recommended = Store.objects.annotate(
        score=Count('followers') * 2 +
        Count('products') * 1 +
        Case(
            When(is_verified=True, then=20),
            default=0,
            output_field=IntegerField()
        ) +
        Case(
            When(is_featured=True, then=10),
            default=0,
            output_field=IntegerField()
        )
    ).exclude(
        id__in=followed_stores
    ).order_by('-score', '-created_at')[:limit]
    
    return recommended


def get_recommended_jobs(user, limit=20):
    """
    Recommandations de jobs basées sur:
    - Compétences de l'étudiant
    - Localisation
    - Catégorie
    """
    from .models import Job, StudentProfile, Skill
    
    if not user.is_authenticated:
        return Job.objects.filter(status='open').order_by('-created_at')[:limit]
    
    # Récupérer le profil étudiant
    try:
        profile = user.student_profile
        user_skills = profile.skills.values_list('name', flat=True)
        user_categories = profile.skills.values_list('category', flat=True).distinct()
    except:
        user_skills = []
        user_categories = []
    
    # Jobs correspondant aux compétences
    jobs = Job.objects.filter(status='open').annotate(
        score=Case(
            # Jobs dans les catégories correspondantes
            When(category__name__in=user_categories, then=15),
            default=0,
            output_field=IntegerField()
        ) +
        # Fraîcheur
        Case(
            When(created_at__gte=timezone.now() - timedelta(days=7), then=10),
            default=0,
            output_field=IntegerField()
        ) +
        # Popularité
        F('views_count') * 0.1
    ).order_by('-score', '-created_at')[:limit]
    
    return jobs


def get_trending_products(days=7, limit=20):
    """
    Produits tendance (les plus populaires récemment)
    """
    from .models import Product
    
    since = timezone.now() - timedelta(days=days)
    
    trending = Product.objects.filter(
        created_at__gte=since
    ).annotate(
        trending_score=Count('likes') * 3 +
        Count('comments') * 2 +
        Count('shares') * 5 +
        F('views_count') * 0.1
    ).order_by('-trending_score', '-created_at')[:limit]
    
    return trending


def calculate_store_trust_score(store):
    """
    Score de confiance d'une boutique (0-100)
    """
    from .models import Review, Order, FraudReport
    
    score = 50  # Score de base
    
    # Vérification
    if store.is_verified:
        score += 30
    
    # Avis positifs
    reviews = Review.objects.filter(product__store=store)
    if reviews.count() > 0:
        avg_rating = reviews.aggregate(Avg('rating'))['rating__avg']
        score += (avg_rating - 3) * 5  # Bonus pour notes > 3
    
    # Nombre d'avis (plus il y en a, plus c'est fiable)
    if reviews.count() >= 10:
        score += 10
    elif reviews.count() >= 5:
        score += 5
    
    # Commandes complétées
    completed_orders = Order.objects.filter(
        store=store,
        status='delivered'
    ).count()
    if completed_orders > 0:
        score += min(10, completed_orders / 10)
    
    # Signalements (pénalité)
    reports = FraudReport.objects.filter(
        reported_store=store,
        status__in=['pending', 'under_review']
    ).count()
    score -= reports * 5
    
    return max(0, min(100, score))

