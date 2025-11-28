from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils import timezone
from django.http import JsonResponse
from django.db.models import Q, Count, Avg, F, Case, When, IntegerField, Sum
from django.views.decorators.http import require_POST, require_http_methods
from django.utils import translation
from django.utils.text import slugify
import json
from .recommendations import get_similar_products

# Les vues de paiement sont importées directement dans urls.py
from .models import (
    Store, Product, ProductImage, Subscription, Promotion, Category, Tag,
    Follow, Like, Comment, Share, Review, Favorite, Notification, SearchHistory,
    Payment, Order, GeneralProfile
)
from .forms import (
    UserRegisterForm, StoreForm, ProductForm, SubscriptionForm, PromotionForm, 
    StorePaymentSettingsForm, CategoryForm, GeneralProfileForm, ContactForm,
    StudentProfileForm
)
from django.core.mail import send_mail
from django.conf import settings


def home(request):
    """Page d'accueil avec les produits en vedette et les catégories populaires"""
    from .recommendations import get_personalized_feed, get_promoted_products
    
    # Récupérer les produits recommandés (système intelligent)
    recommended_products = get_personalized_feed(request.user if request.user.is_authenticated else None, limit=12)
    
    # Derniers produits ajoutés (tous les produits)
    latest_products = Product.objects.all().order_by('-created_at')[:12]
    
    # Produits en vedette (ceux qui ont is_featured=True)
    featured_products = Product.objects.filter(
        is_featured=True
    ).order_by('-featured_until', '-created_at')[:12]
    
    # Si pas de produits en vedette, on utilise les recommandés
    if not featured_products.exists():
        featured_products = recommended_products[:8]
    
    # Produits en promotion (pour la section spéciale)
    promoted_products = get_promoted_products(limit=4)
    
    # Catégories populaires (toutes les catégories avec produits)
    categories = Category.objects.annotate(
        product_count=Count('products')
    ).filter(product_count__gt=0).order_by('-product_count')[:8]
    
    # Boutiques populaires (avec le plus de produits)
    popular_stores = Store.objects.annotate(
        product_count=Count('products')
    ).filter(product_count__gt=0).order_by('-product_count', '-created_at')[:6]
    
    # Pour la pagination, on utilise les produits en vedette
    page = request.GET.get('page', 1)
    paginator = Paginator(featured_products, 12)  # 12 produits par page
    
    try:
        page_obj = paginator.page(page)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)
    
    context = {
        'featured_products': featured_products,  # Produits en vedette
        'categories': categories,  # Catégories populaires
        'popular_stores': popular_stores,  # Boutiques populaires
        'latest_products': latest_products,  # Derniers produits
        'page_obj': page_obj,  # Pour la pagination
        'recommended_products': recommended_products,  # Recommandations personnalisées
        'promoted_products': promoted_products,  # Produits en promotion
    }
    
    return render(request, 'stores/home.html', context)


def register(request):
    """Inscription d'un nouvel utilisateur"""
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Compte créé avec succès! Créez maintenant votre boutique.')
            return redirect('create_store')
    else:
        form = UserRegisterForm()
    return render(request, 'stores/register.html', {'form': form})


@login_required
def create_store(request):
    """Création d'une boutique"""
    # Vérifier si l'utilisateur a déjà une boutique
    if hasattr(request.user, 'store'):
        messages.info(request, 'Vous avez déjà une boutique!')
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = StoreForm(request.POST, request.FILES)
        if form.is_valid():
            store = form.save(commit=False)
            store.owner = request.user
            store.save()
            messages.success(request, 'Boutique créée avec succès!')
            return redirect('dashboard')
    else:
        form = StoreForm()
    return render(request, 'stores/create_store.html', {'form': form})


@login_required
def dashboard(request):
    """Tableau de bord de la boutique"""
    try:
        store = request.user.store
        products = store.products.all().order_by('-created_at')
    except Store.DoesNotExist:
        messages.warning(request, 'Vous devez d\'abord créer une boutique.')
        return redirect('create_store')
    
    # Statistiques pour un profil vendeur plus riche
    total_products = products.count()
    stats = products.aggregate(
        total_views=Sum('views_count'),
        total_likes=Sum('likes_count'),
    )
    total_views = stats['total_views'] or 0
    total_likes = stats['total_likes'] or 0

    # Nombre total d'avis et note moyenne de la boutique
    all_reviews = []
    for product in products:
        all_reviews.extend(list(product.reviews.all()))
    total_reviews = len(all_reviews)
    if total_reviews:
        average_rating = round(sum(r.rating for r in all_reviews) / total_reviews, 1)
    else:
        average_rating = 0
    
    # Statistiques de commandes et paiements
    orders = Order.objects.filter(store=store)
    total_orders = orders.count()
    pending_orders = orders.filter(status='pending').count()
    completed_orders = orders.filter(status='delivered').count()
    
    # Revenus (paiements complétés)
    completed_payments = Payment.objects.filter(
        order__store=store,
        status='completed'
    )
    total_revenue = completed_payments.aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Commandes récentes
    recent_orders = orders.order_by('-created_at')[:5]

    # Promotions actives (produits ou boutique) réellement en cours
    active_promotions = Promotion.objects.filter(
        (
            Q(store=store) |
            Q(product__store=store)
        ),
        status='active',
        expires_at__gt=timezone.now()
    ).select_related('product', 'store')[:5]

    # Abonnement actif (certification en cours)
    active_subscription = store.subscriptions.filter(
        status='active',
        expires_at__gt=timezone.now()
    ).order_by('-expires_at').first()

    return render(request, 'stores/dashboard.html', {
        'store': store,
        'products': products,
        'total_products': total_products,
        'total_views': total_views,
        'total_likes': total_likes,
        'total_reviews': total_reviews,
        'average_rating': average_rating,
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'completed_orders': completed_orders,
        'total_revenue': total_revenue,
        'recent_orders': recent_orders,
        'active_promotions': active_promotions,
        'active_subscription': active_subscription,
    })


