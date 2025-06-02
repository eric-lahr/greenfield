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

def get_player_season_stats(player_id, year):
    stats = {
        'batting': defaultdict(int),
        'pitching': defaultdict(int),
        'fielding': defaultdict(lambda: defaultdict(int)),  # stats per position
    }

    with get_lahman_connection() as conn:
        with conn.cursor() as cur:
            # --- Batting ---
            cur.execute("""
                SELECT 
                    COALESCE(SUM(AB), 0), COALESCE(SUM(H), 0), COALESCE(SUM(HR), 0),
                    COALESCE(SUM("3B"), 0), COALESCE(SUM(BB), 0), COALESCE(SUM(HBP), 0),
                    COALESCE(SUM(SB), 0), COALESCE(SUM("2B"), 0), COALESCE(SUM(RBI), 0), 
                    COALESCE(SUM(SO), 0)
                FROM Batting
                WHERE playerID = %s AND yearID = %s
            """, (player_id, year))
            row = cur.fetchone()
            (
                stats['batting']['AB'], stats['batting']['H'], stats['batting']['HR'],
                stats['batting']['3B'], stats['batting']['BB'], stats['batting']['HBP'],
                stats['batting']['SB'], stats['batting']['2B'], stats['batting']['RBI'],
                stats['batting']['SO']
            ) = row

            # --- Pitching ---
            cur.execute("""
                SELECT 
                    COALESCE(SUM(BFP), 0), COALESCE(SUM(H), 0), COALESCE(SUM(BB), 0),
                    COALESCE(SUM(HBP), 0), COALESCE(SUM(BAOpp), 0), COALESCE(SUM(G), 0),
                    COALESCE(SUM(IPouts), 0), COALESCE(SUM(SO), 0), COALESCE(SUM(HR), 0)
                FROM Pitching
                WHERE playerID = %s AND yearID = %s
            """, (player_id, year))
            row = cur.fetchone()
            (
                stats['pitching']['BFP'], stats['pitching']['H'], stats['pitching']['BB'],
                stats['pitching']['HBP'], stats['pitching']['BAOpp'], stats['pitching']['G'],
                stats['pitching']['IPouts'], stats['pitching']['SO'], stats['pitching']['HR']
            ) = row

            # --- Fielding ---
            cur.execute("""
                SELECT POS, SUM(G) as games, 
                       COALESCE(SUM(PO), 0), COALESCE(SUM(A), 0), COALESCE(SUM(E), 0),
                       COALESCE(SUM(SB), 0), COALESCE(SUM(CS), 0)
                FROM Fielding
                WHERE playerID = %s AND yearID = %s
                GROUP BY POS
            """, (player_id, year))
            for pos, games, po, a, e, sb, cs in cur.fetchall():
                if games >= 15:
                    stats['fielding'][pos] = {
                        'PO': po,
                        'A': a,
                        'E': e,
                        'SB': sb,
                        'CS': cs,
                        'Games': games,
                    }

    return stats

# You can add more queries here later...
# def get_team_stats(year, team_id): ...
# def get_stadium_info(stadium_id): ...
