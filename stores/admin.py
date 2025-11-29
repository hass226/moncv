from django.contrib import admin
from .models import (
    Store, Product, ProductImage, Subscription, Promotion, Category, Tag,
    Follow, Like, Comment, Share, Review, Favorite, Notification, SearchHistory,
    Payment, Order, GeneralProfile,
    # Nouvelles fonctionnalités
    LiveStream, LiveProduct, LiveComment, LivePurchase,
    StudentProfile, Skill, Portfolio, Project, Recommendation,
    Job, JobApplication, JobCategory,
    Classroom, ClassPost, ClassNote, Tutorial,
    AIRequest, FraudReport, AccountVerification
)


@admin.register(GeneralProfile)
class GeneralProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone', 'city', 'country', 'is_public', 'created_at']
    list_filter = ['is_public', 'created_at']
    search_fields = ['user__username', 'phone', 'city', 'country']
    list_editable = ['is_public']
    readonly_fields = ['created_at', 'updated_at', 'last_seen', 'profile_views']
    fieldsets = (
        ('Informations personnelles', {
            'fields': ('user', 'phone', 'avatar')
        }),
        ('Localisation', {
            'fields': ('address', 'city', 'country')
        }),
        ('Réseaux sociaux', {
            'fields': ('facebook_url', 'twitter_handle', 'instagram_handle'),
            'classes': ('collapse',)
        }),
        ('Préférences', {
            'fields': ('is_public', 'email_notifications', 'newsletter')
        }),
        ('Statistiques', {
            'fields': ('profile_views', 'last_seen'),
            'classes': ('collapse',)
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'is_verified', 'is_featured', 'whatsapp_number', 'created_at']
    list_filter = ['is_verified', 'is_featured', 'created_at']
    search_fields = ['name', 'owner__username']
    list_editable = ['is_verified', 'is_featured']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'store', 'price', 'stock', 'is_featured', 'is_bestseller', 'created_at', 'updated_at']
    list_filter = ['is_featured', 'is_bestseller', 'created_at', 'updated_at', 'store', 'category']
    search_fields = ['name', 'description', 'short_description', 'sku', 'store__name']
    list_editable = ['is_featured', 'is_bestseller', 'stock']
    readonly_fields = ['views_count', 'likes_count', 'shares_count', 'created_at', 'updated_at']
    prepopulated_fields = {}
    date_hierarchy = 'created_at'
    list_per_page = 25
    
    fieldsets = (
        ('Informations de base', {
            'fields': ('store', 'name', 'sku', 'category', 'tags')
        }),
        ('Prix et stock', {
            'fields': ('price', 'currency', 'stock', 'weight')
        }),
        ('Description', {
            'fields': ('short_description', 'description')
        }),
        ('Visibilité', {
            'fields': ('is_featured', 'is_bestseller', 'featured_until')
        }),
        ('Métriques', {
            'fields': ('views_count', 'likes_count', 'shares_count'),
            'classes': ('collapse',)
        }),
        ('Dates', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        """Sauvegarder le modèle avec l'utilisateur actuel comme modificateur"""
        if not obj.pk:  # Si c'est une nouvelle entrée
            obj.store = obj.store or (hasattr(request.user, 'store') and request.user.store)
        super().save_model(request, obj, form, change)
    
    def get_queryset(self, request):
        """Optimiser les requêtes avec select_related et prefetch_related"""
        return super().get_queryset(request).select_related('store', 'category').prefetch_related('tags')
    
    def view_on_site(self, obj):
        """Lien pour voir le produit sur le site"""
        from django.urls import reverse
        return reverse('product_detail', args=[obj.id, obj.slug])


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['store', 'plan_type', 'amount', 'payment_method', 'status', 'is_active', 'expires_at', 'created_at']
    list_filter = ['status', 'is_active', 'plan_type', 'payment_method', 'created_at']
    search_fields = ['store__name', 'transaction_id']
    readonly_fields = ['created_at', 'updated_at']
    actions = ['approve_subscriptions', 'reject_subscriptions']
    
    def approve_subscriptions(self, request, queryset):
        """Approuver les abonnements sélectionnés"""
        count = 0
        for subscription in queryset.filter(status='pending'):
            subscription.status = 'completed'
            subscription.is_active = True
            subscription.store.is_verified = True
            subscription.store.save()
            subscription.save()
            count += 1
        self.message_user(request, f'{count} abonnement(s) approuvé(s) avec succès.')
    approve_subscriptions.short_description = "Approuver les abonnements sélectionnés"
    
    def reject_subscriptions(self, request, queryset):
        """Rejeter les abonnements sélectionnés"""
        count = queryset.update(status='failed', is_active=False)
        self.message_user(request, f'{count} abonnement(s) rejeté(s).')
    reject_subscriptions.short_description = "Rejeter les abonnements sélectionnés"


@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    list_display = ['promotion_type', 'product', 'store', 'amount', 'payment_method', 'status', 'expires_at', 'created_at']
    list_filter = ['status', 'promotion_type', 'payment_method', 'created_at']
    search_fields = ['product__name', 'store__name', 'transaction_id']
    actions = ['approve_promotions', 'reject_promotions']
    
    def approve_promotions(self, request, queryset):
        """Approuver les promotions sélectionnées"""
        count = 0
        for promotion in queryset.filter(status='pending'):
            promotion.status = 'active'
            if promotion.promotion_type == 'product' and promotion.product:
                promotion.product.is_featured = True
                promotion.product.featured_until = promotion.expires_at
                promotion.product.save()
            elif promotion.promotion_type == 'store' and promotion.store:
                promotion.store.is_featured = True
                promotion.store.save()
            promotion.save()
            count += 1
        self.message_user(request, f'{count} promotion(s) approuvée(s) avec succès.')
    approve_promotions.short_description = "Approuver les promotions sélectionnées"
    
    def reject_promotions(self, request, queryset):
        """Rejeter les promotions sélectionnées"""
        count = queryset.update(status='cancelled')
        self.message_user(request, f'{count} promotion(s) rejetée(s).')
    reject_promotions.short_description = "Rejeter les promotions sélectionnées"


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'icon', 'created_at']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'created_at']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ['user', 'store', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'store__name']


@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'product__name']


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'product__name', 'content']


