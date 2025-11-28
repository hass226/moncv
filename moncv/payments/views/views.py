import csv
import random
import string
import logging
import requests
from urllib.parse import quote_plus
from django.utils.translation import gettext_lazy as _

from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import TemplateView
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, TemplateView
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.db import transaction
from django.http import JsonResponse, HttpResponseForbidden, Http404, HttpResponseRedirect, HttpResponse
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_http_methods, require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q, Count, Sum
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth import get_user_model
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

from payments.models import (
    PaymentTransaction, PaymentVerificationCode, 
    StoreSubscription, SubscriptionPlan, CodeUsage, WhatsAppConfig
)
from payments.forms import (
    PaymentVerificationForm, VerificationCodeForm,
    GenerateCodesForm, PaymentForm,
    BaseCodeForm, CertificationCodeForm, PromotionCodeForm
)
from stores.forms import SubscriptionForm
from stores.models import Store, Product, Subscription

User = get_user_model()
import logging
import uuid
from datetime import timedelta

logger = logging.getLogger(__name__)

def generate_verification_code():
    """Génère un code de vérification au format XXXX-XXXX-XXXX"""
    # Génère 3 groupes de 4 caractères alphanumériques majuscules
    chars = string.ascii_uppercase + string.digits
    return '-'.join(
        [''.join(random.choices(chars, k=4)) for _ in range(3)]
    )

class CodeDashboard(LoginRequiredMixin, ListView):
    """Tableau de bord pour la gestion des codes"""
    model = PaymentVerificationCode
    template_name = 'payments/code_dashboard.html'
    context_object_name = 'object_list'
    paginate_by = 20
    
    def get_queryset(self):
        # Seulement les codes créés par l'utilisateur actuel
        qs = super().get_queryset().filter(created_by=self.request.user)
        
        # Filtrage par statut
        status = self.request.GET.get('status')
        if status:
            qs = qs.filter(status=status)
            
        # Recherche
        search = self.request.GET.get('q')
        if search:
            qs = qs.filter(
                Q(code__icontains=search) |
                Q(notes__icontains=search) |
                Q(subscription__store__name__icontains=search)
            )
            
        return qs.select_related('subscription', 'subscription__plan', 'subscription__store')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['now'] = timezone.now()
        context['title'] = _('Tableau de bord des codes')
        return context
    
    def test_func(self):
        return self.request.user.is_staff

def send_whatsapp_notification(verification_code, user, store):
    """Send WhatsApp notification to admin about the payment verification"""
    if not getattr(settings, 'WHATSAPP_API_KEY', None):
        logger.warning("WhatsApp API key not configured")
        return False
        
    message = (
        "📢 *Nouvelle vérification de paiement !*\n\n"
        f"🔑 *Code:* {verification_code.code}\n"
        f"👤 *Utilisateur:* {user.get_full_name() or user.username}\n"
        f"📧 *Email:* {user.email}\n"
        f"🏪 *Boutique:* {store.name}\n"
        f"📅 *Date:* {timezone.now().strftime('%d/%m/%Y %H:%M')}"
    )
    
    try:
        response = requests.post(
            'https://api.whatsapp.com/send',
            json={
                'api_key': settings.WHATSAPP_API_KEY,
                'to': settings.ADMIN_WHATSAPP_NUMBER,
                'message': message
            },
            timeout=10
        )
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Failed to send WhatsApp notification: {str(e)}")
        return False

