#!/usr/bin/python3

"""
Translator from C to Cwerg IR

This is not even close to being done and mostly a horrible
unprincipled hack.

EmitIR() is the main work-horse which traverse the AST recursively.

It usually does a post-order traversal where results from
the children are stored int the node_value map.
For some node types, however, we follow a pre-order approach.

"""
import re
import sys
import argparse
from typing import List

from pycparser import c_ast, parse_file

import canonicalize
import common
import meta

RE_NUMBER = re.compile("^[-+]?[0-9]*[.]?[0-9]+([eE][-+]?[0-9]+)?$")

POINTER = ("*",)

TYPE_TRANSLATION_64 = {
    ("char",): "S8",
    ("char", "unsigned",): "U8",
    ("short",): "S16",
    ("short", "unsigned",): "U16",
    ("int",): "S32",
    ("int", "unsigned",): "U32",
    ("long",): "S64",
    ("long", "unsigned",): "U64",
    ("long", "long",): "S64",
    ("long", "long", "unsigned",): "U64",
    ("float",): "F32",
    ("double",): "F64",
    ("void",): None,
    POINTER: "A64",
}

TYPE_TRANSLATION_32 = {
    ("char",): "S8",
    ("char", "unsigned",): "U8",
    ("short",): "S16",
    ("short", "unsigned",): "U16",
    ("int",): "S32",
    ("int", "unsigned",): "U32",
    ("long",): "S32",
    ("long", "unsigned",): "U32",
    ("long", "long",): "S64",
    ("long", "long", "unsigned",): "U64",
    ("float",): "F32",
    ("double",): "F64",
    ("void",): None,
    POINTER: "A32",
}

# MUST BE SET BEFORE USE
TYPE_TRANSLATION = None

tmp_counter = 0


def GetUnique():
    global tmp_counter
    tmp_counter += 1
    return tmp_counter


def RestTmpCounter():
    global tmp_counter
    # for debugging it can be useful to disable this because it makes everyname unique
    tmp_counter = 0


ALL_BITS_SET = {
    "S8": -1,
    "S16": -1,
    "S32": -1,
    "S64": -1,
    "U8": (1 << 8) - 1,
    "U16": (1 << 16) - 1,
    "U32": (1 << 32) - 1,
    "U64": (1 << 64) - 1,
}


def IsNumber(s):
    return RE_NUMBER.match(s)


RE_NUMBER_SUFFIX = re.compile("(ull|ll|ul|l|u)$", re.IGNORECASE)

_NUMBER_TYPES = (int, float)


def StripNumberSuffix(s):
    m = RE_NUMBER_SUFFIX.search(s)
    if m:
        s = s[:m.start()]
    return s


def ExtractNumber(s):
    if s[0] == "'" and s[-1] == "'":
        if s[1] == "\\":
            if s[2] == "n":
                return 10
            assert False, "add escapes as needed"
        else:
            assert len(s) == 3, f"unexpected number: [{s}]"
            return ord(s[1])
    s = StripNumberSuffix(s)
    # gross hack - try a few conversions
    try:
        return int(s, 0)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        pass
    return float.fromhex(s)


def align(x, a):
    return (x + a - 1) // a * a


def SizeOfAndAlignmentStruct(struct: c_ast.Struct, meta_info):
    if struct.decls is None:
        struct = meta_info.struct_links[struct]
    alignment = 1
    size = 0
    for f in struct.decls:
        s, a = SizeOfAndAlignment(f.type, meta_info)
        if a > alignment:
            alignment = a
        size = align(size, a) + s
        # print ("@@", s, a, size, alignment, f)

    return size, alignment


def GetStructOffset(struct: c_ast.Struct, field: c_ast.ID, meta_info):
    if struct.decls is None:
        struct = meta_info.struct_links[struct]
    offset = 0
    for f in struct.decls:
        if f.name == field.name:
            return offset
        s, a = SizeOfAndAlignment(f.type, meta_info)
        offset = align(offset, a) + s
    assert False, f"GetStructOffset unknown field {struct} {field}"


