#!/bin/env python3
"""SEXPR Pretty printer (PP) for Cwerg AST to sexpr syntax

"""

import logging

from typing import Optional

from FE import cwast


logger = logging.getLogger(__name__)


def MaybeSimplifyLeafNode(node) -> Optional[str]:
    if isinstance(node, cwast.TypeBase):
        return cwast.BaseTypeKindToKeyword(node.base_type_kind)
    elif isinstance(node, cwast.ValUndef):
        return "undef"
    elif isinstance(node, cwast.TypeAuto):
        return "auto"
    elif isinstance(node, cwast.Id):
        return node.FullName()
    elif isinstance(node, cwast.MacroId):
        return str(node.name)
    elif isinstance(node, cwast.ValTrue):
        return "true"
    elif isinstance(node, cwast.ValFalse):
        return "false"
    elif isinstance(node, cwast.ValNum):
        return node.number
    elif isinstance(node, cwast.ValVoid):
        return "void_val"
    elif isinstance(node, cwast.ValString):
        k = node.str_kind
        quotes = '"""' if k in (cwast.STR_KIND.HEX_TRIPLE,
                                cwast.STR_KIND.RAW_TRIPLE,
                                cwast.STR_KIND.NORMAL_TRIPLE) else '"'
        prefix = ""
        if k in (cwast.STR_KIND.RAW_TRIPLE, cwast.STR_KIND.RAW):
            prefix = "r"
        elif  k in (cwast.STR_KIND.HEX_TRIPLE, cwast.STR_KIND.HEX):
            prefix = "x"
        return prefix + quotes + node.string + quotes
    else:
        return None


def GetNodeTypeAndFields(node, condense=True):
    cls = node.__class__
    fields = cls.FIELDS[:]
    if not condense:
        return cls.__name__, fields

    if isinstance(node, cwast.StmtCompoundAssignment):
        fields.pop(0)
        return cwast.ASSIGNMENT_SHORTCUT_INV[node.assignment_kind], fields
    elif isinstance(node, cwast.Expr1):
        fields.pop(0)
        return cwast.UNARY_EXPR_SHORTCUT_SEXPR_INV[node.unary_expr_kind], fields
    elif isinstance(node, cwast.Expr2):
        fields.pop(0)
        return cwast.BINARY_EXPR_SHORTCUT_INV[node.binary_expr_kind], fields
    elif isinstance(node, cwast.ExprPointer):
        fields.pop(0)
        return cwast.POINTER_EXPR_SHORTCUT_INV[node.pointer_expr_kind], fields
    elif cls.ALIAS:
        return cls.ALIAS, fields
    else:
        return cls.__name__, fields


STMT_LIST_INDENT = 4
EXPR_LIST_INDENT = 8


def GetColonIndent(field: str) -> int:
    return 0 if field == "body_mod" else STMT_LIST_INDENT

############################################################
# Pretty Print
############################################################


def GetExprIndent(_) -> int:
    return EXPR_LIST_INDENT


def GetDoc(node):
    for nfd in node.ATTRS:
        if nfd.name == "doc":
            val = getattr(node, "doc")
            return val
    return None


def _RenderColonList(val: list, field: str, out, indent: int):

    extra_indent = GetColonIndent(field)
    line = out[-1]
    if field == "body_f":
        out.append([" " * (indent + extra_indent - 3) + ":"])
        for cc in val:
            out.append([" " * (indent + extra_indent)])
            _RenderRecursivelyToIR(
                cc, out, indent + extra_indent)
    else:
        line.append(":")
        for cc in val:
            out.append([" " * (indent + extra_indent)])
            _RenderRecursivelyToIR(cc, out, indent + extra_indent)
            # extra line between top level nodes
            if field == "body_mod":
                out.append([" " * indent])


def _GuessNodeSize(v) -> int:
    if isinstance(v, (cwast.ValAuto, cwast.ValFalse, cwast.ValTrue, cwast.ValNum)):
        return 1
    elif isinstance(v, cwast.ValString):
        if v.triplequoted:
            return 100
        return len(v.string) // 8
    elif isinstance(v, (cwast.FunParam, cwast.MacroParam, cwast.ValCompound)):
        return 3
    elif isinstance(v, cwast.ValPoint):
        return _GuessNodeSize(v.value_or_undef)
    else:
        return 2


def _ListIsCompact(val: list):
    points = 0
    for v in val:
        if GetDoc(v):
            return False
        points += _GuessNodeSize(v)

    if points > 6:
        return False
    # for x in val:
    #    if isinstance(x, cwast.Comment):
    #        return False
    return True


def _RenderList(val: list, field: str, out, indent: int):
    extra_indent = GetExprIndent(field)
    line = out[-1]
    if not val:
        line.append("[]")
    elif len(val) > 12:
        line.append("[")
        force_new_line = True
        sep = ""
        for cc in val:
            line = out[-1]
            if force_new_line or sum(len(x) for x in line) > 80:
                out.append([" " * (indent + extra_indent)])
                line = out[-1]
                sep = ""
                force_new_line = False
            line.append(sep)
            sep = " "
            _RenderRecursivelyToIR(cc, out, indent + extra_indent)
            if line != out[-1]:
                force_new_line = True
        out[-1].append("]")
    elif _ListIsCompact(val):
        line.append("[")
        sep = ""
        for cc in val:
            line = out[-1]
            line.append(sep)
            sep = " "
            _RenderRecursivelyToIR(cc, out, indent + extra_indent)
        out[-1].append("]")

    else:
        line.append("[")
        for cc in val:
            out.append([" " * (indent + extra_indent)])
            _RenderRecursivelyToIR(cc, out, indent + extra_indent)
        out[-1].append("]")