def process_payment(request, plan_id=None):
    """View to handle payment processing"""
    if not request.user.is_authenticated:
        messages.warning(request, gettext_lazy('Veuillez vous connecter pour effectuer un paiement.'))
        return redirect('{}?next={}'.format(settings.LOGIN_URL, request.path))
    
    store = Store.objects.filter(owner=request.user).first()
    if not store:
        messages.error(request, gettext_lazy('Vous devez d\'abord créer une boutique pour effectuer un paiement.'))
        return redirect('stores:store_create')
    
    plan = None
    if plan_id:
        plan = get_object_or_404(SubscriptionPlan, id=plan_id, is_active=True)
    
    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment_method = form.cleaned_data['payment_method']
            phone_number = form.cleaned_data.get('phone_number', '')
            amount = form.cleaned_data['amount']
            
            # Créer une nouvelle transaction de paiement
            transaction = PaymentTransaction.objects.create(
                user=request.user,
                transaction_id=f"TXN-{uuid.uuid4().hex[:8].upper()}",
                payment_method=payment_method,
                service_type='subscription',
                amount=amount,
                phone_number=phone_number,
                status='pending'
            )
            
            # Obtenir la configuration WhatsApp
            whatsapp_config = WhatsAppConfig.get_active_config()
            if not whatsapp_config:
                messages.error(request, gettext_lazy('Configuration WhatsApp non trouvée. Veuillez contacter le support.'))
                return redirect('payments:payment_confirm', transaction_id=transaction.transaction_id)
            
            # Préparer le message WhatsApp
            message = (
                f"Bonjour {request.user.get_full_name() or request.user.username},\n\n"
                "Merci pour votre demande de certification de boutique. "
                "Pour finaliser votre inscription, veuillez contacter notre support technique au "
                f"{whatsapp_config.default_phone_number} pour la certification de votre boutique.\n\n"
                f"ID de transaction: {transaction.transaction_id}\n"
                f"Montant: {amount} FCFA\n"
                f"Boutique: {store.name}\n\n"
                "Cordialement,\nL'équipe de support"
            )
            
            # Encoder le message pour l'URL
            encoded_message = quote_plus(message)
            
            # Construire l'URL WhatsApp
            whatsapp_url = f"https://wa.me/{whatsapp_config.default_phone_number}?text={encoded_message}"
            
            # Rediriger vers WhatsApp
            return redirect(whatsapp_url)
    else:
        initial = {}
        if plan:
            initial.update({
                'amount': plan.price
            })
        form = PaymentForm(initial=initial)
    
    return render(request, 'payments/process_payment.html', {
        'form': form,
        'store': store,
        'plan': plan
    })


def payment_instructions(request):
    """View to display payment instructions"""
    if not request.user.is_authenticated:
        messages.warning(request, gettext_lazy('Veuillez vous connecter pour accéder aux instructions de paiement.'))
        return redirect('{}?next={}'.format(settings.LOGIN_URL, request.path))
    
    store = Store.objects.filter(owner=request.user).first()
    if not store:
        messages.error(request, gettext_lazy('Vous devez d\'abord créer une boutique pour accéder aux instructions de paiement.'))
        return redirect('create_store')  # Utilisation du nom d'URL directement
    
    return render(request, 'payments/payment_instructions.html', {
        'store': store
    })

def payment_confirm(request, transaction_id):
    """View to confirm payment and show next steps"""
    transaction = get_object_or_404(PaymentTransaction, transaction_id=transaction_id, user=request.user)
    
    if request.method == 'POST':
        # Traiter la confirmation de paiement
        transaction.status = 'completed'
        transaction.verified_at = timezone.now()
        transaction.save()
        
        messages.success(request, gettext_lazy('Paiement confirmé avec succès !'))
        return redirect('payments:payment_success', transaction_id=transaction.transaction_id)
    
    return render(request, 'payments/payment_confirm.html', {
        'transaction': transaction
    })


