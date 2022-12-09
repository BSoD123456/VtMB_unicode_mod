#! python3
# coding: utf-8

# VtMB Text files Fixer
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
import re

TF_CFG = {
    'root': r'G:\GOG Games\VtMB\Unofficial_Patch',
}

SYM_AUTOFILL = '@'

def report(*args):
    r = ' '.join(args)
    print(r)
    return r

class c_fixer:

    def __init__(self, cfg, path):
        self.path = path
        self.cfg = cfg
        self.dirty = False

    def rdcfg(self, *keys, default = None):
        cfg = self.cfg
        for k in keys:
            if k in cfg:
                return cfg[k]
        return default

    def load(self):
        with open(self.path, 'rb') as fd:
            self.raw = fd.read()
        for codec in self.rdcfg('codec', default=['windows-1250']):
            try:
                self.txt = self.raw.decode(codec)
                self.codec = codec
                break
            except:
                pass
        else:
            raise UnicodeDecodeError(report('no valid codec for {self.path}'))
        self.parse()

    def save(self):
        if not self.dirty:
            return False
        self.mod = self.txt.encode(self.codec)
        with open(self.path, 'wb') as fd:
            fd.write(self.mod)
        return True

    @property
    def s_codec(self):
        return self.rdcfg('s_codec', 'codec', default='windows-1250')

    @property
    def d_codec(self):
        return self.rdcfg('d_codec', 'codec', default='gbk')

    def parse(self):
        return NotImplemented

    def fix(self):
        return NotImplemented

class c_dlg_fixer(c_fixer):

    def __init__(self, cfg, path):
        super().__init__(cfg, path)

    def _replace_item(self, lidx, ridx, content, prev_content):
        if not ridx == 2 or not content or not content[0] == SYM_AUTOFILL:
            return content
        report(f'auto fill line {lidx} in {self.path}:\n{content}\n->\n{prev_content}')
        self.dirty = True
        return prev_content

    def fix(self):
        rpatt = r'\{(\s)(?:([^\}]+)(\s)|)\}'
        rpatt_rgh = r'\{([^\}]*)\}'
        rs = []
        for li, line in enumerate(self.txt.splitlines()):
            li += 1
            def fix_spc(m):
                s = m.group(1)
                st = s.strip()
                if not st:
                    return m.group(0)
                m1 = re.search('^\s', s)
                m1 = m1.group(0) if m1 else '\t'
                m2 = re.search('\s$', s)
                m2 = m2.group(0) if m2 else m1
                r = f'{m1}{st}{m2}'
                if r != s:
                    report(f'pad space line {li} in {self.path}: {st}')
                    self.dirty = True
                    return f'{{{r}}}'
                else:
                    return m.group(0)
            if not re.match('^' + rpatt * 13 + '$', line):
                if not re.match('^' + rpatt_rgh * 13 + '$', line):
                    report(f'warning: invalid line {li} in {self.path}:\n{line}')
                    rs.append(line)
                    continue
                line = re.sub(rpatt_rgh, fix_spc, line)
                assert re.match('^' + rpatt * 13 + '$', line)
            cch = [0, '']
            def rplc(m):
                ri, prv_ctt = cch
                cch[0] += 1
                s1 = m.group(1)
                ctt = m.group(2)
                if ctt:
                    s2 = m.group(3)
                else:
                    s2 = s1
                rls = ['{', s1]
                r = self._replace_item(li, ri, ctt, prv_ctt)
                if r:
                    rls.append(r)
                    rls.append(s2)
                rls.append('}')
                cch[1] = ctt
                return ''.join(rls)
            line = re.sub(rpatt, rplc, line)
            rs.append(line)
        self.txt = self.rdcfg('newline', default='\n').join(rs)

class c_txt_fixer:

    def __init__(self, cfg, fx_tab):
        self.cfg = cfg
        self.fx = fx_tab

    def fix_all(self):
        return self.fix(self.cfg['root'])

    def fix(self, path):
        dirty = False
        for fn in os.listdir(path):
            fpath = os.path.join(path, fn)
            if os.path.isdir(fpath):
                dirty |= self.fix(fpath)
                continue
            ext = os.path.splitext(fn)[-1][1:]
            if not ext in self.fx:
                continue
            cfg = self.fx[ext]
            fx = cfg['fixer'](cfg, fpath)
            fx.load()
            fx.fix()
            fx.save()
            dirty |= fx.dirty
        return dirty

MOD_TXTS = {
    'dlg': {
        'fixer': c_dlg_fixer,
        'codec': ['gbk', 'windows-1250'],
        'newline': '\r\n',
    },
}

if __name__ == '__main__':
    from pprint import pprint as ppr
    tf = c_txt_fixer(TF_CFG, MOD_TXTS)
    fx = tf.fix_all()