@admin.register(Share)
class ShareAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'platform', 'created_at']
    list_filter = ['platform', 'created_at']
    search_fields = ['user__username', 'product__name']


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'rating', 'created_at']
    list_filter = ['rating', 'created_at']
    search_fields = ['user__username', 'product__name', 'comment']


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'product__name']


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'notification_type', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['user__username', 'message']


@admin.register(SearchHistory)
class SearchHistoryAdmin(admin.ModelAdmin):
    list_display = ['user', 'query', 'created_at']
    list_filter = ['created_at']
    search_fields = ['query', 'user__username']


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['id', 'amount', 'payment_method', 'status', 'payer_name', 'payer_phone', 'created_at']
    list_filter = ['status', 'payment_method', 'created_at']
    search_fields = ['transaction_id', 'payment_reference', 'payer_name', 'payer_email', 'payer_phone']
    readonly_fields = ['created_at', 'updated_at', 'paid_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Informations de base', {
            'fields': ('order', 'subscription', 'promotion', 'amount', 'payment_method', 'status')
        }),
        ('Transaction', {
            'fields': ('transaction_id', 'payment_reference', 'external_id')
        }),
        ('Payer', {
            'fields': ('payer_name', 'payer_email', 'payer_phone')
        }),
        ('Métadonnées', {
            'fields': ('metadata',)
        }),
        ('Dates', {
            'fields': ('paid_at', 'created_at', 'updated_at')
        }),
    )


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'product', 'store', 'customer_name', 'total_price', 'status', 'payment_status', 'created_at']
    list_filter = ['status', 'payment_status', 'delivery_method', 'created_at']
    search_fields = ['customer_name', 'customer_phone', 'customer_email', 'tracking_number', 'product__name', 'store__name']
    readonly_fields = ['created_at', 'updated_at', 'delivered_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Produit et boutique', {
            'fields': ('product', 'store', 'customer')
        }),
        ('Informations de commande', {
            'fields': ('quantity', 'unit_price', 'total_price', 'delivery_fee', 'status', 'delivery_method')
        }),
        ('Localisation', {
            'fields': ('address', 'city', 'postal_code', 'country', 'latitude', 'longitude')
        }),
        ('Contact client', {
            'fields': ('customer_name', 'customer_phone', 'customer_email')
        }),
        ('Paiement', {
            'fields': ('payment_status', 'payment_method')
        }),
        ('Livraison', {
            'fields': ('tracking_number', 'estimated_delivery', 'delivered_at')
        }),
        ('Notes', {
            'fields': ('notes', 'internal_notes')
        }),
        ('Dates', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    actions = ['mark_as_confirmed', 'mark_as_preparing', 'mark_as_shipped', 'mark_as_delivered']
    
    def mark_as_confirmed(self, request, queryset):
        count = queryset.update(status='confirmed')
        self.message_user(request, f'{count} commande(s) confirmée(s).')
    mark_as_confirmed.short_description = "Marquer comme confirmées"
    
    def mark_as_preparing(self, request, queryset):
        count = queryset.update(status='preparing')
        self.message_user(request, f'{count} commande(s) en préparation.')
    mark_as_preparing.short_description = "Marquer comme en préparation"
    
    def mark_as_shipped(self, request, queryset):
        count = queryset.update(status='shipped')
        self.message_user(request, f'{count} commande(s) expédiée(s).')
    mark_as_shipped.short_description = "Marquer comme expédiées"
    
    def mark_as_delivered(self, request, queryset):
        from django.utils import timezone
        count = queryset.update(status='delivered', delivered_at=timezone.now())
        self.message_user(request, f'{count} commande(s) livrée(s).')
    mark_as_delivered.short_description = "Marquer comme livrées"


# ============================================================================
# 🔴 LIVE COMMERCE
# ============================================================================

@admin.register(LiveStream)
class LiveStreamAdmin(admin.ModelAdmin):
    list_display = ['title', 'store', 'status', 'viewers_count', 'total_sales', 'scheduled_at', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['title', 'store__name']
    readonly_fields = ['stream_key', 'viewers_count', 'peak_viewers', 'total_sales', 'total_orders']


@admin.register(LiveProduct)
class LiveProductAdmin(admin.ModelAdmin):
    list_display = ['live_stream', 'product', 'live_price', 'purchases_count', 'created_at']
    list_filter = ['created_at']
    search_fields = ['product__name', 'live_stream__title']


@admin.register(LiveComment)
class LiveCommentAdmin(admin.ModelAdmin):
    list_display = ['live_stream', 'user', 'is_question', 'is_pinned', 'created_at']
    list_filter = ['is_question', 'is_pinned', 'created_at']
    search_fields = ['content', 'user__username']


@admin.register(LivePurchase)
class LivePurchaseAdmin(admin.ModelAdmin):
    list_display = ['live_stream', 'product', 'customer', 'quantity', 'total', 'created_at']
    list_filter = ['created_at']
    search_fields = ['product__name', 'customer__username']


# ============================================================================
# 📄 PROFIL ÉTUDIANT
# ============================================================================

@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'university', 'field_of_study', 'is_verified', 'profile_views', 'created_at']
    list_filter = ['is_verified', 'is_public', 'created_at']
    search_fields = ['user__username', 'university', 'field_of_study']


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ['student', 'name', 'level', 'category', 'created_at']
    list_filter = ['level', 'category', 'created_at']
    search_fields = ['name', 'student__user__username']


@admin.register(Portfolio)
class PortfolioAdmin(admin.ModelAdmin):
    list_display = ['student', 'title', 'created_at']
    list_filter = ['created_at']
    search_fields = ['title', 'student__user__username']


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['student', 'title', 'course', 'grade', 'created_at']
    list_filter = ['created_at']
    search_fields = ['title', 'course', 'student__user__username']


@admin.register(Recommendation)
class RecommendationAdmin(admin.ModelAdmin):
    list_display = ['student', 'recommender', 'rating', 'is_verified', 'created_at']
    list_filter = ['rating', 'is_verified', 'created_at']
    search_fields = ['student__user__username', 'recommender__username']


# ============================================================================
# 💼 CAMPUS JOBS
# ============================================================================

@admin.register(JobCategory)
class JobCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'created_at']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ['title', 'posted_by', 'category', 'status', 'payment_type', 'amount', 'applications_count', 'created_at']
    list_filter = ['status', 'payment_type', 'is_remote', 'created_at']
    search_fields = ['title', 'description', 'posted_by__username']


