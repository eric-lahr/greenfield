# def all_time_team_finder(lahman_team, year=0):
#     print('func:',lahman_team,year)
#     team_name = ''

#     if lahman_team in [
#         'Brooklyn Grays', 'Brooklyn Atlantics', 'Brooklyn Bridegrooms',
#         'Brooklyn Grooms', 'Superbas', 'Brooklyn Trolley Dodgers',
#         'Brooklyn Dodgers', 'Brooklyn Robins', 'Los Angeles Dodgers'
#     ]:
#         team_name = 'Dodgers'

#     elif lahman_team in ['New York Highlanders', 'New York Yankees']:
#         team_name = 'Yankees'

#     elif lahman_team in ['Boston Americans', 'Boston Red Sox']:
#         team_name = 'Red Sox'

#     elif lahman_team == 'Cleveland Spiders':
#         team_name = ''  # Franchise defunct, not carried forward

#     elif (
#         (1893 < year < 1902 and lahman_team == 'Milwaukee Brewers') or
#         (1901 < year < 1954 and lahman_team == 'St. Louis Browns') or
#         lahman_team == 'Baltimore Orioles'
#     ):
#         team_name = 'Orioles'

#     elif lahman_team in ['Tampa Bay Rays', 'Tampa Bay Devil Rays']:
#         team_name = 'Rays'

#     elif lahman_team == 'Toronto Blue Jays':
#         team_name = 'Blue Jays'

#     elif lahman_team in ['St. Paul Saints', 'Chicago White Stockings', 'Chicago White Sox']:
#         team_name = 'White Sox'

#     elif lahman_team in [
#         'Columbus Buckeyes', 'Columbus Senators', 'Grand Rapids Prodigals',
#         'Cleveland Lakeshores', 'Cleveland Bluebirds', 'Cleveland Broncos',
#         'Cleveland Naps', 'Cleveland Indians', 'Cleveland Guardians'
#     ]:
#         team_name = 'Guardians'

#     elif lahman_team == 'Detroit Tigers':
#         team_name = 'Tigers'

#     elif lahman_team == 'Kansas City Royals':
#         team_name = 'Royals'

#     elif lahman_team in ['Washington Senators', 'Washington Nationals']:
#         if year < 1961 and lahman_team == 'Washington Nationals':
#             team_name = 'Twins'
#         elif 1961 <= year < 1972 and lahman_team == 'Washington Senators':
#             team_name = 'Rangers'
#         elif year >= 2005 and lahman_team == 'Washington Nationals':
#             team_name = 'Nationals'
#         else:
#             team_name = ''  # Ambiguous or non-major league year

#     elif lahman_team == 'Minnesota Twins':
#         team_name = 'Twins'

#     elif lahman_team in [
#         'Philadelphia Athletics', 'Kansas City Athletics', 'Oakland Athletics',
#         'Athletics', 'Las Vegas Athletics'
#     ]:
#         team_name = 'Athletics'

#     elif lahman_team in ['Houston Astros', "Houston Colt .45's"]:
#         team_name = 'Astros'

#     elif lahman_team in [
#         'Los Angeles Angels', 'California Angels',
#         'Anaheim Angels', 'Los Angeles Angels of Anaheim'
#     ]:
#         team_name = 'Angels'

#     elif lahman_team == 'Seattle Mariners':
#         team_name = 'Mariners'

#     elif lahman_team == 'Texas Rangers':
#         team_name = 'Rangers'

#     elif (
#         (1969 < year and lahman_team == 'Milwaukee Brewers') or
#         lahman_team == 'Seattle Pilots'
#     ):
#         team_name = 'Brewers'

#     elif lahman_team in [
#         'Boston Red Caps', 'Boston Beaneaters', 'Boston Doves',
#         'Boston Rustlers', 'Boston Braves', 'Boston Bees',
#         'Milwaukee Braves', 'Atlanta Braves'
#     ]:
#         team_name = 'Braves'

#     elif year < 1876 and lahman_team == 'Boston Red Stockings':
#         team_name = 'Red Sox'

