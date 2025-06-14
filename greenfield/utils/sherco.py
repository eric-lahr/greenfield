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
    if h == 0: gopher_string = ''
    else:
        go_check = round(hr / h, 3)
        if go_check >= .1: gopher_string = '+'
        elif go_check <=.05: gopher_string = '-'
        else: gopher_string = ''

    return gopher_string

def wild_pitch(wp):
    if wp >= 5: wp_str = '[WP]'
    else: wp_str = ''

    return wp_str

def pitcher_control_number(walks, hb, hits_allowed, bf):
    br_check = round(((walks + hits_allowed + hb) / bf) * 36)
    if br_check == 36: pcn = 11
    else:
        pcn = str(sorted(numbers, reverse=True)[br_check])

    return pcn

def get_superior_rating(pos, pct, year):
    """Return 'S' if fielding pct qualifies for Superior based on position and year."""
    pos = pos.upper().strip()
    
    # Default to a very high threshold (basically unachievable)
    threshold = 1.1

    if pos == 'P':
        if year >= 1950: threshold = .980
        elif year >= 1930: threshold = .990
        else: threshold = .990
    elif pos == 'C':
        if year >= 1950: threshold = .993
        elif year >= 1930: threshold = .990
        elif year >= 1920: threshold = .990
        elif year >= 1910: threshold = .989
        else: threshold = .985
    elif pos == '1B':
        if year >= 1910: threshold = .995
        else: threshold = .994
    elif pos == '2B':
        if year >= 1930: threshold = .984
        elif year >= 1920: threshold = .980
        else: threshold = .978
    elif pos == '3B':
        if year >= 1920: threshold = .971
        elif year >= 1910: threshold = .967
        else: threshold = .960
    elif pos == 'SS':
        if year >= 1930: threshold = .973
        elif year >= 1920: threshold = .968
        elif year >= 1910: threshold = .960
        else: threshold = .945
    elif pos == 'LF':
        if year >= 1920: threshold = .990
        elif year >= 1910: threshold = .987
        else: threshold = .977
    elif pos == 'CF':
        if year >= 1920: threshold = .990
        elif year >= 1910: threshold = .988
        else: threshold = .986
    elif pos == 'RF':
        if year >= 1910: threshold = .990
        else: threshold = .979

    if pct >= threshold:
        return 'S'
    return ''

def def_rating(pos, a, po, gap):
    pos = pos.upper().strip()
    arm_rate, range_rate = '8', '4'

    arm_check = round(a / gap, 2) if gap else 0
    range_check = round(po / gap, 1) if gap else 0

    if pos == 'P':
        if arm_check >= 0.7:
            arm_rate = '9'
        if range_check >= 0.3:
            range_rate = '5'

    elif pos == 'C':
        arm_rate = '9'  # All catchers get 9
        range_rate = '4'  # As specified

    elif pos == '1B':
        if arm_check >= 0.7:
            arm_rate = '9'
        if range_check >= 8.3:
            range_rate = '5'

    elif pos == '2B':
        if arm_check >= 2.8:
            arm_rate = '9'
        if range_check >= 2.1:
            range_rate = '5'

    elif pos == '3B':
        if arm_check >= 2.0:
            arm_rate = '9'
        if range_check >= 0.8:
            range_rate = '5'

    elif pos == 'SS':
        if arm_check >= 2.8:
            arm_rate = '9'
        if range_check >= 1.6:
            range_rate = '5'

    elif pos in ['LF', 'CF', 'RF', 'OF']:  # Handle any outfield label
        if arm_check >= 0.08:
            arm_rate = '9'
        if range_check >= 2.1:
            range_rate = '5'

    elif pos == 'DH':
        arm_rate = ''
        range_rate = ''

    return arm_rate + range_rate

def get_catcher_throw_rating(cs, sb):
    attempts = sb + cs
    if attempts == 0:
        return ''  # No rating if no attempts

    cs_pct = round(cs / attempts, 3)

    if cs_pct >= 0.50:
        return '-4'
    elif cs_pct >= 0.41:
        return '-3'
    elif cs_pct >= 0.31:
        return '-2'
    elif cs_pct >= 0.21:
        return '-1'
    else:
        return ''
