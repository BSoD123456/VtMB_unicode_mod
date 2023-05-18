#! python3
# coding: utf-8

import os, os.path
import shutil
import json

BAS_PATH = r'E:\temp\tabletmp\paratranz_out'
MOD_PATH = r'E:\temp\tabletmp\work\paratranz_out'
OUT_PATH = r'E:\temp\tabletmp\paratranz_out_merge'

def report(*args):
    r = ' '.join(args)
    print(r)
    return r

def merge_dir(bas, mod, out):
    if os.path.exists(out):
        if os.path.isdir(out):
            shutil.rmtree(out)
        else:
            os.remove(out)
    if not os.path.exists(bas):
        raise ValueError(report('error:', f'not exists: {bas}'))
    elif not os.path.exists(mod):
        shutil.copy(bas, ensure_path(out))
        report('warning:', f'not exists: {mod}')
        return
    elif not os.path.isdir(bas) and not os.path.isdir(mod):
        return merge_file(bas, mod, out)
    elif not os.path.isdir(bas) or not os.path.isdir(mod):
        raise ValueError(report('error:', f'file/dir not match: {bas}|{mod}'))
    for fn in os.listdir(bas):
        bfn = os.path.join(bas, fn)
        mfn = os.path.join(mod, fn)
        ofn = os.path.join(out, fn)
        merge_dir(bfn, mfn, ofn)

def ensure_path(path):
    dpath = os.path.dirname(path)
    if dpath and not os.path.exists(dpath):
        os.makedirs(dpath)
    return path

def load_json(fn):
    if os.path.splitext(fn)[1] != '.json':
        return None
    with open(fn, 'r', encoding = 'utf8') as fd:
        try:
            dat = json.load(fd)
        except:
            report('warning:', f'invalid json file: {fn}')
            return None
    return dat

def save_json(fn, dat):
    with open(ensure_path(fn), 'w', encoding = 'utf8') as fd:
        json.dump(dat, fd, ensure_ascii=False, indent=4, sort_keys=False)

IMPORT_KEYS = ['key', 'original', 'context']
TRANS_KEY = 'translation'

def merge_file(bas, mod, out, ikeys = IMPORT_KEYS, tkey = TRANS_KEY):
    bdat = load_json(bas)
    if not bdat:
        return
    mdat = load_json(mod)
    if not mdat:
        shutil.copyfile(bas, ensure_path(out))
        report('warning:', f'file is empty: {mod}')
        return
    bat_rpt_log = {}
    def batch_report(typ, key):
        if not typ in bat_rpt_log:
            bat_rpt_log[typ] = []
        bat_rpt_log[typ].append(key)
    def batch_report_done():
        if not bat_rpt_log:
            return
        rtxts = []
        rtxts.append(f'in {bas}:')
        for typ, keys in bat_rpt_log.items():
            ktxt = ', '.join(keys)
            rtxts.append(f'  {typ} items: {ktxt}')
        report('warning:', '\n'.join(rtxts))
    mlen = len(mdat)
    mwlk = set()
    for bidx, bitm in enumerate(bdat):
        midx = 0
        while midx < mlen:
            if midx in mwlk:
                midx += 1
                continue
            mitm = mdat[midx]
            midx += 1
            for ikey in ikeys:
                if not ikey in bitm:
                    continue
                elif not ikey in mitm or bitm[ikey] != mitm[ikey]:
                    break
            else:
                mwlk.add(midx - 1)
                break
        else:
            batch_report('unfilled', bitm['key'])
            continue
        if not tkey in mitm:
            batch_report('empty', mitm['key'])
            continue
        if tkey in bitm and bitm[tkey]:
            batch_report('overwrite', bitm['key'])
        bitm[tkey] = mitm[tkey]
    batch_report_done()
    save_json(out, bdat)

if __name__ == '__main__':
    merge_dir(BAS_PATH, MOD_PATH, OUT_PATH)
