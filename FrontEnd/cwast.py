#!/usr/bin/python3

"""AST Nodes and SExpr reader/writer for the Cwerg frontend"""
from __future__ import annotations

import sys
import dataclasses
import logging
import enum

from typing import Optional, Union, Any, TypeAlias, NoReturn, Final

logger = logging.getLogger(__name__)


_ID_PATH_SEPARATOR = "::"


MACRO_SUFFIX = "#"

BUILT_IN_MACROS = set([
    "while",
    "for",
    "trylet",
    "trylet!",
    "tryset",
    "^.",
])


def _GetQualifierIfPresent(name: str) -> Optional[str]:
    tokens = name.split(_ID_PATH_SEPARATOR)
    if len(tokens) == 2:
        return tokens[0]
    assert 1 == len(tokens)
    return None


def GetSymbolName(name: str) -> str:
    return name.split(_ID_PATH_SEPARATOR)[-1]


def IsQualifiedName(name: str) -> bool:
    return _ID_PATH_SEPARATOR in name

############################################################
# Enums
############################################################


@enum.unique
class BASE_TYPE_KIND(enum.Enum):
    """basic scalar types"""
    INVALID = 0

    SINT = 10
    S8 = 11
    S16 = 12
    S32 = 13
    S64 = 14

    UINT = 20
    U8 = 21
    U16 = 22
    U32 = 23
    U64 = 24

    R32 = 30  # real
    R64 = 31  # real

    VOID = 40
    NORET = 41
    BOOL = 42
    TYPEID = 43


def KeywordToBaseTypeKind(s: str) -> BASE_TYPE_KIND:
    ss = s.lower()
    if ss != s:
        return BASE_TYPE_KIND.INVALID
    s = s.upper()
    try:
        return BASE_TYPE_KIND[s]
    except KeyError:
        return BASE_TYPE_KIND.INVALID


def BaseTypeKindToKeyword(kind: BASE_TYPE_KIND) -> str:
    return kind.name.lower()


@enum.unique
class NF(enum.Flag):
    """Node Flags"""
    NONE = 0

    TYPE_ANNOTATED = enum.auto()   # node has a type (x_type)
    VALUE_ANNOTATED = enum.auto()  # node may have a comptime value (x_value)
    FIELD_ANNOTATED = enum.auto()  # node reference a struct field (x_field)
    SYMBOL_ANNOTATED = enum.auto()  # node reference a XXX_SYM_DEF node (x_symbol)
    # possibly uniquified name of module, use during code-gen
    MODNAME_ANNOTATED = enum.auto()

    # Temporary annotations
    # node reference to the imported module (x_module)
    MODULE_ANNOTATED = enum.auto()
    # only used for pretty printing
    ROLE_ANNOTATED = enum.auto()
    # reference to the import node resolving the qualifier  (x_import)
    IMPORT_ANNOTATED = enum.auto()
    SYMTAB = enum.auto()

    # Node families
    MAY_BE_LHS = enum.auto()
    TYPE_CORPUS = enum.auto()
    CONTROL_FLOW = enum.auto()
    GLOBAL_SYM_DEF = enum.auto()
    LOCAL_SYM_DEF = enum.auto()
    TOP_LEVEL = enum.auto()
    MACRO_BODY_ONLY = enum.auto()
    TO_BE_EXPANDED = enum.auto()
    # all non-core nodes will be stripped or converted to core nodes before code-gen
    NON_CORE = enum.auto()


NF_EXPR = NF.VALUE_ANNOTATED | NF.TYPE_ANNOTATED


@enum.unique
class GROUP(enum.IntEnum):
    """Node Family"""
    Misc = enum.auto()
    Type = enum.auto()
    Statement = enum.auto()
    Value = enum.auto()
    Expression = enum.auto()
    Macro = enum.auto()
    Ephemeral = enum.auto()  # should only exist during intermediate steps and in macros


@enum.unique
class BINARY_EXPR_KIND(enum.Enum):
    """same type two operand expressions"""
    INVALID = 0
    ADD = 1
    SUB = 2
    DIV = 3
    MUL = 4
    MOD = 5
    MIN = 6
    MAX = 7

    AND = 10
    OR = 11
    XOR = 12

    EQ = 20
    NE = 21
    LT = 22
    LE = 23
    GT = 24
    GE = 25

    ANDSC = 30  # && (SC = short circuit)
    ORSC = 31   # || (SC = short circuit)

    SHR = 40    # >>
    SHL = 41    # <<

    ROTR = 42    # >>>
    ROTL = 43    # <<<

    PDELTA = 52  # pointer delta result is sint


BINARY_EXPR_SHORTCUT = {
    # Note: order is lexer friendly - longest match first
    #
    "<<": BINARY_EXPR_KIND.SHL,
    ">>": BINARY_EXPR_KIND.SHR,
    "<<<": BINARY_EXPR_KIND.ROTL,
    ">>>": BINARY_EXPR_KIND.ROTR,
    #
    ">=": BINARY_EXPR_KIND.GE,
    ">": BINARY_EXPR_KIND.GT,
    "<=": BINARY_EXPR_KIND.LE,
    "<": BINARY_EXPR_KIND.LT,
    "==": BINARY_EXPR_KIND.EQ,
    "!=": BINARY_EXPR_KIND.NE,
    #
    "+": BINARY_EXPR_KIND.ADD,
    "-": BINARY_EXPR_KIND.SUB,
    "*": BINARY_EXPR_KIND.MUL,
    "/": BINARY_EXPR_KIND.DIV,
    "%": BINARY_EXPR_KIND.MOD,
    #
    "max": BINARY_EXPR_KIND.MAX,
    "min": BINARY_EXPR_KIND.MIN,
    #
    "&&": BINARY_EXPR_KIND.ANDSC,
    "||": BINARY_EXPR_KIND.ORSC,

    #
    "and": BINARY_EXPR_KIND.AND,
    "or": BINARY_EXPR_KIND.OR,
    "xor": BINARY_EXPR_KIND.XOR,
    #
    "&-&": BINARY_EXPR_KIND.PDELTA,
}

BINARY_EXPR_SHORTCUT_INV = {v: k for k, v in BINARY_EXPR_SHORTCUT.items()}


@enum.unique
class POINTER_EXPR_KIND(enum.Enum):
    """pointer and int two operand expressions"""
    INVALID = 0
    INCP = 1   # pointer add int
    DECP = 2   # pointer sub int


POINTER_EXPR_SHORTCUT = {
    #
    "pinc": POINTER_EXPR_KIND.INCP,
    "pdec": POINTER_EXPR_KIND.DECP,
}

POINTER_EXPR_SHORTCUT_INV = {v: k for k, v in POINTER_EXPR_SHORTCUT.items()}


@enum.unique
class ASSIGNMENT_KIND(enum.Enum):
    """Compound Assignment Kinds"""
    INVALID = 0
    ADD = 1
    SUB = 2
    DIV = 3
    MUL = 4
    MOD = 5
    #
    MIN = 6
    MAX = 7
    #
    AND = 10
    OR = 11
    XOR = 12
    #
    SHR = 40    # >>
    SHL = 41    # <<
    ROTR = 42    # >>
    ROTL = 43    # <<


ASSIGNMENT_SHORTCUT = {
    #
    "+=": ASSIGNMENT_KIND.ADD,
    "-=": ASSIGNMENT_KIND.SUB,
    "*=": ASSIGNMENT_KIND.MUL,
    "/=": ASSIGNMENT_KIND.DIV,
    "%=": ASSIGNMENT_KIND.MOD,
    "min=": ASSIGNMENT_KIND.MIN,
    "max=": ASSIGNMENT_KIND.MAX,
    #
    "and=": ASSIGNMENT_KIND.AND,
    "or=": ASSIGNMENT_KIND.OR,
    "xor=": ASSIGNMENT_KIND.XOR,
    #
    "<<=": ASSIGNMENT_KIND.SHL,
    ">>=": ASSIGNMENT_KIND.SHR,
    "<<<=": ASSIGNMENT_KIND.ROTL,
    ">>>=": ASSIGNMENT_KIND.ROTR,
}

ASSIGNMENT_SHORTCUT_INV = {v: k for k, v in ASSIGNMENT_SHORTCUT.items()}

COMPOUND_KIND_TO_EXPR_KIND = {
    ASSIGNMENT_KIND.ADD: BINARY_EXPR_KIND.ADD,
    ASSIGNMENT_KIND.SUB: BINARY_EXPR_KIND.SUB,
    ASSIGNMENT_KIND.DIV: BINARY_EXPR_KIND.DIV,
    ASSIGNMENT_KIND.MUL: BINARY_EXPR_KIND.MUL,
    ASSIGNMENT_KIND.MOD: BINARY_EXPR_KIND.MOD,
    #
    ASSIGNMENT_KIND.AND: BINARY_EXPR_KIND.AND,
    ASSIGNMENT_KIND.OR: BINARY_EXPR_KIND.OR,
    ASSIGNMENT_KIND.XOR: BINARY_EXPR_KIND.XOR,
    #
    ASSIGNMENT_KIND.MAX: BINARY_EXPR_KIND.MAX,
    ASSIGNMENT_KIND.MIN: BINARY_EXPR_KIND.MIN,
    #
    ASSIGNMENT_KIND.SHR: BINARY_EXPR_KIND.SHR,
    ASSIGNMENT_KIND.SHL: BINARY_EXPR_KIND.SHL,
    ASSIGNMENT_KIND.ROTL: BINARY_EXPR_KIND.ROTL,
    ASSIGNMENT_KIND.ROTR: BINARY_EXPR_KIND.ROTR,
}


@enum.unique
class UNARY_EXPR_KIND(enum.Enum):
    """Unary Expression Kind for basic types"""
    INVALID = 0
    NOT = 1
    MINUS = 2
    ABS = 3
    SQRT = 4


UNARY_EXPR_SHORTCUT = {
    "!": UNARY_EXPR_KIND.NOT,
    "~": UNARY_EXPR_KIND.MINUS,
    "abs": UNARY_EXPR_KIND.ABS,
    "sqrt": UNARY_EXPR_KIND.SQRT,
}

UNARY_EXPR_SHORTCUT_INV = {v: k for k, v in UNARY_EXPR_SHORTCUT.items()}

UNARY_EXPR_SHORTCUT_CONCRETE = {
    "!": UNARY_EXPR_KIND.NOT,
    "-": UNARY_EXPR_KIND.MINUS,
}

UNARY_EXPR_SHORTCUT_CONCRETE_INV = {
    v: k for k, v in UNARY_EXPR_SHORTCUT_CONCRETE.items()}


@enum.unique
class MOD_PARAM_KIND(enum.Enum):
    """Module Parameter Kind"""
    INVALID = 0
    CONST_EXPR = 1
    TYPE = 2


@enum.unique
class MACRO_PARAM_KIND(enum.Enum):
    """Macro Parameter Kinds"""
    INVALID = 0
    ID = 1
    STMT_LIST = 2
    EXPR_LIST = 3
    EXPR = 4
    STMT = 5
    FIELD = 6
    TYPE = 7
    EXPR_LIST_REST = 8   # must be last

############################################################
# Field attributes of Nodes
#
# the fields of nodes are subject to a lot of invariants which must be enforced
#
# There are two kinds of fields:
# * regular fields - typically populated directly from source
# * x-fields - typically populated by later analyses
#
# Regular fields follow these rules
#
# All fields belong to one of these categories:
# * FLAG_FIELDS: bools
# * STR_FIELDS: strings
# * INT_FIELDS: ints
# * KIND_FIELDS: enums
# * NODE_FIELD: a single AST Node
# * LIST_FIELDS: zero or more AST Nodes
#
# The order of fields in the Node is:
#
# * fields from FLAG_FIELDS
# * fields from other categories
# If fields are in OPTIONAL_FIELDS they must come last
############################################################


@enum.unique
class NFK(enum.Enum):
    """Node Field Descriptor Kind"""
    INVALID = 0
    STR = enum.auto()
    ATTR_BOOL = enum.auto()  # usually specified via @XXX
    ATTR_STR = enum.auto()  # usually specified via @XXX=YYY
    KIND = enum.auto()  # some enum
    INTERNAL_BOOL = enum.auto()  # like ATTR_BOOL but handled internally
    INTERNAL_STR = enum.auto()  # like an ATTR_STR but handled internally
    NODE = enum.auto()
    LIST = enum.auto()
    STR_LIST = enum.auto()


@dataclasses.dataclass()
class NFD:
    """Node Field Descriptor"""
    kind: NFK
    name: str
    doc: str
    enum_kind: Any = None
    node_type: Any = None
    role: MACRO_PARAM_KIND = MACRO_PARAM_KIND.INVALID


def NfdStr(name, doc):
    return NFD(NFK.STR, name, doc)


def NfdAttrBool(name, doc):
    return NFD(NFK.ATTR_BOOL, name, doc)


def NfdAttrStr(name, doc):
    return NFD(NFK.ATTR_STR, name, doc)


def NfdKind(name, doc, enum_kind):
    return NFD(NFK.KIND, name, doc, enum_kind=enum_kind)


def _ExtractTypes(t):
    """Extract the actual type"""
    if isinstance(t, str):
        return t
    # we cannot test isinstance(t, Union) because Union is a special form
    return tuple([x.__forward_arg__ for x in t.__args__])


