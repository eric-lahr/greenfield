from django.urls import path
from . import views

urlpatterns = [
    path('create/', views.create_team, name='create'),
    path('view/', views.view_team, name='view_team'),
    path('edit/', views.edit_team, name='edit'),
]