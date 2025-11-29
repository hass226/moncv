from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from django.core.validators import RegexValidator
from .models import Store, Product, Subscription, Promotion, Category, StudentProfile, Skill, Portfolio, Project, GeneralProfile


class UserRegisterForm(UserCreationForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}))

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': "Nom d'utilisateur"}),
            'password1': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Mot de passe'}),
            'password2': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirmer le mot de passe'}),
        }


class StoreForm(forms.ModelForm):
    description = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control', 
            'rows': 6, 
            'placeholder': 'Décrivez votre boutique de manière attrayante. Mettez en avant vos points forts, vos spécialités et ce qui vous différencie.\n\nExemple : "Boutique spécialisée dans la vente de vêtements africains faits main. Livraison rapide en 24-48h. Retours faciles. Service client réactif 7j/7."',
            'data-controller': 'textarea-autogrow',
        }),
        help_text="Conseils : Décrivez ce que vous vendez, vos valeurs, vos points forts. Utilisez des mots-clés que vos clients pourraient rechercher.",
        max_length=2000
    )
    
    class Meta:
        model = Store
        fields = ['name', 'description', 'whatsapp_number', 'logo']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Nom de votre boutique',
                'data-controller': 'character-counter',
                'maxlength': '100'
            }),
            'whatsapp_number': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Ex: +2250700000000',
                'pattern': r'\+?[0-9\s-]{10,20}'
            }),
            'logo': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
                'data-preview': 'logo-preview'
            }),
        }


class StorePaymentSettingsForm(forms.ModelForm):
    class Meta:
        model = Store
        fields = ['fedapay_merchant_id', 'paystack_subaccount']
        widgets = {
            'fedapay_merchant_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'ID marchand FedaPay (facultatif)',
            }),
            'paystack_subaccount': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Subaccount Paystack (facultatif)',
            }),
        }


class ProductForm(forms.ModelForm):
    # Champs supplémentaires pour améliorer la présentation
    short_description = forms.CharField(
        max_length=160,
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Description courte (160 caractères max) - Sera affichée dans les listes de produits',
            'maxlength': '160',
            'data-controller': 'character-counter'
        }),
        help_text='Une brève description qui apparaîtra dans les résultats de recherche et les aperçus.'
    )
    
    # Amélioration du champ description
    description = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 6,
            'placeholder': 'Décrivez votre produit en détail. Mettez en avant ses caractéristiques, ses avantages et ses spécifications techniques.',
            'data-controller': 'rich-text-editor'
        }),
        help_text='Utilisez des listes à puces et des paragraphes courts pour une meilleure lisibilité.'
    )
    
    # Champ pour l'image principale
    image = forms.ImageField(
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'data-preview': 'image-preview',
            'accept': 'image/*',
        }),
        help_text='Image principale du produit. Taille recommandée : 800x800px. Formats acceptés : JPG, PNG, WEBP.'
    )
    
    # Champ pour les images supplémentaires
    additional_images = forms.FileField(
        required=False,
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control',
            'multiple': False,
            'accept': 'image/*',
        }),
        help_text='Images supplémentaires (sélectionnez une image à la fois). Maximum 5 images.'
    )
    
    # Champs pour les variations de produit (couleur, taille, etc.)
    has_variations = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'data-controller': 'toggle',
            'data-target': 'variations-container',
            'class': 'form-check-input'
        }),
        label='Ce produit a des variantes (tailles, couleurs, etc.)',
        help_text='Cochez cette case si votre produit est disponible en plusieurs versions.'
    )
    
    class Meta:
        model = Product
        fields = [
            'name', 'price', 'currency', 'short_description', 'description', 
            'image', 'category', 'tags', 'stock', 'is_featured', 'is_bestseller'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Nom du produit',
                'data-controller': 'character-counter',
                'maxlength': '100'
            }),
            'price': forms.NumberInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Prix', 
                'step': '0.01',
                'min': '0'
            }),
            'currency': forms.Select(attrs={
                'class': 'form-select',
                'data-controller': 'select2'
            }),
            'category': forms.Select(attrs={
                'class': 'form-select',
                'data-controller': 'select2'
            }),
            'tags': forms.SelectMultiple(attrs={
                'class': 'form-select',
                'data-controller': 'select2',
                'data-placeholder': 'Sélectionnez des tags...'
            }),
            'stock': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'placeholder': 'Quantité en stock'
            }),
            'is_featured': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'data-toggle': 'toggle',
                'data-on': 'Oui',
                'data-off': 'Non',
                'data-onstyle': 'success',
            }),
            'is_bestseller': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'data-toggle': 'toggle',
                'data-on': 'Oui',
                'data-off': 'Non',
                'data-onstyle': 'primary',
            }),
        }
        help_texts = {
            'is_featured': 'Les produits en vedette apparaissent en haut des résultats de recherche.',
            'is_bestseller': 'Marquez ce produit comme best-seller pour le mettre en avant.',
        }


