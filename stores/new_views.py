"""
Nouvelles vues pour les fonctionnalités avancées de MYMEDAGA
Live Commerce, Profil Étudiant, Campus Jobs, Classroom, Assistant IA
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, JsonResponse, HttpResponseForbidden
from django.urls import reverse
from django.contrib import messages
from django.views.decorators.http import require_POST, require_http_methods
from django.core.paginator import Paginator
from django.utils import timezone
from django.db.models import Q, Count
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings
import json
import uuid

from .models import (
    # Live Commerce
    LiveStream, LiveProduct, LiveComment, LivePurchase,
    # Profil Étudiant
    StudentProfile, Skill, Portfolio, Project, Recommendation,
    # Campus Jobs
    Job, JobApplication, JobCategory,
    # Classroom
    Classroom, ClassPost, ClassNote, Tutorial,
    # Assistant IA
    AIRequest,
    # Anti-arnaque
    FraudReport, AccountVerification,
    # Existants
    Store, Product, Order, Notification
)
from .algorithms import (
    get_personalized_recommendations, get_geo_products,
    detect_fraud_risk, get_recommended_stores, get_recommended_jobs,
    get_trending_products, calculate_store_trust_score
)
from .ai_assistant import process_ai_request


# ============================================================================
# 🔴 LIVE COMMERCE
# ============================================================================

@login_required
def create_live_stream(request):
    """Créer un nouveau live stream"""
    if request.method == 'POST':
        store = get_object_or_404(Store, owner=request.user)
        
        title = request.POST.get('title')
        description = request.POST.get('description', '')
        scheduled_at = request.POST.get('scheduled_at')
        
        live_stream = LiveStream.objects.create(
            store=store,
            title=title,
            description=description,
            stream_key=str(uuid.uuid4()),
            status='scheduled'
        )
        
        if scheduled_at:
            from django.utils.dateparse import parse_datetime
            live_stream.scheduled_at = parse_datetime(scheduled_at)
            live_stream.save()
        
        messages.success(request, 'Live stream créé avec succès!')
        return redirect('live_stream_detail', live_id=live_stream.id)
    
    return render(request, 'stores/live/create_live.html')


@login_required
def live_stream_detail(request, live_id):
    """Détails d'un live stream"""
    live_stream = get_object_or_404(LiveStream, id=live_id)
    
    live_products = live_stream.live_products.all().select_related('product')
    comments = live_stream.comments.all().select_related('user')[:50]
    
    context = {
        'live_stream': live_stream,
        'live_products': live_products,
        'comments': comments,
        'is_owner': live_stream.store.owner == request.user,
    }
    
    return render(request, 'stores/live/live_detail.html', context)


def live_streams_list(request):
    """Feed des Reels vidéo (LiveStream avec vidéo)"""
    live_streams = LiveStream.objects.filter(
        video_file__isnull=False
    ).select_related('store', 'store__owner').order_by('-created_at')

    paginator = Paginator(live_streams, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'stores/live/live_list.html', {
        'live_streams': page_obj
    })


@login_required
@require_POST
def start_live_stream(request, live_id):
    """Démarrer un live stream"""
    live_stream = get_object_or_404(LiveStream, id=live_id, store__owner=request.user)
    
    live_stream.status = 'live'
    live_stream.started_at = timezone.now()
    live_stream.save()
    
    return JsonResponse({'success': True, 'status': 'live'})


@login_required
@require_POST
def end_live_stream(request, live_id):
    """Terminer un live stream"""
    live_stream = get_object_or_404(LiveStream, id=live_id, store__owner=request.user)
    
    live_stream.status = 'ended'
    live_stream.ended_at = timezone.now()
    live_stream.save()
    
    return JsonResponse({'success': True, 'status': 'ended'})


@login_required
@require_POST
def add_product_to_live(request, live_id):
    """Ajouter un produit à un live"""
    live_stream = get_object_or_404(LiveStream, id=live_id, store__owner=request.user)
    product_id = request.POST.get('product_id')
    product = get_object_or_404(Product, id=product_id, store=live_stream.store)
    
    live_price = request.POST.get('live_price')
    
    live_product, created = LiveProduct.objects.get_or_create(
        live_stream=live_stream,
        product=product,
        defaults={
            'live_price': live_price or product.price,
            'order': live_stream.live_products.count()
        }
    )
    
    if not created:
        live_product.live_price = live_price or product.price
        live_product.save()
    
    return JsonResponse({'success': True})


