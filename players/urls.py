from django.urls import path
from . import views

app_name = 'players'

urlpatterns = [
    path('create_from_team/', views.create_players_from_team, name='create_players_from_team'),
    path('create_career/', views.create_career_player, name='create_career_player'),
    path('view/<str:playerID>/', views.view_player, name='view_player'),
    path('edit/', views.edit_players, name='edit'),
]