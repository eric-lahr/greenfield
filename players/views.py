from django.shortcuts import render
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

def rate_player(request, playerID, year, team_name):
    greenfield_dict = {'year': year}
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
                    SUM(SB), SUM("2B"), SUM(RBI), SUM(SO), SUM(G)
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
                HAVING SUM(G) >= 15
            """, (playerID, year))
            fielding = cursor.fetchall()
            # field ex. = [('2B', 160, 206, 14), ('3B', 12, 26, 5), ('OF', 21, 1, 2)]

            # SB and CS from Fielding (catcher stats)
            cursor.execute("""
                SELECT SUM(SB), SUM(CS)
                FROM Fielding
                WHERE playerID = %s AND yearID = %s
            """, (playerID, year))
            sb_cs = cursor.fetchone()

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
        'bats': bats,
        'SB': batting[6]
    }

    pa = batting_stats['AB'] + batting_stats['BB'] + batting_stats['HBP']
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
        'WP': pitching[9],
        'throws': throws
    }

    if pitching_stats['BF']: 
        ip_whole = pitching_stats['IPOuts'] // 3
        ip_rem = pitching_stats['IPOuts'] % 3
        if ip_rem == 1: half_inn = .333
        elif ip_rem == 2: half_inn = .667
        else: half_inn = 0
        pitching_stats['IP'] = ip_whole + half_inn
    else: pitching_stats['IP'] = 0

    # get sherco ratings - offense
    if batting_stats['PA'] > 0:
        bat_clutch = clutch(batting_stats['RBI'], batting_stats['G'])
        bat_letter = hit_letter(batting_stats['H'], batting_stats['AB'])
        hr_num = hr_3b_number(batting_stats['HR'], batting_stats['3B'], batting_stats['H'])
        spd_rate = speed(batting_stats['SB'], batting_stats['PA'])
        walk_so = batter_bb_k(batting_stats['BB'], batting_stats['SO'], batting_stats['HBP'], batting_stats['PA'])
        prob_hit_num = probable_hit_number(batting_stats['H'], batting_stats['PA'])

        off_rate_str = bat_clutch+bat_letter+str(hr_num)+spd_rate+' '+walk_so
    else: off_rate_str, probable_hit_num = '', 66
    greenfield_dict['offense'] = off_rate_str
    greenfield_dict['bat_prob_hit'] = prob_hit_num

    # get sherco ratings - pitching
    if pitching_stats['BF'] != None:
        gopher = gopher(pitching_stats['HR'], pitching_stats['H'])
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
        pitch_string = gopher + pitch_grade + inn_of_eff + ' ' + walk_so + ' ' + wld_pch
        pitch_ph = probable_hit_num(pitching_stats['H'], pitching_stats['BF'], pitching_stats['PA'])
    else: pitch_string, pcn, pitch_ph = '', '', ''
    greenfield_dict['pitching'] = pitch_string
    greenfield_dict['pitch_ctl'] = pcn
    greenfield_dict['pitch_prob_hit'] = pitch_ph

    position_dict = {}
    for position in fielding:
        # [('2B', 160, 206, 14), ('3B', 12, 26, 5), ('OF', 21, 1, 2)]
        fielding_stats = {
            'G': position[4],
            'POS': position[0],
            'PO': position[1],
            'A': position[2],
            'E': position[3],
            'CS': sb_cs[1],
            'SBA': sb_cs[0]
        }

        successes = fielding_stats['PO'] + fielding_stats['A']
        chances = fielding_stats['PO'] + fielding_stats['A'] + fielding_stats['E']
        fpct = round(successes / chances, 3)
        fielding_stats['PCT'] = fpct
        dr = def_rating(
            fielding_stats['POS'], fielding_stats['PCT'], int(year),
            fielding_stats['A'], fielding_stats['PO'], fielding_stats['G'],
            fielding_stats['CS'], fielding_stats['SBA']
        )

        #position_dict[fielding['POS']] = dr
        print(dr)

    greenfield_dict['positions'] = position_dict
    print(greenfield_dict)

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
    }
    return render(request, 'players/rate_player.html', context)

def edit_players(request):
    return render(request, 'players/edit_player.html')