@login_required
@require_POST
def purchase_from_live(request, live_id):
    """Acheter un produit pendant un live"""
    live_stream = get_object_or_404(LiveStream, id=live_id, status='live')
    product_id = request.POST.get('product_id')
    live_product = get_object_or_404(LiveProduct, id=product_id, live_stream=live_stream)
    
    quantity = int(request.POST.get('quantity', 1))
    price = live_product.live_price or live_product.product.price
    total = price * quantity
    
    # Créer la commande
    order = Order.objects.create(
        product=live_product.product,
        customer=request.user,
        store=live_stream.store,
        quantity=quantity,
        unit_price=price,
        total_price=total,
        status='pending'
    )
    
    # Créer l'achat live
    purchase = LivePurchase.objects.create(
        live_stream=live_stream,
        product=live_product.product,
        customer=request.user,
        order=order,
        quantity=quantity,
        price=price,
        total=total
    )
    
    # Mettre à jour les stats
    live_stream.total_sales += total
    live_stream.total_orders += 1
    live_stream.save()
    
    live_product.purchases_count += quantity
    live_product.save()
    
    return JsonResponse({'success': True, 'order_id': order.id})


@login_required
@require_POST
def add_live_comment(request, live_id):
    """Ajouter un commentaire à un live (utilisé en AJAX)"""
    live_stream = get_object_or_404(LiveStream, id=live_id, status='live')
    content = request.POST.get('content', '').strip()

    if not content:
        return JsonResponse({'success': False, 'error': "Commentaire vide"})

    comment = LiveComment.objects.create(
        live_stream=live_stream,
        user=request.user,
        content=content,
    )

    return JsonResponse({
        'success': True,
        'comment': {
            'user': comment.user.username,
            'content': comment.content,
        }
    })


# ============================================================================
# 📄 PROFIL ÉTUDIANT
# ============================================================================

@login_required
def student_profile(request, user_id=None):
    """Voir ou éditer un profil étudiant"""
    if user_id:
        profile_user = get_object_or_404(User, id=user_id)
        profile, created = StudentProfile.objects.get_or_create(user=profile_user)
    else:
        profile, created = StudentProfile.objects.get_or_create(user=request.user)
        profile_user = request.user
    
    # Vérifier les permissions
    can_edit = (request.user == profile_user) or request.user.is_staff
    
    if request.method == 'POST' and can_edit:
        # Mettre à jour le profil
        profile.university = request.POST.get('university', '')
        profile.field_of_study = request.POST.get('field_of_study', '')
        profile.degree_level = request.POST.get('degree_level', '')
        profile.bio = request.POST.get('bio', '')
        profile.city = request.POST.get('city', '')
        profile.country = request.POST.get('country', '')
        profile.phone = request.POST.get('phone', '')
        profile.email_public = request.POST.get('email_public', '')
        profile.website = request.POST.get('website', '')
        profile.linkedin_url = request.POST.get('linkedin_url', '')
        profile.github_url = request.POST.get('github_url', '')
        profile.portfolio_url = request.POST.get('portfolio_url', '')
        
        if 'profile_picture' in request.FILES:
            profile.profile_picture = request.FILES['profile_picture']
        if 'cover_photo' in request.FILES:
            profile.cover_photo = request.FILES['cover_photo']
        if 'resume_file' in request.FILES:
            profile.resume_file = request.FILES['resume_file']
        
        profile.save()
        messages.success(request, 'Profil mis à jour!')
        return redirect('student_profile')
    
    skills = profile.skills.all()
    portfolio_items = profile.portfolio_items.all()
    projects = profile.projects.all()
    recommendations = profile.recommendations.filter(is_verified=True)
    
    # Incrémenter les vues
    if request.user != profile_user:
        profile.profile_views += 1
        profile.save()
    
    context = {
        'profile': profile,
        'profile_user': profile_user,
        'can_edit': can_edit,
        'skills': skills,
        'portfolio_items': portfolio_items,
        'projects': projects,
        'recommendations': recommendations,
    }
    
    return render(request, 'stores/student/profile.html', context)


