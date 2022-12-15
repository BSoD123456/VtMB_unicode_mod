#! python3
# coding: utf-8

# VtMB Injector for GBK support
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

import sys
import os, os.path
import shutil
from hashlib import md5 as _md5

try:
    import iced_x86 as X
    from iced_x86 import Instruction as I, Code as C, Register as R, MemoryOperand as M
except:
    print('''Install iced-x86 with
pip3 install iced-x86
or
pip install iced-x86
''')
    sys.exit()

from glbcfg import GLB_CFG

PP_CFG = {
    'root': GLB_CFG.rdcfg('game'),
    'bitness': 32,
}

def shift_mem(src_len, shft_len):
    def _shift(addr, pe):
        s_offs, d_offs = pe.shift(addr, src_len, shft_len)
        return f'offs:0x{s_offs:08X}/0x{s_offs+src_len-1:08X} -> offs:0x{d_offs:08X}/0x{d_offs+src_len-1:08X} shift(n:0x{shft_len:04X})'
    return _shift

class c_label_ctx:
    def __init__(self):
        self.tab = {}
    def lb(self, name):
        if not name in self.tab:
            self.tab[name] = len(self.tab) + 1
        return self.tab[name]
    def add(self, name, ins):
        ins.ip = self.lb(name)
        return ins

def with_label_ctx(func):
    return func(c_label_ctx())

