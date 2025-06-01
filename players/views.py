from django.shortcuts import render
from django.conf import settings
from psycopg2.extras import RealDictCursor
from greenfield.utils.lahman_db import get_players_by_team_and_year, get_teamID_from_name, get_rated_player_status

def create_players_from_team(request):
    if request.method == 'POST':
        year = request.POST.get('year')
        team_name = request.POST.get('team_name')

        if not year or not team_name:
            return render(request, 'players/create_players_from_team.html', {
                'error': 'Please enter both fields.',
                'searched': True
                })

        # Convert team_name like 'Pirates' into 'PIT'
        team_id = get_teamID_from_name(year, team_name)

        if not team_id:
            return render(request, 'players/create_players_from_team.html', {
                'error': f'No team ID found for "{team_name}" in {year}.',
                'searched': True
            })

        players = get_players_by_team_and_year(year, team_id)
        status_lookup = get_rated_player_status(year, team_name, players)

        if not players:
            return render(request, 'players/player_results.html', {
                'message': 'No players found.',
                'players': [],
                'year': year,
                'team_name': team_name,
                'searched': True
            })
        
        return render(request, 'players/player_results.html', {
            'players': players,
            'status_lookup': status_lookup,
            'year': year,
            'team_name': team_name,
            'searched': True
        })

    return render(request, 'players/create_players_from_team.html')


def create_career_player(request):
    return render(request, 'players/create_custom_player.html')


def view_player(request, playerID):
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM People WHERE playerID = %s", [playerID])
        row = cursor.fetchone()
    # Render with a simple template that displays the player info


def edit_players(request):
    return render(request, 'players/edit_player.html')
