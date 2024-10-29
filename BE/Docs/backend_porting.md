## How to add a new back to Cwerg?

This document sketches Cwerg's approach to the implementation of the existing backends
 (A32/A64). The same strategy should work for other fixed width instruction sets
 like RISC V.
 
 The process is divided into the following steps
 1. Implement an instruction encode/decoder for the target ISA
 2. Implement the code/instruction selector which expands Cwerg IR instructions in to target
    instructions.
 
 
 ### Target Instruction Encoder/Decoder
 
See also [A32 README.md](../CpuA32) and [A64 README.md](../CpuA64)

Cwerg aims to be self-contained, resource-efficient and simple.
Because of this we eschew the creation of a separate symbolic assembler and generate 
target instructions directly in binary form.

Not having a symbolic assembler means:
* we need to deal with relocations ourselves and hence we try to limit the 
  relocations types in the code selection stage as much as possible
* we need to disambiguate the (pseudo) instructions and addressing modes 
  that look similar in the "official" symbolic notation of the ISA but are wildly
  different in their binary encoding
  
While not strictly necessary all existing backends implement a decoder and handle
far more opcodes han necessary for the code selection stage.  

Having a decoder is nice because it:
* allows us to test the encoder more easily 
* helps leverage a lot of work that went into `objdump` (see below)
* helps with the processing of relocations

Our approach follow this playbook starting with the CpuXXX support

1.  Run `objdump -d <exe>` on several large executables built for the target 
    architecture. `firefox` is a good candidate.
    The lines produced will look like this:
    `2086c:    e0815005        add     r5, r1, #666`
    The first (hex) number is the address (which can be ignored). The second number 
    is the hex encoding of the instruction. The rest is the symbolic form of
    instruction. 
2.  Write a decode for all the hex encodings listed by `objdump -d` into a raw form, e.g.
    and enum identifying the opcode and a sequence of operands (integers copied out of 
    the instructions word.).
3.  Write a symbolizer that renders the intermediate representation produced by
    the decoder to symbolic form. 
4.  Write some quick and dirty tests verifying that this symbolic form is roughly
    equivalent to symbolic form emitted by `objdump -d`.
5.  Write the encoder which converts the immediate representation back to hex
    encoding - both for the symbolic and raw representation.
6.  Write an assembler_tool which converts simple textual programs (hello world 
    with syscalls) into working ELF-executables. Make an initial guess for what 
    relocation types will definitely needed and support/test those. 
    Even if the executable is working, make sure it is well-formed by inspecting
    it with `readelf`/`objdump`.

Next up is the Codegen support in CodeGenXXX
 
1.  Start implementing simple patterns in `isel_tab.py` and test them via
    `isel_tester.py` 
2.  Make a barebones hello-world work (e.g. CodeGenX64/TestData/syscall.x64.asm)
    which does not require much in terms of relocations, control flow and register allocation.
3. Make a slightly more sophisticated program work (e.g. CodeGenX64/TestData/cli)
 
For the current backends the intermediate representation consists of an enum
representing the opcode, e.g. `OPC_add` and an array of numbers representing,
the operands, e.g.  `[5, 1, 666]` for `[r5, r1, #666]`.

The maximum number of operands is bounded by a small number and we limit the 
representation of each operand to a 32bit number to keep the representation compact.

As hinted above the size of the opcode enum is larger than the number of 
opcodes listed the target architecture reference manual as we require that each 
opcode have fixed operand types.
For example:
`add r5, r1, #666` and `add r5, r1, r5` will have different opcode because they
differ in the type of the last operand (immediate vs register).

The composition of operand types for each opcode is described by a table which is also 
used to encode/decode each operand. Since an operand is represented by 
a 32bit number this allows for some processing that will simplify the
symbolization of the instruction. For example the bit pattern in the instruction
encoding representing the destination register `r5` will be decoded to the value `5`.
(We know that 5 represents a register because the opcode uniquely definsd the type
of each operand.) This processing can only go so far. For example, if an operand
represents a 64 bit immediate we cannot decode it to its full representation as
it may not fit into 32 bits.

TODO: add a few more detail about ELF and relocations

### Code Selector

See also [A32 README.md](../CodeGenA32) and [A64 README.md](../CodeGenA64)

TODO: finish this section

[Compiler Explorer](godbolt.org) is your friend. If that is not available the next
best thing is running:
```
target-cc -c -o test.o test.c
target-objdump -d test.o
```

 


  