@login_required
@require_POST
def add_skill(request):
    """Ajouter une compétence"""
    profile = get_object_or_404(StudentProfile, user=request.user)
    
    name = request.POST.get('name')
    level = request.POST.get('level', 'intermediate')
    category = request.POST.get('category', '')
    
    skill = Skill.objects.create(
        student=profile,
        name=name,
        level=level,
        category=category
    )
    
    return JsonResponse({'success': True, 'skill_id': skill.id})


@login_required
@require_POST
def add_portfolio_item(request):
    """Ajouter un item au portfolio"""
    profile = get_object_or_404(StudentProfile, user=request.user)
    
    title = request.POST.get('title')
    description = request.POST.get('description')
    url = request.POST.get('url', '')
    github_url = request.POST.get('github_url', '')
    technologies = request.POST.get('technologies', '')
    
    portfolio = Portfolio.objects.create(
        student=profile,
        title=title,
        description=description,
        url=url,
        github_url=github_url,
        technologies=technologies
    )
    
    if 'image' in request.FILES:
        portfolio.image = request.FILES['image']
        portfolio.save()
    
    return JsonResponse({'success': True, 'portfolio_id': portfolio.id})


# ============================================================================
# 💼 CAMPUS JOBS
# ============================================================================

def jobs_list(request):
    """Liste des jobs disponibles"""
    jobs = Job.objects.filter(status='open').select_related(
        'posted_by', 'category'
    ).order_by('-created_at')
    
    # Filtres
    category_id = request.GET.get('category')
    if category_id:
        jobs = jobs.filter(category_id=category_id)
    
    search = request.GET.get('search')
    if search:
        jobs = jobs.filter(
            Q(title__icontains=search) | Q(description__icontains=search)
        )
    
    # Recommandations personnalisées si connecté
    if request.user.is_authenticated:
        recommended_jobs = get_recommended_jobs(request.user, limit=5)
    else:
        recommended_jobs = []
    
    paginator = Paginator(jobs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    categories = JobCategory.objects.all()
    
    context = {
        'jobs': page_obj,
        'categories': categories,
        'recommended_jobs': recommended_jobs,
    }
    
    return render(request, 'stores/jobs/jobs_list.html', context)


@login_required
def create_job(request):
    """Créer une offre de job"""
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        category_id = request.POST.get('category')
        location = request.POST.get('location', '')
        is_remote = request.POST.get('is_remote') == 'on'
        payment_type = request.POST.get('payment_type', 'fixed')
        amount = request.POST.get('amount')
        currency = request.POST.get('currency', 'XOF')
        deadline = request.POST.get('deadline')
        
        try:
            profile = request.user.student_profile
        except:
            profile = None
        
        job = Job.objects.create(
            title=title,
            description=description,
            category_id=category_id if category_id else None,
            posted_by=request.user,
            student_profile=profile,
            location=location,
            is_remote=is_remote,
            payment_type=payment_type,
            amount=amount if amount else None,
            currency=currency,
            status='open'
        )
        
        if deadline:
            from django.utils.dateparse import parse_datetime
            job.deadline = parse_datetime(deadline)
            job.save()
        
        messages.success(request, 'Job créé avec succès!')
        return redirect('job_detail', job_id=job.id)
    
    categories = JobCategory.objects.all()
    return render(request, 'stores/jobs/create_job.html', {'categories': categories})


def job_detail(request, job_id):
    """Détails d'un job"""
    job = get_object_or_404(Job, id=job_id)
    
    # Vérifier si l'utilisateur a déjà postulé
    has_applied = False
    if request.user.is_authenticated:
        has_applied = JobApplication.objects.filter(
            job=job, applicant=request.user
        ).exists()

    # Si on vient d'appliquer via la redirection, forcer l'état 'appliqué'
    just_applied = request.GET.get('applied') == '1'
    if just_applied:
        has_applied = True
    
    applications = []
    selected_status = request.GET.get('status', '')
    if job.posted_by == request.user:
        applications_qs = job.applications.all().select_related('applicant')
        if selected_status in dict(JobApplication.STATUS_CHOICES):
            applications_qs = applications_qs.filter(status=selected_status)
        applications = applications_qs
    
    # Incrémenter les vues
    job.views_count += 1
    job.save()
    
    context = {
        'job': job,
        'has_applied': has_applied,
        'just_applied': just_applied,
        'applications': applications,
        'can_edit': job.posted_by == request.user,
        'selected_status': selected_status,
        'status_choices': JobApplication.STATUS_CHOICES,
    }
    
    return render(request, 'stores/jobs/job_detail.html', context)


@login_required
@require_POST
def apply_to_job(request, job_id):
    """Postuler à un job"""
    job = get_object_or_404(Job, id=job_id, status='open')
    
    # Vérifier si déjà postulé
    if JobApplication.objects.filter(job=job, applicant=request.user).exists():
        return JsonResponse({'success': False, 'error': 'Vous avez déjà postulé'})
    
    cover_letter = request.POST.get('cover_letter', '')
    proposed_price = request.POST.get('proposed_price')
    estimated_duration = request.POST.get('estimated_duration', '')
    
    try:
        profile = request.user.student_profile
    except Exception:
        profile = None
    
    application = JobApplication.objects.create(
        job=job,
        applicant=request.user,
        student_profile=profile,
        cover_letter=cover_letter,
        proposed_price=proposed_price if proposed_price else None,
        estimated_duration=estimated_duration
    )

    job.applications_count += 1
    job.save()

    # Si c'est une requête AJAX, renvoyer du JSON (pour usage API/JS)
    # Détecter requête AJAX sans utiliser request.is_ajax() (obsolète)
    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'application_id': application.id})

    # Sinon (formulaire HTML standard), afficher un message et rediriger vers la page du job
    messages.success(request, 'Votre candidature a été envoyée avec succès !')
    # Rediriger vers la page du job avec un flag pour indiquer qu'on vient de postuler
    job_url = reverse('job_detail', args=[job.id])
    return HttpResponseRedirect(f"{job_url}?applied=1")


