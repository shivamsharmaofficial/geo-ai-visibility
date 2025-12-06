"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

from ai_visibility import views as ai_views

urlpatterns = [
    path("admin/", admin.site.urls),

    path("", ai_views.dashboard_home, name="dashboard_home"),
    path("ai-visibility/", ai_views.dashboard, name="ai_dashboard"),
    path("competitor/", ai_views.competitor_view, name="competitor"),
    path("sources/", ai_views.sources_view, name="sources"),
    path("prompts/", ai_views.prompts_view, name="prompts"),
    path("gam-analysis/", ai_views.gam_analysis_view, name="gam_analysis"),
    path("llm-traffic/", ai_views.llm_traffic_view, name="llm_traffic"),

    # AJAX endpoints
    path("brand/lookup/", ai_views.lookup_brand, name="lookup_brand"),
    path("brand/analyze/", ai_views.run_brand_analysis, name="run_brand_analysis"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
