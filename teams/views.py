from django.shortcuts import render
from .models import Teams
from players.models import Players, PlayerPositionRating

def create_team(request):
    return render(request, 'teams/create_team.html')

def view_teams(request):
    selected_team_id = request.GET.get('team_id')
    teams = Teams.objects.all().order_by('first_name', 'team_name')
    players = []
    player_ratings = {}

    if selected_team_id:
        players = Players.objects.filter(team_serial_id=selected_team_id).order_by('last_name', 'first_name')
        for player in players:
            ratings = PlayerPositionRating.objects.filter(player=player).select_related('position')
            player_ratings[player.id] = ratings

    return render(request, 'teams/view_teams.html', {
        'teams': teams,
        'selected_team_id': selected_team_id,
        'players': players,
        'player_ratings': player_ratings
    })

def edit_team(request):
    return render(request, 'teams/edit_team.html')
