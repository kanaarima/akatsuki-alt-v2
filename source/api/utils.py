def merge_dict(source: dict, target: dict):
    for key in source.keys():
        if key not in target:
            target[key] = source[key]


def update_dicts(a: dict, b: dict):
    merge_dict(a, b)
    merge_dict(b, a)
