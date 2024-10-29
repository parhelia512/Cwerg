## Abstract Syntax Tree (AST) Nodes used by Cwerg



## Node Overview (Core)

Core nodes are the ones that are known to the code generator.

[DefEnum&nbsp;(enum)](#defenum-enum) &ensp;
[DefFun&nbsp;(fun)](#deffun-fun) &ensp;
[DefGlobal&nbsp;(global)](#defglobal-global) &ensp;
[DefMod&nbsp;(module)](#defmod-module) &ensp;
[DefRec&nbsp;(defrec)](#defrec-defrec) &ensp;
[DefType&nbsp;(type)](#deftype-type) &ensp;
[DefVar&nbsp;(let)](#defvar-let) &ensp;
[EnumVal&nbsp;(entry)](#enumval-entry) &ensp;
[Expr1](#expr1) &ensp;
[Expr2](#expr2) &ensp;
[ExprAddrOf&nbsp;(&)](#expraddrof-) &ensp;
[ExprAs&nbsp;(as)](#expras-as) &ensp;
[ExprBitCast&nbsp;(bitwise_as)](#exprbitcast-bitwise_as) &ensp;
[ExprCall&nbsp;(call)](#exprcall-call) &ensp;
[ExprDeref&nbsp;(^)](#exprderef-) &ensp;
[ExprField&nbsp;(.)](#exprfield-.) &ensp;
[ExprFront&nbsp;(front)](#exprfront-front) &ensp;
[ExprNarrow&nbsp;(narrow_as)](#exprnarrow-narrow_as) &ensp;
[ExprPointer](#exprpointer) &ensp;
[ExprStmt&nbsp;(expr)](#exprstmt-expr) &ensp;
[ExprUnsafeCast&nbsp;(unsafe_as)](#exprunsafecast-unsafe_as) &ensp;
[ExprUnwrap&nbsp;(unwrap)](#exprunwrap-unwrap) &ensp;
[ExprWiden&nbsp;(widen_as)](#exprwiden-widen_as) &ensp;
[ExprWrap&nbsp;(wrap_as)](#exprwrap-wrap_as) &ensp;
[FieldVal&nbsp;(field_val)](#fieldval-field_val) &ensp;
[FunParam&nbsp;(param)](#funparam-param) &ensp;
[Id&nbsp;(id)](#id-id) &ensp;
[IndexVal&nbsp;(index_val)](#indexval-index_val) &ensp;
[RecField&nbsp;(field)](#recfield-field) &ensp;
[StmtAssignment&nbsp;(=)](#stmtassignment-) &ensp;
[StmtBlock&nbsp;(block)](#stmtblock-block) &ensp;
[StmtBreak&nbsp;(break)](#stmtbreak-break) &ensp;
[StmtContinue&nbsp;(continue)](#stmtcontinue-continue) &ensp;
[StmtExpr&nbsp;(do)](#stmtexpr-do) &ensp;
[StmtIf&nbsp;(if)](#stmtif-if) &ensp;
[StmtReturn&nbsp;(return)](#stmtreturn-return) &ensp;
[StmtTrap&nbsp;(trap)](#stmttrap-trap) &ensp;
[TypeArray&nbsp;(array)](#typearray-array) &ensp;
[TypeAuto&nbsp;(auto)](#typeauto-auto) &ensp;
[TypeBase](#typebase) &ensp;
[TypeFun&nbsp;(sig)](#typefun-sig) &ensp;
[TypePtr&nbsp;(ptr)](#typeptr-ptr) &ensp;
[TypeUnion&nbsp;(union)](#typeunion-union) &ensp;
[ValArray&nbsp;(array_val)](#valarray-array_val) &ensp;
[ValAuto&nbsp;(auto_val)](#valauto-auto_val) &ensp;
[ValFalse&nbsp;(false)](#valfalse-false) &ensp;
[ValNum&nbsp;(num)](#valnum-num) &ensp;
[ValRec&nbsp;(rec_val)](#valrec-rec_val) &ensp;
[ValString](#valstring) &ensp;
[ValTrue&nbsp;(true)](#valtrue-true) &ensp;
[ValUndef&nbsp;(undef)](#valundef-undef) &ensp;
[ValVoid&nbsp;(void_val)](#valvoid-void_val) &ensp;
(52 nodes)

## Node Overview (Non-Core)

Non-core nodes are syntactic sugar and will be eliminated before
code generation.

[Case&nbsp;(case)](#case-case) &ensp;
[DefMacro&nbsp;(macro)](#defmacro-macro) &ensp;
[EphemeralList](#ephemerallist) &ensp;
[Expr3&nbsp;(?)](#expr3-) &ensp;
[ExprIndex&nbsp;(at)](#exprindex-at) &ensp;
[ExprIs&nbsp;(is)](#expris-is) &ensp;
[ExprLen&nbsp;(len)](#exprlen-len) &ensp;
[ExprOffsetof&nbsp;(offset_of)](#exproffsetof-offset_of) &ensp;
[ExprParen&nbsp;(paren)](#exprparen-paren) &ensp;
[ExprSizeof&nbsp;(size_of)](#exprsizeof-size_of) &ensp;
[ExprSrcLoc&nbsp;(src_loc)](#exprsrcloc-src_loc) &ensp;
[ExprStringify&nbsp;(stringify)](#exprstringify-stringify) &ensp;
[ExprTypeId&nbsp;(typeid_of)](#exprtypeid-typeid_of) &ensp;
[ExprUnionTag&nbsp;(union_tag)](#expruniontag-union_tag) &ensp;
[ExprUnionUntagged&nbsp;(union_untagged)](#exprunionuntagged-union_untagged) &ensp;
[Import&nbsp;(import)](#import-import) &ensp;
[MacroFor&nbsp;(mfor)](#macrofor-mfor) &ensp;
[MacroId&nbsp;(macro_id)](#macroid-macro_id) &ensp;
[MacroInvoke&nbsp;(macro_invoke)](#macroinvoke-macro_invoke) &ensp;
[MacroParam&nbsp;(mparam)](#macroparam-mparam) &ensp;
[MacroVar&nbsp;(mlet)](#macrovar-mlet) &ensp;
[ModParam&nbsp;(modparam)](#modparam-modparam) &ensp;
[StmtCompoundAssignment](#stmtcompoundassignment) &ensp;
[StmtCond&nbsp;(cond)](#stmtcond-cond) &ensp;
[StmtDefer&nbsp;(defer)](#stmtdefer-defer) &ensp;
[StmtStaticAssert&nbsp;(static_assert)](#stmtstaticassert-static_assert) &ensp;
[TypeOf&nbsp;(type_of)](#typeof-type_of) &ensp;
[TypeSlice&nbsp;(slice)](#typeslice-slice) &ensp;
[TypeUnionDelta&nbsp;(uniondelta)](#typeuniondelta-uniondelta) &ensp;
[ValSlice&nbsp;(slice_val)](#valslice-slice_val) &ensp;
(30 nodes)

## Enum Overview

Misc enums used inside of nodes.

[Expr1 Kind](#expr1-kind) &ensp;
[Expr2 Kind](#expr2-kind) &ensp;
[StmtCompoundAssignment Kind](#stmtcompoundassignment-kind) &ensp;
[Base Type Kind](#base-type-kind) &ensp;
[ModParam Kind](#modparam-kind) &ensp;
[MacroParam Kind](#macroparam-kind) &ensp;

## Misc Node Details

### Id (id)
Refers to a type, variable, constant, function, module by name.

    Ids may contain a path component indicating which modules they reference.
    If the path component is missing the Id refers to the current module.

    

Fields:
* name [STR]: name of the object


## Type Node Details

### DefEnum (enum)
Enum definition

Allowed at top level only

Fields:
* name [STR]: name of the object
* base_type_kind [KIND]: one of: [SINT, S8, S16, S32, S64, UINT, U8, U16, U32, U64, R32, R64, VOID, NORET, BOOL, TYPEID](#base-type-kind)
* items [LIST]: enum items and/or comments

Flags:
* pub: has public visibility
* doc: possibly multi-line comment


### DefRec (defrec)
Record definition

Allowed at top level only

Fields:
* name [STR]: name of the object
* fields [LIST]: record fields and/or comments

Flags:
* pub: has public visibility
* doc: possibly multi-line comment


### EnumVal (entry)
 Enum element.

     `value: ValAuto` means previous value + 1

Fields:
* name [STR]: name of the object
* value_or_auto [NODE] (default ValAuto): enum constant or auto

Flags:
* doc: possibly multi-line comment


### FunParam (param)
Function parameter

    

Fields:
* name [STR]: name of the object
* type [NODE]: type expression

Flags:
* arg_ref: in parameter was converted for by-val to pointer
* res_ref: in parameter was converted for by-val to pointer
* doc: possibly multi-line comment


### RecField (field)
Record field

    All fields must be explicitly initialized. Use `ValUndef` in performance
    sensitive situations.
    

Fields:
* name [STR]: name of the object
* type [NODE]: type expression

Flags:
* doc: possibly multi-line comment


### TypeArray (array)
An array of the given type and `size`

    

Fields:
* size [NODE]: compile-time constant size
* type [NODE]: type expression


### TypeAuto (auto)
Placeholder for an unspecified (auto derived) type

    My only occur where explicitly allowed.
    

Fields:


### TypeBase
Base type

    One of: void, bool, r32, r64, u8, u16, u32, u64, s8, s16, s32, s64
    

Fields:
* base_type_kind [KIND]: one of: [SINT, S8, S16, S32, S64, UINT, U8, U16, U32, U64, R32, R64, VOID, NORET, BOOL, TYPEID](#base-type-kind)


### TypeFun (sig)
A function signature

    The `FunParam.name` field is ignored and should be `_`
    

Fields:
* params [LIST]: function parameters and/or comments
* result [NODE]: return type


### TypeOf (type_of)
Type of the expression
    

Fields:
* expr [NODE]: expression


### TypePtr (ptr)
Pointer type
    

Fields:
* type [NODE]: type expression

Flags:
* mut: is mutable


### TypeSlice (slice)
A view/slice of an array with compile-time unknown dimensions

    Internally, this is tuple of `start` and `length`
    (mutable/non-mutable)
    

Fields:
* type [NODE]: type expression

Flags:
* mut: is mutable


### TypeUnion (union)
Union types (tagged unions)

    Unions are "auto flattening", e.g.
    Union(a, Union(b,c), Union(a, d)) = Union(a, b, c, d)
    

Fields:
* types [LIST]: union types

Flags:
* untagged: union type is untagged


### TypeUnionDelta (uniondelta)
Type resulting from the difference of TypeUnion and a non-empty subset sets of its members
    

Fields:
* type [NODE]: type expression
* subtrahend [NODE]: type expression


## Statement Node Details

### Case (case)
Single case of a Cond statement

Fields:
* cond [NODE]: conditional expression must evaluate to a boolean
* body [LIST]: new scope: statement list and/or comments

Flags:
* doc: possibly multi-line comment


### DefFun (fun)
Function definition

    `init` and `fini` indicate module initializer/finalizers

    `extern` indicates a prototype and hence the function body must be empty.

    `cdecl` disables name mangling

    `ref`  fun may be assigned to a variable (i.e. its address may be taken)
     

Allowed at top level only

Fields:
* name [STR]: name of the object
* params [LIST]: function parameters and/or comments
* result [NODE]: return type
* body [LIST]: new scope: statement list and/or comments

Flags:
* init: run function at startup
* fini: run function at shutdown
* pub: has public visibility
* ref: address may be taken
* extern: is external function (empty body)
* cdecl: use c-linkage (no module prefix)
* doc: possibly multi-line comment


### DefGlobal (global)
Variable definition at global scope (DefVar is used for local scope)

    Allocates space in static memory and initializes it with `initial_or_undef`.
    `mut` makes the allocated space read/write otherwise it is readonly.
    

Allowed at top level only

Fields:
* name [STR]: name of the object
* type_or_auto [NODE]: type expression
* initial_or_undef_or_auto [NODE] (default ValAuto): initializer

Flags:
* pub: has public visibility
* mut: is mutable
* ref: address may be taken
* cdecl: use c-linkage (no module prefix)
* doc: possibly multi-line comment


### DefMacro (macro)
Define a macro

    A macro consists of
    * a name
    * the type of AST node (list) it create
    * a parameter list. A parameter name must start with a '$'
    * a list of additional identifiers used by the macro (also starimg with '$')
    * a body containing both regular and macro specific AST node serving as a template
    

Allowed at top level only

Fields:
* name [STR]: name of the object
* macro_result_kind [KIND]: one of: [ID, STMT_LIST, EXPR_LIST, EXPR, STMT, FIELD, TYPE, EXPR_LIST_REST](#MacroParam-kind)
* params_macro [LIST]: macro parameters
* gen_ids [STR_LIST]: name placeholder ids to be generated at macro instantiation time
* body_macro [LIST]: new scope: macro statments/expression

Flags:
* pub: has public visibility
* doc: possibly multi-line comment


### DefMod (module)
Module Definition

    The module is a template if `params` is non-empty

    ordering is used to put the modules in a deterministic order
    

Fields:
* params_mod [LIST]: module template parameters
* body_mod [LIST]: toplevel module definitions and/or comments

Flags:
* doc: possibly multi-line comment
* builtin: module is the builtin module


### DefType (type)
Type definition

    A `wrapped` gives the underlying type a new name that is not type compatible.
    To convert between the two use an `as` cast expression.
    

Allowed at top level only

Fields:
* name [STR]: name of the object
* type [NODE]: type expression

Flags:
* pub: has public visibility
* wrapped: is wrapped type (forces type equivalence by name)
* doc: possibly multi-line comment


### DefVar (let)
Variable definition at local scope (DefGlobal is used for global scope)

    Allocates space on stack (or in a register) and initializes it with `initial_or_undef_or_auto`.
    `mut` makes the allocated space read/write otherwise it is readonly.
    `ref` allows the address of the  variable to be taken and prevents register allocation.

    

Fields:
* name [STR]: name of the object
* type_or_auto [NODE]: type expression
* initial_or_undef_or_auto [NODE] (default ValAuto): initializer

Flags:
* mut: is mutable
* ref: address may be taken
* doc: possibly multi-line comment


### Import (import)
Import another Module from `path` as `name`

Fields:
* name [STR]: name of the object
* path [STR] (default ""): TBD
* args_mod [LIST] (default list): module arguments

Flags:
* doc: possibly multi-line comment


### ModParam (modparam)
Module Parameters

Fields:
* name [STR]: name of the object
* mod_param_kind [KIND]: one of: [CONST_EXPR, TYPE](#modparam-kind)

Flags:
* doc: possibly multi-line comment


### StmtAssignment (=)
Assignment statement

Fields:
* lhs [NODE]: l-value expression
* expr_rhs [NODE]: rhs of assignment

Flags:
* doc: possibly multi-line comment


### StmtBlock (block)
Block statement.

    if `label` is non-empty, nested break/continue statements can target this `block`.
    

Fields:
* label [STR]: block  name (if not empty)
* body [LIST]: new scope: statement list and/or comments

Flags:
* doc: possibly multi-line comment


### StmtBreak (break)
Break statement

    use "" if the target is the nearest for/while/block 

Fields:
* target [STR] (default ""): name of enclosing while/for/block to brach to (empty means nearest)

Flags:
* doc: possibly multi-line comment


### StmtCompoundAssignment
Compound assignment statement

    Note: this does not support pointer inc/dec
    

Fields:
* assignment_kind [KIND]: one of: [ADD, SUB, DIV, MUL, MOD, MIN, MAX, AND, OR, XOR, SHR, SHL, ROTR, ROTL](#stmtcompoundassignment-kind)
* lhs [NODE]: l-value expression
* expr_rhs [NODE]: rhs of assignment

Flags:
* doc: possibly multi-line comment


### StmtCond (cond)
Multicase if-elif-else statement

Fields:
* cases [LIST]: list of case statements

Flags:
* doc: possibly multi-line comment


### StmtContinue (continue)
Continue statement

    use "" if the target is the nearest for/while/block 

Fields:
* target [STR] (default ""): name of enclosing while/for/block to brach to (empty means nearest)

Flags:
* doc: possibly multi-line comment


### StmtDefer (defer)
Defer statement

    Note: defer body's containing return statments have
    non-straightforward semantics.
    

Fields:
* body [LIST]: new scope: statement list and/or comments

Flags:
* doc: possibly multi-line comment


### StmtExpr (do)
Expression statement

    Turns an expression (typically a call) into a statement
    

Fields:
* expr [NODE]: expression

Flags:
* doc: possibly multi-line comment


### StmtIf (if)
If statement

Fields:
* cond [NODE]: conditional expression must evaluate to a boolean
* body_t [LIST]: new scope: statement list and/or comments for true branch
* body_f [LIST]: new scope: statement list and/or comments for false branch

Flags:
* doc: possibly multi-line comment


### StmtReturn (return)
Return statement

    Returns from the first enclosing ExprStmt node or the enclosing DefFun node.
    Uses void_val if the DefFun's return type is void
    

Fields:
* expr_ret [NODE] (default ValVoid): result expression (ValVoid means no result)

Flags:
* doc: possibly multi-line comment


### StmtStaticAssert (static_assert)
Static assert statement (must evaluate to true at compile-time

Allowed at top level only

Fields:
* cond [NODE]: conditional expression must evaluate to a boolean
* message [STR] (default ""): message for assert failures

Flags:
* doc: possibly multi-line comment


### StmtTrap (trap)
Trap statement

Fields:

Flags:
* doc: possibly multi-line comment


## Value Node Details

### FieldVal (field_val)
Part of rec literal

    e.g. `.imag = 5`
    If field is empty use `first field` or `next field`.
    

Fields:
* value_or_undef [NODE]: 
* init_field [STR] (default ""): initializer field or empty (empty means next field)

Flags:
* doc: possibly multi-line comment


### IndexVal (index_val)
Part of an array literal

    e.g. `.1 = 5`
    If index is auto use `0` or `previous index + 1`.
    

Fields:
* value_or_undef [NODE]: 
* init_index [NODE] (default ValAuto): initializer index or empty (empty mean next index)

Flags:
* doc: possibly multi-line comment


### ValArray (array_val)
An array literal

    `[10]int{.1 = 5, .2 = 6, 77}`

    `expr_size` must be constant or auto
    

Fields:
* expr_size [NODE]: expression determining the size or auto
* type [NODE]: type expression
* inits_array [LIST] (default list): array initializers and/or comments

Flags:
* doc: possibly multi-line comment


### ValAuto (auto_val)
Placeholder for an unspecified (auto derived) value

    Used for: array dimensions, enum values, chap and range
    

Fields:


### ValFalse (false)
Bool constant `false`

Fields:


### ValNum (num)
Numeric constant (signed int, unsigned int, real

    Underscores in `number` are ignored. `number` can be explicitly typed via
    suffices like `_u64`, `_s16`, `_r32`.
    

Fields:
* number [STR]: a number


### ValRec (rec_val)
A record literal

    `E.g.: complex{.imag = 5, .real = 1}`
    

Fields:
* type [NODE]: type expression
* inits_field [LIST]: record initializers and/or comments

Flags:
* doc: possibly multi-line comment


### ValSlice (slice_val)
A slice value comprised of a pointer and length

    type and mutability is defined by the pointer
    

Fields:
* pointer [NODE]: pointer component of slice
* expr_size [NODE]: expression determining the size or auto


### ValString
An array value encoded as a string

    type is `[strlen(string)]u8`. `string` may be escaped/raw
    

Fields:
* string [STR]: string literal
* strkind [INTERNAL_STR]: raw: ignore escape sequences in string, hex:
* triplequoted [INTERNAL_BOOL]: string is using 3 double quotes


### ValTrue (true)
Bool constant `true`

Fields:


### ValUndef (undef)
Special constant to indiciate *no default value*
    

Fields:


### ValVoid (void_val)
Only value inhabiting the `TypeVoid` type

    It can be used to model *null* in nullable pointers via a union type.
     

Fields:


## Expression Node Details

### Expr1
Unary expression.

Fields:
* unary_expr_kind [KIND]: one of: [NOT, MINUS](#expr1-kind)
* expr [NODE]: expression


### Expr2
Binary expression.

Fields:
* binary_expr_kind [KIND]: one of: [ADD, SUB, DIV, MUL, MOD, MIN, MAX, AND, OR, XOR, EQ, NE, LT, LE, GT, GE, ANDSC, ORSC, SHR, SHL, ROTR, ROTL, PDELTA](#expr2-kind)
* expr1 [NODE]: left operand expression
* expr2 [NODE]: right operand expression


### Expr3 (?)
Tertiary expression (like C's `? :`)
    

Fields:
* cond [NODE]: conditional expression must evaluate to a boolean
* expr_t [NODE]: expression (will only be evaluated if cond == true)
* expr_f [NODE]: expression (will only be evaluated if cond == false)


### ExprAddrOf (&)
Create a pointer to object represented by `expr`

    Pointer can optionally point to a mutable object if the
    pointee is mutable.
    

Fields:
* expr_lhs [NODE]: l-value expression

Flags:
* mut: is mutable


### ExprAs (as)
Safe Cast (Conversion)

    Allowed:
    u8-u64, s8-s64 <-> u8-u64, s8-s64
    u8-u64, s8-s64 -> r32-r64  (note: one way only)
    

Fields:
* expr [NODE]: expression
* type [NODE]: type expression


### ExprBitCast (bitwise_as)
Bit cast.

    Type must have same size and alignment as type of item

    s32,u32,f32 <-> s32,u32,f32
    s64,u64, f64 <-> s64,u64, f64
    sint, uint <-> ptr

    It is also ok to bitcase complex objects like recs
    

Fields:
* expr [NODE]: expression
* type [NODE]: type expression


### ExprCall (call)
Function call expression.
    

Fields:
* callee [NODE]: expression evaluating to the function to be called
* args [LIST]: function call arguments


### ExprDeref (^)
Dereference a pointer represented by `expr`

Fields:
* expr [NODE]: expression


### ExprField (.)
Access field in expression representing a record.
    

Fields:
* container [NODE]: array and slice
* field [STR]: record field


### ExprFront (front)
Address of the first element of an array or slice

    Similar to `(& (at container 0))` but will not fail if container has zero size
    

Fields:
* container [NODE]: array and slice

Flags:
* mut: is mutable


### ExprIndex (at)
Optionally unchecked indexed access of array or slice
    

Fields:
* container [NODE]: array and slice
* expr_index [NODE]: expression determining the index to be accessed

Flags:
* unchecked: array acces is not checked


### ExprIs (is)
Test actual expression (run-time) type

    Typically used when `expr` is a tagged union type.
    Otherwise, the node can be constant folded.

    `type` can be a tagged union itself.
    

Fields:
* expr [NODE]: expression
* type [NODE]: type expression


### ExprLen (len)
Length of array or slice

    Result type is `uint`.
    

Fields:
* container [NODE]: array and slice


### ExprNarrow (narrow_as)
Narrowing Cast (for unions)

    optionally unchecked
    

Fields:
* expr [NODE]: expression
* type [NODE]: type expression

Flags:
* unchecked: array acces is not checked


### ExprOffsetof (offset_of)
Byte offset of field in record types

    Result has type `uint`

Fields:
* type [NODE]: type expression
* field [STR]: record field


### ExprParen (paren)
Used for preserving parenthesis in the source
    

Fields:
* expr [NODE]: expression


### ExprPointer
Pointer arithmetic expression - optionally bound checked..

Fields:
* pointer_expr_kind [KIND]: one of: [INCP, DECP](#pointerop-kind)
* expr1 [NODE]: left operand expression
* expr2 [NODE]: right operand expression
* expr_bound_or_undef [NODE] (default ValUndef): 


### ExprSizeof (size_of)
Byte size of type

    Result has type is `uint`

Fields:
* type [NODE]: type expression


### ExprSrcLoc (src_loc)
Source Location encoded as u32

Fields:


### ExprStmt (expr)
Expr with Statements

    The body statements must be terminated by a StmtReturn
    

Fields:
* body [LIST]: new scope: statement list and/or comments


### ExprStringify (stringify)
Human readable representation of the expression

    This is useful to implement for assert like features
    

Fields:
* expr [NODE]: expression


### ExprTypeId (typeid_of)
TypeId of type

    Result has type is `typeid`

Fields:
* type [NODE]: type expression


### ExprUnionTag (union_tag)
Typetag of tagged union type

    result has type is `typeid`

Fields:
* expr [NODE]: expression


### ExprUnionUntagged (union_untagged)
Untagged union portion of tagged union type

    Result has type untagged union

Fields:
* expr [NODE]: expression


### ExprUnsafeCast (unsafe_as)
Unsafe Cast

    Allowed:
    ptr a <-> ptr b

    

Fields:
* expr [NODE]: expression
* type [NODE]: type expression


### ExprUnwrap (unwrap)
Cast: enum/wrapped -> underlying type
    

Fields:
* expr [NODE]: expression


### ExprWiden (widen_as)
Widening Cast (for unions)

    Usually this is implicit
    

Fields:
* expr [NODE]: expression
* type [NODE]: type expression


### ExprWrap (wrap_as)
Cast: underlying type -> enum/wrapped
    

Fields:
* expr [NODE]: expression
* type [NODE]: type expression


## Macro Node Details

### EphemeralList
Only exist temporarily after a replacement strep

    will removed (flattened) in the next cleanup list
    

Fields:
* args [LIST]: function call arguments

Flags:
* colon: colon style list


### MacroFor (mfor)
Macro for-loop like statement

    loops over the macro parameter `name_list` which must be a list and
    binds each list element to `name` while expanding the AST nodes in `body_for`.
    

Fields:
* name [STR]: name of the object
* name_list [STR]: name of the object list
* body_for [LIST]: statement list for macro_loop

Flags:
* doc: possibly multi-line comment


### MacroId (macro_id)
Placeholder for a parameter

    This node will be expanded with the actual argument
    

Fields:
* name [STR]: name of the object


### MacroInvoke (macro_invoke)
Macro Invocation

Fields:
* name [STR]: name of the object
* args [LIST]: function call arguments

Flags:
* doc: possibly multi-line comment


### MacroParam (mparam)
Macro Parameter

Fields:
* name [STR]: name of the object
* macro_param_kind [KIND]: one of: [ID, STMT_LIST, EXPR_LIST, EXPR, STMT, FIELD, TYPE, EXPR_LIST_REST](#MacroParam-kind)

Flags:
* doc: possibly multi-line comment


### MacroVar (mlet)
Macro Variable definition whose name stems from a macro parameter or macro_gen_id"

    `name` must start with a `$`.

    

Fields:
* name [STR]: name of the object
* type_or_auto [NODE]: type expression
* initial_or_undef_or_auto [NODE] (default ValAuto): initializer

Flags:
* mut: is mutable
* ref: address may be taken
* doc: possibly multi-line comment

## Enum Details

### Expr1 Kind

|Kind|Abbrev|
|----|------|
|NOT       |!|
|MINUS     |~|

### Expr2 Kind

|Kind|Abbrev|
|----|------|
|ADD       |+|
|SUB       |-|
|DIV       |/|
|MUL       |*|
|MOD       |%|
|MIN       |min|
|MAX       |max|
|AND       |and|
|OR        |or|
|XOR       |xor|
|EQ        |==|
|NE        |!=|
|LT        |<|
|LE        |<=|
|GT        |>|
|GE        |>=|
|ANDSC     |&&|
|ORSC      ||||
|SHR       |>>|
|SHL       |<<|
|ROTR      |>>>|
|ROTL      |<<<|
|PDELTA    |&-&|

### ExprPointer Kind

|Kind|Abbrev|
|----|------|
|INCP      |pinc|
|DECP      |pdec|

### StmtCompoundAssignment Kind

|Kind|Abbrev|
|----|------|
|ADD       |+=|
|SUB       |-=|
|DIV       |/=|
|MUL       |*=|
|MOD       |%=|
|MIN       |min=|
|MAX       |max=|
|AND       |and=|
|OR        |or=|
|XOR       |xor=|
|SHR       |>>=|
|SHL       |<<=|
|ROTR      |>>>=|
|ROTL      |<<<=|

### Base Type Kind

|Kind|
|----|
|SINT      |
|S8        |
|S16       |
|S32       |
|S64       |
|UINT      |
|U8        |
|U16       |
|U32       |
|U64       |
|R32       |
|R64       |
|VOID      |
|NORET     |
|BOOL      |
|TYPEID    |

### ModParam Kind

|Kind|
|----|
|CONST_EXPR|
|TYPE      |

### MacroParam Kind

|Kind|
|----|
|ID        |
|STMT_LIST |
|EXPR_LIST |
|EXPR      |
|STMT      |
|FIELD     |
|TYPE      |
|EXPR_LIST_REST|