@login_required
def store_payment_settings(request):
    """Configuration des paramètres de paiement de la boutique (FedaPay, Paystack)."""
    try:
        store = request.user.store
    except Store.DoesNotExist:
        messages.warning(request, "Vous devez d'abord créer une boutique.")
        return redirect('create_store')

    if request.method == 'POST':
        form = StorePaymentSettingsForm(request.POST, instance=store)
        if form.is_valid():
            form.save()
            messages.success(request, 'Paramètres de paiement mis à jour avec succès.')
            return redirect('dashboard')
    else:
        form = StorePaymentSettingsForm(instance=store)

    return render(request, 'stores/store_payment_settings.html', {
        'store': store,
        'form': form,
    })


@login_required
def add_category(request):
    """Ajouter une catégorie de produits"""
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save(commit=False)
            if not category.slug:
                category.slug = slugify(category.name)
            category.save()
            messages.success(request, 'Catégorie ajoutée avec succès!')
            return redirect('dashboard')
    else:
        form = CategoryForm()
    return render(request, 'stores/add_category.html', {'form': form})


@login_required
def add_product(request):
    """Ajouter un produit"""
    store = get_object_or_404(Store, owner=request.user)
    
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.store = store
            product.save()
            form.save_m2m()  # Pour sauvegarder les tags
            
            # Gérer les images supplémentaires
            if 'additional_images' in request.FILES:
                for img in request.FILES.getlist('additional_images'):
                    if img.size > 5 * 1024 * 1024:  # 5MB max
                        messages.warning(request, f"L'image {img.name} dépasse la taille maximale de 5MB")
                        continue
                    ProductImage.objects.create(
                        product=product,
                        image=img
                    )
            
            messages.success(request, 'Produit ajouté avec succès !')
            return redirect('dashboard')
        else:
            # Afficher les erreurs de formulaire
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Erreur dans le champ {field}: {error}")
    else:
        form = ProductForm()
    
    return render(request, 'stores/add_product.html', {'form': form})


@login_required
def edit_product(request, product_id):
    """Modifier un produit"""
    product = get_object_or_404(Product, id=product_id, store__owner=request.user)
    
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            
            # Gérer les images supplémentaires
            if 'additional_images' in request.FILES:
                for img in request.FILES.getlist('additional_images'):
                    if img.size > 5 * 1024 * 1024:  # 5MB max
                        messages.warning(request, f"L'image {img.name} dépasse la taille maximale de 5MB")
                        continue
                    ProductImage.objects.create(
                        product=product,
                        image=img
                    )
            
            messages.success(request, 'Produit modifié avec succès!')
            return redirect('dashboard')
    else:
        form = ProductForm(instance=product)
    
    # Récupérer les images supplémentaires existantes
    additional_images = product.additional_images.all().order_by('order')
    
    return render(request, 'stores/edit_product.html', {
        'form': form, 
        'product': product,
        'additional_images': additional_images
    })


@login_required
def delete_product(request, product_id):
    """Supprimer un produit"""
    product = get_object_or_404(Product, id=product_id, store__owner=request.user)
    if request.method == 'POST':
        product.delete()
        messages.success(request, 'Produit supprimé avec succès!')
        return redirect('dashboard')
    return render(request, 'stores/delete_product.html', {'product': product})


@login_required
@require_http_methods(["POST"])
def delete_product_image(request, image_id):
    """Supprimer une image supplémentaire d'un produit"""
    try:
        image = ProductImage.objects.select_related('product__store').get(id=image_id)
        if image.product.store.owner != request.user:
            return JsonResponse({'success': False, 'error': 'Non autorisé'}, status=403)
        
        # Supprimer le fichier du stockage
        image.image.delete(save=False)
        # Supprimer l'entrée de la base de données
        image.delete()
        
        return JsonResponse({'success': True})
    except ProductImage.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Image non trouvée'}, status=404)


