import pyperclip
import math

numbers = {
    11,12,13,14,15,16,
    21,22,23,24,25,26,
    31,32,33,34,35,36,
    41,42,43,44,45,46,
    51,52,53,54,55,56,
    61,62,63,64,65,66
    }

positions = ['1b','2b','3b','ss','lf','cf','rf', 'dh','p', 'c']

class Batter:

    def __init__(self):
        print("Player created")
        self.year = int(input("Year: "))
        while True:
            pos = input("Position: ")
            if pos in positions:
                self.pos = pos
                break
            else:
                print("Invalid position")
        self.games = int(input("Games: "))
        self.pa = int(input("Plate Appearances: "))
        if self.pa != 0:
            self.at_bats = int(input("At Bats: "))
            self.hits = int(input("Hits: "))
            self.doubles = int(input("Doubles: "))
            self.triples = int(input("Triples: "))
            self.hr = int(input("Home Runs: "))
            self.rbi = int(input("RBIs: "))
            self.sb = int(input("Stolen Bases: "))
            self.bb = int(input("Walks: "))
            self.so = int(input("Strike Outs: "))
            self.hbp = int(input("Hit By Pitch: "))
        self.po = int(input("Put Outs: "))
        self.assists = int(input("Assists: "))
        self.fld_pct = int(input("Fld% (x1000): "))

    def player_ratings(self):
        # offense
        off_string = ''

        if self.pa != 0:

            clutch = self.rbi / self.games
            if clutch >= .6:
                off_string += '#'

            bavg = round(self.hits / self.at_bats, 3)
            if bavg >= .39: letter = 'AAA'
            elif bavg > .361: letter = 'AA'
            elif bavg > .334: letter = 'A+'
            elif bavg > .306: letter = 'A'
            elif bavg > .278: letter = 'B+'
            elif bavg > .250: letter = 'B'
            elif bavg > .222: letter = 'C+'
            elif bavg > .195: letter = 'C'
            elif bavg > .167: letter = 'D+'
            elif bavg > .139: letter = 'D'
            elif bavg > .111: letter = 'E+'
            elif bavg > .083: letter = 'E'
            else: letter = 'G+'
            off_string += letter

            hr_check = round((self.hr / self.hits) * 36) - 1
            hr_num = sorted(numbers)[hr_check]
            off_string += str(hr_num)

            trip_check = round((self.triples / self.hits) * 36)
            trip_num = sorted(numbers)[hr_check + trip_check]
            if trip_check:
                off_string += '('+str(trip_num)+')'
            
            ob = (self.hits + self.bb + self.hbp)
            xb = (self.doubles + self.triples + self.hr)
            b = ob - xb
            speed_check = round(self.sb / b, 3) * 100
            if speed_check >= 30.1: spd_rate = '****'
            elif speed_check >= 20.1: spd_rate = '***'
            elif speed_check >= 10.1: spd_rate = '**'
            elif speed_check >= 7.6: spd_rate = '*'
            else: spd_rate = ''
            off_string += spd_rate

            walk_check = round((self.bb / self.pa) * 36) - 1
            walk_num = sorted(numbers)[walk_check]
            off_string += ' ['+str(walk_num)+'-'

            k_check = round((self.so / self.pa) * 36)
            k_num = sorted(numbers)[walk_check + k_check]
            off_string += str(k_num)

            hbp_check = round((self.hbp / self.pa) * 36)
            hbp_num = sorted(numbers)[walk_check + k_check + hbp_check]
            if hbp_num != k_num: off_string += '/' + str(hbp_num)
            off_string += ']      '

            ph_check = round((self.hits / self.pa) * 36) - 1
            ph_num = sorted(numbers, reverse=True)[ph_check]
            off_string += str(ph_num)

        # defense
        def_string = ''
        # superior defense check
        if self.year >= 1950 and self.pos == 'p' and self.fld_pct >= 980:sup_rate = 'S'
        elif self.pos == 'p' and self.fld_pct >= 990:sup_rate = 'S'
        elif self.year >= 1950 and self.pos == 'c' and self.fld_pct >= 993:sup_rate = 'S'
        elif self.year >= 1920 and self.pos == 'c' and self.fld_pct >= 990:sup_rate = 'S' 
        elif self.year >= 1910 and self.pos == 'c' and self.fld_pct >= 989:sup_rate = 'S'
        elif self.year < 1910 and self.pos == 'c' and self.fld_pct >= 985:sup_rate = 'S'
        elif self.year >= 1910 and self.pos == '1b' and self.fld_pct >= 995:sup_rate = 'S'
        elif self.year < 1910 and self.pos == '1b' and self.fld_pct >= 994:sup_rate = 'S'
        elif self.year >= 1930 and self.pos == '2b' and self.fld_pct >= 984:sup_rate = 'S'
        elif self.year >= 1920 and self.pos == '2b' and self.fld_pct >= 980:sup_rate = 'S'
        elif self.year < 1920 and self.pos == '2b' and self.fld_pct >= 978:sup_rate = 'S'
        elif self.year >= 1920 and self.pos == '3b' and self.fld_pct >= 971:sup_rate = 'S'
        elif self.year >= 1910 and self.pos == '3b' and self.fld_pct >= 967:sup_rate = 'S'
        elif self.year < 1910 and self.pos == '3b' and self.fld_pct >= 960:sup_rate = 'S'
        elif self.year >= 1930 and self.pos == 'ss' and self.fld_pct >= 973:sup_rate = 'S'
        elif self.year >= 1920 and self.pos == 'ss' and self.fld_pct >= 968:sup_rate = 'S'
        elif self.year >= 1910 and self.pos == 'ss' and self.fld_pct >= 960:sup_rate = 'S'
        elif self.year < 1910 and self.pos == 'ss' and self.fld_pct >= 945:sup_rate = 'S'
        elif self.year >= 1920 and self.fld_pct >= 990 and self.pos in ('lf', 'rf', 'cf'):sup_rate = 'S'
        elif self.year >= 1910 and self.pos == 'lf' and self.fld_pct >= 987:sup_rate = 'S'
        elif self.year < 1910 and self.pos == 'lf' and self.fld_pct >= 977:sup_rate = 'S'
        elif self.year >= 1910 and self.pos == 'cf' and self.fld_pct >= 988:sup_rate = 'S'
        elif self.year < 1910 and self.pos == 'cf' and self.fld_pct >= 986:sup_rate = 'S'
        elif self.year >= 1910 and self.pos == 'rf' and self.fld_pct >= 990:sup_rate = 'S'
        elif self.year < 1910 and self.pos == 'rf' and self.fld_pct >= 979:sup_rate = 'S'
        else: sup_rate = ''

        def_string += sup_rate

        arm_check = round(self.assists / self.games, 2)
        range_check = round(self.po / self.games, 1)
        arm_rate, range_rate = '8', '4'
        if self.pos == 'p':
            if arm_check >= .7: arm_rate = '9'
            if range_check >= .3: range_rate = '5'
        elif self.pos == 'c':
            arm_rate = '9'
        elif self.pos == '1b':
            if arm_check >= .7: arm_rate = '9'
            if range_check >= 8.3: range_rate = '5'
        elif self.pos == '2b':
            if arm_check >= 2.8: arm_rate = '9'
            if range_check >= 2.1: range_rate = '5'
        elif self.pos == '3b':
            if arm_check >= 2.0: arm_rate = '9'
            if range_check >= .8: range_rate = '5'
        elif self.pos == 'ss':
            if arm_check >= 2.8: arm_rate = '9'
            if range_check >= 1.6: range_rate = '5'
        elif self.pos in ('lf', 'cf', 'rf'):
            if arm_check >= .08: arm_rate = '9'
            if range_check >= 2.1: range_rate = '5'

        def_string += arm_rate + range_rate

        print(off_string)
        pyperclip.copy(off_string)
        input('Enter after pasting.')

        print(def_string)
        pyperclip.copy(def_string)
        input('Enter after pasting.')