def verify_payment_code(request):
    """
    View for users to enter their payment verification code
    """
    if not request.user.is_authenticated:
        messages.warning(request, gettext_lazy('Veuillez vous connecter pour vérifier un code de paiement.'))
        return redirect('{}?next={}'.format(settings.LOGIN_URL, request.path))
    
    # Check if user has a store
    store = Store.objects.filter(owner=request.user).first()
    if not store:
        messages.error(request, gettext_lazy('Vous devez avoir une boutique pour vérifier un code de paiement.'))
        return redirect('stores:store_create')
    
    if request.method == 'POST':
        form = PaymentVerificationForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['code'].strip().upper()
            try:
                with transaction.atomic():
                    # Lock the record to prevent concurrent access
                    verification_code = PaymentVerificationCode.objects.select_for_update().get(
                        code=code,
                        status='pending',
                        expires_at__gt=timezone.now()
                    )
                    
                    # Double check the code hasn't been used
                    if verification_code.status != 'pending':
                        messages.error(request, gettext_lazy('Ce code a déjà été utilisé ou a expiré.'))
                        return redirect('payments:verify_payment_code')
                    
                    # Verify the code belongs to the user's store
                    subscription = verification_code.subscription
                    if subscription.store != store:
                        messages.error(request, gettext_lazy('Ce code ne correspond pas à votre boutique.'))
                        return redirect('payments:verify_payment_code')
                    
                    # Update the subscription
                    subscription.status = 'active'
                    subscription.starts_at = timezone.now()
                    subscription.expires_at = timezone.now() + timezone.timedelta(days=30)
                    subscription.save()
                    
                    # Mark the code as used
                    verification_code.status = 'used'
                    verification_code.used_by = request.user
                    verification_code.used_at = timezone.now()
                    verification_code.save()
                    
                    # Send WhatsApp notification
                    send_whatsapp_notification(verification_code, request.user, store)
                    
                    messages.success(request, gettext_lazy('Paiement vérifié avec succès ! Votre abonnement est maintenant actif.'))
                    return redirect('stores:dashboard')
                
            except PaymentVerificationCode.DoesNotExist:
                messages.error(request, gettext_lazy('Code invalide, expiré ou déjà utilisé.'))
    else:
        form = PaymentVerificationForm()
    
    return render(request, 'payments/verify_payment_code.html', {
        'form': form,
        'store': store
    })

class AdminCodeDashboard(LoginRequiredMixin, ListView):
    """Tableau de bord pour la gestion des codes"""
    model = PaymentVerificationCode
    template_name = 'admin/payments/code_dashboard.html'
    context_object_name = 'object_list'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filtrage par statut
        self.status = self.request.GET.get('status')
        if self.status in ['pending', 'used', 'expired']:
            queryset = queryset.filter(status=self.status)
            
        # Filtrage par boutique
        self.store_id = self.request.GET.get('store')
        if self.store_id:
            queryset = queryset.filter(subscription__store_id=self.store_id)
            
        # Tri
        self.sort = self.request.GET.get('sort', '-created_at')
        return queryset.order_by(self.sort)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Formulaire de génération de codes
        # Pass the current user so the form can populate store/product/subscription querysets
        context['generate_form'] = GenerateCodesForm(user=self.request.user)
        
        # Liste des boutiques pour le filtre
        context['stores'] = Store.objects.all()
        
        # Paramètres actuels
        context['current_status'] = getattr(self, 'status', '')
        context['current_store'] = getattr(self, 'store_id', '')
        context['current_sort'] = getattr(self, 'sort', '-created_at')
        
        # Statistiques
        from .tasks import get_code_statistics
        context['stats'] = get_code_statistics()
        
        # Types de plans disponibles
        context['plan_types'] = Subscription.SUBSCRIPTION_PLANS
        
        # URL pour l'exportation avec les filtres actuels
        export_params = self.request.GET.copy()
        if 'page' in export_params:
            del export_params['page']
        context['export_url'] = f"/payments/codes/export/?{export_params.urlencode()}"
        
        return context