@login_required
def edit_store(request):
    """Modifier la boutique"""
    try:
        store = request.user.store
    except Store.DoesNotExist:
        messages.warning(request, 'Vous devez d\'abord créer une boutique.')
        return redirect('create_store')
    
    if request.method == 'POST':
        form = StoreForm(request.POST, request.FILES, instance=store)
        if form.is_valid():
            form.save()
            messages.success(request, 'Boutique modifiée avec succès!')
            return redirect('dashboard')
    else:
        form = StoreForm(instance=store)
    return render(request, 'stores/edit_store.html', {'form': form, 'store': store})


def store_detail(request, store_id):
    """Page publique de la boutique"""
    store = get_object_or_404(Store, id=store_id)
    # Afficher d'abord les produits en vedette
    featured_products = store.products.filter(
        is_featured=True,
        featured_until__gt=timezone.now()
    ).order_by('-created_at')
    other_products = store.products.exclude(
        id__in=featured_products.values_list('id', flat=True)
    ).order_by('-created_at')
    products = list(featured_products) + list(other_products)
    
    # Vérifier si l'utilisateur suit la boutique
    is_following = False
    if request.user.is_authenticated:
        is_following = Follow.objects.filter(user=request.user, store=store).exists()
    
    return render(request, 'stores/store_detail.html', {
        'store': store,
        'products': products,
        'is_following': is_following
    })


@login_required
def subscribe(request):
    """S'abonner pour vérifier sa boutique"""
    try:
        store = request.user.store
    except Store.DoesNotExist:
        messages.warning(request, 'Vous devez d\'abord créer une boutique.')
        return redirect('create_store')
    
    # Vérifier si déjà vérifié
    if store.is_verified and store.has_active_subscription():
        messages.info(request, 'Votre boutique est déjà vérifiée!')
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = SubscriptionForm(request.POST)
        if form.is_valid():
            subscription = form.save(commit=False)
            subscription.store = store
            subscription.plan_type = 'verified'
            subscription.amount = 8000.00  # Prix fixe de 8 000 FCFA pour la certification
            subscription.status = 'pending'
            subscription.save()
            
            # Rediriger vers le paiement
            from .payment_views import initiate_subscription_payment
            return redirect('initiate_subscription_payment', subscription_id=subscription.id)
    else:
        form = SubscriptionForm()
    
    return render(request, 'stores/subscribe.html', {
        'form': form,
        'store': store
    })


@login_required
def promote(request):
    """
    Redirige vers la page de promotion personnalisée
    """
    try:
        # Vérifier que l'utilisateur a bien une boutique
        store = request.user.store
    except Store.DoesNotExist:
        messages.warning(request, 'Vous devez d\'abord créer une boutique.')
        return redirect('create_store')
    
    # Rediriger vers la nouvelle page de promotion
    from django.urls import reverse
    return redirect(reverse('payments:promote'))


@login_required
def my_subscriptions(request):
    """Voir mes abonnements"""
    try:
        store = request.user.store
    except Store.DoesNotExist:
        messages.warning(request, 'Vous devez d\'abord créer une boutique.')
        return redirect('create_store')
    
    subscriptions = store.subscriptions.all().order_by('-created_at')
    return render(request, 'stores/my_subscriptions.html', {
        'subscriptions': subscriptions,
        'store': store
    })


@login_required
def my_promotions(request):
    """Voir mes promotions"""
    try:
        store = request.user.store
    except Store.DoesNotExist:
        messages.warning(request, 'Vous devez d\'abord créer une boutique.')
        return redirect('create_store')
    
    promotions = Promotion.objects.filter(
        store=store
    ).order_by('-created_at')
    
    product_promotions = Promotion.objects.filter(
        product__store=store
    ).order_by('-created_at')
    
    all_promotions = list(promotions) + list(product_promotions)
    
    return render(request, 'stores/my_promotions.html', {
        'promotions': all_promotions,
        'store': store
    })


# ========== INTERACTIONS SOCIALES (TikTok-like) ==========

@login_required
@require_POST
def toggle_like(request, product_id):
    """Like/Unlike un produit (AJAX)"""
    product = get_object_or_404(Product, id=product_id)
    like, created = Like.objects.get_or_create(user=request.user, product=product)
    
    if not created:
        like.delete()
        product.likes_count = max(0, product.likes_count - 1)
        is_liked = False
    else:
        product.likes_count += 1
        is_liked = True
        # Notification au propriétaire
        if product.store.owner != request.user:
            Notification.objects.create(
                user=product.store.owner,
                notification_type='like',
                message=f"{request.user.username} a aimé votre produit {product.name}",
                link=f"/store/{product.store.id}/"
            )
    
    product.save()
    
    return JsonResponse({
        'success': True,
        'is_liked': is_liked,
        'likes_count': product.likes_count
    })