def NfdNode(name, doc, node_type, role):
    return NFD(NFK.NODE, name, doc, node_type=_ExtractTypes(node_type), role=role)


def NfdNodeList(name, doc, node_type, role):
    return NFD(NFK.LIST, name, doc, node_type=_ExtractTypes(node_type), role=role)


NODES_INITS_ARRAY_T: TypeAlias = "IndexVal"
NODES_INITS_REC_T: TypeAlias = "FieldVal"
NODES_FIELDS_T: TypeAlias = "RecField"
NODES_CASES_T: TypeAlias = "Case"
NODES_ITEMS_T: TypeAlias = "EnumVal"
NODES_PARAMS_MOD_T: TypeAlias = "ModParam"
NODES_PARAMS_MACRO_T: TypeAlias = "MacroParam"
NODES_PARAMS_T: TypeAlias = "FunParam"
#
NODES_BODY_MOD_T = Union["DefFun", "DefRec", "DefEnum", "DefVar", "DefMacro", "DefType",
                         "DefGlobal", "StmtStaticAssert", "Import"]

NODES_BODY_T = Union["StmtDefer", "StmtIf", "StmtBreak", "StmtContinue", "StmtReturn",
                     "StmtExpr",
                     "StmtCompoundAssignment", "StmtBlock", "StmtCond", "DefVar",
                     "StmtAssignment", "StmtTrap"]


NODES_TYPES_T = Union["TypeBase", "TypeSpan", "TypeVec", "TypePtr", "TypeFun", "Id",
                      "TypeUnion", "TypeOf", "TypeUnionDelta"]

NODES_TYPES_OR_AUTO_T = Union[NODES_TYPES_T, "TypeAuto"]

NODES_VAL_T = Union["ValFalse", "ValTrue", "ValNum",
                    "ValVoid", "ValVec", "ValString", "ValRec", "ValSpan"]

NODES_EXPR_T = Union[NODES_VAL_T,
                     #
                     "Id", "ExprAddrOf", "ExprDeref", "ExprIndex",
                     "ExprField", "ExprCall", "ExprParen",
                     "Expr1", "Expr2", "Expr3", "ExprPointer",
                     "ExprLen", "ExprFront",
                     "ExprTypeId", "ExprSizeof", "ExprOffsetof", "ExprStmt",
                     "ExprStringify",
                     "ExprUnionTag", "ExprUnionUntagged", "ExprUnsafeCast",
                     "ExprIs", "ExprAs", "ExprWrap", "ExprUnwrap", "ExprNarrow",
                     "ExprWiden", "ExprBitCast"]

NODES_EXPR_OR_AUTO_T = Union[NODES_EXPR_T, "ValAuto"]

NODES_EXPR_OR_UNDEF_T = Union[NODES_EXPR_T, "ValUndef"]

NODES_EXPR_OR_UNDEF_OR_AUTO_T = Union[NODES_EXPR_T, "ValUndef", "ValAuto"]

NODES_BODY_MACRO_T = Union[NODES_BODY_T, NODES_EXPR_T, "MacroFor", "MacroId"]


NODES_COND_T = Union["ValFalse", "ValTrue",
                     #
                     "Id", "ExprDeref", "ExprIndex",
                     "ExprField", "ExprCall", "ExprParen",
                     "Expr1", "Expr2", "Expr3",
                     "ExprStmt", "ExprIs", "ExprNarrow"]

NODES_LHS_T = Union["Id", "ExprDeref", "ExprIndex", "ExprField", "ExprParen"]


def _EnumValues(enum_class):
    return ", ".join(x.name for x in enum_class if x.value != 0)


ALL_FIELDS = [
    NfdStr("number", "a number"),
    NfdStr("name", "name of the object"),

    NfdStr("name_list", "name of the object list"),

    NfdStr("string", "string literal"),
    NfdStr("comment", "comment"),
    NfdStr("message", "message for assert failures"),
    NfdStr("field", "record field"),
    NfdStr("label", "block  name (if not empty)"),
    NfdStr("target",
           "name of enclosing while/for/block to brach to (empty means nearest)"),
    NfdStr("init_field", "initializer field or empty (empty means next field)"),
    NfdStr("path", "TBD"),
    NFD(NFK.STR_LIST, "gen_ids",
        "name placeholder ids to be generated at macro instantiation time"),
    #
    NfdAttrBool("pub", "has public visibility"),
    NfdAttrBool("extern", "is external function (empty body)"),
    NfdAttrBool("mut", "is mutable"),
    NfdAttrBool("ref", "address may be taken"),
    NfdAttrBool("colon", "colon style list"),
    NfdAttrBool("cdecl", "use c-linkage (no module prefix)"),
    NfdAttrBool("wrapped", "is wrapped type (forces type equivalence by name)"),
    NfdAttrBool("discard", "ignore non-void expression"),
    NfdAttrBool("init", "run function at startup"),
    NfdAttrBool("fini", "run function at shutdown"),
    NfdAttrBool("unchecked", "array acces is not checked"),
    NfdAttrBool("untagged", "union type is untagged"),
    NfdAttrBool("arg_ref", "in parameter was converted for by-val to pointer"),
    NfdAttrBool("res_ref", "in parameter was converted for by-val to pointer"),
    NfdAttrBool("builtin", "module is the builtin module"),
    NfdAttrStr("doc", "possibly multi-line comment"),
    NFD(NFK.INTERNAL_BOOL, "triplequoted", "string is using 3 double quotes"),
    NFD(NFK.INTERNAL_STR, "strkind", "raw: ignore escape sequences in string, hex:"),

    #
    NfdKind("unary_expr_kind",
            f"one of: [{_EnumValues(UNARY_EXPR_KIND)}](#expr1-kind)",
            UNARY_EXPR_KIND),
    NfdKind("binary_expr_kind",
            f"one of: [{_EnumValues(BINARY_EXPR_KIND)}](#expr2-kind)",
            BINARY_EXPR_KIND),
    NfdKind("base_type_kind",
            f"one of: [{_EnumValues(BASE_TYPE_KIND)}](#base-type-kind)",
            BASE_TYPE_KIND),
    NfdKind("mod_param_kind",
            f"one of: [{_EnumValues(MOD_PARAM_KIND)}](#modparam-kind)",
            MOD_PARAM_KIND),
    NfdKind("assignment_kind",
            f"one of: [{_EnumValues(ASSIGNMENT_KIND)
                        }](#stmtcompoundassignment-kind)",
            ASSIGNMENT_KIND),
    NfdKind("macro_param_kind",
            f"one of: [{_EnumValues(MACRO_PARAM_KIND)}](#MacroParam-kind)",
            MACRO_PARAM_KIND),
    NfdKind("macro_result_kind",
            f"one of: [{_EnumValues(MACRO_PARAM_KIND)}](#MacroParam-kind)",
            MACRO_PARAM_KIND),
    NfdKind("pointer_expr_kind",
            f"one of: [{_EnumValues(POINTER_EXPR_KIND)}](#pointerop-kind)",
            POINTER_EXPR_KIND),
    #
    # TODO: fix all the None below
    NfdNodeList("params", "function parameters and/or comments", NODES_PARAMS_T,
                MACRO_PARAM_KIND.INVALID),
    NfdNodeList("params_mod", "module template parameters", NODES_PARAMS_MOD_T,
                MACRO_PARAM_KIND.INVALID),
    NfdNodeList("params_macro", "macro parameters", NODES_PARAMS_MACRO_T,
                MACRO_PARAM_KIND.INVALID),
    NfdNodeList("args", "function call arguments",
                NODES_EXPR_T, MACRO_PARAM_KIND.EXPR),
    NfdNodeList("args_mod", "module arguments",
                Union[NODES_EXPR_T, NODES_TYPES_T], MACRO_PARAM_KIND.EXPR),
    NfdNodeList("items", "enum items and/or comments", NODES_ITEMS_T,
                MACRO_PARAM_KIND.INVALID),
    NfdNodeList("fields", "record fields and/or comments", NODES_FIELDS_T,
                MACRO_PARAM_KIND.INVALID),
    NfdNodeList("types", "union types", NODES_TYPES_T,
                MACRO_PARAM_KIND.TYPE),
    NfdNodeList("inits_vec",
                "vec initializers and/or comments", NODES_INITS_ARRAY_T,
                MACRO_PARAM_KIND.INVALID),
    NfdNodeList("inits_rec",
                "rec initializers and/or comments", NODES_INITS_REC_T,
                MACRO_PARAM_KIND.INVALID),
    #
    NfdNodeList("body_mod",
                "toplevel module definitions and/or comments", NODES_BODY_MOD_T,
                MACRO_PARAM_KIND.STMT_LIST),
    NfdNodeList("body", "new scope: statement list and/or comments", NODES_BODY_T,
                MACRO_PARAM_KIND.STMT_LIST),
    NfdNodeList("body_t",
                "new scope: statement list and/or comments for true branch", NODES_BODY_T,
                MACRO_PARAM_KIND.STMT_LIST),
    NfdNodeList("body_f",
                "new scope: statement list and/or comments for false branch", NODES_BODY_T,
                MACRO_PARAM_KIND.STMT_LIST),
    NfdNodeList("body_for", "statement list for macro_loop", NODES_BODY_T,
                MACRO_PARAM_KIND.STMT_LIST),
    NfdNodeList("body_macro",
                "new scope: macro statments/expression", NODES_BODY_MACRO_T,
                MACRO_PARAM_KIND.STMT_LIST),
    NfdNodeList("cases", "list of case statements", NODES_CASES_T,
                MACRO_PARAM_KIND.STMT_LIST),

    #
    NfdNode("init_index",
            "initializer index or empty (empty mean next index)", NODES_EXPR_OR_AUTO_T, MACRO_PARAM_KIND.EXPR),
    NfdNode("type", "type expression", NODES_TYPES_T, MACRO_PARAM_KIND.TYPE),
    NfdNode("subtrahend", "type expression",
            NODES_TYPES_T, MACRO_PARAM_KIND.TYPE),
    NfdNode("type_or_auto", "type expression",
            NODES_TYPES_OR_AUTO_T, MACRO_PARAM_KIND.TYPE),
    NfdNode("result", "return type", NODES_TYPES_T, MACRO_PARAM_KIND.TYPE),
    NfdNode("size", "compile-time constant size",
            NODES_EXPR_T, MACRO_PARAM_KIND.EXPR),
    NfdNode("expr_size", "expression determining the size or auto",
            NODES_EXPR_OR_AUTO_T, MACRO_PARAM_KIND.EXPR),
    NfdNode("expr_index",
            "expression determining the index to be accessed", NODES_EXPR_T, MACRO_PARAM_KIND.EXPR),
    NfdNode("expr", "expression", NODES_EXPR_T, MACRO_PARAM_KIND.EXPR),
    NfdNode("cond", "conditional expression must evaluate to a boolean",
            NODES_COND_T, MACRO_PARAM_KIND.EXPR),
    NfdNode("expr_t",
            "expression (will only be evaluated if cond == true)", NODES_EXPR_T, MACRO_PARAM_KIND.EXPR),
    NfdNode("expr_f",
            "expression (will only be evaluated if cond == false)", NODES_EXPR_T, MACRO_PARAM_KIND.EXPR),
    NfdNode("expr1", "left operand expression",
            NODES_EXPR_T, MACRO_PARAM_KIND.EXPR),
    NfdNode("expr2", "right operand expression",
            NODES_EXPR_T, MACRO_PARAM_KIND.EXPR),
    NfdNode("expr_bound_or_undef", "",
            NODES_EXPR_OR_UNDEF_T, MACRO_PARAM_KIND.EXPR),
    NfdNode("expr_rhs", "rhs of assignment",
            NODES_EXPR_T, MACRO_PARAM_KIND.EXPR),
    NfdNode("expr_ret", "result expression (ValVoid means no result)",
            NODES_EXPR_T, MACRO_PARAM_KIND.EXPR),
    NfdNode("pointer", "pointer component of span",
            NODES_EXPR_T, MACRO_PARAM_KIND.EXPR),
    NfdNode("container", "vec and span",
            NODES_EXPR_T, MACRO_PARAM_KIND.EXPR),
    NfdNode("callee", "expression evaluating to the function to be called",
            NODES_EXPR_T, MACRO_PARAM_KIND.EXPR),
    NfdNode("value", "", NODES_EXPR_T, MACRO_PARAM_KIND.EXPR),
    NfdNode("value_or_auto", "enum constant or auto",
            NODES_EXPR_OR_AUTO_T, MACRO_PARAM_KIND.EXPR),
    NfdNode("value_or_undef", "", NODES_EXPR_OR_UNDEF_T, MACRO_PARAM_KIND.EXPR),
    NfdNode("lhs", "l-value expression", NODES_LHS_T, MACRO_PARAM_KIND.EXPR),
    NfdNode("expr_lhs", "l-value expression",
            NODES_LHS_T, MACRO_PARAM_KIND.EXPR),
    NfdNode("initial_or_undef_or_auto", "initializer",
            NODES_EXPR_OR_UNDEF_OR_AUTO_T, MACRO_PARAM_KIND.EXPR),
]

NEW_SCOPE_FIELDS = set(["body", "body_f", "body_t", "body_macro"])

ALL_FIELDS_MAP: dict[str, NFD] = {nfd.name: nfd for nfd in ALL_FIELDS}


