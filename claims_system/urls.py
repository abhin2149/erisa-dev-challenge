"""
URL configuration for claims_system project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
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
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.shortcuts import redirect
from claims.data_views import data_upload_view, data_export_view, data_management_dashboard

urlpatterns = [
    path('admin/', admin.site.urls),
    path('data-admin/', data_management_dashboard, name='data_admin_dashboard'),
    path('data-admin/data-upload/', data_upload_view, name='data_admin_upload'),
    path('data-admin/data-export/', data_export_view, name='data_admin_export'),
    path('', lambda request: redirect('claims:claims_list'), name='home'),
    path('claims/', include('claims.urls')),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
]