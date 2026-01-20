from django.urls import path
from django.contrib.auth import views as auth_views  # Import standard auth views
from . import views

urlpatterns = [
    # --- AUTHENTICATION ---
    # 1. Login Page (Points to your 'registration/login.html')
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),

    # 2. Logout Action (Points to our custom view)
    path('logout/', views.logout_view, name='logout'),

    # --- PUBLIC PORTAL ---
    path('', views.sector_dashboard, name='sector_dashboard'),
    path('letter/<path:pk>/', views.letter_detail, name='letter_detail'),

    # --- CUSTOM ADMIN PANEL ---
    path('custom-admin/', views.custom_admin_dashboard, name='custom_admin_dashboard'),

    # Users
    path('custom-admin/users/', views.custom_admin_users, name='custom_admin_users'),
    path('custom-admin/users/add/', views.create_user, name='create_user'),
    path('custom-admin/users/view/<int:user_id>/', views.admin_user_detail, name='admin_user_detail'),
    path('custom-admin/users/edit/<int:user_id>/', views.edit_user, name='edit_user'),
    path('custom-admin/users/delete/<int:user_id>/', views.delete_user, name='delete_user'),

    # Letters
    path('custom-admin/letters/', views.custom_admin_letters, name='custom_admin_letters'),
    path('custom-admin/letters/add/', views.add_letter, name='add_letter'),
    path('custom-admin/letters/view/<path:pk>/', views.admin_letter_detail, name='admin_letter_detail'),
    path('custom-admin/letters/edit/<path:pk>/', views.edit_letter, name='edit_letter'),
    path('custom-admin/letters/delete/<path:pk>/', views.delete_letter, name='delete_letter'),
]