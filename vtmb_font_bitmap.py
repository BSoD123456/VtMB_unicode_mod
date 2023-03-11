#! python3
# coding: utf-8

# VtMB Terminal font generator
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

try:
    from PIL import Image, ImageDraw, ImageFont
except:
    print('''Install Pillow with
pip3 install pillow
or
pip install pillow
''')
    raise

# form https://github.com/Angelic47/FontChinese7x7
#FONT_NAME = 'font/guanzhi.ttf'
# from https://www.fontke.com/font/12809313/
FONT_NAME = 'font/XiaoDianZhen.ttf'

FONT_CODEC = 'gbk'

class c_font_bitmap:

    def __init__(self, font_name, font_size):
        self.size = font_size
        try:
            font = ImageFont.FreeTypeFont(font_name, font_size)
        except:
            font_name = os.path.basename(os.path.splitext(font_name)[0])
            font = ImageFont.truetype(font_name, font_size)
        self.font = font
        self.img = Image.new("1", (font_size, font_size), color=0xff)
        self.idr = ImageDraw.Draw(self.img)
        self.char_blank = self.get_char('\0')

    def _draw_char(self, c):
        self.idr.rectangle([(0, 0), self.img.size], fill=0xff)
        self.idr.text((0, 0), c, fill=0, font=self.font, spacing=0)

    def get_char(self, c):
        self._draw_char(c)
        d = self.img.getdata()
        r = [0] * ((len(d)-1) // 8 + 1)
        for i, v in enumerate(d):
            if not v:
                r[i//8] |= (1<<(7-(i%8)))
        return r

    def charset_empty(self, num):
        for i in range(num):
            yield self.char_blank

    def charset_ascii(self):
        for i in range(0x80):
            try:
                yield self.get_char(chr(i))
            except:
                yield self.char_blank

    def charset_ansi(self, codec):
        for h in range(0x81, 0x100):
            for l in range(0x100):
                c = bytes.fromhex('{:04X}'.format((h<<8)+l))
                try:
                    s = c.decode(codec)
                except:
                    yield self.char_blank
                else:
                    try:
                        yield self.get_char(s)
                    except:
                        yield self.char_blank

def vtmb_fbm_charset():
    try:
        fbm = c_font_bitmap(FONT_NAME, 8)
    except:
        raise RuntimeError(
            f'font {font_path} is not valid. please download it by yourself.')
    rs = []
    for r in fbm.charset_empty(0x80):
        rs.extend(r)
    for r in fbm.charset_ascii():
        rs.extend(r)
    for r in fbm.charset_ansi(FONT_CODEC):
        rs.extend(r)
    return bytes(rs)

if __name__ == '__main__':
    pass
