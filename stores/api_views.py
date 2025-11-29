from rest_framework import viewsets, permissions, mixins, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token

from .models import (
    Product,
    Order,
    Store,
    Category,
    Tag,
    Comment,
    Like,
    Favorite,
    Follow,
    Notification,
    StudentProfile,
    Job,
    Classroom,
    Payment,
    Promotion,
    Subscription,
)
from .api_serializers import (
    ProductSerializer,
    OrderSerializer,
    StoreSerializer,
    CategorySerializer,
    TagSerializer,
    CommentSerializer,
    LikeSerializer,
    FavoriteSerializer,
    FollowSerializer,
    NotificationSerializer,
    StudentProfileSerializer,
    JobSerializer,
    ClassroomSerializer,
)
from .recommendations import get_similar_products
from django.utils import timezone
from django.db.models import Sum, Q


class IsStoreOwner(permissions.BasePermission):
    """Permission: l'utilisateur doit être propriétaire de la boutique liée."""

    def has_object_permission(self, request, view, obj):
        if isinstance(obj, Product):
            return hasattr(request.user, "store") and obj.store == getattr(request.user, "store", None)
        if isinstance(obj, Order):
            return hasattr(request.user, "store") and obj.store == getattr(request.user, "store", None)
        if isinstance(obj, Store):
            return hasattr(request.user, "store") and obj == getattr(request.user, "store", None)
        return False


class StoreViewSet(viewsets.ModelViewSet):
    queryset = Store.objects.all()
    serializer_class = StoreSerializer

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        if hasattr(self.request.user, "store"):
            raise permissions.PermissionDenied("Vous avez déjà une boutique.")
        serializer.save(owner=self.request.user)

    def perform_update(self, serializer):
        if not hasattr(self.request.user, "store") or serializer.instance.owner != self.request.user:
            raise permissions.PermissionDenied("Vous ne pouvez modifier que votre propre boutique.")
        serializer.save()


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.select_related("store", "category").all()
    serializer_class = ProductSerializer

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [permissions.AllowAny()]
        # création / modification / suppression réservées aux propriétaires de boutique
        return [permissions.IsAuthenticated(), IsStoreOwner()]

    def perform_create(self, serializer):
        store = getattr(self.request.user, "store", None)
        if not store:
            raise permissions.PermissionDenied("Vous devez avoir une boutique pour créer des produits.")
        serializer.save(store=store)

    def get_queryset(self):
        qs = super().get_queryset()
        # filtres simples
        search = self.request.query_params.get("search")
        category = self.request.query_params.get("category")
        store = self.request.query_params.get("store")
        min_price = self.request.query_params.get("min_price")
        max_price = self.request.query_params.get("max_price")

        if search:
            qs = qs.filter(name__icontains=search)
        if category:
            qs = qs.filter(category_id=category)
        if store:
            qs = qs.filter(store_id=store)
        if min_price:
            qs = qs.filter(price__gte=min_price)
        if max_price:
            qs = qs.filter(price__lte=max_price)

        return qs.order_by("-created_at")

    @action(detail=True, methods=["get"], permission_classes=[permissions.AllowAny])
    def recommendations(self, request, pk=None):
        """Retourne des produits recommandés pour un produit donné."""
        product = self.get_object()
        limit_param = request.query_params.get("limit")
        try:
            limit = int(limit_param) if limit_param is not None else 5
        except ValueError:
            limit = 5

        similar_qs = get_similar_products(product, limit=limit)
        serializer = self.get_serializer(similar_qs, many=True)
        return Response(serializer.data)


class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer

    def get_queryset(self):
        user = self.request.user
        qs = Order.objects.select_related("product", "store", "customer").all()

        if not user.is_authenticated:
            return qs.none()

        if hasattr(user, "store"):
            return qs.filter(store=user.store)

        return qs.filter(customer=user)

    def get_permissions(self):
        if self.action == "create":
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    @action(detail=True, methods=["patch"], permission_classes=[permissions.IsAuthenticated, IsStoreOwner])
    def update_status(self, request, pk=None):
        order = self.get_object()
        new_status = request.data.get("status")
        if not new_status:
            return Response({"detail": "Champ 'status' requis."}, status=400)
        order.status = new_status
        order.save(update_fields=["status", "updated_at"])
        return Response(OrderSerializer(order).data)


class StoreOrdersViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated, IsStoreOwner]

    def get_queryset(self):
        user = self.request.user
        if not hasattr(user, "store"):
            return Order.objects.none()
        return Order.objects.filter(store=user.store).select_related("product", "customer")


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [permissions.AllowAny]


