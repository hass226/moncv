from django import forms
from django.forms import ModelForm
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError

from .models import PaymentVerificationCode, CodeUsage
from stores.models import Store, Subscription, Product

class PaymentVerificationForm(forms.Form):
    PAYMENT_METHODS = (
        ('', 'Sélectionnez une méthode de paiement'),
        ('orange', 'Orange Money'),
        ('mtn', 'MTN Mobile Money'),
        ('moov', 'Moov Money'),
        ('wave', 'Wave'),
        ('paypal', 'PayPal'),
        ('carte', 'Carte Bancaire')
    )
    
    payment_method = forms.ChoiceField(
        label='Méthode de paiement',
        choices=PAYMENT_METHODS,
        required=True,
        widget=forms.Select(attrs={
            'class': 'form-control',
            'id': 'payment-method'
        })
    )
    
    transaction_id = forms.CharField(
        label='Code de transaction',
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ex: OM12345678',
            'id': 'transaction-id'
        })
    )


class VerificationCodeForm(forms.Form):
    """Formulaire pour la vérification d'un code de paiement"""
    code = forms.CharField(
        label=_('Code de vérification'),
        max_length=14,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control text-uppercase',
            'placeholder': 'XXXX-XXXX-XXXX',
            'autocomplete': 'off',
            'style': 'letter-spacing: 2px; font-size: 1.2em;'
        })
    )

    def clean_code(self):
        code = self.cleaned_data['code'].strip().upper()
        # Vérifier le format du code (XXXX-XXXX-XXXX)
        if len(code) != 14 or code[4] != '-' or code[9] != '-':
            raise forms.ValidationError(_("Format de code invalide. Le format attendu est XXXX-XXXX-XXXX"))
        return code


class BaseCodeForm(forms.ModelForm):
    """Formulaire de base pour les codes de vérification et promotionnels"""
    class Meta:
        model = PaymentVerificationCode
        fields = ['code_type', 'code', 'usage_limit', 'expires_at', 'max_attempts', 'notes']
        widgets = {
            'code_type': forms.Select(attrs={'class': 'form-control select2', 'id': 'code-type'}),
            'code': forms.TextInput(attrs={
                'class': 'form-control text-uppercase',
                'placeholder': _('Laissez vide pour générer automatiquement')
            }),
            'usage_limit': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'step': 1,
                'value': 1
            }),
            'expires_at': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control datepicker'
            }),
            'max_attempts': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'value': 5
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('Notes optionnelles sur ce code...')
            }),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.fields['expires_at'].required = True
        self.fields['code'].required = False
        
        # Définir la date d'expiration par défaut à 30 jours
        if not self.instance.pk and 'expires_at' not in self.data:
            self.initial['expires_at'] = (timezone.now() + timezone.timedelta(days=30)).strftime('%Y-%m-%d')
            
    def clean(self):
        cleaned_data = super().clean()
        code_type = cleaned_data.get('code_type')
        
        # Validation spécifique au type de code
        if code_type == 'certification' and not cleaned_data.get('subscription'):
            self.add_error('subscription', _('Ce champ est obligatoire pour les codes de certification.'))
            
        if code_type == 'promotion' and not cleaned_data.get('product'):
            self.add_error('product', _('Ce champ est obligatoire pour les codes promotionnels.'))
            
        return cleaned_data