# Optional fields must come last in a dataclass
_OPTIONAL_FIELDS = {
    "expr_ret": "@ValVoid",
    "value_or_auto": "@ValAuto",
    "target": "",
    "path": "",
    "message": "",
    "initial_or_undef_or_auto": "@ValAuto",
    "init_index": "@ValAuto",
    "init_field": "",
    "inits_vec": "@EmptyList",
    "expr_bound_or_undef": "@ValUndef",
    "args_mod": "@EmptyList",
}


def GetOptional(field: str, srcloc):
    e: Union[None, str] = _OPTIONAL_FIELDS.get(field)
    if e is None:
        return e

    assert isinstance(e, str)
    if e == "@EmptyList":
        return []
    elif e == "":
        return ""
    elif e == "@ValVoid":
        return ValVoid(x_srcloc=srcloc)
    elif e == "@ValAuto":
        return ValAuto(x_srcloc=srcloc)
    elif e == "@ValUndef":
        return ValUndef(x_srcloc=srcloc)
    else:
        assert False


def IsFieldWithDefaultValue(field, val):
    e = _OPTIONAL_FIELDS.get(field)
    if e is None:
        return False

    assert isinstance(e, str)
    if e == "@EmptyList":
        return len(val) == 0
    elif e == "":
        return val == ""
    elif e == "@ValVoid":
        return isinstance(val, ValVoid)
    elif e == "@ValAuto":
        return isinstance(val, ValAuto)
    elif e == "@ValUndef":
        return isinstance(val, ValUndef)
    else:
        assert False


X_FIELDS = {
    "x_srcloc": None,  # set by cwast.py

    # set by mod_pool.py
    # import -> imported module
    "x_module": NF.MODULE_ANNOTATED,
    # set by mod_pool.py
    # uniquified module name
    "x_modname": NF.MODNAME_ANNOTATED,  # unique module name
    # set by symbolize.py
    # contains node from GLOBAL_SYM_DEF/LOCAL_SYM_DEF group
    "x_symbol": NF.SYMBOL_ANNOTATED,
    # set by symbolize.py
    # linksbreak/continue/return nodes to enclosing node
    "x_target": NF.CONTROL_FLOW,
    # set by typify.py
    "x_field": NF.FIELD_ANNOTATED,
    "x_type": NF.TYPE_ANNOTATED,
    "x_offset": NF.TYPE_CORPUS,   # oddball, should be moved into types
    # set by eval.py
    "x_value": NF.VALUE_ANNOTATED,

    # TEMPORARY
    # set by AnnotateRole() in this file
    # used by pretty printing where we do not have sym info
    "x_role":   NF.ROLE_ANNOTATED,
    # set by mod_pool.py
    # containing module links for symbol resolution
    # id -> referenced module
    # fun -> module of archetype (only use for polymorphic function)
    # macro_invoke ->  referenced module
    "x_import": NF.IMPORT_ANNOTATED,
    "x_symtab": NF.SYMTAB,
}


def NODE_NAME(node):
    if node.ALIAS:
        return "[" + node.ALIAS + "]"
    return "[" + node.__class__.__name__ + "]"


def _FLAGS(node):
    out = []
    for c, _ in node.__class__.ATTRS:
        if getattr(node, c):
            out.append("@" + c)
    outs = " ".join(out)
    return " " + outs if outs else outs


# maps node class name and aliases to class
NODES_ALIASES = {}

ALL_NODES = set()


def _CheckNodeFieldOrder(cls):
    """
    order is
    * regular
    * optional
    * flags
    * x_
    """
    optionals = 0
    regulars = 0
    flags = 0
    xs = 0
    for field, node_type in cls.__annotations__.items():
        if field.startswith("x_"):
            assert field in X_FIELDS, f"unexpected x-field: {
                field} in node {node_type}"
            if field != "x_srcloc":
                flag_kind = X_FIELDS[field]
                assert flag_kind in cls.FLAGS, f"{cls}: {
                    field} missing flag {flag_kind}"
            xs += 1
            continue
        nfd = ALL_FIELDS_MAP[field]
        if field in _OPTIONAL_FIELDS:
            optionals += 1
            assert flags + xs == 0, f"{cls}: {field}"
        elif nfd.kind is NFK.ATTR_BOOL or nfd.kind is NFK.ATTR_STR:
            flags += 0
            assert xs == 0
        else:
            regulars += 1
            assert optionals + flags + xs == 0


def NodeCommon(cls):
    cls.__eq__ = lambda a, b: id(a) == id(b)
    cls.__hash__ = lambda a: id(a)

    assert hasattr(cls, "ALIAS") and hasattr(
        cls, "FLAGS") and hasattr(cls, "GROUP")
    assert hasattr(cls, "x_srcloc"), f"class is missing x_srcloc {cls}"
    if cls.GROUP is GROUP.Statement:
        assert hasattr(cls, "doc"), f"mising doc {cls.__name__}"
    _CheckNodeFieldOrder(cls)

    ALL_NODES.add(cls)
    NODES_ALIASES[cls.__name__] = cls

    if cls.ALIAS is not None:
        NODES_ALIASES[cls.ALIAS] = cls
    cls.FIELDS = []
    cls.ATTRS = []
    cls.ATTRS_MAP = {}
    for field, _ in cls.__annotations__.items():
        if not field.startswith("x_"):
            nfd = ALL_FIELDS_MAP[field]
            if nfd.kind is NFK.ATTR_BOOL or nfd.kind is NFK.ATTR_STR:
                cls.ATTRS.append((field, nfd))
                cls.ATTRS_MAP[field] = nfd
            else:
                cls.FIELDS.append((field, nfd))
    return cls

############################################################
# Typing
############################################################


@enum.unique
class UnionKind(enum.Enum):
    """Union Kind"""
    INVALID = 0
    NORMAL = enum.auto()
    TAG_ONLY = enum.auto()
    POINTER = enum.auto()


def align(x, a):
    return (x + a - 1) // a * a


@dataclasses.dataclass()
class CanonType:
    """Canonical Type"""
    # type of node, e.g. DefRec, TypeBase, TypeUnion, TypeSpan, etc.
    node: Any
    name: str
    #
    mut: bool = False
    dim: int = -1
    untagged: bool = False
    base_type_kind: BASE_TYPE_KIND = BASE_TYPE_KIND.INVALID
    children: list["CanonType"] = dataclasses.field(default_factory=list)
    #
    ast_node: Optional[Union["DefRec", "DefEnum"]] = None
    # we may rewrite spans and unions into recs
    # this provides a way to access the original type (mostly its typeid)
    original_type: Optional["CanonType"] = None
    replacement_type: Optional["CanonType"] = None
    # The fields below are filled during finalization
    alignment: int = -1
    size: int = -1
    register_types: Optional[list[Any]] = None
    typeid: int = -1
    union_kind: UnionKind = UnionKind.INVALID

    def __hash__(self):
        return hash(self.name)

    def is_bool(self) -> bool:
        return self.base_type_kind is BASE_TYPE_KIND.BOOL

    def is_void(self) -> bool:
        return self.base_type_kind is BASE_TYPE_KIND.VOID

    def is_int(self) -> bool:
        return self.base_type_kind in BASE_TYPE_KIND_INT

    def is_uint(self) -> bool:
        return self.base_type_kind in BASE_TYPE_KIND_UINT

    def is_sint(self) -> bool:
        return self.base_type_kind in BASE_TYPE_KIND_SINT

    def is_real(self) -> bool:
        return self.base_type_kind in BASE_TYPE_KIND_REAL

    def is_number(self) -> bool:
        return self.base_type_kind in BASE_TYPE_KIND_REAL or self.base_type_kind in BASE_TYPE_KIND_INT

    def is_wrapped(self) -> bool:
        return self.node is DefType

    def underlying_wrapped_type(self) -> "CanonType":
        assert self.is_wrapped()
        return self.children[0]

    def is_fun(self) -> bool:
        return self.node is TypeFun

    def is_rec(self) -> bool:
        return self.node is DefRec

    def parameter_types(self) -> list["CanonType"]:
        assert self.is_fun()
        return self.children[:-1]

    def result_type(self) -> "CanonType":
        assert self.is_fun()
        return self.children[-1]

    def is_pointer(self) -> bool:
        return self.node is TypePtr

    def is_span(self) -> bool:
        return self.node is TypeSpan

    def is_enum(self) -> bool:
        return self.node is DefEnum

    def is_base_type(self) -> bool:
        return self.node is TypeBase

    def is_base_or_enum_type(self) -> bool:
        return self.node is TypeBase or self.node is DefEnum

    def is_union(self) -> bool:
        return self.node is TypeUnion

    def is_untagged_union(self) -> bool:
        return self.node is TypeUnion and self.untagged

    def is_tagged_union(self) -> bool:
        return self.node is TypeUnion and not self.untagged

    def union_member_types(self) -> list["CanonType"]:
        assert self.is_union()
        return self.children

    def is_array(self) -> bool:
        return self.node is TypeVec

    def is_void_or_wrapped_void(self) -> bool:
        if self.node is DefType:
            return self.children[0].is_void()
        return self.is_void()

    def underlying_pointer_type(self) -> "CanonType":
        assert self.is_pointer()
        return self.children[0]

    def underlying_span_type(self) -> "CanonType":
        assert self.is_span()
        return self.children[0]

    def underlying_array_type(self) -> "CanonType":
        assert self.is_array()
        return self.children[0]

    def is_vec_or_span(self) -> bool:
        return self.node is TypeVec or self.node is TypeSpan

    def underlying_vec_or_span_type(self) -> "CanonType":
        assert self.is_array() or self.is_span()
        return self.children[0]

    def contained_type(self) -> "CanonType":
        if self.node is TypeVec or self.node is TypeSpan:
            return self.children[0]
        else:
            assert False, f"expected vec or span type: {self.name}"

    def aligned_size(self) -> int:
        # somtimes we need to round up. e.g. struct {int32, int8} needs 3 bytes padding
        return align(self.size, self.alignment)

    def array_dim(self):
        assert self.is_array()
        return self.dim

    def array_element_size(self):
        assert self.is_array()
        return self.size // self.dim

    def is_mutable(self) -> bool:
        return self.mut

    def fits_in_register(self) -> bool:
        reg_type = self.register_types
        return reg_type is not None and len(reg_type) == 1

    def get_single_register_type(self) -> str:
        reg_type = self.register_types
        assert reg_type is not None and len(reg_type) == 1, f"{self} {reg_type}"
        return reg_type[0]

    def get_original_typeid(self):
        if not self.original_type:
            return self.typeid
        else:
            return self.original_type.get_original_typeid()

    def _set_union_kind(self):
        seen_pointer = False
        for t in self.union_member_types():
            if t.is_wrapped():
                t = t.children[0]
            if t.is_void():
                continue
            elif t.is_pointer():
                if seen_pointer:
                    return UnionKind.NORMAL
                seen_pointer = True
            else:
                return UnionKind.NORMAL
        if seen_pointer:
            return UnionKind.POINTER
        return UnionKind.TAG_ONLY

    def finalize(self, size: int, alignment: int, register_types):
        # self.typeid = typeid
        self.size = size
        self.alignment = alignment
        self.register_types = register_types
        if self.is_tagged_union():
            self._set_union_kind()

    def __str__(self):
        return self.name + ("☠" if self.replacement_type else " ")



NO_TYPE = CanonType(None, "@invali@d")


@dataclasses.dataclass(frozen=True)
class SrcLoc:
    filename: str
    lineno: int

    def __str__(self):
        return f"{self.filename}({self.lineno})"


SRCLOC_UNKNOWN: Final[SrcLoc] = SrcLoc("@unknown@", 0)
SRCLOC_GENERATED: Final[SrcLoc] = SrcLoc("@generated@", 0)

############################################################
# Emphemeral
############################################################


@NodeCommon
@dataclasses.dataclass()
class EphemeralList:
    """Only exist temporarily after a replacement strep

    will removed (flattened) in the next cleanup list
    """
    ALIAS = None
    GROUP = GROUP.Macro
    FLAGS = NF.NON_CORE
    #
    args: list[NODES_EXPR_T]
    #
    colon: bool = False  # colon style list
    #
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN


############################################################
#
############################################################
@NodeCommon
@dataclasses.dataclass()
class Import:
    """Import another Module from `path` as `name`"""
    ALIAS = "import"
    GROUP = GROUP.Statement
    FLAGS = NF.GLOBAL_SYM_DEF | NF.NON_CORE | NF.MODULE_ANNOTATED
    #
    name: str
    path: str
    args_mod: list[NODES_EXPR_T]
    #
    doc: str = ""
    #
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN
    x_module: Optional[Any] = None

    def __repr__(self):
        return f"{NODE_NAME(self)} {self.name}"


INVALID_IMPORT = Import("$$INVALID", "", [])


@NodeCommon
@dataclasses.dataclass()
class RecField:  #
    """Record field

    All fields must be explicitly initialized. Use `ValUndef` in performance
    sensitive situations.
    """
    ALIAS = "field"
    GROUP = GROUP.Type
    FLAGS = NF.TYPE_ANNOTATED | NF.TYPE_CORPUS
    #
    name: str
    type: NODES_TYPES_T
    #
    doc: str = ""
    #
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN
    x_type: CanonType = NO_TYPE
    x_offset: int = -1

    def __repr__(self):
        return f"{NODE_NAME(self)} {self.name}: {self.type}"


