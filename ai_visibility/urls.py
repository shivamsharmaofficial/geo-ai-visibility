from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='ai_dashboard'),
    path('brand/lookup/', views.lookup_brand, name='brand_lookup'),
]
