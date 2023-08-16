import datetime


def merge_dict(source: dict, target: dict) -> None:
    for key in source.keys():
        if key not in target:
            target[key] = source[key]


def update_dicts(a: dict, b: dict) -> None:
    merge_dict(a, b)
    merge_dict(b, a)


def find_unique(check_func, iterA, iterB):
    a = list()
    b = list()
    for x in iterA:
        for y in iterB:
            if check_func(x, y):
                break
        else:
            continue
        a.append(x)
    for x in iterB:
        for y in iterA:
            if check_func(x, y):
                break
        else:
            continue
        b.append(x)
    return (a, b)


def yesterday() -> datetime.datetime:
    return (datetime.datetime.today() - datetime.timedelta(days=1)).date()