@NodeCommon
@dataclasses.dataclass()
class DefRec:
    """Record definition"""
    ALIAS = "defrec"
    GROUP = GROUP.Type
    FLAGS = NF.TYPE_CORPUS | NF.TYPE_ANNOTATED | NF.GLOBAL_SYM_DEF | NF.TOP_LEVEL
    #
    name: str
    fields: list[NODES_FIELDS_T]
    #
    pub:  bool = False
    doc: str = ""
    #
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN
    x_type: CanonType = NO_TYPE

    def __repr__(self):
        return f"{NODE_NAME(self)}{_FLAGS(self)} {self.name}"

############################################################
# Identifier
############################################################


@NodeCommon
@dataclasses.dataclass()
class Id:
    """Refers to a type, variable, constant, function, module by name.

    Ids may contain a path component indicating which modules they reference.
    If the path component is missing the Id refers to the current module.

    """
    ALIAS = "id"
    GROUP = GROUP.Misc
    FLAGS = NF_EXPR | NF.SYMBOL_ANNOTATED | NF.MAY_BE_LHS | NF.IMPORT_ANNOTATED
    #
    name: str          # id or mod::id or enum::id or mod::enum::id
    #
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN
    x_type: CanonType = NO_TYPE
    x_value: Optional[Any] = None
    x_symbol: Optional[Any] = None
    x_import: Import = INVALID_IMPORT  # which import the id is qualified with

    def __repr__(self):
        return f"{NODE_NAME(self)} {self.name}"


@NodeCommon
@dataclasses.dataclass()
class TypeAuto:
    """Placeholder for an unspecified (auto derived) type

    My only occur where explicitly allowed.
    """
    ALIAS = "auto"
    GROUP = GROUP.Type
    FLAGS = NF.TYPE_ANNOTATED
    #
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN
    x_type: CanonType = NO_TYPE

    def __repr__(self):
        return f"{NODE_NAME(self)}"


############################################################
# TypeNodes
############################################################
@NodeCommon
@dataclasses.dataclass()
class FunParam:
    """Function parameter

    """
    ALIAS = "param"
    GROUP = GROUP.Type
    FLAGS = NF.LOCAL_SYM_DEF
    #
    name: str      # empty str means no var specified (fun proto type)
    type: NODES_TYPES_T
    #
    arg_ref: bool = False
    res_ref: bool = False
    doc: str = ""
    #
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN

    def __repr__(self):
        return f"{NODE_NAME(self)} {self.name}: {self.type}"


BASE_TYPE_KIND_UINT = set([
    BASE_TYPE_KIND.U8,
    BASE_TYPE_KIND.U16,
    BASE_TYPE_KIND.U32,
    BASE_TYPE_KIND.U64,
    BASE_TYPE_KIND.UINT,

])

BASE_TYPE_KIND_SINT = set([
    BASE_TYPE_KIND.S8,
    BASE_TYPE_KIND.S16,
    BASE_TYPE_KIND.S32,
    BASE_TYPE_KIND.S64,
    BASE_TYPE_KIND.SINT,
])

BASE_TYPE_KIND_INT = BASE_TYPE_KIND_UINT | BASE_TYPE_KIND_SINT

BASE_TYPE_KIND_REAL = set([
    BASE_TYPE_KIND.R32,
    BASE_TYPE_KIND.R64,
])


BASE_TYPE_KIND_TO_SIZE: dict[BASE_TYPE_KIND, int] = {
    BASE_TYPE_KIND.U8: 1,
    BASE_TYPE_KIND.U16: 2,
    BASE_TYPE_KIND.U32: 4,
    BASE_TYPE_KIND.U64: 8,

    BASE_TYPE_KIND.S8: 1,
    BASE_TYPE_KIND.S16: 2,
    BASE_TYPE_KIND.S32: 4,
    BASE_TYPE_KIND.S64: 8,
    BASE_TYPE_KIND.R32: 4,
    BASE_TYPE_KIND.R64: 8,
    BASE_TYPE_KIND.TYPEID: 2,
    BASE_TYPE_KIND.BOOL: 1,
    #
    BASE_TYPE_KIND.VOID: 0,
    BASE_TYPE_KIND.NORET: 0,

}


@NodeCommon
@dataclasses.dataclass()
class TypeBase:
    """Base type

    One of: void, bool, r32, r64, u8, u16, u32, u64, s8, s16, s32, s64
    """
    ALIAS = None
    GROUP = GROUP.Type
    FLAGS = NF.TYPE_ANNOTATED | NF.TYPE_CORPUS
    #
    base_type_kind: BASE_TYPE_KIND
    #
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN
    x_type: CanonType = NO_TYPE

    def __repr__(self):
        return f"{NODE_NAME(self)} {self.base_type_kind.name}"


@NodeCommon
@dataclasses.dataclass()
class TypePtr:
    """Pointer type
    """
    ALIAS = "ptr"
    GROUP = GROUP.Type
    FLAGS = NF.TYPE_ANNOTATED | NF.TYPE_CORPUS
    #
    type: NODES_TYPES_T
    #
    mut: bool = False  # pointee is mutable
    #
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN
    x_type: CanonType = NO_TYPE

    def __repr__(self):
        return f"{NODE_NAME(self)}{_FLAGS(self)} {self.type}"


@NodeCommon
@dataclasses.dataclass()
class TypeSpan:
    """A span (view) of a vec with compile-time unknown dimensions

    Internally, this is tuple of `start` and `length`
    (mutable/non-mutable)
    """
    ALIAS = "span"
    GROUP = GROUP.Type
    FLAGS = NF.TYPE_ANNOTATED | NF.TYPE_CORPUS | NF.NON_CORE
    #
    type: NODES_TYPES_T
    #
    mut: bool = False  # span is mutable
    #
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN
    x_type: CanonType = NO_TYPE

    def __repr__(self):
        mod = "-MUT" if self.mut else ""
        return f"{NODE_NAME(self)}{mod}({self.type})"


@NodeCommon
@dataclasses.dataclass()
class TypeVec:
    """An array of the given type and `size`

    """
    ALIAS = "vec"
    GROUP = GROUP.Type
    FLAGS = NF.TYPE_ANNOTATED | NF.TYPE_CORPUS
    #
    size: "NODES_EXPR_T"      # must be const and unsigned
    type: NODES_TYPES_T
    #
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN
    x_type: CanonType = NO_TYPE

    def __repr__(self):
        return f"{NODE_NAME(self)} ({self.type}) {self.size}"


@NodeCommon
@dataclasses.dataclass()
class TypeFun:
    """A function signature

    The `FunParam.name` field is ignored and should be `_`
    """
    ALIAS = "sig"
    GROUP = GROUP.Type
    FLAGS = NF.TYPE_ANNOTATED | NF.TYPE_CORPUS
    #
    params: list[NODES_PARAMS_T]
    result: NODES_TYPES_T
    #
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN
    x_type: CanonType = NO_TYPE

    def __repr__(self):
        t = [str(t) for t in self.params]
        return f"{NODE_NAME(self)} {' '.join(t)} -> {self.result}"


@NodeCommon
@dataclasses.dataclass()
class TypeUnion:
    """Union types (tagged unions)

    Unions are "auto flattening", e.g.
    Union(a, Union(b,c), Union(a, d)) = Union(a, b, c, d)
    """
    ALIAS = "union"
    GROUP = GROUP.Type
    FLAGS = NF.TYPE_ANNOTATED | NF.TYPE_CORPUS
    #
    types: list[NODES_TYPES_T]
    #
    untagged: bool = False
    #
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN
    x_type: CanonType = NO_TYPE

    def __repr__(self):
        t = [str(t) for t in self.types]
        extra = "-untagged" if self.untagged else ""
        return f"{NODE_NAME(self)}{extra} {' '.join(t)}"


@NodeCommon
@dataclasses.dataclass()
class TypeUnionDelta:
    """Type resulting from the difference of TypeUnion and a non-empty subset sets of its members
    """
    ALIAS = "union_delta"
    GROUP = GROUP.Type
    FLAGS = NF.TYPE_ANNOTATED | NF.NON_CORE
    #
    type: NODES_TYPES_T
    subtrahend: NODES_TYPES_T
    #
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN
    x_type: CanonType = NO_TYPE

    def __repr__(self):
        return f"{NODE_NAME(self)}{self.type} - {self.subtrahend}"


@NodeCommon
@dataclasses.dataclass()
class TypeOf:
    """(Static) type of the expression. Computed at compile-time.
    The underlying expression is not evaluated.
    """
    ALIAS = "type_of"
    GROUP = GROUP.Type
    FLAGS = NF.TYPE_ANNOTATED | NF.NON_CORE
    #
    expr: NODES_EXPR_T
    #
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN
    x_type: CanonType = NO_TYPE

    def __repr__(self):
        return f"{NODE_NAME(self)}"
############################################################
# Val Nodes
############################################################


@NodeCommon
@dataclasses.dataclass()
class ValAuto:
    """Placeholder for an unspecified (auto derived) value

    Used for: array dimensions, enum values, chap and range
    """
    ALIAS = "auto_val"
    GROUP = GROUP.Value
    FLAGS = NF_EXPR
    #
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN
    x_type: CanonType = NO_TYPE
    x_value: Optional[Any] = None

    def __repr__(self):
        return f"{NODE_NAME(self)}"


@NodeCommon
@dataclasses.dataclass()
class ValTrue:
    """Bool constant `true`"""
    ALIAS = "true"
    GROUP = GROUP.Value
    FLAGS = NF_EXPR
    #
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN
    x_type: CanonType = NO_TYPE
    x_value: Optional[Any] = None

    def __repr__(self):
        return f"{NODE_NAME(self)}"


@NodeCommon
@dataclasses.dataclass()
class ValFalse:
    """Bool constant `false`"""
    ALIAS = "false"
    GROUP = GROUP.Value
    FLAGS = NF_EXPR
    #
    x_type: CanonType = NO_TYPE
    x_value: Optional[Any] = None
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN

    def __repr__(self):
        return f"{NODE_NAME(self)}"


@NodeCommon
@dataclasses.dataclass()
class ValNum:
    """Numeric constant (signed int, unsigned int, real

    Underscores in `number` are ignored. `number` can be explicitly typed via
    suffices like `_u64`, `_s16`, `_r32`.
    """
    ALIAS = ""
    GROUP = GROUP.Value
    FLAGS = NF_EXPR
    #
    number: str   # maybe a (unicode) character as well
    #
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN
    x_type: CanonType = NO_TYPE
    x_value: Optional[Any] = None

    def __repr__(self):
        return f"{NODE_NAME(self)} {self.number}"


@NodeCommon
@dataclasses.dataclass()
class ValUndef:
    """Special constant to indiciate *no default value*
    """
    ALIAS = "undef"
    GROUP = GROUP.Value
    FLAGS = NF.VALUE_ANNOTATED
    #
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN
    x_value: Optional[Any] = None    # this is always a ValUndef() object

    def __repr__(self):
        return f"{NODE_NAME(self)}"


@NodeCommon
@dataclasses.dataclass()
class ValVoid:
    """Only value inhabiting the `TypeVoid` type

    It can be used to model *null* in nullable pointers via a union type.
     """
    ALIAS = "void_val"
    GROUP = GROUP.Value
    FLAGS = NF_EXPR
    #
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN
    x_type: CanonType = NO_TYPE
    x_value: Optional[Any] = None

    def __repr__(self):
        return f"{NODE_NAME(self)}"


@NodeCommon
@dataclasses.dataclass()
class IndexVal:
    """Part of an array literal

    e.g. `.1 = 5`
    If index is auto use `0` or `previous index + 1`.
    """
    ALIAS = "index_val"
    GROUP = GROUP.Value
    FLAGS = NF_EXPR
    #
    value_or_undef: NODES_EXPR_T
    init_index: NODES_EXPR_OR_AUTO_T  # compile time constant
    #
    doc: str = ""
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN
    x_type: CanonType = NO_TYPE
    x_value: Optional[Any] = None

    def __repr__(self):
        return f"{NODE_NAME(self)} [{self.init_index}] = {self.value_or_undef}"


@NodeCommon
@dataclasses.dataclass()
class FieldVal:
    """Part of rec literal

    e.g. `.imag = 5`
    If field is empty use `first field` or `next field`.
    """
    ALIAS = "field_val"
    GROUP = GROUP.Value
    FLAGS = NF_EXPR | NF.FIELD_ANNOTATED
    #
    value_or_undef: "NODES_EXPR_T"
    init_field: str
    #
    doc: str = ""
    #
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN
    x_type: CanonType = NO_TYPE
    x_value: Optional[Any] = None
    x_field: Optional["RecField"] = None

    def __repr__(self):
        return f"{NODE_NAME(self)} {self.init_field}"


@NodeCommon
@dataclasses.dataclass()
class ValVec:
    """An vec literal

    `[10]int{.1 = 5, .2 = 6, 77}`

    `expr_size` must be constant or auto

    Note, that it is NOT possible to use a type alias here.
    Both the element type and the dimension need to be specified.
    """
    ALIAS = "vec_val"
    GROUP = GROUP.Value
    FLAGS = NF_EXPR
    #
    expr_size: NODES_EXPR_OR_AUTO_T
    type: NODES_TYPES_T
    inits_vec: list[NODES_INITS_ARRAY_T]
    #
    doc: str = ""
    #
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN
    x_type: CanonType = NO_TYPE
    x_value: Optional[Any] = None

    def __repr__(self):
        return f"{NODE_NAME(self)} type={self.type} size={self.expr_size}"


