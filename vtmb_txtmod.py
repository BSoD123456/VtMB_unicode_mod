#! python3
# coding: utf-8

# VtMB Text files modifier
# Copyright (C) 2022 Tring
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
import shutil
import re
import json

TM_CFG = {
    'mod': r'G:\GOG Games\VtMB\Unofficial_Patch',
    'bak': r'G:\GOG Games\VtMB\trans_bak',
    'work': '.',
    'codec': 'utf-8',
}

def report(*args):
    r = ' '.join(args)
    print(r)
    return r

class c_parser:

    def __init__(self, cfg, dat):
        if '__parser__' in dat:
            raise RuntimeError(report('parser already inited'))
        dat['__parser__'] = self
        self.cfg = cfg
        self.dat = dat
        self.dirty = False

    def rdcfg(self, *keys, default = None):
        cfg = self.cfg
        for k in keys:
            if k in cfg:
                return cfg[k]
        return default

    def load(self, path):
        with open(path, 'rb') as fd:
            raw = fd.read()
        codec = self.rdcfg('s_codec', 'codec', default='ascii')
        try:
            self.txt = raw.decode(codec)
        except:
            raise ValueError(report('no valid codec for {path}'))

    def save(self, path):
        if not self.dirty:
            return False
        codec = self.rdcfg('d_codec', 'codec', default='ascii')
        mod = self.txt.encode(codec)
        with open(path, 'wb') as fd:
            fd.write(mod)
        return True

    def parse(self):
        return NotImplemented

    def modify(self):
        return NotImplemented

class c_dlg_parser(c_parser):

    def parse(self):
        rpatt = r'\{\s*([^\}]*?)\s*\}'
        dirty = False
        li = 0
        for line in self.txt.splitlines():
            li += 1
            lis = str(li)
            if lis in self.dat:
                pair = self.dat[lis]
            else:
                pair = {}
            for ri, m in enumerate(re.finditer(rpatt, line)):
                s = m.group(1)
                if not s:
                    continue
                if ri == 0:
                    if s != lis:
                        report('warning: missing line {lis}/{s}')
                        li = int(s)
                elif ri <= 2:
                    if not s in pair:
                        pair[s] = ''
                        dirty = True
            if not lis in self.dat and pair:
                self.dat[lis] = pair
        return dirty

    def modify(self):
        rpatt = r'(\{\s*)([^\}]*?)(\s*\})'
        rpatt_idx = r'^\{\s*(\d+)\s*\}'
        rs = []
        dirty = False
        for line in self.txt.splitlines():
            m = re.search(rpatt_idx, line)
            if not m:
                report('warning: invalid line index:\n{line}')
                rs.append(line)
                continue
            lis = m.group(1)
            if not lis in self.dat:
                rs.append(line)
                continue
            pair = self.dat[lis]
            cch = [0, False]
            def rplc(m):
                ri = cch[0]
                cch[0] += 1
                s = m.group(2)
                if not s or not 0 < ri <= 2 or not s in pair or not pair[s]:
                    return m.group(0)
                cch[1] = True
                return f'{{\t{pair[s]}\t}}'
            line = re.sub(rpatt, rplc, line)
            rs.append(line)
            dirty |= cch[1]
        if dirty:
            self.txt = self.rdcfg('newline', default='\n').join(rs)
            self.dirty = True
        return dirty