@login_required
@require_POST
def update_job_application_status(request, application_id):
    """Permet au recruteur d'accepter ou refuser une candidature."""
    application = get_object_or_404(JobApplication, id=application_id)
    job = application.job

    # Seul le créateur du job peut modifier le statut de la candidature
    if job.posted_by != request.user:
        return HttpResponseForbidden("Vous n'avez pas l'autorisation de modifier cette candidature.")

    new_status = request.POST.get("status")
    if new_status not in dict(JobApplication.STATUS_CHOICES):
        return JsonResponse({"success": False, "error": "Statut invalide."}, status=400)

    # Mémoriser l'ancien statut pour éviter les notifications inutiles
    old_status = application.status
    application.status = new_status
    application.save()

    # Notifier le candidat si le statut a réellement changé
    if old_status != new_status:
        status_label = dict(JobApplication.STATUS_CHOICES).get(new_status, new_status)
        Notification.objects.create(
            user=application.applicant,
            notification_type='job',
            message=f"Votre candidature au job '{job.title}' est maintenant : {status_label}",
            link=f"/jobs/{job.id}/"
        )

        # Envoi d'un email simple au candidat (si une adresse email est disponible)
        if application.applicant.email:
            subject = f"Mise à jour de votre candidature - {job.title}"
            body = (
                f"Bonjour {application.applicant.username},\n\n"
                f"Votre candidature au job '{job.title}' est maintenant : {status_label}.\n"
                f"Vous pouvez consulter les détails du job ici : {settings.SITE_URL}/jobs/{job.id}/\n\n"
                f"Cordialement,\nL'équipe MYMEDAGA"
            )
            try:
                send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [application.applicant.email], fail_silently=True)
            except Exception:
                # On ignore les erreurs d'envoi pour ne pas casser le flux principal
                pass

    messages.success(request, "Statut de la candidature mis à jour.")

    # Rediriger vers la page du job
    return redirect("job_detail", job_id=job.id)