@NodeCommon
@dataclasses.dataclass()
class ValSpan:
    """A span value comprised of a pointer and length

    type and mutability is defined by the pointer
    """
    ALIAS = "span_val"
    GROUP = GROUP.Value
    FLAGS = NF_EXPR | NF.NON_CORE
    #
    pointer: "NODES_EXPR_T"
    expr_size: "NODES_EXPR_T"
    #
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN
    x_type: CanonType = NO_TYPE
    x_value: Optional[Any] = None

    def __repr__(self):
        return f"{NODE_NAME(self)} {self.pointer} {self.expr_size}"


@NodeCommon
@dataclasses.dataclass()
class ValString:
    """An vec_val encoded as a string

    type is `[strlen(string)]u8`. `string` may be escaped/raw
    """
    ALIAS = None
    GROUP = GROUP.Value
    FLAGS = NF_EXPR
    #
    string: str
    #
    strkind: str = ""   # or raw or hex
    triplequoted: bool = False
    #
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN
    x_type: CanonType = NO_TYPE
    x_value: Optional[Any] = None

    def __repr__(self):
        return f"{NODE_NAME(self)} {self.string}"


@NodeCommon
@dataclasses.dataclass()
class ValRec:
    """A record literal

    `E.g.: complex{.imag = 5, .real = 1}`
    """
    ALIAS = "rec_val"
    GROUP = GROUP.Value
    FLAGS = NF_EXPR
    #
    type: NODES_TYPES_T
    inits_rec: list[NODES_INITS_REC_T]
    #
    doc: str = ""
    #
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN
    x_type: CanonType = NO_TYPE
    x_value: Optional[Any] = None

    def __repr__(self):
        t = [str(i) for i in self.inits_rec]
        return f"{NODE_NAME(self)} [{self.type}] {' '.join(t)}"


############################################################
# ExprNode
############################################################


@NodeCommon
@dataclasses.dataclass()
class ExprDeref:
    """Dereference a pointer represented by `expr`"""
    ALIAS = "^"
    GROUP = GROUP.Expression
    FLAGS = NF_EXPR | NF.MAY_BE_LHS
    #
    expr: NODES_EXPR_T  # must be of type AddrOf
    #
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN
    x_type: CanonType = NO_TYPE
    x_value: Optional[Any] = None

    def __repr__(self):
        return f"{NODE_NAME(self)} {self.expr}"


@NodeCommon
@dataclasses.dataclass()
class ExprAddrOf:
    """Create a pointer to object represented by `expr`

    Pointer can optionally point to a mutable object if the
    pointee is mutable.
    """
    ALIAS = "&"
    GROUP = GROUP.Expression
    FLAGS = NF_EXPR
    #
    expr_lhs: NODES_EXPR_T
    #
    mut: bool = False
    #
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN
    x_type: CanonType = NO_TYPE
    x_value: Optional[Any] = None

    def __repr__(self):
        return f"{NODE_NAME(self)}{_FLAGS(self)} {self.expr_lhs}"


@NodeCommon
@dataclasses.dataclass()
class ExprCall:
    """Function call expression.
    """
    ALIAS = "call"
    GROUP = GROUP.Expression
    FLAGS = NF_EXPR
    #
    callee: NODES_EXPR_T
    args: list[NODES_EXPR_T]
    #
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN
    x_type: CanonType = NO_TYPE
    x_value: Optional[Any] = None

    def is_polymorphic(self) -> bool:
        return isinstance(self.callee, Id) and self.callee.name.endswith("@")

    def __repr__(self):
        return f"{NODE_NAME(self)} {self.callee}"


@NodeCommon
@dataclasses.dataclass()
class ExprParen:
    """Used for preserving parenthesis in the source
    """
    ALIAS = "paren"
    GROUP = GROUP.Expression
    FLAGS = NF_EXPR | NF.NON_CORE
    #
    expr: NODES_EXPR_T
    #
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN
    x_type: CanonType = NO_TYPE
    x_value: Optional[Any] = None

    def __repr__(self):
        return f"{NODE_NAME(self)} {self.expr}"


@NodeCommon
@dataclasses.dataclass()
class ExprField:
    """Access field in expression representing a record.
    """
    ALIAS = "."
    GROUP = GROUP.Expression
    FLAGS = NF_EXPR | NF.FIELD_ANNOTATED | NF.MAY_BE_LHS
    #
    container: NODES_EXPR_T  # must be of type rec
    field: str
    #
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN
    x_type: CanonType = NO_TYPE
    x_value: Optional[Any] = None
    x_field: Optional["RecField"] = None

    def __repr__(self):
        return f"{NODE_NAME(self)} {self.container}  field:{self.field}"


@NodeCommon
@dataclasses.dataclass()
class Expr1:
    """Unary expression."""
    ALIAS = None
    GROUP = GROUP.Expression
    FLAGS = NF_EXPR
    #
    unary_expr_kind: UNARY_EXPR_KIND
    expr: NODES_EXPR_T
    #
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN
    x_type: CanonType = NO_TYPE
    x_value: Optional[Any] = None

    def __repr__(self):
        return f"{NODE_NAME(self)} {self.unary_expr_kind} {self.expr}"


@NodeCommon
@dataclasses.dataclass()
class ExprPointer:
    """Pointer arithmetic expression - optionally bound checked.."""
    ALIAS = None
    GROUP = GROUP.Expression
    FLAGS = NF_EXPR
    #
    pointer_expr_kind: POINTER_EXPR_KIND
    expr1: NODES_EXPR_T
    expr2: NODES_EXPR_T
    expr_bound_or_undef: NODES_EXPR_T
    #
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN
    x_type: CanonType = NO_TYPE
    x_value: Optional[Any] = None

    def __repr__(self):
        return f"{self.pointer_expr_kind.name}({self.expr1}, {self.expr2}, {self.expr_bound_or_undef})"


@NodeCommon
@dataclasses.dataclass()
class Expr2:
    """Binary expression."""
    ALIAS = None
    GROUP = GROUP.Expression
    FLAGS = NF_EXPR
    #
    binary_expr_kind: BINARY_EXPR_KIND
    expr1: NODES_EXPR_T
    expr2: NODES_EXPR_T
    #
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN
    x_type: CanonType = NO_TYPE
    x_value: Optional[Any] = None

    def __repr__(self):
        return f"{self.binary_expr_kind.name}({self.expr1}, {self.expr2})"


@NodeCommon
@dataclasses.dataclass()
class Expr3:
    """Tertiary expression (like C's `? :`)
    """
    ALIAS = "?"
    GROUP = GROUP.Expression
    FLAGS = NF_EXPR | NF.NON_CORE
    #
    cond: NODES_EXPR_T  # must be of type  bool
    expr_t: NODES_EXPR_T
    expr_f: NODES_EXPR_T
    #
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN
    x_type: CanonType = NO_TYPE
    x_value: Optional[Any] = None

    def __repr__(self):
        return f"? {self.cond} {self.expr_t} {self.expr_f}"

# Array/Slice Expressions


@NodeCommon
@dataclasses.dataclass()
class ExprIndex:
    """Optionally unchecked indexed access of vec or span
    """
    ALIAS = "at"
    GROUP = GROUP.Expression
    FLAGS = NF_EXPR | NF.MAY_BE_LHS | NF.NON_CORE
    #
    container: NODES_EXPR_T  # must be of type span or vec
    expr_index: NODES_EXPR_T  # must be of int type
    #
    unchecked: bool = False
    #
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN
    x_type: CanonType = NO_TYPE
    x_value: Optional[Any] = None

    def __repr__(self):
        return f"AT {self.container} {self.expr_index}"


@NodeCommon
@dataclasses.dataclass()
class ExprLen:
    """Length of vec or span

    Result type is `uint`.
    """
    ALIAS = "len"
    GROUP = GROUP.Expression
    FLAGS = NF_EXPR | NF.NON_CORE
    #
    container: NODES_EXPR_T   # must be of type span or vec
    #
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN
    x_type: CanonType = NO_TYPE
    x_value: Optional[Any] = None

    def __repr__(self):
        return self.__class__.__name__
# Cast Like Expressions


@NodeCommon
@dataclasses.dataclass()
class ExprFront:
    """Address of the first element of an vec or span

    Similar to `(& (at container 0))` but will not fail if container has zero size
    """
    ALIAS = "front"
    GROUP = GROUP.Expression
    FLAGS = NF_EXPR
    #
    container: NODES_EXPR_T   # must be of type span or vec
    #
    mut: bool = False
    #
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN
    x_type: CanonType = NO_TYPE
    x_value: Optional[Any] = None

    def __repr__(self):
        return self.__class__.__name__


# Cast Like Expressions
@NodeCommon
@dataclasses.dataclass()
class ExprIs:
    """Test actual expression (run-time) type

    Typically used when `expr` is a tagged union type.
    Otherwise, the node can be constant folded.

    `type` can be a tagged union itself.
    """
    ALIAS = "is"
    GROUP = GROUP.Expression
    FLAGS = NF_EXPR | NF.NON_CORE
    #
    expr: NODES_EXPR_T
    type: NODES_TYPES_T
    #
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN
    x_type: CanonType = NO_TYPE
    x_value: Optional[Any] = None

    def __repr__(self):
        return f"{NODE_NAME(self)} {self.expr} {self.type}"


@NodeCommon
@dataclasses.dataclass()
class ExprWrap:
    """Cast: underlying type -> enum/wrapped
    """
    ALIAS = "wrap_as"
    GROUP = GROUP.Expression
    FLAGS = NF_EXPR
    #
    expr: NODES_EXPR_T
    type: NODES_TYPES_T
    #
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN
    x_type: CanonType = NO_TYPE
    x_value: Optional[Any] = None

    def __repr__(self):
        return f"{self.expr} WRAP {self.type}"


@NodeCommon
@dataclasses.dataclass()
class ExprUnwrap:
    """Cast: enum/wrapped -> underlying type
    """
    ALIAS = "unwrap"
    GROUP = GROUP.Expression
    FLAGS = NF_EXPR
    #
    expr: NODES_EXPR_T
    #
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN
    x_type: CanonType = NO_TYPE
    x_value: Optional[Any] = None

    def __repr__(self):
        return f"{NODE_NAME(self)} {self.expr}"


@NodeCommon
@dataclasses.dataclass()
class ExprAs:
    """Safe Cast (Conversion)

    Allowed:
    u8-u64, s8-s64 <-> u8-u64, s8-s64
    u8-u64, s8-s64 -> r32-r64  (note: one way only)
    """
    ALIAS = "as"
    GROUP = GROUP.Expression
    FLAGS = NF_EXPR
    #
    expr: NODES_EXPR_T
    type: NODES_TYPES_T
    #
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN
    x_type: CanonType = NO_TYPE
    x_value: Optional[Any] = None

    def __repr__(self):
        return f"{NODE_NAME(self)} {self.expr} -> {self.type}"


@NodeCommon
@dataclasses.dataclass()
class ExprNarrow:
    """Narrowing Cast (for unions)

    optionally unchecked
    """
    ALIAS = "narrow_as"
    GROUP = GROUP.Expression
    FLAGS = NF_EXPR
    #
    expr: NODES_EXPR_T
    type: NODES_TYPES_T
    #
    unchecked: bool = False
    #
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN
    x_type: CanonType = NO_TYPE
    x_value: Optional[Any] = None

    def __repr__(self):
        return f"{NODE_NAME(self)} {self.expr} -> {self.type}"


@NodeCommon
@dataclasses.dataclass()
class ExprWiden:
    """Widening Cast (for unions)

    Usually this is implicit
    """
    ALIAS = "widen_as"
    GROUP = GROUP.Expression
    FLAGS = NF_EXPR
    #
    expr: NODES_EXPR_T
    type: NODES_TYPES_T
    #
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN
    x_type: CanonType = NO_TYPE
    x_value: Optional[Any] = None

    def __repr__(self):
        return f"{NODE_NAME(self)} {self.expr} {self.expr.x_type} -> {self.type.x_type}"


@NodeCommon
@dataclasses.dataclass()
class ExprUnsafeCast:
    """Unsafe Cast

    Allowed:
    ptr a <-> ptr b

    """
    ALIAS = "unsafe_as"
    GROUP = GROUP.Expression
    FLAGS = NF_EXPR
    #
    expr: NODES_EXPR_T
    type: NODES_TYPES_T
    #
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN
    x_type: CanonType = NO_TYPE
    x_value: Optional[Any] = None

    def __repr__(self):
        return f"{NODE_NAME(self)} {self.expr} -> {self.type}"


@NodeCommon
@dataclasses.dataclass()
class ExprBitCast:
    """Bit cast.

    Type must have same size and alignment as type of item

    s32,u32,f32 <-> s32,u32,f32
    s64,u64, f64 <-> s64,u64, f64
    sint, uint <-> ptr(x)
    ptr(a) <-> ptr(b)
    It is also ok to bitcase complex objects like recs
    """
    ALIAS = "bitwise_as"
    GROUP = GROUP.Expression
    FLAGS = NF_EXPR
    #
    expr: NODES_EXPR_T
    type: NODES_TYPES_T
    #
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN
    x_type: CanonType = NO_TYPE
    x_value: Optional[Any] = None

    def __repr__(self):
        return f"{NODE_NAME(self)} {self.expr} {self.type.x_type}"


