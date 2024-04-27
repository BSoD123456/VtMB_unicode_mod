#! python3
# coding: utf-8

import json

def load_json(fn):
    with open(fn, 'r', encoding='utf8') as fd:
        return json.load(fd)

def cmp_dict(d1, d2, path):
    m = True
    for k1, i1 in d1.items():
        if not k1 in d2:
            print(f'k1 not in d2: {path} k1')
            continue
        i2 = d2[k1]
        if isinstance(i1, dict):
            assert isinstance(i2, dict)
            if not cmp_dict(i1, i2, '/'.join([path, k1])):
                m = False
        else:
            assert i1 == '' and isinstance(i2, str)
    return m

if __name__ == '__main__':
    m = cmp_dict(
        load_json(r'tab1\output.json'),
        load_json(r'output_fin.json'),
        '.'
    )
    print(m)
