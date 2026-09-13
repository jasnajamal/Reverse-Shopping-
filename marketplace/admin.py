from django.contrib import admin

from .models import (
    Users,
    Categories,
    Products,
    ProductImages,
    Requirements,
    RequirementImages,
    Offers,
    Orders,
    Reviews,
    ReviewImages,
    Notifications,
)


@admin.register(Users)
class UsersAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'name',
        'email',
        'role',
        'category',
        'created_at',
    )

    list_filter = (
        'role',
        'category',
    )

    search_fields = (
        'name',
        'email',
    )

    ordering = ('-id',)


@admin.register(Categories)
class CategoriesAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'name',
    )

    search_fields = (
        'name',
    )


@admin.register(Products)
class ProductsAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'product_name',
        'seller',
        'category',
        'price',
        'condition_type',
        'brand',
        'created_at',
    )

    list_filter = (
        'category',
        'condition_type',
    )

    search_fields = (
        'product_name',
        'brand',
        'seller__name',
    )

    ordering = ('-id',)


@admin.register(ProductImages)
class ProductImagesAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'product',
        'image_path',
    )

    search_fields = (
        'product__product_name',
        'image_path',
    )


@admin.register(Requirements)
class RequirementsAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'buyer',
        'product_type',
        'category',
        'budget_min',
        'budget_max',
        'preferred_brand',
        'condition_type',
        'required_by',
        'created_at',
    )

    list_filter = (
        'category',
        'condition_type',
    )

    search_fields = (
        'product_type',
        'buyer__name',
        'buyer__email',
        'preferred_brand',
    )

    ordering = ('-id',)


@admin.register(RequirementImages)
class RequirementImagesAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'requirement',
        'image_path',
    )

    search_fields = (
        'requirement__product_type',
        'image_path',
    )


@admin.register(Offers)
class OffersAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'requirement',
        'product',
        'offer_price',
        'delivery_days',
        'warranty',
        'created_at',
    )

    list_filter = (
        'delivery_days',
    )

    search_fields = (
        'requirement__product_type',
        'product__product_name',
        'product__seller__name',
    )

    ordering = ('-id',)


@admin.register(Orders)
class OrdersAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'buyer',
        'offer',
        'order_status',
        'order_date',
    )

    list_filter = (
        'order_status',
    )

    search_fields = (
        'buyer__name',
        'buyer__email',
        'offer__product__product_name',
    )

    ordering = ('-id',)


@admin.register(Reviews)
class ReviewsAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'order',
        'buyer',
        'seller',
        'rating',
        'created_at',
    )

    list_filter = (
        'rating',
    )

    search_fields = (
        'buyer__name',
        'seller__name',
        'review_text',
    )

    ordering = ('-id',)


@admin.register(ReviewImages)
class ReviewImagesAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'review',
        'image_path',
    )

    search_fields = (
        'image_path',
    )


@admin.register(Notifications)
class NotificationsAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'message',
        'is_read',
        'created_at',
    )

    list_filter = (
        'is_read',
    )

    search_fields = (
        'user__name',
        'user__email',
        'message',
    )

    ordering = ('-id',)