@NodeCommon
@dataclasses.dataclass()
class ExprTypeId:
    """TypeId of type

    Result has type is `typeid`"""
    ALIAS = "typeid_of"
    GROUP = GROUP.Expression
    FLAGS = NF_EXPR | NF.NON_CORE
    #
    type: NODES_TYPES_T
    #
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN
    x_type: CanonType = NO_TYPE
    x_value: Optional[Any] = None

    def __repr__(self):
        return f"{NODE_NAME(self)} {self.type}"


@NodeCommon
@dataclasses.dataclass()
class ExprUnionTag:
    """Typetag of tagged union type

    result has type is `typeid`"""
    ALIAS = "union_tag"
    GROUP = GROUP.Expression
    FLAGS = NF_EXPR | NF.NON_CORE
    #
    expr: NODES_EXPR_T
    #
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN
    x_type: CanonType = NO_TYPE
    x_value: Optional[Any] = None

    def __repr__(self):
        return f"{NODE_NAME(self)} {self.expr}"


@NodeCommon
@dataclasses.dataclass()
class ExprUnionUntagged:
    """Untagged union portion of tagged union type

    Result has type untagged union"""
    ALIAS = "union_untagged"
    GROUP = GROUP.Expression
    FLAGS = NF_EXPR | NF.NON_CORE
    #
    expr: NODES_EXPR_T
    #
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN
    x_type: CanonType = NO_TYPE
    x_value: Optional[Any] = None

    def __repr__(self):
        return f"{NODE_NAME(self)} {self.expr}"


@NodeCommon
@dataclasses.dataclass()
class ExprSizeof:
    """Byte size of type

    Result has type is `uint`"""
    ALIAS = "size_of"
    GROUP = GROUP.Expression
    FLAGS = NF_EXPR | NF.NON_CORE
    #
    type: NODES_TYPES_T
    #
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN
    x_type: CanonType = NO_TYPE
    x_value: Optional[Any] = None

    def __repr__(self):
        return f"{NODE_NAME(self)} {self.type}"


@NodeCommon
@dataclasses.dataclass()
class ExprOffsetof:
    """Byte offset of field in record types

    Result has type `uint`"""
    ALIAS = "offset_of"
    GROUP = GROUP.Expression
    FLAGS = NF_EXPR | NF.FIELD_ANNOTATED | NF.NON_CORE
    #
    type: NODES_TYPES_T  # must be rec
    field: str
    #
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN
    x_type: CanonType = NO_TYPE
    x_value: Optional[Any] = None
    x_field: Optional["RecField"] = None

    def __repr__(self):
        return f"{NODE_NAME(self)} {self.type} {self.field}"


@NodeCommon
@dataclasses.dataclass()
class ExprStmt:
    """Expr with Statements

    The body statements must be terminated by a StmtReturn
    """
    ALIAS = "expr"
    GROUP = GROUP.Expression
    FLAGS = NF_EXPR
    #
    body: list[NODES_BODY_T]  # new scope
    #
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN
    x_type: CanonType = NO_TYPE
    x_value: Optional[Any] = None

    def __repr__(self):
        return f"{NODE_NAME(self)}"


############################################################
# Stmt
############################################################
@NodeCommon
@dataclasses.dataclass()
class StmtBlock:
    """Block statement.

    if `label` is non-empty, nested break/continue statements can target this `block`.
    """
    ALIAS = "block"
    GROUP = GROUP.Statement
    FLAGS = NF(0)
    #
    label: str
    body: list[NODES_BODY_T]  # new scope
    #
    doc: str = ""
    #
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN

    def __repr__(self):
        return f"{NODE_NAME(self)} {self.label}"


@NodeCommon
@dataclasses.dataclass()
class StmtDefer:
    """Defer statement

    Note: defer body's containing return statments have
    non-straightforward semantics.
    """
    ALIAS = "defer"
    GROUP = GROUP.Statement
    FLAGS = NF.NON_CORE
    #
    body:  list[NODES_BODY_T]  # new scope, must NOT contain RETURN
    #
    doc: str = ""
    #
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN

    def __repr__(self):
        return f"{NODE_NAME(self)}"


@NodeCommon
@dataclasses.dataclass()
class StmtIf:
    """If statement"""
    ALIAS = "if"
    GROUP = GROUP.Statement
    FLAGS = NF(0)
    #
    cond: NODES_EXPR_T        # must be of type bool
    body_t: list[NODES_BODY_T]  # new scope
    body_f: list[NODES_BODY_T]  # new scope
    #
    doc: str = ""
    #
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN

    def __repr__(self):
        return f"{NODE_NAME(self)} {self.cond}"


@NodeCommon
@dataclasses.dataclass()
class Case:
    """Single case of a Cond statement"""
    ALIAS = "case"
    GROUP = GROUP.Statement
    FLAGS = NF.NON_CORE
    #
    cond: NODES_EXPR_T        # must be of type bool
    body: list[NODES_BODY_T]  # new scope
    #
    doc: str = ""
    #
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN

    def __repr__(self):
        return f"{NODE_NAME(self)} {self.cond}"


@NodeCommon
@dataclasses.dataclass()
class StmtCond:
    """Multicase if-elif-else statement"""
    ALIAS = "cond"
    GROUP = GROUP.Statement
    FLAGS = NF.NON_CORE
    #
    cases: list[NODES_CASES_T]
    #
    doc: str = ""
    #
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN

    def __repr__(self):
        return f"{NODE_NAME(self)}"


@NodeCommon
@dataclasses.dataclass()
class StmtBreak:
    """Break statement

    use "" if the target is the nearest for/while/block """
    ALIAS = "break"
    GROUP = GROUP.Statement
    FLAGS = NF.CONTROL_FLOW
    #
    target: str  # use "" for no value
    #
    doc: str = ""
    #
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN
    x_target: Optional[Any] = None

    def __repr__(self):
        return f"{NODE_NAME(self)} {self.target}"


@NodeCommon
@dataclasses.dataclass()
class StmtContinue:
    """Continue statement

    use "" if the target is the nearest for/while/block """
    ALIAS = "continue"
    GROUP = GROUP.Statement
    FLAGS = NF.CONTROL_FLOW
    #
    target: str  # use "" for no value
    #
    doc: str = ""
    #
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN
    x_target: Optional[Any] = None

    def __repr__(self):
        return f"{NODE_NAME(self)} {self.target}"


@NodeCommon
@dataclasses.dataclass()
class StmtReturn:
    """Return statement

    Returns from the first enclosing ExprStmt node or the enclosing DefFun node.
    Uses void_val if the DefFun's return type is void
    """
    ALIAS = "return"
    GROUP = GROUP.Statement
    FLAGS = NF.CONTROL_FLOW
    #
    expr_ret: NODES_EXPR_T
    #
    doc: str = ""
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN
    x_target: Optional[Any] = None

    def __repr__(self):
        return f"{NODE_NAME(self)} {self.expr_ret}"


@NodeCommon
@dataclasses.dataclass()
class StmtExpr:
    """Expression statement

    Turns an expression (typically a call) into a statement
    """
    ALIAS = "do"
    GROUP = GROUP.Statement
    FLAGS = NF.NONE
    #
    expr: ExprCall
    #
    doc: str = ""
    #
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN

    def __repr__(self):
        return f"{NODE_NAME(self)} {self.expr}"


@NodeCommon
@dataclasses.dataclass()
class StmtStaticAssert:
    """Static assert statement (must evaluate to true at compile-time"""
    ALIAS = "static_assert"
    GROUP = GROUP.Statement
    FLAGS = NF.TOP_LEVEL | NF.NON_CORE
    #
    cond: NODES_EXPR_T  # must be of type bool
    message: str     # should this be an expression?
    #
    doc: str = ""
    #
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN

    def __repr__(self):
        return f"{NODE_NAME(self)} {self.cond}"


@NodeCommon
@dataclasses.dataclass()
class StmtTrap:
    """Trap statement"""
    ALIAS = "trap"
    GROUP = GROUP.Statement
    FLAGS = NF.NONE
    #
    doc: str = ""
    #
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN

    def __repr__(self):
        return f"{NODE_NAME(self)}"


@NodeCommon
@dataclasses.dataclass()
class StmtCompoundAssignment:
    """Compound assignment statement

    Note: this does not support pointer inc/dec
    """
    ALIAS = None
    GROUP = GROUP.Statement
    FLAGS = NF.NON_CORE
    #
    assignment_kind: ASSIGNMENT_KIND
    lhs: NODES_LHS_T
    expr_rhs: NODES_EXPR_T
    #
    doc: str = ""
    #
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN

    def __repr__(self):
        return f"{NODE_NAME(self)} [{self.assignment_kind.name}] {self.lhs} = {self.expr_rhs}"


@NodeCommon
@dataclasses.dataclass()
class StmtAssignment:
    """Assignment statement"""
    ALIAS = "="
    GROUP = GROUP.Statement
    FLAGS = NF.NONE
    #
    lhs: NODES_LHS_T
    expr_rhs: NODES_EXPR_T
    #
    doc: str = ""
    #
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN

    def __repr__(self):
        return f"{NODE_NAME(self)} {self.lhs} = {self.expr_rhs}"


############################################################
# Definitions
############################################################


@NodeCommon
@dataclasses.dataclass()
class EnumVal:
    """ Enum element.

     `value: ValAuto` means previous value + 1"""
    ALIAS = "entry"
    GROUP = GROUP.Type
    FLAGS = NF.TYPE_ANNOTATED | NF.VALUE_ANNOTATED | NF.GLOBAL_SYM_DEF
    #
    name: str
    value_or_auto: Union["ValNum", ValAuto]
    #
    doc: str = ""
    #
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN
    x_type: CanonType = NO_TYPE
    x_value: Optional[Any] = None

    def __repr__(self):
        return f"{NODE_NAME(self)} {self.name}: {self.value_or_auto}"


@NodeCommon
@dataclasses.dataclass()
class DefEnum:
    """Enum definition"""
    ALIAS = "enum"
    GROUP = GROUP.Type
    FLAGS = NF.TYPE_CORPUS | NF.TYPE_ANNOTATED | NF.GLOBAL_SYM_DEF | NF.TOP_LEVEL | NF.VALUE_ANNOTATED
    #
    name: str
    base_type_kind: BASE_TYPE_KIND   # must be integer
    items: list[NODES_ITEMS_T]
    #
    pub:  bool = False
    doc: str = ""
    #
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN
    x_type: CanonType = NO_TYPE
    x_value: Optional[Any] = None  # used to guide the evaluation of EnumVal

    def __repr__(self):
        return f"{NODE_NAME(self)}{_FLAGS(self)} {self.name}"


@NodeCommon
@dataclasses.dataclass()
class DefType:
    """Type definition

    A `wrapped` gives the underlying type a new name that is not type compatible.
    To convert between the two use an `as` cast expression.
    """
    ALIAS = "type"
    GROUP = GROUP.Statement
    FLAGS = NF.TYPE_ANNOTATED | NF.TYPE_CORPUS | NF.GLOBAL_SYM_DEF | NF.TOP_LEVEL
    #
    name: str
    type: NODES_TYPES_T
    #
    pub:  bool = False
    wrapped: bool = False
    doc: str = ""
    #
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN
    x_type: CanonType = NO_TYPE

    def __repr__(self):
        return f"{NODE_NAME(self)}{_FLAGS(self)} {self.name} = {self.type}"


@NodeCommon
@dataclasses.dataclass()
class DefVar:
    """Variable definition at local scope (DefGlobal is used for global scope)

    Allocates space on stack (or in a register) and initializes it with `initial_or_undef_or_auto`.
    `mut` makes the allocated space read/write otherwise it is readonly.
    `ref` allows the address of the  variable to be taken and prevents register allocation.

    """
    ALIAS = "let"
    GROUP = GROUP.Statement
    FLAGS = NF.LOCAL_SYM_DEF
    #
    name: str
    type_or_auto: NODES_TYPES_OR_AUTO_T
    initial_or_undef_or_auto: NODES_EXPR_T
    #
    mut: bool = False
    ref: bool = False
    doc: str = ""
    #
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN

    def __repr__(self):
        return f"{NODE_NAME(self)}{_FLAGS(self)} {self.name} {self.type_or_auto} {self.initial_or_undef_or_auto}"


@NodeCommon
@dataclasses.dataclass()
class DefGlobal:
    """Variable definition at global scope (DefVar is used for local scope)

    Allocates space in static memory and initializes it with `initial_or_undef`.
    `mut` makes the allocated space read/write otherwise it is readonly.
    """
    ALIAS = "global"
    GROUP = GROUP.Statement
    FLAGS = NF.GLOBAL_SYM_DEF | NF.TOP_LEVEL
    #
    name: str
    type_or_auto: NODES_TYPES_OR_AUTO_T
    initial_or_undef_or_auto: NODES_EXPR_T
    #
    pub: bool = False
    mut: bool = False
    ref: bool = False
    cdecl: bool = False
    doc: str = ""
    #
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN

    def __repr__(self):
        return f"{NODE_NAME(self)}{_FLAGS(self)} {self.name} {self.type_or_auto} {self.initial_or_undef_or_auto}"


