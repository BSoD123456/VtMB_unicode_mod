#! python3
# coding: utf-8

import json

class c_global_config:

    def __init__(self, fname, codec, default):
        self.fname = fname
        self.codec = codec
        self.dat = default
        self.load()

    def load(self):
        try:
            with open(self.fname, 'r', encoding=self.codec) as fd:
                dat = json.load(fd)
        except:
            print('use default global config.')
            self.save()
        else:
            self.dat.update(dat)

    def save(self):
        with open(self.fname, 'w', encoding=self.codec) as fd:
            json.dump(self.dat, fd, ensure_ascii=False, indent=4, sort_keys=False)

    def rdcfg(self, *keys, default = None):
        cfg = self.dat
        for k in keys:
            if k in cfg:
                return cfg[k]
        return default

GLB_CFG = c_global_config('config.json', 'utf-8', {
    'game': r'G:\GOG Games\VtMB',
    'work': '.',
})
