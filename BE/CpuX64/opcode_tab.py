#!/usr/bin/python3

"""
X64 64bit assembler + disassembler + side-effects table

This depends on x86data.js from https://github.com/asmjit/asmdb

We intend to only support a small subset of the opcode space.
Enough for code generation.
"""
import collections
import dataclasses
import enum
import itertools
import json
import os
import re
import sys
from typing import List, Dict, Tuple, Optional

from Util import cgen

# https://stackoverflow.com/questions/14698350/x86-64-asm-maximum-bytes-for-an-instruction/18972014
MAX_INSTRUCTION_LENGTH = 11
MAX_INSTRUCTION_LENGTH_WITH_PREFIXES = 15
MAX_OPERAND_COUNT = 6
MAX_INSTRUCTION_NAME_LENGTH = 27
MAX_FINGERPRINT = 6000  # really (1 << 13)

# list of opcodes we expect to use during X64 code generation
# plus some extra ones.
# coverage is > 95% of all opcodes commonly found in x86-64 executable.
# Many others can likely be addded by just adding the name here without additional
# work.
SUPPORTED_OPCODES = {
    "cmpxchg",
    "lockcmpxchg", # fake: cmpxchg with lock prefix
    "add", "addss", "addsd",  #
    "sub", "subss", "subsd",  #

    "imul", "mulss", "mulsd",  #
    "div", "idiv", "divss", "divsd",  #
    "or", "and", "xor",  #
    "sar", "shr", "shl", "ror", "rol",  #
    #
    "mov",  # includes movabs
    "movsx",  # sign extension
    "movzx",  # zero extension
    "movq",
    "movsxd",  # sign extension
    "movaps", "movapd", "movdqa",  # algned packed
    "movups", "movupd", "movdqu",  # unaligned packed
    "movsd", "movss",
    #
    "minss", "minsd",
    "maxss", "maxsd",
    "sqrtss", "sqrtsd",
    ""
    "neg", "not", "inc", "neg",  #
    "pxor", "por", "pand",  #
    "cvtss2sd", "cvtss2si",  #
    "cvtsd2ss", "cvtsd2si",  #
    "cvtsi2ss", "cvtsi2sd",  #
    "cvttss2si", "cvttsd2si",
    #
    "test", "cmp",  #
    "ucomiss", "ucomisd", "comisd", "comiss",  # comapre scalar
    "lea",  #
    "xchg",
    "popcnt", "tzcnt", "lzcnt",  #
    "pop", "push",  #
    #
    "call", "ret", "syscall", "endbr64",
    "jmp",
    "js",
    "jns",
    "jle",  # "/jng",
    "jne",  # "/jnz",
    "jge",  # "/jnl",
    "jbe",  # "/jna",
    "jb",  # "/jnae/jc",
    "jae",  # "/jnb/jnc"
    "je",  # "/jz",
    "ja",  # "/jnbe",
    "jl",  # "/jnge",
    "jp",  # "/jpe",
    "jnp",  # "/jpo",
    "jge",  # "/jnl",
    "jg",  # "/jnle",
    #
    "cmovb",  # "/cmovnae/cmovc"
    "cmovae",  # /cmovnb/cmovnc"
    "cmove",  # "/cmovz"
    "cmovo",
    "cmovno",
    "cmovs",
    "cmovns",
    "cmovne",  # "/cmovnz"
    "cmovbe",  # "/cmovna"
    "cmova",  # "/cmovnbe"
    "cmovs",
    "cmovns",
    "cmovp",  # "/cmovpe"
    "cmovnp",  # "/cmovpo"
    "cmovl",  # "/cmovnge"
    "cmovge",  # "/cmovnl"
    "cmovle",  # "/cmovng"
    "cmovle",  # "/cmovng"
    "cmovg",  # "/cmovnle"
    "cmovge",  # "/cmovnl
    #
    "seto",
    "setno",
    "setb",  # "/setnae/setc",
    "setae",  # "/setnb/setnc",
    "sete",  # "/setz",
    "setne",  # "/setnz",
    "setbe",  # "/setna",
    "seta",  # "/setnbe",
    "sets",
    "setns",
    "setp",  # "/setpe",
    "setnp",  # "/setpo",
    "setl",  # "/setnge",
    "setge",  # "/setnl",
    "setle",  # "/setng",
    "setg",  # "/setnle",
    "int3",  # for breakpoints
    "cwd", "cdq", "cqo",
    "ldmxcsr", "stmxcsr",
    "movq", "movd",
    # Note: sfence is currently excluded because we skip all MMX instructions
    "mfence", "lfence",
    # may require additional work because the M format behaves slightly different
    # depending on whether the mem or reg variant is used.
    # "movhps",

}

# this information is not yet used
_OPCODES_WITH_MULTIPLE_REG_WRITE = {
    "div", "idiv", "imul", "mul", "mulx",
    "cmpxchg8b", "cmpxchg16b", "cmpxchg32b",
    "xadd", "xchg",
    "cpuid", "rdtsc", "rdtscp",
    "rdpkru", "rdpru", "rdpmc", "rdmsr",
    "xgetbv",
    "vgatherdpd", "vgatherdps", "vgatherqpd", "vgatherqps",
    "vpgatherdd", "vpgatherdq", "vpgatherqd", "vpgatherqq",
    "vp2intersectd", "vp2intersectq",
}

# opcode extension/flavors we do not support for now
_DISALLOWED_EXTENSIONS = {
    "Deprecated",
    "MMX",
    "MMX2",
    "X86",
    "_Rep",
}


def IsDisallowExtension(ext):
    for m in ext.split():
        if m in _DISALLOWED_EXTENSIONS:
            return True
    return False


_IMPLICIT_OPERANDS = {
    "al", "ax", "eax", "rax",
    "dx", "edx", "rdx",  #
    "cl",  #
    "1",  # for shifts
}

# not used yet
_M_BUT_NOT_MEM = {
    "r64", "xmm[63:0]",
}

# not used yet
_M_BUT_NOT_REG = {
    "m32", "m64",
}

_OP_MAP = {
    "I": {
        "ib/ub", "iw/uw", "id/ud", "iq/uq",  #
        "ib", "iw", "id", "uw", "ud",
    },
    "R": {
        "r8", "r16", "r32", "r64",
        "xmm[31:0]", "xmm[63:0]",
        "xmm",
    },
    "M": {
        "r8/m8", "r16/m16", "r32/m32", "r64/m64",
        "r32/m16", "r64/m16",
        "mem",  #
        "xmm[31:0]/m32", "xmm[63:0]/m64", "xmm/m128",
        "m32",
        # the stuff below has not been tested but may work
        # non address
        # "r64", "xmm[63:0]", "xmm[31:0]",
        # non register
        # "m64",

    },
    "D": {"rel8", "rel32"},  # displacement
    "O": {"r8", "r16", "r32", "r64"},  # byte_with_reg
    "x": _IMPLICIT_OPERANDS,
    # "r": {"r8", "r16", "r32", "r64"},
}

_SUPPORTED_OPERANDS = set.union(*[x for x in _OP_MAP.values()])

_UNSUPPORTED_OPERANDS = {
    "moff8", "moff16", "moff32", "moff64",  #
    "fs", "gs",
    "creg", "dreg",  # problems with M encoding of r64
    "sreg",
}