@NodeCommon
@dataclasses.dataclass()
class DefFun:
    """Function definition

    `init` and `fini` indicate module initializer/finalizers

    `extern` indicates a prototype and hence the function body must be empty.

    `cdecl` disables name mangling

    `ref`  fun may be assigned to a variable (i.e. its address may be taken)
     """
    ALIAS = "fun"
    GROUP = GROUP.Statement
    FLAGS = NF.TYPE_ANNOTATED | NF.GLOBAL_SYM_DEF | NF.TOP_LEVEL | NF.IMPORT_ANNOTATED
    #
    name: str
    params: list[NODES_PARAMS_T]
    result: NODES_TYPES_T
    body: list[NODES_BODY_T]  # new scope
    #
    init: bool = False
    fini: bool = False
    pub: bool = False
    ref: bool = False
    extern: bool = False
    cdecl: bool = False
    doc: str = ""
    #
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN
    x_type: CanonType = NO_TYPE
    x_import: Import = INVALID_IMPORT  # only used for polymorphic function

    def is_polymorphic(self) -> bool:
        return self.name.endswith("@")

    def __repr__(self):
        params = ', '.join(str(p) for p in self.params)
        return f"{NODE_NAME(self)}{_FLAGS(self)} {self.name} [{params}]->{self.result}"


@NodeCommon
@dataclasses.dataclass()
class ModParam:
    """Module Parameters"""
    ALIAS = "modparam"
    GROUP = GROUP.Statement
    FLAGS = NF.GLOBAL_SYM_DEF | NF.NON_CORE
    #
    name: str
    mod_param_kind: MOD_PARAM_KIND
    #
    doc: str = ""
    #
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN

    def __repr__(self):
        return f"{NODE_NAME(self)} {self.name} {self.mod_param_kind.name}"


@NodeCommon
@dataclasses.dataclass()
class DefMod:
    """Module Definition

    The module is a template if `params` is non-empty

    ordering is used to put the modules in a deterministic order
    """
    ALIAS = "module"
    GROUP = GROUP.Statement
    FLAGS = NF.GLOBAL_SYM_DEF | NF.MODNAME_ANNOTATED | NF.SYMTAB
    #
    params_mod: list[NODES_PARAMS_MOD_T]
    body_mod: list[NODES_BODY_MOD_T]
    #
    doc: str = ""
    builtin: bool = False
    #
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN
    x_modname: str = ""  # unique name for code gen, derived from path
    x_symtab: Any = None

    def __repr__(self):
        params = ', '.join(str(p) for p in self.params_mod)
        return f"{NODE_NAME(self)}{_FLAGS(self)} {self.x_modname} [{params}]"
############################################################
# Macro Like
############################################################


@NodeCommon
@dataclasses.dataclass()
class ExprSrcLoc:
    """Source Location encoded as u32"""
    ALIAS = "src_loc"
    GROUP = GROUP.Expression
    FLAGS = NF.TO_BE_EXPANDED | NF.NON_CORE | NF_EXPR
    #
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN


@NodeCommon
@dataclasses.dataclass()
class ExprStringify:
    """Human readable representation of the expression

    This is useful to implement for assert like features
    """
    ALIAS = "stringify"
    GROUP = GROUP.Expression
    FLAGS = NF.TO_BE_EXPANDED | NF.NON_CORE | NF_EXPR
    #
    expr:  NODES_EXPR_T
    # the next two are not really used since node gets replaced with string
    x_type: CanonType = NO_TYPE
    x_value: Optional[Any] = None
    #
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN

############################################################
# Macro
############################################################


@NodeCommon
@dataclasses.dataclass()
class MacroId:
    """Placeholder for a parameter

    This node will be expanded with the actual argument
    """
    ALIAS = "macro_id"
    GROUP = GROUP.Macro
    FLAGS = NF.NON_CORE | NF.ROLE_ANNOTATED
    #
    name: str

    #
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN
    x_role: MACRO_PARAM_KIND = MACRO_PARAM_KIND.INVALID

    def __repr__(self):
        return f"{NODE_NAME(self)} {self.name}"


@NodeCommon
@dataclasses.dataclass()
class MacroVar:
    """Macro Variable definition whose name stems from a macro parameter or macro_gen_id"

    `name` must start with a `$`.

    """
    ALIAS = "mlet"
    GROUP = GROUP.Macro
    FLAGS = NF.TYPE_ANNOTATED | NF.LOCAL_SYM_DEF | NF.MACRO_BODY_ONLY | NF.NON_CORE
    #
    name: str
    type_or_auto: NODES_TYPES_OR_AUTO_T
    initial_or_undef_or_auto: NODES_EXPR_T
    #
    mut: bool = False
    ref: bool = False
    doc: str = ""
    #
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN

    def __repr__(self):
        return f"{NODE_NAME(self)}{_FLAGS(self)} {self.name} {self.initial_or_undef_or_auto}"


@NodeCommon
@dataclasses.dataclass()
class MacroFor:
    """Macro for-loop like statement

    loops over the macro parameter `name_list` which must be a list and
    binds each list element to `name` while expanding the AST nodes in `body_for`.
    """
    ALIAS = "mfor"
    GROUP = GROUP.Macro
    FLAGS = NF.MACRO_BODY_ONLY | NF.NON_CORE
    #
    name: str
    name_list: str
    body_for: list[Any]
    #
    doc: str = ""
    #
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN


@NodeCommon
@dataclasses.dataclass()
class MacroParam:
    """Macro Parameter"""
    ALIAS = "mparam"
    GROUP = GROUP.Macro
    FLAGS = NF.LOCAL_SYM_DEF | NF.NON_CORE
    #
    name: str
    macro_param_kind: MACRO_PARAM_KIND
    #
    doc: str = ""
    #
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN

    def __repr__(self):
        return f"{NODE_NAME(self)} {self.name} {self.macro_param_kind.name}"


@NodeCommon
@dataclasses.dataclass()
class MacroInvoke:
    """Macro Invocation"""
    ALIAS = "macro_invoke"
    GROUP = GROUP.Macro
    FLAGS = NF.TO_BE_EXPANDED | NF.NON_CORE | NF.IMPORT_ANNOTATED | NF.ROLE_ANNOTATED
    #
    name: str
    args: list[NODES_EXPR_T]
    #
    doc: str = ""
    #
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN
    x_import: Import = INVALID_IMPORT
    x_role: MACRO_PARAM_KIND = MACRO_PARAM_KIND.INVALID

    def __repr__(self):
        return f"{NODE_NAME(self)} {self.name}"


@NodeCommon
@dataclasses.dataclass()
class DefMacro:
    """Define a macro

    A macro consists of
    * a name
    * the type of AST node (list) it create
    * a parameter list. A parameter name must start with a '$'
    * a list of additional identifiers used by the macro (also starimg with '$')
    * a body containing both regular and macro specific AST node serving as a template
    """
    ALIAS = "macro"
    GROUP = GROUP.Statement
    FLAGS = NF.GLOBAL_SYM_DEF | NF.TOP_LEVEL | NF.NON_CORE
    #
    name: str
    macro_result_kind: MACRO_PARAM_KIND
    params_macro: list[NODES_PARAMS_MACRO_T]
    gen_ids: list[str]
    body_macro: list[Any]  # new scope
    #
    pub: bool = False
    doc: str = ""
    #
    x_srcloc: SrcLoc = SRCLOC_UNKNOWN

    def __repr__(self):
        return f"{NODE_NAME(self)} {self.name}"


BINOP_BOOL = {
    BINARY_EXPR_KIND.GE,
    BINARY_EXPR_KIND.GT,
    BINARY_EXPR_KIND.LE,
    BINARY_EXPR_KIND.LT,
    BINARY_EXPR_KIND.EQ,
    BINARY_EXPR_KIND.NE,
    BINARY_EXPR_KIND.ANDSC,
    BINARY_EXPR_KIND.ORSC,
}

BINOP_OPS_HAVE_SAME_TYPE = {
    BINARY_EXPR_KIND.GE,
    BINARY_EXPR_KIND.GT,
    BINARY_EXPR_KIND.LE,
    BINARY_EXPR_KIND.LT,
    BINARY_EXPR_KIND.EQ,
    BINARY_EXPR_KIND.NE,
    #
    BINARY_EXPR_KIND.ADD,
    BINARY_EXPR_KIND.SUB,
    BINARY_EXPR_KIND.MUL,
    BINARY_EXPR_KIND.DIV,
    BINARY_EXPR_KIND.MOD,
    BINARY_EXPR_KIND.MIN,
    BINARY_EXPR_KIND.MAX,
    #
    BINARY_EXPR_KIND.ANDSC,
    BINARY_EXPR_KIND.ORSC,
    #
    BINARY_EXPR_KIND.SHL,
    BINARY_EXPR_KIND.SHR,
    #
    BINARY_EXPR_KIND.AND,
    BINARY_EXPR_KIND.OR,
    BINARY_EXPR_KIND.XOR,
}


############################################################
#
############################################################
def VisitAstRecursively(node, visitor, field=None):
    if visitor(node, field):
        return

    for f, nfd in node.__class__.FIELDS:
        if nfd.kind is NFK.NODE:
            child = getattr(node, f)
            VisitAstRecursively(child, visitor, f)
        elif nfd.kind is NFK.LIST:
            for child in getattr(node, f):
                VisitAstRecursively(child, visitor, f)


def VisitAstRecursivelyWithParent(node, visitor, parent, field=None):
    if visitor(node, parent, field):
        return

    for f, nfd in node.__class__.FIELDS:
        if nfd.kind is NFK.NODE:
            child = getattr(node, f)
            VisitAstRecursivelyWithParent(child, visitor, node, f)
        elif nfd.kind is NFK.LIST:
            for child in getattr(node, f):
                VisitAstRecursivelyWithParent(child, visitor, node, f)


def VisitAstRecursivelyPost(node, visitor, field=None):
    for f, nfd in node.__class__.FIELDS:
        if nfd.kind is NFK.NODE:
            child = getattr(node, f)
            VisitAstRecursivelyPost(child, visitor, f)
        elif nfd.kind is NFK.LIST:
            for child in getattr(node, f):
                VisitAstRecursivelyPost(child, visitor, f)

    visitor(node, field)


def VisitAstRecursivelyWithAllParents(node, parents: list[Any], visitor):
    if visitor(node, parents):
        return
    parents.append(node)
    for c, nfd in node.__class__.FIELDS:
        if nfd.kind is NFK.NODE:
            VisitAstRecursivelyWithAllParents(
                getattr(node, c), parents, visitor)
        elif nfd.kind is NFK.LIST:
            for child in getattr(node, c):
                VisitAstRecursivelyWithAllParents(child, parents, visitor)
    parents.pop(-1)


def MaybeReplaceAstRecursively(node, replacer):
    """Note: the root node will not be replaced"""
    for f, nfd in node.__class__.FIELDS:
        if nfd.kind is NFK.NODE:
            child = getattr(node, f)
            new_child = replacer(child, node, f)
            if new_child:
                setattr(node, f, new_child)
            else:
                MaybeReplaceAstRecursively(child, replacer)
        elif nfd.kind is NFK.LIST:
            children = getattr(node, f)
            for n, child in enumerate(children):
                new_child = replacer(child, node, f)
                if new_child:
                    children[n] = new_child
                else:
                    MaybeReplaceAstRecursively(child, replacer)


def MaybeReplaceAstRecursivelyPost(node, replacer):
    """Note: the root node will not be replaced"""
    for f, nfd in node.__class__.FIELDS:
        # print ("replace: ", node.__class__.__name__, c)
        if nfd.kind is NFK.NODE:
            child = getattr(node, f)
            MaybeReplaceAstRecursivelyPost(child, replacer)
            new_child = replacer(child, node, f)
            if new_child:
                setattr(node, f, new_child)
        elif nfd.kind is NFK.LIST:
            children = getattr(node, f)
            for n, child in enumerate(children):
                MaybeReplaceAstRecursivelyPost(child, replacer)
                new_child = replacer(child, node, f)
                if new_child:
                    children[n] = new_child


def _MaybeFlattenEphemeralList(nodes: list[Any]):
    has_ephemeral = False
    for n in nodes:
        if isinstance(n, EphemeralList):
            has_ephemeral = True
            break
    if not has_ephemeral:
        return nodes
    out = []
    for c in nodes:
        if isinstance(c, EphemeralList):
            out += _MaybeFlattenEphemeralList(c.args)
        else:
            out.append(c)
    return out


def EliminateEphemeralsRecursively(node):
    for f, nfd in node.__class__.FIELDS:
        if nfd.kind is NFK.NODE:
            child = getattr(node, f)
            if isinstance(child, EphemeralList):
                new_child = _MaybeFlattenEphemeralList([child])
                assert len(
                    new_child) == 1, f"{f} {node.__class__} {len(new_child)}"
                setattr(node, f, new_child[0])
            EliminateEphemeralsRecursively(child)
        elif nfd.kind is NFK.LIST:
            children = getattr(node, f)
            new_children = _MaybeFlattenEphemeralList(children)
            if new_children is not children:
                setattr(node, f, new_children)
            for child in children:
                EliminateEphemeralsRecursively(child)


