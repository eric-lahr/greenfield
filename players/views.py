from django.shortcuts import render, redirect
from django.urls import reverse
from django.conf import settings
from psycopg2.extras import RealDictCursor
from greenfield.utils.lahman_db import (
    get_players_by_team_and_year,
    get_teamID_from_name,
    get_rated_player_status,
    get_player_season_stats,
    get_lahman_connection
    )
from greenfield.utils.sherco import (
    clutch, hit_letter, hr_3b_number,
    speed, batter_bb_k, probable_hit_number,
    pitch_letter, innings_of_effectiveness,
    pitcher_bb_k_hbp, wild_pitch, gopher,
    pitcher_control_number, def_rating
)
from .models import Players, Position, PlayerPositionRating  # Your Greenfield models
from teams.models import Teams
from django.db.models import Q
from django.contrib import messages
from .forms import PlayerForm, PlayerPositionRatingFormSet
from django.forms import modelformset_factory
from django.contrib import messages
from django.db import transaction
from urllib.parse import urlencode

def create_players_from_team(request):
    # Try to get from either GET or POST
    year = request.GET.get('year') or request.POST.get('year')
    team_name = request.GET.get('team_name') or request.POST.get('team_name')

    if request.method == 'POST' and (not year or not team_name):
        return render(request, 'players/create_players_from_team.html', {
            'error': 'Please enter both fields.',
            'searched': True
        })

    if year and team_name:
        # Convert 'Pirates' -> 'PIT'
        team_id = get_teamID_from_name(year, team_name)
        if not team_id:
            return render(request, 'players/create_players_from_team.html', {
                'error': f"Could not find team ID for {team_name} in {year}.",
                'searched': True
            })

        # FIXED: use team_id instead of team_name
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

    # If no year/team_name provided, show the form
    return render(request, 'players/create_players_from_team.html')


def create_career_player(request):
    return render(request, 'players/create_custom_player.html')


def view_player(request, playerID):
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM People WHERE playerID = %s", [playerID])
        row = cursor.fetchone()
    # Render with a simple template that displays the player info