@login_required
def export_codes(request):
    """
    Exporte les codes de vérification au format CSV
    """
    from .models import PaymentVerificationCode
    
    # Récupérer les paramètres de filtrage
    status = request.GET.get('status')
    store_id = request.GET.get('store')
    sort = request.GET.get('sort', '-created_at')
    
    # Construire la requête
    queryset = PaymentVerificationCode.objects.all()
    
    if status in ['pending', 'used', 'expired']:
        queryset = queryset.filter(status=status)
        
    if store_id:
        queryset = queryset.filter(subscription__store_id=store_id)
    
    queryset = queryset.order_by(sort).select_related('subscription__store', 'created_by', 'used_by')
    
    # Créer la réponse HTTP avec l'en-tête CSV
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
    response['Content-Disposition'] = f'attachment; filename="verification_codes_{timestamp}.csv"'
    
    # Écrire les données CSV avec encodage UTF-8
    response.write('\ufeff'.encode('utf8'))  # BOM pour Excel
    writer = csv.writer(response, delimiter=';')
    
    # En-têtes
    writer.writerow([
        'Code', 'Statut', 'Boutique', 'Type de plan',
        'Créé par', 'Créé le', 'Expire le',
        'Utilisé par', 'Utilisé le', 'Notes'
    ])
    
    # Données
    for code in queryset:
        writer.writerow([
            code.code,
            code.get_status_display(),
            code.subscription.store.name if code.subscription and code.subscription.store else '',
            code.subscription.get_plan_type_display() if code.subscription else '',
            str(code.created_by) if code.created_by else '',
            code.created_at.strftime('%Y-%m-%d %H:%M') if code.created_at else '',
            code.expires_at.strftime('%Y-%m-%d %H:%M') if code.expires_at else '',
            str(code.used_by) if code.used_by else '',
            code.used_at.strftime('%Y-%m-%d %H:%M') if code.used_at else '',
            (code.notes or '').replace('\n', ' ').replace('\r', '')
        ])
    
    return response

import logging
logger = logging.getLogger(__name__)