@login_required
@require_POST
def update_job_status(request, job_id):
    """Met à jour le statut global d'un job (open, in_progress, completed, cancelled)."""
    job = get_object_or_404(Job, id=job_id)

    # Seul le créateur du job peut modifier le statut du job
    if job.posted_by != request.user:
        return HttpResponseForbidden("Vous n'avez pas l'autorisation de modifier ce job.")

    new_status = request.POST.get("status")
    valid_status = {choice[0] for choice in Job.STATUS_CHOICES}
    if new_status not in valid_status:
        return JsonResponse({"success": False, "error": "Statut invalide."}, status=400)

    job.status = new_status
    job.save()

    messages.success(request, "Statut du job mis à jour.")

    # Pour un usage AJAX, on renvoie du JSON, sinon on redirige
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"success": True, "status": job.status})

    return redirect("job_detail", job_id=job.id)


@login_required
def my_jobs(request):
    """Liste des jobs postés par l'utilisateur connecté."""
    jobs = Job.objects.filter(posted_by=request.user).select_related('category').order_by('-created_at')

    # Filtre par statut via ?status=
    selected_status = request.GET.get('status', '')
    valid_status = {choice[0] for choice in Job.STATUS_CHOICES}
    if selected_status in valid_status:
        jobs = jobs.filter(status=selected_status)

    # Statistiques simples par statut (sur tous les jobs de l'utilisateur, pas seulement filtrés)
    all_jobs = Job.objects.filter(posted_by=request.user)
    stats = {
        'total': all_jobs.count(),
        'open': all_jobs.filter(status='open').count(),
        'in_progress': all_jobs.filter(status='in_progress').count(),
        'completed': all_jobs.filter(status='completed').count(),
        'cancelled': all_jobs.filter(status='cancelled').count(),
    }

    paginator = Paginator(jobs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'jobs': page_obj,
        'categories': JobCategory.objects.all(),
        'recommended_jobs': [],
        'my_jobs_view': True,
        'job_stats': stats,
        'selected_status': selected_status,
        'job_status_choices': Job.STATUS_CHOICES,
    }

    return render(request, 'stores/jobs/jobs_list.html', context)


# ============================================================================
# 🎓 CLASSROOM
# ============================================================================

@login_required
def classrooms_list(request):
    """Liste des classes"""
    if request.user.is_authenticated:
        my_classrooms = request.user.classrooms.all()
        public_classrooms = Classroom.objects.filter(
            is_public=True
        ).exclude(id__in=my_classrooms.values_list('id', flat=True))
    else:
        my_classrooms = []
        public_classrooms = Classroom.objects.filter(is_public=True)
    
    context = {
        'my_classrooms': my_classrooms,
        'public_classrooms': public_classrooms,
    }
    
    return render(request, 'stores/classroom/classrooms_list.html', context)


@login_required
def create_classroom(request):
    """Créer une classe"""
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        course_code = request.POST.get('course_code', '')
        university = request.POST.get('university', '')
        is_public = request.POST.get('is_public') == 'on'
        
        classroom = Classroom.objects.create(
            name=name,
            description=description,
            course_code=course_code,
            university=university,
            created_by=request.user,
            is_public=is_public,
            invite_code=str(uuid.uuid4())[:8].upper()
        )
        
        # Ajouter le créateur comme membre
        classroom.members.add(request.user)
        classroom.members_count = 1
        classroom.save()
        
        messages.success(request, 'Classe créée avec succès!')
        return redirect('classroom_detail', classroom_id=classroom.id)
    
    return render(request, 'stores/classroom/create_classroom.html')


def classroom_detail(request, classroom_id):
    """Détails d'une classe"""
    classroom = get_object_or_404(Classroom, id=classroom_id)
    
    # Vérifier l'accès
    is_member = request.user in classroom.members.all() if request.user.is_authenticated else False
    can_access = is_member or classroom.is_public or classroom.created_by == request.user
    
    if not can_access:
        messages.error(request, 'Vous n\'avez pas accès à cette classe.')
        return redirect('classrooms_list')
    
    posts = classroom.posts.all().select_related('author').order_by('-is_pinned', '-created_at')
    notes = classroom.notes.all().select_related('author').order_by('-updated_at')
    tutorials = classroom.tutorials.all().select_related('author').order_by('-created_at')
    
    context = {
        'classroom': classroom,
        'is_member': is_member,
        'posts': posts,
        'notes': notes,
        'tutorials': tutorials,
    }
    
    return render(request, 'stores/classroom/classroom_detail.html', context)


