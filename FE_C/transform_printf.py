#!/usr/bin/python3

import re
from typing import Optional, List

from pycparser import c_ast

import common
import meta

__all__ = ["TokenizeFormatString", "FormatOptions", "PrintfSplitterTransform"]

PRINTF_OPTION = re.compile(r"%([-+ 0]*)([0-9]*)([.][0-9]+)?([lqh]+)?([cduoxefgsp])")

LENGTH_TRANSLATION = {
    None: "",
    "l": "l",
    "ll": "q",
    "q": "q",
    "h": "h",
}


def MakeSimpleTypeDecl(name, type_names):
    return c_ast.TypeDecl(name, [], common.GetCanonicalIdentifierType(type_names))


def MakePrintfStyleDecl(name: str, type_names: List[str], is_pointer=False):
    parameter_fd = c_ast.Decl("fd", [], [], [],
                              MakeSimpleTypeDecl("fd", ["int"]), None, None)

    parameter_value = c_ast.Decl("value", [], [], [],
                                 MakeSimpleTypeDecl("value", type_names), None, None)
    if is_pointer:
        parameter_value.type = c_ast.PtrDecl([], parameter_value.type)

    fun_result = MakeSimpleTypeDecl(name, ["int"])
    return c_ast.Decl(
        name, [], [], [], c_ast.FuncDecl(
            c_ast.ParamList([parameter_fd, parameter_value]),
            fun_result), None, None)


PRINTF_PROTOTYPES = {
    "write_u": MakePrintfStyleDecl("write_u", ["int", "unsigned"]),
    "write_d": MakePrintfStyleDecl("write_d", ["int"]),
    "write_x": MakePrintfStyleDecl("write_x", ["int", "unsigned"]),
    "write_c": MakePrintfStyleDecl("write_c", ["char"]),
    "write_s": MakePrintfStyleDecl("write_s", ["char"], True)
}

_PRINTF_DISPATCH = {
    "c": "write_c",
    "s": "write_s",
    "d": "write_d",
    #
    "u": "write_u",
    "x": "write_x",
}


def GetSingleArgPrintForFormat(fmt):
    key = fmt[-2:]
    if key[0] != "l":
        key = key[-1]
    name = _PRINTF_DISPATCH.get(key)
    assert name is not None, f"format string [{fmt}] is not yet supported"
    return name


# Not used yet
class FormatOptions:

    def __init__(self, s: str) -> None:
        m = PRINTF_OPTION.match(s)
        assert m
        flags, width, precision, length, kind = m.groups()
        self.kind = kind
        self.length = LENGTH_TRANSLATION.get(length, "")
        self.precision = int(precision[1:]) if precision else -1
        self.width = int(width) if width else -1
        self.show_sign = "+" in flags
        self.adjust_left = "-" in flags
        self.pad_with_zero = "0" in flags
        self.space_for_plus = " " in flags

    def __str__(self):
        f = []
        if self.show_sign: f.append("+")
        if self.adjust_left: f.append("-")
        if self.pad_with_zero: f.append("0")
        if self.space_for_plus: f.append(" ")
        return "[FormatOptions (%s) %d %d %s %s]" % ("".join(f), self.width, self.precision, self.length, self.kind)


def TokenizeFormatString(s: str):
    """
    this breaks up a (well-formed) printf format string into a list of strings.

    Each string falls into three categories
    1. starts with "%" end ends with "[cduoxefgsp]" and contains no "%" in between
    2. consists of exactly "%" (was "%%" in the original string)
    3. does not contain any "%"
    """
    out = []
    last = 0

    def add_plain(start, end):
        if start != end:
            plain = s[start: end]
            out.append(plain if plain != "%%" else "%")

    # loop over all category 1 sub strings
    for m in PRINTF_OPTION.finditer(s):
        start, end = m.span()
        add_plain(last, start)
        last = end
        out.append(m.group(0))
    add_plain(last, len(s))
    return out


# ================================================================================
# This transformation splits printf calls with constant format string into several printf
# calls. Each of which has at most one argument besides the format string
# This eliminates the primary use case of variable argument lists.
#
# if `use_specialized_printf` is true the printfs will also be renamed based on
# PRINTF_DISPATCH and the printf prototype will be replaced by PRINTF_PROTOTYPES.
# printf with only a single argument after splitting will renamed into `puts`
#
# This invalidates sym_tab and type_tab
# ================================================================================
def _IsSuitablePrintf(node: c_ast.Node, _):
    if not isinstance(node, c_ast.FuncCall): return None
    if not isinstance(node.name, c_ast.ID): return None
    if node.name.name != "printf": return None
    assert isinstance(node.args, c_ast.ExprList)
    assert len(node.args.exprs) > 0
    format_arg = node.args.exprs[0]
    if not isinstance(format_arg, c_ast.Constant): return None
    assert format_arg.type == "string"
    return True


CONST_STDOUT = c_ast.Constant("int", "1")


def MakePrintfCall(fmt_str, arg_node: Optional[c_ast.Node], use_specialized_printf):
    if use_specialized_printf:
        if arg_node:
            args = [CONST_STDOUT, arg_node]
            name = GetSingleArgPrintForFormat(fmt_str)
        else:
            args = [CONST_STDOUT, c_ast.Constant("string", '"' + fmt_str + '"')]
            name = "write_s"
    else:
        args = [c_ast.Constant("string", '"' + fmt_str + '"')]
        if arg_node:
            args.append(arg_node)
        name = "printf"
    return c_ast.FuncCall(c_ast.ID(name), c_ast.ExprList(args))


def _DoPrintfSplitter(call: c_ast.FuncCall, parent, use_specialized_printf):
    args: List = call.args.exprs
    fmt_pieces = TokenizeFormatString(args[0].value[1:-1])
    assert len(fmt_pieces) >= 1
    if use_specialized_printf and len(fmt_pieces) == 1:
        s = fmt_pieces[0]
        if len(s) <= 1 or s[0] != "%":
            call.name.name = "write_s"
            args.insert(0, CONST_STDOUT)
            return
        else:
            call.name.name = GetSingleArgPrintForFormat(s)
            args[0] = CONST_STDOUT
            return

    stmts = common.GetStatementList(parent)
    if not stmts:
        stmts = [call]
        common.ReplaceNode(parent, call, c_ast.Compound(stmts))

    calls = []
    args = args[1:]  # skip the format string
    # note this has a small bug: we should evaluate all the
    # args and then print them instead of interleaaving
    # computation and printing.
    for f in fmt_pieces:
        arg = None
        if f[0] == '%' and len(f) > 1:
            arg = args.pop(0)
        c = MakePrintfCall(f, arg, use_specialized_printf)
        calls.append(c)
    pos = stmts.index(call)
    stmts[pos:pos + 1] = calls


def PrintfSplitterTransform(ast: c_ast.FileAST, use_specialized_printf):
    candidates = common.FindMatchingNodesPostOrder(ast, ast, _IsSuitablePrintf)

    for call, parent in candidates:
        _DoPrintfSplitter(call, parent, use_specialized_printf)
    if not use_specialized_printf or len(candidates) == 0:
        return
    # remove old printf prototype (use ellipsis)
    ext = ast.ext
    to_be_deleted = []
    for node in ext:
        if isinstance(node, c_ast.Decl) and node.name == "printf":
            to_be_deleted.append(node)
    for node in to_be_deleted:
        ext.remove(node)
    # prepend protos
    # ext[0:0] = list(PRINTF_PROTOTYPES.values())


if __name__ == "__main__":
    import sys

    for a in sys.argv[1:]:
        print([str(x) for x in TokenizeFormatString(a)])