MOD_DLLS = {
    'vguimatsurface': {
        'path': 'Bin',
        'file': 'vguimatsurface.dll',
        'md5':  '0e8c1c67e4a4c7f227e4b5fa9e7e3eee',
        'patch': (lambda base_addr, code_ext, data_ext, hooks, funcs:[
            (0x38954, b'GetGlyphOutlineW'), # ipt replace GetGlyphOutlineA to GetGlyphOutlineW
            (code_ext - 1, b'\xcc\xcc'), # force extend code sect
            (data_ext - 1, b'\x00\x00\x00\x00\x00'), # force extend data sect
            # CMatSystemSurface::DrawUnicodeChar
            (0x0f1c0, [
                I.create_branch(C.JMP_REL32_32, code_ext + hooks[0]),
            ]),
            (0x0f24c, [
                I.create_reg_reg(C.MOV_R32_RM32, R.EBX, R.EAX),
            ]),
            (0x0f284, shift_mem(0x30, 1)),
            (0x0f282, [
                I.create_reg_reg(C.MOV_R16_RM16, R.AX, R.BX),
            ]),
##            (0x0f2a3, [
##                I.create_branch(C.JMP_REL32_32, code_ext + hooks[k]),
##                I.create(C.NOPD),
##                I.create(C.NOPD),
##                I.create(C.NOPD),
##            ]),
            (0x0f2b5, [
                I.create_reg_reg(C.MOVZX_R32_RM16, R.EBX, R.BX),
            ]),
            # CMatSystemSurface::DrawPrintText
            (0xf7bb, shift_mem(0x13, -1)),
            (0xf7b7, [
                I.create_reg_reg(C.MOV_R16_RM16, R.BX, R.AX),
            ]),
            (0xf7ca, [
                I.create_mem_reg(C.MOV_RM16_R16, M(R.EBP, displ=-0x44, displ_size=1), R.BX),
            ]),
            (0xf7e5, [
                I.create_reg_reg(C.MOVZX_R32_RM16, R.EBX, R.BX),
                I.create(C.NOPD),
            ]),
##            (0xf81d, [
##                I.create(C.NOPD),
##                I.create(C.NOPD),
##                I.create(C.NOPD),
##                I.create(C.NOPD),
##                I.create(C.NOPD),
##                I.create(C.NOPD),
##            ]),
            # CFontAmalgam::GetFontForChar
            (0x15dc0, [
                I.create_branch(C.JMP_REL32_32, code_ext + hooks[2]),
                I.create(C.NOPD),
            ]),
            # CWin32Font::Create
            (0x15f7a, [
                I.create_reg_u32(C.MOV_R8_IMM8, R.AL, 134), #GB2312
                I.create(C.NOPD),
            ]),
            # CWin32Font::GetCharABCWidths
            (0x16380, [
                I.create_branch(C.JMP_REL32_32, code_ext + hooks[1]),
                I.create(C.NOPD),
                I.create(C.NOPD),
            ]),
            # call GetCharABCWidthsW -> call GetCharABCWidthsA
##            (0x163c7, [
##                I.create_mem(C.CALL_RM32, M(displ=0x10036020, displ_size=4)),
##            ]),
            # get_char_info_ctype <- iswcntrl/iswspace/...
            (0x2bd9c, [
                I.create_branch(C.JMP_REL32_32, code_ext + hooks[3]),
                I.create(C.NOPD),
                I.create(C.NOPD),
                I.create(C.NOPD),
                I.create(C.NOPD),
                I.create(C.NOPD),
            ]),
            # hooks for DrawUnicodeChar
            (code_ext + hooks[0], with_label_ctx(lambda lbc: [
                I.create_mem_u32(C.AND_RM32_IMM32, M(R.ESP, displ=0x4, displ_size=1), 0xffff),
                I.create_mem_u32(C.MOV_RM8_IMM8, M(displ=base_addr+data_ext+2, displ_size=4), 0),
                I.create_reg(C.PUSH_R32, R.ECX),
                I.create_reg_mem(C.MOV_R16_RM16, R.AX, M(R.ESP, displ=0x8, displ_size=1)),
                I.create_reg_u32(C.CMP_RM16_IMM16, R.AX, 0x100),
                I.create_branch(C.JB_REL32_32, lbc.lb('handle')),
                I.create_reg_u32(C.CMP_RM16_IMM16, R.AX, 0xff00),
                I.create_branch(C.JB_REL32_32, lbc.lb('ret')),
                I.create_reg_reg(C.MOVZX_R16_RM8, R.AX, R.AL),
                #handle
                lbc.add('handle',
                    I.create_reg_u32(C.CMP_RM8_IMM8, R.AL, 0x40),
                ),
                I.create_branch(C.JB_REL32_32, lbc.lb('ret')),
                #read log
                I.create_reg_mem(C.MOVZX_R16_RM8, R.CX, M(displ=base_addr+data_ext, displ_size=4)),
                I.create_reg_reg(C.TEST_RM8_R8, R.CL, R.CL),
                I.create_branch(C.JE_REL32_32, lbc.lb('byte_1')),
                #byte_2
                #I.create_reg_u32(C.SHL_RM16_IMM8, R.CX, 8),
                I.create_reg_u32(C.SHL_RM16_IMM8, R.AX, 8), #LE for unicode convert
                I.create_reg_reg(C.OR_R16_RM16, R.AX, R.CX),
                #convert gbk to unicode
                I.create_branch(C.CALL_REL32_32, code_ext + funcs[0]),
                I.create_mem_reg(C.MOV_RM16_R16, M(R.ESP, displ=0x8, displ_size=1), R.AX),
                I.create_mem_u32(C.MOV_RM8_IMM8, M(displ=base_addr+data_ext+2, displ_size=4), 2),
                I.create_branch(C.JMP_REL32_32, lbc.lb('ret')),
                #byte_1
                lbc.add('byte_1',
                    I.create_reg_u32(C.CMP_RM8_IMM8, R.AL, 0x80),
                ),
                I.create_branch(C.JB_REL32_32, lbc.lb('ret')),
                #log and bypass
                I.create_mem_u32(C.MOV_RM8_IMM8, M(displ=base_addr+data_ext+2, displ_size=4), 1),
                I.create_mem_reg(C.MOV_RM8_R8, M(displ=base_addr+data_ext, displ_size=4), R.AL),
                I.create_reg_reg(C.XOR_R32_RM32, R.EAX, R.EAX),
                I.create_reg(C.POP_R32, R.ECX),
                I.create_u32(C.RETND_IMM16, 0x4),
                #ret
                lbc.add('ret',
                    I.create_mem_u32(C.MOV_RM8_IMM8, M(displ=base_addr+data_ext, displ_size=4), 0),
                ),
                I.create_reg_mem(C.MOV_EAX_MOFFS32, R.EAX, M(displ=0x1004af4c, displ_size=4)),
                I.create_reg(C.POP_R32, R.ECX),
                I.create_branch(C.JMP_REL32_32, 0xf1c5),
            ])),
            # hooks for GetCharABCWidths
            (code_ext + hooks[1], with_label_ctx(lambda lbc: [
                I.create_mem_u32(C.AND_RM32_IMM32, M(R.ESP, displ=0x4, displ_size=1), 0xffff),
                I.create_mem_u32(C.MOV_RM8_IMM8, M(displ=base_addr+data_ext+3, displ_size=4), 0),
                I.create_reg(C.PUSH_R32, R.ECX),
                I.create_reg_mem(C.MOV_R32_RM32, R.EAX, M(R.ESP, displ=0x8, displ_size=1)),
                I.create_reg_u32(C.CMP_RM16_IMM16, R.AX, 0x100),
                I.create_branch(C.JB_REL32_32, lbc.lb('handle')),
                I.create_reg_u32(C.CMP_RM16_IMM16, R.AX, 0xff00),
                I.create_branch(C.JB_REL32_32, lbc.lb('ret')),
                I.create_reg_reg(C.MOVZX_R16_RM8, R.AX, R.AL),
                #handle
                lbc.add('handle',
                    I.create_reg_u32(C.CMP_RM8_IMM8, R.AL, 0x40),
                ),
                I.create_branch(C.JB_REL32_32, lbc.lb('ret')),
                #read log
                I.create_reg_mem(C.MOVZX_R16_RM8, R.CX, M(displ=base_addr+data_ext+1, displ_size=4)),
                I.create_reg_reg(C.TEST_RM8_R8, R.CL, R.CL),
                I.create_branch(C.JE_REL32_32, lbc.lb('byte_1')),
                #byte_2
                #I.create_reg_u32(C.SHL_RM16_IMM8, R.CX, 8),
                I.create_reg_u32(C.SHL_RM16_IMM8, R.AX, 8), #LE for unicode convert
                I.create_reg_reg(C.OR_R16_RM16, R.AX, R.CX),
                #convert gbk to unicode
                I.create_branch(C.CALL_REL32_32, code_ext + funcs[0]),
                I.create_mem_reg(C.MOV_RM16_R16, M(R.ESP, displ=0x8, displ_size=1), R.AX),
                I.create_mem_u32(C.MOV_RM8_IMM8, M(displ=base_addr+data_ext+3, displ_size=4), 2),
                I.create_branch(C.JMP_REL32_32, lbc.lb('ret')),
                #byte_1
                lbc.add('byte_1',
                    I.create_reg_u32(C.CMP_RM8_IMM8, R.AL, 0x80),
                ),
                I.create_branch(C.JB_REL32_32, lbc.lb('ret')),
                #log and bypass
                I.create_mem_u32(C.MOV_RM8_IMM8, M(displ=base_addr+data_ext+3, displ_size=4), 1),
                I.create_mem_reg(C.MOV_RM8_R8, M(displ=base_addr+data_ext+1, displ_size=4), R.AL),
                I.create_reg(C.POP_R32, R.ECX),
                I.create_reg_mem(C.MOV_R32_RM32, R.EAX, M(R.ESP, displ=0x8, displ_size=1)),
                I.create_mem_u32(C.MOV_RM32_IMM32, M(R.EAX), 0),
                I.create_reg_mem(C.MOV_R32_RM32, R.EAX, M(R.ESP, displ=0xc, displ_size=1)),
                I.create_mem_u32(C.MOV_RM32_IMM32, M(R.EAX), 0),
                I.create_reg_mem(C.MOV_R32_RM32, R.EAX, M(R.ESP, displ=0x10, displ_size=1)),
                I.create_mem_u32(C.MOV_RM32_IMM32, M(R.EAX), 0),
                I.create_u32(C.RETND_IMM16, 0x10),
                #ret
                lbc.add('ret',
                    I.create_mem_u32(C.MOV_RM8_IMM8, M(displ=base_addr+data_ext+1, displ_size=4), 0),
                ),
                I.create_reg(C.POP_R32, R.ECX),
                I.create_reg_mem(C.MOV_R32_RM32, R.EAX, M(R.ESP, displ=0x4, displ_size=1)),
                I.create_reg_u32(C.SUB_RM32_IMM8, R.ESP, 0xc),
                I.create_branch(C.JMP_REL32_32, 0x16387),
            ])),
            # hooks for CFontAmalgam::GetFontForChar, un-negtive src char
            (code_ext + hooks[2], with_label_ctx(lambda lbc: [
                I.create_reg_mem(C.MOV_R32_RM32, R.EAX, M(R.ESP, displ=0x4, displ_size=1)),
                I.create_reg_u32(C.AND_EAX_IMM32, R.EAX, 0xff00),
                I.create_reg_u32(C.CMP_EAX_IMM32, R.EAX, 0xff00),
                I.create_branch(C.JNE_REL32_32, lbc.lb('keep2')),
                #keep1
                I.create_mem_u32(C.AND_RM32_IMM32, M(R.ESP, displ=0x4, displ_size=1), 0xff),
                I.create_branch(C.JMP_REL32_32, lbc.lb('ret')),
                #keep2
                lbc.add('keep2',
                    I.create_mem_u32(C.AND_RM32_IMM32, M(R.ESP, displ=0x4, displ_size=1), 0xffff),
                ),
                #ret
                lbc.add('ret',
                    I.create_reg(C.PUSH_R32, R.ESI),
                ),
                I.create_reg_mem(C.MOV_R32_RM32, R.ESI, M(R.ECX, displ=0xc, displ_size=1)),
                I.create_reg_reg(C.XOR_R32_RM32, R.EDX, R.EDX),
                I.create_branch(C.JMP_REL32_32, 0x15dc6),
            ])),
            # hooks for get_char_info_ctype <- iswcntrl/iswspace/...
            (code_ext + hooks[3], with_label_ctx(lambda lbc: [
                I.create_mem_u32(C.CMP_RM16_IMM16, M(R.ESP, displ=0x4, displ_size=1), 0xff00),
                I.create_branch(C.JAE_REL32_32, lbc.lb('ret_bypass')),
                #ret
                I.create_reg(C.PUSH_R32, R.EBP),
                I.create_reg_reg(C.MOV_R32_RM32, R.EBP, R.ESP),
                I.create_reg(C.PUSH_R32, R.ECX),
                I.create_mem_u32(C.CMP_RM16_IMM16, M(R.EBP, displ=0x8, displ_size=1), 0xffff),
                I.create_branch(C.JMP_REL32_32, 0x2bda6),
                #bypass
                lbc.add('ret_bypass',
                    I.create_reg_mem(C.MOV_R32_RM32, R.EAX, M(R.ESP, displ=0x8, displ_size=1)),
                ),
                # I don't know what ctype is 0x300, maybe standard uchar?
                # but it's work to let flags 0x157 be true and flags 0x8 be false.
                I.create_reg_u32(C.AND_EAX_IMM32, R.EAX, 0x300),
                I.create(C.RETND), #cdecl
            ])),
            # hooks for DrawUnicodeChar width calc
##            (code_ext + hooks[k], [
##                I.create_reg_mem(C.MOV_R32_RM32, R.ECX, M(R.ESP, displ=0x30, displ_size=1)),
##                I.create_reg_mem(C.ADD_R32_RM32, R.ECX, M(R.ESP, displ=0x40, displ_size=1)),
##                I.create_mem_reg(C.MOV_RM32_R32, M(R.ESP, displ=0x30, displ_size=1), R.ECX),
##                I.create_reg_mem(C.MOV_R32_RM32, R.EDI, M(R.ESP, displ=0x10, displ_size=1)),
##                I.create_reg_mem(C.MOV_R32_RM32, R.ECX, M(R.ESP, displ=0x2c, displ_size=1)),
##                I.create_branch(C.JMP_REL32_32, 0xf2ab),
##            ]),
            # func convert ansi to unicode
            (code_ext + funcs[0], with_label_ctx(lambda lbc: [
                I.create_reg_u32(C.SUB_RM32_IMM8, R.ESP, 0x4),
                I.create_reg(C.PUSH_R32, R.EAX),
                I.create_reg(C.PUSH_R32, R.ECX),
                I.create_reg(C.PUSH_R32, R.EDX),
                # get g_pVGuiLocalize
                I.create_branch(C.CALL_REL32_32, 0x19e00),
                I.create_reg_mem(C.MOV_R32_RM32, R.EDX, M(R.EAX)),
                I.create_u32(C.PUSHD_IMM32, 0x2),
                I.create_reg_mem(C.LEA_R32_M, R.EAX, M(R.ESP, displ=0x10, displ_size=1)),
                I.create_reg(C.PUSH_R32, R.EAX),
                I.create_reg_mem(C.LEA_R32_M, R.EAX, M(R.ESP, displ=0x10, displ_size=1)),
                I.create_reg(C.PUSH_R32, R.EAX),
                # g_pVGuiLocalize->ConvertANSIToUnicode(src, dst, 2)
                I.create_mem(C.CALL_RM32, M(R.EDX, displ=0x1c, displ_size=1)),
                I.create_reg(C.POP_R32, R.EDX),
                I.create_reg(C.POP_R32, R.ECX),
                I.create_reg(C.POP_R32, R.EAX),
                # ret unicode char
                I.create_reg_mem(C.MOV_R16_RM16, R.AX, M(R.ESP)),
                I.create_reg_u32(C.ADD_RM32_IMM8, R.ESP, 0x4),
                I.create(C.RETND),
            ])),
        ])(0x10000000, 0x35000, 0x4e000, [0, 0x100, 0x200, 0x300], [0x800]),
    },
    'vstdlib': {
        'path': 'Bin',
        'file': 'vstdlib.dll',
        'md5':  '82791036bdadc8e08cfd5ee46823944a',
        'patch': [
            # Q_isprint
##            (0x40D4, [
##                I.create(C.RETND),
##            ]),
            (0x40db, [
                I.create_reg_u32(C.CMP_EAX_IMM32, R.EAX, 0x80),
            ]),
        ],
    },
##    'vgui2': {
##        'path': 'Bin',
##        'file': 'vgui2.dll',
##        'md5':  '21347f4265fa01173f09e31dc57ddbce',
##        'patch': [
##            # CLocalizedStringTable::ConvertANSIToUnicode CP_ACP -> CP_OEMCP (GBK)
##            (0x9373, [
##                I.create_u32(C.PUSHD_IMM8, 1),
##            ]),
##        ],
##    },
    'client': {
        'path': 'Unofficial_Patch\cl_dlls',
        'file': 'client.dll',
        'md5':  '1c80bb0ae0486c9dfb6ecc35c604b050',
        'patch': (lambda base_addr, code_ext, data_ext, hooks, funcs:[
            #(code_ext - 1, b'\xcc\xcc'), # force extend code sect
            # a func which split text to multi lines, here find breakable position
            (0x55075, [
                I.create_branch(C.JMP_REL32_32, code_ext + hooks[0]),
            ]),
            # mabe a bug, that make the 1st line shorter than others.
            (0x550e3, [
                I.create_reg_mem(C.LEA_R32_M, R.EBP, M(R.EDX, displ=-0x1, displ_size=1))
            ]),
            # subtitle linebreak modify
            (0xf223b, with_label_ctx(lambda lbc: [
                # mod width_limit_len if the last char is not space
                I.create_reg(C.PUSH_R32, R.EAX),
                I.create_reg_mem(C.MOV_R32_RM32, R.EAX, M(R.EBP, displ=-0x10, displ_size=1)),
                I.create_reg_mem(C.ADD_R32_RM32, R.EAX, M(R.ESP)),
                I.create_reg_mem(C.MOV_R8_RM8, R.AL, M(R.EAX, displ=0x1, displ_size=1)),
                I.create_reg(C.DEC_RM8, R.AL),
                I.create_reg_u32(C.CMP_RM8_IMM8, R.AL, 0x20),
                I.create_reg(C.POP_R32, R.EAX),
                I.create_branch(C.JB_REL32_32, lbc.lb('check_width_limit_len')),
                I.create_reg(C.INC_R32, R.EAX),
                # check width_limit_len from orig code
                lbc.add('check_width_limit_len',
                    I.create_mem_reg(C.MOV_RM32_R32, M(R.EBP, displ=-0xc, displ_size=1), R.EAX),
                ),
                I.create_mem_u32(C.CMP_RM32_IMM8, M(R.EBP, displ=-0xc, displ_size=1), 0),
                I.create_branch(C.JLE_REL32_32, 0xf2358),
                I.create_reg_mem(C.MOV_R32_RM32, R.ECX, M(R.EBP, displ=-0xc, displ_size=1)),
                I.create_reg_mem(C.CMP_R32_RM32, R.ECX, M(R.EBP, displ=-0x14, displ_size=1)),
                I.create_branch(C.JGE_REL32_32, 0xf2358),
                # mod buff and break line
                I.create_reg(C.PUSH_R32, R.ESI),
                I.create_reg(C.PUSH_R32, R.EDI),
                I.create_reg_mem(C.MOV_R32_RM32, R.ESI, M(R.EBP, displ=-0x10, displ_size=1)),
                I.create_reg_mem(C.LEA_R32_M, R.EDI, M(R.EBP, displ=-0x4030, displ_size=4)),
                I.create_reg_mem(C.MOV_R32_RM32, R.ECX, M(R.EBP, displ=-0xc, displ_size=1)),
                I.create_mem_reg(C.MOV_RM32_R32, M(R.EBP, displ=-0x202c, displ_size=4), R.ECX),
                I.create_reg_reg(C.XOR_R32_RM32, R.EDX, R.EDX),
                # loop
                lbc.add('loop',
                    I.create_reg_mem(C.MOV_R8_RM8, R.AL, M(R.ESI, index=R.EDX)),
                ),
                I.create_reg_reg(C.CMP_R32_RM32, R.ECX, R.EDX),
                I.create_branch(C.JNE_REL32_32, lbc.lb('next')),
                I.create_mem_u32(C.MOV_RM8_IMM8, M(R.EDI), 0),
                I.create_reg_u32(C.CMP_AL_IMM8, R.AL, 0x20),
                I.create_branch(C.JBE_REL32_32, lbc.lb('next_nocopy')),
                I.create_reg(C.INC_R32, R.EDI),
                I.create_mem(C.INC_RM32, M(R.EBP, displ=-0x14, displ_size=1)),
                lbc.add('next',
                    I.create_mem_reg(C.MOV_RM8_R8, M(R.EDI), R.AL),
                ),
                lbc.add('next_nocopy',
                    I.create_reg(C.INC_R32, R.EDI),
                ),
                I.create_reg(C.INC_R32, R.EDX),
                I.create_reg_reg(C.TEST_RM8_R8, R.AL, R.AL),
                I.create_branch(C.JNE_REL32_32, lbc.lb('loop')),
                # end
                I.create_reg(C.POP_R32, R.EDI),
                I.create_reg(C.POP_R32, R.ESI),
                I.create_branch(C.JMP_REL32_32, 0xf22e2),
                #I.create(C.NOPD),
            ])),
            # make a line start position table in draw_text_info
            (0x1aea1d, [
                I.create_branch(C.JMP_REL32_32, code_ext + hooks[1]),
                I.create(C.NOPD),
            ]),
            # hooks find breakable char
            (code_ext + hooks[0], with_label_ctx(lambda lbc: [
                I.create_reg_reg(C.MOV_R32_RM32, R.EDX, R.EBP),
                I.create_reg_reg(C.XOR_R32_RM32, R.EAX, R.EAX),
                I.create_reg_reg(C.XOR_R32_RM32, R.ECX, R.ECX),
                I.create_reg_reg(C.XOR_R32_RM32, R.EBP, R.EBP),
                # search loop
                lbc.add('loop',
                    I.create_reg_reg(C.TEST_RM8_R8, R.AH, R.AH),
                ),
                I.create_branch(C.JE_REL32_32, lbc.lb('uchar')),
                # is byte-2
##                I.create_reg_mem(C.LEA_R32_M, R.EAX, M(R.ECX, displ=0x1, displ_size=1)),
##                I.create_reg_reg(C.CMP_R32_RM32, R.EAX, R.EDX),
##                I.create_reg_u32(C.MOV_R32_IMM32, R.EAX, 0x0), # clear AH, but do not set condi
##                I.create_branch(C.JAE_REL32_32, lbc.lb('log_b2')),
                I.create_reg_reg(C.XOR_R8_RM8, R.AH, R.AH),
                # check punctuation
                I.create_reg_mem(C.MOV_R8_RM8, R.AL, M(R.ESI, index=R.ECX, displ=0x1, displ_size=1)),
                I.create_reg_u32(C.CMP_RM8_IMM8, R.AL, 0xa1),
                I.create_branch(C.JB_REL32_32, lbc.lb('log_b2')),
                I.create_reg_u32(C.CMP_RM8_IMM8, R.AL, 0xa9),
                I.create_branch(C.JBE_REL32_32, lbc.lb('next')),
                lbc.add('log_b2',
                    I.create_reg_mem(C.LEA_R32_M, R.EBP, M(R.ECX, displ=0x1, displ_size=1)),
                ),
                I.create_branch(C.JMP_REL32_32, lbc.lb('next')),
                # not byte-2, is u-char
                lbc.add('uchar',
                    I.create_reg_mem(C.MOV_R8_RM8, R.AL, M(R.ESI, index=R.ECX)),
                ),
                I.create_reg_u32(C.CMP_AL_IMM8, R.AL, 0x80),
                I.create_branch(C.JB_REL32_32, lbc.lb('ascii')),
                # is byte-1
                I.create_reg_u32(C.MOV_R8_IMM8, R.AH, 1),
                I.create_branch(C.JMP_REL32_32, lbc.lb('next')),
                # is ascii
                lbc.add('ascii',
                    I.create_reg_u32(C.CMP_AL_IMM8, R.AL, 0x20),
                ),
                I.create_branch(C.JE_REL32_32, lbc.lb('found')),
                I.create_reg_u32(C.CMP_AL_IMM8, R.AL, 0x2d),
                I.create_branch(C.JNE_REL32_32, lbc.lb('next')),
                # log breakable
                lbc.add('found',
                    I.create_reg_reg(C.MOV_R32_RM32, R.EBP, R.ECX),
                ),
                I.create_reg_reg(C.XOR_RM8_R8, R.AH, R.AH),
                # next
                lbc.add('next',
                    I.create_reg(C.INC_R32, R.ECX),
                ),
                I.create_reg_reg(C.CMP_R32_RM32, R.ECX, R.EDX),
                # the last char may be not space, should not check the last char
                I.create_branch(C.JB_REL32_32, lbc.lb('loop')),
                # ret
                I.create_branch(C.JMP_REL32_32, 0x55083),
            ])),
            # hooks record line start position in draw_text_info
            (code_ext + hooks[1], with_label_ctx(lambda lbc: [
                I.create_mem_reg(C.MOV_RM32_R32, M(R.ECX, index=R.EAX, scale=4), R.EBX),
                I.create_reg(C.PUSH_R32, R.EAX),
                I.create_reg_mem(C.MOV_R8_RM8, R.AL, M(R.ESP, displ=0x1c, displ_size=1)),
                # 0xa0 can only make gb2312 working, not gbk ext
                # but 0x80 still can not make gbk ext working currectly
                # whatever, 0x80 is more flexible than 0xa0
                I.create_reg_u32(C.CMP_AL_IMM8, R.AL, 0x80),
                I.create_reg(C.POP_R32, R.EAX),
                I.create_branch(C.JB_REL32_32, lbc.lb('pass')),
                I.create_mem(C.DEC_RM32, M(R.ECX, index=R.EAX, scale=4)),
                lbc.add('pass',
                    I.create_reg_mem(C.MOV_R32_RM32, R.ECX, M(R.EBP)),
                ),
                I.create_branch(C.JMP_REL32_32, 0x1aea23),
            ])),
        ])(0x10000000, 0x1e3000, 0x683000, [-0x400, -0x300], []),
    },
}

