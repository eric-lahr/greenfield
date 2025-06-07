from django.shortcuts import render
from .models import Teams
from players.models import Players, PlayerPositionRating
from django.db.models import Case, When, Value, IntegerField

def create_team(request):
    return render(request, 'teams/create_team.html')

def edit_team(request):
    return render(request, 'teams/edit_team.html')

def view_teams(request):
    selected_team_id = request.GET.get('team_id')
    teams = Teams.objects.all().order_by('first_name', 'team_name')
    players = []
    player_ratings = {}

    if selected_team_id:
        # Step 1: Get players normally
        players = list(Players.objects.filter(team_serial_id=selected_team_id))

        # Step 2: Get ratings and tag each player with a flag for "is_pitcher"
        for player in players:
            ratings = (
                PlayerPositionRating.objects.filter(player=player)
                .select_related('position')
            )
            player_ratings[player.id] = ratings
            player.is_pitcher = any(
                r.position.name == 'P' for r in ratings if r.position
            )

        # Step 3: Sort players: non-pitchers first, then pitchers
        players.sort(key=lambda p: (p.is_pitcher, p.last_name, p.first_name))

    return render(request, 'teams/view_teams.html', {
        'teams': teams,
        'selected_team_id': selected_team_id,
        'players': players,
        'player_ratings': player_ratings
    })