@login_required
@require_POST
def join_classroom(request, classroom_id):
    """Rejoindre une classe"""
    classroom = get_object_or_404(Classroom, id=classroom_id)
    
    invite_code = request.POST.get('invite_code', '')
    
    # Vérifier le code d'invitation ou si c'est public
    if not classroom.is_public and invite_code != classroom.invite_code:
        return JsonResponse({'success': False, 'error': 'Code d\'invitation invalide'})
    
    if request.user not in classroom.members.all():
        classroom.members.add(request.user)
        classroom.members_count += 1
        classroom.save()
    
    return JsonResponse({'success': True})


@login_required
@require_http_methods(["POST"])
def add_class_post(request, classroom_id):
    """Créer un post/discussion dans une classe avec gestion des fichiers."""
    classroom = get_object_or_404(Classroom, id=classroom_id)

    # Vérifier les permissions
    if request.user not in classroom.members.all():
        return JsonResponse({'success': False, 'error': "Accès refusé"}, status=403)

    # Récupérer les données du formulaire
    title = request.POST.get('title', '').strip()
    content = request.POST.get('content', '').strip()
    post_type = request.POST.get('post_type', 'discussion')
    uploaded_file = request.FILES.get('file')

    # Validation
    if not content and not uploaded_file:
        return JsonResponse({'success': False, 'error': "Le contenu ou un fichier est requis"}, status=400)

    # Vérifier la taille du fichier (max 10MB)
    if uploaded_file and uploaded_file.size > 10 * 1024 * 1024:  # 10MB
        return JsonResponse({'success': False, 'error': "Le fichier est trop volumineux (max 10MB)"}, status=400)

    # Créer le post
    post = ClassPost.objects.create(
        classroom=classroom,
        author=request.user,
        title=title or None,
        content=content,
        post_type=post_type,
        file=uploaded_file
    )

    # Mettre à jour le compteur de posts
    classroom.posts_count = classroom.posts.count()
    classroom.save()

    # Réponse
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'post_id': post.id,
            'html': render_to_string('stores/classroom/_post.html', {
                'post': post,
                'is_member': True
            })
        })
    return redirect('classroom_detail', classroom_id=classroom.id)


@login_required
@require_POST
def add_class_note(request, classroom_id):
    """Créer une note collaborative dans une classe."""
    classroom = get_object_or_404(Classroom, id=classroom_id)

    if request.user not in classroom.members.all():
        return JsonResponse({'success': False, 'error': "Accès refusé"}, status=403)

    title = request.POST.get('title', '').strip()
    topic = request.POST.get('topic', '').strip()
    content = request.POST.get('content', '').strip()

    if not title or not content:
        return JsonResponse({'success': False, 'error': "Titre et contenu requis"}, status=400)

    ClassNote.objects.create(
        classroom=classroom,
        author=request.user,
        title=title,
        topic=topic or None,
        content=content,
    )

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    return redirect('classroom_detail', classroom_id=classroom.id)


@login_required
@require_POST
def add_tutorial(request, classroom_id):
    """Ajouter un tutoriel/ressource (cours) dans une classe."""
    classroom = get_object_or_404(Classroom, id=classroom_id)

    if request.user not in classroom.members.all():
        return JsonResponse({'success': False, 'error': "Accès refusé"}, status=403)

    title = request.POST.get('title', '').strip()
    description = request.POST.get('description', '').strip()
    video_url = request.POST.get('video_url', '').strip()
    external_url = request.POST.get('external_url', '').strip()
    uploaded_file = request.FILES.get('file')

    if not title:
        return JsonResponse({'success': False, 'error': "Titre requis"}, status=400)

    Tutorial.objects.create(
        classroom=classroom,
        author=request.user,
        title=title,
        description=description,
        video_url=video_url or None,
        external_url=external_url or None,
        file=uploaded_file,
    )

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    return redirect('classroom_detail', classroom_id=classroom.id)


# ============================================================================
# 🤖 ASSISTANT IA
# ============================================================================