@login_required
@require_http_methods(['GET', 'POST'])
def generate_verification_codes(request):
    """
    Vue pour générer des codes de vérification avec des options avancées
    """
    logger.info("Accès à la vue generate_verification_codes")
    
    if request.method == 'POST':
        logger.info("Méthode POST détectée")
        
        # Créer une copie mutable de request.POST
        post_data = request.POST.copy()
        
        # Si c'est une demande de code de certification, créer d'abord la souscription
        if post_data.get('code_type') == 'certification':
            try:
                store_id = post_data.get('store')
                store = get_object_or_404(Store, id=store_id, owner=request.user)
                plan_type = post_data.get('plan_type')
                days_valid = int(post_data.get('days_valid', 30))
                expires_at = timezone.now() + timezone.timedelta(days=days_valid)
                
                # Vérifier que l'utilisateur est bien propriétaire de la boutique
                if store.owner != request.user:
                    error_msg = f"Tentative d'accès non autorisé à la boutique {store.id} par l'utilisateur {request.user.id}"
                    logger.warning(error_msg)
                    messages.error(request, _('Accès non autorisé à cette boutique.'))
                    return redirect('payments:generate_verification_codes')
                
                # Créer le plan d'abonnement
                plan_name = dict(Subscription.SUBSCRIPTION_PLANS).get(plan_type, f'Plan {plan_type}')
                logger.info(f"Création du plan d'abonnement: {plan_name}")
                
                plan, created = SubscriptionPlan.objects.get_or_create(
                    name=plan_name,
                    defaults={
                        'description': f'Abonnement {plan_name} généré automatiquement',
                        'price': 0,
                        'duration_days': days_valid,
                        'features': ['Généré automatiquement']
                    }
                )
                
                logger.info(f"Plan {'créé' if created else 'existant'}: {plan.id}")
                
                # Créer une souscription pour ces codes
                subscription = StoreSubscription.objects.create(
                    store=store,
                    plan=plan,
                    status='active',
                    start_date=timezone.now(),
                    end_date=expires_at
                )
                logger.info(f"Souscription créée: {subscription.id}")
                
                # Ajouter l'ID de la souscription aux données du formulaire
                post_data['subscription'] = str(subscription.id)
                
            except Exception as e:
                logger.error(f"Erreur lors de la création du plan/souscription: {str(e)}")
                messages.error(request, _('Une erreur est survenue lors de la création du plan d\'abonnement.'))
                return redirect('payments:generate_verification_codes')
        
        # Créer le formulaire avec les données mises à jour
        form = GenerateCodesForm(post_data, user=request.user)
        logger.info(f"Formulaire créé, valide: {form.is_valid()}")
        
        if form.is_valid():
            # Récupérer les données du formulaire
            store = form.cleaned_data.get('store')
            code_type = form.cleaned_data.get('code_type')
            count = form.cleaned_data.get('count', 1)
            days_valid = form.cleaned_data.get('days_valid', 30)
            usage_limit = form.cleaned_data.get('usage_limit', 1)
            max_attempts = form.cleaned_data.get('max_attempts', 5)
            notes = form.cleaned_data.get('notes', '')
            subscription = form.cleaned_data.get('subscription')
            
            logger.info(f"Données du formulaire - Type: {code_type}, Nombre: {count}, Jours: {days_valid}")
            logger.info(f"Boutique: {store}, Abonnement: {subscription.id if subscription else 'Aucun'}")
            
            expires_at = timezone.now() + timezone.timedelta(days=days_valid)
            
            # Récupérer le produit pour les codes promotionnels
            product = form.cleaned_data.get('product')
            discount_type = form.cleaned_data.get('discount_type')
            discount_value = form.cleaned_data.get('discount_value')
            
            # Générer les codes dans une transaction pour garantir l'intégrité
            try:
                with transaction.atomic():
                    codes = []
                    logger.info(f"Début de la génération de {count} codes de type {code_type}")
                    
                    for i in range(count):
                        # Créer le code avec les paramètres avancés
                        code_data = {
                            'code_type': code_type,
                            'created_by': request.user,
                            'expires_at': expires_at,
                            'usage_limit': usage_limit,
                            'max_attempts': max_attempts,
                            'notes': f"{notes} - Lot de {count} codes - {i+1}/{count}" if notes else f"Lot de {count} codes - {i+1}/{count}",
                            'ip_address': request.META.get('REMOTE_ADDR'),
                            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                            'status': 'pending'
                        }
                        
                        # Ajouter les champs spécifiques au type de code
                        if code_type == 'certification' and subscription:
                            code_data['subscription'] = subscription
                            logger.debug(f"Code {i+1}: Ajout de l'abonnement {subscription.id}")
                        elif code_type == 'promotion' and product:
                            code_data['product'] = product
                            code_data['discount_type'] = discount_type
                            code_data['discount_value'] = discount_value
                            logger.debug(f"Code {i+1}: Ajout du produit {product.id} avec réduction {discount_value}{'%' if discount_type == 'percentage' else 'FCFA'}")
                        
                        try:
                            verification_code = PaymentVerificationCode.objects.create(**code_data)
                            codes.append(verification_code)
                            logger.debug(f"Code {i+1} généré: {verification_code.code}")
                        except Exception as e:
                            logger.error(f"Erreur lors de la création du code {i+1}: {str(e)}")
                            raise
                    
                    logger.info(f"{len(codes)} codes générés avec succès")
                    
            except Exception as e:
                logger.error(f"Erreur lors de la génération des codes: {str(e)}")
                messages.error(request, _('Une erreur est survenue lors de la génération des codes.'))
                return redirect('payments:generate_verification_codes')
            
            # Stocker les IDs des codes générés dans la session pour compatibilité
            generated_ids = [code.id for code in codes]
            request.session['generated_code_ids'] = generated_ids

            messages.success(
                request,
                _('%(count)d codes de vérification ont été générés avec succès.') % {'count': count}
            )

            # Si la requête est AJAX, renvoyer directement les codes au format JSON
            if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
                # Préparer les données des codes
                codes_data = []
                for c in codes:
                    codes_data.append({
                        'id': c.id,
                        'code': c.code,
                        'status': c.status,
                        'expires_at': c.expires_at.isoformat() if c.expires_at else None,
                        'discount': c.get_discount_display() if hasattr(c, 'get_discount_display') else None
                    })

                view_url = reverse('payments:view_generated_codes') + f"?ids={','.join(str(i) for i in generated_ids)}"

                return JsonResponse({'success': True, 'codes': codes_data, 'view_url': view_url})

            return redirect('payments:view_generated_codes')
        
        # En cas d'erreur de formulaire
        # Si AJAX, renvoyer les erreurs de formulaire au format JSON
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
            errors = {k: [str(v) for v in vs] for k, vs in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors}, status=400)

        messages.error(
            request,
            _('Veuillez corriger les erreurs ci-dessous.')
        )
    else:
        # Pré-remplir le formulaire avec des valeurs par défaut
        initial = {
            'count': 1,
            'days_valid': 30,
            'usage_limit': 1,
            'max_attempts': 5,
        }
        form = GenerateCodesForm(user=request.user, initial=initial)
    
    # Préparer le contexte pour le template
    context = {
        'form': form,
        'title': _('Générer des codes de vérification'),
        'now': timezone.now(),
    }
    
    return render(request, 'payments/generate_codes.html', context)

