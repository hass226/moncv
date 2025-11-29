"""
Vues pour la gestion des paiements avec validation côté serveur
"""

import json
import logging
import stripe
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_http_methods
from django.utils import timezone
from django.db import transaction
from django.db.models import Q
from django.conf import settings

from .models import Payment, Order, Subscription, Promotion
from .payment_providers import get_payment_provider
from .paydunya_service import configure_paydunya
import paydunya

logger = logging.getLogger(__name__)
stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', '')


@login_required
@require_http_methods(["GET"])
def paypal_return(request):
    """
    Retour PayPal après approbation du paiement.
    """
    transaction_id = request.GET.get('transaction_id') or request.GET.get('token')
    if not transaction_id:
        messages.error(request, "Identifiant de transaction manquant dans le retour PayPal.")
        return redirect('dashboard')

    payment = get_object_or_404(Payment, transaction_id=transaction_id)

    order = payment.order
    if order:
        if order.customer and order.customer != request.user and order.store.owner != request.user:
            messages.error(request, "Vous n'avez pas accès à ce paiement.")
            return redirect('home')

    with transaction.atomic():
        payment.status = 'completed'
        payment.paid_at = timezone.now()
        payment.payment_method = 'paypal'
        payment.save()

        if order:
            order.payment_status = 'completed'
            order.status = 'confirmed'
            order.payment_method = 'paypal'
            order.save()

    messages.success(request, "Paiement PayPal confirmé avec succès.")

    if order:
        return redirect('payment_status', payment_id=payment.id)
    return redirect('dashboard')


@login_required
@require_http_methods(["GET", "POST"])
def initiate_payment(request, order_id):
    """
    Initie un paiement pour une commande
    Validation côté serveur obligatoire
    """
    order = get_object_or_404(Order, id=order_id)
    
    # Vérifier que la commande appartient au client ou que c'est le vendeur
    if order.customer != request.user and order.store.owner != request.user:
        messages.error(request, 'Vous n\'avez pas accès à cette commande.')
        return redirect('home')
    
    if request.method == 'POST':
        payment_method = request.POST.get('payment_method')
        phone_number = request.POST.get('phone_number', '').strip()
        
        if not phone_number:
            messages.error(request, 'Veuillez fournir un numéro de téléphone.')
            return render(request, 'stores/payment.html', {'order': order})
        
        # Valider le numéro de téléphone selon le réseau
        validation_result = validate_phone_number(phone_number, payment_method)
        if not validation_result['valid']:
            messages.error(request, validation_result['error'])
            return render(request, 'stores/payment.html', {'order': order})
        
        # Créer l'enregistrement de paiement
        payment = Payment.objects.create(
            order=order,
            amount=order.get_total_with_delivery(),
            payment_method=payment_method,
            status='pending',
            payer_phone=phone_number,
            payer_name=order.customer_name or request.user.username,
            payer_email=order.customer_email or request.user.email,
            transaction_id=f"ORD{order.id}_{int(timezone.now().timestamp())}"
        )
        
        # Journaliser la transaction
        logger.info(f"Payment initiated: Order #{order.id}, Payment #{payment.id}, Method: {payment_method}, Amount: {payment.amount}")
        
        try:
            # Obtenir le provider de paiement
            environment = getattr(settings, 'PAYMENT_ENVIRONMENT', 'sandbox')
            provider = get_payment_provider(payment_method, environment)

            # Devise utilisée pour la commande (devise du produit)
            order_currency = getattr(order.product, 'currency', 'XOF')

            # Initier le paiement avec le provider
            if payment_method == 'cinetpay':
                result = provider.initiate_payment(
                    amount=float(payment.amount),
                    phone_number=phone_number,
                    transaction_id=payment.transaction_id,
                    description=f"Commande #{order.id} - {order.product.name}",
                    currency=order_currency,
                )
            else:
                result = provider.initiate_payment(
                    amount=float(payment.amount),
                    phone_number=phone_number,
                    transaction_id=payment.transaction_id,
                    description=f"Commande #{order.id} - {order.product.name}"
                )

            # Certains providers peuvent retourner une chaîne JSON ou un message texte
            if isinstance(result, str):
                try:
                    result = json.loads(result)
                except Exception:
                    logger.error(f"Payment provider returned non-JSON string: {result}")
                    result = {'success': False, 'error': result}
            
            if isinstance(result, dict) and result.get('success'):
                # Mettre à jour le paiement avec les infos du provider
                provider_response = result.get('provider_response', {}) or {}

                # Certains providers peuvent renvoyer provider_response sous forme de chaîne JSON ou texte
                if isinstance(provider_response, str):
                    try:
                        provider_response = json.loads(provider_response)
                    except Exception:
                        logger.error(f"Provider response is non-JSON string: {provider_response}")
                        provider_response = {}

                if not isinstance(provider_response, dict):
                    provider_response = {}

                payment.external_id = provider_response.get('transaction_id', '')
                payment.metadata = provider_response
                payment.save()
                
                # Mettre à jour la commande
                order.payment_status = 'processing'
                order.payment_method = payment_method
                order.save()
                
                # Si le provider retourne une URL de paiement, rediriger
                if result.get('payment_url'):
                    return redirect(result['payment_url'])
                
                messages.success(request, 'Paiement initié avec succès. Vérification en cours...')
                # Programmer une vérification automatique
                verify_payment_async(payment.id)
                return redirect('payment_status', payment_id=payment.id)
            else:
                error_message = ''
                if isinstance(result, dict):
                    error_message = result.get('error', 'Unknown error')
                else:
                    error_message = str(result)

                payment.status = 'failed'
                payment.metadata = {'error': error_message}
                payment.save()
                
                logger.error(f"Payment failed: {result.get('error')}")
                messages.error(request, f"Erreur lors de l'initiation du paiement: {result.get('error')}")
                
        except Exception as e:
            logger.error(f"Payment exception: {str(e)}", exc_info=True)
            payment.status = 'failed'
            payment.metadata = {'exception': str(e)}
            payment.save()
            messages.error(request, 'Une erreur est survenue. Veuillez réessayer.')

    store = order.store
    stripe_available = bool(getattr(store, 'stripe_account_id', ''))
    payment_methods = get_available_payment_methods(store=store)

    return render(request, 'stores/payment.html', {
        'order': order,
        'payment_methods': payment_methods,
        'stripe_available': stripe_available,
    })