class SubscriptionForm(forms.ModelForm):
    class Meta:
        model = Subscription
        # Plus de sélection de méthode de paiement ni d'ID de transaction à ce stade :
        # on crée simplement la demande d'abonnement, puis on redirige vers la page de paiement.
        fields = []


class StudentProfileForm(forms.ModelForm):
    class Meta:
        model = StudentProfile
        fields = [
            'university', 'field_of_study', 'degree_level', 'graduation_year', 'gpa',
            'bio', 'resume_file', 'profile_picture', 'cover_photo',
            'phone', 'email_public', 'website', 'linkedin_url', 'github_url', 'portfolio_url',
            'city', 'country', 'is_public'
        ]
        widgets = {
            'university': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Université Félix Houphouët-Boigny'
            }),
            'field_of_study': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Informatique, Gestion, Droit...'
            }),
            'degree_level': forms.Select(attrs={
                'class': 'form-select',
            }, choices=StudentProfile._meta.get_field('degree_level').choices),
            'graduation_year': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '2000',
                'max': '2030',
                'placeholder': 'Ex: 2024'
            }),
            'gpa': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'max': '4',
                'placeholder': 'Ex: 3.5'
            }),
            'bio': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Décrivez-vous brièvement...',
                'data-controller': 'character-counter',
                'maxlength': '500'
            }),
            'resume_file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.doc,.docx',
            }),
            'profile_picture': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
                'data-preview': 'profile-picture-preview'
            }),
            'cover_photo': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
                'data-preview': 'cover-photo-preview'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: +2250700000000'
            }),
            'email_public': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'email@exemple.com'
            }),
            'website': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://votresite.com'
            }),
            'linkedin_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://linkedin.com/in/votrenom'
            }),
            'github_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://github.com/votrenom'
            }),
            'portfolio_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://votreportfolio.com'
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ville'
            }),
            'country': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Pays'
            }),
            'is_public': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'data-toggle': 'toggle',
                'data-on': 'Public',
                'data-off': 'Privé',
                'data-onstyle': 'success',
                'data-offstyle': 'secondary',
            }),
        }
        help_texts = {
            'gpa': 'Sur une échelle de 0 à 4 (optionnel)',
            'email_public': 'Cette adresse sera visible sur votre profil public',
            'is_public': 'Rendre votre profil visible par les recruteurs et autres utilisateurs',
        }

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if phone and not phone.startswith('+'):
            raise forms.ValidationError("Veuillez inclure l'indicatif du pays (ex: +225 pour la Côte d'Ivoire)")
        return phone


