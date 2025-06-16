from django.shortcuts import render, get_object_or_404
from io import BytesIO
from .models import Teams
from players.models import Players, PlayerPositionRating
from django.db.models import Case, When, Value, IntegerField, Prefetch
from django.http import HttpResponse
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.platypus import Table, TableStyle, Paragraph, SimpleDocTemplate, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from greenfield.utils.sherco import parse_pitching_sort_key, get_primary_position_order, get_primary_position

def create_team(request):
    return render(request, 'teams/create_team.html')

def edit_team(request):
    return render(request, 'teams/edit_team.html')

def new_view_team(request):
    selected_team_id = request.GET.get('team_id')
    teams = Teams.objects.all().order_by('first_name', 'team_name')
    players = []
    player_ratings = {}

    if selected_team_id:
        players = list(Players.objects.filter(team_serial_id=selected_team_id))
        for player in players:
            ratings = (
                player.position_ratings.all()
                .select_related('position')
            )
            player_ratings[player.id] = ratings
            player.ratings = ratings
            player.is_pitcher = any(r.position.name == 'P' for r in ratings if r.position)
            player.primary_position = get_primary_position(ratings)

        # Sort: batters by position then name; pitchers by pitching values
        batters = [p for p in players if not p.is_pitcher]
        pitchers = [p for p in players if p.is_pitcher]

        batters.sort(key=lambda p: (get_primary_position_order(p), p.last_name, p.first_name))
        pitchers.sort(key=lambda p: parse_pitching_sort_key(p.pitching))

        players = batters + pitchers

    return render(request, 'teams/view_team_defense.html', {
        'teams': teams,
        'selected_team_id': selected_team_id,
        'players': players,
        'player_ratings': player_ratings
    })


def new_create_pdf(request, team_serial):
    team = get_object_or_404(Teams, pk=team_serial)
    players = list(Players.objects.filter(team_serial_id=team_serial))

    for player in players:
        ratings = PlayerPositionRating.objects.filter(player=player).select_related('position')
        player.ratings = ratings
        player.is_pitcher = any(r.position.name == 'P' for r in ratings if r.position)
        player.primary_position = get_primary_position(ratings)

    batters = [p for p in players if not p.is_pitcher]
    pitchers = [p for p in players if p.is_pitcher]

    batters.sort(key=lambda p: (get_primary_position_order(p), p.last_name, p.first_name))
    pitchers.sort(key=lambda p: parse_pitching_sort_key(p.pitching))

    players = batters + pitchers

    # === PDF Setup ===
    buffer = BytesIO()
    margin = 50  # Safe margin
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=60,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()
    styleN = styles["Normal"]
    styleN.fontSize = 9
    styleN.leading = 11

    elements = []

    # Title
    title = f"Team: {team.team_name} ({team.first_name})"
    elements.append(Paragraph(title, styles["Title"]))
    elements.append(Spacer(1, 12))

    # Table headers and data
    headers = ["Name", "B-T", "Offense", "Defense", "Pitching"]
    table_data = [headers]

    for player in players:
        name = f"{player.first_name} {player.last_name}"
        hand = f"{player.bats}-{player.throws}"
        offense = f"{player.offense or ''} PH-{player.bat_prob_hit}" if player.bat_prob_hit else (player.offense or '')
        pitching = " ".join(filter(None, [
            player.pitching,
            f"PCN-{player.pitch_ctl}" if player.pitch_ctl is not None else '',
            f"PPH-{player.pitch_prob_hit}" if player.pitch_prob_hit is not None else ''
        ]))
        defense = ', '.join(f"{r.position.name}: {r.rating}" for r in player.ratings if r.position)

        row = [
            Paragraph(name, styleN),
            Paragraph(hand, styleN),
            Paragraph(offense.strip(), styleN),
            Paragraph(defense, styleN),
            Paragraph(pitching.strip(), styleN),
        ]
        table_data.append(row)

    # Column widths — total must be < page width - 2 * margin (about 6.5 inches)
    col_widths = [
        2.3 * inch,  # Name
        0.6 * inch,  # B-T
        1.5 * inch,  # Offense
        1.7 * inch,  # Defense
        1.4 * inch   # Pitching
    ]

    table = Table(table_data, colWidths=col_widths)
    table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.darkblue),
        ('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
    ]))

    elements.append(table)

    # Build PDF and force download
    doc.build(elements)
    buffer.seek(0)
    response = HttpResponse(buffer.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{team.team_name}_{team.first_name}_full.pdf"'
    return response