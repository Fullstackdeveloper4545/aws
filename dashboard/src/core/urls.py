from django.urls import path
from . import views, bnsf_views

app_name = 'core'

urlpatterns = [
    path('', views.dashboard_home, name='dashboard_home'),
    path('process/<uuid:process_id>/', views.process_detail, name='process_detail'),
    path('api/processes/', views.get_processes_data, name='get_processes_data'),
    path('config/emails/', views.EmailConfigListView.as_view(), name='email_config_list'),
    path('config/emails/add/', views.EmailConfigCreateView.as_view(), name='email_config_add'),
    path('config/emails/<int:pk>/edit/', views.EmailConfigUpdateView.as_view(), name='email_config_edit'),
    path('config/emails/<int:pk>/delete/', views.EmailConfigDeleteView.as_view(), name='email_config_delete'),
    
    # Credentials URLs
    path('credentials/', views.CredentialsListView.as_view(), name='credentials_list'),
    path('credentials/add/', views.CredentialsCreateView.as_view(), name='credentials_add'),
    path('credentials/<uuid:pk>/', views.CredentialsDetailView.as_view(), name='credentials_detail'),
    path('credentials/<uuid:pk>/edit/', views.CredentialsUpdateView.as_view(), name='credentials_edit'),
    path('credentials/<uuid:pk>/delete/', views.CredentialsDeleteView.as_view(), name='credentials_delete'),
    
    # Site Credential URLs
    path('site-credentials/', views.SiteCredentialListView.as_view(), name='site_credential_list'),
    path('site-credentials/add/', views.SiteCredentialCreateView.as_view(), name='site_credential_add'),
    path('site-credentials/<int:pk>/edit/', views.SiteCredentialUpdateView.as_view(), name='site_credential_edit'),
    path('site-credentials/<int:pk>/delete/', views.SiteCredentialDeleteView.as_view(), name='site_credential_delete'),
    
    # AJAX endpoints for credentials
    path('api/credentials/', views.get_credentials_data, name='get_credentials_data'),
    path('api/site-credentials/', views.get_site_credentials_data, name='get_site_credentials_data'),
    
    # BNSF API Fetch
    path('bnsf-fetch/', bnsf_views.bnsf_fetch_data, name='bnsf_fetch_data'),
    path('bnsf-data/', bnsf_views.bnsf_data_list, name='bnsf_data_list'),
    path('api/bnsf/fetch-waybill/', bnsf_views.fetch_bnsf_waybill, name='api_fetch_bnsf_waybill'),
    path('api/bnsf/waybill/<int:waybill_id>/', bnsf_views.get_waybill_data, name='api_get_waybill_data'),
    path('api/bnsf/start-fetch/', bnsf_views.start_bnsf_fetch, name='api_start_bnsf_fetch'),
    path('api/bnsf/progress/<str:job_id>/', bnsf_views.get_bnsf_progress, name='api_get_bnsf_progress'),
]