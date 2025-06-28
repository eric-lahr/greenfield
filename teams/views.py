import csv
from django.shortcuts import render, get_object_or_404
from io import BytesIO, StringIO
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
from greenfield.utils.sherco import (
    parse_pitching_sort_key, get_primary_position_order, get_primary_position,
    get_defense_string, get_pitching_string, get_pitching_string
    )

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


def create_pdf_batters(request, team_serial):
    team = get_object_or_404(Teams, pk=team_serial)
    players = list(Players.objects.filter(team_serial_id=team_serial))

    for player in players:
        ratings = PlayerPositionRating.objects.filter(player=player).select_related('position')
        player.ratings = ratings
        player.is_pitcher = any(r.position.name == 'P' for r in ratings if r.position)
        player.primary_position = get_primary_position(ratings)

    # Filter only batters
    batters = [p for p in players if not p.is_pitcher]
    batters.sort(key=lambda p: (get_primary_position_order(p), p.last_name, p.first_name))

    buffer = BytesIO()
    margin = 50
    doc = SimpleDocTemplate(buffer, pagesize=letter, leftMargin=margin, rightMargin=margin, topMargin=60, bottomMargin=40)

    styles = getSampleStyleSheet()
    styleN = styles["Normal"]
    styleN.fontSize = 9
    styleN.leading = 11

    elements = [Paragraph(f"Batters: {team.team_name} ({team.first_name})", styles["Title"]), Spacer(1, 12)]

    headers = ["Name", "B-T", "Offense", "Defense"]
    table_data = [headers]

    for p in batters:
        name = f"{p.first_name} {p.last_name}"
        hand = f"{p.bats}-{p.throws}"
        offense = f"{p.offense or ''} PH-{p.bat_prob_hit}" if p.bat_prob_hit else (p.offense or '')
        defense = ', '.join(f"{r.position.name}: {r.rating}" for r in p.ratings if r.position)

        row = [
            Paragraph(name, styleN),
            Paragraph(hand, styleN),
            Paragraph(offense.strip(), styleN),
            Paragraph(defense, styleN),
        ]
        table_data.append(row)

    col_widths = [2.4 * inch, 0.6 * inch, 2.0 * inch, 2.2 * inch]

    table = Table(table_data, colWidths=col_widths)
    table.setStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.darkblue),
        ('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
    ])

    elements.append(table)
    doc.build(elements)

    buffer.seek(0)
    response = HttpResponse(buffer.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{team.team_name}_{team.first_name}_batters.pdf"'
    return response


def create_pdf_pitchers(request, team_serial):
    team = get_object_or_404(Teams, pk=team_serial)
    players = list(Players.objects.filter(team_serial_id=team_serial))

    for player in players:
        ratings = PlayerPositionRating.objects.filter(player=player).select_related('position')
        player.ratings = ratings
        player.is_pitcher = any(r.position.name == 'P' for r in ratings if r.position)
        player.primary_position = get_primary_position(ratings)
        player.offense = player.offense or ''  # Ensure exists
        player.defense = get_defense_string(ratings)
        player.pitching = get_pitching_string(player)

    pitchers = [p for p in players if p.is_pitcher]
    pitchers.sort(key=lambda p: parse_pitching_sort_key(p.pitching))

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{team.team_name}_{team.first_name}_pitchers.pdf"'
    p = canvas.Canvas(response, pagesize=letter)
    width, height = letter

    margin = 40
    y = height - 50
    p.setFont("Helvetica-Bold", 14)
    p.drawString(margin, y, f"Pitchers - {team.team_name} ({team.first_name})")
    y -= 30

    headers = ["Name", "B-T", "Offense", "Defense", "Pitching"]
    col_widths = [1.6 * inch, 0.5 * inch, 2.0 * inch, 1.0 * inch, 2.5 * inch]
    x_positions = [margin]
    for width in col_widths[:-1]:
        x_positions.append(x_positions[-1] + width)

    p.setFont("Helvetica-Bold", 10)
    for i, header in enumerate(headers):
        p.drawString(x_positions[i], y, header)
    y -= 15
    p.setFont("Helvetica", 10)

    for player in pitchers:
        if y < 50:
            p.showPage()
            y = height - 50
            p.setFont("Helvetica-Bold", 10)
            for i, header in enumerate(headers):
                p.drawString(x_positions[i], y, header)
            y -= 15
            p.setFont("Helvetica", 10)

        data = [
            f"{player.first_name} {player.last_name}",
            f"{player.bats}-{player.throws}",
            player.offense,
            player.defense,
            player.pitching,
        ]
        for i, val in enumerate(data):
            p.drawString(x_positions[i], y, str(val))
        y -= 15

    p.save()
    return response


def create_csv_batters(request, team_serial):
    team = get_object_or_404(Teams, pk=team_serial)
    players = list(Players.objects.filter(team_serial_id=team_serial))

    for player in players:
        ratings = PlayerPositionRating.objects.filter(player=player).select_related('position')
        player.ratings = ratings
        player.is_pitcher = any(r.position.name == 'P' for r in ratings if r.position)

    batters = [p for p in players if not p.is_pitcher]
    batters.sort(key=lambda p: (get_primary_position_order(p), p.last_name, p.first_name))

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Name", "B-T", "Offense", "Defense"])

    for p in batters:
        name = f"{p.first_name} {p.last_name}"
        hand = f"{p.bats}-{p.throws}"
        offense = f"{p.offense or ''} PH-{p.bat_prob_hit}" if p.bat_prob_hit else (p.offense or '')
        defense = ', '.join(f"{r.position.name}: {r.rating}" for r in p.ratings if r.position)
        writer.writerow([name, hand, offense.strip(), defense])

    response = HttpResponse(output.getvalue(), content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{team.team_name}_{team.first_name}_batters.csv"'
    return response


def create_csv_pitchers(request, team_serial):
    team = get_object_or_404(Teams, pk=team_serial)
    players = list(Players.objects.filter(team_serial_id=team_serial))

    for player in players:
        ratings = PlayerPositionRating.objects.filter(player=player).select_related('position')
        player.ratings = ratings
        player.is_pitcher = any(r.position.name == 'P' for r in ratings if r.position)
        player.primary_position = get_primary_position(ratings)
        player.offense = player.offense or ''
        player.defense = get_defense_string(ratings)
        player.pitching = get_pitching_string(player)

    pitchers = [p for p in players if p.is_pitcher]
    pitchers.sort(key=lambda p: parse_pitching_sort_key(p.pitching))

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Name", "B-T", "Offense", "Defense", "Pitching"])

    for p in pitchers:
        name = f"{p.first_name} {p.last_name}"
        hand = f"{p.bats}-{p.throws}"
        writer.writerow([name, hand, p.offense, p.defense, p.pitching])

    response = HttpResponse(output.getvalue(), content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{team.team_name}_{team.first_name}_pitchers.csv"'
    return response