@login_required
def ai_assistant(request):
    """Interface de l'assistant IA"""
    if request.method == 'POST':
        request_type = request.POST.get('request_type')
        input_text = request.POST.get('input_text', '')
        product_id = request.POST.get('product_id')
        store_id = request.POST.get('store_id')
        target_language = request.POST.get('target_language', '')
        
        product = None
        store = None
        
        if product_id:
            product = get_object_or_404(Product, id=product_id)
            store = product.store
        
        if store_id:
            store = get_object_or_404(Store, id=store_id, owner=request.user)
        
        ai_request = AIRequest.objects.create(
            user=request.user,
            request_type=request_type,
            product=product,
            store=store,
            input_text=input_text,
            target_language=target_language,
            input_language='fr'
        )

        try:
            # Traiter la requête IA (peut dépendre d'une clé API externe)
            process_ai_request(ai_request)
            success = ai_request.status == 'completed'
            return JsonResponse({
                'success': success,
                'result': {
                    'output_text': ai_request.output_text or '',
                    'metadata': ai_request.metadata or {},
                    'status': ai_request.status,
                },
                'error': None if success else (ai_request.error_message or "La requête IA n'a pas pu être terminée. Vérifiez la configuration côté serveur."),
            })
        except Exception as e:
            ai_request.status = 'failed'
            ai_request.metadata = {'error': str(e)}
            ai_request.save()
            return JsonResponse({
                'success': False,
                'error': 'Erreur côté serveur IA. Vérifiez la configuration (clé API, connexion internet, etc.).',
            }, status=500)
    
    # Historique des requêtes
    recent_requests = AIRequest.objects.filter(
        user=request.user
    ).order_by('-created_at')[:10]
    
    return render(request, 'stores/ai/assistant.html', {
        'recent_requests': recent_requests
    })


# ============================================================================
# 🔒 ANTI-ARNaque
# ============================================================================

@login_required
def report_fraud(request):
    """Signaler une arnaque"""
    if request.method == 'POST':
        report_type = request.POST.get('report_type')
        description = request.POST.get('description')
        reported_user_id = request.POST.get('reported_user_id')
        reported_store_id = request.POST.get('reported_store_id')
        reported_product_id = request.POST.get('reported_product_id')
        
        fraud_report = FraudReport.objects.create(
            reported_by=request.user,
            report_type=report_type,
            description=description,
            reported_user_id=reported_user_id if reported_user_id else None,
            reported_store_id=reported_store_id if reported_store_id else None,
            reported_product_id=reported_product_id if reported_product_id else None,
        )
        
        if 'evidence' in request.FILES:
            fraud_report.evidence = request.FILES['evidence']
            fraud_report.save()
        
        messages.success(request, 'Signalement envoyé. Merci!')
        return redirect('home')
    
    return render(request, 'stores/fraud/report.html')


@login_required
@require_POST
def like_class_post(request, post_id):
    """Like/Unlike un post de classe."""
    post = get_object_or_404(ClassPost, id=post_id)
    
    # Vérifier que l'utilisateur est membre de la classe
    if request.user not in post.classroom.members.all():
        return JsonResponse({'success': False, 'error': 'Accès refusé'}, status=403)
    
    # Vérifier si l'utilisateur a déjà liké ce post
    liked = False
    if request.user in post.likes.all():
        post.likes.remove(request.user)
        post.likes_count -= 1
    else:
        post.likes.add(request.user)
        post.likes_count += 1
        liked = True
    
    post.save()
    
    return JsonResponse({
        'success': True,
        'likes_count': post.likes_count,
        'liked': liked
    })


@login_required
def verify_account(request):
    """Demander la vérification du compte"""
    if request.method == 'POST':
        verification_type = request.POST.get('verification_type')
        document_number = request.POST.get('document_number', '')
        
        verification = AccountVerification.objects.create(
            user=request.user,
            verification_type=verification_type,
            document_number=document_number
        )
        
        if 'document_file' in request.FILES:
            verification.document_file = request.FILES['document_file']
            verification.save()
        
        messages.success(request, 'Demande de vérification envoyée!')
        return redirect('student_profile')
    
    return render(request, 'stores/fraud/verify.html')

