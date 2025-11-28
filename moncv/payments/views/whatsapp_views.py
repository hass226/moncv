from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse

from ..models import WhatsAppMessage
from ..whatsapp_service import WhatsAppService

@login_required
def send_whatsapp_message(request, product_id):
    """
    Vue pour envoyer un message WhatsApp concernant un produit
    """
    from stores.models import Product
    
    product = get_object_or_404(Product, id=product_id)
    
    # Vérifier les permissions si nécessaire
    # if not request.user.has_perm('stores.change_product', product):
    #     messages.error(request, _("Vous n'avez pas la permission d'envoyer des messages pour ce produit."))
    #     return redirect('product_detail', pk=product_id)
    
    if request.method == 'POST':
        phone_number = request.POST.get('phone_number')
        custom_message = request.POST.get('message')
        
        if not phone_number:
            messages.error(request, _("Le numéro de téléphone est requis."))
            return redirect('product_detail', pk=product_id)
        
        # Envoyer le message via le service WhatsApp
        whatsapp_service = WhatsAppService()
        result = whatsapp_service.send_product_message(
            product=product,
            phone_number=phone_number,
            message=custom_message
        )
        
        if result.status == 'sent':
            messages.success(request, _("Message WhatsApp envoyé avec succès !"))
        else:
            messages.error(request, _("Erreur lors de l'envoi du message WhatsApp: %(error)s") % {'error': result.error_message})
        
        return redirect('product_detail', pk=product_id)
    
    # Afficher le formulaire d'envoi de message
    return render(request, 'payments/whatsapp_send.html', {
        'product': product,
        'default_message': _("Bonjour, voici les détails du produit que vous avez demandé : {product_name}").format(
            product_name=product.name
        )
    })

@login_required
@require_http_methods(["POST"])
def send_whatsapp_ajax(request, product_id):
    """
    Vue pour envoyer un message WhatsApp via AJAX
    """
    from stores.models import Product
    
    if not request.is_ajax():
        return JsonResponse({'success': False, 'error': _('Requête invalide')}, status=400)
    
    product = get_object_or_404(Product, id=product_id)
    phone_number = request.POST.get('phone_number')
    custom_message = request.POST.get('message')
    
    if not phone_number:
        return JsonResponse({'success': False, 'error': _('Le numéro de téléphone est requis.')}, status=400)
    
    try:
        whatsapp_service = WhatsAppService()
        result = whatsapp_service.send_product_message(
            product=product,
            phone_number=phone_number,
            message=custom_message
        )
        
        if result.status == 'sent':
            return JsonResponse({
                'success': True,
                'message': _('Message WhatsApp envoyé avec succès !'),
                'message_id': result.id
            })
        else:
            return JsonResponse({
                'success': False,
                'error': _("Erreur lors de l'envoi du message WhatsApp: %(error)s") % {'error': result.error_message}
            }, status=400)
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': _('Une erreur est survenue: %(error)s') % {'error': str(e)}
        }, status=500)

@login_required
def whatsapp_message_list(request):
    """
    Vue pour afficher l'historique des messages WhatsApp
    """
    messages = WhatsAppMessage.objects.select_related('product').order_by('-created_at')
    
    # Filtrer par statut si spécifié
    status = request.GET.get('status')
    if status in ['pending', 'sent', 'delivered', 'failed']:
        messages = messages.filter(status=status)
    
    # Filtrer par produit si spécifié
    product_id = request.GET.get('product_id')
    if product_id:
        messages = messages.filter(product_id=product_id)
    
    return render(request, 'payments/whatsapp_list.html', {
        'messages': messages,
        'status_filter': status,
        'product_id': product_id
    })

@login_required
def whatsapp_message_detail(request, message_id):
    """
    Vue pour afficher les détails d'un message WhatsApp
    """
    message = get_object_or_404(WhatsAppMessage, id=message_id)
    return render(request, 'payments/whatsapp_detail.html', {
        'whatsapp_message': message
    })