def SizeOfAndAlignmentUnion(struct: c_ast.Union, meta_info):
    if struct.decls is None:
        struct = meta_info.struct_links[struct]
    alignment = 1
    size = 0
    for f in struct.decls:
        s, a = SizeOfAndAlignment(f.type, meta_info)
        if a > alignment:
            alignment = a
        if s > size:
            size = s
    # assert False, f"SizeOfAndAlignmentUnion {struct}"
    return size, alignment


def SizeOfAndAlignment(node, meta_info):
    if isinstance(node, (c_ast.Typename, c_ast.Decl, c_ast.TypeDecl)):
        return SizeOfAndAlignment(node.type, meta_info)

    if isinstance(node, c_ast.Struct):
        return SizeOfAndAlignmentStruct(node, meta_info)
    elif isinstance(node, c_ast.Union):
        return SizeOfAndAlignmentUnion(node, meta_info)
    elif isinstance(node, c_ast.IdentifierType):
        type_name = TYPE_TRANSLATION[tuple(node.names)]
        assert type_name, f"could not determine sizeof {node}"
        bitsize = int(type_name[1:])
        return bitsize // 8, bitsize // 8
    elif isinstance(node, c_ast.ArrayDecl):
        size, align = SizeOfAndAlignment(node.type, meta_info)
        size = (size + align - 1) // align * align
        return size * int(node.dim.value), align
    elif isinstance(node, c_ast.PtrDecl):
        type_name = TYPE_TRANSLATION[POINTER]
        bitsize = int(type_name[1:])
        return bitsize // 8, bitsize // 8
    else:
        assert False, node


def IsLocalDecl(_node, parent):
    return not isinstance(parent, (c_ast.FileAST, c_ast.ParamList, c_ast.FuncDef))


def ScalarDeclType(type):
    if isinstance(type, c_ast.TypeDecl):
        return ScalarDeclType(type.type)

    if isinstance(type, c_ast.ArrayDecl):
        return None
    elif isinstance(type, c_ast.PtrDecl):
        return TYPE_TRANSLATION[POINTER]
    elif isinstance(type, c_ast.IdentifierType):
        return TYPE_TRANSLATION[tuple(type.names)]
    elif isinstance(type, (c_ast.FuncDef, c_ast.Struct, c_ast.Union)):
        return None
    else:
        assert False, type


def GetVarKind(node, parent):
    if isinstance(parent, c_ast.ParamList):
        return "param"
    elif isinstance(parent, c_ast.FileAST):
        return "\nglobal"
    elif isinstance(parent, c_ast.FuncDef):
        return "result"
    else:
        return "local"


def StringifyType(type_or_decl):
    if isinstance(type_or_decl, (c_ast.Decl, c_ast.TypeDecl, c_ast.Typename)):
        return StringifyType(type_or_decl.type)

    if isinstance(type_or_decl, c_ast.FuncDecl):
        return "c32"
    elif isinstance(type_or_decl, c_ast.PtrDecl):
        return TYPE_TRANSLATION[POINTER]
    elif isinstance(type_or_decl, c_ast.ArrayDecl):
        return TYPE_TRANSLATION[POINTER]
    elif isinstance(type_or_decl, (c_ast.Struct, c_ast.Union)):
        return TYPE_TRANSLATION[POINTER]
    elif isinstance(type_or_decl, c_ast.IdentifierType):
        return TYPE_TRANSLATION[tuple(type_or_decl.names)]
    elif type(type_or_decl) == str:
        return type_or_decl
    else:
        assert False, type_or_decl
        # return str(type_or_decl)


def GetTmp(type):
    assert type is not None
    return "%%%s_%s" % (StringifyType(type), GetUnique())


def HasNoResult(type):
    return isinstance(type, c_ast.IdentifierType) and type.names[0] == "void"


TAB = "  "


