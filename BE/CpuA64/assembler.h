#pragma once
// (c) Robert Muth - see LICENSE for more info

#include "BE/CpuA64/opcode_gen.h"
#include "BE/Elf/elfhelper.h"
#include "BE/Elf/elf_unit.h"


namespace cwerg::a64 {
using namespace cwerg;

using A64Unit = elf::Unit<uint64_t>;

// Initialize a pristine A64Unit from a textual assembly content
extern bool UnitParse(std::istream* input, A64Unit* unit);

extern void AddIns(A64Unit* unit, Ins* ins);

extern elf::Executable<uint64_t> MakeExe(A64Unit* unit, bool create_sym_tab);

extern std::ostream& operator<<(std::ostream& os, const A64Unit& s);

extern void ApplyRelocation(const elf::Reloc<uint64_t>& rel);

}  // namespace cwerg::a64
