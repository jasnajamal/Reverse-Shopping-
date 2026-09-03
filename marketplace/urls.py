from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('buyer/', views.buyer_dashboard, name='buyer_dashboard'),
    path('post-requirement/', views.post_requirement, name='post_requirement'),
    path('my-requirements/', views.my_requirements, name='my_requirements'),
    path('seller/', views.seller_dashboard, name='seller_dashboard'),
    path('buyer-requirements/', views.buyer_requirements, name='buyer_requirements'),
    path('submit-offer/<int:requirement_id>/', views.submit_offer, name='submit_offer'),
    path('update-offer/<int:offer_id>/', views.update_offer, name='update_offer'),
    path('view-offers/<int:requirement_id>/', views.view_offers, name='view_offers'),
    path('view-offers/<int:requirement_id>/', views.view_offers, name='view_offers'),

]