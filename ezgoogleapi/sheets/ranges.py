import string
import numpy as np

all_columns = list(string.ascii_uppercase) + [c + d for c in string.ascii_uppercase for d in string.ascii_uppercase]


def _get_numerics(range_):
    re_val = {}
    if type(range_) == str:
        re_val['start'] = int("".join([char for char in range_ if char.isdigit()]))
        re_val['end'] = re_val['start']
        return re_val
    try:
        re_val['start'] = int("".join([char for char in range_[0] if char.isdigit()]))
    except ValueError:
        re_val['start'] = None
    try:
        re_val['end'] = int("".join([char for char in range_[1] if char.isdigit()]))
    except ValueError:
        re_val['end'] = None

    return re_val


def _get_alpha(range_):
    if type(range_) == str:
        return {'start': "".join([char for char in range_ if char.isalpha()]),
            'end': "".join([char for char in range_ if char.isalpha()])}
    return {'start': "".join([char for char in range_[0] if char.isalpha()]),
            'end': "".join([char for char in range_[1] if char.isalpha()])}


def _get_ranges(range_):
    if '!' in range_:
        range_ = range_.split('!')[1]
    if ':' in range_:
        range_ = range_.split(':')

    rows = _get_numerics(range_)
    columns = _get_alpha(range_)

    if not rows['start']:
        if not rows['end']:
            index = []
        else:
            index = np.arange(1, rows['end'] + 1)
    else:
        if not rows['end']:
            index = rows['start']
        else:
            index = np.arange(rows['start'], rows['end'] + 1)

    col_range = _get_columns(start=columns['start'], end=columns['end'])

    return index, col_range


def _get_columns(start=None, end=None, width=None):
    if not width:
        try:
            ia = all_columns.index(start)
            ib = all_columns.index(end)
            cols = [col for col in all_columns if all_columns.index(col) in range(ia, ib + 1)]
            return cols
        except ValueError:
            return None

    return [col for col in all_columns if all_columns.index(col) in range(width)]


if __name__ == '__main__':
    print(_get_ranges('A:A'))
