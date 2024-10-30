#!/bin/env python3
"""
Assembler produces A64 ELF executables
"""
import argparse
import os
import stat
import sys
from typing import Dict, Any

from BE.CpuX64 import assembler as asm


def lint(input):
    src = sys.stdin if input == "-" else open(input)
    print("UNIT", asm.UnitParse(src))


def assemble_common(input, output):
    src = sys.stdin if input == "-" else open(input)
    dst = sys.stdout if output == "-" else open(output, "wb")
    unit = asm.UnitParse(src)
    for sym in unit.symbols:
        assert sym.section, f"undefined symbol: {sym}"

    # print(unit)
    exe = asm.Assemble(unit, True)
    # for phdr in exe.segments:
    #    print(phdr)
    #    for sec in phdr.sections:
    #        print(sec)
    print("WRITING EXE")
    exe.save(dst)
    if output != "-":
        os.chmod(output, stat.S_IREAD | stat.S_IEXEC | stat.S_IWRITE)


def assemble(input, output):
    assemble_common(input, output)


def main():
    parser = argparse.ArgumentParser(description='assembler_tool')
    subparsers = parser.add_subparsers(dest='subparser')

    parser_lint = subparsers.add_parser(
        'lint', description='just parse the input and print result')
    parser_lint.add_argument('input', type=str, help='input file')

    parser_assemble = subparsers.add_parser(
        'assemble',
        description='parse and emit elf exe. Also add _start entry point calling main')
    parser_assemble.add_argument('input', type=str, help='input file')
    parser_assemble.add_argument('output', type=str, help='output file')

    # First extract all the parser members into a dict
    kwargs: Dict[str, Any] = vars(parser.parse_args())

    # Next invoke the proper handler which is derived from the subparser
    # name. E.g. subparser `assembler_raw` is handled by the Python
    # function assembler_raw()
    handler = globals().get(kwargs.pop('subparser'))
    if handler:
        handler(**kwargs)
    else:
        parser.print_help(sys.stderr)


if __name__ == '__main__':
    main()