def hash_md5(val):
    return _md5(val).hexdigest()

def report(*args):
    r = ' '.join(args)
    print(r)
    return r

alignup   = lambda v, a: ((v - 1) // a + 1) * a
aligndown = lambda v, a: (v // a) * a

def readval_le(raw, offset, size, signed):
    neg = False
    v = 0
    endpos = offset + size - 1
    for i in range(endpos, offset - 1, -1):
        b = raw[i]
        if signed and i == endpos and b > 0x7f:
            neg = True
            b &= 0x7f
        #else:
        #    b &= 0xff
        v <<= 8
        v += b
    return v - (1 << (size*8 - 1)) if neg else v

def writeval_le(val, dst, offset, size):
    if val < 0:
        val += (1 << (size*8))
    for i in range(offset, offset + size):
        dst[i] = (val & 0xff)
        val >>= 8

class c_mark:

    def __init__(self, raw, offset):
        self._raw = raw
        self._mod = None
        self.offset = offset
        self.parent = None
        self._par_offset = 0

    @property
    def raw(self):
        if self.parent:
            return self.parent.raw
        return self._mod if self._mod else self._raw

    @property
    def mod(self):
        if self.parent:
            return self.parent.mod
        if not self._mod:
            self._mod = bytearray(self._raw)
        return self._mod

    @property
    def par_offset(self):
        po = self._par_offset
        if self.parent:
            po += self.parent.par_offset
        return po

    def shift(self, offs):
        self._par_offset += offs

    def extendto(self, cnt):
        extlen = self.offset + cnt - len(self.raw)
        if extlen > 0:
            self.mod.extend(bytes(extlen))

    def readval(self, pos, cnt, signed):
        return readval_le(self.raw, self.offset + pos, cnt, signed)

    def writeval(self, val, pos, cnt):
        self.extendto(pos + cnt)
        writeval_le(val, self.mod, self.offset + pos, cnt)

    def fill(self, val, pos, cnt):
        for i in range(pos, pos + cnt):
            self.mod[i] = val

    I8  = lambda self, pos: self.readval(pos, 1, True)
    U8  = lambda self, pos: self.readval(pos, 1, False)
    I16 = lambda self, pos: self.readval(pos, 2, True)
    U16 = lambda self, pos: self.readval(pos, 2, False)
    I32 = lambda self, pos: self.readval(pos, 4, True)
    U32 = lambda self, pos: self.readval(pos, 4, False)
    I64 = lambda self, pos: self.readval(pos, 8, True)
    U64 = lambda self, pos: self.readval(pos, 8, False)

    W8  = lambda self, val, pos: self.writeval(val, pos, 1)
    W16 = lambda self, val, pos: self.writeval(val, pos, 2)
    W32 = lambda self, val, pos: self.writeval(val, pos, 4)
    W64 = lambda self, val, pos: self.writeval(val, pos, 8)

    def BYTES(self, pos, cnt):
        st = self.offset + pos
        if cnt is None:
            ed = None
        else:
            ed = st + cnt
            self.extendto(pos + cnt)
        return self.raw[st: ed]

    def STR(self, pos, cnt, codec = 'utf8'):
        return self.BYTES(pos, cnt).split(b'\0')[0].decode(codec)

    def BYTESN(self, pos):
        st = self.offset + pos
        rl = len(self.raw)
        ed = rl
        for i in range(st, rl):
            if self.raw[i] == 0:
                ed = i
                break
        return self.raw[st:ed], ed - st

    def STRN(self, pos, codec = 'utf8'):
        b, n = self.BYTESN(pos)
        return b.decode(codec), n

    def sub(self, pos, length = 0):
        if length > 0:
            s = c_mark(None, 0)
            s._mod = bytearray(self.BYTES(pos, length))
            s._par_offset = self.par_offset + pos
        else:
            s = c_mark(None, self.offset + pos)
            s.parent = self
        return s

class c_pe_file(c_mark):

    def __init__(self, raw):
        super().__init__(raw, 0)
        self.parse_head()

    def parse_head(self):
        if self.U16(0) != 0x5a4d:
            raise ValueError(report('invalid PE header'))
        self.parse_coff(self.sub(self.U32(0x3c)))

    def parse_coff(self, mark):
        self.mark_coff = mark
        if mark.U32(0) != 0x4550:
            raise ValueError(report('invalid COFF header'))
        self.num_sect = mark.U16(0x6)
        self.parse_opt_coff(mark.sub(0x18), mark.U16(0x14))

    def parse_opt_coff(self, mark, size):
        if size < 0x1c:
            self.parse_opt_win(mark.sub(size) if size > 0 else mark, 0)
            return
        self.mark_opt_coff = mark
        magic = mark.U16(0)
        if magic == 0x10b:
            self.flag_32plus = False
        elif magic == 0x20b:
            self.flag_32plus = True
        else:
            raise ValueError(report('invalid magic'))
        self.size_code = mark.U32(0x4)
        self.size_idat = mark.U32(0x8)
        self.size_udat = mark.U32(0xc)
        self.addr_entry = mark.U32(0x10)
        self.addr_code = mark.U32(0x14)
        self.addr_data = mark.U32(0x18)
        self.parse_opt_win(mark.sub(0x1c), size - 0x1c)

    def parse_opt_win(self, mark, size):
        if size < 0x44:
            self.parse_opt_datdir(mark.sub(size) if size > 0 else mark, 0, 0)
            return
        self.mark_opt_win = mark
        self.addr_base = mark.U32(0)
        self.align_addr = mark.U32(0x4)
        self.align_offs = mark.U32(0x8)
        self.size_img = mark.U32(0x1c)
        self.size_hdr = mark.U32(0x20)
        self.parse_opt_datdir(mark.sub(0x44), size - 0x44, mark.U32(0x40))

    def parse_opt_datdir(self, mark, size, num):
        dsize = num * 0x8
        if size < dsize:
            self.parse_sect(mark.sub(size) if size > 0 else mark, 0)
            return
        assert size == dsize
        self.mark_opt_datdir = mark
        datdir = []
        for i in range(num):
            p = i * 0x8
            mark_dd = mark.sub(i * 0x8)
            datdir_info = {
                'mark_h': mark_dd,
                'addr': mark_dd.U32(0),
                'size_v': mark_dd.U32(0x4),
                'mark': None,
            }
            datdir.append(datdir_info)
        self.tab_datdir = datdir
        self.parse_sect(mark.sub(size), 0)

    def _upd_opt_datdir(self, sect_info):
        s_mark = sect_info['mark']
        s_szva = self.aligned_address(sect_info['size_v'])
        s_addr = sect_info['addr']
        s_last = s_addr + s_szva
        for i, datdir_info in enumerate(self.tab_datdir):
            if datdir_info['mark']:
                continue
            d_addr = datdir_info['addr']
            d_szv = datdir_info['size_v']
            if not s_addr <= d_addr < s_last:
                continue
            if not d_addr + d_szv < s_last:
                raise ValueError(report(
                    f'data dir {i} cross section {sect_info["name"]}'))
            datdir_info['mark'] = s_mark.sub(d_addr - s_addr)

    def parse_sect(self, mark, idx):
        if idx >= self.num_sect:
            self.parse_tail(self.sub(self.offs_sect_nxt))
            return
        sect_info = {
            'mark_h': mark,
            'idx': idx,
            'name': mark.STR(0, 0x8),
            'size_v': mark.U32(0x8),
            'addr': mark.U32(0xc),
            'size': mark.U32(0x10),
            'offs': mark.U32(0x14),
        }
        ch = mark.U32(0x24)
        sect_info['char'] = {
            'code': ch & 0x20,
            'idat': ch & 0x40,
            'udat': ch & 0x80,
            'ncch': ch & 0x4000000,
            'npag': ch & 0x8000000,
            'shar': ch & 0x10000000,
            'exec': ch & 0x20000000,
            'read': ch & 0x40000000,
            'writ': ch & 0x80000000,
        }
        sect_info['mark'] = self.sub(sect_info['offs'], sect_info['size'])
        if idx == 0:
            self.tab_sect = []
        elif self.offs_sect_nxt != sect_info['offs']:
            raise ValueError(report(
                f'invalid offset of sect {sect_info["name"]}'))
        self.offs_sect_nxt = sect_info['offs'] + sect_info['size']
        self.tab_sect.append(sect_info)
        self._upd_opt_datdir(sect_info)
        self.parse_sect(mark.sub(0x28), idx+1)

    def parse_tail(self, mark):
        self.mark_tail = mark
        self.offs_tail = mark.offset

    def aligned_offset(self, offs):
        return alignup(offs, self.align_offs)

    def aligned_address(self, addr):
        return alignup(addr, self.align_addr)

    def _shift_sect(self, idx, elen, elen_v):
        if idx >= len(self.tab_sect):
            return
        sect_info = self.tab_sect[idx]
        mkh = sect_info['mark_h']
        if elen > 0:
            sect_info['offs'] += elen
            mkh.W32(sect_info['offs'], 0x14)
            sect_info['mark'].shift(elen)
        if elen_v > 0:
            sect_info['addr'] += elen_v
            mkh.W32(sect_info['addr'], 0xc)
        self._shift_sect(idx + 1, elen, elen_v)

    def _get_sect_by_addr(self, addr, cache = None, nearest = False):
        if cache:
            st = cache['st']
            ed = cache['ed']
            if st <= addr < ed:
                return cache['si'], addr - st
        if nearest:
            lst_offs = float('inf')
            lst_si = None
        for sect_info in self.tab_sect:
            s_szva = self.aligned_address(sect_info['size_v'])
            s_addr = sect_info['addr']
            s_last = s_addr + s_szva
            if s_addr <= addr < s_last:
                if not cache is None:
                    cache['st'] = s_addr
                    cache['ed'] = s_last
                    cache['si'] = sect_info
                return sect_info, addr - s_addr
            elif nearest and s_addr <= addr:
                cur_offs = addr - s_addr
                if cur_offs < lst_offs:
                    lst_offs = cur_offs
                    lst_si = sect_info
                    if not cache is None:
                        cache['st'] = s_addr
                        cache['ed'] = s_last
                        cache['si'] = sect_info
        else:
            if nearest and lst_si:
                return lst_si, lst_offs
            else:
                raise ValueError(report(f'invalid address 0x{addr:x}'))

    def _shift_addr(self, mark, moffs, st_addr, ed_addr, elen_v):
        addr = mark.U32(moffs)
        if addr >= st_addr and (ed_addr is None or addr < ed_addr):
            addr += elen_v
            mark.W32(addr, moffs)
        return addr

    def _shift_datdir_export(self, datdir_info, st_addr, ed_addr, elen_v):
        mk = datdir_info['mark']
        if mk.U32(0) != 0:
            raise ValueError(report(f'invalid export tab'))
        addr_name = self._shift_addr(mk, 0xc, st_addr, ed_addr, elen_v)
        num_func = mk.U32(0x14)
        num_fname = mk.U32(0x18)
        addr_func_arr = self._shift_addr(mk, 0x1c, st_addr, ed_addr, elen_v)
        addr_fname_arr = self._shift_addr(mk, 0x20, st_addr, ed_addr, elen_v)
        addr_fnord_arr = self._shift_addr(mk, 0x24, st_addr, ed_addr, elen_v)
        sect_cache = {}
        sect_info, offs_sect = self._get_sect_by_addr(addr_func_arr, sect_cache)
        mk_s = sect_info['mark']
        for i in range(offs_sect, offs_sect + num_func * 0x4, 0x4):
            self._shift_addr(mk_s, i, st_addr, ed_addr, elen_v)
        sect_info, offs_sect = self._get_sect_by_addr(addr_fname_arr, sect_cache)
        mk_s = sect_info['mark']
        for i in range(offs_sect, offs_sect + num_fname * 0x4, 0x4):
            self._shift_addr(mk_s, i, st_addr, ed_addr, elen_v)

    def _shift_datdir_import(self, datdir_info, st_addr, ed_addr, elen_v):
        mk = datdir_info['mark']
        szv = datdir_info['size_v']
        if szv % 0x14:
            raise ValueError(report('invalid import table size 0x{szv}'))
        sect_cache = {}
        flag_32plus = self.flag_32plus
        for i in range(0, szv - 0x14, 0x14): # last is empty
            addr_ilt = self._shift_addr(mk, i, st_addr, ed_addr, elen_v)
            addr_name = self._shift_addr(mk, i + 0xc, st_addr, ed_addr, elen_v)
            addr_iat = self._shift_addr(mk, i + 0x10, st_addr, ed_addr, elen_v)
            for addr_tab in (addr_ilt, addr_iat):
                sect_info, offs_sect = self._get_sect_by_addr(addr_tab, sect_cache)
                mk_s = sect_info['mark']
                offs_idx = offs_sect
                while True:
                    ti_v = mk_s.U32(offs_idx)
                    if flag_32plus:
                        ti_v2 = mk_s.U32(offs_idx + 0x4)
                        if ti_v == 0 and ti_v2 == 0:
                            break
                        ti_addr = ti_v
                        ti_flg = ti_v2
                    else:
                        if ti_v == 0:
                            break
                        ti_addr = (ti_v & 0x7fffffff)
                        ti_flg = (ti_v & 0x80000000)
                    if ti_flg:
                        report(f'warning: import tab by ord 0x{ti_addr:x}')
                        continue
                    if ti_addr >= st_addr and (ed_addr is None or ti_addr < ed_addr):
                        ti_addr += elen_v
                    if flag_32plus:
                        mk_s.W32(ti_addr, offs_idx)
                        offs_idx += 0x8
                    else:
                        mk_s.W32(ti_addr | ti_flg, offs_idx)
                        offs_idx += 0x4

    def _shift_datdir_reloc(self, datdir_info, st_addr, ed_addr, elen_v):
        mk = datdir_info['mark']
        szv = datdir_info['size_v']
        idx = 0
        sect_cache = {}
        while idx < szv:
            tbase = mk.U32(idx)
            if tbase >= st_addr and (ed_addr is None or tbase < ed_addr):
                tbase += elen_v
                mk.W32(tbase, idx)
                tb_shift = True
            else:
                tb_shift = False
            idx += 0x4
            tsize = mk.U32(idx) - 0x8
            idx += 0x4
            for i in range(idx, idx + tsize, 2):
                rel_v = mk.U16(i)
                rel_addr = (rel_v & 0xfff) + tbase
                rel_flg = rel_v >> 12
                if not tb_shift and rel_addr >= st_addr and (ed_addr is None or rel_addr < ed_addr):
                    raise ValueError(report(
                        f'reloc item 0x{rel_addr:x} shift cross block 0x{tbase:x}'))
                if rel_flg == 0:
                    pass
                elif rel_flg == 3:
                    sect_info, offs_sect = self._get_sect_by_addr(rel_addr, sect_cache)
                    mk_s = sect_info['mark']
                    s_addr = mk_s.U32(offs_sect)
                    s_addr_based = s_addr - self.addr_base
                    if s_addr_based >= st_addr and (ed_addr is None or s_addr_based < ed_addr):
                        d_addr = s_addr + elen_v
                        mk_s.W32(d_addr, offs_sect)
                    #else:
                        #report(f'warning: ref 0x{s_addr:x} < 0x{st_addr + self.addr_base:x} at 0x{rel_addr + self.addr_base:x} not changed')
                else:
                    report(f'warning: not implemented reloc type 0x{rel_flg:x}')
            idx += tsize
            if idx > szv:
                raise ValueError(report('invalid .reloc size'))

    def _shift_datdir(self, idx, st_addr, ed_addr, elen_v):
        datdir_info = self.tab_datdir[idx]
        if idx == 0:
            self._shift_datdir_export(datdir_info, st_addr, ed_addr, elen_v)
        elif idx == 0x1:
            self._shift_datdir_import(datdir_info, st_addr, ed_addr, elen_v)
        elif idx == 0x5:
            self._shift_datdir_reloc(datdir_info, st_addr, ed_addr, elen_v)
        elif idx == 0xc:
            # IAT handled by import tab
            pass
        else:
            report(f'warning: not implemented datdir({idx}) shift')
            return NotImplemented

    def _shift_datdir_tab(self, st_addr, ed_addr, elen_v):
        mk = self.mark_opt_datdir
        for i, datdir_info in enumerate(self.tab_datdir):
            if datdir_info['addr'] >= st_addr and (ed_addr is None or datdir_info['addr'] < ed_addr):
                datdir_info['addr'] += elen_v
                datdir_info['mark_h'].W32(datdir_info['addr'], 0)
                self._shift_datdir(i, st_addr, ed_addr, elen_v)

    def ext_sect(self, idx, dlen):
        if idx >= len(self.tab_sect):
            return
        sect_info = self.tab_sect[idx]
        mks = sect_info['mark']
        mkh = sect_info['mark_h']
        sz = sect_info['size']
        szv = sect_info['size_v']
        szva = self.aligned_address(szv)
        if dlen <= sz:
            if dlen > szv:
                if sect_info['char']['code']:
                    mks.fill(0xcc, szv, dlen - szv)
                sect_info['size_v'] = dlen
                mkh.W32(sect_info['size_v'], 0x8)
            return
        dlen_f = self.aligned_offset(dlen)
        elen = dlen_f - sz
        sect_info['size'] = dlen_f
        mkh.W32(sect_info['size'], 0x10)
        mks.extendto(dlen_f)
        elen_v = 0
        if dlen > szv:
            if sect_info['char']['code']:
                mks.fill(0xcc, szv, dlen - szv)
            elen_v = (self.aligned_address(dlen) - szva)
            sect_info['size_v'] = dlen
            mkh.W32(sect_info['size_v'], 0x8)
        self._shift_sect(idx + 1, elen, elen_v)
        shift_st_addr = sect_info['addr'] + szva
        self._shift_datdir_tab(shift_st_addr, None, elen_v)
        mkc = self.mark_opt_coff
        self.addr_entry = self._shift_addr(mkc, 0x10, shift_st_addr, None, elen_v)
        self.addr_code = self._shift_addr(mkc, 0x14, shift_st_addr, None, elen_v)
        self.addr_data = self._shift_addr(mkc, 0x18, shift_st_addr, None, elen_v)
        if sect_info['char']['code']:
            self.size_code += elen_v
            mkc.W32(self.size_code, 0x4)
        if sect_info['char']['idat']:
            self.size_idat += elen_v
            mkc.W32(self.size_idat, 0x8)
        if sect_info['char']['udat']:
            self.size_udat += elen_v
            mkc.W32(self.size_udat, 0xc)
        self.size_img += elen_v
        self.mark_opt_win.W32(self.size_img, 0x1c)
        self.offs_tail += elen

    def _access(self, a_st, a_ed):
        sect_info, offs_sect = self._get_sect_by_addr(a_st, None, True)
        s_st = sect_info['addr']
        s_ed = s_st + sect_info['size']
        s_ed_v = s_st + sect_info['size_v']
        if a_ed > s_ed or a_ed > s_ed_v:
            self.ext_sect(sect_info['idx'], a_ed - s_st)
        return sect_info, offs_sect

    def replace(self, r_addr, dst):
        rlen = len(dst)
        sect_info, offs_sect = self._access(r_addr, r_addr + rlen)
        mk = sect_info['mark']
        for i, b in enumerate(dst):
            mk.W8(b, offs_sect + i)
        return offs_sect + sect_info['offs']

    def _shift(self, mk, offs_sect, s_len, shft_len):
        if shft_len < 0:
            s_offs = offs_sect - shft_len
            rng = range(s_offs, s_offs + s_len)
        else:
            s_offs = offs_sect
            rng = range(s_offs + s_len - 1, s_offs - 1, -1)
        for i in rng:
            mk.W8(mk.U8(i), i + shft_len)
        return s_offs, s_offs + shft_len

    def shift(self, s_st, s_len, shft_len):
        s_ed = s_st + s_len
        d_st = s_st + shft_len
        d_ed = s_ed + shft_len
        a_st = min(s_st, d_st)
        a_ed = max(s_ed, d_ed)
        sect_info, offs_sect = self._access(a_st, a_ed)
        mk = sect_info['mark']
        r_st, r_ed = self._shift(mk, offs_sect, s_len, shft_len)
        self._shift_datdir_tab(s_st, s_ed, shft_len)
        return r_st, r_ed

    def _page_aligned_base(self, addr):
        page_len = 0x1000
        return aligndown(addr, page_len)

    def _page_ed(self, st_addr):
        page_len = 0x1000
        assert not st_addr % page_len
        return st_addr + page_len

    def _find_reloc_block_remain(self, mk, blk_base, blk_offs, blk_size, rng_addr, is_first):
        lst_i = 0
        for i in range(0, blk_size, 2):
            rel_v = mk.U16(blk_offs + i)
            rel_addr = (rel_v & 0xfff) + blk_base
            rel_flg = rel_v >> 12
            if rel_flg == 0:
                pass
            elif rel_flg == 3:
                if rng_addr <= rel_addr:
                    break
                lst_i = i + 2
            else:
                report(f'warning: not implemented reloc type 0x{rel_flg:x} at 0x{blk_offs+i:x}')
        if is_first:
            return lst_i
        else:
            return blk_size - lst_i

    def _find_reloc(self, mk, szv, rng_st_addr, rng_len):
        rng_ed_addr = rng_st_addr + rng_len
        reloc_st_offs = 0
        reloc_ed_offs = None
        blk_fst_entry_offs = None
        blk_fst_page_addr = self._page_aligned_base(rng_st_addr)
        blk_fst_rm_size = None
        blk_lst_entry_offs = None
        blk_lst_page_addr = self._page_aligned_base(rng_ed_addr - 1)
        blk_lst_rm_size = None
        idx = 0
        while idx < szv:
            blk_enttry_offs = idx
            blk_page_st_addr = mk.U32(idx)
            blk_page_ed_addr = self._page_ed(blk_page_st_addr)
            idx += 0x4
            blk_size = mk.U32(idx) - 0x8
            idx += 0x4
            if blk_page_ed_addr <= rng_st_addr:
                reloc_st_offs = idx + blk_size
            elif rng_ed_addr <= blk_page_st_addr:
                break
            reloc_ed_offs = idx + blk_size
            if blk_page_st_addr <= rng_st_addr < blk_page_ed_addr:
                assert blk_fst_entry_offs is None
                blk_fst_entry_offs = blk_enttry_offs
                blk_fst_page_addr = blk_page_st_addr
                blk_fst_rm_size = self._find_reloc_block_remain(
                    mk, blk_page_st_addr, idx, blk_size, rng_st_addr, True)
                reloc_st_offs = idx + blk_fst_rm_size
            if blk_page_st_addr <= rng_ed_addr <= blk_page_ed_addr:
                assert blk_lst_entry_offs is None
                blk_lst_entry_offs = blk_enttry_offs
                blk_lst_page_addr = blk_page_st_addr
                blk_lst_rm_size = self._find_reloc_block_remain(
                    mk, blk_page_st_addr, idx, blk_size, rng_ed_addr, False)
                reloc_ed_offs = idx + blk_size - blk_lst_rm_size
            idx += blk_size
        assert idx <= szv
        return (reloc_st_offs, reloc_ed_offs,
            blk_fst_entry_offs, blk_fst_page_addr, blk_fst_rm_size,
            blk_lst_entry_offs, blk_lst_page_addr, blk_lst_rm_size)

    def _pack_reloc(self, r_st, reloc_offs):
        reloc_pack = []
        blk = None
        blk_base = set()
        for offs in sorted(reloc_offs):
            addr = r_st + offs
            blk_addr = self._page_aligned_base(addr)
            offs_blk = r_st - blk_addr
            if not blk_addr in blk_base:
                blk = []
                reloc_pack.append((blk_addr, blk))
                blk_base.add(blk_addr)
            blk.append(offs + offs_blk)
        return reloc_pack

    def update_reloc(self, r_st, r_len, reloc_offs):
        blk_entry_len = 0x8
        reloc_entry_len = 0x2
        datdir_info = self.tab_datdir[0x5]
        mk = datdir_info['mark']
        szv = datdir_info['size_v']
        (cut_st_offs, cut_ed_offs,
            blk_fst_entry_offs, blk_fst_page_addr, blk_fst_rm_size,
            blk_lst_entry_offs, blk_lst_page_addr, blk_lst_rm_size,
        ) = self._find_reloc(mk, szv, r_st, r_len)
        cut_len = cut_ed_offs - cut_st_offs
        if not blk_lst_entry_offs is None and blk_fst_entry_offs != blk_lst_entry_offs:
            cut_len -= blk_entry_len
        tail_len = szv - cut_ed_offs
        new_reloc_len = 0
        reloc_pack = self._pack_reloc(r_st, reloc_offs)
        if reloc_pack:
            new_reloc_len = 0
            for blk_addr, blk in reloc_pack:
                new_reloc_len += blk_entry_len + len(blk) * reloc_entry_len
            rp_blk_fst_page_addr = reloc_pack[0][0]
            assert rp_blk_fst_page_addr >= blk_fst_page_addr
            rp_blk_lst_page_addr = reloc_pack[-1][0]
            assert rp_blk_lst_page_addr <= blk_lst_page_addr
            skip_fst = False
            skip_lst = False
            if (not blk_fst_entry_offs is None
                and rp_blk_fst_page_addr == blk_fst_page_addr):
                new_reloc_len -= blk_entry_len
                skip_fst = True
            if (not blk_lst_entry_offs is None
                and rp_blk_lst_page_addr == blk_lst_page_addr):
                if not skip_fst:
                    new_reloc_len -= blk_entry_len
                skip_lst = True
        shift_len = new_reloc_len - cut_len
        self.shift(datdir_info['addr'] + cut_ed_offs, tail_len, shift_len)
        datdir_info['size_v'] += shift_len
        datdir_info['mark_h'].W32(datdir_info['size_v'], 0x4)
        rp_blk_num = len(reloc_pack)
        idx = cut_st_offs
        for i, (blk_addr, blk) in enumerate(reloc_pack):
            blk_entry_idx = idx
            idx += blk_entry_len
            blk_sz = len(blk) * reloc_entry_len + blk_entry_len
            if i == 0 and skip_fst:
                blk_entry_idx = blk_fst_entry_offs
                blk_sz += blk_fst_rm_size
                idx -= blk_entry_len
            else:
                mk.W32(blk_addr, blk_entry_idx)
            if i == rp_blk_num - 1 and skip_lst:
                blk_sz += blk_lst_rm_size
            mk.W32(blk_sz, blk_entry_idx + 0x4)
            for r_offs in blk:
                mk.W16(0x3000 | r_offs, idx)
                idx += reloc_entry_len
        if not reloc_pack:
            if blk_fst_entry_offs == blk_lst_entry_offs != None:
                mk.W32(blk_fst_rm_size + blk_lst_rm_size + blk_entry_len,
                    blk_fst_entry_offs + 0x4)
            else:
                if not blk_fst_entry_offs is None:
                    mk.W32(blk_fst_rm_size + blk_entry_len, blk_fst_entry_offs + 0x4)
                if not blk_lst_entry_offs is None:
                    mk.W32(blk_lst_page_addr, idx)
                    mk.W32(blk_lst_rm_size + blk_entry_len, idx + 0x4)

    def repack(self):
        size_all = self.size_hdr
        size_code = 0
        size_idat = 0
        size_udat = 0
        yield self.BYTES(0, size_all)
        nxt_offs = size_all
        nxt_addr = size_all
        for sect_info in self.tab_sect:
            if sect_info['offs'] != nxt_offs:
                raise ValueError(report(
                    f'invalid offset of sect {sect_info["name"]}'))
            if sect_info['addr'] != nxt_addr:
                raise ValueError(report(
                    f'invalid address of sect {sect_info["name"]}'))
            szv = self.aligned_address(sect_info['size_v'])
            sz = sect_info['size']
            mk = sect_info['mark']
            yield mk.BYTES(0, sz)
            nxt_offs = self.aligned_offset(nxt_offs + sz)
            nxt_addr += szv
            size_all += sz
            if sect_info['char']['code']:
                size_code += szv
            if sect_info['char']['idat']:
                size_idat += szv
            if sect_info['char']['udat']:
                size_udat += szv
        if (size_code != self.size_code
            or size_idat != self.size_idat
            or size_udat != self.size_udat
            or nxt_addr != self.size_img):
            raise ValueError(report(
                f'invalid size of sects'))
        tl = self.mark_tail
        if self.offs_tail != nxt_offs:
            raise ValueError(report('invalid offset of tail'))
        yield tl.BYTES(0, None)

class c_pe_patcher:

    def __init__(self, cfg, src_info):
        self.cfg = cfg
        self.src_info = src_info
        self.dst_info = {}
        self.load_all()

    def load_all(self):
        for name in self.src_info:
            if not self.load_src(name):
                report(f'warning: load {name} failed')

    def save_all(self, overwrite = False):
        for name in self.src_info:
            if not self.save_dst(name, overwrite):
                report(f'warning: save {name} failed')

    def patch_all(self):
        for name in self.src_info:
            if not self.patch(name):
                report(f'warning: patch {name} failed')

    def load_src(self, name):
        if not name in self.src_info:
            report(f'error: unknown src {name}')
            return False
        sinfo = self.src_info[name]
        dinfo = {}
        fpath, fname, dstmd5 = sinfo['path'], sinfo['file'], sinfo['md5']
        fn = os.path.join(self.cfg['root'], fpath, fname)
        if not os.path.exists(fn):
            report(f'error: {fn} not exist')
            return False
        fn_b, fn_e = os.path.splitext(fn)
        fn_src = fn_b + '_src' + fn_e
        fn_dst = fn_b + '_dst' + fn_e
        dinfo['ori_fn'] = fn
        dinfo['src_fn'] = fn_src
        dinfo['dst_fn'] = fn_dst
        dinfo['load_from'] = 'ori'
        with open(fn, 'rb') as fd:
            raw = fd.read()
        fmd5 = hash_md5(raw)
        if fmd5 != dstmd5:
            if os.path.exists(fn_src):
                with open(fn_src, 'rb') as fd:
                    raw = fd.read()
                fmd5 = hash_md5(raw)
            if not fmd5 == dstmd5:
                report(f'error: {name} md5 unmatch: cur:{fmd5} dst:{dstmd5}')
                return False
            dinfo['load_from'] = 'src'
        try:
            pe = c_pe_file(raw)
        except:
            return False
        dinfo['pe'] = pe
        if 'en' in sinfo and not sinfo['en']:
            #bypass
            dinfo['patch'] = []
        else:
            dinfo['patch'] = sinfo['patch']
        self.dst_info[name] = dinfo
        return True

    def save_dst(self, name, overwrite = False):
        if not name in self.dst_info:
            report(f'error: unknown dst {name}')
            return False
        assert name in self.src_info
        dinfo = self.dst_info[name]
        fn = dinfo['ori_fn']
        fn_src = dinfo['src_fn']
        fn_dst = dinfo['dst_fn']
        pe = dinfo['pe']
        if dinfo['load_from'] == 'ori' and not os.path.exists(fn_src):
            shutil.copy2(fn, fn_src)
        with open(fn_dst, 'wb') as fd:
            try:
                for d in pe.repack():
                    fd.write(d)
            except:
                report(f'error: {name} repack failed')
                return False
        if overwrite:
            shutil.copy2(fn_dst, fn)
        return True

    def _check_reloc(self, dec, ins):
        if not (ins.memory_displ_size
            and ins.memory_displacement
            and ins.memory_base == 0):
            return None
        offs_info = dec.get_constant_offsets(ins)
        assert (offs_info.has_displacement
                and offs_info.displacement_size >= 4
                and 0 < offs_info.displacement_offset < ins.len)
        return offs_info.displacement_offset

    def disasm(self, dbyt, ip, ret_ins = False):
        dec = X.Decoder(self.cfg['bitness'], dbyt, ip = ip)
        fmt = X.Formatter(X.FormatterSyntax.NASM)
        fmt.first_operand_char_index = 8
        asm_repr = []
        asm_reloc = []
        if ret_ins:
            rins = []
        for ins in dec:
            disasm = fmt.format(ins)
            b_st = ins.ip - ip
            raw = dbyt[b_st:b_st + ins.len].hex().upper()
            asm_repr.append(f"{ins.ip:08X} {raw:20} {disasm}")
            reloc = self._check_reloc(dec, ins)
            if not reloc is None:
                asm_reloc.append(b_st + reloc)
            if ret_ins:
                rins.append(ins)
        if ret_ins:
            return asm_repr, asm_reloc, rins
        else:
            return asm_repr, asm_reloc

    def asm(self, patch):
        bitness = self.cfg['bitness']
        asm_patch = []
        for ip, seg in patch:
            asm_info = {}
            asm_patch.append((ip, asm_info))
            if callable(seg):
                asm_info['type'] = 'func'
                asm_info['func'] = seg
                continue
            elif isinstance(seg, (bytes, bytearray)):
                asm_info['type'] = 'raw'
                asm_info['byte'] = seg
                continue
            asm_info['type'] = 'asm'
            enc = X.BlockEncoder(bitness)
            enc.add_many(seg)
            dbyt = enc.encode(ip)
            asm_info['byte'] = dbyt
            asm_info['repr'], asm_info['reloc'] = self.disasm(dbyt, ip)
        return asm_patch

    def patch(self, name):
        if not name in self.dst_info:
            report(f'error: unknown dst {name}')
            return False
        dinfo = self.dst_info[name]
        pe = dinfo['pe']
        report(f'patch {name}:')
        asm_patch = self.asm(dinfo['patch'])
        for addr, patch_info in asm_patch:
            ptyp = patch_info['type']
            report(f'addr:0x{addr:08X} ({ptyp}):')
            if ptyp == 'func':
                func = patch_info['func']
                assert callable(func)
                rstr = func(addr, pe)
                report(rstr)
            elif ptyp in ['asm', 'raw']:
                byt = patch_info['byte']
                offs = pe.replace(addr, byt)
                byt_len = len(byt)
                brf_len = 8
                brf_byt = [f'{b:02X}' for b in byt[:brf_len]]
                brf = ' '.join(brf_byt)
                if byt_len > brf_len:
                    brf += '...'
                report(f'offs:0x{offs:08X} write(n:0x{byt_len:04X}): {brf}')
                if ptyp == 'asm':
                    pe.update_reloc(addr, byt_len, patch_info['reloc'])
                    report('asm:')
                    for i in patch_info['repr']:
                        report(i)
            else:
                report(f'warning: unknown patch type {ptyp}')
        return True

if __name__ == '__main__':
    from pprint import pprint as ppr
    pt = c_pe_patcher(PP_CFG, MOD_DLLS)
    pt.patch_all()
    pt.save_all(True)
