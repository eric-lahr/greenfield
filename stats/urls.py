from django.urls import path
from . import views

app_name = 'stats'

urlpatterns = [
    path('competitions/', views.CompetitionListView.as_view(), name='competition-list'),
    path('competitions/new/', views.CompetitionCreateView.as_view(), name='competition-add'),
    path('competitions/<int:pk>/leagues/count/', views.LeagueCountView.as_view(), name='league-count'),
    path('competitions/<int:pk>/leagues/add', views.LeagueCreateView.as_view(), name='league-add'),
    path(
        'competitions/leagues/<int:league_pk>/divisions/count/',
        views.DivisionCountView.as_view(),
        name='division-count'
        ),
    path(
        'competitions/leagues/<int:league_pk>/divisions/add/',
        views.DivisionCreateView.as_view(),
        name='division-add'
        ),
    path('competitions/<int:pk>/', views.CompetitionDetailView.as_view(), name='competition-detail'),
    path('competitions/<int:pk>/assign/', views.CompetitionTeamAssignView.as_view(), name="competition-assign"),
    path(
        'competitions/leagues/<int:league_pk>/assign/',
        views.LeagueTeamAssignView.as_view(),
        name='league-assign'
        ),
    path(
        'competitions/leagues/<int:league_pk>/divisions/<int:division_pk>/assign/',
        views.DivisionTeamAssignView.as_view(),
        name='division-assign'
        ),
    path('games/create/', views.create_game, name='create-game'),
    path('games/select/', views.game_select_view, name='game-select'),
    path('games/<int:game_id>/delete/', views.delete_game_view, name='delete-game'),
    path('games/<int:game_id>/finalize/', views.finalize_game_view, name='finalize-game'),
    path('games/<int:game_id>/lineups/', views.enter_lineups_view, name='enter-lineups'),
    path('games/<int:game_id>/statlines/', views.enter_statlines_view, name='enter-statlines'),
    path('games/<int:game_id>/substitutions/', views.enter_substitutions, name='enter-substitutions'),
    path('games/<int:game_id>/inning-scores/', views.enter_inning_scores, name='enter-inning-scores'),
    path('games/<int:game_id>/boxscore/', views.game_boxscore_view, name='game-boxscore'),
    path('competitions/select/', views.competition_select_view, name='competition-select'),
    path('competitions/menu/', views.competition_menu_view, name='competition-menu'),
    path('competitions/stats/', views.competition_player_stats_view, name='competition-player-stats'),
    path('competitions/team-stats/', views.competition_team_stats_view, name='competition-team-stats'),
    path('competitions/leaders/', views.competition_leaders_view, name='competition-leaders'),
    path('competitions/standings/', views.competition_standings_view, name='competition-standings'),
    path('competitions/games/', views.competition_games_view, name='competition-games'),
    path('competitions/<int:pk>/teams/json/', views.competition_teams_json, name='competition-teams-json'),
    path('competitions/<int:pk>/standings/',
     views.StandingsView.as_view(),
     name='competition-standings'),
]