@login_required
@require_POST
def add_comment(request, product_id):
    """Ajouter un commentaire"""
    product = get_object_or_404(Product, id=product_id)
    content = request.POST.get('content', '').strip()
    
    if content:
        comment = Comment.objects.create(
            user=request.user,
            product=product,
            content=content
        )
        # Notification au propriétaire
        if product.store.owner != request.user:
            Notification.objects.create(
                user=product.store.owner,
                notification_type='comment',
                message=f"{request.user.username} a commenté votre produit {product.name}",
                link=f"/store/{product.store.id}/"
            )
        
        return JsonResponse({
            'success': True,
            'comment': {
                'id': comment.id,
                'user': comment.user.username,
                'content': comment.content,
                'created_at': comment.created_at.strftime('%d/%m/%Y %H:%M')
            }
        })
    
    return JsonResponse({'success': False, 'error': 'Commentaire vide'})


@login_required
@require_POST
def share_product(request, product_id):
    """Partager un produit"""
    product = get_object_or_404(Product, id=product_id)
    platform = request.POST.get('platform', '')
    
    Share.objects.create(
        user=request.user,
        product=product,
        platform=platform
    )
    
    product.shares_count += 1
    product.save()
    
    return JsonResponse({
        'success': True,
        'shares_count': product.shares_count
    })


@login_required
@require_POST
def toggle_follow(request, store_id):
    """Suivre/Ne plus suivre une boutique"""
    store = get_object_or_404(Store, id=store_id)
    follow, created = Follow.objects.get_or_create(user=request.user, store=store)
    
    if not created:
        follow.delete()
        is_following = False
    else:
        is_following = True
        # Notification au propriétaire
        if store.owner != request.user:
            Notification.objects.create(
                user=store.owner,
                notification_type='follow',
                message=f"{request.user.username} suit maintenant votre boutique",
                link=f"/store/{store.id}/"
            )
    
    return JsonResponse({
        'success': True,
        'is_following': is_following,
        'followers_count': store.get_followers_count()
    })


@login_required
@require_POST
def toggle_favorite(request, product_id):
    """Ajouter/Retirer des favoris"""
    product = get_object_or_404(Product, id=product_id)
    favorite, created = Favorite.objects.get_or_create(user=request.user, product=product)
    
    if not created:
        favorite.delete()
        is_favorite = False
    else:
        is_favorite = True
    
    return JsonResponse({
        'success': True,
        'is_favorite': is_favorite
    })


@login_required
def add_review(request, product_id):
    """Ajouter un avis/note"""
    product = get_object_or_404(Product, id=product_id)
    
    if request.method == 'POST':
        rating = int(request.POST.get('rating', 0))
        comment = request.POST.get('comment', '').strip()
        
        if 1 <= rating <= 5:
            review, created = Review.objects.get_or_create(
                user=request.user,
                product=product,
                defaults={'rating': rating, 'comment': comment}
            )
            
            if not created:
                review.rating = rating
                review.comment = comment
                review.save()
            
            # Notification au propriétaire
            if product.store.owner != request.user:
                Notification.objects.create(
                    user=product.store.owner,
                    notification_type='review',
                    message=f"{request.user.username} a noté votre produit {product.name}",
                    link=f"/store/{product.store.id}/"
                )
            
            messages.success(request, 'Avis enregistré avec succès!')
            return redirect('product_detail', product_id=product.id)
    
    return redirect('store_detail', store_id=product.store.id)


def product_detail(request, product_id):
    """Page détaillée d'un produit avec commentaires et avis"""
    from .algorithms import get_personalized_recommendations
    
    product = get_object_or_404(Product, id=product_id)
    
    # Incrémenter les vues
    product.views_count += 1
    product.save()
    
    # Vérifier si l'utilisateur a liké/favorisé
    is_liked = False
    is_favorite = False
    user_review = None
    
    if request.user.is_authenticated:
        is_liked = Like.objects.filter(user=request.user, product=product).exists()
        is_favorite = Favorite.objects.filter(user=request.user, product=product).exists()
        user_review = Review.objects.filter(user=request.user, product=product).first()
    
    # Commentaires
    comments = product.comments.all().order_by('-created_at')[:20]
    
    # Avis
    reviews = product.reviews.all().order_by('-created_at')
    average_rating = product.get_average_rating()
    
    # Produits recommandés
    if request.user.is_authenticated:
        try:
            # Obtenir les recommandations personnalisées existantes
            recommended_products = get_personalized_recommendations(request.user, limit=None)
            recommended_products = recommended_products.exclude(id=product.id)[:5]
        except Exception:
            # Fallback simple basé sur similarité
            recommended_products = get_similar_products(product, limit=5)
    else:
        # Fallback simple pour visiteurs non connectés
        recommended_products = get_similar_products(product, limit=5)
    
    return render(request, 'stores/product_detail.html', {
        'product': product,
        'is_liked': is_liked,
        'is_favorite': is_favorite,
        'comments': comments,
        'reviews': reviews,
        'recommended_products': recommended_products,
        'user_review': user_review,
        'average_rating': average_rating
    })


