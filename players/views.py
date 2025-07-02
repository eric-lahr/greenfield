from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.conf import settings
from collections import OrderedDict
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
    pitcher_control_number, def_rating,
    get_superior_rating, get_catcher_throw_rating
)
from greenfield.utils.all_time import all_time_team_finder, get_franchise_display_map
from .models import Players, Position, PlayerPositionRating  # Your Greenfield models
from teams.models import Teams
from django.db.models import Q
from django.contrib import messages
from .forms import (
    PlayerForm, PlayerPositionRatingFormSet, PlayerEditForm,
    PlayerPositionRatingModelFormset, CustomPlayerStatsForm,
    PictureFormSet
)
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

    if year and team_name and year != 'All Time':
        # Convert 'Pirates' -> 'PIT'
        team_id = get_teamID_from_name(year, team_name)
        if not team_id:
            return render(request, 'players/create_players_from_team.html', {
                'error': f"Could not find team ID for {team_name} in {year}.",
                'searched': True
            })

        # FIXED: use team_id instead of team_name
        if year == 'All Time':
            return redirect(reverse('players:search_career_players'))
        else:
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


def create_custom_player(request):
    if request.method == 'POST':
        form = CustomPlayerStatsForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            year = data['year']
            team_name = data['team_name']
            greenfield_dict = {
                'year': year,
                'team_name': team_name,
                'first_name': data['first_name'],
                'last_name': data['last_name'],
                'bats': data['bats'],
                'throws': data['throws'],
            }

            # Calculate PA
            SF = data.get('SF') or 0
            SH = data.get('SH') or 0
            PA = data['AB'] + data['BB'] + data['HBP'] + SF + SH

            # Batting ratings
            if PA > 5:
                off_rate_str = (
                    clutch(data['RBI'], data['G']) +
                    hit_letter(data['H'], data['AB']) +
                    str(hr_3b_number(data['HR'], data['triples'], data['H'])) +
                    (speed(data['SB'], data['H'], data['BB'], data['HBP'], data['doubles'], data['triples'], data['HR']) if data['SB'] > 0 else '') +
                    ' ' + batter_bb_k(data['BB'], data['SO'], data['HBP'], PA)
                )
                prob_hit_num = probable_hit_number(data['H'], PA)
            else:
                off_rate_str = 'G+ [n-36]'
                prob_hit_num = 66

            greenfield_dict.update({
                'offense': off_rate_str,
                'bat_prob_hit': prob_hit_num
            })

            # Pitching ratings
            if data['BFP']:
                ip_whole = data['IP_outs'] // 3
                ip_rem = data['IP_outs'] % 3
                ip = ip_whole + (0.333 if ip_rem == 1 else 0.667 if ip_rem == 2 else 0)

                if not data['BAOpp']:
                    data['BAOpp'] = round(int(data['HA']) / (int(data['BFP']) - int(data['BB_pitch']) - int(data['HBP_pitch'])), 3)

                pitch_string = (
                    gopher(data['HRA'], data['HA']) +
                    pitch_letter(data['BAOpp']) +
                    innings_of_effectiveness(data['GP'], ip) +
                    ' ' + pitcher_bb_k_hbp(data['BFP'], data['BB_pitch'], data['SO_pitch'], data['HBP_pitch']) +
                    ' ' + wild_pitch(data['WP'])
                )
                pitch_ctl = pitcher_control_number(data['BB_pitch'], data['HBP_pitch'], data['HA'], data['BFP'])
                pitch_ph = probable_hit_number(data['HA'], data['BFP'])
            else:
                pitch_string = ''
                pitch_ctl = ''
                pitch_ph = ''

            greenfield_dict.update({
                'pitching': pitch_string,
                'pitch_ctl': pitch_ctl,
                'pitch_prob_hit': pitch_ph
            })

            # Fielding
            position_ratings = []
            for i in [1, 2, 3, 4, 5]:
                pos = data.get(f'POS{i}')
                if pos:
                    po = data.get(f'POS{i}_PO') or 0
                    a = data.get(f'POS{i}_A') or 0
                    e = data.get(f'POS{i}_E') or 0
                    g = data.get(f'POS{i}_G') or 0
                    fpct = round((po + a) / (po + a + e), 3) if (po + a + e) > 0 else 0.000
                    superior = get_superior_rating(pos, fpct, int(year))
                    dr = def_rating(pos, a, po, g)
                    cr = get_catcher_throw_rating(data.get('CS') or 0, data.get('SBA') or 0)
                    position_ratings.append((pos, g, superior + dr + cr))

            position_ratings.sort(key=lambda x: x[1], reverse=True)
            greenfield_dict['positions'] = OrderedDict((pos, rating) for pos, g, rating in position_ratings)

            request.session['greenfield_data'] = greenfield_dict
            return redirect('players:create_record')  # or 'players:review_custom_player' if previewing

    else:
        form = CustomPlayerStatsForm()

    return render(request, 'players/create_custom_player.html', {'form': form})