class c_lip_parser(c_parser):

    def _parse_sect(self):
        cur = []
        stack = []
        title = None
        for li, line in enumerate(self.txt.splitlines()):
            li += 1
            if not line:
                continue
            elif line == '{':
                if title is None:
                    raise ValueError(report(f'invalid lip sector at line {li}'))
                nsct = []
                cur.append((title, nsct))
                stack.append(cur)
                cur = nsct
                title = None
            elif line == '}':
                if not title is None:
                    cur.append(title)
                if not stack:
                    raise ValueError(report(f'invalid lip sector at line {li}'))
                cur = stack.pop()
                title = None                
            else:
                if ('{' in line or '}' in line) and not len(re.findall(r'\{.+\}', line)) == line.count('{') == line.count('}'):
                    raise ValueError(report(f'invalid lip sector at line {li}'))
                if not title is None:
                    cur.append(title)
                title = line
        if not title is None:
            cur.append(title)
        if stack:
            raise ValueError(report(f'invalid lip sector at line {li}'))
        return cur

    def _find_sect(self, sect, keys, idx = 0):
        r = {}
        for v in sect:
            if not isinstance(v, tuple):
                continue
            k, ctt = v
            for key in keys:
                ks = key.split('/')
                if len(ks) <= idx:
                    continue
                if ks[idx] == k:
                    if idx + 1 < len(ks):
                        nr = self._find_sect(ctt, keys, idx + 1)
                        for nk, nv in nr.items():
                            if nk in r:
                                raise ValueError(report(f'dumplicate sector {nk}'))
                            r[nk] = nv
                    else:
                        if key in r:
                            raise ValueError(report(f'dumplicate sector {key}'))
                        r[key] = ctt
        return r

    def _parse_txt(self, line):
        cch = [0]
        llen = len(line)
        def get_word():
            ed = llen
            if cch[0] >= llen:
                breakpoint()
            for i in range(cch[0], llen):
                c = line[i]
                if c == ' ':
                    ed = i
                    break
            r = line[cch[0]:ed]
            cch[0] = i + 1
            return r
        def get_quote_a():
            if not line[cch[0]] == '"':
                raise ValueError(report(f'invalid text line: {line}'))
            cch[0] += 1
            ed = None
            for i in range(cch[0], llen):
                c = line[i]
                if c == '"':
                    ed = i
            if ed is None:
                raise ValueError(report(f'invalid text line: {line}'))
            r = line[cch[0]:ed]
            cch[0] = ed + 2
            return r
        def get_quote_u():
            if not line[cch[0]] == '"':
                raise ValueError(report(f'invalid text line: {line}'))
            cch[0] += 2
            rs = []
            ed = None
            for i in range(cch[0], llen):
                c = line[i]
                if c == '"' and not (i - cch[0])%2:
                    ed = i
            if ed is None:
                raise ValueError(report(f'invalid text line: {line}'))
            r = line[cch[0]:ed]
            cch[0] = ed + 3
            codec = self.rdcfg('s_codec', 'codec', default='ascii')
            return r.encode(codec).decode('utf-16le')
        if not get_word() == 'PHRASE':
            raise ValueError(report(f'invalid text line: {line}'))
        typ = get_word()
        if not typ in ['char', 'unicode']:
            raise ValueError(report(f'invalid text line: {line}'))
        clen = get_word()
        if not clen.isdigit():
            raise ValueError(report(f'invalid text line: {line}'))
        clen = int(clen)
        if clen == 0:
            return ''
        if typ == 'char':
            txt = get_quote_a()
        else:
            txt = get_quote_u()
        try:
            float(get_word())
            float(get_word())
        except:
            raise ValueError(report(f'invalid text line: {line}'))
        #check clen
        return txt

    def parse(self):
        dirty = False
        sect = self._parse_sect()
        dst_sects = self._find_sect(sect, ['english', 'OPTIONS', 'CLOSECAPTION/english'])
        if 'english' in dst_sects and 'CLOSECAPTION/english' in dst_sects:
            raise ValueError(report(f'dumplicate sector english'))
        elif 'english' in dst_sects:
            txt_sect = dst_sects['english']
        elif 'CLOSECAPTION/english' in dst_sects:
            txt_sect = dst_sects['CLOSECAPTION/english']
        else:
            return False
        if not 'OPTIONS' in dst_sects:
            raise ValueError(report(f'missing sector OPTIONS'))
        else:
            opt_sect = dst_sects['OPTIONS']
        spk_name = None
        for line in opt_sect:
            if not isinstance(line, str):
                raise ValueError(report(f'invalid sect item: {line}'))
            opt = line.split()
            if len(opt) < 1:
                raise ValueError(report(f'invalid option item: {line}'))
            elif len(opt) == 1:
                k = opt[0]
                v = ''
            elif len(opt) > 2:
                k = opt[0]
                v = line[len(k)+1:]
            else:
                k, v = opt
            if k == 'speaker_name':
                spk_name = v
                break
        if spk_name is None:
            raise ValueError(report(f'missing speaker_name'))
        if len(txt_sect) != 1:
            raise ValueError(report(f'invalid sector english'))
        line = txt_sect[0]
        if not isinstance(line, str):
            raise ValueError(report(f'invalid sect item: {line}'))
        line = self._parse_txt(line)
        if not spk_name in self.dat:
            self.dat[spk_name] = ''
            dirty = True
        if not line in self.dat:
            self.dat[line] = ''
            dirty = True
        return dirty

