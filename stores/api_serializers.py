from rest_framework import serializers

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
)


class StoreSerializer(serializers.ModelSerializer):
    owner_username = serializers.CharField(source="owner.username", read_only=True)

    class Meta:
        model = Store
        fields = [
            "id",
            "owner",
            "owner_username",
            "name",
            "description",
            "whatsapp_number",
            "logo",
            "is_verified",
            "is_featured",
            "address",
            "city",
            "latitude",
            "longitude",
            "created_at",
        ]
        read_only_fields = [
            "owner",
            "is_verified",
            "is_featured",
            "created_at",
        ]


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug", "icon", "created_at"]


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "name", "slug", "created_at"]


class ProductSerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(source="store.name", read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "store",
            "store_name",
            "name",
            "price",
            "currency",
            "description",
            "image",
            "category",
            "is_featured",
            "featured_until",
            "views_count",
            "likes_count",
            "shares_count",
            "created_at",
        ]
        read_only_fields = [
            "store",
            "views_count",
            "likes_count",
            "shares_count",
            "created_at",
        ]


class OrderSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    store_name = serializers.CharField(source="store.name", read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "product",
            "product_name",
            "customer",
            "store",
            "store_name",
            "latitude",
            "longitude",
            "address",
            "city",
            "postal_code",
            "country",
            "quantity",
            "unit_price",
            "total_price",
            "delivery_fee",
            "status",
            "delivery_method",
            "customer_name",
            "customer_phone",
            "customer_email",
            "payment_status",
            "payment_method",
            "tracking_number",
            "estimated_delivery",
            "delivered_at",
            "notes",
            "internal_notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "store",
            "status",
            "payment_status",
            "tracking_number",
            "estimated_delivery",
            "delivered_at",
            "internal_notes",
            "created_at",
            "updated_at",
        ]

    def create(self, validated_data):
        request = self.context.get("request")
        product = validated_data["product"]
        validated_data.setdefault("store", product.store)

        if "unit_price" not in validated_data or not validated_data["unit_price"]:
            validated_data["unit_price"] = product.price

        quantity = validated_data.get("quantity") or 1
        validated_data["total_price"] = validated_data["unit_price"] * quantity

        if request and request.user.is_authenticated and not validated_data.get("customer"):
            validated_data["customer"] = request.user

        return super().create(validated_data)


class CommentSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = Comment
        fields = [
            "id",
            "user",
            "user_username",
            "product",
            "content",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["user", "created_at", "updated_at"]


class LikeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Like
        fields = ["id", "user", "product", "created_at"]
        read_only_fields = ["user", "created_at"]


class FavoriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Favorite
        fields = ["id", "user", "product", "created_at"]
        read_only_fields = ["user", "created_at"]


class FollowSerializer(serializers.ModelSerializer):
    class Meta:
        model = Follow
        fields = ["id", "user", "store", "created_at"]
        read_only_fields = ["user", "created_at"]


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "id",
            "notification_type",
            "message",
            "link",
            "is_read",
            "created_at",
        ]
        read_only_fields = ["created_at"]


class StudentProfileSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = StudentProfile
        fields = [
            "id",
            "user",
            "user_username",
            "university",
            "field_of_study",
            "degree_level",
            "graduation_year",
            "gpa",
            "bio",
            "resume_file",
            "profile_picture",
            "cover_photo",
            "phone",
            "email_public",
            "website",
            "linkedin_url",
            "github_url",
            "portfolio_url",
            "city",
            "country",
            "is_verified",
            "is_public",
            "profile_views",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "user",
            "is_verified",
            "profile_views",
            "created_at",
            "updated_at",
        ]


class ClassroomSerializer(serializers.ModelSerializer):

    class Meta:
        model = Classroom
        fields = [
            "id",
            "name",
            "description",
            "course_code",
            "university",
            "created_by",
            "is_public",
            "members_count",
            "posts_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "created_by",
            "members_count",
            "posts_count",
            "created_at",
            "updated_at",
        ]


class JobSerializer(serializers.ModelSerializer):
    posted_by_username = serializers.CharField(source="posted_by.username", read_only=True)

    class Meta:
        model = Job
        fields = [
            "id",
            "title",
            "description",
            "category",
            "posted_by",
            "posted_by_username",
            "student_profile",
            "location",
            "is_remote",
            "latitude",
            "longitude",
            "payment_type",
            "amount",
            "amount_max",
            "currency",
            "status",
        ]
        read_only_fields = ["posted_by", "student_profile"]