# if these instructions have an immediate of size X but the register size is Y,
# the immediate will be signed extended to size Y if  X < y.
_OPCODES_WITH_IMMEDIATE_SIGN_EXTENSION = {
    "and", "or", "sub", "cmp", "add", "xor", "imul", "mov", "test",
}


def ContainsUnsupportedOperands(ops):
    for o in ops:
        if o in _UNSUPPORTED_OPERANDS:
            return True
    return False


_OPERAND_MODIFIERS = {
    "x:",  # read/write
    "X:",  # read/write, zero extend
    "w:",  # write only
    "W:",  # write only, zero extend
    "R:",  # read only
}

_SUPPORTED_FORMATS = {
    "MI",
    "MR",
    "RM",
    "D",
    "M",
    "I",
    "O",
    "RMI",
    "",
    # custom formats:
    "OI",  # mov ['w:r8', 'ib/ub'] I ['B0+r', 'ib'] etc
    "xM",  # div ['ax', 'r8/m8'] xM ['F6', '/6']
    "xxM",  # div ['dx', 'ax', 'r16/m16'] xxM
    "Mx",  # sar ['r8/m8', 'cl'] Mx
    "xI",
    "Ox",  # xchg
    "xO",  # xchg
    "xx",  # cwd, cdq, cqo
    "MRx", # cmpxchg
}

# Note. we do not support "h" registers
_REG_NAMES = ["ax", "cx", "dx", "bx", "sp", "bp", "si", "di"]

REG_NAMES = {
    # this assumes we do not use "h" registers
    8: [r.replace("x", "") + "l" for r in _REG_NAMES] + [f"r{i}b" for i in range(8, 16)],
    16: [r for r in _REG_NAMES] + [f"r{i}w" for i in range(8, 16)],
    32: [f"e{r}" for r in _REG_NAMES] + [f"r{i}d" for i in range(8, 16)],
    64: [f"r{r}" for r in _REG_NAMES] + [f"r{i}" for i in range(8, 16)],
}

XREG_NAMES = [f"xmm{r}" for r in range(16)]


def Hexify(data) -> str:
    return " ".join(f"{b:02x}" for b in data)


def IsOpXmm(c: str, ops: List, format: str) -> bool:
    pos = format.find(c)
    assert pos >= 0
    return "xmm" in ops[pos]


def GetOpWidth(op):
    if op in {"al"}:
        return 8
    elif op in {"ax", "dx"}:
        return 16
    elif op in {"eax", "edx"}:
        return 32
    elif op in {"rax", "rdx"}:
        return 64
    elif op.endswith("128"):
        return 128
    elif op.endswith("8"):
        return 8
    elif op.endswith("16"):
        return 16
    elif op.endswith("32"):
        return 32
    elif op.endswith("64"):
        return 64
    elif op.endswith("xmm[31:0]"):
        return 32
    elif op.endswith("xmm[63:0]"):
        return 64
    elif op.endswith("xmm"):
        return 128
    else:
        assert False, f"{op}"


def FindSpecificOpWidth(c: str, ops: List, format: str) -> int:
    pos = format.find(c)
    assert pos >= 0
    return GetOpWidth(ops[pos])


@enum.unique
class OK(enum.Enum):
    """Operand Kind"""
    RIP_BASE = 1
    MODRM_RM_BASE = 2
    OFFABS8 = 3
    OFFABS32 = 4
    SIB_SCALE = 5
    SIB_INDEX = 6
    SIB_BASE = 7
    SIB_INDEX_AS_BASE = 8
    #
    IMM8 = 10
    IMM16 = 11
    IMM32 = 12
    OFFPCREL8 = 13
    OFFPCREL32 = 14
    IMM8_16 = 17
    IMM8_32 = 18
    IMM8_64 = 19
    IMM32_64 = 20
    IMM64 = 21
    #
    BYTE_WITH_REG8 = 24
    BYTE_WITH_REG16 = 25
    BYTE_WITH_REG32 = 26
    BYTE_WITH_REG64 = 27
    #
    MODRM_RM_REG8 = 28
    MODRM_RM_REG16 = 29
    MODRM_RM_REG32 = 30
    MODRM_RM_REG64 = 31
    #
    MODRM_RM_XREG32 = 32
    MODRM_RM_XREG64 = 33
    MODRM_RM_XREG128 = 34
    #
    MODRM_REG8 = 35
    MODRM_REG16 = 36
    MODRM_REG32 = 37
    MODRM_REG64 = 38
    #
    MODRM_XREG32 = 39
    MODRM_XREG64 = 40
    MODRM_XREG128 = 41

    IMPLICIT_AL = 50
    IMPLICIT_AX = 51
    IMPLICIT_EAX = 52
    IMPLICIT_RAX = 53
    IMPLICIT_DX = 54
    IMPLICIT_EDX = 55
    IMPLICIT_RDX = 56
    IMPLICIT_CL = 57
    IMPLICIT_1 = 68


# Maps IMM OK to (encoded-size, rendered-size)
OK_IMM_TO_SIZE: Dict[OK, Tuple[int, int]] = {
    OK.IMM8: (8, 8),
    OK.IMM16: (16, 16),
    OK.IMM32: (32, 32),

    OK.IMM8_16: (8, 16),
    OK.IMM8_32: (8, 32),
    OK.IMM8_64: (8, 64),
    OK.IMM32_64: (32, 64),
    OK.IMM64: (64, 64),
}

OK_OFF_TO_SIZE: Dict[OK, Tuple[int, Optional[int]]] = {
    OK.OFFPCREL8: (8, None),
    OK.OFFPCREL32: (32, None),
    OK.OFFABS8: (8, None),
    OK.OFFABS32: (32, None),
}

OK_REG_TO_INFO = {
    OK.MODRM_RM_XREG32: (32, "x"),
    OK.MODRM_RM_XREG64: (64, "x"),
    OK.MODRM_RM_XREG128: (128, "x"),
    #
    OK.MODRM_RM_REG8: (8, "r"),
    OK.MODRM_RM_REG16: (16, "r"),
    OK.MODRM_RM_REG32: (32, "r"),
    OK.MODRM_RM_REG64: (64, "r"),
    #
    OK.MODRM_XREG32: (32, "x"),
    OK.MODRM_XREG64: (64, "x"),
    OK.MODRM_XREG128: (128, "x"),
    #
    OK.MODRM_REG8: (8, "r"),
    OK.MODRM_REG16: (16, "r"),
    OK.MODRM_REG32: (32, "r"),
    OK.MODRM_REG64: (64, "r"),
    #
    OK.BYTE_WITH_REG8: (8, "r"),
    OK.BYTE_WITH_REG16: (16, "r"),
    OK.BYTE_WITH_REG32: (32, "r"),
    OK.BYTE_WITH_REG64: (64, "r"),
}

OK_ADDR_REG = {
    OK.RIP_BASE,
    OK.MODRM_RM_BASE,
    OK.SIB_INDEX,
    OK.SIB_BASE,
    OK.SIB_INDEX_AS_BASE,
}

