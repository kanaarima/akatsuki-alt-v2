import datetime


def merge_dict(source: dict, target: dict) -> None:
    for key in source.keys():
        if key not in target:
            target[key] = source[key]


def update_dicts(a: dict, b: dict) -> None:
    merge_dict(a, b)
    merge_dict(b, a)


def yesterday() -> datetime.datetime:
    return (datetime.datetime.today() - datetime.timedelta(days=1)).date()