def search_career_players(request):
    players = []
    first_name = last_name = ""

    if request.method == "GET":
        first_name = request.GET.get("first_name", "").strip()
        last_name = request.GET.get("last_name", "").strip()

        if first_name or last_name:
            conn = get_lahman_connection()
            cursor = conn.cursor()

            # Base query
            query = """
                SELECT p.playerID, p.nameFirst, p.nameLast, p.nameGiven,
                    MIN(stats.yearID) AS first_year,
                    MAX(stats.yearID) AS last_year,

                    (
                        SELECT t.name
                        FROM (
                            SELECT teamID, SUM(G) as total_games
                            FROM (
                                SELECT teamID, G FROM Batting WHERE playerID = p.playerID
                                UNION ALL
                                SELECT teamID, G FROM Pitching WHERE playerID = p.playerID
                                UNION ALL
                                SELECT teamID, G FROM Fielding WHERE playerID = p.playerID
                            ) AS appearances
                            GROUP BY teamID
                            ORDER BY total_games DESC
                            LIMIT 1
                        ) AS top_team
                        JOIN Teams t ON t.teamID = top_team.teamID
                        ORDER BY t.yearID DESC
                        LIMIT 1
                    ) AS primary_team,

                    (
                        SELECT POS
                        FROM Fielding f
                        WHERE f.playerID = p.playerID
                        GROUP BY POS
                        ORDER BY SUM(G) DESC
                        LIMIT 1
                    ) AS primary_position

                FROM People p
                JOIN (
                    SELECT playerID, yearID FROM Batting
                    UNION
                    SELECT playerID, yearID FROM Pitching
                    UNION
                    SELECT playerID, yearID FROM Fielding
                ) stats USING(playerID)
            """

            # WHERE clause and params
            where_clauses = []
            params = []

            if first_name:
                where_clauses.append("LOWER(p.nameFirst) ILIKE %s")
                params.append(f"%{first_name.lower()}%")

            if last_name:
                where_clauses.append("LOWER(p.nameLast) ILIKE %s")
                params.append(f"%{last_name.lower()}%")

            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)

            query += """
                GROUP BY p.playerID, p.nameFirst, p.nameLast, p.nameGiven
                ORDER BY p.nameGiven
            """

            cursor.execute(query, params)
            players = cursor.fetchall()
            conn.close()

    return render(request, "players/career_search.html", {
        "players": players,
        "first_name": first_name,
        "last_name": last_name,
    })


