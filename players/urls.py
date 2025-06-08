from django.urls import path
from . import views

app_name = 'players'

urlpatterns = [
    path('create_from_team/', views.create_players_from_team, name='create_players_from_team'),
    path('career-search/', views.search_career_players, name='search_career_players'),
    path('rate/career/<str:player_id>/', views.rate_player_career, name='rate_player_career'),
    path('view/<str:playerID>/', views.view_player, name='view_player'),
    path('rate/<str:playerID>/<int:year>/<str:team_name>/', views.rate_player, name='rate_player'),
    path('create_record/', views.create_record, name='create_record'),
    path('edit/', views.edit_players, name='edit'),
]