@login_required
def paydunya_pay_order(request, order_id):
    """Lance un paiement simple via PayDunya pour une commande"""
    order = get_object_or_404(Order, id=order_id)
    
    # Vérifier que l'utilisateur a le droit de payer cette commande
    if order.customer and order.customer != request.user:
        messages.error(request, "Vous n'avez pas accès à cette commande.")
        return redirect('home')
    
    configure_paydunya()
    
    invoice = paydunya.CheckoutInvoice()
    # Montant en FCFA (XOF) – à adapter si tes prix sont déjà en XOF
    amount_fcfa = int(float(order.get_total_with_delivery()))
    invoice.add_item(
        "Commande CampusCommerce",
        1,
        1,
        amount_fcfa,
    )
    
    if invoice.create():
        # On pourrait stocker invoice.token dans Payment plus tard
        return redirect(invoice.url)
    else:
        messages.error(request, "Erreur PayDunya : " + getattr(invoice, 'response_text', 'Impossible de créer la facture.'))
        return redirect('payment_status', payment_id=order.payments.first().id) if order.payments.exists() else redirect('dashboard')


def validate_phone_number(phone, payment_method):
    """
    Valide un numéro de téléphone selon le réseau de paiement
    Validation basique côté client, la vraie validation vient du serveur du fournisseur
    """
    phone = phone.replace(' ', '').replace('-', '').replace('+', '')
    
    # Validation basique de format
    if not phone or len(phone) < 8:
        return {'valid': False, 'error': 'Numéro de téléphone invalide'}
    
    # Validation selon le réseau (optionnel, juste pour l'UX)
    if payment_method == 'orange_money':
        # Orange Money fonctionne généralement avec les numéros Orange
        # Mais on ne peut pas vraiment vérifier sans l'API
        pass
    elif payment_method == 'moov_money':
        # Moov Money fonctionne avec les numéros Moov
        pass
    
    return {'valid': True}