def search(request):
    """Recherche avancée avec filtres"""
    query = request.GET.get('q', '').strip()
    category_id = request.GET.get('category', '')
    min_price = request.GET.get('min_price', '')
    max_price = request.GET.get('max_price', '')
    sort_by = request.GET.get('sort', 'relevance')
    
    products = Product.objects.all()
    
    # Recherche textuelle
    if query:
        products = products.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(tags__name__icontains=query)
        ).distinct()
        
        # Enregistrer la recherche
        if request.user.is_authenticated:
            SearchHistory.objects.create(user=request.user, query=query)
        else:
            SearchHistory.objects.create(query=query)
    
    # Filtre par catégorie
    if category_id:
        products = products.filter(category_id=category_id)
    
    # Filtre par prix
    if min_price:
        products = products.filter(price__gte=min_price)
    if max_price:
        products = products.filter(price__lte=max_price)
    
    # Tri
    if sort_by == 'price_asc':
        products = products.order_by('price')
    elif sort_by == 'price_desc':
        products = products.order_by('-price')
    elif sort_by == 'popular':
        products = products.annotate(
            popularity=Count('likes') + Count('comments') * 2
        ).order_by('-popularity')
    elif sort_by == 'newest':
        products = products.order_by('-created_at')
    else:  # relevance
        products = products.annotate(
            relevance=Count('likes') * 3 + Count('comments') * 2
        ).order_by('-relevance', '-created_at')
    
    # Pagination
    paginator = Paginator(products, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Catégories pour le filtre
    categories = Category.objects.annotate(
        product_count=Count('products')
    ).order_by('-product_count')
    
    return render(request, 'stores/search.html', {
        'page_obj': page_obj,
        'query': query,
        'categories': categories,
        'selected_category': category_id,
        'min_price': min_price,
        'max_price': max_price,
        'sort_by': sort_by
    })


def api_products(request):
    """API simple pour retourner des produits en JSON (pour app mobile).

    Exemple de réponse :
    {
        "results": [
            {"id": 1, "name": "Produit", "price": 10.0, ...},
            ...
        ]
    }
    """
    limit_param = request.GET.get('limit')
    try:
        limit = int(limit_param) if limit_param is not None else 20
    except ValueError:
        limit = 20

    products_qs = Product.objects.select_related('store').order_by('-created_at')[:limit]

    products_data = []
    for p in products_qs:
        image_url = ''
        if p.image and hasattr(p.image, 'url'):
            image_url = p.image.url

        products_data.append({
            'id': p.id,
            'name': p.name,
            'description': p.description,
            'price': float(p.price),
            'currency': getattr(p, 'currency', 'EUR'),
            'image_url': image_url,
            'store': {
                'id': p.store.id if p.store else None,
                'name': p.store.name if p.store else None,
            },
            'likes_count': getattr(p, 'likes_count', 0),
            'views_count': getattr(p, 'views_count', 0),
            'is_featured': getattr(p, 'is_featured', False),
            'created_at': p.created_at.isoformat() if hasattr(p, 'created_at') else None,
        })

    return JsonResponse({'results': products_data})


@login_required
def api_subscriptions(request):
    """API simple pour retourner les abonnements d'une boutique en JSON."""
    store_id = request.GET.get('store') or request.GET.get('store_id')
    if not store_id:
        return JsonResponse({'results': []})

    try:
        store_id = int(store_id)
    except (ValueError, TypeError):
        return JsonResponse({'results': []}, status=400)

    subs_qs = Subscription.objects.filter(store_id=store_id).order_by('-created_at')
    results = []
    for s in subs_qs:
        results.append({
            'id': s.id,
            'plan': getattr(s.plan, 'name', '') if hasattr(s, 'plan') else getattr(s, 'plan_type', ''),
            'status': s.status,
            'starts_at': s.start_date.isoformat() if s.start_date else None,
            'ends_at': s.end_date.isoformat() if s.end_date else None,
        })

    return JsonResponse({'results': results})


@login_required
def my_favorites(request):
    """Page des favoris de l'utilisateur"""
    favorites = Favorite.objects.filter(user=request.user).order_by('-created_at')
    products = [f.product for f in favorites]
    
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'stores/my_favorites.html', {
        'page_obj': page_obj
    })


@login_required
def my_following(request):
    """Boutiques suivies"""
    follows = Follow.objects.filter(user=request.user).order_by('-created_at')
    stores = [f.store for f in follows]
    
    return render(request, 'stores/my_following.html', {
        'stores': stores
    })


@login_required
def notifications(request):
    """Page des notifications"""
    notifications_list = Notification.objects.filter(user=request.user).order_by('-created_at')[:50]
    
    # Marquer comme lues
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    
    return render(request, 'stores/notifications.html', {
        'notifications': notifications_list
    })