class CertificationCodeForm(BaseCodeForm):
    """Formulaire pour les codes de certification"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filtrer les abonnements par l'utilisateur connecté
        self.fields['subscription'] = forms.ModelChoiceField(
            queryset=Subscription.objects.filter(store__owner=self.user) if self.user else Subscription.objects.none(),
            label=_('Abonnement associé'),
            required=True,
            widget=forms.Select(attrs={
                'class': 'form-control select2',
                'data-placeholder': _('Sélectionnez un abonnement...')
            })
        )
        
        # Définir la valeur par défaut du type de code
        self.fields['code_type'].initial = 'certification'
        self.fields['code_type'].widget = forms.HiddenInput()

    class Meta(BaseCodeForm.Meta):
        fields = BaseCodeForm.Meta.fields + ['subscription']


class PromotionCodeForm(BaseCodeForm):
    """Formulaire pour les codes promotionnels"""
    discount_type = forms.ChoiceField(
        choices=[('percentage', '%'), ('fixed', 'FCFA')],
        initial='percentage',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    discount_value = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filtrer les produits par l'utilisateur connecté
        self.fields['product'] = forms.ModelChoiceField(
            queryset=Product.objects.filter(store__owner=self.user) if self.user else Product.objects.none(),
            label=_('Produit associé'),
            required=True,
            widget=forms.Select(attrs={
                'class': 'form-control select2',
                'data-placeholder': _('Sélectionnez un produit...')
            })
        )
        
        # Définir la valeur par défaut du type de code
        self.fields['code_type'].initial = 'promotion'
        self.fields['code_type'].widget = forms.HiddenInput()
        
        # Initialiser les valeurs de réduction si elles existent déjà
        if self.instance and self.instance.discount_value is not None:
            self.initial['discount_type'] = self.instance.discount_type
            self.initial['discount_value'] = self.instance.discount_value

    class Meta(BaseCodeForm.Meta):
        fields = BaseCodeForm.Meta.fields + ['product', 'discount_type', 'discount_value']
        
    def save(self, commit=True):
        code = super().save(commit=False)
        code.discount_type = self.cleaned_data.get('discount_type')
        code.discount_value = self.cleaned_data.get('discount_value')
        
        if commit:
            code.save()
            self.save_m2m()
            
        return code


class GenerateCodesForm(forms.Form):
    """Formulaire pour générer des codes en lot"""
    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        
        # Mettre à jour les choix en fonction de l'utilisateur connecté
        if user:
            # Mise à jour des querysets pour les champs dépendants de l'utilisateur
            # Les administrateurs/staff peuvent voir toutes les boutiques
            if getattr(user, 'is_staff', False):
                stores = Store.objects.all()
            else:
                stores = Store.objects.filter(owner=user)
            self.fields['store'].queryset = stores
            # Mettre à jour les abonnements et produits en fonction des boutiques de l'utilisateur
            if stores.exists():
                self.fields['subscription'].queryset = Subscription.objects.filter(store__in=stores)
                self.fields['product'].queryset = Product.objects.filter(store__in=stores)

                # Si l'utilisateur n'a qu'un seul abonnement, le sélectionner par défaut
                if self.fields['subscription'].queryset.count() == 1:
                    self.fields['subscription'].initial = self.fields['subscription'].queryset.first()
            else:
                self.fields['subscription'].queryset = Subscription.objects.none()
                self.fields['product'].queryset = Product.objects.none()
                
            # Si l'utilisateur n'a qu'une seule boutique, la sélectionner par défaut
            if stores.count() == 1:
                self.fields['store'].initial = stores.first()
        
        # Définir les champs requis en fonction du type de code
        self.set_required_fields()
    
    def set_required_fields(self):
        """Définit les champs requis en fonction du type de code sélectionné"""
        # Vérifier d'abord dans self.data (soumission de formulaire)
        code_type = None
        
        if hasattr(self, 'data') and self.data:
            code_type = self.data.get('code_type')
        
        # Si pas dans data, vérifier dans les données initiales
        if not code_type and hasattr(self, 'initial') and 'code_type' in self.initial:
            code_type = self.initial['code_type']
        
        # Si toujours pas de code_type, vérifier dans les données du formulaire
        if not code_type and hasattr(self, 'cleaned_data') and 'code_type' in self.cleaned_data:
            code_type = self.cleaned_data['code_type']
        
        # Par défaut, tous les champs ne sont pas requis
        self.fields['subscription'].required = False
        self.fields['product'].required = False
        
        # Si le type de code est défini, mettre à jour les champs requis
        if code_type == 'certification':
            self.fields['subscription'].required = True
            # Si l'utilisateur n'a qu'un seul abonnement, le sélectionner automatiquement
            if hasattr(self, 'user') and self.user and not self.data.get('subscription'):
                subscription = Subscription.objects.filter(store__owner=self.user).first()
                if subscription:
                    self.initial['subscription'] = subscription.id
        elif code_type == 'promotion':
            self.fields['product'].required = True
    
    # Champs pour la boutique et le type de plan
    store = forms.ModelChoiceField(
        queryset=Store.objects.none(),
        label=_('Boutique'),
        required=True,
        widget=forms.Select(attrs={
            'class': 'form-control select2',
            'data-placeholder': _('Sélectionnez une boutique...'),
            'id': 'store-field'
        })
    )
    
    plan_type = forms.ChoiceField(
        choices=(
            ('basic', 'Basique'),
            ('standard', 'Standard'),
            ('premium', 'Premium'),
        ),
        label=_('Type de plan'),
        required=True,
        widget=forms.Select(attrs={
            'class': 'form-control',
            'id': 'plan-type-field'
        })
    )
    
    code_type = forms.ChoiceField(
        choices=PaymentVerificationCode.CODE_TYPES,
        label=_('Type de code'),
        widget=forms.Select(attrs={
            'class': 'form-control',
            'id': 'code-type-selector'
        })
    )
    
    # Champs pour les codes de certification
    subscription = forms.ModelChoiceField(
        queryset=Subscription.objects.none(),
        label=_('Abonnement associé'),
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control select2',
            'data-placeholder': _('Sélectionnez un abonnement...'),
            'id': 'subscription-field'
        })
    )
    
    # Champs pour les codes promotionnels
    product = forms.ModelChoiceField(
        queryset=Product.objects.none(),
        label=_('Produit associé'),
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control select2',
            'data-placeholder': _('Sélectionnez un produit...'),
            'id': 'product-field'
        })
    )
    
    # Champs communs
    count = forms.IntegerField(
        label=_('Nombre de codes à générer'),
        min_value=1,
        max_value=100,
        initial=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': 1,
            'max': 100
        })
    )
    
    days_valid = forms.IntegerField(
        label=_('Durée de validité (en jours)'),
        min_value=1,
        initial=30,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': 1
        })
    )
    
    usage_limit = forms.IntegerField(
        label=_('Nombre maximum d\'utilisations par code'),
        min_value=0,
        initial=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': 0
        }),
        help_text=_('0 pour un nombre illimité d\'utilisations')
    )
    
    max_attempts = forms.IntegerField(
        label=_('Nombre maximum de tentatives'),
        min_value=1,
        max_value=20,
        initial=5,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': 1,
            'max': 20
        })
    )
    
    # Champs pour les codes promotionnels
    discount_type = forms.ChoiceField(
        choices=[('percentage', '%'), ('fixed', 'FCFA')],
        initial='percentage',
        widget=forms.Select(attrs={
            'class': 'form-control',
            'id': 'discount-type-field'
        }),
        required=False
    )
    
    discount_value = forms.DecimalField(
        label=_('Valeur de la réduction'),
        max_digits=10,
        decimal_places=2,
        min_value=0,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'id': 'discount-value-field'
        })
    )
    
    class Media:
        js = ('js/code_generation.js',)
    
    def clean(self):
        cleaned_data = super().clean()
        code_type = cleaned_data.get('code_type')
        store = cleaned_data.get('store')
        
        # Log des données nettoyées
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Données nettoyées: {cleaned_data}")
        
        # Validation des champs obligatoires communs
        required_fields = ['store', 'code_type', 'count', 'days_valid']
        for field in required_fields:
            if field not in cleaned_data or cleaned_data[field] is None:
                error_msg = f'Champ manquant: {field}'
                logger.warning(error_msg)
                self.add_error(field, _('Ce champ est obligatoire.'))
        
        # Validation de la boutique
        if store and self.user and store.owner != self.user:
            error_msg = f'Utilisateur non autorisé pour la boutique: user_id={self.user.id}, store_owner_id={store.owner.id}'
            logger.warning(error_msg)
            self.add_error('store', _("Vous n'êtes pas autorisé à générer des codes pour cette boutique."))
        
        # Validation spécifique au type de code
        if code_type == 'certification':
            if not cleaned_data.get('subscription'):
                error_msg = 'Abonnement manquant pour un code de certification'
                logger.warning(error_msg)
                self.add_error('subscription', _('Ce champ est obligatoire pour les codes de certification.'))
            
            # Vérifier que l'abonnement appartient bien à la boutique sélectionnée
            subscription = cleaned_data.get('subscription')
            if subscription and store and subscription.store != store:
                error_msg = f'Abonnement {subscription.id} n\'appartient pas à la boutique {store.id}'
                logger.warning(error_msg)
                self.add_error('subscription', _("L'abonnement sélectionné n'appartient pas à la boutique choisie."))
            
        elif code_type == 'promotion':
            if not cleaned_data.get('product'):
                error_msg = 'Produit manquant pour un code promotionnel'
                logger.warning(error_msg)
                self.add_error('product', _('Ce champ est obligatoire pour les codes promotionnels.'))
            
            if not cleaned_data.get('discount_value'):
                error_msg = 'Valeur de réduction manquante pour un code promotionnel'
                logger.warning(error_msg)
                self.add_error('discount_value', _('Ce champ est obligatoire pour les codes promotionnels.'))
            
            # Vérifier que le produit appartient bien à la boutique sélectionnée
            product = cleaned_data.get('product')
            if product and store and product.store != store:
                error_msg = f'Produit {product.id} n\'appartient pas à la boutique {store.id}'
                logger.warning(error_msg)
                self.add_error('product', _("Le produit sélectionné n'appartient pas à la boutique choisie."))
            
            # Validation de la valeur de réduction
            discount_value = cleaned_data.get('discount_value')
            discount_type = cleaned_data.get('discount_type')
            
            if discount_value is not None:
                if discount_type == 'percentage' and (discount_value <= 0 or discount_value > 100):
                    error_msg = f'Valeur de réduction invalide: {discount_value}% (doit être entre 0 et 100)'
                    logger.warning(error_msg)
                    self.add_error('discount_value', _('La réduction en pourcentage doit être comprise entre 0 et 100%'))
                elif discount_type == 'fixed' and discount_value <= 0:
                    error_msg = f'Montant de réduction invalide: {discount_value} (doit être supérieur à 0)'
                    logger.warning(error_msg)
                    self.add_error('discount_value', _('Le montant de la réduction doit être supérieur à 0'))
        
        # Validation des valeurs numériques
        count = cleaned_data.get('count')
        if count is not None and (count < 1 or count > 100):
            error_msg = f'Nombre de codes invalide: {count} (doit être entre 1 et 100)'
            logger.warning(error_msg)
            self.add_error('count', _('Le nombre de codes doit être compris entre 1 et 100'))
            
        days_valid = cleaned_data.get('days_valid')
        if days_valid is not None and days_valid < 1:
            error_msg = f'Durée de validité invalide: {days_valid} jours (doit être d\'au moins 1 jour)'
            logger.warning(error_msg)
            self.add_error('days_valid', _('La durée de validité doit être d\'au moins 1 jour'))
            
        usage_limit = cleaned_data.get('usage_limit', 1)
        if usage_limit is not None and usage_limit < 0:
            error_msg = f'Limite d\'utilisation invalide: {usage_limit} (ne peut pas être négative)'
            logger.warning(error_msg)
            self.add_error('usage_limit', _('La limite d\'utilisation ne peut pas être négative'))
            
        max_attempts = cleaned_data.get('max_attempts', 5)
        if max_attempts is not None and (max_attempts < 1 or max_attempts > 20):
            error_msg = f'Nombre maximum de tentatives invalide: {max_attempts} (doit être entre 1 et 20)'
            logger.warning(error_msg)
            self.add_error('max_attempts', _('Le nombre maximum de tentatives doit être compris entre 1 et 20'))
        
        # Log des erreurs de validation
        if self.errors:
            logger.warning(f'Erreurs de validation du formulaire: {self.errors}')
        else:
            logger.info('Formulaire valide')
            
        return cleaned_data


class SubscriptionForm(ModelForm):
    """Formulaire pour la création et la modification des abonnements"""
    class Meta:
        model = Subscription
        fields = ['plan_type', 'amount', 'payment_method', 'status', 'transaction_id', 'expires_at']
        widgets = {
            'plan_type': forms.Select(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': '0.01'}),
            'payment_method': forms.Select(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'transaction_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ID de transaction'}),
            'expires_at': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }


class PaymentForm(forms.Form):
    PAYMENT_METHODS = (
        ('orange', 'Orange Money'),
        ('mtn', 'MTN Mobile Money'),
        ('moov', 'Moov Money'),
        ('wave', 'Wave'),
        ('paypal', 'PayPal'),
        ('carte', 'Carte Bancaire')
    )
    
    payment_method = forms.ChoiceField(
        label='Méthode de paiement',
        choices=PAYMENT_METHODS,
        required=True,
        widget=forms.RadioSelect(attrs={
            'class': 'form-check-input'
        })
    )
    
    phone_number = forms.CharField(
        label='Numéro de téléphone',
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ex: +225XXXXXXXX',
            'id': 'phone-number'
        }),
        help_text="Renseignez votre numéro si vous payez par mobile money"
    )
    
    amount = forms.DecimalField(
        label='Montant à payer',
        max_digits=10,
        decimal_places=2,
        required=True,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'id': 'amount'
        })
    )
    
    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number', '').strip()
        if phone_number and not phone_number.startswith('+'):
            phone_number = f'+225{phone_number.lstrip('225')}'
        return phone_number
