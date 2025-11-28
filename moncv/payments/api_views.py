from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
import json
import logging

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import PaymentTransaction
from .mobile_money import process_mobile_money_payment, MobileMoneyConfig

logger = logging.getLogger(__name__)

@csrf_exempt
@require_http_methods(["POST"])
def sms_webhook(request):
    """
    Webhook pour recevoir les SMS de l'application Android
    
    Format attendu:
    {
        "sender": "+22670123456",
        "message": "Vous avez reçu 5000 FCFA de +226701234567. Code: ABC123. Ref: TX123456",
        "device_id": "unique_device_id",
        "timestamp": 1634567890
    }
    """
    try:
        data = json.loads(request.body.decode('utf-8'))
        sender = data.get('sender', '').strip()
        message = data.get('message', '').strip()
        device_id = data.get('device_id')
        
        if not sender or not message:
            return JsonResponse(
                {'error': 'Champs manquants: sender et message sont requis'}, 
                status=400
            )
        
        # Vérifier la clé API si nécessaire
        api_key = request.headers.get('X-API-Key')
        if not api_key or api_key != getattr(settings, 'SMS_GATEWAY_API_KEY', ''):
            return JsonResponse(
                {'error': 'Clé API invalide ou manquante'}, 
                status=403
            )
        
        # Traiter le SMS
        transaction = process_mobile_money_payment(sender, message)
        
        if transaction:
            return JsonResponse({
                'status': 'success',
                'transaction_id': transaction.transaction_id,
                'amount': str(transaction.amount),
                'status': transaction.status,
                'message': 'Paiement traité avec succès'
            })
        else:
            return JsonResponse(
                {'status': 'ignored', 'message': 'SMS non reconnu comme un paiement valide'},
                status=200
            )
            
    except json.JSONDecodeError:
        return JsonResponse(
            {'error': 'Données JSON invalides'}, 
            status=400
        )
    except Exception as e:
        logger.error(f"Erreur lors du traitement du webhook SMS: {str(e)}", exc_info=True)
        return JsonResponse(
            {'error': 'Erreur interne du serveur'}, 
            status=500
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_payment_status(request, transaction_id):
    """
    Vérifier le statut d'une transaction de paiement
    """
    try:
        transaction = PaymentTransaction.objects.get(
            transaction_id=transaction_id,
            user=request.user
        )
        
        return Response({
            'transaction_id': transaction.transaction_id,
            'status': transaction.status,
            'amount': str(transaction.amount),
            'payment_method': transaction.get_payment_method_display(),
            'created_at': transaction.created_at,
            'verified_at': transaction.verified_at
        })
        
    except PaymentTransaction.DoesNotExist:
        return Response(
            {'error': 'Transaction non trouvée'}, 
            status=status.HTTP_404_NOT_FOUND
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_mobile_money_payment(request):
    """
    Créer une demande de paiement Mobile Money
    """
    from django.utils import timezone
    
    amount = request.data.get('amount')
    phone_number = request.data.get('phone_number')
    operator = request.data.get('operator', 'orange')
    service_type = request.data.get('service_type', 'store')
    reference_id = request.data.get('reference_id')
    
    if not all([amount, phone_number]):
        return Response(
            {'error': 'Les champs amount et phone_number sont requis'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Générer un ID de transaction unique
        transaction_id = f"MM{int(timezone.now().timestamp())}{request.user.id}"
        
        # Créer la transaction
        transaction = PaymentTransaction.objects.create(
            user=request.user,
            transaction_id=transaction_id,
            payment_method=operator,
            service_type=service_type,
            reference_id=reference_id,
            amount=amount,
            phone_number=phone_number,
            status='pending',
            notes=f"En attente de paiement Mobile Money via {operator}"
        )
        
        # Dans un environnement réel, vous pourriez envoyer une demande de paiement à l'API de l'opérateur
        # Ici, nous simulons simplement la création de la transaction
        
        return Response({
            'status': 'pending',
            'transaction_id': transaction.transaction_id,
            'amount': str(transaction.amount),
            'phone_number': transaction.phone_number,
            'message': 'Demande de paiement créée avec succès. En attente de confirmation.'
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        logger.error(f"Erreur lors de la création du paiement: {str(e)}", exc_info=True)
        return Response(
            {'error': 'Erreur lors de la création du paiement'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