def rate_player(request, playerID, year, team_name):
    greenfield_dict = {'year': year, 'team_name': team_name}
    name_first = request.GET.get('namefirst', 'Unknown')
    name_last = request.GET.get('namelast', 'Player')
    greenfield_dict['first_name'] = name_first
    greenfield_dict['last_name'] = name_last

    with get_lahman_connection() as conn:

        with conn.cursor() as cursor:
            # Bats/Throws info
            cursor.execute("""
                SELECT bats, throws
                FROM People
                WHERE playerID = %s
            """, (playerID,))
            bats_throws = cursor.fetchone()
            bats = bats_throws[0] if bats_throws else None
            throws = bats_throws[1] if bats_throws else None

        with conn.cursor() as cursor:
            # Batting stats
            cursor.execute("""
                SELECT
                    SUM(H), SUM(AB), SUM(HR), SUM("3B"), SUM(BB), SUM(HBP),
                    SUM(SB), SUM("2B"), SUM(RBI), SUM(SO), SUM(G), SUM(SF),
                    SUM(SH)
                FROM Batting
                WHERE playerID = %s AND yearID = %s
            """, (playerID, year))
            batting = cursor.fetchone()

            # Pitching stats
            cursor.execute("""
                SELECT
                    SUM(BFP), SUM(H), SUM(BB), SUM(HBP), SUM(BAOpp),
                    SUM(G), SUM(IPouts), SUM(SO), SUM(HR), SUM(WP)
                FROM Pitching
                WHERE playerID = %s AND yearID = %s
            """, (playerID, year))
            pitching = cursor.fetchone()

            # Fielding summary by position (POS)
            cursor.execute("""
                SELECT POS, SUM(PO), SUM(A), SUM(E), SUM(G)
                FROM Fielding
                WHERE playerID = %s AND yearID = %s
                GROUP BY POS
                HAVING SUM(G) >= 6
            """, (playerID, year))
            fielding = cursor.fetchall()
            # field ex. = [('2B', 160, 206, 14), ('3B', 12, 26, 5), ('OF', 21, 1, 2)]

            # SB and CS from Fielding (catcher stats)
            cursor.execute("""
                SELECT SUM(SB), SUM(CS)
                FROM Fielding
                WHERE playerID = %s AND yearID = %s AND POS = 'C'
            """, (playerID, year))
            sb_cs = cursor.fetchone()
            sba_total = sb_cs[0] or 0
            cs_total = sb_cs[1] or 0

            # of_splits = []
            of_stats = [row for row in fielding if row[0] == 'OF']
            non_of_stats = [row for row in fielding if row[0] != 'OF']
            of_splits = []

            if of_stats:
                cursor.execute("""
                    SELECT POS, SUM(PO), SUM(A), SUM(E), SUM(G)
                    FROM FieldingOFsplit
                    WHERE playerID = %s AND yearID = %s
                    GROUP BY POS
                    HAVING SUM(G) >= 15
                """, (playerID, year))
                of_splits = cursor.fetchall()

            if of_splits:
                fielding = non_of_stats + of_splits
            else:
                fieldimng = non_of_stats + of_stats

    batting_stats = {
        'G': batting[10],
        'H': batting[0],
        'AB': batting[1],
        'HR': batting[2],
        '2B': batting[7],
        '3B': batting[3],
        'BB': batting[4],
        'HBP': batting[5],
        'SB': batting[6],
        '2B': batting[7],
        'RBI': batting[8],
        'SO': batting[9],
        'SB': batting[6],
        'SF': batting[11],
        'SH': batting[12]
    }

    if batting_stats['SH'] == None: batting_stats['SH'] = 0
    if batting_stats['SF'] == None: batting_stats['SF'] = 0
    pa = batting_stats['AB'] + batting_stats['BB'] + batting_stats['HBP'] + batting_stats['SF'] + batting_stats['SH']
    batting_stats['PA'] = pa

    pitching_stats = {
        'BF': pitching[0],
        'HA': pitching[1],
        'BB': pitching[2],
        'HBP': pitching[3],
        'BAOpp': pitching[4],
        'G': pitching[5],
        'IPOuts': pitching[6],
        'SO': pitching[7],
        'HRA': pitching[8],
        'WP': pitching[9]
    }

    if pitching_stats['BF']: 
        ip_whole = pitching_stats['IPOuts'] // 3
        ip_rem = pitching_stats['IPOuts'] % 3
        if ip_rem == 1: half_inn = .333
        elif ip_rem == 2: half_inn = .667
        else: half_inn = 0
        pitching_stats['IP'] = ip_whole + half_inn
        print(pitching_stats['IP'])
    else: pitching_stats['IP'] = 0

    # get sherco ratings - offense
    if batting_stats['PA'] > 5:
        bat_clutch = clutch(batting_stats['RBI'], batting_stats['G'])
        bat_letter = hit_letter(batting_stats['H'], batting_stats['AB'])
        hr_num = hr_3b_number(batting_stats['HR'], batting_stats['3B'], batting_stats['H'])
        if batting_stats['SB'] > 0:
            spd_rate = speed(
                batting_stats['SB'], batting_stats['H'], batting_stats['BB'], batting_stats['HBP'],
                batting_stats['2B'], batting_stats['3B'], batting_stats['HR']
                )
        else: spd_rate = ''
        walk_so = batter_bb_k(batting_stats['BB'], batting_stats['SO'], batting_stats['HBP'], batting_stats['PA'])
        prob_hit_num = probable_hit_number(batting_stats['H'], batting_stats['PA'])

        off_rate_str = bat_clutch+bat_letter+str(hr_num)+spd_rate+' '+walk_so
    else: off_rate_str, prob_hit_num = 'G+ [n-36]', 66 

    greenfield_dict['offense'] = off_rate_str
    greenfield_dict['bat_prob_hit'] = prob_hit_num
    greenfield_dict['bats'] = bats
    greenfield_dict['throws'] = throws

    # get sherco ratings - pitching
    if pitching_stats['BF'] != None:
        gopher_ball = gopher(pitching_stats['HRA'], pitching_stats['HA'])
        pitch_grade = pitch_letter(pitching_stats['BAOpp'])
        inn_of_eff = innings_of_effectiveness(pitching_stats['G'], pitching_stats['IP'])
        walk_so = pitcher_bb_k_hbp(
            pitching_stats['BF'], pitching_stats['BB'],
            pitching_stats['SO'], pitching_stats['HBP']
            )
        wld_pch = wild_pitch(pitching_stats['WP'])
        pcn = pitcher_control_number(
            pitching_stats['BB'], pitching_stats['HBP'],
            pitching_stats['HA'], pitching_stats['BF']
            )
        pitch_string = gopher_ball + pitch_grade + inn_of_eff + ' ' + walk_so + ' ' + wld_pch
        pitch_ph = probable_hit_number(pitching_stats['HA'], pitching_stats['BF'])
    else: pitch_string, pcn, pitch_ph = '', '', ''
    greenfield_dict['pitching'] = pitch_string
    greenfield_dict['pitch_ctl'] = pcn
    greenfield_dict['pitch_prob_hit'] = pitch_ph

    position_dict = {}
    for position, po, a, e, g in fielding:
        # [('2B', 160, 206, 14), ('3B', 12, 26, 5), ('OF', 21, 1, 2)]
        fielding_stats = {
            'G': g, #position[4],
            'POS': position, #position[0],
            'PO': po, 
            'A': a, #position[2],
            'E': e, #position[3],
            'CS': sba_total,
            'SBA': cs_total
        }

        successes = po + a
        chances = po + a + e #fielding_stats['PO'] + fielding_stats['A'] + fielding_stats['E']
        fpct = round(successes / chances, 3) if chances > 0 else 0.000
        fielding_stats['PCT'] = fpct

        dr = def_rating(
            fielding_stats['POS'], fielding_stats['PCT'], int(year),
            fielding_stats['A'], fielding_stats['PO'], fielding_stats['G'],
            fielding_stats['CS'], fielding_stats['SBA']
        )

        position_dict[position] = dr

    greenfield_dict['positions'] = position_dict
    request.session['greenfield_data'] = greenfield_dict

    context = {
        'playerID': playerID,
        'year': year,
        'team_name': team_name,
        'batting': batting,
        'pitching': pitching,
        'fielding': fielding,
        'sb': sb_cs[0] or 0,
        'cs': sb_cs[1] or 0,
        'name_first': name_first,
        'name_last': name_last,
        'greenfield': greenfield_dict,
        'pa': pa
    }
    return render(request, 'players/rate_player.html', context)

