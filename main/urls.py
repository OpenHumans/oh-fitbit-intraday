from django.urls import path

from . import views

urlpatterns = [
    path(r'', views.index, name='index'),
    path(r'setup/', views.setup, name='setup'),
    path(r'dashboard/', views.dashboard, name='dashboard'),
    path(r'logout/', views.logout_user, name='logout'),
    path(r'about/', views.about, name='about'),
    path(r'create-fitbit/', views.create_fitbit, name='create-fitbit'),
    path(r'delete-fitbit/', views.delete_fitbit, name='delete-fitbit'),
    path(r'fitbit/authorized/', views.complete_fitbit, name='fb_complete'),
]
