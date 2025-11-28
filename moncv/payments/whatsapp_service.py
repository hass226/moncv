import requests
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from .models import WhatsAppMessage, WhatsAppConfig

class WhatsAppService:
    """Service pour gérer l'envoi de messages WhatsApp"""
    
    def __init__(self, api_key=None, api_url=None, phone_number=None):
        # Récupérer la configuration active
        self.config = WhatsAppConfig.get_active_config()
        
        # Utiliser les paramètres fournis ou les valeurs par défaut de la configuration
        self.api_key = api_key or self.config.api_key
        self.api_url = api_url or self.config.api_url
        self.phone_number = phone_number or self.config.default_phone_number
    
    def send_product_message(self, product, phone_number, message=None):
        """
        Envoyer un message WhatsApp pour un produit
        
        Args:
            product: Instance du modèle Product
            phone_number: Numéro de téléphone du destinataire (format international)
            message: Message personnalisé (optionnel)
            
        Returns:
            WhatsAppMessage: Instance du message créé
        """
        # Créer le message dans la base de données
        default_message = _(
            "Bonjour, je suis intéressé par le produit : {product_name}\n"
            "Prix : {price} FCFA\n"
            "Description : {description}\n"
            "Merci de me contacter pour plus d'informations."
        ).format(
            product_name=product.name,
            price=product.price,
            description=product.description[:200] + '...' if len(product.description) > 200 else product.description
        )
        
        whatsapp_message = WhatsAppMessage.objects.create(
            product=product,
            recipient=phone_number,
            message=message or default_message,
            status='pending'
        )
        
        try:
            # Préparer le numéro de téléphone du destinataire
            recipient_phone = phone_number.strip().replace(' ', '').replace('+', '')
            if not recipient_phone.startswith('226'):
                recipient_phone = f'226{recipient_phone.lstrip("226")}'
            
            # Préparer le numéro d'expéditeur (notre numéro par défaut)
            sender_phone = self.phone_number.strip().replace(' ', '').replace('+', '')
            if not sender_phone.startswith('226'):
                sender_phone = f'226{sender_phone.lstrip("226")}'
            
            # Construire l'URL de l'API WhatsApp
            whatsapp_url = f"{self.api_url}?phone={recipient_phone}"
            
            # Ajouter le message encodé en URL
            from urllib.parse import quote
            product_info = (
                f"*Nouvelle demande d'information*\n\n"
                f"*Produit*: {product.name}\n"
                f"*Prix*: {product.price} FCFA\n"
                f"*Message*: {message or 'Aucun message supplémentaire'}"
            )
            whatsapp_url += f"&text={quote(product_info)}"
            
            # Enregistrer l'URL complète (pour débogage)
            whatsapp_message.details = {'whatsapp_url': whatsapp_url}
            whatsapp_message.save()
            
            # Marquer comme envoyé (dans un vrai cas d'utilisation, vous enverriez la requête)
            # response = requests.get(whatsapp_url, headers={'Authorization': f'Bearer {self.api_key}'})
            # if response.status_code == 200:
            #     whatsapp_message.mark_as_sent()
            # else:
            #     whatsapp_message.mark_as_failed(f"Erreur {response.status_code}: {response.text}")
            
            # Pour l'instant, on simule un envoi réussi
            whatsapp_message.mark_as_sent()
            
            return whatsapp_message
            
        except Exception as e:
            whatsapp_message.mark_as_failed(str(e))
            return whatsapp_message


def send_whatsapp_notification(sender, instance, created, **kwargs):
    """
    Signal pour envoyer une notification WhatsApp lorsqu'un produit est acheté
    """
    from django.db.models.signals import post_save
    from django.dispatch import receiver
    from .models import PaymentTransaction
    
    if created and instance.status == 'completed' and instance.service_type == 'store':
        # Récupérer le produit associé à la transaction
        product = instance.product  # À adapter selon votre modèle
        if product and instance.phone_number:
            whatsapp_service = WhatsAppService()
            whatsapp_service.send_product_message(
                product=product,
                phone_number=instance.phone_number,
                message=_("Merci pour votre achat ! Voici les détails de votre commande :")
            )

# Connecter le signal
from django.db.models.signals import post_save
from .models import PaymentTransaction

post_save.connect(send_whatsapp_notification, sender=PaymentTransaction)
