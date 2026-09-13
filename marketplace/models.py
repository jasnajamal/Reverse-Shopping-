# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class Categories(models.Model):
    name = models.CharField(unique=True, max_length=100)

    class Meta:
        managed = False
        db_table = 'categories'


class Offers(models.Model):
    requirement = models.ForeignKey('Requirements', models.DO_NOTHING)
    product = models.ForeignKey('Products', models.DO_NOTHING)
    offer_price = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_days = models.IntegerField(blank=True, null=True)
    warranty = models.CharField(max_length=100, blank=True, null=True)
    message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'offers'


class Orders(models.Model):
    buyer = models.ForeignKey('Users', models.DO_NOTHING)
    offer = models.ForeignKey(Offers, models.DO_NOTHING)
    order_status = models.CharField(max_length=9, blank=True, null=True)
    order_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'orders'


class ProductImages(models.Model):
    product = models.ForeignKey('Products', models.DO_NOTHING)
    image_path = models.CharField(max_length=255)

    class Meta:
        managed = False
        db_table = 'product_images'


class Products(models.Model):
    seller = models.ForeignKey('Users', models.DO_NOTHING)
    category = models.ForeignKey(Categories, models.DO_NOTHING)
    product_name = models.CharField(max_length=150)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    condition_type = models.CharField(max_length=4)
    brand = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'products'


class RequirementImages(models.Model):
    requirement = models.ForeignKey('Requirements', models.DO_NOTHING)
    image_path = models.CharField(max_length=255)

    class Meta:
        managed = False
        db_table = 'requirement_images'


class Requirements(models.Model):
    buyer = models.ForeignKey('Users', models.DO_NOTHING)
    category = models.ForeignKey(Categories, models.DO_NOTHING)
    product_type = models.CharField(max_length=100)
    budget_min = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    budget_max = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    preferred_brand = models.CharField(max_length=100, blank=True, null=True)
    condition_type = models.CharField(max_length=6, blank=True, null=True)
    additional_requirements = models.TextField(blank=True, null=True)
    required_by = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'requirements'


class ReviewImages(models.Model):
    review = models.ForeignKey('Reviews', models.DO_NOTHING)
    image_path = models.CharField(max_length=255)

    class Meta:
        managed = False
        db_table = 'review_images'


class Reviews(models.Model):
    order = models.ForeignKey(Orders, models.DO_NOTHING)
    buyer = models.ForeignKey('Users', models.DO_NOTHING)
    seller = models.ForeignKey('Users', models.DO_NOTHING, related_name='reviews_seller_set')
    rating = models.IntegerField()
    review_text = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'reviews'


class Users(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    email = models.CharField(unique=True, max_length=100)
    password = models.CharField(max_length=255)
    role = models.CharField(max_length=6)
    category = models.ForeignKey(
        'Categories',
        models.DO_NOTHING,
        blank=True,
        null=True
    )
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'users'

class Notifications(models.Model):
    user = models.ForeignKey('Users', models.DO_NOTHING)
    message = models.CharField(max_length=255)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'notifications'