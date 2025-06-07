import math

numbers = {
    11,12,13,14,15,16,
    21,22,23,24,25,26,
    31,32,33,34,35,36,
    41,42,43,44,45,46,
    51,52,53,54,55,56,
    61,62,63,64,65,66
    }

def clutch(rbi, g):
    rate = round(rbi / g, 3)
    if rate >= .6: cr = '#'
    else: cr = ''

    return cr

def hit_letter(h, ab):
    if ab == 0 or h == 0:
        bavg = .001
    else:
        bavg = round(h / ab, 3)

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

    return letter

def hr_3b_number(hr, trip, h):
    hr_trp_score = ''
    if hr > 0 and h > 0:
        hr_check = (hr / h) * 36
        if hr_check < .5: hr_num, hr_check = '', 0
        elif hr_check >= .5:
            hr_check = round(hr_check) - 1
            hr_num = sorted(numbers)[hr_check]
        hr_trp_score += str(hr_num)
    else: hr_check = 0
    
    if trip > 0 and h > 0:
        trip_check = round((trip / h) * 36)
        if trip_check >= 1:
            trip_num = sorted(numbers)[hr_check + trip_check]
            hr_trp_score += '(' + str(trip_num) + ')'

    return hr_trp_score

def speed(sb, h, bb, hbp, double, triple, hr):
    speed_check = round(sb / ((h + bb + hbp) - (double + triple + hr)), 3)

    if speed_check >= .301: spd_rate = '****'
    elif speed_check >= .201: spd_rate = '***'
    elif speed_check >= .101: spd_rate = '**'
    elif speed_check >= .076: spd_rate = '*'
    else: spd_rate = ''

    return spd_rate

def batter_bb_k(bb, so, hbp, pa):
    if bb == 0: walk_check, walk_num = 0, 'n'
    else:
        walk_check = round((bb / pa) * 36) - 1
        if walk_check <= 0: walk_num, walk_check = 'n', 0
        else: walk_num = sorted(numbers)[walk_check]
    k_check = round((so / pa) * 36)
    k_num = sorted(numbers)[walk_check + k_check]
    hbp_check = math.ceil((hbp / pa) * 36)

    if hbp_check:
        hbp_num = sorted(numbers)[walk_check + k_check + hbp_check]
        hbp_str = '/' + str(hbp_num)
    else: hbp_str = ''

    bb_k_string = '[' + str(walk_num) + '-' +str(k_num) + hbp_str + ']'

    return bb_k_string

def probable_hit_number(h, pa):
    ph_check = round((h / pa) * 36) - 1
    ph_num = sorted(numbers, reverse=True)[ph_check]

    return ph_num

def pitch_letter(bavg_against):
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

    return letter

def innings_of_effectiveness(g, ip):

    return str(round(ip / g))

def pitcher_bb_k_hbp(bf, bb, so, hbp):
    bb_check = math.ceil((bb / bf) * 36)
    bb_num = sorted(numbers)[bb_check]
    if bb_num < 11: bb_num = 11
    bb_string = '[' + str(bb_num) + '-'
    k_check = round((so / bf) * 36)
    if k_check == 0: k_str = 'n'
    else:
        k_num = sorted(numbers)[bb_check + k_check]
        k_str = str(k_num)
    hp_check = math.ceil((hbp / bf) * 36)
    if hp_check == 0: hp_str = ']'
    else:
        hp_num = sorted(numbers)[bb_check + k_check + hp_check]
        hp_str = str('/' + str(hp_num) + ']')

    return bb_string + k_str + hp_str

# def pitcher_bb_k_hbp(bf, bb, so, hbp):
#     bb_check = math.ceil((bb / bf) * 36)
#     bb_num = sorted(numbers)[bb_check]
#     kbbwp_string = ' (' + str(bb_num)+'-'

#     k_check = round((so / bf) * 36)
#     k_num = sorted(numbers)[bb_check + k_check]
#     kbbwp_string += str(k_num)

#     hp_check = math.ceil((hbp / bf) * 36)
#     hp_num = sorted(numbers)[bb_check + k_check + hp_check]
#     if hp_num == k_num: kbbwp_string += ') '
#     else: kbbwp_string += '/' + str(hp_num) + ') '
#     if hbp > 5: kbbwp_string += '[WP] '

#     return kbbwp_string