#     elif lahman_team in ['Miami Marlins', 'Florida Marlins']:
#         team_name = 'Marlins'

#     elif lahman_team == 'New York Mets':
#         team_name = 'Mets'

#     elif lahman_team in [
#         'Philadelphia Quakers', 'Philadelphia Phils', 'Philadelphia Blue Jays',
#         'Philadelphia Phillies'
#     ]:
#         team_name = 'Phillies'

#     elif lahman_team in ['Montreal Expos']:
#         team_name = 'Nationals'

#     elif lahman_team in ['Chicago Orphans', 'Chicago Colts', 'Chicago Cubs']:
#         team_name = 'Cubs'

#     elif 1870 < year < 1890 and lahman_team == 'Chicago White Stockings':
#         team_name = 'Cubs'

#     elif lahman_team in ['Cincinnati Red Stockings', 'Cincinnati Redlegs', 'Cincinnati Reds']:
#         team_name = 'Reds'

#     elif lahman_team in ['Allegheny', 'Pittsburgh Alleghenys', 'Pittsburgh Pirates']:
#         team_name = 'Pirates'

#     elif lahman_team in ['St. Louis Brown Stockings', 'St. Louis Perfectos', 'St. Louis Cardinals']:
#         team_name = 'Cardinals'

#     elif 1882 < year < 1892 and lahman_team == 'St. Louis Browns':
#         team_name = 'Cardinals'

#     elif lahman_team == 'Arizona Diamondbacks':
#         team_name = 'Diamondbacks'

#     elif lahman_team == 'Colorado Rockies':
#         team_name = 'Rockies'

#     elif lahman_team == 'San Diego Padres':
#         team_name = 'Padres'

#     elif lahman_team in ['New York Gothams', 'New York Giants', 'San Francisco Giants']:
#         team_name = 'Giants'

#     return team_name

def all_time_team_finder(team_name, debut_year):
    print(f"--> all_time_team_finder input: {team_name=} {debut_year=}")
    team_map = {
        'Montreal Expos': 'Nationals',
        'Washington Nationals': 'Nationals',
        'Florida Marlins': 'Marlins',
        'Miami Marlins': 'Marlins',
        'Tampa Bay Devil Rays': 'Rays',
        'Tampa Bay Rays': 'Rays',
        # Add others as needed
    }
    mapped = team_map.get(team_name, '')
    print(f"--> Mapped: {mapped}")
    return mapped

def get_franchise_display_map():
    return {
        'LAD': 'Dodgers',
        'BRO': 'Dodgers',
        'SFG': 'Giants',
        'NYG': 'Giants',
        'WSN': 'Nationals',
        'MON': 'Nationals',
        'FLA': 'Marlins',
        'MIA': 'Marlins',
        'TBD': 'Rays',
        'TBR': 'Rays',
        'KCA': 'Athletics',
        'OAK': 'Athletics',
        'PHA': 'Athletics',
        'PHI': 'Phillies',  # defunct Philadelphia A's
        'CLE': 'Guardians',
        'BOS': 'Red Sox',
        'NYA': 'Yankees',
        'NYY': 'Yankees',
        'BAL': 'Orioles',
        'TOR': 'Blue Jays',
        'CHC': 'Cubs',
        'CIN': 'Reds',
        'ATL': 'Braves',
        'PIT': 'Pirates',
        'SLN': 'Cardinals',
        'STL': 'Cardinals',
        'CHW': 'White Sox',
        'DET': 'Tigers',
        'MIN': 'Twins',
        'HOU': 'Astros',
        'SEA': 'Mariners',
        'TEX': 'Rangers',
        'KCR': 'Royals',
        'LAA': 'Angels',
        'ANA': 'Angels',
        'CAL': 'Angels',
        'NYM': 'Mets',
        'MIL': 'Brewers',
        'SDP': 'Padres',
        'COL': 'Rockies',
        'ARI': 'Diamondbacks'
        # Add others as needed
    }
