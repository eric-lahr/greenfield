from django.shortcuts import render, get_object_or_404
from .models import Teams
from players.models import Players, PlayerPositionRating
from django.db.models import Case, When, Value, IntegerField
from django.http import HttpResponse
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch

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

def create_team_pdf(request, team_serial):
    team = get_object_or_404(Teams, pk=team_serial)
    players = list(Players.objects.filter(team_serial_id=team_serial))
    player_ratings = {}

    # Collect ratings and identify pitchers
    for player in players:
        ratings = PlayerPositionRating.objects.filter(player=player).select_related('position')
        player_ratings[player.id] = ratings
        player.is_pitcher = any(r.position.name == 'P' for r in ratings if r.position)

    # Sort players: non-pitchers first, then pitchers
    players.sort(key=lambda p: (p.is_pitcher, p.last_name, p.first_name))

    # Setup PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{team.team_name}_{team.first_name}.pdf"'
    p = canvas.Canvas(response, pagesize=letter)
    width, height = letter

    # Title/Header
    margin = 50
    y_start = height - 50
    p.setFont("Helvetica-Bold", 14)
    p.drawString(margin, y_start, f"Team: {team.team_name} ({team.first_name})")
    y_start -= 30

    # Table headers
    p.setFont("Helvetica-Bold", 10)
    headers = ["Name", "Bats", "Throws", "Offense", "Positions", "Pitching"]
    col_widths = [1.5 * inch, 0.7 * inch, 0.7 * inch, 1.7 * inch, 1.4 * inch, 0.9 * inch]
    x_positions = [margin]
    for width in col_widths[:-1]:
        x_positions.append(x_positions[-1] + width)

    y = y_start
    for i, header in enumerate(headers):
        p.drawString(x_positions[i], y, header)
    y -= 15
    p.line(margin, y, width - margin, y)
    y -= 10

    # Table content
    p.setFont("Helvetica", 9)
    for player in players:
        if y < 50:  # New page if too low (we try to keep it one page but safe fallback)
            p.showPage()
            y = height - 50
            p.setFont("Helvetica-Bold", 14)
            p.drawString(margin, y, f"Team: {team.team_name} ({team.first_name})")
            y -= 30
            p.setFont("Helvetica-Bold", 10)
            for i, header in enumerate(headers):
                p.drawString(x_positions[i], y, header)
            y -= 15
            p.line(margin, y, width - margin, y)
            y -= 10
            p.setFont("Helvetica", 9)

        name = f"{player.first_name} {player.last_name}"
        positions = ", ".join([f"{r.position.name}: {r.rating}" for r in player_ratings[player.id]])
        pitching = player.pitching if (hasattr(player, 'pitching') and player.pitching is not None) else ""

        row_data = [
            name,
            player.bats,
            player.throws,
            player.offense,
            positions,
            pitching
        ]
        for i, value in enumerate(row_data):
            p.drawString(x_positions[i], y, str(value))
        y -= 15

    p.showPage()
    p.save()
    return response