# x->b2->a1 = 0
#   Assignment: =
#     StructRef: .
#       UnaryOp: *
#         StructRef: .
#           UnaryOp: *
#             ID: x
#           ID: b2
#       ID: a1
#     Constant: int, 0

# xx.b1.c1.d1 = 0
# Assignment: =
#       StructRef: .
#         StructRef: .
#           StructRef: .
#             ID: xx
#             ID: b1
#           ID: c1
#         ID: d1
#       Constant: int, 0


def GetLValueAddress(lvalue, meta_info: meta.MetaInfo, node_value, id_gen):
    if isinstance(lvalue, c_ast.UnaryOp) and lvalue.op == "*":
        EmitIR([lvalue, lvalue.expr], meta_info, node_value, id_gen)
        node_value[lvalue] = node_value[lvalue.expr]
    elif isinstance(lvalue, c_ast.ArrayRef):
        assert False, lvalue
    elif isinstance(lvalue, c_ast.StructRef):
        struct = meta_info.type_links[lvalue.name]
        assert isinstance(struct, c_ast.Struct)

        # print ("@@", struct_def)
        EmitIR([lvalue, lvalue.name], meta_info, node_value, id_gen)

        offset = GetStructOffset(struct, lvalue.field, meta_info)
        if offset == 0:
            tmp = node_value[lvalue.name]
        else:
            kind = TYPE_TRANSLATION[POINTER]
            tmp = GetTmp(kind)
            print(
                f"{TAB}lea {tmp}:{StringifyType(kind)} = {node_value[lvalue.name]} {offset}")
        node_value[lvalue] = tmp
    elif isinstance(lvalue, c_ast.ID):
        type = meta_info.type_links[lvalue]
        assert isinstance(
            type, (c_ast.PtrDecl, c_ast.Struct, c_ast.Union)), type
        if isinstance(type, (c_ast.Struct, c_ast.Union, c_ast.FuncDecl)):
            kind = TYPE_TRANSLATION[POINTER]
            tmp = GetTmp(kind)
            # TODO: this needs to select the right lea/lea.mem/lea.stk
            print(f"{TAB}lea {tmp}:{kind} = {lvalue.name}")
            node_value[lvalue] = tmp
        else:
            assert isinstance(type, c_ast.PtrDecl), type
            node_value[lvalue] = lvalue.name
    else:
        assert False, lvalue


def RenderList(items):
    return "[" + " ".join(items) + "]"


def EmitFunctionHeader(fun_name: str, fun_decl: c_ast.FuncDecl, kind):
    return_type = StringifyType(fun_decl.type)
    params = fun_decl.args.params if fun_decl.args else []
    ins = []
    for p in params:
        ins += [StringifyType(p)]
    outs = [return_type] if return_type else []

    print(f"\n\n.fun {fun_name} {kind} {RenderList(outs)} = {RenderList(ins)}")


def HandleAssignment(node: c_ast.Assignment, meta_info: meta.MetaInfo, node_value, id_gen):
    assert node.op == "=", node
    lvalue = node.lvalue
    EmitIR([node, node.rvalue], meta_info, node_value, id_gen)
    tmp = node_value[node.rvalue]
    if isinstance(lvalue, c_ast.ID):
        # because of the canonicalization step only register promotable scalars will
        # naked like this
        symbol = meta_info.sym_links[lvalue]
        print(f"{TAB}mov {lvalue.name} = {tmp}")
        node_value[node] = tmp
        return

    GetLValueAddress(lvalue, meta_info, node_value, id_gen)
    if isinstance(tmp, _NUMBER_TYPES):
        kind = meta_info.type_links[node.rvalue]
        tmp2 = GetTmp(kind)
        print(f"{TAB}mov {tmp2}:{StringifyType(kind)} = {tmp}")
        tmp = tmp2
    print(f"{TAB}st {node_value[lvalue]} 0 = {tmp}")
    node_value[node] = tmp


