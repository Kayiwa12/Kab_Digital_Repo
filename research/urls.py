from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('research/', views.research_list, name='research_list'),
    path('research/<str:dspace_uuid>/', views.research_detail, name='research_detail'),
    path('advanced-search/', views.advanced_search, name='advanced_search'),
    path('researchers/', views.researchers_list, name='researchers_list'),
    path('researchers/<int:researcher_id>/', views.researcher_detail, name='researcher_detail'),
    path('analytics/', views.analytics_view, name='analytics'),
    path('coverage/', views.coverage_view, name='coverage'),
    path('trends/', views.trends_view, name='trends'),
    path('about/', views.about_view, name='about'),
    
    # Admin tools
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('quick-admin-login/', views.quick_admin_login, name='quick_admin_login'),
    path('admin-dashboard/sync/', views.admin_trigger_sync, name='admin_trigger_sync'),
    path('admin-dashboard/logs/', views.admin_sync_logs, name='admin_sync_logs'),
    
    # JSON API endpoints
    path('api/analytics/', views.api_analytics_data, name='api_analytics_data'),
    path('api/trends/', views.api_trends_data, name='api_trends_data'),
]