def get_available_payment_methods(store=None):
    """Retourne la liste des méthodes de paiement réellement disponibles.

    On filtre Payment.PAYMENT_METHODS en fonction de la configuration
    présente dans settings (clés API, IDs, etc.) ET, si fourni, des
    paramètres propres à la boutique (store).
    """
    methods = []
    from django.conf import settings as dj_settings

    for code, label in Payment.PAYMENT_METHODS:
        # PayDunya (plateforme uniquement)
        if code == 'paydunya':
            if not getattr(dj_settings, 'PAYDUNYA_MASTER_KEY', ''):
                continue

        # FedaPay : nécessite la config plateforme + éventuellement un identifiant marchand par boutique
        elif code == 'fedapay':
            if not getattr(dj_settings, 'FEDAPAY_API_KEY', ''):
                continue
            if store is not None and not getattr(store, 'fedapay_merchant_id', ''):
                continue

        # Paystack : nécessite la config plateforme + éventuellement un subaccount par boutique
        elif code == 'paystack':
            if not getattr(dj_settings, 'PAYSTACK_SECRET_KEY', ''):
                continue
            if store is not None and not getattr(store, 'paystack_subaccount', ''):
                continue

        # CinetPay (plateforme uniquement)
        elif code == 'cinetpay':
            if not getattr(dj_settings, 'CINETPAY_API_KEY', '') or not getattr(dj_settings, 'CINETPAY_SITE_ID', ''):
                continue

        # Stripe (plateforme uniquement ici ; filtrage par boutique géré ailleurs pour les commandes)
        elif code == 'stripe':
            if not getattr(dj_settings, 'STRIPE_SECRET_KEY', '') or not getattr(dj_settings, 'STRIPE_PUBLISHABLE_KEY', ''):
                continue

        # PayPal : nécessite au minimum un client_id et un secret global
        elif code == 'paypal':
            if not getattr(dj_settings, 'PAYPAL_CLIENT_ID', '') or not getattr(dj_settings, 'PAYPAL_SECRET_KEY', ''):
                continue

        # Méthodes mobile money legacy (si jamais encore présentes)
        elif code == 'orange_money':
            if not getattr(dj_settings, 'ORANGE_MONEY_API_KEY', ''):
                continue
        elif code == 'moov_money':
            if not getattr(dj_settings, 'MOOV_MONEY_API_KEY', ''):
                continue
        elif code == 'mtn_money':
            if not getattr(dj_settings, 'MTN_MONEY_API_KEY', ''):
                continue
        elif code == 'wave':
            if not getattr(dj_settings, 'WAVE_API_KEY', ''):
                continue

        methods.append((code, label))

    return methods


@login_required
def payment_status(request, payment_id):
    """Affiche le statut d'un paiement"""
    payment = get_object_or_404(Payment, id=payment_id)
    
    # Vérifier les permissions
    if payment.order:
        if payment.order.customer != request.user and payment.order.store.owner != request.user:
            messages.error(request, 'Vous n\'avez pas accès à ce paiement.')
            return redirect('home')
    
    # Vérifier le statut avec le provider
    if payment.status == 'pending' or payment.status == 'processing':
        verify_payment(payment.id)
        payment.refresh_from_db()
    
    return render(request, 'stores/payment_status.html', {
        'payment': payment,
        'order': payment.order
    })


def verify_payment(payment_id):
    """
    Vérifie le statut d'un paiement avec le provider
    Cette fonction doit être appelée côté serveur uniquement
    """
    payment = get_object_or_404(Payment, id=payment_id)
    
    if payment.status in ['completed', 'failed', 'cancelled']:
        return  # Déjà traité

    # Pour l'instant, on ne vérifie automatiquement que les paiements PayDunya.
    # Les anciens paiements (orange_money, moov_money, etc.) ne sont plus supportés
    # et ne doivent pas déclencher d'appels API.
    if payment.payment_method != 'paydunya':
        logger.info(f"Skipping verification for legacy payment method: {payment.payment_method}")
        return
    
    try:
        environment = getattr(settings, 'PAYMENT_ENVIRONMENT', 'sandbox')
        provider = get_payment_provider(payment.payment_method, environment)
        
        # Vérifier avec le provider
        result = provider.verify_payment(payment.transaction_id)
        
        if result['success']:
            new_status = result['status']
            
            # Journaliser
            logger.info(f"Payment verification: Payment #{payment.id}, Status: {new_status}")
            
            # Mettre à jour le paiement
            payment.status = new_status
            payment.metadata.update(result.get('provider_response', {}))
            
            if new_status == 'completed':
                payment.paid_at = timezone.now()
                
                # Mettre à jour la commande
                if payment.order:
                    with transaction.atomic():
                        payment.order.payment_status = 'completed'
                        payment.order.status = 'confirmed'
                        payment.order.save()
                        payment.save()
                        
                        # Notification au vendeur
                        from .models import Notification
                        Notification.objects.create(
                            user=payment.order.store.owner,
                            notification_type='order',
                            message=f"Nouvelle commande #{payment.order.id} - Paiement reçu: {payment.amount}€",
                            link=f"/dashboard/"
                        )
            else:
                payment.save()
            
            return result
        else:
            logger.warning(f"Payment verification failed: {result.get('error')}")
            return result
            
    except Exception as e:
        logger.error(f"Payment verification exception: {str(e)}", exc_info=True)
        return {'success': False, 'error': str(e)}