def extract_bytes(val: int, num_bytes: int) -> List[str]:
    mask = (1 << (num_bytes * 8)) - 1
    val = val & mask
    out = []
    for _ in range(num_bytes):
        out.append(val & 0xff)
        val >>= 8
    return out


def byte_encode_values(scalar: str, values):
    if scalar in {"S8", "U8"}:
        return values
    elif scalar in {"S16", "U16"}:
        out = []
        for x in values:
            i = int(x) & 0xffff
            out += [i & 0xff, (i >> 8) & 0xff]
        return [str(x) for x in out]
    elif scalar in {"S32", "U32"}:
        out = []
        for x in values:
            i = int(x) & 0xffffffff
            out += [i & 0xff, (i >> 8) & 0xff, (i >> 16) & 0xff, (i >> 24) & 0xff]
        return [str(x) for x in out]
    elif scalar in {"S64", "U64"}:
        out = []
        for x in values:
            i = int(x) & 0xffffffff
            out += [i & 0xff, (i >> 8) & 0xff, (i >> 16) & 0xff, (i >> 24) & 0xff]
        return [str(x) for x in out]
    else:
        assert False, f"unsupported initializer {scalar}: {values}"



# hack - just good enough to handle nanojpeg.c
def EmitInitData(init: c_ast.InitList, type_decl):
    assert isinstance(init, c_ast.InitList)
    values = []
    for v in init.exprs:
        assert isinstance(v, c_ast.Constant)
        assert v.type == "int"
        values.append(str(ExtractNumber(v.value)))
    assert isinstance(type_decl, c_ast.ArrayDecl), f"unexpected initializer {type_decl}"
    scalar = ScalarDeclType(type_decl.type)
    dim = ExtractNumber(type_decl.dim.value)
    assert dim == len(values)
    print(f'.data 1 [{" ".join(byte_encode_values(scalar, values))}]')


def IsGlobalDecl(node, parent):
    return isinstance(parent, c_ast.FileAST)


def HandleDecl(node_stack, meta_info: meta.MetaInfo, node_value, id_gen):
    decl: c_ast.Decl = node_stack[-1]
    parent = node_stack[-2]
    name = decl.name

    if IsGlobalDecl(decl, parent):
        size, align = SizeOfAndAlignment(decl, meta_info)
        assert name is not None
        print(f"\n.mem {name} {align} RW")
        if decl.init:
            EmitInitData(decl.init, decl.type)

        else:
            print(f".data {size} [0]")

    elif IsLocalDecl(decl, parent):
        # we also need to take into account if the address is taken later
        scalar = ScalarDeclType(decl.type)
        if scalar:
            print(f"{TAB}.reg {scalar} [{name}]")

            if decl.init:
                EmitIR(node_stack + [decl.init], meta_info, node_value, id_gen)
                print(f"{TAB}mov {name} = {node_value[decl.init]}")

        else:
            size, alignment = SizeOfAndAlignment(decl, meta_info)
            print(f".stk {name} {alignment} {size}")
            if decl.init:
                assert False, "stack with initialized data"
                # print("INIT-STACK", decl.init)

    else:
        assert False, decl


def HandleStructRef(node: c_ast.StructRef, parent, meta_info, node_value, id_gen):
    assert node.type == "."
    EmitIR([parent, node, node.name], meta_info, node_value, id_gen)
    kind = TYPE_TRANSLATION[POINTER]
    tmp = GetTmp(kind)
    struct = meta_info.type_links[node.name]
    assert isinstance(struct, c_ast.Struct)
    offset = GetStructOffset(struct, node.field, meta_info)
    print(f"{TAB}lea {tmp}:{kind} = {node_value[node.name]} {offset}")
    if isinstance(parent, c_ast.StructRef):
        node_value[node] = tmp
    elif isinstance(parent, c_ast.UnaryOp) and parent.op == "&":
        node_value[node] = tmp
    elif isinstance(meta_info.type_links[node.field], c_ast.ArrayDecl):
        node_value[node] = tmp
    else:
        # print ("@@@@@", meta_info.type_links[node.field])
        field_type = meta_info.type_links[node.field]
        val_type = ScalarDeclType(field_type)
        val = GetTmp(val_type)
        print(f"{TAB}ld {val}:{val_type} = {tmp} 0")
        node_value[node] = val


