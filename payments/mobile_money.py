import re
from datetime import datetime, timedelta
from django.db import models
from django.conf import settings
from django.utils import timezone

class MobileMoneyConfig(models.Model):
    """Configuration pour les opérateurs Mobile Money"""
    OPERATOR_CHOICES = [
        ('orange', 'Orange Money'),
        ('moov', 'Moov Money'),
        ('mtn', 'MTN Mobile Money'),
        ('wave', 'Wave')
    ]
    
    operator = models.CharField(max_length=20, choices=OPERATOR_CHOICES, unique=True)
    sms_sender = models.CharField(max_length=50, help_text="Numéro ou nom d'expéditeur des SMS (ex: Orange, Moov)")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Templates de SMS avec des groupes nommés pour l'extraction
    sms_regex_pattern = models.TextField(
        help_text="Expression régulière pour extraire les données du SMS. Doit contenir des groupes nommés: amount, phone, code"
    )
    
    # Configuration API (si disponible)
    api_key = models.CharField(max_length=255, blank=True, null=True)
    api_secret = models.CharField(max_length=255, blank=True, null=True)
    api_base_url = models.URLField(blank=True, null=True)
    
    class Meta:
        app_label = 'payments'
        verbose_name = 'Configuration Mobile Money'
        verbose_name_plural = 'Configurations Mobile Money'
    
    def __str__(self):
        return self.get_operator_display()
    
    def get_regex(self):
        """Retourne l'expression régulière compilée"""
        try:
            return re.compile(self.sms_regex_pattern, re.IGNORECASE | re.MULTILINE | re.DOTALL)
        except re.error:
            # En cas d'erreur dans la regex, retourner un pattern par défaut
            return re.compile(
                r'(?P<amount>\d+(?:[.,]\d+)?).*?'
                r'(?P<phone>\+?[0-9]{8,15}).*?'
                r'(?P<code>[A-Z0-9]{6,})',
                re.IGNORECASE | re.DOTALL
            )


def parse_mobile_money_sms(sender, message, operator_config=None):
    """
    Parse un SMS de paiement Mobile Money et retourne les données extraites
    
    Args:
        sender (str): L'expéditeur du SMS
        message (str): Le contenu du SMS
        operator_config (MobileMoneyConfig, optional): Configuration de l'opérateur. Si None, on essaie de la détecter.
    
    Returns:
        dict: Dictionnaire avec les données extraites ou None si non reconnu
    """
    from .models import PaymentTransaction
    
    if operator_config is None:
        # Essayer de trouver la configuration correspondant à l'expéditeur
        try:
            operator_config = MobileMoneyConfig.objects.filter(
                sms_sender__iexact=sender,
                is_active=True
            ).first()
        except MobileMoneyConfig.DoesNotExist:
            operator_config = None
    
    if operator_config is None:
        # Si aucune configuration spécifique, essayer avec les configurations actives
        active_configs = MobileMoneyConfig.objects.filter(is_active=True)
        for config in active_configs:
            if config.sms_sender.lower() in sender.lower():
                operator_config = config
                break
        else:
            # Aucune configuration trouvée
            return None
    
    # Utiliser l'expression régulière pour extraire les données
    regex = operator_config.get_regex()
    match = regex.search(message)
    
    if not match:
        return None
    
    # Extraire les données avec des valeurs par défaut
    data = {
        'operator': operator_config.operator,
        'amount': match.groupdict().get('amount', '0').replace(',', '.'),
        'phone': match.groupdict().get('phone', '').strip(),
        'code': match.groupdict().get('code', '').strip().upper(),
        'raw_message': message,
        'sender': sender,
        'config_used': operator_config.id
    }
    
    # Nettoyer et convertir les données
    try:
        data['amount'] = float(data['amount'])
    except (ValueError, TypeError):
        data['amount'] = 0.0
    
    # Rechercher une transaction existante avec ce code
    existing_tx = PaymentTransaction.objects.filter(
        transaction_id=data['code'],
        payment_method__in=[op[0] for op in MobileMoneyConfig.OPERATOR_CHOICES]
    ).first()
    
    if existing_tx:
        data['existing_transaction'] = existing_tx
    
    return data


def process_mobile_money_payment(sender, message):
    """
    Traite un SMS de paiement Mobile Money et crée/mets à jour la transaction
    
    Args:
        sender (str): L'expéditeur du SMS
        message (str): Le contenu du SMS
        
    Returns:
        PaymentTransaction: La transaction créée ou mise à jour, ou None si non reconnue
    """
    from .models import PaymentTransaction
    
    # Parser le SMS
    payment_data = parse_mobile_money_sms(sender, message)
    if not payment_data:
        return None
    
    # Vérifier si la transaction existe déjà
    existing_tx = payment_data.get('existing_transaction')
    
    if existing_tx:
        # Mettre à jour la transaction existante
        if existing_tx.status != 'completed' and payment_data['amount'] >= existing_tx.amount:
            existing_tx.status = 'completed'
            existing_tx.verified_at = timezone.now()
            existing_tx.notes = f"Paiement confirmé par SMS reçu de {sender}"
            existing_tx.save(update_fields=['status', 'verified_at', 'notes'])
        return existing_tx
    
    # Créer une nouvelle transaction
    # Note: Dans un cas réel, vous voudrez peut-être associer cela à un utilisateur/commande spécifique
    transaction = PaymentTransaction.objects.create(
        transaction_id=payment_data['code'],
        payment_method=payment_data['operator'],
        amount=payment_data['amount'],
        phone_number=payment_data['phone'],
        status='completed',
        verified_at=timezone.now(),
        notes=f"Paiement Mobile Money détecté automatiquement. SMS reçu de {sender}"
    )
    
    return transaction
