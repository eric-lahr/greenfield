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

positions = ['1b','2b','3b','ss','lf','cf','rf', 'of', 'dh','p', 'c']

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

    def player_ratings(self):
        # offense
        off_string = ''

        if self.pa != 0:

            clutch = self.rbi / self.games
            if clutch >= .6:
                off_string += '#'

            if self.hits == 0: bavg = .0
            else: bavg = round(self.hits / self.at_bats, 3)
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

            if self.hr != 0:
                hr_check = round((self.hr / self.hits) * 36) - 1
                hr_num = sorted(numbers)[hr_check]
            else: hr_num, hr_check = '', 0
            off_string += str(hr_num)

            if self.hits != 0:
                trip_check = round((self.triples / self.hits) * 36)
                trip_num = sorted(numbers)[hr_check + trip_check]
            else:
                trip_num = ''
            off_string += '('+str(trip_num)+')'
            
            ob = (self.hits + self.bb + self.hbp)
            xb = (self.doubles + self.triples + self.hr)
            b = ob - xb
            if self.sb != 0 and b != 0:
                speed_check = round(self.sb / b, 3) * 100
            else: speed_check = 0
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

        print(off_string)
        pyperclip.copy(off_string)
        input('Enter after pasting.')


    def defensive_rating(self):
        n = int(input('How many positions did the player play? '))
        i = 0
        self.def_string = ''
        self.sup_rate = ''
        self.arm_rate, self.range_rate = '8', '4'
        self.catch_arm = ''

        while i < n:
            i += 1
            while True:
                self.pos = input(f'Position {i}: ')
                if self.pos not in positions:
                    print('Invalid position.')
                else: break
            
            self.year = int(input('Year: '))
            self.gap = int(input('Games at position: '))
            self.po = int(input("Put Outs: "))
            self.a = int(input('Assists: '))
            self.pct = int(input('Fielding % (x1000): '))
            self.arm_check = round(self.a / self.gap, 2)
            self.range_check = round(self.po / self.gap, 1)

            if self.pos == 'p':
                if ((self.year >= 1950) and (self.pct >= 980) or
                    (self.year < 1950) and (self.pct >= 990)):
                    self.sup_rate = 'S'
                if self.arm_check >= .7: arm_rate = '9'
                if self.range_check >= .3: range_rate = '5'
            elif self.pos == 'c':
                if ((self.year >= 1950) and (self.pct >= 993) or
                    (1920 <= self.year < 1950) and (self.pct >= 990) or
                    (1910 <= self.year < 1920) and (self.pct >= 989) or
                    (self.year < 1910) and (self.pct >= 985)):
                    self.sup_rate = 'S'
                self.arm_rate = '9'
                self.sb_allowed = int(input("Stolen Bases Allowed: "))
                self.caught = int(input("Runners Caught Stealing: "))
                self.catch_rate = (self.caught / (self.caught + self.sb_allowed))
                if self.catch_rate >= .5: self.catch_arm = '-4'
                elif self.catch_rate >= .41: self.catch_arm = '-3'
                elif self.catch_rate >= .31: self.catch_arm = '-2'
                elif self.catch_rate >= .21: self.catch_arm = '-1'
                else: self.catch_arm = ''
            elif self.pos == '1b':
                if ((self.year >= 1910) and (self.pct >= 995) or
                    (1910 > self.year) and (self.pct >=994)):
                    self.sup_rate = 'S'             
            elif self.pos == '2b':
                if ((self.year >= 1930) and (self.pct >= 984) or
                    (self.year < 1920) and (self.pct >= 978)):
                    self.sup_rate = 'S'
            elif self.pos == '3b':
                if ((self.year >= 1920) and (self.pct >= 971) or
                    (1920 > self.year >= 1910) and (self.pct >= 967) or
                    (self.year < 1910) and (self.pct >= 960)):
                    self.sup_rate = 'S'
            elif self.pos == 'ss':
                if ((self.year >= 1930) and (self.pct >= 973) or
                    (1930 > self.year >= 1920) and (self.pct >= 968) or
                    (1920 > self.year >= 1910) and (self.pct >= 960) or
                    (self.year < 1910) and (self.pct >= 945)):
                    self.sup_rate = 'S'
            elif self.pos == 'lf':
                if ((self.year >= 1920) and (self.pct >= 990) or
                    (1920 > self.year >= 1910) and (self.pct >= 987) or
                    (self.year < 1910) and (self.pct >= 977)):
                    self.sup_rate = 'S'
            elif self.pos == 'cf':
                if ((self.year >= 1920) and (self.pct >= 990) or
                    (1920 > self.year >= 1910) and (self.pct >= 988) or
                    (self.year < 1910) and (self.pct >= 986)):
                    self.sup_rate = 'S'
            elif self.pos == 'rf' or self.pos == 'of':
                if ((self.year >= 1910) and (self.pct >= 990) or
                    (self.year < 1010) and (self.pct >= 979)):
                    self.sup_rate = 'S'
            if self.pos == 'dh':
                self.arm_rate, self.range_rate = 'D', 'H'

            if i != n:
                comma = ', '
            else:
                comma = ''

            self.def_string += self.sup_rate + self.arm_rate + self.range_rate + self.catch_arm + comma

        print(self.def_string)
        pyperclip.copy(self.def_string)
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


def main():
    last_choice = 'b'
    while True:
        choice = input(f"Choose player type (b = Batter, p = Pitcher) [default: {last_choice}]: ").strip().lower()
        if choice == '':
            choice = last_choice
        else:
            last_choice = choice

        if choice == 'b':
            player = Batter()
            player.player_ratings()
            player.defensive_rating()
        elif choice == 'p':
            player = Pitcher()
            player.player_ratings()
            player.defensive_rating()
            player.pitching()
        else:
            print("Invalid choice. Please enter b, p, or c.")
            continue

        # Simulate object disposal by overwriting reference
        player = None

if __name__ == "__main__":
    main()
