from django.urls import path
from . import views

urlpatterns = [
    path('', views.sector_dashboard, name='dashboard'),
    path('letter/<path:pk>/', views.letter_detail, name='letter_detail'),

]