def HandleFuncCall(node: c_ast.FuncCall, meta_info, node_value):
    # print ("ARGS", node.args)
    if HasNoResult(meta_info.type_links[node]):
        results = []
        node_value[node] = None
    else:
        kind = meta_info.type_links[node]
        tmp = GetTmp(kind)
        results = [f"{tmp}:{StringifyType(kind)}"]
        node_value[node] = tmp
    params = []
    if node.args:
        for a in node.args:
            p = node_value[a]
            kind = meta_info.type_links[a]
            if isinstance(p, _NUMBER_TYPES):
                tmp = GetTmp(kind)
                if isinstance(kind, c_ast.PtrDecl):
                    assert p == 0
                    print(
                        f"{TAB}lea {tmp}:{StringifyType(kind)} = 0:{StringifyType(kind)}")

                else:
                    print(f"{TAB}mov {tmp}:{StringifyType(kind)} = {p}")
                p = tmp
            params.append(p)
        for p in reversed(params):
            print(f"{TAB}pusharg {p}")
    print(f"{TAB}bsr {node_value[node.name]}")
    for p in results:
        print(f"{TAB}poparg {p}")


def HandleSwitch(node: c_ast.Switch, meta_info, node_value, id_gen):
    EmitIR([node, node.cond], meta_info, node_value, id_gen)
    label = "switch_%d_" % GetUnique()
    label_tab = label + "tab"
    label_end = label + "end"
    label_default = label + "default"
    cases = []
    default = None
    max_val = 0
    for s in node.stmt:
        if isinstance(s, c_ast.Case):
            val = ExtractNumber(s.expr.value)
            assert val >= 0, f"switch over signed data not implemented"
            if max_val < val:
                max_val = val
            block = label + str(val).replace("-", "minus")
            cases.append((val, s.stmts, block))
        else:
            assert isinstance(s, c_ast.Default), s
            cases.append((None, s.stmts, label_default))
            default = s

    lst = [f"{a} {c}" for a, b, c in cases if a is not None]
    dl = label_default if default else label_end
    switch_value = node_value[node.cond]
    kind = meta_info.type_links[node.cond]
    print(f"{TAB}blt {max_val}:{StringifyType(kind)} {switch_value} {dl}")
    print(f"{TAB}.jtb {label_tab}  {max_val + 1} {dl} [{' '.join(lst)}]")
    print(f"{TAB}switch {switch_value} {label_tab}")
    for a, b, c in cases:
        print(f".bbl {c}")
        for s in b:
            if isinstance(s, c_ast.Break):
                print(f"{TAB}bra {label_end}")
            else:
                EmitIR([node, node.stmt, s], meta_info, node_value, id_gen)
    print(f"\n.bbl {label_end}")


MAP_COMPARE = {
    "!=": "bne",
    "==": "beq",
    "<": "blt",
    "<=": "ble",
}


def EmitConditionalBranch(op: str, target: str, left_type, left, right_type, right):
    if op == ">" or op == ">=":
        op = "<" if op == ">" else "<="
        left_type, left, right_type, right = right_type, right, left_type, left

    kind = ""
    if isinstance(left, _NUMBER_TYPES):
        kind = f":{StringifyType(left_type)}"
    print(f"{TAB}{MAP_COMPARE[op]} {left}{kind} {right} {target}")


def IsScalarType(type):
    if isinstance(type, c_ast.TypeDecl):
        return IsScalarType(type.type)

    return isinstance(type, c_ast.IdentifierType)


