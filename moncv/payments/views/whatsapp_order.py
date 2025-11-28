from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils.translation import gettext_lazy as _
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

from stores.models import Product
from .whatsapp_views import send_whatsapp_ajax

@login_required
@require_http_methods(["POST"])
def process_whatsapp_order(request, product_id):
    """
    Traite une commande WhatsApp
    """
    product = get_object_or_404(Product, id=product_id)
    
    # Récupérer le numéro de téléphone de l'utilisateur s'il est connecté
    phone_number = request.user.phone_number if hasattr(request.user, 'phone_number') else ''
    
    # Si l'utilisateur n'a pas de numéro de téléphone, utiliser celui du formulaire
    if not phone_number:
        phone_number = request.POST.get('phone_number', '')
    
    # Si toujours pas de numéro, utiliser le numéro par défaut du magasin
    if not phone_number and hasattr(product, 'store') and product.store.whatsapp_number:
        phone_number = product.store.whatsapp_number
    
    # Si toujours pas de numéro, utiliser le numéro par défaut
    if not phone_number:
        phone_number = '22601256984'  # Numéro par défaut
    
    # Préparer le message
    message = (
        f"Nouvelle commande de {request.user.get_full_name() or 'un client'}\n\n"
        f"*Produit*: {product.name}\n"
        f"*Prix*: {product.price} FCFA\n"
        f"*Boutique*: {getattr(product.store, 'name', 'Inconnue')}\n\n"
        f"Contact client: {phone_number}"
    )
    
    # Envoyer le message WhatsApp
    response = send_whatsapp_ajax(request, product_id)
    
    # Si c'est une requête AJAX, retourner la réponse JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return response
    
    # Sinon, rediriger avec un message
    if response.status_code == 200:
        messages.success(request, _("Votre demande a été envoyée avec succès sur WhatsApp !"))
    else:
        messages.error(request, _("Une erreur est survenue lors de l'envoi de votre demande."))
    
    return redirect('product_detail', product_id=product_id)

@csrf_exempt
def whatsapp_webhook(request):
    """
    Webhook pour recevoir les mises à jour de statut des messages WhatsApp
    """
    if request.method == 'POST':
        # Traiter les mises à jour de statut des messages
        # Cette partie dépendra de l'API WhatsApp que vous utilisez
        pass
    
    return JsonResponse({'status': 'ok'})
