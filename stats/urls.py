from django.urls import path
from . import views

app_name = 'stats'

urlpatterns = [
    path('competitions/', views.CompetitionListView.as_view(), name='competition-list'),
    path('competitions/new/', views.CompetitionCreateView.as_view(), name='competition-create'),
    path('games/new/', views.GameCreateView.as_view(), name='game-create'),
    path('games/select/', views.GameSelectView.as_view(), name='game-select'),
    path('games/<int:game_id>/lineups/', views.enter_lineups_view, name='enter-lineups'),
]