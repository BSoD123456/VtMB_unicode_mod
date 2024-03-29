#! python3
# coding: utf-8

# Paratranz files converter
# Copyright (C) 2023 Tring
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of  MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see <http://www.gnu.org/licenses/>.

import os, os.path
import json

from glbcfg import GLB_CFG

RAW_FILE = 'output.json'
PRTZ_PATH = 'paratranz_out'

WORK_PATH = GLB_CFG.rdcfg('work')

def report(*args):
    r = ' '.join(args)
    print(r)
    return r

class c_min:
    def __lt__(s, d):
        return s != d
    def __gt__(s, d):
        return False
VMIN = c_min()

class c_paratranz_convert:

    def __init__(self, raw_name, paratranz_path, codec = 'utf-8'):
        self.raw_name = raw_name
        self.prtz_path = paratranz_path
        self.codec = codec

    @staticmethod
    def _ensure_path(path):
        dpath = os.path.dirname(path)
        if dpath and not os.path.exists(dpath):
            os.makedirs(dpath)

    @staticmethod
    def _prtz_item(key, orig, trans, ctxt = None):
        r = {
            'key': key,
            'original': orig,
            'translation': trans,
        }
        if ctxt:
            r['context'] = ctxt
        return r

    @staticmethod
    def _prtz_key(item):
        return item['key']

    @staticmethod
    def _prtz_pair(item):
        return item['original'], item['translation']

    @staticmethod
    def _prtz_cmt(item):
        return item['context'] if 'context' in item else None

    @staticmethod
    def _trim_file_name(fn):
        kn, ext = os.path.splitext(fn)
        rs = []
        ns = kn.split('_')
        for n in ns:
            if len(n) == 1:
                continue
            r = []
            for c in n:
                if not c.isdigit():
                    r.append(c)
            if r:
                rs.append(''.join(r))
        return '_'.join(rs) + ext

    @staticmethod
    def _sort_file_name(dat, cb_key):
        keys = {}
        alldone = [False]
        def _key_gen(fn):
            ns = os.path.splitext(fn)[0].split('_')
            for n in ns:
                st = 0
                isdgt = False
                for i, c in enumerate(n):
                    if c.isdigit() == isdgt:
                        continue
                    if i > st:
                        if isdgt:
                            yield f'{int(n[st:i]):08}'
                        else:
                            yield n[st:i]
                    isdgt = not isdgt
                    st = i
                if st < len(n):
                    if isdgt:
                        yield f'{int(n[st:]):08}'
                    else:
                        yield n[st:]
            while True:
                yield ''
        def _key(itm):
            fn = cb_key(itm)
            if not fn in keys:
                keys[fn] = _key_gen(fn)
            k = next(keys[fn])
            if k != '':
                alldone[0] = False
            return k
        while not alldone[0]:
            alldone[0] = True
            dat.sort(key = _key)

    def _load_json(self, fn):
        if not os.path.exists(fn):
            return None
        with open(fn, 'r', encoding = self.codec) as fd:
            try:
                dat = json.load(fd)
            except:
                report(f'warning: invalid json file: {fn}')
                return None
        return dat

    def _save_json(self, fn, dat):
        self._ensure_path(fn)
        with open(fn, 'w', encoding = self.codec) as fd:
            json.dump(dat, fd, ensure_ascii=False, indent=4, sort_keys=False)

    def raw2prtz(self):
        if self.load_raw():
            self.save_prtz()

    def prtz2raw(self):
        if self.load_prtz():
            self.save_raw()

    def load_raw(self):
        dat = self._load_json(self.raw_name)
        if not dat:
            self.dat = {}
            return False
        self.dat = dat
        return True

    def save_raw(self):
        self._save_json(self.raw_name, self.dat)

    def save_prtz(self):
        r = self.save_prtz_dlg()
        r = self.save_prtz_lip() or r
        return r

    def save_prtz_dlg(self):
        try:
            dat = self.dat['dlg']
        except:
            report(f'warning: no dlg data found')
            return False
        for fpath, txts in dat.items():
            rs = []
            for idx, txt in txts.items():
                for k, t in txt.items():
                    (s, d), = ((s, d) for s, d in t.items())
                    if not (s or d):
                        continue
                    if k == 'common':
                        idxext = ''
                    else:
                        idxext = '#' + k
                    rs.append(self._prtz_item(idx + idxext, s, d))
            rs.sort(key = lambda itm: int(self._prtz_key(itm).split('#')[0]))
            if rs:
                self._save_json(
                    os.path.join(self.prtz_path, fpath + '.json'), rs)
        return True

    def save_prtz_lip(self):
        try:
            dat = self.dat['lip']
        except:
            report(f'warning: no lip data found')
            return False
        rs = {}
        rt = {}
        for fpath, txts in dat.items():
            tlen = len(txts)
            if tlen == 0:
                continue
            elif tlen == 1:
                (s, d), = ((k, v) for k, v in txts.items())
                assert not s and not d
                continue
            fkey, fname = os.path.split(fpath)
            fkey = os.path.join(fkey, self._trim_file_name(fname))
            for i, (s, d) in enumerate(txts.items()):
                if i == 0:
                    ttl_s = s
                    ttl_d = d
                    if ttl_s:
                        _n1, _n2 = os.path.splitext(fkey)
                        fkey = ''.join([_n1, '-' + ttl_s.lower(), _n2])
                    cmt = None
                    if (ttl_s or ttl_d) and fkey in rs:
                        o_ttl_s, o_ttl_d = rt[fkey]
                        if o_ttl_s != ttl_s:
                            if o_ttl_s.lower() == ttl_s.lower():
                                report(f'warning: unmatch title in case {o_ttl_s}/{ttl_s}: {fpath}')
                                cmt = ttl_s
                            else:
                                raise ValueError(report(
                                    f'error: unmatch title for lip: {fpath}'))
                        if o_ttl_d and ttl_d:
                            if o_ttl_d != ttl_d:
                                raise ValueError(report(
                                    f'error: unmatch title for lip: {fpath}'))
                        elif ttl_d:
                            rt[fkey][1] = ttl_d
                    elif not fkey in rs:
                        rt[fkey] = [ttl_s, ttl_d]
                        rs[fkey] = []
                    continue
                if s or d:
                    if i < tlen - 1:
                        _n = '#'.join((fname, str(i)))
                        _c = None
                    else:
                        _n = fname
                        _c = cmt
                    rs[fkey].append(self._prtz_item(_n, s, d, _c))
        for fkey, itms in rs.items():
            r = []
            ttl_s, ttl_d = rt[fkey]
            if ttl_s or ttl_d:
                r.append(self._prtz_item('title', ttl_s, ttl_d))
            self._sort_file_name(itms, self._prtz_key)
            r.extend(itms)
            if r:
                self._save_json(
                    os.path.join(self.prtz_path, fkey + '.json'), r)
        return True

    def _load_prtz(self, path):
        apath = os.path.join(self.prtz_path, path)
        for fn in os.listdir(apath):
            fpath = os.path.join(path, fn)
            afpath = os.path.join(apath, fn)
            if os.path.isdir(afpath):
                self._load_prtz(fpath)
                continue
            fname, ext = os.path.splitext(fn)
            if ext != '.json':
                continue
            kname, ext = os.path.splitext(fname)
            if ext == '.dlg':
                rdat = self.dat['dlg']
                dat = self.load_prtz_dlg(afpath)
                if not dat:
                    continue
                key = os.path.join(path, fname)
                assert not key in rdat
                rdat[key] = dat
            elif ext == '.lip':
                rdat = self.dat['lip']
                for fkey, dat in self.load_prtz_lip(afpath):
                    key = os.path.join(path, fkey)
                    assert not key in rdat
                    rdat[key] = dat

    def load_prtz(self):
        self.dat = {
            'dlg': {},
            'lip': {},
        }
        self._load_prtz('')
        return self.dat['dlg'] or self.dat['lip']

    def load_prtz_dlg(self, fn):
        dat = self._load_json(fn)
        if not dat:
            return None
        rs = {}
        for itm in dat:
            key = self._prtz_key(itm)
            s, d = self._prtz_pair(itm)
            idxs = key.split('#')
            assert 1 <= len(idxs) <= 2
            idx = idxs[0]
            ikey = idxs[1] if len(idxs) == 2 else 'common'
            if not idx in rs:
                rs[idx] = {}
            rs[idx][ikey] = {s: d}
        return rs

    def load_prtz_lip(self, fn):
        dat = self._load_json(fn)
        if not dat:
            return
        ttl = ('', '')
        cch = {}
        for i, itm in enumerate(dat):
            key = self._prtz_key(itm)
            s, d = self._prtz_pair(itm)
            cmt = self._prtz_cmt(itm)
            if key == 'title':
                assert i == 0
                ttl = (s, d)
                continue
            elif '#' in key:
                cch[s] = d
                continue
            rdat = {}
            if cmt:
                rdat[cmt] = ttl[1]
            else:
                rdat[ttl[0]] = ttl[1]
            if cch:
                rdat.update(cch)
                cch = {}
            rdat[s] = d
            yield key, rdat

    def _cmp(self, v1, v2, path):
        if type(v1) != type(v2):
            report(f'1!=2: type {type(v1)} / {type(v2)} ({path})')
        elif isinstance(v1, (list, tuple)):
            self._cmp_list(v1, v2, path)
        elif isinstance(v1, dict):
            self._cmp_dict(v1, v2, path)
        elif v1 != v2:
            report(f'1!=2: {v1} / {v2} ({path})')

    def _cmp_empty(self, v):
        if isinstance(v, dict):
            r = True
            for k, i in v.items():
                if k or not self._cmp_empty(i):
                    r = False
                    break
            if not r:
                return self._cmp_empty_lip(v)
            return r
        elif isinstance(v, (list, tuple)):
            r = True
            for i in v:
                if not self._cmp_empty(i):
                    r = False
                    break
            return r
        else:
            return not v

    def _cmp_empty_lip(self, v):
        if len(v) > 2:
            return False
        for i in v.values():
            if not isinstance(i, str):
                return False
        if len(v) < 2:
            return True
        elif len(v) == 2:
            if '' in v and v[''] == '':
                return True
        return False

    def _cmp_dict(self, d1, d2, path):
        for k in d1:
            dpath = ','.join([path, k])
            v1 = d1[k]
            if not k in d2:
                if not self._cmp_empty(v1):
                    report(f'1+: {k} ({dpath})')
                continue
            v2 = d2[k]
            self._cmp(v1, v2, dpath)
        for k in d2:
            if k in d1:
                continue
            if not self._cmp_empty(d2[k]):
                dpath = ','.join([path, k])
                report(f'2+: {k} ({dpath})')

    def _cmp_list(self, s1, s2, path):
        if len(s1) != len(s2):
            report(f'1!=2: len {len(s1)} / {len(s2)} ({path})')
        for i in range(len(s1)):
            v1 = s1[i]
            v2 = s2[i]
            dpath = dpath = ','.join([path, str(i)])
            self._cmp(v1, v2, dpath)

    def compare(self):
        self.load_raw()
        dat_raw = self.dat
        self.load_prtz()
        dat_prtz = self.dat
        self._cmp(dat_raw, dat_prtz, 'root')

def main(pc):
    while True:
        print(
'''1, raw -> paratranz
2, paratranz -> raw
3, compare
0, quit
''')
        v = input('Choose(1/2/3/0):')
        if v == '1':
            return pc.raw2prtz()
        elif v == '2':
            return pc.prtz2raw()
        elif v == '3':
            return pc.compare()
        elif v == '0':
            break
        
if __name__ == '__main__':
    pc = c_paratranz_convert(
        os.path.join(WORK_PATH, RAW_FILE),
        os.path.join(WORK_PATH, PRTZ_PATH),
    )
    main(pc)
