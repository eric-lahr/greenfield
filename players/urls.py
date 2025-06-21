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
    path('edit/', views.select_team_for_edit, name='select_team_for_edit'),
    path('edit/<int:player_id>/', views.edit_player, name='edit_player'),
    path('delete/<int:player_id>/', views.delete_player, name='delete_player'),
    path('create_custom_player/', views.create_custom_player, name='create_custom_player'),
]