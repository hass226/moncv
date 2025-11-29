from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from . import payment_views
from . import new_views


urlpatterns = [
    # Pages publiques
    path('', views.home, name='home'),
    path('store/<int:store_id>/', views.store_detail, name='store_detail'),
    
    # Authentification
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='stores/login.html'), name='login'),
    path('logout/', views.custom_logout, name='logout'),
    
    # Dashboard et gestion boutique
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/payments-settings/', views.store_payment_settings, name='store_payment_settings'),
    path('create-store/', views.create_store, name='create_store'),
    path('edit-store/', views.edit_store, name='edit_store'),
    path('product/delete-image/<int:image_id>/', views.delete_product_image, name='delete_product_image'),
    
    # Gestion produits
    path('add-product/', views.add_product, name='add_product'),
    path('edit-product/<int:product_id>/', views.edit_product, name='edit_product'),
    path('delete-product/<int:product_id>/', views.delete_product, name='delete_product'),
    path('add-category/', views.add_category, name='add_category'),
    
    # Abonnements et promotions
    path('subscribe/', views.subscribe, name='subscribe'),
    path('promote/', views.promote, name='promote'),
    path('my-subscriptions/', views.my_subscriptions, name='my_subscriptions'),
    path('my-promotions/', views.my_promotions, name='my_promotions'),
    
    # Profil utilisateur
    path('profile/', views.user_profile, name='user_profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('profile/general/edit/', views.general_profile_edit, name='general_profile_edit'),
    
    # Interactions sociales (TikTok-like)
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),
    path('product/<int:product_id>/like/', views.toggle_like, name='toggle_like'),
    path('product/<int:product_id>/comment/', views.add_comment, name='add_comment'),
    path('product/<int:product_id>/share/', views.share_product, name='share_product'),
    path('product/<int:product_id>/favorite/', views.toggle_favorite, name='toggle_favorite'),
    path('product/<int:product_id>/review/', views.add_review, name='add_review'),
    path('store/<int:store_id>/follow/', views.toggle_follow, name='toggle_follow'),
    
    # Recherche et navigation
    path('search/', views.search, name='search'),
    path('favorites/', views.my_favorites, name='my_favorites'),
    path('following/', views.my_following, name='my_following'),
    path('notifications/', views.notifications, name='notifications'),
    path('top-stores/', views.top_stores, name='top_stores'),

    # API mobile
    path('api/products/', views.api_products, name='api_products'),
    path('api/subscriptions/', views.api_subscriptions, name='api_subscriptions'),
    
    # API pour WhatsApp avec localisation
    path('product/<int:product_id>/whatsapp-order/', views.get_whatsapp_link_with_location, name='whatsapp_order'),
    
    # Checkout et commandes
    path('product/<int:product_id>/checkout/', views.checkout, name='checkout'),
    
    # Langue et devise
    path('set-language/', views.set_language, name='set_language'),
    path('set-currency/', views.set_currency, name='set_currency'),
    
    # Paiements
    path('order/<int:order_id>/payment/', payment_views.initiate_payment, name='initiate_payment'),
    path('order/<int:order_id>/paydunya/', payment_views.paydunya_pay_order, name='paydunya_pay_order'),
    path('subscription/<int:subscription_id>/payment/', payment_views.initiate_subscription_payment, name='initiate_subscription_payment'),
    path('promotion/<int:promotion_id>/payment/', payment_views.initiate_promotion_payment, name='initiate_promotion_payment'),
    path('payment/<int:payment_id>/status/', payment_views.payment_status, name='payment_status'),
    path('payments/', payment_views.my_payments, name='my_payments'),
    path('payment/paypal/return/', payment_views.paypal_return, name='paypal_return'),
    path('payment/webhook/<str:provider>/', payment_views.payment_webhook, name='payment_webhook'),
    path('stripe/create-account/', payment_views.create_stripe_account, name='create_stripe_account'),
    path('stripe/create-payment-intent/<int:order_id>/', payment_views.create_stripe_payment_intent, name='create_stripe_payment_intent'),
    path('stripe/create-subscription-intent/<int:subscription_id>/', payment_views.create_stripe_subscription_intent, name='create_stripe_subscription_intent'),
    path('stripe/create-promotion-intent/<int:promotion_id>/', payment_views.create_stripe_promotion_intent, name='create_stripe_promotion_intent'),
    path('stripe/webhook/', payment_views.stripe_webhook, name='stripe_webhook'),
    
    # Gestion des commandes (vendeur)
    path('store/orders/', views.store_orders, name='store_orders'),
    path('order/<int:order_id>/update-status/', views.update_order_status, name='update_order_status'),
    
    # ============================================================================
    # 🔴 LIVE COMMERCE
    # ============================================================================
    path('live/', new_views.live_streams_list, name='live_streams_list'),
    path('live/create/', new_views.create_live_stream, name='create_live_stream'),
    path('live/<int:live_id>/', new_views.live_stream_detail, name='live_stream_detail'),
    path('live/<int:live_id>/start/', new_views.start_live_stream, name='start_live_stream'),
    path('live/<int:live_id>/end/', new_views.end_live_stream, name='end_live_stream'),
    path('live/<int:live_id>/add-product/', new_views.add_product_to_live, name='add_product_to_live'),
    path('live/<int:live_id>/purchase/', new_views.purchase_from_live, name='purchase_from_live'),
    path('live/<int:live_id>/comment/', new_views.add_live_comment, name='add_live_comment'),
    
    # ============================================================================
    # 📄 PROFIL ÉTUDIANT
    # ============================================================================
    path('profile/', new_views.student_profile, name='student_profile'),
    path('profile/<int:user_id>/', new_views.student_profile, name='student_profile_view'),
    path('profile/skill/add/', new_views.add_skill, name='add_skill'),
    path('profile/portfolio/add/', new_views.add_portfolio_item, name='add_portfolio_item'),
    
    # ============================================================================
    # 💼 CAMPUS JOBS
    # ============================================================================
    path('jobs/', new_views.jobs_list, name='jobs_list'),
    path('jobs/my/', new_views.my_jobs, name='my_jobs'),
    path('jobs/create/', new_views.create_job, name='create_job'),
    path('jobs/<int:job_id>/', new_views.job_detail, name='job_detail'),
    path('jobs/<int:job_id>/apply/', new_views.apply_to_job, name='apply_to_job'),
    path('jobs/<int:job_id>/status/', new_views.update_job_status, name='update_job_status'),
    path('jobs/application/<int:application_id>/status/', new_views.update_job_application_status, name='update_job_application_status'),
    
    # ============================================================================
    # 🎓 CLASSROOM
    # ============================================================================
    path('classrooms/', new_views.classrooms_list, name='classrooms_list'),
    path('classrooms/create/', new_views.create_classroom, name='create_classroom'),
    path('classrooms/<int:classroom_id>/', new_views.classroom_detail, name='classroom_detail'),
    path('classrooms/<int:classroom_id>/join/', new_views.join_classroom, name='join_classroom'),
    path('classrooms/<int:classroom_id>/posts/add/', new_views.add_class_post, name='add_class_post'),
    path('classrooms/<int:classroom_id>/notes/add/', new_views.add_class_note, name='add_class_note'),
    path('classrooms/<int:classroom_id>/tutorials/add/', new_views.add_tutorial, name='add_tutorial'),
    path('classrooms/posts/<int:post_id>/like/', new_views.like_class_post, name='like_class_post'),
    
    # ============================================================================
    # 🤖 ASSISTANT IA
    # ============================================================================
    path('ai-assistant/', new_views.ai_assistant, name='ai_assistant'),
    
    # ============================================================================
    # 🔒 ANTI-ARNaque
    # ============================================================================
    path('report-fraud/', new_views.report_fraud, name='report_fraud'),
    path('verify-account/', new_views.verify_account, name='verify_account'),
    
    # ============================================================================
    # 📞 Contact
    # ============================================================================
    path('contact/', views.contact, name='contact'),
]