def CloneNodeRecursively(node, var_map, block_map):
    clone = dataclasses.replace(node)
    if isinstance(clone, DefVar):
        var_map[node] = clone
    elif isinstance(clone, (StmtBlock, ExprStmt)):
        block_map[node] = clone

    if NF.SYMBOL_ANNOTATED in clone.FLAGS:
        clone.x_symbol = var_map.get(clone.x_symbol, clone.x_symbol)
    if NF.CONTROL_FLOW in clone.FLAGS:
        clone.x_taget = var_map.get(clone.x_target, clone.x_target)
    for f, nfd in node.__class__.FIELDS:
        if nfd.kind is NFK.NODE:
            setattr(clone, f, CloneNodeRecursively(
                getattr(node, f), var_map, block_map))
        elif nfd.kind is NFK.LIST:
            out = [CloneNodeRecursively(cc, var_map, block_map)
                   for cc in getattr(node, f)]
            setattr(clone, f, out)
    return clone


############################################################
# Helpers
############################################################
def AnnotateRoleForMacroInvoke(node, parent=None, field=""):
    """Some nodes can play multiple role. Determine which one.

    This is useful if we do not have symbol information (x_symbol)
    but want to pretty print the code
    """

    def visitor(node, parent, field: str):
        if not isinstance(node, (MacroInvoke, MacroId)):
            return
        if isinstance(parent, EphemeralList):
            if parent.colon:
                node.x_role = MACRO_PARAM_KIND.STMT
            else:
                node.x_role = MACRO_PARAM_KIND.EXPR
        else:
            nfd = ALL_FIELDS_MAP[field]
            assert nfd.kind in (NFK.NODE, NFK.LIST)
            if nfd.role is MACRO_PARAM_KIND.STMT_LIST:
                node.x_role = MACRO_PARAM_KIND.STMT
            elif nfd.role is MACRO_PARAM_KIND.TYPE:
                node.x_role = MACRO_PARAM_KIND.TYPE
            else:
                node.x_role = MACRO_PARAM_KIND.EXPR

    VisitAstRecursivelyWithParent(node, visitor, parent, field)


def AnnotateImportsForQualifers(mod: DefMod):
    """Set the x_import field.

    We do this even for unqualified names using a `dummy_import`.
    This is important for macros whose
    syntax tree might get copied into a different from where it originated.
    """
    imports: dict[str, Import] = {}
    dummy_import = Import("$self", "", [], x_module=mod)

    def visitor(node, _):
        nonlocal imports, dummy_import
        if isinstance(node, Import):
            name = node.name
            if name in imports:
                CompilerError(node.x_srcloc, f"duplicate import {name}")
            imports[name] = node
        if isinstance(node, (Id, DefFun, MacroInvoke)):
            q = _GetQualifierIfPresent(node.name)
            if q:
                # only polymorphic functions may have qualifiers
                if isinstance(node, DefFun):
                    assert node.is_polymorphic()
                if q not in imports:
                    CompilerError(node.x_srcloc, f"unkown module {q}")
                node.x_import = imports[q]
            else:
                node.x_import = dummy_import

    VisitAstRecursivelyPost(mod, visitor)


def StripFromListRecursively(node, cls):
    for f, nfd in node.__class__.FIELDS:
        if nfd.kind is NFK.NODE:
            child = getattr(node, f)
            StripFromListRecursively(child, cls)
        elif nfd.kind is NFK.LIST:
            children = getattr(node, f)
            for child in children:
                StripFromListRecursively(child, cls)
            new_children = [c for c in children if not isinstance(c, cls)]
            if len(new_children) != len(children):
                setattr(node, f, new_children)


############################################################
# AST Checker
############################################################
ASSERT_AFTER_ERROR = True

# message format follows:
# https://learn.microsoft.com/en-us/visualstudio/msbuild/msbuild-diagnostic-format-for-tasks


def CompilerError(srcloc, msg, kind='syntax') -> NoReturn:
    global ASSERT_AFTER_ERROR
    print(f"{srcloc}: error {kind}: {msg}", file=sys.stdout)
    if ASSERT_AFTER_ERROR:
        # this will enit a stack trace which is the main purpose
        assert False
    exit(1)


def _CheckMacroRecursively(node, seen_names: set[str]):
    def visitor(node, _):
        if isinstance(node, (MacroParam, MacroFor)):
            assert node.name.startswith("$")
            assert node.name not in seen_names, f"duplicate name: {node.name}"
            seen_names.add(node.name)
    VisitAstRecursively(node, visitor)


def _IsPermittedNode(node, permitted, parent, toplevel_node, node_mod: DefMod,
                     allow_type_auto: bool) -> bool:
    if node.__class__.__name__ in permitted:
        return True
    if isinstance(node, MacroInvoke):
        # this could be made stricter, i.e. only for exprs and stmts
        return True
    if isinstance(node, TypeAuto):
        return allow_type_auto
    if isinstance(node, MacroId):
        return isinstance(toplevel_node, DefMacro) or node_mod.params_mod

    if isinstance(parent, (MacroInvoke, EphemeralList)):
        return True  # refine
    if isinstance(toplevel_node, DefMacro):
        return True  # refine
    return False


def CheckAST(node_mod: DefMod, disallowed_nodes, allow_type_auto=False, pre_symbolize=False):
    """
    This check is run at various stages of compilation.

    `disallowed_nodes` contains a set of nodes that must not appear.

    `pre_symbolize` indicates that the check is running before symbolization so
    that the field `x_modname` is not yet set.


    """
    # this only works with pre-order traversal
    toplevel_node = None

    def visitor(node, parent, field):
        nonlocal disallowed_nodes
        nonlocal toplevel_node
        nonlocal node_mod
        nonlocal pre_symbolize
        # print (f"@@@@ field={field}: {node.__class__.__name__}")

        if type(node) in disallowed_nodes:
            CompilerError(
                node.x_srcloc, f"Disallowed node: {type(node)} in {toplevel_node}")

        assert isinstance(
            node.x_srcloc, SrcLoc) and node.x_srcloc != SRCLOC_UNKNOWN, f"Node without srcloc node {node} for parent={parent} field={field} {node.x_srcloc}"

        if NF.TOP_LEVEL in node.FLAGS:
            if field != "body_mod":
                CompilerError(
                    node.x_srcloc, f"only allowed at toplevel [{field}]: {node}")
            toplevel_node = node
        if NF.MACRO_BODY_ONLY in node.FLAGS:
            assert isinstance(
                toplevel_node, DefMacro), f"only allowed in macros: {node}"
        if node.GROUP is GROUP.Ephemeral:
            assert isinstance(
                toplevel_node, DefMacro), f"only allowed in macros: {node}"
        if isinstance(node, DefMacro):
            if not node.name.endswith("#") and node.name not in BUILT_IN_MACROS:
                CompilerError(
                    node.x_srcloc, f"macro name must end with `#`: {node.name}")
            for p in node.params_macro:
                if isinstance(p, MacroParam):
                    assert p.name.startswith("$")
            for i in node.gen_ids:
                assert i.startswith("$")
            _CheckMacroRecursively(node, set())
        elif isinstance(node, Id):
            # when we synthesize Ids later we do not bother with x_import anymore
            if not pre_symbolize:
                assert node.x_symbol is not None or isinstance(
                    node.x_import, Import), f"{node} without x_import"
            if node.name.startswith("$"):
                CompilerError(node.x_srcloc, f"{node} start with $")
        elif isinstance(node, MacroId):
            assert node.name.startswith("$")
        elif isinstance(node, MacroInvoke):
            if not pre_symbolize:
                assert isinstance(node.x_import, Import)
        elif isinstance(node, Import):
            if not pre_symbolize:
                assert isinstance(node.x_module, DefMod)
        elif isinstance(node, DefMod):
            if not pre_symbolize:
                assert node.x_modname, f"missing x_modname {node}"
        if field is not None:
            nfd = ALL_FIELDS_MAP[field]
            if not _IsPermittedNode(node, nfd.node_type, parent, toplevel_node,
                                    node_mod,
                                    allow_type_auto):
                CompilerError(
                    node.x_srcloc, f"unexpected node for field={field}: {node.__class__.__name__}")

    VisitAstRecursivelyWithParent(node_mod, visitor, None)


##########################################################################################
# Doc Generation
##########################################################################################
PROLOG = """## Abstract Syntax Tree (AST) Nodes used by Cwerg

"""


def _RenderKindSimple(name, kind, fout):
    print(f"\n### {name} Kind\n", file=fout)
    print("|Kind|", file=fout)
    print("|----|", file=fout)
    for x in kind:
        if x is kind.INVALID:
            continue
        print(f"|{x.name:10}|", file=fout)


def _RenderKind(name, kind, inv, fout):
    print(f"\n### {name} Kind\n", file=fout)
    print("|Kind|Abbrev|", file=fout)
    print("|----|------|", file=fout)
    for x in kind:
        if x is kind.INVALID:
            continue
        assert x in inv, f"No custom name defined for emnum {x}"
        print(f"|{x.name:10}|{inv[x]}|", file=fout)


def MakeAnchor(name, alias):
    out = name.lower()
    if alias:
        out += "-" + alias
    tab = str.maketrans(" ", "-", "?,^&=@#$%")
    return out.lower().translate(tab)


def GenerateDocumentation(fout):
    print(PROLOG, file=fout)
    nodes = sorted((node.__name__, node) for node in ALL_NODES)
    print("""
## Node Overview (Core)

Core nodes are the ones that are known to the code generator.
""",  file=fout)
    n = 0
    for name, cls in nodes:
        if NF.NON_CORE in cls.FLAGS:
            continue
        n += 1
        alias = ""
        if cls.ALIAS:
            alias = f"&nbsp;({cls.ALIAS})"
        anchor = MakeAnchor(name, cls.ALIAS)
        print(f"[{name}{alias}](#{anchor}) &ensp;", file=fout)
    print(f"({n} nodes)", file=fout)

    print("""
## Node Overview (Non-Core)

Non-core nodes are syntactic sugar and will be eliminated before
code generation.
""",  file=fout)
    n = 0
    for name, cls in nodes:
        if NF.NON_CORE not in cls.FLAGS:
            continue
        n += 1
        alias = ""
        if cls.ALIAS:
            alias = f"&nbsp;({cls.ALIAS})"
        anchor = MakeAnchor(name, cls.ALIAS)
        print(f"[{name}{alias}](#{anchor}) &ensp;", file=fout)
    print(f"({n} nodes)", file=fout)

    print("""
## Enum Overview

Misc enums used inside of nodes.
""",  file=fout)
    for cls in ["Expr1", "Expr2", "StmtCompoundAssignment", "Base Type",
                "ModParam", "MacroParam"]:
        name = cls + " Kind"
        anchor = MakeAnchor(name, None)
        print(f"[{name}](#{anchor}) &ensp;", file=fout)

    nodes = sorted((node.GROUP, node.__name__, node) for node in ALL_NODES)
    last_group = ""
    for group, name, cls in nodes:
        if last_group != group:
            print(f"\n## {group.name} Node Details",  file=fout)
            last_group = group
        print("", file=fout)
        alias = ""
        if cls.ALIAS:
            alias = f" ({cls.ALIAS})"
        print(f"### {name}{alias}", file=fout)

        print(cls.__doc__,  file=fout)

        if NF.TOP_LEVEL in cls.FLAGS:
            print("", file=fout)
            print("Allowed at top level only", file=fout)
        if len(cls.__annotations__):
            print("", file=fout)
            print("Fields:",  file=fout)

            for field, nfd in cls.FIELDS:
                kind = nfd.kind
                extra = ""
                optional_val = GetOptional(field, 0)
                if optional_val is not None:
                    if optional_val == "":
                        extra = ' (default "")'
                    elif isinstance(optional_val, ValNum):
                        extra = f' (default {optional_val.number})'
                    else:
                        extra = f' (default {optional_val.__class__.__name__})'
                print(f"* {field} [{kind.name}]{extra}: {nfd.doc}", file=fout)
            if cls.ATTRS:
                print("", file=fout)
                print("Flags:",  file=fout)
                for field, nfd in cls.ATTRS:
                    print(f"* {field}: {nfd.doc}", file=fout)
            print("", file=fout)

    print("## Enum Details",  file=fout)

    _RenderKind(Expr1.__name__,  UNARY_EXPR_KIND,
                UNARY_EXPR_SHORTCUT_INV, fout)
    _RenderKind(Expr2.__name__,  BINARY_EXPR_KIND,
                BINARY_EXPR_SHORTCUT_INV, fout)
    _RenderKind(ExprPointer.__name__, POINTER_EXPR_KIND,
                POINTER_EXPR_SHORTCUT_INV, fout)
    _RenderKind(StmtCompoundAssignment.__name__,
                ASSIGNMENT_KIND, ASSIGNMENT_SHORTCUT_INV, fout)
    _RenderKindSimple("Base Type",
                      BASE_TYPE_KIND, fout)
    _RenderKindSimple("ModParam",
                      MOD_PARAM_KIND, fout)
    _RenderKindSimple("MacroParam",
                      MACRO_PARAM_KIND, fout)


##########################################################################################
if __name__ == "__main__":
    logging.basicConfig(level=logging.WARN)
    logger.setLevel(logging.INFO)
    GenerateDocumentation(sys.stdout)
