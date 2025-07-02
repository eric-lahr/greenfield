from players.models import Players
from teams.models import Teams

# Replace with actual team name/year used in your game
team = Teams.objects.get(first_name='2024', team_name='Dodgers')
players = Players.objects.filter(team_serial_id=team.id)

print(f"Team ID: {team.id}")
print(f"Player count: {players.count()}")
for p in players:
    print(p.first_name, p.last_name, p.team_serial_id)
