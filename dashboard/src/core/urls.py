from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.dashboard_home, name='dashboard_home'),
    path('process/<uuid:process_id>/', views.process_detail, name='process_detail'),
    path('api/processes/', views.get_processes_data, name='get_processes_data'),
    path('config/emails/', views.EmailConfigListView.as_view(), name='email_config_list'),
    path('config/emails/add/', views.EmailConfigCreateView.as_view(), name='email_config_add'),
    path('config/emails/<int:pk>/edit/', views.EmailConfigUpdateView.as_view(), name='email_config_edit'),
    path('config/emails/<int:pk>/delete/', views.EmailConfigDeleteView.as_view(), name='email_config_delete'),
]