def top_stores(request):
    """Classement des boutiques les plus performantes"""
    # On part de toutes les boutiques qui ont au moins un produit
    stores = Store.objects.all()

    # Calculer un score basé sur les vues et likes de tous les produits de chaque boutique
    stores_with_stats = []
    for store in stores:
        products = store.products.all()
        stats = products.aggregate(
            total_views=Sum('views_count'),
            total_likes=Sum('likes_count'),
        )
        total_views = stats['total_views'] or 0
        total_likes = stats['total_likes'] or 0
        followers = store.get_followers_count()

        # Score simple : vues + 3*likes + 5*followers + bonus si vérifié/en vedette
        score = (
            total_views +
            total_likes * 3 +
            followers * 5 +
            (20 if store.is_verified else 0) +
            (10 if store.is_featured else 0)
        )

        stores_with_stats.append({
            'store': store,
            'total_views': total_views,
            'total_likes': total_likes,
            'followers': followers,
            'score': score,
        })

    # Trier par score décroissant
    stores_with_stats.sort(key=lambda s: s['score'], reverse=True)

    return render(request, 'stores/top_stores.html', {
        'stores_with_stats': stores_with_stats,
    })


@require_http_methods(["GET", "POST"])
def get_whatsapp_link_with_location(request, product_id):
    """Génère un lien WhatsApp avec la localisation du client"""
    from urllib.parse import quote
    
    product = get_object_or_404(Product, id=product_id)
    
    # Récupérer les données de localisation depuis la requête
    latitude = request.POST.get('latitude') or request.GET.get('latitude', '')
    longitude = request.POST.get('longitude') or request.GET.get('longitude', '')
    address = request.POST.get('address') or request.GET.get('address', '')
    
    # Message de base
    message = f"Bonjour, je souhaite commander {product.name} ({product.price} XOF)."
    
    # Ajouter la localisation si disponible
    if latitude and longitude:
        # Créer un lien Google Maps avec les coordonnées
        maps_link = f"https://www.google.com/maps?q={latitude},{longitude}"
        if address:
            message += f"\n\n📍 Ma localisation: {address}\n🔗 {maps_link}"
        else:
            message += f"\n\n📍 Ma localisation: {latitude}, {longitude}\n🔗 {maps_link}"
    
    # Nettoyer le numéro WhatsApp (enlever les espaces et caractères spéciaux)
    whatsapp_number = product.store.whatsapp_number.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
    # Si le numéro commence par +, le garder, sinon ajouter le code pays
    if whatsapp_number.startswith('+'):
        whatsapp_number = whatsapp_number[1:]  # Enlever le +
    elif not whatsapp_number.startswith('00'):
        # Si pas de code pays, ajouter 00 (format international)
        whatsapp_number = '00' + whatsapp_number.lstrip('0')
    
    # Encoder le message pour l'URL
    message_encoded = quote(message)
    
    # Créer le lien WhatsApp
    whatsapp_url = f"https://wa.me/{whatsapp_number}?text={message_encoded}"
    
    # Si c'est une requête AJAX, retourner JSON, sinon rediriger
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.POST:
        return JsonResponse({
            'success': True,
            'whatsapp_url': whatsapp_url,
            'message': message
        })
    else:
        # Redirection directe vers WhatsApp
        return redirect(whatsapp_url)