class GeneralProfileForm(forms.ModelForm):
    class Meta:
        model = GeneralProfile
        fields = [
            'phone', 'avatar', 'address', 'city', 'country',
            'is_public', 'bio', 'facebook_url', 'twitter_handle',
            'instagram_handle', 'email_notifications', 'newsletter'
        ]
        widgets = {
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+2250700000000',
                'pattern': '\\+?[0-9\\s-]{10,20}'
            }),
            'avatar': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/jpeg,image/png,image/webp',
                'data-preview': 'avatar-preview',
                'data-max-size': '5242880'  # 5MB
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Votre adresse complète',
                'rows': 2
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ville de résidence'
            }),
            'country': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Pays de résidence'
            }),
            'bio': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Décrivez-vous en quelques mots...',
                'maxlength': '500'
            }),
            'facebook_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://facebook.com/votre-profil'
            }),
            'twitter_handle': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '@votrepseudo',
                'maxlength': '50'
            }),
            'instagram_handle': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '@votrepseudo',
                'maxlength': '50'
            }),
            'is_public': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'role': 'switch'
            }),
            'email_notifications': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'role': 'switch'
            }),
            'newsletter': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'role': 'switch'
            }),
        }
        help_texts = {
            'phone': 'Format international recommandé : +225XXXXXXXX',
            'avatar': 'Image carrée recommandée (200x200px). Formats acceptés : JPG, PNG, WEBP (max 5 Mo)',
            'is_public': 'Rendre votre profil visible par tous les visiteurs du site',
            'email_notifications': 'Recevoir des notifications par email',
            'newsletter': "Recevoir notre newsletter et des offres spéciales",
            'bio': 'Décrivez-vous en quelques mots (500 caractères maximum)',
            'facebook_url': 'URL complète de votre profil Facebook',
            'twitter_handle': 'Votre pseudo Twitter sans le @',
            'instagram_handle': 'Votre pseudo Instagram sans le @'
        }

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if not phone:
            return phone
            
        if not phone.startswith('+'):
            raise forms.ValidationError("Veuillez inclure l'indicatif du pays (ex: +225 pour la Côte d'Ivoire)")
            
        # Supprimer tous les caractères non numériques sauf le signe +
        clean_phone = '+' + ''.join(c for c in phone[1:] if c.isdigit())
        
        if len(clean_phone) < 10:
            raise forms.ValidationError("Le numéro de téléphone est trop court")
            
        if len(clean_phone) > 16:
            raise forms.ValidationError("Le numéro de téléphone est trop long")
            
        return clean_phone

    def clean_facebook_url(self):
        facebook_url = self.cleaned_data.get('facebook_url')
        if facebook_url and not facebook_url.startswith(('http://', 'https://')):
            return 'https://' + facebook_url
        return facebook_url


class SkillForm(forms.ModelForm):
    class Meta:
        model = Skill
        fields = ['name', 'level', 'category']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Python, Design, Marketing Digital...'
            }),
            'level': forms.Select(attrs={
                'class': 'form-select',
            }),
            'category': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Programmation, Design, Langues...'
            }),
        }


class PortfolioForm(forms.ModelForm):
    class Meta:
        model = Portfolio
        fields = ['title', 'description', 'image', 'url', 'github_url', 'technologies']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Titre du projet'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Décrivez le projet et votre rôle...'
            }),
            'image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
                'data-preview': 'portfolio-image-preview'
            }),
            'url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'Lien vers le projet en ligne (optionnel)'
            }),
            'github_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'Lien vers le dépôt GitHub (optionnel)'
            }),
            'technologies': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Python, Django, React, Figma...'
            }),
        }
        help_texts = {
            'technologies': 'Séparez les technologies par des virgules',
        }


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['title', 'description', 'course', 'grade', 'file']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Titre du projet ou du devoir'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Description du projet et compétences mises en œuvre...'
            }),
            'course': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nom du cours ou de la matière'
            }),
            'grade': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Note obtenue (optionnel)'
            }),
            'file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.doc,.docx,.zip',
            }),
        }


class CategoryForm(forms.ModelForm):
    """
    Formulaire pour la création et la modification de catégories
    """
    class Meta:
        model = Category
        fields = ['name', 'icon']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nom de la catégorie',
                'required': 'required'
            }),
            'icon': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: fas fa-tag',
                'help_text': "Nom de l'icône Bootstrap"
            })
        }


class ContactForm(forms.Form):
    """
    Formulaire de contact
    """
    name = forms.CharField(
        label='Votre nom',
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Votre nom complet',
            'required': 'required'
        })
    )
    
    email = forms.EmailField(
        label='Votre email',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'votre@email.com',
            'required': 'required'
        })
    )
    
    phone = forms.CharField(
        label='Téléphone (optionnel)',
        required=False,
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+225 07 00 00 00 00',
        }),
        validators=[
            RegexValidator(
                regex=r'^\+?[0-9\s-]{10,20}$',
                message='Format de numéro invalide. Ex: +225 07 00 00 00 00',
                code='invalid_phone'
            ),
        ]
    )
    
    subject = forms.CharField(
        label='Sujet',
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Sujet de votre message',
            'required': 'required'
        })
    )
    
    message = forms.CharField(
        label='Votre message',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 5,
            'placeholder': 'Décrivez-nous votre demande en détail...',
            'required': 'required'
        })
    )
    
    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()
        if phone:
            # Nettoyer le numéro de téléphone
            phone = ''.join(c for c in phone if c.isdigit() or c == '+')
        return phone