def _RenderMacroInvoke(node: cwast.MacroInvoke, out, indent: int):
    line = out[-1]
    line.append(f"({node.name}")
    for a in node.args:
        line = out[-1]
        if isinstance(a, cwast.EphemeralList):
            line.append(" ")
            if a.colon:
                _RenderColonList(a.args, "dummy", out, indent)
            else:
                _RenderList(a.args, "dummy", out, indent)
        else:
            line.append(" ")
            _RenderRecursivelyToIR(a, out, indent)
    line = out[-1]
    line.append(")")


_ATTR_MODE = {
    "doc": "skip",  # handled elsewhere
    "mut": "skip",
    "ref": "after",
    "pub": "before",
    "init": "before",
    "fini": "before",
    "extern": "before",
    "popl": "before",
    "builtin": "before",
    "cdecl": "before",
    "polymorphic": "after",
    "arg_ref": "after",
    "res_ref": "after",
    "unchecked": "after",
    "wrapped": "after",
    "untagged": "after",
    "poly": "before",
    "preserve_mut": "before",
}


def _RenderAttr(node, out, indent, before_paren: bool):
    if before_paren:
        doc = GetDoc(node)
        if doc:
            out[-1].append("@doc ")
            out[-1].append(doc)
            out.append([" " * indent])

    for nfd in node.ATTRS:
        mode = _ATTR_MODE[nfd.name]

        if mode == "skip":
            continue
        elif mode == "before":
            if not before_paren:
                continue
        elif mode == "after":
            if before_paren:
                continue
        else:
            assert False

        val = getattr(node, nfd.name)
        if not val:
            continue
        if isinstance(val, bool):
            out[-1].append(f"@{nfd.name} ")
        else:
            assert False, f"in node {
                node} unknown attribute [{field}]: [{val}]"
            out.append(f"@{field} {val} ")


def _RenderRecursivelyToIR(node, out, indent: int):
    if cwast.NF.TOP_LEVEL in node.FLAGS:
        out.append([""])
    abbrev = MaybeSimplifyLeafNode(node)
    if abbrev:
        out[-1].append(abbrev)
        return

    _RenderAttr(node, out, indent, before_paren=True)

    if isinstance(node, cwast.MacroInvoke):
        _RenderMacroInvoke(node, out, indent)
        return

    if isinstance(node, cwast.ValPoint) and isinstance(node.point, cwast.ValAuto) and not node.doc:
        _RenderRecursivelyToIR(node.value_or_undef, out, indent)
        return

    node_name, fields = GetNodeTypeAndFields(node)
    if isinstance(node, (cwast.DefGlobal, cwast.DefVar, cwast.DefGlobal,
                         cwast.TypePtr, cwast.TypeSpan, cwast.ExprAddrOf,
                         cwast.ExprFront)):
        if node.mut:
            node_name += "!"

    out[-1].append("(")
    spacer = ""
    _RenderAttr(node, out, indent, before_paren=False)
    out[-1].append(node_name)
    spacer = " "

    for nfd in fields:
        field_kind = nfd.kind
        field = nfd.name
        line = out[-1]
        val = getattr(node, nfd.name)

        if cwast.IsFieldWithDefaultValue(field, val):
            continue

        if field_kind is not cwast.NFK.LIST or field != "body_f":
            line.append(spacer)
        spacer = " "
        # spacer = str(field_kind.value)

        if field_kind is cwast.NFK.STR:
            line.append(str(val))
        elif field_kind is cwast.NFK.NAME:
            line.append(str(val))
        elif field_kind is cwast.NFK.KIND:
            line.append(val.name)
        elif field_kind is cwast.NFK.NODE:
            _RenderRecursivelyToIR(val, out, indent)
        elif field_kind is cwast.NFK.LIST:
            if field in ("items", "fields", "body_mod", "body", "body_t", "body_f", "body_for",
                         "cases", "body_macro"):
                _RenderColonList(val, field, out, indent)
            else:
                _RenderList(val, field, out, indent)
        elif field_kind is cwast.NFK.NAME_LIST:
            val = [v.name for v in val]
            line.append(f"[{' '.join(val)}]")
        else:
            assert False, f"unexpected field {field}"

    line = out[-1]
    line.append(")")

    if isinstance(node, cwast.DefMod):
        out.append([""])


def PrettyPrint(mod: cwast.DefMod, outp):
    out = [[""]]
    _RenderRecursivelyToIR(mod, out, 0)
    for a in out:
        print("".join(a), file=outp)


############################################################
#
############################################################
if __name__ == "__main__":
    import argparse

    from FE import parse_sexpr

    def main():
        parser = argparse.ArgumentParser(description='pretty_printer')
        parser.add_argument("-inplace",
                            action="store_true", help='update files in place')
        parser.add_argument('files', metavar='F', type=str, nargs='+',
                            help='an input source file')
        args = parser.parse_args()

        logging.basicConfig(level=logging.WARN)
        logger.setLevel(logging.INFO)
        for fn in args.files:
            assert fn.endswith(".cws")
            fp = open(fn, encoding="utf8")
            mod = parse_sexpr.ReadModFromStream(fp, fn)
            fp.close()
            out = [[""]]
            _RenderRecursivelyToIR(mod, out, 0)
            if args.inplace:
                fp = open(fn, "w", encoding="utf8")
                for a in out:
                    for b in a:
                        fp.write(b)
                    fp.write("\n")
                fp.close()
            else:
                for a in out:
                    print("".join(a))
    main()
