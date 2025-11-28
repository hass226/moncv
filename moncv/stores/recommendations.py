from django.db.models import Count, Q, F, Case, When, Value, IntegerField, BooleanField, Avg, Sum, ExpressionWrapper, DurationField, FloatField
from django.db.models.functions import Coalesce, ExtractDay
from django.utils import timezone
from datetime import timedelta
import random

from .models import Product, Store, Promotion, Subscription, Category, SearchHistory, Like, Favorite


def get_similar_products(product, limit=5, user=None):
    """Retourne une liste de produits similaires pour les recommandations.
    
    Nouvelle logique de scoring :
    - Même catégorie : +30 points
    - Même boutique : +20 points
    - Mots-clés similaires : +10 points par mot-clé correspondant
    - Produit en vedette : +15 points
    - Boutique vérifiée : +10 points
    - Note moyenne : + (note * 5) points
    - Nombre de vues : + (vues / 100) points
    - Nombre de likes : + (likes * 2) points
    - Fraîcheur : + (jours depuis création / 10) points
    """
    from django.db.models.functions import Length
    
    # Récupérer les mots-clés du produit
    keywords = set()
    if product.name:
        keywords.update(product.name.lower().split()[:5])
    if product.description:
        keywords.update(product.description.lower().split()[:10])
    
    # Créer une requête de base
    qs = Product.objects.exclude(id=product.id)
    
    # Calculer le score pour chaque produit
    qs = qs.annotate(
        # Score de base
        score=Value(0, output_field=IntegerField()),
        
        # Score pour la catégorie
        category_score=Case(
            When(category=product.category, then=Value(30)),
            default=Value(0),
            output_field=IntegerField()
        ),
        
        # Score pour la boutique
        store_score=Case(
            When(store=product.store, then=Value(20)),
            default=Value(0),
            output_field=IntegerField()
        ),
        
        # Score pour les mots-clés (à calculer plus tard)
        keyword_score=Value(0, output_field=IntegerField()),
        
        # Score pour les produits en vedette
        featured_score=Case(
            When(is_featured=True, then=Value(15)),
            default=Value(0),
            output_field=IntegerField()
        ),
        
        # Score pour les boutiques vérifiées
        verified_score=Case(
            When(store__is_verified=True, then=Value(10)),
            default=Value(0),
            output_field=IntegerField()
        ),
        
        # Score pour la note moyenne
        rating_score=Coalesce(
            Avg('reviews__rating') * 5,
            Value(0),
            output_field=IntegerField()
        ),
        
        # Score pour les vues
        views_score=F('views_count') / 100,
        
        # Score pour les likes
        likes_score=F('likes_count') * 2,
        
        # Score de fraîcheur (plus récent = meilleur score)
        # Utilisation d'une approche différente pour calculer les jours écoulés
        days_since_created=ExpressionWrapper(
            (timezone.now().date() - F('created_at__date')),
            output_field=DurationField()
        ),
        # Conversion en score (1 jour = 0.1 point)
        freshness_score=Case(
            When(created_at__isnull=False, then=Value(10.0)),  # Valeur par défaut pour les nouveaux produits
            default=Value(0.0),
            output_field=FloatField()
        )
    )
    
    # Calculer le score total
    qs = qs.annotate(
        total_score=(
            F('category_score') + 
            F('store_score') + 
            F('featured_score') + 
            F('verified_score') + 
            F('rating_score') + 
            F('views_score') + 
            F('likes_score') + 
            Coalesce(F('freshness_score'), 0.0)
        )
    )
    
    # Trier par score total
    qs = qs.order_by('-total_score', '-created_at')
    
    # Limiter les résultats
    return qs[:limit]


def get_promoted_products(limit=10):
    """Récupère les produits en promotion, triés par date d'expiration"""
    now = timezone.now()
    return Product.objects.filter(
        promotions__status='active',
        promotions__starts_at__lte=now,
        promotions__expires_at__gt=now
    ).order_by('promotions__expires_at')[:limit]


def get_verified_store_products(limit=10):
    """Récupère les produits des boutiques vérifiées"""
    return Product.objects.filter(
        store__is_verified=True
    ).order_by('-created_at')[:limit]


