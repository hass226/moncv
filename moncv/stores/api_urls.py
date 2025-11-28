from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken.views import obtain_auth_token

from .api_views import (
    StoreViewSet,
    ProductViewSet,
    OrderViewSet,
    StoreOrdersViewSet,
    CategoryViewSet,
    TagViewSet,
    CommentViewSet,
    LikeViewSet,
    FavoriteViewSet,
    FollowViewSet,
    NotificationViewSet,
    StudentProfileViewSet,
    ClassroomViewSet,
    JobViewSet,
    dashboard_stats,
    signup,
)

router = DefaultRouter()
router.register(r"stores", StoreViewSet, basename="api-stores")
router.register(r"products", ProductViewSet, basename="api-products")
router.register(r"orders", OrderViewSet, basename="api-orders")
router.register(r"store/orders", StoreOrdersViewSet, basename="api-store-orders")
router.register(r"categories", CategoryViewSet, basename="api-categories")
router.register(r"tags", TagViewSet, basename="api-tags")
router.register(r"comments", CommentViewSet, basename="api-comments")
router.register(r"likes", LikeViewSet, basename="api-likes")
router.register(r"favorites", FavoriteViewSet, basename="api-favorites")
router.register(r"follows", FollowViewSet, basename="api-follows")
router.register(r"notifications", NotificationViewSet, basename="api-notifications")
router.register(r"student-profiles", StudentProfileViewSet, basename="api-student-profiles")
router.register(r"classrooms", ClassroomViewSet, basename="api-classrooms")
router.register(r"jobs", JobViewSet, basename="api-jobs")

urlpatterns = [
    path("login/", obtain_auth_token, name="api-login"),
    path("signup/", signup, name="api-signup"),
    path("dashboard/", dashboard_stats, name="api-dashboard"),
    path("", include(router.urls)),
]
