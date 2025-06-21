from django.urls import path
from . import views

app_name = 'stats'

urlpatterns = [
    path('competitions/', views.CompetitionListView.as_view(), name='competition-list'),
    path('competitions/new/', views.CompetitionCreateView.as_view(), name='competition-create'),
    path('games/create/', views.create_game_view, name='create-game'),
    path('games/select/', views.game_select_view, name='game-select'),
    path('games/<int:game_id>/delete/', views.delete_game_view, name='delete-game'),
    path('games/<int:game_id>/finalize/', views.finalize_game_view, name='finalize-game'),
    path('games/<int:game_id>/lineups/', views.enter_lineups_view, name='enter-lineups'),
    path('games/<int:game_id>/statlines/', views.enter_statlines_view, name='enter-statlines'),
    path('games/<int:game_id>/substitutions/', views.enter_substitutions, name='enter-substitutions'),
    path('games/<int:game_id>/inning-scores/', views.enter_inning_scores, name='enter-inning-scores'),
    path('games/<int:game_id>/enhanced-stats/', views.enter_enhanced_stats, name='enter-enhanced-stats'),
]