@login_required
def view_generated_codes(request):
    """
    View to display generated codes
    """
    
    code_ids = request.session.pop('generated_code_ids', None)
    
    if not code_ids:
        messages.warning(request, gettext_lazy('Aucun code généré récemment.'))
        return redirect('payments:code_dashboard')
    
    codes = PaymentVerificationCode.objects.filter(id__in=code_ids).select_related(
        'subscription', 'subscription__store'
    )
    
    if not codes.exists():
        messages.warning(request, gettext_lazy('Les codes générés n\'ont pas été trouvés.'))
        return redirect('payments:code_dashboard')
    
    # Tous les codes ont la même date d'expiration (générés ensemble)
    expires_at = codes.first().expires_at
    store = codes.first().subscription.store
    
    return render(request, 'admin/payments/view_codes.html', {
        'codes': codes,
        'store': store,
        'expires_at': expires_at
    })

@require_http_methods(['POST'])
@user_passes_test(lambda u: u.is_staff)
def mark_code_used(request, code_id):
    """
    API endpoint to mark a code as used (admin only)
    """
    try:
        with transaction.atomic():
            # Verrouiller l'enregistrement pour éviter les accès concurrents
            code = PaymentVerificationCode.objects.select_for_update().get(id=code_id)
            
            if code.status != 'pending':
                return JsonResponse({
                    'success': False,
                    'error': gettext_lazy('Ce code a déjà été utilisé ou a expiré.')
                })
            
            # Marquer le code comme utilisé
            code.status = 'used'
            code.used_by = request.user
            code.used_at = timezone.now()
            code.save()
            
            # Mettre à jour la souscription associée
            subscription = code.subscription
            subscription.status = 'active'
            subscription.starts_at = timezone.now()
            subscription.expires_at = timezone.now() + timezone.timedelta(days=30)  # 1 mois par défaut
            subscription.save()
            
            return JsonResponse({
                'success': True,
                'message': gettext_lazy('Le code a été marqué comme utilisé avec succès.')
            })
    
    except PaymentVerificationCode.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': gettext_lazy('Code non trouvé.')
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


def verify_payment(request):
    """
    View to handle payment verification form
    """
    if request.method == 'POST':
        form = PaymentVerificationForm(request.POST)
        if form.is_valid():
            transaction_id = form.cleaned_data['transaction_id']
            payment_method = form.cleaned_data['payment_method']
            amount = form.cleaned_data['amount']
            phone_number = form.cleaned_data.get('phone_number')
            
            # Check if transaction already exists
            transaction = PaymentTransaction.objects.filter(
                transaction_id=transaction_id,
                payment_method=payment_method
            ).first()
            
            if transaction:
                # Transaction already exists, show its status
                if transaction.status == 'completed':
                    messages.success(request, f'Paiement déjà vérifié et approuvé. Montant: {transaction.amount} FCFA')
                else:
                    messages.info(request, f'Transaction trouvée mais en attente de vérification. Statut: {transaction.get_status_display()}')
                return redirect('payment_status', transaction_id=transaction_id)
            
            # Create a new pending transaction
            transaction = PaymentTransaction(
                transaction_id=transaction_id,
                payment_method=payment_method,
                amount=amount,
                phone_number=phone_number,
                status='pending',
                user=request.user if request.user.is_authenticated else None
            )
            
            try:
                # In a real implementation, you would verify the payment with the payment provider here
                # For now, we'll simulate a successful verification
                # TODO: Implement actual payment verification with the payment provider
                
                # Simulate verification (replace with actual API call)
                is_verified = True  # This would come from the payment provider API
                
                if is_verified:
                    transaction.mark_as_completed()
                    messages.success(request, 'Paiement vérifié avec succès !')
                    # TODO: Add any post-payment actions here (e.g., grant access, send email, etc.)
                else:
                    transaction.mark_as_failed()
                    messages.error(request, 'Paiement non trouvé ou invalide. Veuillez vérifier le code et réessayer.')
                
                transaction.save()
                return redirect('payment_status', transaction_id=transaction_id)
                
            except Exception as e:
                logger.error(f'Error verifying payment: {str(e)}', exc_info=True)
                messages.error(request, f'Une erreur est survenue lors de la vérification du paiement: {str(e)}')
        else:
            messages.error(request, gettext_lazy('Veuillez corriger les erreurs ci-dessous.'))
    else:
        form = PaymentVerificationForm()
    
    return render(request, 'payments/verify_payment.html', {
        'form': form,
        'title': 'Vérifier un paiement'
    })