def verify_payment_async(payment_id):
    """
    Vérifie un paiement de manière asynchrone (à implémenter avec Celery en production)
    Pour l'instant, on fait une vérification après un délai
    """
    import threading
    import time
    
    def verify_after_delay():
        time.sleep(10)  # Attendre 10 secondes
        verify_payment(payment_id)
    
    thread = threading.Thread(target=verify_after_delay)
    thread.daemon = True
    thread.start()


@csrf_exempt
@require_POST
def payment_webhook(request, provider):
    """
    Webhook pour recevoir les notifications des fournisseurs de paiement
    C'est ici que la vraie validation se fait côté serveur
    """
    try:
        # Récupérer les données du webhook
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST.dict()
        
        # Journaliser la requête webhook
        logger.info(f"Webhook received from {provider}: {json.dumps(data)}")
        
        # Extraire l'ID de transaction
        transaction_id = data.get('transaction_id') or data.get('order_id') or data.get('reference')
        
        if not transaction_id:
            logger.warning(f"Webhook without transaction_id from {provider}")
            return HttpResponse('Missing transaction_id', status=400)
        
        # Trouver le paiement
        try:
            payment = Payment.objects.get(transaction_id=transaction_id)
        except Payment.DoesNotExist:
            logger.warning(f"Payment not found for transaction_id: {transaction_id}")
            return HttpResponse('Payment not found', status=404)
        
        # Vérifier la signature du webhook (sécurité)
        if not verify_webhook_signature(request, provider, data):
            logger.error(f"Invalid webhook signature from {provider}")
            return HttpResponse('Invalid signature', status=403)
        
        # Traiter selon le statut du webhook
        status = data.get('status', '').upper()
        
        if status in ['SUCCESS', 'SUCCESSFUL', 'COMPLETED', 'PAID']:
            # Paiement réussi - VALIDATION CÔTÉ SERVEUR
            with transaction.atomic():
                payment.status = 'completed'
                payment.paid_at = timezone.now()
                payment.metadata = data
                payment.save()
                
                # Traiter selon le type de paiement
                if payment.order:
                    payment.order.payment_status = 'completed'
                    payment.order.status = 'confirmed'
                    payment.order.save()
                    
                    # Notification
                    from .models import Notification
                    Notification.objects.create(
                        user=payment.order.store.owner,
                        notification_type='order',
                        message=f"✅ Paiement confirmé pour la commande #{payment.order.id}",
                        link=f"/dashboard/"
                    )
                
                elif payment.subscription:
                    payment.subscription.status = 'completed'
                    payment.subscription.is_active = True
                    payment.subscription.store.is_verified = True
                    payment.subscription.store.save()
                    payment.subscription.save()
                    
                    # Notification
                    from .models import Notification
                    Notification.objects.create(
                        user=payment.subscription.store.owner,
                        notification_type='order',
                        message=f"✅ Abonnement activé! Votre boutique est maintenant vérifiée.",
                        link=f"/dashboard/"
                    )
                
                elif payment.promotion:
                    payment.promotion.status = 'active'
                    payment.promotion.save()
                    
                    # Activer la promotion
                    if payment.promotion.promotion_type == 'product' and payment.promotion.product:
                        payment.promotion.product.is_featured = True
                        payment.promotion.product.featured_until = payment.promotion.expires_at
                        payment.promotion.product.save()
                    elif payment.promotion.promotion_type == 'store' and payment.promotion.store:
                        payment.promotion.store.is_featured = True
                        payment.promotion.store.save()
                    
                    # Notification
                    from .models import Notification
                    Notification.objects.create(
                        user=payment.promotion.store.owner if payment.promotion.store else payment.promotion.product.store.owner,
                        notification_type='order',
                        message=f"✅ Promotion activée!",
                        link=f"/dashboard/"
                    )
            
            logger.info(f"Payment confirmed via webhook: Payment #{payment.id}")
            
        elif status in ['FAILED', 'CANCELLED', 'REJECTED']:
            payment.status = 'failed'
            payment.metadata = data
            payment.save()
            logger.warning(f"Payment failed via webhook: Payment #{payment.id}")
        
        return HttpResponse('OK', status=200)
        
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}", exc_info=True)
        return HttpResponse('Error', status=500)


