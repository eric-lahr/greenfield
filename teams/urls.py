from django.urls import path
from . import views

urlpatterns = [
    path('create/', views.create_team, name='create'),
    path('teams/view/', views.view_teams, name='view_teams'),
    path('edit/', views.edit_team, name='edit'),
]