def payment_status(request, transaction_id):
    """
    View to display payment status
    """
    transaction = get_object_or_404(PaymentTransaction, transaction_id=transaction_id)
    return render(request, 'payments/payment_status.html', {
        'transaction': transaction,
        'title': gettext_lazy('Statut du paiement')
    })


def payment_success(request):
    """
    View to display payment success page
    """
    transaction_id = request.GET.get('transaction_id')
    context = {
        'title': gettext_lazy('Paiement réussi'),
    }
    
    if transaction_id:
        try:
            transaction = PaymentTransaction.objects.get(transaction_id=transaction_id)
            context['transaction'] = transaction
        except PaymentTransaction.DoesNotExist:
            pass
    
    return render(request, 'payments/payment_success.html', context)


def payment_cancel(request):
    """
    View to handle cancelled payments
    """
    transaction_id = request.GET.get('transaction_id')
    context = {
        'title': gettext_lazy('Paiement annulé'),
    }
    
    if transaction_id:
        try:
            transaction = PaymentTransaction.objects.get(transaction_id=transaction_id)
            context['transaction'] = transaction
            
            # Mettre à jour le statut de la transaction si elle existe
            if transaction.status == 'pending':
                transaction.status = 'cancelled'
                transaction.save(update_fields=['status'])
                
        except PaymentTransaction.DoesNotExist:
            pass
    
    return render(request, 'payments/payment_cancel.html', context)