_IMPLICIT_TO_OK: Dict[str, OK] = {
    "al": OK.IMPLICIT_AL,
    "ax": OK.IMPLICIT_AX,
    "eax": OK.IMPLICIT_EAX,
    "rax": OK.IMPLICIT_RAX,
    "dx": OK.IMPLICIT_DX,
    "edx": OK.IMPLICIT_EDX,
    "rdx": OK.IMPLICIT_RDX,
    "cl": OK.IMPLICIT_CL,
    "1": OK.IMPLICIT_1,
}

OK_TO_IMPLICIT: Dict[OK, str] = {v: k for k, v in _IMPLICIT_TO_OK.items()}


def _FP(bf0, b66, bf2, bf3, b0f, b48, d):
    return (bf0 << 13) | (b66 << 12) | (bf2 << 11) | (bf3 << 10) | (b0f << 9) | (b48 << 8) | d


def FingerPrintRawInstructions(data) -> int:
    b48 = 0
    bf0 = 0
    bf2 = 0
    bf3 = 0
    b66 = 0
    for n, d in enumerate(data):
        if (d & 0xf0) == 0x40:
            b48 = (d >> 3) & 1
        elif d == 0x66:
            b66 = 1
        elif d == 0xf0:
            bf0 = 1
        elif d == 0xf2:
            bf2 = 1
        elif d == 0xf3:
            bf3 = 1
        elif d == 0x0f:  # not a prefix
            return _FP(bf0, b66, bf2, bf3, 1, b48, data[n + 1])
        else:
            return _FP(bf0, b66, bf2, bf3, 0, b48, d)
    assert False


def FingerPrintOpcode(opc: "Opcode") -> List[int]:
    b48 = 1 if opc.rexw else 0
    bf0 = 0
    bf2 = 0
    bf3 = 0
    b66 = 0

    def emit(d, m, b0f):
        if m == 0xff:
            return [_FP(bf0, b66, bf2, bf3, b0f, b48, d)]
        else:
            assert m == 0xf8
            assert opc.byte_with_reg_pos >= 0
            return [_FP(bf0, b66, bf2, bf3, b0f, b48, d | r) for r in range(8)]

    for n, (d, m) in enumerate(zip(opc.data, opc.mask)):
        if d == 0x66:
            b66 = 1
            assert m == 0xff
        elif d == 0xf0:
            bf0 = 1
            assert m == 0xff
        elif d == 0xf2:
            bf2 = 1
            assert m == 0xff
        elif d == 0xf3:
            bf3 = 1
            assert m == 0xff
        elif d == 0x0f:  # not a prefix
            assert m == 0xff
            return emit(opc.data[n + 1], opc.mask[n + 1], 1)
        else:
            return emit(d, m, 0)
    assert False


@enum.unique
class MEM_MODE(enum.Enum):
    NONE = 1
    SIB = 2
    SIB_BP_DISP = 3
    RIP_DISP = 4


def StripRex(data: bytes) -> Tuple[int, bytes]:
    for n, b in enumerate(data):
        if b in {0x66, 0xf0, 0xf2, 0xf3}:
            continue
        if (b & 0xf0) == 0x40:
            data = data[:]
            del data[n]
            return b, data
        return 0, data