class c_txt_mod:

    def __init__(self, cfg, prs_tab, fname):
        self.cfg = cfg
        self.parser = prs_tab
        self.fpath = os.path.join(cfg['work'], fname)
        self.dirty = False
        self.load()

    @staticmethod
    def _ensure_path(path):
        dpath = os.path.dirname(path)
        if not os.path.exists(dpath):
            os.makedirs(dpath)

    def load(self):
        if not os.path.exists(self.fpath):
            self.dat = {}
            return False
        with open(self.fpath, 'r', encoding=self.cfg['codec']) as fd:
            try:
                self.dat = json.load(fd)
            except:
                report(f'warning: invalid work file: {self.fpath}')
                self.dat = {}
                return False
        return True

    def _to_json(self, obj):
        if isinstance(obj, (list, tuple)):
            return [self._to_json(i) for i in obj]
        elif isinstance(obj, dict):
            return {k: self._to_json(v) for k, v in obj.items() if not isinstance(k, str) or k[:2] != '__'}
        else:
            return obj

    def save(self):
        if not self.dirty:
            return False
        report(f'auto save work file to {self.fpath}')
        self._ensure_path(self.fpath)
        with open(self.fpath, 'w', encoding=self.cfg['codec']) as fd:
            json.dump(self._to_json(self.dat), fd, ensure_ascii=False, indent=4, sort_keys=False)
        return True

    def _parse(self, path):
        apath = os.path.join(self.cfg['mod'], path)
        for fn in os.listdir(apath):
            fpath = os.path.join(path, fn)
            afpath = os.path.join(apath, fn)
            if os.path.isdir(afpath):
                self._parse(fpath)
                continue
            ext = os.path.splitext(fn)[-1][1:]
            if not ext in self.parser:
                continue
            if ext in self.dat:
                edat = self.dat[ext]
            else:
                edat = {}
                self.dat[ext] = edat
            if fpath in edat:
                fdat = edat[fpath]
            else:
                fdat = {}
                edat[fpath] = fdat
            if '__parser__' in fdat:
                psr = fdat['__parser__']
            else:
                cfg = self.parser[ext]
                psr = cfg['parser'](cfg, fdat)
                bfpath = os.path.join(self.cfg['bak'], fpath)
                if os.path.exists(bfpath):
                    psr.load(bfpath)
                else:
                    psr.load(afpath)
            try:
                self.dirty |= psr.parse()
            except Exception as ex:
                report(f'error at {fpath}')
                raise ex

    def parse(self):
        self._parse('')

    def modify(self):
        for edat in self.dat.values():
            for fpath, fdat in edat.items():
                if not '__parser__' in fdat:
                    report('warning: modify before parse: {fpath}')
                    continue
                psr = fdat['__parser__']
                psr.modify()
                if not psr.dirty:
                    continue
                report(f'modify {fpath}')
                afpath = os.path.join(self.cfg['mod'], fpath)
                bfpath = os.path.join(self.cfg['bak'], fpath)
                if not os.path.exists(bfpath):
                    report(f'bak {afpath} to {bfpath}')
                    self._ensure_path(bfpath)
                    shutil.copy2(afpath, bfpath)
                psr.save(afpath)
                psr.dirty = False

MOD_TXTS = {
    'dlg': {
        'parser': c_dlg_parser,
        's_codec': 'windows-1250',
        'd_codec': 'gbk',
        'newline': '\r\n',
    },
    'lip': {
        'parser': c_lip_parser,
        's_codec': 'windows-1250',
        'd_codec': 'gbk',
        'newline': '\r\n',
    },
}

if __name__ == '__main__':
    from pprint import pprint as ppr
    tm = c_txt_mod(TM_CFG, MOD_TXTS, 'output.json')
    tm.parse()
    tm.modify()
    tm.save()