@login_required
@csrf_exempt
@require_POST
def stripe_webhook(request):
    """
    Handle Stripe webhook events
    """
    import stripe
    from django.conf import settings
    
    # Vérifier que la clé secrète Stripe est configurée
    if not hasattr(settings, 'STRIPE_SECRET_KEY') or not settings.STRIPE_SECRET_KEY:
        logger.error('STRIPE_SECRET_KEY is not configured in settings')
        return JsonResponse({'error': 'Server configuration error'}, status=500)
    
    # Configurer l'API Stripe
    stripe.api_key = settings.STRIPE_SECRET_KEY
    
    # Récupérer la signature du webhook
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    
    try:
        # Vérifier la signature du webhook
        event = stripe.Webhook.construct_event(
            payload,
            sig_header,
            settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        # Données invalides
        logger.error(f'Invalid payload: {str(e)}')
        return JsonResponse({'error': 'Invalid payload'}, status=400)
    except stripe.error.SignatureVerificationError as e:
        # Signature invalide
        logger.error(f'Invalid signature: {str(e)}')
        return JsonResponse({'error': 'Invalid signature'}, status=400)

    # Gérer les différents types d'événements
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        
        # Récupérer ou créer la transaction
        try:
            transaction = PaymentTransaction.objects.get(
                transaction_id=session.id,
                status='pending'
            )
            
            # Mettre à jour le statut de la transaction
            transaction.status = 'completed'
            transaction.save()
            
            # Mettre à jour le statut de l'abonnement si nécessaire
            if hasattr(transaction, 'subscription'):
                subscription = transaction.subscription
                subscription.status = 'active'
                subscription.save()
                
                # Envoyer une notification par email ou autre
                logger.info(f'Subscription {subscription.id} activated for transaction {transaction.id}')
                
        except PaymentTransaction.DoesNotExist:
            logger.warning(f'Transaction not found for session: {session.id}')
    
    # Retourner une réponse 200 pour confirmer la réception du webhook
    return JsonResponse({'status': 'success'})


def my_transactions(request):
    """
    View to display user's payment history
    """
    transactions = PaymentTransaction.objects.filter(user=request.user).order_by('-created_at')
    
    return render(request, 'payments/my_transactions.html', {
        'transactions': transactions,
        'title': 'Mes transactions'
    })

@login_required
def initier_paiement_formation(request, formation_id):
    """
    Vue pour initier un paiement pour une formation ou certification
    """
    # Récupérer les détails de la formation depuis la base de données
    # Ici, vous devriez récupérer la formation depuis votre modèle Formation
    # formation = get_object_or_404(Formation, id=formation_id)
    
    # Pour l'exemple, on utilise des valeurs par défaut
    formation = {
        'id': formation_id,
        'titre': 'Formation Test',
        'prix': 50000,  # En FCFA
        'type': 'formation'  # ou 'certification'
    }
    
    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            # Créer une nouvelle transaction
            transaction = PaymentTransaction(
                user=request.user,
                transaction_id=f"TRX-{uuid.uuid4().hex[:10].upper()}",
                payment_method=form.cleaned_data['payment_method'],
                service_type=formation['type'],
                reference_id=formation['id'],
                amount=formation['prix'],
                phone_number=form.cleaned_data.get('phone_number'),
                status='pending'
            )
            transaction.save()
            
            # Rediriger vers la page de vérification du paiement
            return redirect('verify_payment_formation', transaction_id=transaction.transaction_id)
    else:
        form = PaymentForm()
    
    return render(request, 'payments/initier_paiement.html', {
        'form': form,
        'formation': formation,
        'title': f'Paiement - {formation["titre"]}'
    })

def verify_payment_formation(request, transaction_id):
    """
    Vue pour vérifier le statut d'un paiement de formation
    """
    transaction = get_object_or_404(PaymentTransaction, transaction_id=transaction_id)
    
    if request.method == 'POST':
        form = PaymentVerificationForm(request.POST)
        if form.is_valid():
            # Ici, vous devriez vérifier le paiement auprès du processeur de paiement
            # Pour l'exemple, on simule un paiement réussi
            transaction.status = 'completed'
            transaction.verified_at = timezone.now()
            transaction.save()
            
            # Mettre à jour le statut de la formation de l'utilisateur
            # formation = Formation.objects.get(id=transaction.reference_id)
            # inscription, created = InscriptionFormation.objects.get_or_create(
            #     utilisateur=request.user,
            #     formation=formation,
            #     defaults={'statut': 'validee' if transaction.status == 'completed' else 'en_attente'}
            # )
            
            messages.success(request, 'Paiement effectué avec succès !')
            return redirect('formation_detail', formation_id=transaction.reference_id)
    else:
        form = PaymentVerificationForm()
    
    return render(request, 'payments/verify_payment_formation.html', {
        'form': form,
        'transaction': transaction,
        'title': 'Vérification du paiement'
    })


class PromoteView(TemplateView):
    template_name = 'payments/promote.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['whatsapp_number'] = "+22601256984"
        context['phone_number'] = "+22601256984"
        return context


def delete_code(request, code_id):
    """
    Vue pour supprimer un code de vérification
    """
    if not request.user.is_staff:
        raise PermissionDenied("Vous n'êtes pas autorisé à effectuer cette action.")
    
    code = get_object_or_404(PaymentVerificationCode, id=code_id)
    
    if request.method == 'POST':
        # Enregistrer l'action pour l'audit
        CodeUsage.objects.create(
            code=code,
            user=request.user,
            success=True,
            details={'action': 'deletion', 'by': request.user.get_full_name() or request.user.username}
        )
        
        # Supprimer le code
        code.delete()
        
        messages.success(request, _('Le code a été supprimé avec succès.'))
        return redirect('payments:code_dashboard')
    
    # Si la méthode n'est pas POST, afficher une page de confirmation
    context = {
        'code': code,
        'title': _('Confirmer la suppression')
    }
    return render(request, 'payments/confirm_delete_code.html', context)
