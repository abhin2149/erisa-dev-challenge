from django.urls import path
from . import views
from .data_views import data_upload_view, data_export_view, data_management_dashboard

app_name = 'claims'

urlpatterns = [
    path('', views.claims_list, name='claims_list'),
    path('claim/<int:claim_id>/details/', views.claim_detail, name='claim_detail'),
    path('claim/<int:claim_id>/flag/', views.flag_claim, name='flag_claim'),
    path('claim/<int:claim_id>/add-note/', views.add_note, name='add_note'),
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Data management URLs
    path('data-upload/', data_upload_view, name='data_upload'),
    path('data-export/', data_export_view, name='data_export'),
    path('data-dashboard/', data_management_dashboard, name='data_dashboard'),
]