class PromotionForm(forms.ModelForm):
    TARGET_AUDIENCE_CHOICES = [
        ('all', 'Tous les utilisateurs'),
        ('followers', 'Abonnés de la boutique'),
        ('previous_customers', 'Anciens clients'),
        ('inactive_customers', 'Clients inactifs (plus de 3 mois)'),
    ]
    
    PACK_CHOICES = [
        ('1000', '🚀 Pack Flash - 1000 FCFA'),
        ('2000', '⚡ Pack Express - 2000 FCFA'),
        ('3000', '💎 Pack Pro - 3000 FCFA'),
        ('5000', '� Pack VIP - 5000 FCFA'),
    ]
    
    PACK_DETAILS = {
        '1000': {'duration': 1, 'reach': '2 500 personnes', 'features': ['Mise en avant 24h', 'Notification push']},
        '2000': {'duration': 2, 'reach': '6 000 personnes', 'features': ['Mise en avant 48h', 'Notification push', 'Email marketing']},
        '3000': {'duration': 3, 'reach': '12 000 personnes', 'features': ['Mise en avant 72h', 'Notification push', 'Email marketing', 'Mise en avant sur la page d\'accueil']},
        '5000': {'duration': 7, 'reach': '30 000 personnes', 'features': ['Mise en avant 1 semaine', 'Notification push', 'Email marketing', 'Mise en avant sur la page d\'accueil', 'Bannière publicitaire']},
    }

    pack = forms.ChoiceField(
        label='Choisissez votre pack',
        choices=PACK_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'd-none'}),  # Masquer les boutons radio par défaut
        required=True
    )
    
    target_audience = forms.MultipleChoiceField(
        label='Public cible',
        choices=TARGET_AUDIENCE_CHOICES,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=True,
        initial=['all']
    )
    
    custom_message = forms.CharField(
        label='Message personnalisé',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Écrivez un message accrocheur pour votre promotion...',
            'maxlength': '200'
        }),
        required=False,
        help_text='200 caractères maximum. Ce message apparaîtra dans la notification de promotion.'
    )
    
    discount_code = forms.CharField(
        label='Code de réduction (optionnel)',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ex: SOLDE20',
            'maxlength': '20'
        }),
        required=False,
        help_text='Créez un code promo pour suivre l\'efficacité de votre campagne.'
    )

    class Meta:
        model = Promotion
        # ici on ne configure que la promotion elle-même. Le montant est calculé en fonction du pack.
        fields = ['promotion_type', 'product', 'store', 'amount']
        widgets = {
            'promotion_type': forms.Select(attrs={'class': 'form-control'}),
            'product': forms.Select(attrs={'class': 'form-control'}),
            'store': forms.Select(attrs={'class': 'form-control'}),
            # Montant affiché en lecture seule, calculé automatiquement selon le pack
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'readonly': 'readonly'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        # Le montant est calculé à partir du pack, il ne doit pas être obligatoire dans le formulaire
        if 'amount' in self.fields:
            self.fields['amount'].required = False
        if user and hasattr(user, 'store'):
            self.fields['product'].queryset = Product.objects.filter(store=user.store)
            self.fields['store'].queryset = Store.objects.filter(id=user.store.id)
            self.fields['store'].initial = user.store.id
        else:
            self.fields['product'].queryset = Product.objects.none()
            self.fields['store'].queryset = Store.objects.none()

    def save(self, commit=True):
        promotion = super().save(commit=False)
        pack = self.cleaned_data.get('pack')

        # Définir le prix, la durée et le nombre de personnes en fonction du pack choisi
        if pack == '1000':
            price = 1000
            duration_days = 1
            reach = 2500  # Augmenté de 1000 à 2500
        elif pack == '2000':
            price = 2000
            duration_days = 2
            reach = 6000  # Augmenté de 3000 à 6000
        elif pack == '3000':
            price = 3000
            duration_days = 3
            reach = 12000  # Augmenté de 6000 à 12000
        elif pack == '5000':
            price = 5000
            duration_days = 7
            reach = 30000  # Augmenté de 15000 à 30000
        else:
            # Valeur par défaut de sécurité
            price = 1000
            duration_days = 1
            reach = 1000

        promotion.amount = price
        promotion.starts_at = timezone.now()
        promotion.expires_at = timezone.now() + timedelta(days=duration_days)
        # Sauvegarder la portée estimée dans les métadonnées
        if not promotion.metadata:
            promotion.metadata = {}
        promotion.metadata['estimated_reach'] = reach
        if commit:
            promotion.save()
        return promotion

