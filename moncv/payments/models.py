import uuid
import random
import string
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _

class PaymentTransaction(models.Model):
    TRANSACTION_TYPES = (
        ('orange', 'Orange Money'),
        ('mtn', 'MTN Mobile Money'),
        ('moov', 'Moov Money'),
        ('wave', 'Wave'),
        ('paypal', 'PayPal'),
        ('carte', 'Carte Bancaire')
    )
    
    SERVICE_TYPES = (
        ('store', 'Boutique'),
        ('promo', 'Promotion'),
        ('certif', 'Certification'),
        ('formation', 'Formation')
    )
    
    STATUS_CHOICES = (
        ('pending', 'En attente'),
        ('completed', 'Complété'),
        ('failed', 'Échoué'),
        ('cancelled', 'Annulé')
    )
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    transaction_id = models.CharField('ID de transaction', max_length=50, unique=True)
    payment_method = models.CharField('Méthode de paiement', max_length=20, choices=TRANSACTION_TYPES)
    service_type = models.CharField('Type de service', max_length=20, choices=SERVICE_TYPES, default='store')
    reference_id = models.PositiveIntegerField('ID de référence', null=True, blank=True, 
                                             help_text="ID de la formation, certification, etc.")
    amount = models.DecimalField('Montant', max_digits=10, decimal_places=2)
    phone_number = models.CharField('Numéro de téléphone', max_length=20, blank=True, null=True)
    status = models.CharField('Statut', max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField('Date de création', default=timezone.now)
    verified_at = models.DateTimeField('Date de vérification', null=True, blank=True)
    notes = models.TextField('Notes', blank=True, null=True)
    
    class Meta:
        app_label = 'payments'
        verbose_name = 'Transaction de paiement'
        verbose_name_plural = 'Transactions de paiement'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_payment_method_display()} - {self.amount} - {self.status}"


def generate_verification_code():
    """
    Génère un code de vérification unique au format XXXX-XXXX-XXXX
    - Utilise un mélange de chiffres et de lettres majuscules
    - Évite les caractères ambigus (0/O, 1/I)
    - Vérifie l'unicité dans la base de données
    """
    chars = '23456789ABCDEFGHJKLMNPQRSTUVWXYZ'  # Exclut 0,1,O,I pour éviter les confusions
    max_attempts = 10
    
    for _ in range(max_attempts):
        # Génère 3 groupes de 4 caractères
        code_parts = []
        for _ in range(3):
            part = ''.join(random.choices(chars, k=4))
            code_parts.append(part)
        
        code = '-'.join(code_parts)
        
        # Vérifie si le code existe déjà dans la base de données
        if not PaymentVerificationCode.objects.filter(code=code).exists():
            return code
    
    # Si on arrive ici, on n'a pas trouvé de code unique après plusieurs tentatives
    # On génère un code avec un UUID comme solution de secours
    fallback_code = f"{uuid.uuid4().hex[:4].upper()}-{uuid.uuid4().hex[:4].upper()}-{uuid.uuid4().hex[:4].upper()}"
    return fallback_code


class SubscriptionPlan(models.Model):
    """Subscription plans for stores"""
    name = models.CharField(_('Plan Name'), max_length=100)
    description = models.TextField(_('Description'))
    price = models.DecimalField(_('Price'), max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    duration_days = models.PositiveIntegerField(_('Duration in days'))
    is_active = models.BooleanField(_('Is Active'), default=True)
    features = models.JSONField(_('Features'), default=list)
    created_at = models.DateTimeField(_('Created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated at'), auto_now=True)

    class Meta:
        app_label = 'payments'
        verbose_name = _('Subscription Plan')
        verbose_name_plural = _('Subscription Plans')
        ordering = ['price']

    def __str__(self):
        return f"{self.name} - {self.price} FCFA ({self.duration_days} days)"


class StoreSubscription(models.Model):
    """Store subscription details"""
    STATUS_CHOICES = (
        ('active', _('Active')),
        ('expired', _('Expired')),
        ('pending', _('Pending Payment')),
        ('cancelled', _('Cancelled')),
    )
    
    store = models.ForeignKey('stores.Store', on_delete=models.CASCADE, related_name='payment_subscriptions')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT, related_name='subscriptions')
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='pending')
    start_date = models.DateTimeField(_('Start Date'), null=True, blank=True)
    end_date = models.DateTimeField(_('End Date'), null=True, blank=True)
    created_at = models.DateTimeField(_('Created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated at'), auto_now=True)

    class Meta:
        app_label = 'payments'
        verbose_name = _('Store Subscription')
        verbose_name_plural = _('Store Subscriptions')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.store.name} - {self.plan.name} ({self.status})"

    def is_active(self):
        return self.status == 'active' and self.end_date and timezone.now() <= self.end_date