def EmitID(parent, node: c_ast.ID, meta_info: meta.MetaInfo, node_value):
    if isinstance(parent, c_ast.StructRef):
        assert parent.field != node
    type_info = meta_info.type_links[node]
    if isinstance(type_info, c_ast.IdentifierType):
        node_value[node] = node.name
        return
    elif isinstance(type_info, c_ast.Struct):
        if parent.field == node:
            node_value[node] = node.name
            return
    elif isinstance(type_info, c_ast.FuncDecl):
        node_value[node] = node.name
        return
    elif not isinstance(type_info, c_ast.ArrayDecl):
        node_value[node] = node.name
        return
    elif isinstance(type_info, c_ast.ArrayDecl):
        if type_info.dim is None:
            node_value[node] = node.name
            return

    kind = TYPE_TRANSLATION[POINTER]
    tmp = GetTmp(kind)
    # TODO: this needs to select the right lea/lea.mem/lea.stk
    print(f"{TAB}lea {tmp}:{kind} = {node.name}")
    node_value[node] = tmp


BIN_OP_MAP = {
    "*": "mul",
    "+": "add",
    "-": "sub",
    "/": "div",
    "%": "rem",
    "<<": "shl",
    ">>": "shr",
    "^": "xor",
    "|": "or",
    "&": "and",
}


def HandleBinop(node: c_ast.BinaryOp, meta_info: meta.MetaInfo, node_value,
                _id_gen: common.UniqueId):
    node_kind = meta_info.type_links[node]
    assert node.op in BIN_OP_MAP, f"unexpected binop {node}"
    left = node_value[node.left]
    right = node_value[node.right]

    if (node.op == "-" and
            isinstance(meta_info.type_links[node.left], (c_ast.PtrDecl, c_ast.ArrayDecl)) and
            isinstance(meta_info.type_links[node.right], (c_ast.PtrDecl, c_ast.ArrayDecl))):
        assert False, f"pointer substracting not yet supported {node}"

    op = BIN_OP_MAP[node.op]
    if isinstance(node_kind, (c_ast.PtrDecl, c_ast.ArrayDecl)):
        # need to scale
        op = "lea"
        element_size, _ = SizeOfAndAlignment(node_kind.type, meta_info)
        if node.op == "-":
            element_size *= -1
        else:
            assert node.op == "+"
        if element_size == 1 and node.op == "+":
            pass
        elif isinstance(right, _NUMBER_TYPES):
            right = str(right * element_size)
        else:
            right_kind = meta_info.type_links[node.right]
            tmp = GetTmp(right_kind)
            print(
                f"{TAB}mul {tmp}:{StringifyType(right_kind)} = {right} {element_size}")
            right = tmp
    tmp = GetTmp(node_kind)
    left_kind = ""
    if isinstance(left, _NUMBER_TYPES):
        left_kind = f":{StringifyType(node_kind)}"

    print(f"{TAB}{op} {tmp}:{StringifyType(node_kind)} = {left}{left_kind} {right}")
    node_value[node] = tmp


