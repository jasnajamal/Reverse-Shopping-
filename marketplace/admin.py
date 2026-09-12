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
)


@admin.register(Users)
class UsersAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'email', 'role', 'category', 'created_at')


@admin.register(Categories)
class CategoriesAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')


@admin.register(Products)
class ProductsAdmin(admin.ModelAdmin):
    list_display = ('id', 'product_name', 'seller', 'category', 'price', 'condition_type', 'brand', 'created_at')


@admin.register(ProductImages)
class ProductImagesAdmin(admin.ModelAdmin):
    list_display = ('id', 'product', 'image_path')


@admin.register(Requirements)
class RequirementsAdmin(admin.ModelAdmin):
    list_display = ('id', 'buyer', 'product_type', 'category', 'budget_min', 'budget_max', 'preferred_brand', 'condition_type', 'required_by', 'created_at')


@admin.register(RequirementImages)
class RequirementImagesAdmin(admin.ModelAdmin):
    list_display = ('id', 'requirement', 'image_path')


@admin.register(Offers)
class OffersAdmin(admin.ModelAdmin):
    list_display = ('id', 'requirement', 'product', 'offer_price', 'delivery_days', 'warranty', 'created_at')


@admin.register(Orders)
class OrdersAdmin(admin.ModelAdmin):
    list_display = ('id', 'buyer', 'offer', 'order_status', 'order_date')


@admin.register(Reviews)
class ReviewsAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'buyer', 'seller', 'rating', 'created_at')


@admin.register(ReviewImages)
class ReviewImagesAdmin(admin.ModelAdmin):
    list_display = ('id', 'review', 'image_path')