class CommentViewSet(viewsets.ModelViewSet):
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        product_id = self.request.query_params.get("product")
        qs = Comment.objects.select_related("user", "product").all()
        if product_id:
            qs = qs.filter(product_id=product_id)
        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class LikeViewSet(viewsets.ModelViewSet):
    serializer_class = LikeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Like.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class FavoriteViewSet(viewsets.ModelViewSet):
    serializer_class = FavoriteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Favorite.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class FollowViewSet(viewsets.ModelViewSet):
    serializer_class = FollowSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Follow.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by("-created_at")


class StudentProfileViewSet(viewsets.ModelViewSet):
    serializer_class = StudentProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return StudentProfile.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        if hasattr(self.request.user, "student_profile"):
            raise permissions.PermissionDenied("Profil étudiant déjà existant.")
        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        if serializer.instance.user != self.request.user:
            raise permissions.PermissionDenied("Vous ne pouvez modifier que votre propre profil.")
        serializer.save()


class ClassroomViewSet(viewsets.ModelViewSet):
    serializer_class = ClassroomSerializer

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        qs = Classroom.objects.select_related("created_by").all()
        public_only = self.request.query_params.get("public")
        if public_only == "true":
            qs = qs.filter(is_public=True)
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class JobViewSet(viewsets.ModelViewSet):
    serializer_class = JobSerializer

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        qs = Job.objects.select_related("category", "posted_by", "student_profile").all()
        status_param = self.request.query_params.get("status")
        if status_param:
            qs = qs.filter(status=status_param)
        return qs

    def perform_create(self, serializer):
        student_profile = getattr(self.request.user, "student_profile", None)
        serializer.save(posted_by=self.request.user, student_profile=student_profile)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def dashboard_stats(request):
    user = request.user
    if not hasattr(user, "store"):
        return Response({"detail": "Aucune boutique associée à cet utilisateur."}, status=status.HTTP_400_BAD_REQUEST)

    store = user.store
    products = store.products.all()

    total_products = products.count()
    stats = products.aggregate(
        total_views=Sum("views_count"),
        total_likes=Sum("likes_count"),
    )
    total_views = stats["total_views"] or 0
    total_likes = stats["total_likes"] or 0

    all_reviews = []
    for product in products:
        all_reviews.extend(list(product.reviews.all()))
    total_reviews = len(all_reviews)
    if total_reviews:
        average_rating = round(sum(r.rating for r in all_reviews) / total_reviews, 1)
    else:
        average_rating = 0

    orders = Order.objects.filter(store=store)
    total_orders = orders.count()
    pending_orders = orders.filter(status="pending").count()
    completed_orders = orders.filter(status="delivered").count()

    completed_payments = Payment.objects.filter(
        order__store=store,
        status="completed",
    )
    total_revenue = completed_payments.aggregate(Sum("amount"))["amount__sum"] or 0

    active_promotions = Promotion.objects.filter(
        (Q(store=store) | Q(product__store=store)),
        status="active",
        expires_at__gt=timezone.now(),
    ).count()

    active_subscription = store.subscriptions.filter(
        is_active=True,
        expires_at__gt=timezone.now(),
    ).order_by("-expires_at").first()

    return Response(
        {
            "store": {
                "id": store.id,
                "name": store.name,
                "is_verified": store.is_verified,
                "is_featured": store.is_featured,
            },
            "total_products": total_products,
            "total_views": total_views,
            "total_likes": total_likes,
            "total_reviews": total_reviews,
            "average_rating": average_rating,
            "total_orders": total_orders,
            "pending_orders": pending_orders,
            "completed_orders": completed_orders,
            "total_revenue": float(total_revenue),
            "active_promotions_count": active_promotions,
            "has_active_subscription": bool(active_subscription),
        }
    )


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def signup(request):
  """Inscription simple via API.

  Attend au minimum : username, password.
  Optionnel : email.
  """
  username = (request.data.get("username") or "").strip()
  password = request.data.get("password") or ""
  email = (request.data.get("email") or "").strip()

  if not username or not password:
      return Response({"detail": "username et password sont obligatoires."}, status=status.HTTP_400_BAD_REQUEST)

  if User.objects.filter(username=username).exists():
      return Response({"detail": "Ce nom d'utilisateur est déjà pris."}, status=status.HTTP_400_BAD_REQUEST)

  user = User.objects.create_user(username=username, email=email or None, password=password)
  token, _ = Token.objects.get_or_create(user=user)

  return Response(
      {
          "id": user.id,
          "username": user.username,
          "token": token.key,
      },
      status=status.HTTP_201_CREATED,
  )