def EmitIR(node_stack, meta_info: meta.MetaInfo, node_value, id_gen: common.UniqueId):
    node = node_stack[-1]
    if isinstance(node, c_ast.FuncDef):
        RestTmpCounter()
        fun_decl = node.decl.type
        EmitFunctionHeader(node.decl.name, fun_decl, "NORMAL")
        return_type = StringifyType(fun_decl.type)
        if return_type:
            print(f".reg {return_type} [%out]")
        params = fun_decl.args.params if fun_decl.args else []
        # for p in params:
        #    print(f".reg {StringifyType(p)} [{p.name}]")
        print(f"\n.bbl %start")
        for p in params:
            print(f"{TAB}poparg {p.name}:{StringifyType(p)}")
        EmitIR(node_stack + [node.body], meta_info, node_value, id_gen)
        return
    elif isinstance(node, c_ast.Decl) and isinstance(node.type, c_ast.FuncDecl):
        # EmitFunctionHeader(node.name, node.type)
        return
    elif isinstance(node, c_ast.Decl):
        if node.name is not None:
            HandleDecl(node_stack, meta_info, node_value, id_gen)
        return
    elif isinstance(node, c_ast.If):
        cond = node.cond
        if isinstance(cond, c_ast.BinaryOp) and cond.op in common.COMPARISON_INVERSE_MAP:
            EmitIR(node_stack + [cond.left], meta_info, node_value, id_gen)
            EmitIR(node_stack + [cond.right], meta_info, node_value, id_gen)
            EmitConditionalBranch(cond.op, node.iftrue.name,
                                  meta_info.type_links[cond.left],
                                  node_value[cond.left],
                                  meta_info.type_links[cond.right],
                                  node_value[cond.right])
            print(f"{TAB}bra {node.iffalse.name}")
        else:
            EmitIR(node_stack + [cond], meta_info, node_value, id_gen)
            print(
                f"{TAB}brcond {node_value[cond]} {node.iftrue.name} {node.iffalse.name}")
            assert False
        return
    elif isinstance(node, c_ast.Label):
        print(f"\n.bbl {node.name}")
        EmitIR(node_stack + [node.stmt], meta_info, node_value, id_gen)
        return
    elif isinstance(node, c_ast.Assignment):
        HandleAssignment(node, meta_info, node_value, id_gen)
        return
    elif isinstance(node, c_ast.Struct):
        return
    elif isinstance(node, c_ast.UnaryOp) and node.op == "&":
        GetLValueAddress(node.expr, meta_info, node_value, id_gen)
        node_value[node] = node_value[node.expr]
        return
    elif isinstance(node, c_ast.Switch):
        HandleSwitch(node, meta_info, node_value, id_gen)
        return
    elif isinstance(node, c_ast.StructRef):
        HandleStructRef(node, node_stack[-2], meta_info, node_value, id_gen)
        return

    for c in node:
        node_stack.append(c)
        EmitIR(node_stack, meta_info, node_value, id_gen)
        node_stack.pop(-1)

    if isinstance(node, c_ast.ID):
        EmitID(node_stack[-2], node, meta_info, node_value)
    elif isinstance(node, c_ast.Constant):
        if meta_info.type_links[node] is meta.STRING_IDENTIFIER_TYPE:
            name = id_gen.next("string_const")
            print(f".mem {name} 4 RO")
            print(".data", "1", node.value[:-1] + '\\x00"')
            kind = TYPE_TRANSLATION[POINTER]
            tmp = GetTmp(kind)
            print(f"{TAB}lea.mem {tmp}:{kind} = {name} 0")
            node_value[node] = tmp
            node_value[node] = tmp
        else:
            node_value[node] = ExtractNumber(node.value)
    elif isinstance(node, c_ast.IdentifierType):
        pass
    elif isinstance(node, c_ast.Goto):
        print(f"{TAB}bra {node.name}")
    elif isinstance(node, c_ast.BinaryOp):
        HandleBinop(node, meta_info, node_value, id_gen)
    elif isinstance(node, c_ast.UnaryOp):
        assert node.op != "&"  # this is handled further up
        # TODO: force this to be size_t
        if node.op == "sizeof":
            expr = node.expr
            expr = meta_info.type_links.get(expr, expr)
            tmp, _ = SizeOfAndAlignment(expr, meta_info)
        elif node.op == "*":
            if isinstance(node_stack[-2], c_ast.StructRef):
                tmp = node_value[node.expr]
            else:
                kind = meta_info.type_links[node]
                tmp = GetTmp(kind)
                print(
                    f"{TAB}ld {tmp}:{StringifyType(kind)} = {node_value[node.expr]} 0")
                node_value[node] = tmp
        elif node.op == "~":
            kind = meta_info.type_links[node]
            tmp = GetTmp(kind)
            x = ALL_BITS_SET[StringifyType(kind)]
            print(
                f"{TAB}xor {tmp}:{StringifyType(kind)} = {node_value[node.expr]} {x}")
            node_value[node] = tmp
        elif node.op == "-":
            kind = meta_info.type_links[node]
            tmp = GetTmp(kind)
            print(
                f"{TAB}sub {tmp}:{StringifyType(kind)} = 0  {node_value[node.expr]}")
            node_value[node] = tmp
        else:
            assert False, f"post inc/dec not yet supported:\n{node}"
            # tmp = GetTmp(meta_info.type_links[node])
            # print(TAB, tmp, "=", node.op, node_value[node.expr])
        node_value[node] = tmp
    elif isinstance(node, c_ast.Cast):
        dst_kind = StringifyType(meta_info.type_links[node])
        src_kind = StringifyType(meta_info.type_links[node.expr])
        if src_kind == dst_kind:
            node_value[node] = node_value[node.expr]
            return

        if isinstance(node_value[node.expr], _NUMBER_TYPES):
            if node_value[node.expr] >= 0:
                # non-negative numbers, especially zero are compatible with most things
                node_value[node] = node_value[node.expr]
            else:
                tmp = GetTmp(meta_info.type_links[node.expr])
                print(f"{TAB}mov {tmp}:{src_kind} = {node_value[node.expr]}")
                # needs more work especially for narrowing
                tmp2 = GetTmp(meta_info.type_links[node])
                assert dst_kind is not None
                print(f"{TAB}conv {tmp2}:{dst_kind} = {tmp}")
                node_value[node] = tmp2
        else:
            tmp = GetTmp(meta_info.type_links[node])
            assert dst_kind is not None

            print(f"{TAB}conv {tmp}:{dst_kind} = {node_value[node.expr]}")
            node_value[node] = tmp
    elif isinstance(node, c_ast.FuncCall):
        HandleFuncCall(node, meta_info, node_value)
    elif isinstance(node, c_ast.Return):
        if node.expr:
            print(f"{TAB}mov %out = {node_value[node.expr]}")
            print(f"{TAB}pusharg %out")
        print(f"{TAB}ret")
    elif isinstance(node, c_ast.EmptyStatement):
        pass
    elif isinstance(node, c_ast.ExprList):
        node_value[node] = node_value[node.exprs[-1]]
    elif isinstance(node, (
            c_ast.TypeDecl, c_ast.PtrDecl, c_ast.ArrayDecl, c_ast.FuncDecl, c_ast.Typename)):
        pass
    elif isinstance(node, (
            c_ast.EllipsisParam, c_ast.ParamList, c_ast.Compound, c_ast.FuncDef, c_ast.FileAST)):
        pass
    else:
        assert False, node