def checkout(request, product_id):
    """Page de checkout pour finaliser une commande"""
    product = get_object_or_404(Product, id=product_id)
    
    if request.method == 'POST':
        # Calculer la quantité et le sous-total
        quantity = int(request.POST.get('quantity', 1))
        unit_price = product.price
        subtotal = float(unit_price) * quantity

        # Créer la commande avec le sous-total uniquement
        order = Order.objects.create(
            product=product,
            store=product.store,
            customer=request.user if request.user.is_authenticated else None,
            quantity=quantity,
            unit_price=unit_price,
            total_price=subtotal,
            delivery_method=request.POST.get('delivery_method', 'delivery'),
            customer_name=request.POST.get('customer_name', ''),
            customer_phone=request.POST.get('customer_phone', ''),
            customer_email=request.POST.get('customer_email', ''),
            address=request.POST.get('delivery_address', ''),
            city=request.POST.get('city', ''),
            postal_code=request.POST.get('postal_code', ''),
            latitude=request.POST.get('latitude') or None,
            longitude=request.POST.get('longitude') or None,
            notes=request.POST.get('notes', ''),
            payment_method=request.POST.get('payment_method', ''),
            payment_status='pending'
        )

        # Calculer les frais de livraison (stockés séparément)
        if order.delivery_method == 'express':
            order.delivery_fee = 5.00
        elif order.delivery_method == 'delivery':
            order.delivery_fee = 2.00
        else:
            order.delivery_fee = 0.00
        order.save()
        
        # Créer le message WhatsApp avec localisation
        message = f"🛒 *NOUVELLE COMMANDE #{order.id}*\n\n"
        message += f"📦 *Produit:* {product.name}\n"
        message += f"💰 *Prix unitaire:* {product.price}€\n"
        message += f"📊 *Quantité:* {order.quantity}\n"
        message += f"💵 *Total:* {order.total_price}€\n"
        message += f"\n━━━━━━━━━━━━━━━━━━━━\n"
        
        # TOUJOURS inclure la localisation si disponible
        if order.latitude and order.longitude:
            lat = float(order.latitude)
            lng = float(order.longitude)
            maps_link = f"https://www.google.com/maps?q={lat},{lng}"
            address = order.address or f"{lat:.6f}, {lng:.6f}"
            
            message += f"📍 *Localisation de livraison:*\n{address}\n\n"
            message += f"🗺️ *Voir sur la carte:*\n{maps_link}\n"
            message += f"\n━━━━━━━━━━━━━━━━━━━━\n"
        elif order.address:
            message += f"📍 *Adresse de livraison:*\n{order.address}\n"
            message += f"\n━━━━━━━━━━━━━━━━━━━━\n"
        
        message += f"👤 *Client:* {order.customer_name}\n"
        message += f"📞 *Téléphone:* {order.customer_phone}\n"
        if order.customer_email:
            message += f"📧 *Email:* {order.customer_email}\n"
        message += f"🚚 *Livraison:* {order.get_delivery_method_display()}\n"
        message += f"💳 *Paiement:* {order.get_payment_method_display()}\n"
        if order.notes:
            message += f"📝 *Notes:* {order.notes}\n"
        
        message += f"\n✅ Commande confirmée et prête pour traitement.\n"
        message += f"\nMerci de confirmer la disponibilité et les modalités de livraison."
        
        # Formater le numéro WhatsApp - encoder le message pour l'URL
        import urllib.parse
        whatsapp_number = product.store.whatsapp_number
        # Nettoyer le numéro
        clean_number = whatsapp_number.replace(' ', '').replace('-', '').replace('+', '')
        if not clean_number.startswith('00'):
            if clean_number.startswith('0'):
                clean_number = clean_number[1:]
            clean_number = '00' + clean_number
        
        encoded_message = urllib.parse.quote(message)
        whatsapp_url = f"https://wa.me/{clean_number}?text={encoded_message}"
        
        # Rediriger vers le paiement au lieu de WhatsApp directement
        messages.success(request, f'✅ Commande créée avec succès! (Commande #{order.id})')
        # Option 1: Rediriger vers le paiement
        return redirect('initiate_payment', order_id=order.id)
        # Option 2: Ou rediriger vers WhatsApp (décommenter la ligne suivante et commenter la précédente)
        # return redirect(whatsapp_url)
    
    return render(request, 'stores/checkout.html', {
        'product': product
    })


from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.utils import translation

@csrf_exempt
@require_http_methods(["POST"])
def custom_logout(request):
    """Vue personnalisée pour la déconnexion qui gère à la fois GET et POST"""
    if request.method == 'POST':
        logout(request)
        return redirect('home')
    # Si la méthode est GET, on affiche un formulaire de confirmation
    return render(request, 'registration/logout.html')


def set_language(request):
    """Changer la langue de l'interface"""
    try:
        import json
        data = json.loads(request.body)
        language = data.get('language', 'fr')
        
        if language in ['fr', 'en']:
            request.session['language'] = language
            translation.activate(language)
            return JsonResponse({'success': True, 'language': language})
        
        return JsonResponse({'success': False, 'error': 'Langue invalide'}, status=400)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Données invalides'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["POST"])
def set_currency(request):
    """Changer la devise de l'interface"""
    import json
    data = json.loads(request.body)
    currency = data.get('currency', 'EUR')
    
    valid_currencies = ['EUR', 'XOF', 'XAF', 'NGN', 'GHS', 'KES', 'ZAR', 'EGP', 'MAD', 'USD', 'GBP']
    if currency in valid_currencies:
        request.session['currency'] = currency
        return JsonResponse({'success': True, 'currency': currency})
    
    return JsonResponse({'success': False, 'error': 'Devise invalide'})


@login_required
def store_orders(request):
    """Gestion des commandes pour le vendeur"""
    try:
        store = request.user.store
    except Store.DoesNotExist:
        messages.warning(request, 'Vous devez d\'abord créer une boutique.')
        return redirect('create_store')
    
    orders = Order.objects.filter(store=store).order_by('-created_at')
    
    # Filtres
    status_filter = request.GET.get('status', '')
    if status_filter:
        orders = orders.filter(status=status_filter)
    
    # Statistiques
    stats = {
        'total': orders.count(),
        'pending': orders.filter(status='pending').count(),
        'confirmed': orders.filter(status='confirmed').count(),
        'preparing': orders.filter(status='preparing').count(),
        'shipped': orders.filter(status='shipped').count(),
        'delivered': orders.filter(status='delivered').count(),
    }
    
    return render(request, 'stores/store_orders.html', {
        'orders': orders,
        'stats': stats,
        'status_filter': status_filter
    })


