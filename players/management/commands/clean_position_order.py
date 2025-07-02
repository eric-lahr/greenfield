import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from django.core.management.base import BaseCommand
from players.models import Players, PlayerPositionRating, Position
from greenfield.utils.lahman_db import get_lahman_connection
from collections import defaultdict

class Command(BaseCommand):
    help = "Clean and assign position_order for each player's positions based on Lahman fielding games"

    def handle(self, *args, **kwargs):
        conn = get_lahman_connection()
        cursor = conn.cursor()

        # Build Position map
        position_map = {pos.name: pos for pos in Position.objects.all()}

        updated_count = 0
        skipped_count = 0

        for player in Players.objects.all():
            # Convert 'All Time' to None for full-career stats
            year = None if player.year.lower() == 'all time' else int(player.year)

            ratings = PlayerPositionRating.objects.filter(player=player)
            if not ratings.exists():
                self.stdout.write(f"Skipping {player} (no positions)")
                skipped_count += 1
                continue

            pos_games = {}
            for rating in ratings:
                pos_code = rating.position.name
                playerID = f"{player.first_name.lower()[0]}{player.last_name.lower()}"

                query = "SELECT SUM(G) FROM fielding WHERE playerID = %s AND POS = %s"
                params = [playerID, pos_code]

                if year:
                    query += " AND yearID = %s"
                    params.append(year)

                cursor.execute(query, params)
                result = cursor.fetchone()
                games = result[0] if result and result[0] is not None else 0
                pos_games[rating] = games

            # Sort by games played (desc)
            sorted_ratings = sorted(pos_games.items(), key=lambda x: -x[1])

            for order, (rating, _) in enumerate(sorted_ratings):
                rating.position_order = order
                rating.save()

            updated_count += 1
            self.stdout.write(f"Updated {player}: {[f'{r.position.name}:{r.position_order}' for r, _ in sorted_ratings]}")

        cursor.close()
        conn.close()

        self.stdout.write(self.style.SUCCESS(f"Done: {updated_count} players updated, {skipped_count} skipped."))