def main(argv):
    parser = argparse.ArgumentParser(description='translate')
    parser.add_argument('--mode', type=int,
                        default=0,
                        help='mode 32 or 64 bit')
    parser.add_argument('--cpp_args', type=str, default=[], action='append',
                        help='args passed through to the pycparser')
    parser.add_argument('filename', type=str,
                        help='c-files to translate')
    args = parser.parse_args()

    if args.mode not in {32, 64}:
        print("no valid mode specified. Use --mode=32 or --mode-64")
        exit(1)
    global TYPE_TRANSLATION
    TYPE_TRANSLATION = TYPE_TRANSLATION_32 if args.mode == 32 else TYPE_TRANSLATION_64
    print("#" * 60)
    print("#", args.filename)
    print("#" * 60)
    ast = parse_file(args.filename, use_cpp=True, cpp_args=args.cpp_args)
    canonicalize.SimpleCanonicalize(ast, use_specialized_printf=True)
    meta_info = meta.MetaInfo(ast)
    canonicalize.Canonicalize(ast, meta_info, skip_constant_casts=False)
    global_id_gen = common.UniqueId()
    EmitIR([ast], meta_info, {}, global_id_gen)


if __name__ == "__main__":
    # logging.basicConfig(level=logging.DEBUG)
    main(sys.argv[1:])