class PaymentVerificationCode(models.Model):
    """Modèle pour stocker les codes de vérification de paiement et les codes promotionnels"""
    CODE_TYPES = (
        ('certification', _('Certification')),
        ('promotion', _('Promotion produit')),
    )
    
    CODE_STATUS = (
        ('pending', _('En attente')),
        ('used', _('Utilisé')),
        ('expired', _('Expiré')),
        ('cancelled', _('Annulé')),
    )
    
    # Types de réduction pour les codes promotionnels
    DISCOUNT_TYPES = (
        ('percentage', '%'),
        ('fixed', 'FCFA'),
    )
    
    # Informations sur le code
    code = models.CharField(_('Code de vérification'), max_length=20, unique=True, 
                           default=generate_verification_code, db_index=True)
    code_type = models.CharField(_('Type de code'), max_length=20, 
                                choices=CODE_TYPES, default='certification',
                                db_index=True)
    
    # Relations
    subscription = models.ForeignKey(
        StoreSubscription, 
        on_delete=models.CASCADE, 
        related_name='verification_codes',
        verbose_name=_('Abonnement associé'),
        null=True,
        blank=True,
        help_text=_('Obligatoire pour les codes de certification')
    )
    product = models.ForeignKey(
        'stores.Product',
        on_delete=models.SET_NULL,
        related_name='promo_codes',
        verbose_name=_('Produit associé'),
        null=True,
        blank=True,
        help_text=_('Obligatoire pour les codes promotionnels')
    )
    
    # Statut et suivi
    status = models.CharField(
        _('Statut'), 
        max_length=20, 
        choices=CODE_STATUS, 
        default='pending',
        db_index=True
    )
    
    # Utilisation
    usage_limit = models.PositiveIntegerField(
        _('Nombre maximum d\'utilisations'), 
        default=1,
        help_text=_('Nombre maximum de fois que ce code peut être utilisé (0 pour illimité)')
    )
    usage_count = models.PositiveIntegerField(
        _('Nombre d\'utilisations'), 
        default=0,
        help_text=_('Nombre de fois que ce code a été utilisé')
    )
    
    # Dates importantes
    created_at = models.DateTimeField(_('Date de création'), auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(_('Dernière mise à jour'), auto_now=True)
    used_at = models.DateTimeField(_('Date d\'utilisation'), null=True, blank=True)
    expires_at = models.DateTimeField(
        _('Date d\'expiration'), 
        db_index=True,
        help_text=_('Date à laquelle ce code expirera automatiquement')
    )
    
    # Informations sur la création
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='generated_codes',
        verbose_name=_('Créé par')
    )
    
    # Pour les codes promotionnels
    discount_type = models.CharField(
        _('Type de réduction'),
        max_length=10,
        choices=DISCOUNT_TYPES,
        default='percentage',
        blank=True,
        help_text=_('Type de réduction (pourcentage ou montant fixe)')
    )
    discount_value = models.DecimalField(
        _('Valeur de la réduction'),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_('Valeur de la réduction (en pourcentage ou montant fixe)')
    )
    
    # Suivi des utilisations
    used_by = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='used_codes',
        through='CodeUsage',
        through_fields=('code', 'user'),
        verbose_name=_('Utilisé par'),
        blank=True
    )
    
    # Autres métadonnées
    notes = models.TextField(_('Notes'), blank=True, 
                            help_text=_('Informations supplémentaires sur ce code'))
    ip_address = models.GenericIPAddressField(_('Adresse IP'), null=True, blank=True)
    user_agent = models.TextField(_('User Agent'), blank=True, null=True)
    
    # Sécurité
    last_verification_attempt = models.DateTimeField(_('Dernière tentative'), null=True, blank=True)
    failed_attempts = models.PositiveIntegerField(_('Tentatives échouées'), default=0)
    max_attempts = models.PositiveIntegerField(
        _('Nombre maximum de tentatives'), 
        default=5,
        help_text=_('Nombre maximum de tentatives de validation avant blocage')
    )

    class Meta:
        app_label = 'payments'
        verbose_name = _('Code de vérification')
        verbose_name_plural = _('Codes de vérification')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['code', 'status']),
            models.Index(fields=['expires_at', 'status']),
        ]
        
    def __str__(self):
        return f"{self.code} - {self.get_status_display()} (Utilisé {self.usage_count}/{self.usage_limit if self.usage_limit > 0 else '∞'})"
    
    def save(self, *args, **kwargs):
        """
        Sauvegarde le code avec des validations supplémentaires
        """
        # Pour les nouvelles instances
        if not self.pk:
            # Définit la date d'expiration par défaut (30 jours)
            if not self.expires_at:
                self.expires_at = timezone.now() + timezone.timedelta(days=30)
                
            # Génère un code unique si non fourni
            if not self.code:
                self.code = generate_verification_code()
        
        # Si le code est marqué comme utilisé, mettre à jour la date d'utilisation
        if self.status == 'used' and not self.used_at:
            self.used_at = timezone.now()
            
        # Valider les données avant la sauvegarde
        self.full_clean()
            
        super().save(*args, **kwargs)
    
    def is_valid(self):
        """
        Vérifie si le code est valide (non utilisé, non expiré et n'a pas dépassé le nombre maximal de tentatives)
        """
        now = timezone.now()
        
        # Vérifie le statut
        if self.status != 'pending':
            return False
            
        # Vérifie la date d'expiration
        if self.expires_at and self.expires_at <= now:
            self.status = 'expired'
            self.save(update_fields=['status', 'updated_at'])
            return False
            
        # Vérifie le nombre d'utilisations
        if self.usage_limit > 0 and self.usage_count >= self.usage_limit:
            return False
            
        # Vérifie le nombre de tentatives échouées
        if self.failed_attempts >= self.max_attempts:
            return False
            
        # Validation spécifique au type de code
        if self.code_type == 'certification' and not self.subscription:
            return False
            
        if self.code_type == 'promotion' and not self.product:
            return False
            
        return True
    
    def record_usage(self, user, request=None):
        """
        Enregistre l'utilisation du code par un utilisateur
        """
        if not self.is_valid():
            return False
            
        # Crée un enregistrement d'utilisation
        usage = CodeUsage(
            code=self,
            user=user,
            ip_address=request.META.get('REMOTE_ADDR') if request else None,
            user_agent=request.META.get('HTTP_USER_AGENT') if request else None
        )
        usage.save()
        
        # Met à jour le compteur d'utilisations
        self.usage_count += 1
        
        # Si c'était la dernière utilisation possible
        if self.usage_limit > 0 and self.usage_count >= self.usage_limit:
            self.status = 'used'
            self.used_at = timezone.now()
        
        # Sauvegarde les modifications
        update_fields = ['usage_count', 'status', 'used_at']
        if request:
            self.last_verification_attempt = timezone.now()
            update_fields.append('last_verification_attempt')
            
        self.save(update_fields=update_fields)
        
        # Ajoute l'utilisateur à la relation many-to-many
        self.used_by.add(user)
        
        return True
    
    def record_failed_attempt(self, request=None):
        """
        Enregistre une tentative de validation échouée
        """
        self.failed_attempts += 1
        self.last_verification_attempt = timezone.now()
        
        # Si le nombre maximum de tentatives est atteint, marque comme expiré
        if self.failed_attempts >= self.max_attempts:
            self.status = 'expired'
            
        self.save(update_fields=['failed_attempts', 'last_verification_attempt', 'status', 'updated_at'])
        
        # Enregistre les informations de la requête si disponible
        if request:
            CodeUsage.objects.create(
                code=self,
                user=request.user if request.user.is_authenticated else None,
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
                success=False
            )
    
    def get_remaining_uses(self):
        """
        Retourne le nombre d'utilisations restantes
        """
        if self.usage_limit == 0:  # Illimité
            return float('inf')
        return max(0, self.usage_limit - self.usage_count)
    
    def get_remaining_attempts(self):
        """
        Retourne le nombre de tentatives restantes
        """
        return max(0, self.max_attempts - self.failed_attempts)
    
    def get_usage_history(self):
        """
        Retourne l'historique des utilisations de ce code
        """
        return self.code_usages.all().order_by('-used_at')
        
    def get_discount_display(self):
        """
        Retourne une représentation lisible de la réduction
        """
        if self.code_type != 'promotion' or not self.discount_value:
            return "-"
            
        if self.discount_type == 'percentage':
            return f"{self.discount_value}%"
        else:
            return f"{self.discount_value} FCFA"
            
    def get_associated_item(self):
        """
        Retourne l'élément associé au code (abonnement ou produit)
        """
        if self.code_type == 'certification':
            return self.subscription
        elif self.code_type == 'promotion':
            return self.product
        return None


