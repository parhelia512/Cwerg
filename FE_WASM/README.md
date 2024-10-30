## WASM Frontend (Deprecated)

The WASM Frontend is primarily use to exercise the Cwerg backend with more
realistic inputs. It consists of a transpiler that
convert WASM into Cwerg IR and support libraries which will provide a WASI API.

This component is unlikely to get much love in the foreseeable future and
there will only be a Python implementation.

The [parser](parser.py) and the [instructions table](opcode_tab.py) do not have any other dependencies and might be useful by themselves.

Note: Most WASM programs and the WASI bindings require 64bit ints which currently
makes them unsuitable for A32 code generation.

### WASI Support

Currently implemented are:

* args_get
* args_sizes_get
* clock_time_get (a64 only)
* fd_fdstat_get (A64 only)
* fd_prestat_dir_name
* fd_close
* fd_write
* fd_read
* path_open (A64 open)
* proc_exit


### WebAssembly Pain Points

* provides no easy way to do printf debugging in a WASM/WAST files since strings cannot be added easily
* combines stack machine + local variables
* follows the LLVM approach of encoding operand type in opcode -> combinatorial explosion of opcode space
* no rigorous stack invariants at the end of a block, e.g. if there are unconditional branches,
  so all we can do is patch things up
* interleaving of code and tests in WAST files (TestData/test_rewriter.py
  attempts to help with that but it is adhoc and buggy)
* featuritis (e.g. upcoming support for exception handling)


### Generating WASM/WASI executables

#### Wasienv (wasmer)

https://medium.com/wasmer/wasienv-wasi-development-workflow-for-humans-1811d9a50345

provides: wasicc, wasic++, wasild in `~/.local/bin`

`wasmer <wasm-file>`  interpret wasm file (with WASI support)

### References

#### Meta

https://github.com/mbasso/awesome-wasm

#### Overview / Intro

https://mvolkmann.github.io/blog/webassembly/

https://rsms.me/wasm-intro


#### Spec

https://github.com/WebAssembly/spec

https://github.com/WebAssembly/design/blob/main/Semantics.md

#### Runtime (WASI)

* https://github.com/bytecodealliance/wasmtime
* wasi test suite https://github.com/caspervonb/wasi-test-suite
* wasi API https://github.com/WebAssembly/WASI/blob/main/phases/snapshot/docs.md#modules

https://github.com/WebAssembly/wabt

* ubuntu https://packages.ubuntu.com/search?keywords=wabt
* tests https://github.com/WebAssembly/wabt/tree/main/test/spec
* wasm2wat wasm -> wast
* wat2wasm wast -> wasm

https://github.com/WebAssembly/binaryen

* ubuntu package: https://packages.ubuntu.com/search?keywords=binaryen
* wasm-dis wasm -> wast
* wasm-as wast -> wasm