def verify_webhook_signature(request, provider, data):
    """
    Vérifie la signature du webhook pour s'assurer qu'il vient bien du provider
    IMPORTANT: Ne jamais accepter un paiement sans vérifier la signature
    """
    import hmac
    import hashlib

    # Récupérer la signature envoyée
    signature = request.headers.get('X-Signature') or request.headers.get('Signature') or data.get('signature')
    
    if not signature:
        return False
    
    # Récupérer le secret selon le provider
    if provider == 'orange':
        secret = getattr(settings, 'ORANGE_MONEY_API_SECRET', '')
    elif provider == 'moov':
        secret = getattr(settings, 'MOOV_MONEY_API_SECRET', '')
    elif provider == 'mtn':
        secret = getattr(settings, 'MTN_MONEY_API_SECRET', '')
    elif provider == 'wave':
        secret = getattr(settings, 'WAVE_API_SECRET', '')
    else:
        return False
    
    if not secret:
        # En mode sandbox, on peut accepter sans signature pour les tests
        # Mais en production, c'est OBLIGATOIRE
        if getattr(settings, 'PAYMENT_ENVIRONMENT', 'sandbox') == 'production':
            return False
        return True
    
    # Calculer la signature attendue
    message = json.dumps(data, sort_keys=True)
    expected_signature = hmac.new(
        secret.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()
    
    # Comparer (comparaison sécurisée pour éviter les timing attacks)
    import hmac as _hmac
    return _hmac.compare_digest(signature, expected_signature)


@login_required
def create_stripe_account(request):
    if not hasattr(request.user, 'store'):
        messages.error(request, "Vous devez d'abord créer une boutique.")
        return redirect('create_store')

    store = request.user.store

    if store.stripe_account_id:
        messages.info(request, "Votre compte Stripe est déjà configuré.")
        return redirect('dashboard')

    # S'assurer que la clé Stripe est bien disponible côté serveur
    secret_key = getattr(settings, 'STRIPE_SECRET_KEY', '')
    if not secret_key:
        messages.error(request, "Stripe n'est pas encore configuré côté plateforme (clé secrète manquante).")
        return redirect('dashboard')

    # (Re)positionner explicitement la clé API Stripe avant l'appel
    stripe.api_key = secret_key

    account = stripe.Account.create(type="express")
    store.stripe_account_id = account.id
    store.save()

    base_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')

    account_link = stripe.AccountLink.create(
        account=account.id,
        refresh_url=f"{base_url}/dashboard/",
        return_url=f"{base_url}/dashboard/",
        type="account_onboarding",
    )

    return redirect(account_link.url)


@login_required
@require_http_methods(["POST"])
def create_stripe_payment_intent(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    if order.customer != request.user and order.store.owner != request.user:
        return JsonResponse({'error': "Accès refusé"}, status=403)

    if not order.store.stripe_account_id:
        return JsonResponse({'error': "Le vendeur n'a pas encore configuré son compte Stripe."}, status=400)

    try:
        raw_amount = order.get_total_with_delivery()
        amount_decimal = float(raw_amount)

        currency = getattr(order.product, 'currency', 'EUR').lower()

        amount = int(amount_decimal * 100)
        application_fee_amount = int(amount * 0.01)

        intent = stripe.PaymentIntent.create(
            amount=amount,
            currency=currency,
            payment_method_types=["card"],
            application_fee_amount=application_fee_amount,
            transfer_data={
                "destination": order.store.stripe_account_id,
            },
            metadata={
                "order_id": str(order.id),
            },
        )

        return JsonResponse({
            "clientSecret": intent.client_secret,
            "publishableKey": getattr(settings, 'STRIPE_PUBLISHABLE_KEY', ''),
        })
    except Exception as e:
        logger.error(f"Stripe PaymentIntent error: {str(e)}", exc_info=True)
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def create_stripe_subscription_intent(request, subscription_id):
    subscription = get_object_or_404(Subscription, id=subscription_id, store__owner=request.user)

    try:
        amount_decimal = float(subscription.amount)
        amount = int(amount_decimal * 100)

        intent = stripe.PaymentIntent.create(
            amount=amount,
            currency="xaf",
            payment_method_types=["card"],
            metadata={
                "subscription_id": str(subscription.id),
            },
        )

        return JsonResponse({
            "clientSecret": intent.client_secret,
            "publishableKey": getattr(settings, 'STRIPE_PUBLISHABLE_KEY', ''),
        })
    except Exception as e:
        logger.error(f"Stripe Subscription PaymentIntent error: {str(e)}", exc_info=True)
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def create_stripe_promotion_intent(request, promotion_id):
    promotion = get_object_or_404(Promotion, id=promotion_id)

    # Vérifier que l'utilisateur a le droit sur cette promotion
    if promotion.store and promotion.store.owner != request.user:
        if promotion.product and promotion.product.store.owner != request.user:
            return JsonResponse({'error': "Accès refusé"}, status=403)

    try:
        amount_decimal = float(promotion.amount)
        amount = int(amount_decimal * 100)

        # Utiliser la devise du produit si disponible, sinon par défaut XOF/XAF
        if promotion.product and hasattr(promotion.product, 'currency'):
            currency = str(promotion.product.currency).lower()
        else:
            currency = "xaf"

        intent = stripe.PaymentIntent.create(
            amount=amount,
            currency=currency,
            payment_method_types=["card"],
            metadata={
                "promotion_id": str(promotion.id),
            },
        )

        return JsonResponse({
            "clientSecret": intent.client_secret,
            "publishableKey": getattr(settings, 'STRIPE_PUBLISHABLE_KEY', ''),
        })
    except Exception as e:
        logger.error(f"Stripe Promotion PaymentIntent error: {str(e)}", exc_info=True)
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")
    webhook_secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', '')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except Exception:
        return HttpResponse(status=400)

    if event.get("type") == "payment_intent.succeeded":
        data_object = event["data"]["object"]
        metadata = data_object.get("metadata", {}) or {}
        amount_received = data_object.get("amount_received") or data_object.get("amount")
        currency = data_object.get("currency", "eur").upper()

        order_id = metadata.get("order_id")
        subscription_id = metadata.get("subscription_id")
        promotion_id = metadata.get("promotion_id")

        # Paiement commande (Stripe Connect avec split 1%)
        if order_id:
            try:
                order = Order.objects.get(id=order_id)
            except Order.DoesNotExist:
                return HttpResponse(status=200)

            with transaction.atomic():
                payment = Payment.objects.create(
                    order=order,
                    amount=(amount_received or 0) / 100 if amount_received else order.get_total_with_delivery(),
                    payment_method='stripe',
                    status='completed',
                    transaction_id=data_object.get("id", ""),
                    external_id=data_object.get("id", ""),
                    metadata=data_object,
                    paid_at=timezone.now(),
                )

                order.payment_status = 'completed'
                order.status = 'confirmed'
                order.payment_method = 'stripe'
                order.save()

                from .models import Notification
                Notification.objects.create(
                    user=order.store.owner,
                    notification_type='order',
                    message=f"Nouvelle commande #{order.id} - Paiement Stripe reçu: {payment.amount} {currency}",
                    link=f"/dashboard/",
                )

        # Paiement abonnement (certification boutique)
        elif subscription_id:
            try:
                subscription = Subscription.objects.get(id=subscription_id)
            except Subscription.DoesNotExist:
                return HttpResponse(status=200)

            with transaction.atomic():
                payment = Payment.objects.create(
                    subscription=subscription,
                    amount=(amount_received or 0) / 100 if amount_received else float(subscription.amount),
                    payment_method='stripe',
                    status='completed',
                    transaction_id=data_object.get("id", ""),
                    external_id=data_object.get("id", ""),
                    metadata=data_object,
                    paid_at=timezone.now(),
                )

                subscription.status = 'completed'
                subscription.is_active = True
                subscription.store.is_verified = True
                subscription.store.save()
                subscription.save()

                from .models import Notification
                Notification.objects.create(
                    user=subscription.store.owner,
                    notification_type='order',
                    message="Votre abonnement de vérification a été payé et votre boutique est maintenant vérifiée.",
                    link=f"/dashboard/",
                )

        # Paiement promotion
        elif promotion_id:
            try:
                promotion = Promotion.objects.get(id=promotion_id)
            except Promotion.DoesNotExist:
                return HttpResponse(status=200)

            with transaction.atomic():
                payment = Payment.objects.create(
                    promotion=promotion,
                    amount=(amount_received or 0) / 100 if amount_received else float(promotion.amount),
                    payment_method='stripe',
                    status='completed',
                    transaction_id=data_object.get("id", ""),
                    external_id=data_object.get("id", ""),
                    metadata=data_object,
                    paid_at=timezone.now(),
                )

                promotion.status = 'active'
                promotion.save()

                # Activer la mise en avant
                if promotion.promotion_type == 'product' and promotion.product:
                    promotion.product.is_featured = True
                    promotion.product.featured_until = promotion.expires_at
                    promotion.product.save()
                    owner = promotion.product.store.owner
                else:
                    if promotion.store:
                        promotion.store.is_featured = True
                        promotion.store.save()
                        owner = promotion.store.owner
                    else:
                        owner = None

                if owner:
                    from .models import Notification
                    Notification.objects.create(
                        user=owner,
                        notification_type='order',
                        message="Votre promotion a été activée avec succès.",
                        link=f"/dashboard/",
                    )

    return HttpResponse(status=200)


@login_required
@require_http_methods(["GET", "POST"])
def initiate_subscription_payment(request, subscription_id):
    """
    Initie un paiement pour un abonnement
    Validation côté serveur obligatoire
    """
    subscription = get_object_or_404(Subscription, id=subscription_id, store__owner=request.user)
    
    if request.method == 'POST':
        payment_method = request.POST.get('payment_method')
        phone_number = request.POST.get('phone_number', '').strip()
        
        if not phone_number:
            messages.error(request, 'Veuillez fournir un numéro de téléphone.')
            return render(request, 'stores/payment_subscription.html', {
                'subscription': subscription,
                'payment_methods': get_available_payment_methods(store=subscription.store),
            })
        
        # Valider le numéro de téléphone
        validation_result = validate_phone_number(phone_number, payment_method)
        if not validation_result['valid']:
            messages.error(request, validation_result['error'])
            return render(request, 'stores/payment_subscription.html', {
                'subscription': subscription,
                'payment_methods': get_available_payment_methods(),
            })
        
        # Créer l'enregistrement de paiement
        payment = Payment.objects.create(
            subscription=subscription,
            amount=subscription.amount,
            payment_method=payment_method,
            status='pending',
            payer_phone=phone_number,
            payer_name=request.user.username,
            payer_email=request.user.email,
            transaction_id=f"SUB{subscription.id}_{int(timezone.now().timestamp())}"
        )
        
        # Journaliser
        logger.info(f"Subscription payment initiated: Subscription #{subscription.id}, Payment #{payment.id}, Method: {payment_method}, Amount: {payment.amount}")
        
        try:
            # Obtenir le provider de paiement
            environment = getattr(settings, 'PAYMENT_ENVIRONMENT', 'sandbox')
            provider = get_payment_provider(payment_method, environment)

            # Devise pour l'abonnement (par défaut XOF)
            subscription_currency = 'XOF'

            # Initier le paiement
            if payment_method == 'cinetpay':
                result = provider.initiate_payment(
                    amount=float(payment.amount),
                    phone_number=phone_number,
                    transaction_id=payment.transaction_id,
                    description=f"Abonnement vérification - {subscription.store.name}",
                    currency=subscription_currency,
                )
            else:
                result = provider.initiate_payment(
                    amount=float(payment.amount),
                    phone_number=phone_number,
                    transaction_id=payment.transaction_id,
                    description=f"Abonnement vérification - {subscription.store.name}"
                )

            if isinstance(result, str):
                try:
                    result = json.loads(result)
                except Exception:
                    logger.error(f"Subscription provider returned non-JSON string: {result}")
                    result = {'success': False, 'error': result}
            
            if isinstance(result, dict) and result.get('success'):
                provider_response = result.get('provider_response', {}) or {}
                payment.external_id = provider_response.get('transaction_id', '')
                payment.metadata = provider_response
                payment.save()
                
                subscription.payment_method = payment_method
                subscription.transaction_id = payment.transaction_id
                subscription.save()
                
                if result.get('payment_url'):
                    return redirect(result['payment_url'])
                
                messages.success(request, 'Paiement initié avec succès. Vérification en cours...')
                verify_payment_async(payment.id)
                return redirect('payment_status', payment_id=payment.id)
            else:
                payment.status = 'failed'
                payment.metadata = {'error': result.get('error', 'Unknown error')}
                payment.save()
                
                logger.error(f"Subscription payment failed: {result.get('error')}")
                messages.error(request, f"Erreur lors de l'initiation du paiement: {result.get('error')}")
                
        except Exception as e:
            logger.error(f"Subscription payment exception: {str(e)}", exc_info=True)
            payment.status = 'failed'
            payment.metadata = {'exception': str(e)}
            payment.save()
            messages.error(request, 'Une erreur est survenue. Veuillez réessayer.')
    
    return render(request, 'stores/payment_subscription.html', {
        'subscription': subscription,
        'payment_methods': get_available_payment_methods(store=subscription.store),
    })


@login_required
@require_http_methods(["GET", "POST"])
def initiate_promotion_payment(request, promotion_id):
    """
    Initie un paiement pour une promotion
    Validation côté serveur obligatoire
    """
    promotion = get_object_or_404(Promotion, id=promotion_id)
    
    # Vérifier les permissions
    if promotion.store and promotion.store.owner != request.user:
        if promotion.product and promotion.product.store.owner != request.user:
            messages.error(request, 'Vous n\'avez pas accès à cette promotion.')
            return redirect('home')
    
    # Récupérer les méthodes de paiement disponibles pour la boutique
    store = promotion.store or (promotion.product.store if promotion.product else None)
    payment_methods = get_available_payment_methods(store=store)
    
    if not payment_methods:
        messages.error(request, 'Aucune méthode de paiement disponible pour le moment. Veuillez contacter le support.')
        return redirect('my_promotions')
    
    if request.method == 'POST':
        payment_method = request.POST.get('payment_method')
        phone_number = request.POST.get('phone_number', '').strip()
        
        if not phone_number:
            messages.error(request, 'Veuillez fournir un numéro de téléphone.')
            return render(request, 'stores/payment_promotion.html', {
                'promotion': promotion,
                'payment_methods': payment_methods,
                'current_currency': getattr(store, 'currency', 'XOF') if store else 'XOF'
            })
        
        # Valider le numéro de téléphone
        validation_result = validate_phone_number(phone_number, payment_method)
        if not validation_result['valid']:
            messages.error(request, validation_result['error'])
            return render(request, 'stores/payment_promotion.html', {
                'promotion': promotion,
                'payment_methods': get_available_payment_methods(),
            })
        
        # Créer l'enregistrement de paiement
        payment = Payment.objects.create(
            promotion=promotion,
            amount=promotion.amount,
            payment_method=payment_method,
            status='pending',
            payer_phone=phone_number,
            payer_name=request.user.username,
            payer_email=request.user.email,
            transaction_id=f"PROM{promotion.id}_{int(timezone.now().timestamp())}"
        )
        
        # Journaliser
        logger.info(f"Promotion payment initiated: Promotion #{promotion.id}, Payment #{payment.id}, Method: {payment_method}, Amount: {payment.amount}")
        
        try:
            # Obtenir le provider de paiement
            environment = getattr(settings, 'PAYMENT_ENVIRONMENT', 'sandbox')
            provider = get_payment_provider(payment_method, environment)

            # Initier le paiement
            description = f"Promotion {promotion.get_promotion_type_display()}"
            if promotion.product:
                description += f" - {promotion.product.name}"
            elif promotion.store:
                description += f" - {promotion.store.name}"

            # Devise pour la promotion (si liée à un produit, prendre sa devise, sinon XOF)
            promo_currency = getattr(getattr(promotion, 'product', None), 'currency', 'XOF')

            if payment_method == 'cinetpay':
                result = provider.initiate_payment(
                    amount=float(payment.amount),
                    phone_number=phone_number,
                    transaction_id=payment.transaction_id,
                    description=description,
                    currency=promo_currency,
                )
            else:
                result = provider.initiate_payment(
                    amount=float(payment.amount),
                    phone_number=phone_number,
                    transaction_id=payment.transaction_id,
                    description=description
                )

            if isinstance(result, str):
                try:
                    result = json.loads(result)
                except Exception:
                    logger.error(f"Promotion provider returned non-JSON string: {result}")
                    result = {'success': False, 'error': result}
            
            if isinstance(result, dict) and result.get('success'):
                provider_response = result.get('provider_response', {}) or {}
                payment.external_id = provider_response.get('transaction_id', '')
                payment.metadata = provider_response
                payment.save()
                
                promotion.payment_method = payment_method
                promotion.transaction_id = payment.transaction_id
                promotion.save()
                
                if result.get('payment_url'):
                    return redirect(result['payment_url'])
                
                messages.success(request, 'Paiement initié avec succès. Vérification en cours...')
                verify_payment_async(payment.id)
                return redirect('payment_status', payment_id=payment.id)
            else:
                payment.status = 'failed'
                payment.metadata = {'error': result.get('error', 'Unknown error')}
                payment.save()
                
                logger.error(f"Promotion payment failed: {result.get('error')}")
                messages.error(request, f"Erreur lors de l'initiation du paiement: {result.get('error')}")
                
        except Exception as e:
            logger.error(f"Promotion payment exception: {str(e)}", exc_info=True)
            payment.status = 'failed'
            payment.metadata = {'exception': str(e)}
            payment.save()
            messages.error(request, 'Une erreur est survenue. Veuillez réessayer.')
    
    return render(request, 'stores/payment_promotion.html', {
        'promotion': promotion,
        'payment_methods': get_available_payment_methods(store=(promotion.store or (promotion.product.store if promotion.product else None))),
    })


@login_required
def my_payments(request):
    """Liste des paiements de l'utilisateur"""
    if hasattr(request.user, 'store'):
        # Vendeur: voir tous ses paiements (commandes, abonnements, promotions)
        payments = Payment.objects.filter(
            Q(order__store=request.user.store) |
            Q(subscription__store=request.user.store) |
            Q(promotion__store=request.user.store) |
            Q(promotion__product__store=request.user.store)
        ).order_by('-created_at')
    else:
        # Client: voir ses propres paiements
        payments = Payment.objects.filter(order__customer=request.user).order_by('-created_at')
    
    return render(request, 'stores/my_payments.html', {
        'payments': payments
    })