@login_required
@require_POST
def update_order_status(request, order_id):
    """Mettre à jour le statut d'une commande"""
    order = get_object_or_404(Order, id=order_id, store__owner=request.user)
    
    new_status = request.POST.get('status')
    tracking_number = request.POST.get('tracking_number', '')
    
    if new_status in dict(Order.STATUS_CHOICES):
        order.status = new_status
        if tracking_number:
            order.tracking_number = tracking_number
        if new_status == 'delivered':
            order.delivered_at = timezone.now()
        order.save()
        
        # Notification au client
        if order.customer:
            Notification.objects.create(
                user=order.customer,
                notification_type='order',
                message=f"Votre commande #{order.id} est maintenant {order.get_status_display().lower()}",
                link=f"/order/{order.id}/"
            )
        
        messages.success(request, f'Statut de la commande #{order.id} mis à jour.')
    else:
        messages.error(request, 'Statut invalide.')
    
    return redirect('store_orders')


@login_required
@login_required
def user_profile(request, user_id=None):
    """
    Affiche le profil d'un utilisateur avec ses produits.
    Si user_id n'est pas fourni, affiche le profil de l'utilisateur connecté.
    """
    if user_id:
        user = get_object_or_404(User, id=user_id)
        is_own_profile = (request.user == user)
    else:
        user = request.user
        is_own_profile = True
    
    # Récupérer ou créer le profil général
    general_profile, created = GeneralProfile.objects.get_or_create(user=user)

    # Récupérer le StudentProfile s'il existe (utilisé pour les champs profile_picture/cover_photo)
    try:
        student_profile = user.student_profile
    except Exception:
        student_profile = None

    # Vérifier si le profil est public ou si l'utilisateur est le propriétaire
    if not general_profile.is_public and not is_own_profile:
        messages.warning(request, "Ce profil est privé.")
        return redirect('home')
    
    # Incrémenter le compteur de vues si ce n'est pas le propriétaire
    if not is_own_profile:
        general_profile.profile_views += 1
        general_profile.save()
    
    # Récupérer les produits de l'utilisateur (s'il a une boutique)
    user_products = []
    if hasattr(user, 'store'):
        user_products = Product.objects.filter(store=user.store).order_by('-created_at')[:12]  # Limiter à 12 produits
    
    # Vérifier si l'utilisateur a des produits
    has_products = len(user_products) > 0
    
    context = {
        'profile_user': user,
        'general_profile': general_profile,
        'student_profile': student_profile,
        'is_own_profile': is_own_profile,
        'user_products': user_products,
        'has_products': has_products,
    }
    
    return render(request, 'profiles/user_profile.html', context)


@login_required
def edit_profile(request):
    """
    Vue pour éditer le profil de l'utilisateur.
    Redirige vers la page d'édition du profil général.
    """
    return redirect('general_profile_edit')


def general_profile_edit(request):
    """
    Vue pour éditer le profil général de l'utilisateur.
    """
    if not request.user.is_authenticated:
        return redirect('login')
    
    try:
        profile = request.user.generalprofile
    except GeneralProfile.DoesNotExist:
        profile = GeneralProfile(user=request.user)
    
    # Préparer éventuellement le StudentProfile et son formulaire
    try:
        student_profile = request.user.student_profile
    except Exception:
        student_profile = None

    if request.method == 'POST':
        form = GeneralProfileForm(request.POST, request.FILES, instance=profile)

        # Créer une instance temporaire si nécessaire pour binder le formulaire étudiant
        if student_profile:
            student_inst = student_profile
        else:
            student_inst = None

        student_form = StudentProfileForm(request.POST, request.FILES, instance=student_inst)

        forms_valid = form.is_valid() and student_form.is_valid()

        if forms_valid:
            profile = form.save(commit=False)
            profile.user = request.user
            profile.save()

            # Sauvegarder le StudentProfile si des champs ont été soumis
            student_obj = student_form.save(commit=False)
            if not student_obj.user_id:
                student_obj.user = request.user
            student_obj.save()

            messages.success(request, 'Votre profil a été mis à jour avec succès.')
            return redirect('user_profile')
    else:
        form = GeneralProfileForm(instance=profile)
        student_form = StudentProfileForm(instance=student_profile)

    return render(request, 'stores/general_profile_edit.html', {
        'form': form,
        'profile': profile,
        'student_form': student_form,
    })


def contact(request):
    """
    Vue pour la page de contact
    """
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            # Envoyer l'email
            subject = f"Nouveau message de contact de {form.cleaned_data['name']}"
            message = f"""
            Nom: {form.cleaned_data['name']}
            Email: {form.cleaned_data['email']}
            Téléphone: {form.cleaned_data.get('phone', 'Non fourni')}
            
            Message:
            {form.cleaned_data['message']}
            """
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.CONTACT_EMAIL],
                fail_silently=False,
            )
            
            messages.success(request, 'Votre message a été envoyé avec succès ! Nous vous répondrons dès que possible.')
            return redirect('contact')
    else:
        initial_data = {}
        if request.user.is_authenticated:
            initial_data['name'] = request.user.get_full_name() or request.user.username
            initial_data['email'] = request.user.email
            if hasattr(request.user, 'generalprofile'):
                initial_data['phone'] = request.user.generalprofile.phone
        
        form = ContactForm(initial=initial_data)
    
    return render(request, 'stores/contact.html', {'form': form})