def edit_players(request):
    return render(request, 'players/edit_player.html')

# def create_record(request):
#     if request.method == 'POST' and 'bats' in request.POST:
#         year = request.POST.get('year')
#         team_name = request.POST.get('team_name')
#         name_first = request.POST.get('name_first')
#         name_last = request.POST.get('name_last')

#         # Step 1: Get or create team
#         team, created = Teams.objects.get_or_create(first_name=year, team_name=team_name)
#         if created:
#             messages.info(request, f"{year} {team_name} team created.")
#         else:
#             messages.info(request, f"{year} {team_name} team already exists.")

#         # Step 2: Check for existing player on this team/year
#         player_exists = Players.objects.filter(
#             first_name=name_first,
#             last_name=name_last,
#             year=year,
#             team_serial=team
#         ).exists()

#         if player_exists:
#             messages.error(request, f"{name_first} {name_last} already exists for {year} {team_name}.")
#             params = urlencode({'year': year, 'team_name': team_name})
#             return redirect(f"{reverse('players:create_players_from_team')}?{params}")

#         # Step 3: Handle submitted form and formset
#         player_form = PlayerForm(request.POST)
#         rating_formset = PlayerPositionRatingFormSet(request.POST)

#         if player_form.is_valid() and rating_formset.is_valid():
#             with transaction.atomic():
#                 player = player_form.save(commit=False)
#                 player.first_name = name_first
#                 player.last_name = name_last
#                 player.year = year
#                 player.team_serial = team
#                 player.save()

#                 for form in rating_formset:
#                     if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
#                         PlayerPositionRating.objects.create(
#                             player=player,
#                             position=form.cleaned_data['position'],
#                             rating=form.cleaned_data['rating']
#                         )

#                 messages.success(request, "Player and position ratings saved successfully.")

#             # Optional: clean up session
#             if 'greenfield_data' in request.session:
#                 del request.session['greenfield_data']

#             params = urlencode({'year': year, 'team_name': team_name})
#             return redirect(f"{reverse('players:create_players_from_team')}?{params}")

#         else:
#             messages.error(request, "Please fix the form errors and try again.")

#     else:
#         # GET method — preload form from session data
#         greenfield_dict = request.session.get('greenfield_data', {})

#         year = greenfield_dict.get('year', '')
#         team_name = greenfield_dict.get('team_name', '')
#         name_first = greenfield_dict.get('first_name', '')
#         name_last = greenfield_dict.get('last_name', '')

#         player_form = PlayerForm(initial={
#             'bats': greenfield_dict.get('bats', ''),
#             'throws': greenfield_dict.get('throws', ''),
#             'uni_num': '',
#             'offense': greenfield_dict.get('offense', ''),
#             'bat_prob_hit': greenfield_dict.get('bat_prob_hit', ''),
#             'pitching': greenfield_dict.get('pitching', ''),
#             'pitch_ctl': greenfield_dict.get('pitch_ctl', ''),
#             'pitch_prob_hit': greenfield_dict.get('pitch_prob_hit', ''),
#         })