def get_personalized_feed(user, limit=20):
    """Génère un fil d'actualité personnalisé selon la hiérarchie demandée
    
    Nouvelle hiérarchie de recommandation :
    1. Produits des boutiques suivies par l'utilisateur (s'ils existent)
    2. Produits des catégories préférées de l'utilisateur
    3. Produits similaires aux produits likés/consultés
    4. Produits tendance (les plus populaires)
    5. Nouveautés (derniers produits ajoutés)
    
    Chaque section est limitée pour assurer de la diversité dans les recommandations.
    """
    from django.db.models import Count, Q, F, Case, When, Value, IntegerField
    from django.utils import timezone
    
    # Initialiser la liste des produits recommandés
    recommended_products = []
    
    # 1. Produits des boutiques suivies
    if user is not None and user.is_authenticated:
        followed_stores = user.following.values_list('store_id', flat=True)
        if followed_stores:
            followed_products = Product.objects.filter(
                store_id__in=followed_stores
            ).annotate(
                is_followed_store=Value(True, output_field=BooleanField())
            ).order_by('-created_at')
            
            # Prendre jusqu'à 30% des recommandations
            take = min(limit // 3, followed_products.count())
            recommended_products.extend(list(followed_products[:take]))
    
    # 2. Produits des catégories préférées
    if user is not None and user.is_authenticated and len(recommended_products) < limit:
        # Récupérer les catégories préférées de l'utilisateur
        favorite_categories = Category.objects.filter(
            products__favorites__user=user
        ).annotate(
            fav_count=Count('products__favorites')
        ).order_by('-fav_count')[:3]
        
        if favorite_categories:
            category_products = Product.objects.filter(
                category__in=favorite_categories
            ).exclude(
                id__in=[p.id for p in recommended_products]
            ).annotate(
                is_favorite_category=Value(True, output_field=BooleanField())
            ).order_by('-created_at')
            
            # Prendre jusqu'à 30% des recommandations
            take = min(limit // 3, category_products.count())
            recommended_products.extend(list(category_products[:take]))
    
    # 3. Produits similaires aux produits likés/consultés
    if user is not None and user.is_authenticated and len(recommended_products) < limit:
        # Récupérer les produits likés par l'utilisateur
        liked_products = Product.objects.filter(
            likes__user=user
        ).order_by('-likes__created_at')[:3]
        
        similar_products = []
        for product in liked_products:
            # Obtenir des produits similaires pour chaque produit aimé
            similar = get_similar_products(product, limit=3)
            similar_products.extend([p for p in similar if p not in recommended_products])
        
        # Ajouter jusqu'à 20% des recommandations
        take = min(limit // 5, len(similar_products))
        recommended_products.extend(similar_products[:take])
    
    # 4. Produits tendance (les plus populaires)
    if len(recommended_products) < limit:
        needed = limit - len(recommended_products)
        if needed > 0:
            # Produits les plus populaires (vues + likes)
            trending_products = Product.objects.annotate(
                popularity=Count('likes') * 2 + Count('views_count')
            ).exclude(
                id__in=[p.id for p in recommended_products]
            ).order_by('-popularity', '-created_at')
            
            # Prendre jusqu'à 20% des recommandations
            take = min(needed, trending_products.count())
            recommended_products.extend(list(trending_products[:take]))
    
    # 5. Derniers produits ajoutés (pour compléter)
    if len(recommended_products) < limit:
        needed = limit - len(recommended_products)
        if needed > 0:
            new_products = Product.objects.exclude(
                id__in=[p.id for p in recommended_products]
            ).order_by('-created_at')[:needed]
            
            recommended_products.extend(list(new_products))
    
    # Mélanger les recommandations pour plus de variété
    random.shuffle(recommended_products)
    
    # Retourner le nombre demandé de produits
    return recommended_products[:limit]


def get_store_recommendations(store, limit=5):
    """Recommandations de boutiques similaires"""
    # Logique de recommandation de boutiques similaires
    # Basé sur les catégories, la localisation, etc.
    return Store.objects.exclude(id=store.id).filter(
        is_verified=True
    ).annotate(
        similar_categories=Count('products__category', filter=Q(products__category__in=store.products.values('category')))
    ).order_by('-similar_categories', '-created_at')[:limit]
    
    # 2. Produits des boutiques certifiées (limite à 30% du feed)
    verified_limit = int(limit * 0.3)
    verified_products = list(get_verified_store_products(verified_limit))
    
    # 3. Autres produits recommandés (le reste)
    remaining_limit = limit - len(promoted_products) - len(verified_products)
    recommended_products = []
    
    if remaining_limit > 0:
        # Si l'utilisateur est connecté, on peut personnaliser les recommandations
        if user is not None and user.is_authenticated:
            # Produits des boutiques suivies
            followed_stores = user.following.values_list('store_id', flat=True)
            if followed_stores:
                recommended_products = list(Product.objects.filter(
                    store_id__in=followed_stores
                ).exclude(
                    id__in=[p.id for p in promoted_products + verified_products]
                ).order_by('-created_at')[:remaining_limit])
        
        # Si on n'a pas assez de produits recommandés ou utilisateur non connecté
        if len(recommended_products) < remaining_limit:
            # Produits populaires
            popular_products = Product.objects.annotate(
                popularity=Count('likes') * 3 + Count('comments') * 2 + Count('views_count')
            ).exclude(
                id__in=[p.id for p in promoted_products + verified_products + recommended_products]
            ).order_by('-popularity', '-created_at')[:remaining_limit - len(recommended_products)]
            
            recommended_products.extend(list(popular_products))
    
    # Combiner les listes en respectant la hiérarchie
    feed = []
    feed.extend(promoted_products)
    feed.extend(verified_products)
    feed.extend(recommended_products)
    
    # S'assurer qu'on ne dépasse pas la limite
    return feed[:limit]


def get_store_recommendations(store, limit=5):
    """Recommandations de boutiques similaires"""
    # Trouver des boutiques avec des produits de mêmes catégories
    categories = store.products.values_list('category_id', flat=True).distinct()
    
    return Store.objects.filter(
        products__category_id__in=categories
    ).exclude(
        id=store.id
    ).annotate(
        common_categories=Count('products__category', filter=Q(products__category_id__in=categories)),
        is_verified=Case(
            When(is_verified=True, then=Value(1)),
            default=Value(0),
            output_field=IntegerField()
        )
    ).order_by(
        '-is_verified', '-common_categories', '-products__created_at'
    ).distinct()[:limit]