class Opcode:
    """
    An opcode represent an x86-64 instruction.
    We create separate Opcodes for each structurally different flavor of the
    instruction. For example `add reg, memory-access` will become six different
    opcodes (no-offset, offset8, offset32) X (sib, no-sib)
    The presence or absence of the REX.W and 0x66 (Operand override) prefixes also
    forces new Opcodes.
    """

    Opcodes: List["Opcode"] = []
    OpcodesByFP: Dict[int, List["Opcode"]] = collections.defaultdict(list)
    name_to_opcode: Dict[str, "Opcode"] = {}

    def __init__(self, name: str, variant: str, operands: List[str], format: str):
        Opcode.Opcodes.append(self)
        self.name: str = name
        self.variant: str = variant
        self.operands = operands
        self.format = format
        # the discriminant uniquely identifies and instruction
        # we also have the notion of a finger-print which is not unique 
        self.discriminant_mask: int = 0
        self.discriminant_data: int = 0
        self.mem_width = 0
        #
        self.rexw = False
        self.modrm_pos = -1
        self.sib_pos = -1
        self.offset_pos = -1
        self.imm_pos = -1
        self.byte_with_reg_pos = -1
        #
        self.fields: List[OK] = []
        self.mask: List[int] = []
        self.data: List[int] = []

    def __str__(self):
        fields_str = ' '.join([str(f) for f in self.fields])
        mask = Hexify(self.mask)
        data = Hexify(self.data)
        ops_str = ' '.join(self.operands)
        return f"{self.name}.{self.variant}  [{ops_str}] {self.format}   [{fields_str}]  mask:[{mask}] data:[{data}]"

    def EnumName(self):
        if self.variant:
            return self.name + "_" + self.variant
        else:
            return self.name

    def Finalize(self):
        assert re.match("^[a-z0-9]+$", self.name)
        if self.operands:
            if self.name in {"movsx", "movzx", "cvtsi2sd", "cvtsi2ss"}:
                bw = GetOpWidth(self.operands[1])
                self.variant = f"_{bw}" + self.variant
            if "xmm" not in self.operands[0] and self.format[0] != "I":
                bw = GetOpWidth(self.operands[0])
                self.variant = f"{bw}" + self.variant

        # hack to disambiguate:
        # movq, "W:xmm[63:0], r64[63:0]/m64", "RM", "REX.W 66 0F 6E /r", "SSE2 X64"
        # movq, "W:xmm[63:0], xmm[63:0]/m64", "RM", "F3 0F 7E /r", "SSE2"
        if self.name == "movq" and self.operands[1] == "xmm[63:0]/m64":
            self.variant += "_alt"

        if self.variant.startswith("_"):
            self.variant = self.variant[1:]
        fullname = self.EnumName()
        assert len(
            fullname) <= MAX_INSTRUCTION_NAME_LENGTH, f"max length exceeded: {fullname}  {len(fullname)}"
        assert fullname not in Opcode.name_to_opcode, f"duplicate={fullname}"
        Opcode.name_to_opcode[fullname] = self
        assert len(self.fields) <= MAX_OPERAND_COUNT, f"{self}"
        assert len(self.data) <= MAX_INSTRUCTION_LENGTH, f"{self}"
        # the discriminant reflects all instruction bytes except the rex byte
        self.discriminant_mask = int.from_bytes(self.mask[0:6], "little")
        self.discriminant_data = (self.discriminant_mask &
                                  int.from_bytes(self.data[0:6], "little"))
        expected_len = len(self.operands)
        if self.modrm_pos >= 0:
            if OK.OFFABS8 in self.fields or OK.OFFABS32 in self.fields:
                expected_len += 1
            if self.sib_pos >= 0:
                expected_len += 2
        for fp in FingerPrintOpcode(self):
            Opcode.OpcodesByFP[fp].append(self)
            # assert len(self.fields) == expected_len, f"{self.fields} vs {self.operands}"

    def AddRexW(self):
        self.rexw = True

    def AddImplicits(self, implicits: List[str]):
        for i in implicits:
            self.fields.append(_IMPLICIT_TO_OK[i])
            self.variant += "_" + i

    def AddByte(self, b: int):
        self.data.append(b)
        self.mask.append(0xff)

    def AddByteWithReg(self, b: int):
        self.variant += "_r"
        bw = FindSpecificOpWidth("O", self.operands, self.format)
        self.byte_with_reg_pos = len(self.data)
        self.fields.append({8: OK.BYTE_WITH_REG8,
                            16: OK.BYTE_WITH_REG16,
                            32: OK.BYTE_WITH_REG32,
                            64: OK.BYTE_WITH_REG64,
                            }[bw])
        self.data.append(b)
        self.mask.append(0xf8)
        assert (b & 0xf8) == b

    def AddReg(self):
        bw = FindSpecificOpWidth("R", self.operands, self.format)
        if IsOpXmm("R", self.operands, self.format):
            self.variant += "_x"
            self.fields.append({32: OK.MODRM_XREG32,
                                64: OK.MODRM_XREG64,
                                128: OK.MODRM_XREG128}[bw])
        else:
            self.variant += "_r"
            bw = FindSpecificOpWidth("R", self.operands, self.format)
            self.fields.append({8: OK.MODRM_REG8,
                                16: OK.MODRM_REG16,
                                32: OK.MODRM_REG32,
                                64: OK.MODRM_REG64}[bw])

    def AddRegOp(self, ext: Optional[int]):
        self.modrm_pos = len(self.data)
        mask = 0xc0
        data = (3 << 6)
        if ext is not None:
            mask |= 0x38
            data |= (ext << 3)
        self.mask.append(mask)
        self.data.append(data)
        bw = FindSpecificOpWidth("M", self.operands, self.format)
        if IsOpXmm("M", self.operands, self.format):
            self.variant += "_mx"
            self.fields.append({32: OK.MODRM_RM_XREG32,
                                64: OK.MODRM_RM_XREG64,
                                128: OK.MODRM_RM_XREG128}[bw])
        else:
            self.variant += "_mr"
            self.fields.append({8: OK.MODRM_RM_REG8,
                                16: OK.MODRM_RM_REG16,
                                32: OK.MODRM_RM_REG32,
                                64: OK.MODRM_RM_REG64,
                                }[bw])

    def AddMemOpCommonTail(self, mod: int):
        if mod == 0:
            pass
        elif mod == 1:
            self.variant += "8"
            self.offset_pos = len(self.data)
            self.fields.append(OK.OFFABS8)
            self.mask += [0]
            self.data += [0]
        elif mod == 2:
            self.variant += "32"
            self.offset_pos = len(self.data)
            self.fields.append(OK.OFFABS32)
            self.mask += [0, 0, 0, 0]
            self.data += [0, 0, 0, 0]

    def AddMemOp(self, mem_mode: MEM_MODE, mod: int, ext: int = -1):
        if not self.name.startswith("lea"):
            self.mem_width = FindSpecificOpWidth(
                "M", self.operands, self.format)
        self.modrm_pos = len(self.data)
        assert mod <= 2
        data = mod << 6
        mask = 0xc0

        if ext >= 0:
            assert ext <= 7
            mask |= 0x38
            data |= ext << 3
        if mem_mode in {MEM_MODE.SIB, MEM_MODE.SIB_BP_DISP}:
            # we need a sib byte
            self.mask.append(mask | 0x7)
            self.data.append(data | 0x4)
            self.sib_pos = len(self.data)
            if mem_mode == MEM_MODE.SIB:
                self.variant += "_mbis"
                self.mask.append(0)
                self.data.append(0)
                self.fields += [OK.SIB_BASE, OK.SIB_INDEX, OK.SIB_SCALE]
            else:
                # fix base at 5
                self.variant += "_mi"
                self.mask.append(0x07)
                self.data.append(0x05)
                self.fields += [OK.SIB_INDEX_AS_BASE, OK.SIB_SCALE]
                assert mod == 0
                mod = 2
        elif mem_mode == MEM_MODE.RIP_DISP:
            self.variant += "_mpc"
            self.mask.append(mask | 0x7)
            self.data.append(data | 0x5)
            self.fields += [OK.RIP_BASE]
            assert mod == 0
            mod = 2
        else:
            self.variant += "_mB"
            self.mask.append(mask)
            self.data.append(data)
            self.fields.append(OK.MODRM_RM_BASE)
        self.AddMemOpCommonTail(mod)

    def AddImmOp(self, op):
        self.imm_pos = len(self.data)
        size = 0
        if op == "ib":
            if self.name == "push" and self.format == "I":
                self.variant += "64"
                self.fields.append(OK.IMM8_64)
            elif self.name in _OPCODES_WITH_IMMEDIATE_SIGN_EXTENSION:
                bw = GetOpWidth(self.operands[0])
                self.fields.append({8: OK.IMM8, 16: OK.IMM8_16,
                                    32: OK.IMM8_32, 64: OK.IMM8_64}[bw])
            else:
                self.fields.append(OK.IMM8)
            self.variant += "_imm8"
            size = 1
        elif op == "iw":
            if self.name == "push" and self.format == "I":
                self.variant += "16"
            self.fields.append(OK.IMM16)
            self.variant += "_imm16"
            size = 2
        elif op == "id":
            if self.name == "push" and self.format == "I":
                self.variant += "64"
                self.fields.append(OK.IMM32_64)
            elif self.name in _OPCODES_WITH_IMMEDIATE_SIGN_EXTENSION:
                bw = GetOpWidth(self.operands[0])
                self.fields.append({32: OK.IMM32, 64: OK.IMM32_64}[bw])
            else:
                self.fields.append(OK.IMM32)
            self.variant += "_imm32"
            size = 4
        elif op == "iq":
            self.fields.append(OK.IMM64)
            self.variant += "_imm64"
            size = 8
        else:
            assert False
        self.mask += [0] * size
        self.data += [0] * size

    def AddOffsetPCREL(self, op):
        self.offset_pos = len(self.data)
        if op == "cb":
            self.fields.append(OK.OFFPCREL8)
            self.mask += [0]
            self.data += [0]
        elif op == "cd":
            self.fields.append(OK.OFFPCREL32)
            self.mask += [0, 0, 0, 0]
            self.data += [0, 0, 0, 0]
        else:
            assert False

    def DisassembleOperands(self, data: List) -> List[int]:
        rex, data = StripRex(data)

        out: List[int] = []

        def GetRegBits(offset: int, data_bit_pos, rex_bit_pos: int) -> int:
            nonlocal rex
            r = (data[offset] >> data_bit_pos) & 0x7
            if rex:
                r |= ((rex >> rex_bit_pos) & 1) << 3
            return r

        def GetSInt(pos, src_width, dst_width):
            x = int.from_bytes(
                data[pos: pos + src_width // 8], "little", signed=True)
            if dst_width is not None and dst_width != 64:
                return x & (1 << dst_width) - 1
            return x

        for o in self.fields:
            if o in OK_TO_IMPLICIT:
                out.append(0)  # dummy
            elif o in {OK.MODRM_RM_REG8, OK.MODRM_RM_REG16, OK.MODRM_RM_REG32, OK.MODRM_RM_REG64}:
                out.append(GetRegBits(self.modrm_pos, 0, 0))
                if o is OK.MODRM_RM_REG8 and 4 <= out[-1] <= 7:
                    assert rex
            elif o in {OK.MODRM_RM_XREG32, OK.MODRM_RM_XREG64, OK.MODRM_RM_XREG128}:
                out.append(GetRegBits(self.modrm_pos, 0, 0))
            elif o is OK.MODRM_RM_BASE:
                out.append(GetRegBits(self.modrm_pos, 0, 0))
            elif o in {OK.MODRM_REG8, OK.MODRM_REG16, OK.MODRM_REG32, OK.MODRM_REG64}:
                out.append(GetRegBits(self.modrm_pos, 3, 2))
                if o is OK.MODRM_REG8 and 4 <= out[-1] <= 7:
                    assert rex
            elif o in {OK.MODRM_XREG32, OK.MODRM_XREG64, OK.MODRM_XREG128}:
                out.append(GetRegBits(self.modrm_pos, 3, 2))
            elif o is OK.RIP_BASE:
                out.append(0)  # dummy
            elif o is OK.SIB_BASE:
                out.append(GetRegBits(self.sib_pos, 0, 0))
            elif o in {OK.SIB_INDEX_AS_BASE, OK.SIB_INDEX}:
                out.append(GetRegBits(self.sib_pos, 3, 1))
                assert o != OK.SIB_INDEX_AS_BASE or out[-1] != 0x4
            elif o is OK.SIB_SCALE:
                out.append(data[self.sib_pos] >> 6)
            elif o is OK.BYTE_WITH_REG8:
                r = GetRegBits(self.byte_with_reg_pos, 0, 0)
                if 4 <= r <= 7:
                    assert rex, f"xH (high byte) regs are not supported"
                out.append(r)
            elif o in {OK.BYTE_WITH_REG16, OK.BYTE_WITH_REG32, OK.BYTE_WITH_REG64}:
                out.append(GetRegBits(self.byte_with_reg_pos, 0, 0))
            elif o in OK_IMM_TO_SIZE:
                out.append(GetSInt(self.imm_pos, *OK_IMM_TO_SIZE[o]))
            elif o in OK_OFF_TO_SIZE:
                out.append(GetSInt(self.offset_pos, *OK_OFF_TO_SIZE[o]))
            else:
                assert False, f"{o}"
        assert len(self.fields) == len(out), f"{self} {out}"
        return out

    def AssembleOperands(self, operands: List[int]) -> List[int]:
        assert len(operands) == len(self.fields)
        rex = 0
        if self.rexw:
            rex |= 0x08
        out = self.data[:]

        def SetRegBits(reg, pos, shift, rex_shift):
            nonlocal rex
            out[pos] |= (reg & 0x7) << shift
            rex |= ((reg >> 3) & 1) << rex_shift

        def SetSInt(v, pos, dst_width, src_width):
            # print (f"{self.name}:  {v} {pos} {dst_byte_width}  {src_bit_width}")
            # if not src_bit_width:
            #    v += (8 << dst_byte_width)

            v &= (1 << dst_width) - 1
            # TODO: check
            # assert -(8) <= v < (8 << dst_byte_width)
            while v:
                out[pos] = v & 0xff
                pos += 1
                v >>= 8

        for v, o in zip(operands, self.fields):
            if o in OK_TO_IMPLICIT:
                continue
            elif o in {OK.MODRM_RM_REG8, OK.MODRM_RM_REG16, OK.MODRM_RM_REG32,
                       OK.MODRM_RM_REG64}:
                if o is OK.MODRM_RM_REG8 and (4 <= v <= 7):
                    rex |= 0x40  # force rex, otherwise we select ah, ch, dh, bh
                SetRegBits(v, self.modrm_pos, 0, 0)
            elif o in {OK.MODRM_RM_XREG32, OK.MODRM_RM_XREG64, OK.MODRM_RM_XREG128}:
                SetRegBits(v, self.modrm_pos, 0, 0)
            elif o is OK.MODRM_RM_BASE:
                SetRegBits(v, self.modrm_pos, 0, 0)
            elif o in {OK.MODRM_REG8, OK.MODRM_REG16, OK.MODRM_REG32,
                       OK.MODRM_REG64}:
                if o is OK.MODRM_REG8 and (4 <= v <= 7):
                    rex |= 0x40  # force rex, otherwise we select ah, ch, dh, bh
                SetRegBits(v, self.modrm_pos, 3, 2)
            elif o in {OK.MODRM_XREG32, OK.MODRM_XREG64, OK.MODRM_XREG128}:
                SetRegBits(v, self.modrm_pos, 3, 2)
            elif o is OK.RIP_BASE:
                continue
            elif o is OK.SIB_BASE:
                SetRegBits(v, self.sib_pos, 0, 0)
            elif o is OK.SIB_INDEX_AS_BASE:
                assert v != 4
                SetRegBits(v, self.sib_pos, 3, 1)
            elif o is OK.SIB_INDEX:
                SetRegBits(v, self.sib_pos, 3, 1)
            elif o is OK.SIB_SCALE:
                assert 0 <= v <= 3
                out[self.sib_pos] |= v << 6
            elif o is OK.BYTE_WITH_REG8:
                if 4 <= v <= 7:  # otherwise we use high byte regs (ah, ...)
                    rex |= 0x40
                SetRegBits(v, self.byte_with_reg_pos, 0, 0)
            elif o in {OK.BYTE_WITH_REG16, OK.BYTE_WITH_REG32,
                       OK.BYTE_WITH_REG64}:
                SetRegBits(v, self.byte_with_reg_pos, 0, 0)
            elif o in OK_IMM_TO_SIZE:
                SetSInt(v, self.imm_pos, *OK_IMM_TO_SIZE[o])
            elif o in OK_OFF_TO_SIZE:
                SetSInt(v, self.offset_pos, *OK_OFF_TO_SIZE[o])
            else:
                assert False, f"{o}"

        if rex:
            pos = 0
            for b in out:
                if b in {0xf0, 0xf2, 0xf3, 0x66}:
                    pos += 1
                else:
                    break
            out.insert(pos, rex | 0x40)
        return out

    def UsesRex(self, operands: List[int]) -> bool:
        assert len(operands) == len(self.fields)
        if self.rexw:
            return True
        for v, o in zip(operands, self.fields):
            if o in {OK.MODRM_RM_REG8, OK.MODRM_RM_REG16, OK.MODRM_RM_REG32,
                     OK.MODRM_RM_REG64, OK.MODRM_RM_XREG32, OK.MODRM_RM_XREG64,
                     OK.MODRM_RM_XREG128, OK.MODRM_RM_BASE,
                     OK.MODRM_REG8, OK.MODRM_REG16, OK.MODRM_REG32,
                     OK.MODRM_REG64, OK.MODRM_XREG32, OK.MODRM_XREG64, OK.MODRM_XREG128,
                     OK.SIB_BASE, OK.SIB_INDEX_AS_BASE, OK.SIB_INDEX, OK.BYTE_WITH_REG8,
                     OK.BYTE_WITH_REG16, OK.BYTE_WITH_REG32,
                     OK.BYTE_WITH_REG64}:
                if o in {OK.MODRM_RM_REG8, OK.MODRM_REG8, OK.BYTE_WITH_REG8} and (4 <= v <= 7):
                    return True  # force rex, otherwise we select ah, ch, dh, bh
                if v >> 3:   # uses register r8 or  higher
                    return True
        return False

    @classmethod
    def FindOpcode(cls, data: List) -> Optional["Opcode"]:
        rules = Opcode.OpcodesByFP[FingerPrintRawInstructions(data)]
        _, data = StripRex(data)
        discriminant = int.from_bytes(data, "little")
        for r in rules:
            if (r.discriminant_mask & discriminant) == r.discriminant_data:
                return r
        return None


_RELOC_TYPE_X64_NONE = 0  # avoid elf dependency


@dataclasses.dataclass
class Ins:
    """X64 flavor of an Instruction

    There can be at most one relocation associated with an Ins
    """
    opcode: Opcode
    operands: List[int] = dataclasses.field(default_factory=list)
    #
    # Note the addend is store in `operands[reloc_pos]
    reloc_symbol: str = ""
    reloc_kind: int = _RELOC_TYPE_X64_NONE
    reloc_pos = 0
    is_local_sym = False

    def clear_reloc(self):
        self.reloc_kind = _RELOC_TYPE_X64_NONE
        self.reloc_pos = 0

    def has_reloc(self):
        return self.reloc_kind != _RELOC_TYPE_X64_NONE

    def set_reloc(self, kind, is_local, pos, symbol):
        self.reloc_kind = kind
        self.reloc_pos = pos
        self.reloc_symbol = symbol
        self.is_local_sym = is_local

    def __str__(self):
        reloc_str = ""
        if self.has_reloc():
            reloc_str = f"{self.reloc_kind}:{self.reloc_symbol}:{self.operands[self.reloc_pos]}"
        return f"{self.opcode.EnumName()} {reloc_str}"


def Disassemble(data: List) -> Optional[Ins]:
    opcode = Opcode.FindOpcode(data)
    if opcode is None:
        return None
    operands = opcode.DisassembleOperands(data)
    if operands is None:
        return None
    return Ins(opcode, operands)


def Assemble(ins: Ins) -> List[int]:
    assert not ins.has_reloc(), "reloc has not been resolved"
    return ins.opcode.AssembleOperands(ins.operands)


def InsLength(ins: Ins) -> int:
    return len(ins.opcode.data) + ins.opcode.UsesRex(ins.operands)


_SUPPORTED_ENCODING_PARAMS = {
    "/0", "/1", "/2", "/3", "/4", "/5", "/6", "/7",  #
    "/r",  #
    "REX.W",
    "ib", "iw", "id", "iq",  #
    "cd", "cb",
}

_RE_BYTE_VARIATIONS = re.compile("^[0-9A-F][0-9A-F]([+]r)?$")

_RE_BYTE = re.compile("^[0-9A-F][0-9A-F]$")
_RE_BYTE_WITH_REG = re.compile("^[0-9A-F][0-9A-F][+]r?$")

_SIB_MOD_COMBOS = [
    (0, MEM_MODE.SIB_BP_DISP), (0, MEM_MODE.RIP_DISP),
    (0, MEM_MODE.SIB), (0, MEM_MODE.NONE),
    (1, MEM_MODE.SIB), (1, MEM_MODE.NONE),
    (2, MEM_MODE.SIB), (2, MEM_MODE.NONE),
]


def HandlePatternMR(name: str, ops, format, encoding, inv: bool, after=[]):
    if name != "lea":
        # the register encoding does not make sense for lea
        opc = Opcode(name, "", ops, format)
        for x in encoding:
            if x == "REX.W":
                opc.AddRexW()
            elif _RE_BYTE.match(x):
                opc.AddByte(int(x, 16))
            elif x == "/r":
                if inv:
                    opc.AddReg()
                    opc.AddRegOp(None)
                else:
                    opc.AddRegOp(None)
                    opc.AddReg()
                opc.AddImplicits(after)
            elif x in {"ib", "iw", "id", "iq"}:
                opc.AddImmOp(x)
            else:
                assert False

    for mod, sib_mode in _SIB_MOD_COMBOS:
        opc = Opcode(name, "", ops, format)
        for x in encoding:
            if x == "REX.W":
                opc.AddRexW()
            elif _RE_BYTE.match(x):
                opc.AddByte(int(x, 16))
            elif x == "/r":
                if inv:
                    opc.AddReg()
                    opc.AddMemOp(sib_mode, mod)
                else:
                    opc.AddMemOp(sib_mode, mod)
                    opc.AddReg()
                opc.AddImplicits(after)
            elif x in {"ib", "iw", "id", "iq"}:
                opc.AddImmOp(x)
            else:
                assert False


def HandlePatternMI(name: str, ops, format, encoding, before, after):
    opc = Opcode(name, "", ops, format)
    for x in encoding:
        if x == "REX.W":
            opc.AddRexW()
        elif _RE_BYTE.match(x):
            opc.AddByte(int(x, 16))
        elif x.startswith("/"):
            ext = int(x[1:])
            opc.AddImplicits(before)
            opc.AddRegOp(ext)
            opc.AddImplicits(after)
        elif x in {"ib", "iw", "id", "iq"}:
            opc.AddImmOp(x)
        else:
            assert False, f"unexpected pattern for {name}"

    # 81 7c 24 28 ff 0f 00    cmp    DWORD PTR [rsp+0x28],0xfff
    for mod, sib_mode in _SIB_MOD_COMBOS:
        opc = Opcode(name, "", ops, format)
        for x in encoding:
            if x == "REX.W":
                opc.AddRexW()
            elif _RE_BYTE.match(x):
                opc.AddByte(int(x, 16))
            elif x.startswith("/"):
                ext = int(x[1:])
                opc.AddImplicits(before)
                opc.AddMemOp(sib_mode, mod, ext=ext)
                opc.AddImplicits(after)
            elif x in {"ib", "iw", "id", "iq"}:
                opc.AddImmOp(x)
            else:
                assert False


def HandlePattern(name: str, ops: List[str], format: str, encoding: List[str], meta: List[str]):
    assert format in _SUPPORTED_FORMATS, f"bad format [{format}]"
    for f in encoding:
        assert f in _SUPPORTED_ENCODING_PARAMS or _RE_BYTE_VARIATIONS.match(
            f), f"bad parameter [{repr(f)}]"
    for o in ops:
        assert o in _SUPPORTED_OPERANDS, f"unexpected operand: [{o}]"

    assert len(format) == len(ops), f"{name} fmt={format} ops={ops}"
    for op, kind in zip(ops, format):
        assert op in _OP_MAP[kind], f"{op} not allowed for {kind}"

    if format in {"MI", "M", "xM", "xxM", "Mx"}:
        before = []
        after = []
        seen_non_X = False
        for i, c in enumerate(format):
            if c != "x":
                seen_non_X = True
            elif seen_non_X:
                after.append(ops[i])
            else:
                before.append(ops[i])
        HandlePatternMI(name, ops, format, encoding, before, after)
    elif format == "MR":
        HandlePatternMR(name, ops, format, encoding, inv=False)
    elif format == "MRx":
        HandlePatternMR(name, ops, format, encoding, inv=False, after=[ops[-1]])
    elif format == "RM" or format == "RMI":
        HandlePatternMR(name, ops, format, encoding, inv=True)
    elif format == "":
        opc = Opcode(name, "", ops, format)
        for x in encoding:
            if _RE_BYTE.match(x):
                opc.AddByte(int(x, 16))
            else:
                assert False
    elif format in {"I", "O", "OI", "xI", "xO", "Ox"}:
        opc = Opcode(name, "", ops, format)
        before: List[str] = []
        after: List[str] = []
        seen_non_X = False
        for i, c in enumerate(format):
            if c != "x":
                seen_non_X = True
            elif seen_non_X:
                after.append(ops[i])
            else:
                before.append(ops[i])
        for x in encoding:
            if x == "REX.W":
                opc.AddRexW()
            elif _RE_BYTE_WITH_REG.match(x):
                opc.AddImplicits(before)
                opc.AddByteWithReg(int(x[0:2], 16))
                opc.AddImplicits(after)
            elif _RE_BYTE.match(x):
                opc.AddByte(int(x, 16))
            elif x in {"ib", "iw", "id", "iq"}:
                opc.AddImplicits(before)
                opc.AddImmOp(x)
                opc.AddImplicits(after)
            else:
                assert False
    elif format in {"xx"}:
        opc = Opcode(name, "", ops, format)
        opc.AddImplicits(ops)
        for x in encoding:
            if x == "REX.W":
                opc.AddRexW()
            elif _RE_BYTE.match(x):
                opc.AddByte(int(x, 16))
            else:
                assert False
    elif format == "D":
        opc = Opcode(name, "", ops, format)
        for x in encoding:
            if _RE_BYTE.match(x):
                opc.AddByte(int(x, 16))
            elif x in {"cb", "cd"}:
                opc.AddOffsetPCREL(x)
            else:
                assert False
    else:
        assert False, f"bad format {format}"


def ExtractOps(s):
    def clean(o):
        if o[0:2] in _OPERAND_MODIFIERS:
            o = o[2:]
        if o[0] == "~":  # indicates commutativity
            o = o[1:]
        return o

    return [clean(x) for x in s.split(",") if x]


def OpcodeSanityCheck(opcodes: Dict[int, List[Opcode]]):
    patterns = collections.defaultdict(list)
    for opcode in Opcode.Opcodes:
        patterns[(opcode.rexw, opcode.discriminant_mask,
                  opcode.discriminant_data)].append(opcode)

    print(f"Checkin Opcodes for conflicts")
    for k, group in patterns.items():
        if len(group) != 1:
            print (f"ERROR: this should not happen, maybe the discriminant needs to be longer")
            print (f"{k[1]:x} {k[2]:x}", [x.name for x in group])
            assert False
    print(f"Checkin Opcodes for overlap causing decoding ambiguity")
    for group in opcodes.values():
        for a, b in itertools.combinations(group, 2):
            if a.rexw == b.rexw:
                c = a.discriminant_mask & b.discriminant_mask
                if (a.discriminant_data & c) == (b.discriminant_data & c):
                    assert a.name == b.name
                    if a.variant.replace("mbis", "mB") == b.variant:
                        # this is ok sib requires a special bit pattern in the
                        # modrm byte
                        continue
                    if a.variant.replace("mi32", "mB") == b.variant:
                        # same as above
                        continue
                    if a.variant.replace("mi32", "mbis") == b.variant:
                        # this is ok as the bp_disp_off32 requires a special
                        # bit pattern in the sib byte
                        continue
                    if a.variant.replace("mpc32", "mB") == b.variant:
                        # this is ok, rip_disp requires a special bit pattern in the
                        # modrm byte
                        continue

                    print(a)
                    print(b)
                    print()
                    assert False


def FixupFormat(name: str, format: str, ops: List, encoding) -> str:
    """Make sure for each operands we have exactly one format character"""
    if format == "I" and ("B8+r" in encoding or "B0+r" in encoding):
        return "OI"
    if format == "NONE":
        if len(ops) == 0:
            return ""
        else:
            format = ""

    if len(format) == len(ops):
        return format

    assert format in {"", "I", "M", "O", "MR"}, f"name={name} format={format}, ops={ops}"
    f = [c for c in format]
    def tr(x):
        if x in _IMPLICIT_OPERANDS or x == "1":
            return "x"
        else:
            return f.pop(0)

    return "".join(tr(o) for o in ops)


# this excludes among others:
# "and", "X:r64, ud", "MI"      , "81 /4 id"
# "X:rax, ud", "I"       , "25 id"
def SkipInstruction(name, format, ops):
    if format == "MI" and ops[0] == "r64":
        return True

    if format == "I" and ops[0] == "rax" and ops[1] == "ud":
        return True

    # the decision which one of these to skip is somewhat arbitrary but
    # we followed what objdump does
    if name == "xchg" and (format == "RM" or ops[0].endswith("ax")):
        return True
    return False


def CreateOpcodes(instructions: List, verbose: bool):
    count = collections.defaultdict(int)
    for name, ops, format, encoding, metadata in instructions:
        if IsDisallowExtension(metadata):
            continue
        ops = ops.replace("<", "").replace(">", "").replace(", ", ",")
        ops_orig = [x for x in ops.split(",") if x]
        written_ops = [x for x in ops_orig if x[0:2]
                       in {"X:", "x:", "W:", "w:"}]
        assert len(
            written_ops) <= 1 or name in _OPCODES_WITH_MULTIPLE_REG_WRITE, f"{name}"
        ops = ExtractOps(ops)
        name = name.split("/")[0]
        # hack merge entries for movss/movsd
        if name in {"movss", "movsd"}:
            if ops[1] in {"m32", "m64"}:
                bits = int(ops[1][1:])
                ops[1] = f"xmm[{bits - 1}:0]/{ops[1]}"
            elif ops[0] in {"m32", "m64"}:
                bits = int(ops[0][1:])
                ops[0] = f"xmm[{bits - 1}:0]/{ops[0]}"
            else:
                continue
        if name not in SUPPORTED_OPCODES or ContainsUnsupportedOperands(ops):
            continue
        if SkipInstruction(name, format, ops):
            continue

        # hack: the /r value is ignored by the CPU, assume it is zero
        if name.startswith("set") and "/r" in encoding:
            encoding = encoding.replace("/r", "/0")

        count[name] += 1
        metadata = metadata.split()
        encoding = encoding.split()
        # hack
        format = FixupFormat(name, format, ops, encoding)

        assert format in _SUPPORTED_FORMATS, f"{format}"
        if verbose:
            print(name, ops, format, encoding, metadata)
        HandlePattern(name, ops, format, encoding, metadata)
        if "_XLock" in metadata:
            name = "lock" + name
            if name in SUPPORTED_OPCODES:
                HandlePattern(name, ops, format, ["F0"] + encoding,  metadata)
                count[name] += 1

    for k in SUPPORTED_OPCODES:
        assert count[k], f"unknown opcode [{k}]"
    for opcode in Opcode.Opcodes:
        opcode.Finalize()


def LoadOpcodes(filename: str):
    # This file is file https://github.com/asmjit/asmdb (see file comment)
    _START_MARKER = "// ${JSON:BEGIN}"
    _END_MARKER = "// ${JSON:END}"
    data = open(filename).read()
    start = data.find(_START_MARKER) + len(_START_MARKER)
    end = data.find(_END_MARKER)

    tables = json.loads(data[start:end])

    CreateOpcodes(tables["instructions"], False)


def _render_enum_simple(symbols, name, fout):
    print("\n%s {" % name, file=fout)
    for sym in symbols:
        print(f"    {sym},", file=fout)
    print("};", file=fout)


def _EmitCodeH(fout):
    print(
        f"constexpr const unsigned MAX_OPERAND_COUNT = {MAX_OPERAND_COUNT};", file=fout)
    print(
        f"constexpr const unsigned MAX_INSTRUCTION_LENGTH = {MAX_INSTRUCTION_LENGTH};", file=fout)
    print(f"constexpr const unsigned MAX_INSTRUCTION_LENGTH_WITH_PREFIXES = {MAX_INSTRUCTION_LENGTH_WITH_PREFIXES};",
          file=fout)
    print(
        f"constexpr const unsigned MAX_INSTRUCTION_NAME_LENGTH = {MAX_INSTRUCTION_NAME_LENGTH};", file=fout)
    print(
        f"constexpr const unsigned MAX_FINGERPRINT = {MAX_FINGERPRINT};", file=fout)

    cgen.RenderEnum(cgen.NameValues(MEM_MODE),
                    "class MEM_WIDTH : uint8_t", fout)
    cgen.RenderEnum(cgen.NameValues(OK), "class OK : uint8_t", fout)


def _RenderOpcodeTable():
    """Note: we sneak in an invalid first entry

    The first entry only match the 0x0 instruction which happens to be invalid
    so it can serve as a sentinel
    """

    def Q(x):
        return "NA" if x < 0 else str(x)

    out = [
        '  // invalid',
        '  {0, 0, 0, 0, NA, NA, NA, NA, NA, {}, {}, {}},'
    ]

    for name, opc in sorted(Opcode.name_to_opcode.items()):
        mem_width_log = {0: 0, 8: 1, 16: 2,
                         32: 3, 64: 4, 128: 5}[opc.mem_width]
        out += [
            f"  {{{len(opc.fields)}, {len(opc.data)}, {mem_width_log}, {int(opc.rexw)}, {Q(opc.modrm_pos)}, " +
            f"{Q(opc.sib_pos)}, {Q(opc.offset_pos)}, {Q(opc.imm_pos)}, {Q(opc.byte_with_reg_pos)},  // {name}",
            "   {" + ", ".join(["OK::" + f.name for f in opc.fields]) + "},",
            "   {" + ", ".join([f"0x{b:02x}" for b in opc.data]) + "},",
            "   {" + ", ".join([f"0x{b:02x}" for b in opc.mask]) + "}},",
        ]
    return out


def _EmitEnum(fout):
    print ("// auto generated - do not edit", file=fout)
    opcodes = list(sorted(Opcode.name_to_opcode.keys()))
    # note we sneak in an invalid first entry
    _render_enum_simple(["invalid"] + opcodes, "enum class OPC : uint16_t", fout)


def _EmitEncodings(fout):
    print("// Indexed by OPC", file=fout)
    print("const Opcode OpcodeTableEncodings[] = {", file=fout)
    print("\n".join(_RenderOpcodeTable()), file=fout)
    print("};\n", file=fout)


_MNEMONIC_HASH_TABLE_SIZE = 8192


def hash_djb2(x: str):
    """ Simple string hash function for mnemonics

     see http://www.cse.yorku.ca/~oz/hash.html"""
    h = 5381
    for c in x:
        h = (h << 5) + h + ord(c)
    return h & 0xffff


def _RenderMnemonicHashLookup():
    table = ["invalid"] * _MNEMONIC_HASH_TABLE_SIZE
    for name, opc in Opcode.name_to_opcode.items():
        h = hash_djb2(name)
        for d in range(16):
            hh = (h + d) % _MNEMONIC_HASH_TABLE_SIZE
            if table[hh] == "invalid":
                table[hh] = name
                break
        else:
            assert False, f"probing distance exceeded {name}"
    items = [f"OPC::{t}," for t in table]
    return ["   " + " ".join(items[i:i + 4]) for i in range(0, len(items), 4)]


def _EmitNames(fout):
    print("// auto generated - do not edit", file=fout)
    print("// OpcodeTableName is indexed by OPC", file=fout)
    print("const char OpcodeTableNames[][32] = {", file=fout)
    print('  "invalid",', file=fout)
    for name in sorted(Opcode.name_to_opcode.keys()):
        print(f'  "{name}",', file=fout)
    print("};\n", file=fout)
    print(
        f"constexpr const unsigned MNEMONIC_HASH_TABLE_SIZE = {_MNEMONIC_HASH_TABLE_SIZE};", file=fout)
    print("// Indexed by djb2 hash of mnemonic. Collisions are resolved via linear probing",
          file=fout)
    print(
        f"static const OPC MnemonicHashTable[MNEMONIC_HASH_TABLE_SIZE] = {{", file=fout)
    print("\n".join(_RenderMnemonicHashLookup()), file=fout)
    print("};\n", file=fout)


def _EmitCollisions(fout):
    print("// Indexed by Fingerprint", file=fout)
    print("uint16_t FingerprintToCollisionIndex[] = {", file=fout)
    pos = 0
    count = 1
    for fp, collisions in sorted(Opcode.OpcodesByFP.items()):
        while pos < fp:
            print("  0,")
            pos += 1
        print(f"  {count},  // {fp}")
        count += 1 + len(collisions)
        pos += 1
    print("};\n", file=fout)
    print("")
    print("OPC FingerprintCollisions[] = {", file=fout)
    print(f"  OPC::invalid, ")
    count = 1
    for fp, collisions in sorted(Opcode.OpcodesByFP.items()):
        for c in collisions:
            print(f"  OPC::{c.EnumName()},  // {fp}")
        print(f"  OPC::invalid, ")
    print("};\n", file=fout)


def _EmitCodeC(fout):
    cgen.RenderEnumToStringMap(cgen.NameValues(OK), "OK", fout)
    cgen.RenderEnumToStringFun("OK", fout)


LoadOpcodes(os.path.join(os.path.dirname(__file__), "x86data.js"))

if __name__ == "__main__":
    if len(sys.argv) <= 1:
        print(f"TOTAL instruction templates: {len(Opcode.Opcodes)}")
        OpcodeSanityCheck(Opcode.OpcodesByFP)
        print(f"Different fingerprints: {len(Opcode.OpcodesByFP)}")
        print(f"Max fingerprint: {max(Opcode.OpcodesByFP.keys())}")
        print(
            f"Max fingerprint collisions: {max(len(x) for x in Opcode.OpcodesByFP.values())}")
        last_name = ""
        for opc in Opcode.Opcodes:
            if last_name != opc.name:
                print()
                last_name = opc.name
            fields_str = ' '.join([str(f) for f in opc.fields])
            ops_str = ' '.join(opc.operands)
            print(f"{opc.EnumName():20} {ops_str:30} {fields_str}")
        if False:
            for k, v in _OPCODES_BY_FP.items():
                if v:
                    print(f"{k:10x} {len(v)}")
    elif sys.argv[1] == "gen_encodings":
        _EmitEncodings(sys.stdout)
    elif sys.argv[1] == "gen_enum":
        _EmitEnum(sys.stdout)
    elif sys.argv[1] == "gen_names":
        _EmitNames(sys.stdout)
    elif sys.argv[1] == "gen_collisions":
        _EmitCollisions(sys.stdout)
    elif sys.argv[1] == "gen_c":
        cgen.ReplaceContent(_EmitCodeC, sys.stdin, sys.stdout)
    elif sys.argv[1] == "gen_h":
        cgen.ReplaceContent(_EmitCodeH, sys.stdin, sys.stdout)