def gopher(hr, h):
    go_check = round(hr / h, 3)
    if go_check >= .1: gopher_string = '+'
    else: gopher_string = ''

    return gopher_string

def wild_pitch(wp):
    if wp >= 5: wp_str = '[WP]'
    else: wp_str = ''

    return wp_str

def pitcher_control_number(walks, hb, hits_allowed, bf):
    br_check = round(((walks + hits_allowed + hb) / bf) * 36)
    pcn = str(sorted(numbers, reverse=True)[br_check])

    return pcn

def def_rating(pos, pct, year, a, po, gap, caught, sb_allowed):
    sup_rate, arm_rate, range_rate, catch_arm = '', '8', '4', ''
    arm_check = round(a / gap, 2)
    range_check = round(po / gap, 1)

    if pos == 'P':
        if ((year >= 1950) and (pct >= 980) or
            (year < 1950) and (pct >= 990)):
            sup_rate = 'S'
        if arm_check >= .7: arm_rate = '9'
        if range_check >= .3: range_rate = '5'
    elif pos == 'C':
        if ((year >= 1950) and (pct >= 993) or
            (1920 <= year < 1950) and (pct >= 990) or
            (1910 <= year < 1920) and (pct >= 989) or
            (year < 1910) and (pct >= 985)):
            sup_rate = 'S'
        arm_rate = '9'
        print(caught, sb_allowed)
        if (caught + sb_allowed) != 0:
            print(caught, sb_allowed)
            catch_pct = (caught / (caught + sb_allowed))
            print(catch_pct)
            if catch_pct >= .5: catch_arm = '-4'
            elif catch_pct >= .41: catch_arm = '-3'
            elif catch_pct >= .31: catch_arm = '-2'
            elif catch_pct >= .21: catch_arm = '-1'
        else: catch_arm = ''
    elif pos == '1B':
        if ((year >= 1910) and (pct >= 995) or
            (1910 > year) and (pct >=994)):
            sup_rate = 'S'
        if arm_check >= .7: arm_rate = '9'
        if range_check >= 8.3: range_rate = '5'
    elif pos == '2B':
        if ((year >= 1930) and (pct >= 984) or
            (year < 1920) and (pct >= 978)):
            sup_rate = 'S'
        if arm_check >= 2.8: arm_rate = '9'
        if range_check >= 2.1: range_rate = '5'
    elif pos == '3B':
        if ((year >= 1920) and (pct >= 971) or
            (1920 > year >= 1910) and (pct >= 967) or
            (year < 1910) and (pct >= 960)):
            sup_rate = 'S'
        if arm_check >= 2: arm_rate = '9'
        if range_check >= .8: range_rate = '5'
    elif pos == 'SS':
        if ((year >= 1930) and (pct >= 973) or
            (1930 > year >= 1920) and (pct >= 968) or
            (1920 > year >= 1910) and (pct >= 960) or
            (year < 1910) and (pct >= 945)):
            sup_rate = 'S'
        if arm_check >= 2.8: arm_rate = '9'
        if range_check >= 1.6: range_rate = '5'
    elif pos == 'LF':
        if ((year >= 1920) and (pct >= 990) or
            (1920 > year >= 1910) and (pct >= 987) or
            (year < 1910) and (pct >= 977)):
            sup_rate = 'S'
        if arm_check >= .08: arm_rate = '9'
        if range_check >= 2.1: range_rate = '5'
    elif pos == 'CF':
        if ((year >= 1920) and (pct >= 990) or
            (1920 > year >= 1910) and (pct >= 988) or
            (year < 1910) and (pct >= 986)):
            sup_rate = 'S'
        if arm_check >= .08: arm_rate = '9'
        if range_check >= 2.1: range_rate = '5'
    elif pos == 'RF' or pos == 'of':
        if ((year >= 1910) and (pct >= 990) or
            (year < 1010) and (pct >= 979)):
            sup_rate = 'S'
        if arm_check >= .08: arm_rate = '9'
        if range_check >= 2.1: range_rate = '5'
    elif pos == 'OF' or pos == 'of':
        if ((year >= 1910) and (pct >= 990) or
            (year < 1010) and (pct >= 979)):
            sup_rate = 'S'
        if arm_check >= .08: arm_rate = '9'
        if range_check >= 2.1: range_rate = '5'
    if pos == 'dh':
        arm_rate, range_rate = 'D', 'H'

    return sup_rate + arm_rate + range_rate + catch_arm