def rate_player_career(request, player_id):
    greenfield_dict = {'year': 'All Time'}

    with get_lahman_connection() as conn:
        with conn.cursor() as cursor:
            # Player names
            cursor.execute("""
                SELECT nameFirst, nameLast, nameGiven,
                EXTRACT(YEAR FROM debut)
                FROM People
                WHERE playerID = %s
            """, (player_id,))
            result = cursor.fetchone()
            name_first, name_last, name_given, debut = result
            print(debut)
            greenfield_dict['first_name'] = name_first
            greenfield_dict['last_name'] = name_last
            greenfield_dict['debut_year'] = int(debut)

            # Bats / Throws
            cursor.execute("""
                SELECT bats, throws
                FROM People
                WHERE playerID = %s
            """, (player_id,))
            bats_throws = cursor.fetchone()
            bats = bats_throws[0] if bats_throws else None
            throws = bats_throws[1] if bats_throws else None

            # Batting totals
            cursor.execute("""
                SELECT
                    SUM(H), SUM(AB), SUM(HR), SUM("3B"), SUM(BB), SUM(HBP),
                    SUM(SB), SUM("2B"), SUM(RBI), SUM(SO), SUM(G), SUM(SF),
                    SUM(SH)
                FROM Batting
                WHERE playerID = %s
            """, (player_id,))
            batting = cursor.fetchone()

            # Pitching totals
            cursor.execute("""
                SELECT
                    SUM(BFP), SUM(H), SUM(BB), SUM(HBP), SUM(SH), SUM(SF),
                    SUM(G), SUM(IPouts), SUM(SO), SUM(HR), SUM(WP),
                    COUNT(DISTINCT yearID) AS seasons
                FROM Pitching
                WHERE playerID = %s
            """, (player_id,))
            pitching = cursor.fetchone()

            # Fielding summary by position
            cursor.execute("""
                SELECT POS, SUM(PO), SUM(A), SUM(E), SUM(G)
                FROM Fielding
                WHERE playerID = %s
                GROUP BY POS
                HAVING SUM(G) >= 6
                ORDER BY SUM(G) DESC
            """, (player_id,))
            fielding = cursor.fetchall()

            # Catcher SB/CS
            cursor.execute("""
                SELECT SUM(SB), SUM(CS)
                FROM Fielding
                WHERE playerID = %s AND POS = 'C'
            """, (player_id,))
            sb_cs = cursor.fetchone()
            sba_total = sb_cs[0] or 0
            cs_total = sb_cs[1] or 0

            # OF Splits
            of_stats = [row for row in fielding if row[0] == 'OF']
            non_of_stats = [row for row in fielding if row[0] != 'OF']
            of_splits = []

            if of_stats:
                cursor.execute("""
                    SELECT POS, SUM(PO), SUM(A), SUM(E), SUM(G)
                    FROM FieldingOFsplit
                    WHERE playerID = %s
                    GROUP BY POS
                    HAVING SUM(G) >= 15
                    ORDER BY SUM(G) DESC
                """, (player_id,))
                of_splits = cursor.fetchall()

            if of_splits:
                fielding = non_of_stats + of_splits
            else:
                fielding = non_of_stats + of_stats
            fielding.sort(key=lambda row: row[4], reverse=True)

            # Get top franchise by appearances
            cursor.execute("""
                SELECT franchID, SUM(games) as total_games
                FROM (
                    SELECT t.franchID, b.G AS games
                    FROM Batting b
                    JOIN Teams t ON b.teamID = t.teamID AND b.yearID = t.yearID
                    WHERE b.playerID = %s

                    UNION ALL

                    SELECT t.franchID, p.G AS games
                    FROM Pitching p
                    JOIN Teams t ON p.teamID = t.teamID AND p.yearID = t.yearID
                    WHERE p.playerID = %s

                    UNION ALL

                    SELECT t.franchID, f.G AS games
                    FROM Fielding f
                    JOIN Teams t ON f.teamID = t.teamID AND f.yearID = t.yearID
                    WHERE f.playerID = %s
                ) AS combined
                GROUP BY franchID
                ORDER BY total_games DESC
                LIMIT 1
            """, (player_id, player_id, player_id))

            top_team = cursor.fetchone()
            
            print(f"Top franchise: {top_team}")

            franchise_id = top_team[0] if top_team else 'UNK'
            display_map = get_franchise_display_map()
            franchise_display = display_map.get(franchise_id, "Unknown Team")

            greenfield_dict['team_name'] = franchise_display
            print(f"Final franchise name: {franchise_display}")

    # --- Sherco Ratings Calculations ---

    # Batting block
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
        'RBI': batting[8],
        'SO': batting[9],
        'SF': batting[11],
        'SH': batting[12]
    }

    for key in ['SH', 'SF']:
        if batting_stats[key] is None:
            batting_stats[key] = 0

    pa = sum([
        batting_stats['AB'] or 0,
        batting_stats['BB'] or 0,
        batting_stats['HBP'] or 0,
        batting_stats['SF'] or 0,
        batting_stats['SH'] or 0
    ])
    batting_stats['PA'] = pa

    if pa > 5:
        off_rate_str = (
            clutch(batting_stats['RBI'], batting_stats['G']) +
            hit_letter(batting_stats['H'], batting_stats['AB']) +
            str(hr_3b_number(batting_stats['HR'], batting_stats['3B'], batting_stats['H'])) +
            (speed(
                batting_stats['SB'], batting_stats['H'], batting_stats['BB'], batting_stats['HBP'],
                batting_stats['2B'], batting_stats['3B'], batting_stats['HR']
            ) if batting_stats['SB'] else '') + ' ' +
            batter_bb_k(batting_stats['BB'], batting_stats['SO'], batting_stats['HBP'], batting_stats['PA'])
        )
        prob_hit_num = probable_hit_number(batting_stats['H'], batting_stats['PA'])
    else:
        off_rate_str, prob_hit_num = 'G+ [n-36]', 66

    greenfield_dict.update({
        'offense': off_rate_str,
        'bat_prob_hit': prob_hit_num,
        'bats': bats,
        'throws': throws
    })

    # Pitching block
    pitching_stats = {
        'BF': pitching[0],
        'HA': pitching[1],
        'BB': pitching[2] if pitching[2] is not None else 0,
        'HBP': pitching[3] if pitching[3] is not None else 0,
        'G': pitching[6],
        'IPOuts': pitching[7],
        'SO': pitching[8],
        'HRA': pitching[9],
        'WP': pitching[10]
    }

    if pitching_stats['BF']:
        ip_whole = pitching_stats['IPOuts'] // 3
        ip_rem = pitching_stats['IPOuts'] % 3
        half_inn = {1: .333, 2: .667}.get(ip_rem, 0)
        pitching_stats['IP'] = ip_whole + half_inn
        pitching_stats['SH'] = pitching[4] if pitching[4] is not None else 0
        pitching_stats['SF'] = pitching[5] if pitching[5] is not None else 0
        print(pitching_stats['SF'], pitching_stats['SH'])
    else:
        pitching_stats['IP'] = 0

    if pitching_stats['BF']:
        OppAB = (
            (pitching_stats['BF'] - pitching_stats['BB'] - pitching_stats['HBP']) - 
            (pitching_stats['SH'] - pitching_stats['SF'])
            )
        if OppAB > 0:
            BAOpp = round(pitching_stats['HA'] / OppAB, 3)
        else: BAOpp = .4
        wp_avg = round(pitching_stats['WP'] / pitching[11])
        pitch_string = (
            gopher(pitching_stats['HRA'], pitching_stats['HA']) +
            pitch_letter(BAOpp) +
            innings_of_effectiveness(pitching_stats['G'], pitching_stats['IP']) + ' ' +
            pitcher_bb_k_hbp(pitching_stats['BF'], pitching_stats['BB'], pitching_stats['SO'], pitching_stats['HBP']) + ' ' +
            wild_pitch(wp_avg)
        )
        pcn = pitcher_control_number(pitching_stats['BB'], pitching_stats['HBP'], pitching_stats['HA'], pitching_stats['BF'])
        pitch_ph = probable_hit_number(pitching_stats['HA'], pitching_stats['BF'])
    else:
        pitch_string, pcn, pitch_ph, BAOpp = '', '', '', 0

    greenfield_dict.update({
        'pitching': pitch_string,
        'pitch_ctl': pcn,
        'pitch_prob_hit': pitch_ph
    })

    # Fielding ratings
    position_ratings = []
    for pos, po, a, e, g in fielding:
        successes = po + a
        chances = po + a + e
        fpct = round(successes / chances, 3) if chances > 0 else 0.000
        superior = get_superior_rating(pos, fpct, greenfield_dict['debut_year'])
        dr = def_rating(pos, a, po, g)
        cr = get_catcher_throw_rating(cs_total, sba_total)
        position_ratings.append((pos, g, superior + dr + cr))

    # Sort by descending games played, then store in ordered dict
    position_ratings.sort(key=lambda x: x[1], reverse=True)
    ordered_position_dict = OrderedDict((pos, rating) for pos, g, rating in position_ratings)

    greenfield_dict['positions'] = ordered_position_dict
    request.session['greenfield_data'] = greenfield_dict

    context = {
        'playerID': player_id,
        'year': 'All Time',
        'team_name': franchise_display,
        'batting': batting,
        'pitching': pitching,
        'fielding': fielding,
        'sb': sba_total,
        'cs': cs_total,
        'name_first': name_first,
        'name_last': name_last,
        'greenfield': greenfield_dict,
        'pa': pa,
        'baopp': BAOpp,
        'career_mode': True,
    }
    return render(request, 'players/rate_player.html', context)


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
                HAVING SUM(G) >= 1
                ORDER BY SUM(G) DESC
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
                    HAVING SUM(G) >= 5
                    ORDER BY SUM(G) DESC
                """, (playerID, year))
                of_splits = cursor.fetchall()

            if of_splits:
                fielding = non_of_stats + of_splits
            else:
                fieldimng = non_of_stats + of_stats
            fielding.sort(key=lambda row: row[4], reverse=True)

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

    # Fielding ratings
    position_ratings = []
    for pos, po, a, e, g in fielding:
        successes = po + a
        chances = po + a + e
        fpct = round(successes / chances, 3) if chances > 0 else 0.000
        superior = get_superior_rating(pos, fpct, greenfield_dict['year'])
        dr = def_rating(pos, a, po, g)
        cr = get_catcher_throw_rating(cs_total, sba_total)
        position_ratings.append((pos, g, superior + dr + cr))

    # Sort by descending games played, then store in ordered dict
    position_ratings.sort(key=lambda x: x[1], reverse=True)
    ordered_position_dict = OrderedDict((pos, rating) for pos, g, rating in position_ratings)

    greenfield_dict['positions'] = ordered_position_dict
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

def select_team_for_edit(request):
    teams = Teams.objects.all().order_by('first_name', 'team_name')
    selected_team_id = request.GET.get('team_id')
    players = []
    if selected_team_id:
        players = Players.objects.filter(team_serial_id=selected_team_id).order_by('last_name', 'first_name')
    return render(request, 'players/select_team_for_edit.html', {
        'teams': teams,
        'players': players,
        'selected_team_id': int(selected_team_id) if selected_team_id else None,
    })


def edit_player(request, player_id):
    player = get_object_or_404(Players, pk=player_id)
    position_ratings = PlayerPositionRating.objects.filter(player=player)

    if request.method == 'POST':
        player_form = PlayerEditForm(request.POST, request.FILES, instance=player)
        formset = PlayerPositionRatingModelFormset(request.POST, queryset=position_ratings)
        picture_formset = PictureFormSet(request.POST, request.FILES, instance=player)

        if player_form.is_valid() and formset.is_valid() and picture_formset.is_valid():
            player_form.save()
            formset.save()
            picture_formset.save()
            return redirect('players:select_team_for_edit')
    else:
        player_form = PlayerEditForm(instance=player)
        formset = PlayerPositionRatingModelFormset(queryset=position_ratings)
        picture_formset = PictureFormSet(instance=player)

    return render(request, 'players/edit_player.html', {
        'player_form': player_form,
        'formset': formset,
        'picture_formset': picture_formset,
        'player': player,
    })


def delete_player(request, player_id):
    player = get_object_or_404(Players, pk=player_id)

    if request.method == 'POST':
        player_name = f"{player.first_name} {player.last_name} ({player.year})"
        player.delete()
        messages.success(request, f"{player_name} has been deleted.")

        year = request.GET.get('year', '')
        team_name = request.GET.get('team_name', '')

        if year and team_name:
            params = urlencode({'year': year, 'team_name': team_name})
            return redirect(f"{reverse('players:create_players_from_team')}?{params}")
        else:
            return redirect('players:search_career_players')

    return render(request, 'players/confirm_delete.html', {
        'player': player
    })


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

                for idx, form in enumerate(rating_formset):
                    if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                        PlayerPositionRating.objects.create(
                            player=player,
                            position=form.cleaned_data['position'],
                            rating=form.cleaned_data['rating'],
                            position_order=idx  # 👈 assign order explicitly
                        )

                messages.success(request, "Player and position ratings saved successfully.")
                print(f"Created player {player.first_name} {player.last_name} (year={player.year}) for team ID {team.serial}")

            # Clean up session
            request.session.pop('greenfield_data', None)

            if year == 'All Time':
                return redirect(reverse('players:search_career_players'))
            else:
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