class Pitcher(Batter):

    def __init__(self):
        super().__init__()
        print("Pitcher created")
        self.games = int(input("Games Pitched: "))
        self.innings = float(input("Innings Pitched: "))
        self.hits_allowed = int(input("Hits Allowed: "))
        self.hr_allowed = int(input("Home Runs Allowed: "))
        self.walks = int(input("Walks: "))
        self.k = int(input("Strikeouts: "))
        self.hb = int(input("Hit Batters: "))
        self.bf = int(input("Batters Faced: "))

    def pitching(self):
        pitch_string = ''
        self.player_ratings()
        gopher = round(self.hr_allowed / self.hits_allowed, 2)
        if gopher >= .1: pitch_string += '+'
        elif gopher <= .05: pitch_string += '-'

        bavg_against = round(self.hits_allowed / (self.bf - self.walks - self.hb), 3)
        if bavg_against < .140: letter = 'J+'
        elif bavg_against < .168: letter = 'J'
        elif bavg_against < .196: letter = 'K'
        elif bavg_against < .223: letter = 'L'
        elif bavg_against < .251: letter = 'M'
        elif bavg_against < .279: letter = 'W'
        elif bavg_against < .307: letter = 'X'
        elif bavg_against < .335: letter = 'Y'
        elif bavg_against < .361: letter = 'Z+'
        else: letter = 'Z'
        pitch_string += letter

        ie = round(self.innings / self.games)
        pitch_string += str(ie)

        bb_check = math.ceil((self.walks / self.bf) * 36)
        bb_num = sorted(numbers)[bb_check]
        pitch_string += ' (' + str(bb_num)+'-'

        k_check = round((self.k / self.bf) * 36)
        k_num = sorted(numbers)[bb_check + k_check]
        pitch_string += str(k_num)

        hp_check = math.ceil((self.hb / self.bf) * 36)
        hp_num = sorted(numbers)[bb_check + k_check + hp_check]
        if hp_num == k_num: pitch_string += ') '
        else: pitch_string += '/' + str(hp_num) + ') '
        if self.hb > 5: pitch_string += '[WP] '

        br_check = round(((self.walks + self.hits_allowed + self.hb) / self.bf) * 36)
        pcn = sorted(numbers, reverse=True)[br_check]
        pitch_string += 'PCN-' + str(pcn)

        pph_check = round((self.hits_allowed / self.bf) * 36) - 1
        pph = sorted(numbers, reverse=True)[pph_check]
        pitch_string += ' PPH-' + str(pph)

        print(pitch_string)
        pyperclip.copy(pitch_string)
        input("Enter after pasting.")


