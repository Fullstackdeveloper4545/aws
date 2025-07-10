from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.dashboard_home, name='dashboard_home'),
    path('process/<uuid:process_id>/', views.process_detail, name='process_detail'),
    path('api/processes/', views.get_processes_data, name='get_processes_data'),
]