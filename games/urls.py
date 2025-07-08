from django.urls import path
from . import views

app_name = 'games'

urlpatterns = [
    path('setup/', views.setup_game, name='setup_game'),
    path('live/<int:session_id>/', views.live_game, name='live_game'),
    path(
        'session/<int:session_id>/lineup/away/',
        views.lineup_entry,
        {'side': 'away'},
        name='lineup_away'
    ),
    path(
        'session/<int:session_id>/lineup/home/',
        views.lineup_entry,
        {'side': 'home'},
        name='lineup_home'
    ),
    path(
        'session/<int:session_id>/substitute/',
        views.substitute,
        name='substitute'
    ),
    path(
        'sessions/',
        views.session_list,
        name='session_list'
    ),
    path(
        'live/<int:session_id>/undo/',
        views.undo_last_event,
        name='live_undo'
    ),
    path(
        'live/<int:session_id>/stats/',
        views.game_stats,
        name='game_stats'
    ),
]