class Catcher(Batter):
    def __init__(self):
        super().__init__()
        print("Catcher created")

        self.sb_against = int(input('Stolen Bases Against: '))
        self.caught = int(input('Runners Caught Stealing: '))
    
    def catcher_rating(self):
        print("Catcher's extra method")
        self.player_ratings()

        cs_rate = round(self.caught / (self.sb_against + self.caught), 2)
        if cs_rate <= .2: cr ='no rating'
        elif cs_rate <= .3: cr = '-1'
        elif cs_rate <= .4: cr = '-2'
        elif cs_rate <= .5: cr = '-3'
        elif cs_rate > .5: cr = '-4'

        print('Catchers rating: ',cr)
        pyperclip.copy(cr)
        input('Enter after pasting.)')


def main():
    last_choice = 'b'
    while True:
        choice = input(f"Choose player type (b = Batter, p = Pitcher, c = Catcher) [default: {last_choice}]: ").strip().lower()
        if choice == '':
            choice = last_choice
        else:
            last_choice = choice

        if choice == 'b':
            player = Batter()
            player.player_ratings()
        elif choice == 'p':
            player = Pitcher()
            player.pitching()
        elif choice == 'c':
            player = Catcher()
            player.catcher_rating()
        else:
            print("Invalid choice. Please enter b, p, or c.")
            continue

        # Simulate object disposal by overwriting reference
        player = None

if __name__ == "__main__":
    main()