#         # Prepare initial data for formset from dict (positions: {pos_name: rating})
#         positions_data = greenfield_dict.get('positions', {})
#         formset_initial = []
#         for pos_name, rating in positions_data.items():
#             pos_obj = Position.objects.filter(name=pos_name).first()
#             if pos_obj:
#                 formset_initial.append({
#                     'position': pos_obj.pk,
#                     'rating': rating
#                 })

#         rating_formset = PlayerPositionRatingFormSet(
#             initial=formset_initial
#         )

#     return render(request, 'players/create_record.html', {
#         'form': player_form,
#         'formset': rating_formset,
#         'year': year,
#         'team_name': team_name,
#         'name_first': name_first,
#         'name_last': name_last
#     })

def create_record(request):
    if request.method == 'POST' and 'confirm_save' in request.POST:
        # 🔁 Load fallback from session FIRST
        greenfield_dict = request.session.get('greenfield_data', {})
        print("SESSION DATA:", greenfield_dict)  # 🔍 Debug print

        # ✅ Use POST if available, else session
        year = str(request.POST.get('year') or greenfield_dict.get('year', ''))
        team_name = request.POST.get('team_name') or greenfield_dict.get('team_name', '')
        name_first = request.POST.get('name_first') or greenfield_dict.get('first_name', '')
        name_last = request.POST.get('name_last') or greenfield_dict.get('last_name', '')

        print(f"Creating or getting team: year='{year}' team_name='{team_name}'")
        team, created = Teams.objects.get_or_create(
            first_name=year,  # 💡 year stored as string
            team_name=team_name
        )
        if created:
            messages.info(request, f"{year} {team_name} team created.")
        else:
            messages.info(request, f"{year} {team_name} team already exists.")

        # Step 2: Check if player already exists
        player_exists = Players.objects.filter(
            first_name=name_first,
            last_name=name_last,
            year=year,
            team_serial=team
        ).exists()

        if player_exists:
            messages.error(request, f"{name_first} {name_last} already exists for {year} {team_name}.")
            params = urlencode({'year': year, 'team_name': team_name})
            return redirect(f"{reverse('players:create_players_from_team')}?{params}")

        # Step 3: Handle form + formset
        player_form = PlayerForm(request.POST)
        rating_formset = PlayerPositionRatingFormSet(request.POST)

        if player_form.is_valid() and rating_formset.is_valid():
            with transaction.atomic():
                player = player_form.save(commit=False)
                player.first_name = name_first
                player.last_name = name_last
                player.year = year
                player.team_serial = team  # ✅ link by object (Django knows to use PK)
                player.save()

                for form in rating_formset:
                    if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                        PlayerPositionRating.objects.create(
                            player=player,
                            position=form.cleaned_data['position'],
                            rating=form.cleaned_data['rating']
                        )

                messages.success(request, "Player and position ratings saved successfully.")
                print(f"Created player {player.first_name} {player.last_name} (year={player.year}) for team ID {team.serial}")

            # Clean up session
            request.session.pop('greenfield_data', None)

            params = urlencode({'year': year, 'team_name': team_name})
            return redirect(f"{reverse('players:create_players_from_team')}?{params}")
        else:
            messages.error(request, "Please fix the form errors and try again.")
    else:
        # GET — load initial form
        greenfield_dict = request.session.get('greenfield_data', {})
        year = str(greenfield_dict.get('year', ''))
        team_name = greenfield_dict.get('team_name', '')
        name_first = greenfield_dict.get('first_name', '')
        name_last = greenfield_dict.get('last_name', '')

        player_form = PlayerForm(initial={
            'bats': greenfield_dict.get('bats', ''),
            'throws': greenfield_dict.get('throws', ''),
            'uni_num': '',
            'offense': greenfield_dict.get('offense', ''),
            'bat_prob_hit': greenfield_dict.get('bat_prob_hit', ''),
            'pitching': greenfield_dict.get('pitching', ''),
            'pitch_ctl': greenfield_dict.get('pitch_ctl', ''),
            'pitch_prob_hit': greenfield_dict.get('pitch_prob_hit', ''),
        })

        formset_initial = []
        for pos_name, rating in greenfield_dict.get('positions', {}).items():
            pos_obj = Position.objects.filter(name=pos_name).first()
            if pos_obj:
                formset_initial.append({
                    'position': pos_obj.pk,
                    'rating': rating
                })

        rating_formset = PlayerPositionRatingFormSet(initial=formset_initial)

    return render(request, 'players/create_record.html', {
        'form': player_form,
        'formset': rating_formset,
        'year': year,
        'team_name': team_name,
        'name_first': name_first,
        'name_last': name_last
    })