@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    list_display = ['job', 'applicant', 'status', 'proposed_price', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['job__title', 'applicant__username']


# ============================================================================
# 🎓 CLASSROOM
# ============================================================================

@admin.register(Classroom)
class ClassroomAdmin(admin.ModelAdmin):
    list_display = ['name', 'course_code', 'university', 'created_by', 'is_public', 'members_count', 'created_at']
    list_filter = ['is_public', 'created_at']
    search_fields = ['name', 'course_code', 'university']


@admin.register(ClassPost)
class ClassPostAdmin(admin.ModelAdmin):
    list_display = ['classroom', 'author', 'post_type', 'is_pinned', 'likes_count', 'created_at']
    list_filter = ['post_type', 'is_pinned', 'created_at']
    search_fields = ['title', 'content', 'author__username']


@admin.register(ClassNote)
class ClassNoteAdmin(admin.ModelAdmin):
    list_display = ['classroom', 'author', 'title', 'topic', 'is_shared', 'updated_at']
    list_filter = ['is_shared', 'created_at']
    search_fields = ['title', 'topic', 'author__username']


@admin.register(Tutorial)
class TutorialAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'tutorial_type', 'views_count', 'created_at']
    list_filter = ['tutorial_type', 'created_at']
    search_fields = ['title', 'author__username']


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ['product', 'image_preview', 'order', 'created_at']
    list_filter = ['created_at']
    search_fields = ['product__name']
    list_editable = ['order']
    readonly_fields = ['image_preview', 'created_at', 'updated_at']
    list_per_page = 25
    
    def image_preview(self, obj):
        from django.utils.html import format_html
        if obj.image:
            return format_html('<img src="{}" style="max-width: 100px; max-height: 100px;" />'.format(obj.image.url))
        return "Aucune image"
    image_preview.short_description = 'Aperçu'
    
    fieldsets = (
        (None, {
            'fields': ('product', 'image', 'image_preview', 'order')
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('product')


# ============================================================================
# 🤖 ASSISTANT IA
# ============================================================================

@admin.register(AIRequest)
class AIRequestAdmin(admin.ModelAdmin):
    list_display = ['user', 'request_type', 'status', 'tokens_used', 'cost', 'created_at']
    list_filter = ['request_type', 'status', 'created_at']
    search_fields = ['user__username', 'input_text']
    readonly_fields = ['created_at', 'completed_at']


# ============================================================================
# 🔒 ANTI-ARNaque
# ============================================================================

@admin.register(FraudReport)
class FraudReportAdmin(admin.ModelAdmin):
    list_display = ['reported_by', 'report_type', 'status', 'reported_user', 'reported_store', 'created_at']
    list_filter = ['report_type', 'status', 'created_at']
    search_fields = ['reported_by__username', 'description']
    actions = ['mark_as_resolved', 'mark_as_dismissed']
    
    def mark_as_resolved(self, request, queryset):
        from django.utils import timezone
        count = queryset.update(status='resolved', resolved_at=timezone.now())
        self.message_user(request, f'{count} signalement(s) résolu(s).')
    mark_as_resolved.short_description = "Marquer comme résolus"
    
    def mark_as_dismissed(self, request, queryset):
        count = queryset.update(status='dismissed')
        self.message_user(request, f'{count} signalement(s) rejeté(s).')
    mark_as_dismissed.short_description = "Rejeter les signalements"


@admin.register(AccountVerification)
class AccountVerificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'verification_type', 'status', 'submitted_at', 'reviewed_at']
    list_filter = ['verification_type', 'status', 'submitted_at']
    search_fields = ['user__username', 'document_number']
    actions = ['approve_verifications', 'reject_verifications']
    
    def approve_verifications(self, request, queryset):
        from django.utils import timezone
        count = 0
        for verification in queryset.filter(status='pending'):
            verification.status = 'approved'
            verification.reviewed_at = timezone.now()
            verification.user.student_profile.is_verified = True
            verification.user.student_profile.save()
            verification.save()
            count += 1
        self.message_user(request, f'{count} vérification(s) approuvée(s).')
    approve_verifications.short_description = "Approuver les vérifications"
    
    def reject_verifications(self, request, queryset):
        from django.utils import timezone
        count = queryset.update(status='rejected', reviewed_at=timezone.now())
        self.message_user(request, f'{count} vérification(s) rejetée(s).')
    reject_verifications.short_description = "Rejeter les vérifications"

