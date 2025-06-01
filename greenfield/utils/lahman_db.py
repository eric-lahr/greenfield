# greenfield/utils/lahman_db.py

import psycopg2
from psycopg2.extras import RealDictCursor
from players.models import Players
from teams.models import Teams

def get_lahman_connection():
    return psycopg2.connect(
        dbname="lahman",
        user="kershaw",
        password="24champions",
        host="localhost",
        port="5432"
    )

def get_players_by_team_and_year(year, team_name):
    query = """
        SELECT p.playerID, p.nameFirst, p.nameLast, SUM(b.G) as games_played
        FROM people p
        JOIN batting b ON p.playerID = b.playerID
        WHERE b.yearID = %s AND b.teamID = %s
        GROUP BY p.playerID, p.nameFirst, p.nameLast
        HAVING SUM(b.G) >= 10
        ORDER BY games_played DESC;
    """
    with get_lahman_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, [year, team_name])
            return cur.fetchall()

def get_teamID_from_name(year, team_name):
    query = """
        SELECT teamID
        FROM teams
        WHERE yearID = %s AND name ILIKE %s
        LIMIT 1;
    """
    with get_lahman_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, [year, f"%{team_name}%"])
            result = cur.fetchone()
            return result[0] if result else None

def get_rated_player_status(year, team_name, lahman_players):
    try:
        team = Teams.objects.get(first_name=str(year), team_name__iexact=team_name)
    except Teams.DoesNotExist:
        return {p['playerid']: False for p in lahman_players}

    rated_ids = set(
        Players.objects.filter(
            year=year,
            team_serial=team.id
        ).values_list('first_name', 'last_name')
    )

    # Create a dict of playerid → status
    status_lookup = {}
    for player in lahman_players:
        is_rated = (player['namefirst'], player['namelast']) in rated_ids
        status_lookup[player['playerid']] = 'rated' if is_rated else ''
    return status_lookup



# You can add more queries here later...
# def get_team_stats(year, team_id): ...
# def get_stadium_info(stadium_id): ...