class CodeUsage(models.Model):
    """
    Modèle pour suivre l'utilisation des codes de vérification
    """
    code = models.ForeignKey(
        PaymentVerificationCode,
        on_delete=models.CASCADE,
        related_name='code_usages',
        verbose_name=_('Code de vérification')
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='code_usage_history',
        verbose_name=_('Utilisateur')
    )
    used_at = models.DateTimeField(_('Date d\'utilisation'), auto_now_add=True)
    ip_address = models.GenericIPAddressField(_('Adresse IP'), null=True, blank=True)
    user_agent = models.TextField(_('User Agent'), blank=True, null=True)
    success = models.BooleanField(_('Réussite'), default=True,
                                help_text=_('Indique si la tentative a réussi'))
    details = models.JSONField(_('Détails'), default=dict, blank=True,
                             help_text=_('Détails supplémentaires sur l\'utilisation'))
    
    class Meta:
        verbose_name = _('Utilisation de code')
        verbose_name_plural = _('Utilisations de codes')
        ordering = ['-used_at']
        indexes = [
            models.Index(fields=['code', 'used_at']),
            models.Index(fields=['user', 'used_at']),
            models.Index(fields=['success', 'used_at']),
        ]
        
    def __str__(self):
        action = "utilisé" if self.success else "tentative échouée"
        return f"Code {self.code.code} {action} par {self.user or 'Anonyme'} le {self.used_at}"
        
    @classmethod
    def record_usage(cls, code, user=None, request=None, success=True, **details):
        """
        Enregistre une utilisation de code
        """
        ip_address = None
        user_agent = None
        
        if request:
            # Récupère l'adresse IP du client
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip_address = x_forwarded_for.split(',')[0]
            else:
                ip_address = request.META.get('REMOTE_ADDR')
                
            user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
        
        return cls.objects.create(
            code=code,
            user=user if user and user.is_authenticated else None,
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
            details=details
        )


