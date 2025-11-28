from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_http_methods
from django.http import JsonResponse
import re
from .models import PaymentTransaction
import logging

logger = logging.getLogger(__name__)

@csrf_exempt
@require_http_methods(["POST"])
def sms_webhook(request):
    """
    Webhook pour recevoir les notifications de paiement par SMS.
    Format attendu: "Vous avez reçu 5000 FCFA de +22507000000. Ref: OM12345678"
    """
    try:
        # Récupérer les données du webhook
        if request.content_type == 'application/json':
            data = request.json()
        else:
            data = request.POST
            
        message = data.get('message', '')
        sender = data.get('sender', '')
        
        # Journalisation pour le débogage
        logger.info(f"Reçu un SMS de {sender}: {message}")
        
        # Extraire les informations du message
        pattern = r"Vous avez reçu (\d+) FCFA de (\+?\d+).*?Ref: ([A-Z0-9]+)"
        match = re.search(pattern, message, re.IGNORECASE)
        
        if not match:
            logger.warning(f"Format de message non reconnu: {message}")
            return JsonResponse(
                {'status': 'error', 'message': 'Format de message non reconnu'}, 
                status=400
            )
        
        amount = int(match.group(1))
        phone_number = match.group(2)
        transaction_id = match.group(3)
        
        # Déterminer le type de paiement
        if transaction_id.upper().startswith('OM'):
            payment_method = 'orange'
        elif transaction_id.upper().startswith('MTN'):
            payment_method = 'mtn'
        elif transaction_id.upper().startswith('MOOV'):
            payment_method = 'moov'
        elif transaction_id.upper().startswith('WV'):
            payment_method = 'wave'
        else:
            payment_method = 'unknown'
        
        # Créer ou mettre à jour la transaction
        transaction, created = PaymentTransaction.objects.update_or_create(
            transaction_id=transaction_id,
            defaults={
                'payment_method': payment_method,
                'amount': amount,
                'phone_number': phone_number,
                'status': 'completed'
            }
        )
        
        # Si la transaction est nouvelle, déclencher les actions correspondantes
        if created:
            logger.info(f"Nouvelle transaction enregistrée: {transaction_id}")
            # Ici, vous pouvez ajouter des actions supplémentaires comme envoyer un email de confirmation
            # ou déclencher d'autres processus métier
        else:
            logger.info(f"Transaction mise à jour: {transaction_id}")
            
        return JsonResponse({
            'status': 'success', 
            'transaction_id': str(transaction.id),
            'created': created
        })
        
    except Exception as e:
        logger.error(f"Erreur lors du traitement du webhook SMS: {str(e)}", exc_info=True)
        return JsonResponse(
            {'status': 'error', 'message': 'Erreur interne du serveur'}, 
            status=500
        )
