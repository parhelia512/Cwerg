// (c) Robert Muth - see LICENSE for more info

#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <string_view>

#include "BE/CpuX64/opcode_gen.h"
#include "BE/CpuX64/symbolic.h"
#include "Util/assert.h"
#include "Util/parse.h"

using namespace cwerg::x64;

std::string ExtractData(std::string_view line) {
  std::string out;
  out.reserve(line.size());
  unsigned nibble;
  bool have_nibble = false;
  for (char c : line) {
    if (cwerg::IsWhiteSpace(c)) {
      if (have_nibble) {
        out.push_back(nibble);
        have_nibble = false;
      }
    } else {
      const int hex_digit = cwerg::HexDigit(c);
      ASSERT(hex_digit >= 0, "");
      if (have_nibble) {
        out.push_back((nibble << 4) | unsigned(hex_digit));
        have_nibble = false;
      } else {
        nibble = hex_digit;
        have_nibble = true;
      }
    }
  }
  if (have_nibble) {
    out.push_back(nibble);
    have_nibble = false;
  }
  return out;
}

void batch(std::string_view data, const std::string& line) {
  Ins ins;
  if (!Disassemble(&ins, data)) {
    std::cout << "could not find opcode for: " << line << "\n";
    return;
  }
  std::vector<std::string> ops;
  std::string_view enum_name = InsSymbolize(ins, true, false, &ops);
  std::cout << std::left << std::setw(30) << line << std::dec << " "
            << enum_name;
  std::string_view sep = " ";
  for (const std::string& op : ops) {
    std::cout << sep << op;
    sep = ", ";
  }
  std::cout << "\n";
}

void disass_short(const Ins& ins, const std::string& line) {
  std::vector<std::string> ops;
  std::string_view enum_name = InsSymbolize(ins, true, true, &ops);
  std::cout << line << " " << enum_name;
  std::string_view sep = " ";
  for (const std::string& op : ops) {
    std::cout << sep << op;
    sep = " ";
  }
  std::cout << "\n";
}

void disass_long(const Ins& ins, const std::string& line) {
  std::vector<std::string> ops;
  std::string_view enum_name = InsSymbolize(ins, true, false, &ops);
  std::cout << "    " << enum_name << "\n";
  for (unsigned x = 0; x < ins.opcode->num_fields; ++x) {
    int64_t v = ins.operands[x];
    char buffer[64];
    char* s = buffer;
    if (int64_t(v) < 0) {
      *s++ = '-';
      v = -v;
    }
    *s++ = '0';
    *s++ = 'x';
    ToHexString(v, s);

    std::cout << "    " << std::left << std::setw(35)
              << EnumToString(ins.opcode->fields[x]) << " " << std::setw(10)
              << ops[x] << " (" << buffer << ")\n";
  }
  std::cout << "\n";
}

void disass(std::string_view data, const std::string& line) {
  Ins ins;
  if (!Disassemble(&ins, data)) {
    std::cout << "could not disassemble " << line << std::dec << "\n";
    return;
  }
  disass_short(ins, line);
  disass_long(ins, line);
  char buffer[128];
  const uint32_t num_bytes = Assemble(ins, buffer);
  ASSERT(num_bytes == UsesRex(ins) + ins.opcode->num_bytes,
         "size mismatch " << num_bytes << " vs "
                          << UsesRex(ins) + ins.opcode->num_bytes);
  ASSERT(num_bytes == data.size(), "re-assembler size mismatch");
  /*
  for (uint32_t i = 0; i < num_bytes; ++i) {
    std::cout << std::hex << (unsigned(data[i]) & 0xff) << " "
              << (unsigned(buffer[i]) & 0xff) << "\n";
  }
  */
  for (uint32_t i = 0; i < num_bytes; ++i) {
    ASSERT(data[i] == buffer[i], "assembler byte mismatch "
                                     << std::dec << i << " " << std::hex
                                     << unsigned(data[i]) << " "
                                     << unsigned(buffer[i]));
  }
}

int main(int argc, char* argv[]) {
  if (argc <= 1) {
    std::cout << "no command specified\n";
    return 1;
  }
  if (std::string_view("batch") == argv[1]) {
    for (std::string line; getline(std::cin, line);) {
      if (line[0] == '#') continue;
      const std::string data = ExtractData(line);
      batch(data, line);
    }
  } else {
    std::string out;
    out.reserve(argc);
    for (unsigned i = 1; i < argc; ++i) {
      const std::string data = ExtractData(argv[i]);
      disass(data, argv[i]);
    }

    return 0;
  }
}