class WhatsAppMessage(models.Model):
    """Modèle pour suivre les messages WhatsApp envoyés pour les produits"""
    STATUS_CHOICES = (
        ('pending', _('En attente')),
        ('sent', _('Envoyé')),
        ('delivered', _('Livré')),
        ('failed', _('Échec')),
    )
    
    product = models.ForeignKey(
        'stores.Product',
        on_delete=models.CASCADE,
        related_name='whatsapp_messages',
        verbose_name=_('Produit')
    )
    recipient = models.CharField(_('Destinataire'), max_length=20, help_text=_('Numéro de téléphone au format international'))
    message = models.TextField(_('Message'))
    status = models.CharField(_('Statut'), max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(_('Date de création'), auto_now_add=True)
    sent_at = models.DateTimeField(_('Date d\'envoi'), null=True, blank=True)
    status_updated_at = models.DateTimeField(_('Dernière mise à jour'), auto_now=True)
    error_message = models.TextField(_('Message d\'erreur'), blank=True, null=True)
    
    class Meta:
        verbose_name = _('Message WhatsApp')
        verbose_name_plural = _('Messages WhatsApp')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Message pour {self.product.name} à {self.recipient} - {self.get_status_display()}"
    
    def mark_as_sent(self):
        """Marquer le message comme envoyé"""
        self.status = 'sent'
        self.sent_at = timezone.now()
        self.save()
    
    def mark_as_delivered(self):
        """Marquer le message comme livré"""
        self.status = 'delivered'
        self.save()
    
    def mark_as_failed(self, error_message):
        """Marquer le message comme échoué avec un message d'erreur"""
        self.status = 'failed'
        self.error_message = error_message
        self.save()


class WhatsAppConfig(models.Model):
    """Configuration pour l'API WhatsApp"""
    default_phone_number = models.CharField(
        _('Numéro WhatsApp par défaut'),
        max_length=20,
        default='+22601256984',
        help_text=_('Numéro de téléphone WhatsApp au format international (ex: +226012345678)')
    )
    api_key = models.CharField(
        _('Clé API'),
        max_length=255,
        blank=True,
        help_text=_('Clé d\'API pour l\'envoi de messages WhatsApp')
    )
    api_url = models.URLField(
        _('URL de l\'API'),
        default='https://api.whatsapp.com/send',
        help_text=_('URL de base de l\'API WhatsApp')
    )
    is_active = models.BooleanField(
        _('Actif'),
        default=True,
        help_text=_('Activer/désactiver l\'envoi de messages WhatsApp')
    )
    created_at = models.DateTimeField(_('Date de création'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Dernière mise à jour'), auto_now=True)

    class Meta:
        verbose_name = _('Configuration WhatsApp')
        verbose_name_plural = _('Configurations WhatsApp')

    def __str__(self):
        return f"Configuration WhatsApp - {self.default_phone_number}"
    
    def save(self, *args, **kwargs):
        # S'assurer qu'il n'y a qu'une seule configuration active
        if self.is_active:
            WhatsAppConfig.objects.exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)

    @classmethod
    def get_active_config(cls):
        """Récupérer la configuration active"""
        try:
            return cls.objects.filter(is_active=True).first() or cls.objects.create()
        except Exception:
            return cls()