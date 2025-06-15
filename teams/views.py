from django.shortcuts import render, get_object_or_404
from .models import Teams
from players.models import Players, PlayerPositionRating
from django.db.models import Case, When, Value, IntegerField, Prefetch
from django.http import HttpResponse
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from greenfield.utils.sherco import parse_pitching_sort_key, get_primary_position_order

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
        players = list(Players.objects.filter(team_serial_id=selected_team_id))

        for player in players:
            # 🔁 ORDER ratings by custom 'position_order'
            ratings = (
                player.position_ratings.all()
                .select_related('position')
            )
            player_ratings[player.id] = ratings

            player.is_pitcher = any(
                r.position.name == 'P' for r in ratings if r.position
            )

        # Separate and sort batters/pitchers
        batters = [p for p in players if not p.is_pitcher]
        pitchers = [p for p in players if p.is_pitcher]

        # Sort batters alphabetically
        batters.sort(key=lambda p: (get_primary_position_order(p), p.last_name, p.first_name))
        pitchers.sort(key=lambda p: parse_pitching_sort_key(p.pitching))

        # Merge
        players = batters + pitchers

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

    for player in players:
        ratings = PlayerPositionRating.objects.filter(player=player).select_related('position')
        player_ratings[player.id] = ratings
        player.ratings = ratings  # attach ratings for sorting
        player.is_pitcher = any(r.position.name == 'P' for r in ratings if r.position)
        player.primary_position = get_primary_position(ratings)

    # Sort batters and pitchers separately, using shared utils
    pitchers = [p for p in players if p.is_pitcher]
    batters = [p for p in players if not p.is_pitcher]

    pitchers.sort(key=lambda p: parse_pitching_sort(p.pitching))
    batters.sort(key=lambda p: (p.primary_position, p.last_name, p.first_name))

    players = batters + pitchers  # final sorted list

    # Setup PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{team.team_name}_{team.first_name}.pdf"'
    p = canvas.Canvas(response, pagesize=letter)
    width, height = letter

    # Title/Header
    margin = 40
    y_start = height - 50
    p.setFont("Helvetica-Bold", 14)
    p.drawString(margin, y_start, f"Team: {team.team_name} ({team.first_name})")
    y_start -= 30

    # Table headers
    p.setFont("Helvetica-Bold", 10)
    headers = ["Name", "B-T", "Role", "Ratings"]
    col_widths = [2.3 * inch, 1.1 * inch, 1.1 * inch, 3.3 * inch]
    x_positions = [margin]
    for width in col_widths[:-1]:
        x_positions.append(x_positions[-1] + width)

    # Draw headers
    p.setFont("Helvetica-Bold", 10)
    for i, header in enumerate(headers):
        p.drawString(x_positions[i], y, header)
    y -= 15
    p.line(margin, y, width - margin, y)
    y -= 10

    # Table content
    p.setFont("Helvetica", 9)
    for player in players:
        if y < 50:
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
        hand = f"{player.bats}-{player.throws}"
        role = "Pitcher" if player.is_pitcher else "Batter"
        
        ratings_parts = []

        if player.is_pitcher:
            if player.pitching:
                ratings_parts.append(player.pitching)
            if player.pitch_ctl is not None:
                ratings_parts.append(f"PCN-{player.pitch_ctl}")
            if player.pitch_prob_hit is not None:
                ratings_parts.append(f"PPH-{player.pitch_prob_hit}")

        # Always include offense/PH, even for pitchers
        if player.offense:
            ratings_parts.insert(0, player.offense)
        if player.bat_prob_hit is not None:
            ratings_parts.insert(1, f"PH-{player.bat_prob_hit}")

        ratings = " ".join(ratings_parts)

        row_data = [name, hand, role, ratings]
        for i, value in enumerate(row_data):
            p.drawString(x_positions[i], y, str(value))
        y -= 15

    p.showPage()
    p.save()
    return response