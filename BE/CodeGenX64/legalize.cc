// (c) Robert Muth - see LICENSE for more info

#include <algorithm>
#include <iomanip>

#include "BE/Base/canonicalize.h"
#include "BE/Base/cfg.h"
#include "BE/Base/liveness.h"
#include "BE/Base/lowering.h"
#include "BE/Base/optimize.h"
#include "BE/Base/sanity.h"
#include "BE/Base/serialize.h"
#include "BE/CodeGenX64/isel_gen.h"
#include "BE/CodeGenX64/regs.h"

namespace cwerg::code_gen_x64 {
namespace {

using namespace cwerg;
using namespace cwerg::base;

// +-prefix converts an enum the underlying integer type
template <typename T>
constexpr auto operator+(T e) noexcept
    -> std::enable_if_t<std::is_enum<T>::value, std::underlying_type_t<T>> {
  return static_cast<std::underlying_type_t<T>>(e);
}

bool IsOutOfBoundImmediate(OPC opc, Handle op, unsigned pos) {
  if (op.kind() != RefKind::CONST) return false;
  const DK dk = ConstKind(Const(op));
  if (DKFlavor(dk) == DK_FLAVOR_F) return true;
  switch (opc) {
    case OPC::MOV:
      return false;
    case OPC::DIV:
    case OPC::REM:
    case OPC::MUL:
    case OPC::CNTLZ:
    case OPC::CNTTZ:
    case OPC::CONV:
      return true;
    case OPC::ST:
    case OPC::ST_STK:
    case OPC::ST_MEM:
      if (pos == 2) return true;
      break;
    default:
      break;
  }

  switch (dk) {
    case DK::S8:
    case DK::S16:
    case DK::S32:
    case DK::S64:
    case DK::A64:
    case DK::C64: {
      int64_t x = ConstValueInt64(Const(op));
      return x < -(1LL << 31) || (1LL << 31) <= x;
    }
    case DK::U8:
    case DK::U16:
    case DK::U32:
    case DK::U64: {
      uint64_t x = ConstValueU(Const(op));
      return (1UL << 31) <= x;
    }
    default:
      break;
  }
  ASSERT(false, "");
  return true;
}

bool MaybeRewrite(OPC_KIND kind) {
  switch (kind) {
    case OPC_KIND::ALU:
    case OPC_KIND::ALU1:
    case OPC_KIND::COND_BRA:
    case OPC_KIND::CONV:
    case OPC_KIND::MOV:
    case OPC_KIND::ST:
      return true;
    default:
      return false;
  }
}

void FunRewriteOutOfBoundsImmediates(Fun fun, Unit unit,
                                     std::vector<Ins>* inss) {
  for (Bbl bbl : FunBblIter(fun)) {
    inss->clear();
    bool dirty = false;
    for (Ins ins : BblInsIter(bbl)) {
      if (MaybeRewrite(InsOpcode(ins).kind)) {
        const unsigned n = InsOpcode(ins).num_operands;
        for (unsigned pos = 0; pos < n; ++pos) {
          if (!IsOutOfBoundImmediate(InsOPC(ins), InsOperand(ins, pos), pos))
            continue;
          const DK kind = ConstKind(Const(InsOperand(ins, pos)));
          if (kind == DK::R64 || kind == DK::R32) {
            InsEliminateImmediateViaMem(ins, pos, fun, unit, DK::A64, DK::U32,
                                        inss);
          } else {
            InsEliminateImmediateViaMov(ins, pos, fun, inss);
          }
          dirty = true;
        }
      }
      inss->push_back(ins);
    }
    if (dirty) BblReplaceInss(bbl, *inss);
  }
}

void FunRewriteDivRemShiftsCAS(Fun fun, Unit unit, std::vector<Ins>* inss) {
  for (Bbl bbl : FunBblIter(fun)) {
    inss->clear();
    bool dirty = false;
    for (Ins ins : BblInsIter(bbl)) {
      if (InsOpcode(ins).kind == OPC_KIND::ALU ||
          InsOpcode(ins).kind == OPC_KIND::CAS) {
        const DK dk = RegKind(Reg(InsOperand(ins, 0)));
        if (DKFlavor(dk) != DK_FLAVOR_F) {
          switch (InsOPC(ins)) {
            case OPC::DIV: {
              Reg rax = FunFindOrAddCpuReg(fun, GPR_REGS[0], dk);
              Reg rcx = FunFindOrAddCpuReg(fun, GPR_REGS[1], dk);
              Reg rdx = FunFindOrAddCpuReg(fun, GPR_REGS[2], dk);
              inss->push_back(InsNew(OPC::MOV, rax, InsOperand(ins, 1)));
              inss->push_back(InsNew(OPC::MOV, rcx, InsOperand(ins, 2)));
              inss->push_back(ins);
              inss->push_back(InsNew(OPC::MOV, InsOperand(ins, 0), rax));
              InsInit(ins, OPC::DIV, rdx, rax, rcx);
              dirty = true;
              continue;
            }
            case OPC::REM: {
              Reg rax = FunFindOrAddCpuReg(fun, GPR_REGS[0], dk);
              Reg rcx = FunFindOrAddCpuReg(fun, GPR_REGS[1], dk);
              Reg rdx = FunFindOrAddCpuReg(fun, GPR_REGS[2], dk);
              inss->push_back(InsNew(OPC::MOV, rax, InsOperand(ins, 1)));
              inss->push_back(InsNew(OPC::MOV, rcx, InsOperand(ins, 2)));
              inss->push_back(ins);
              inss->push_back(InsNew(OPC::MOV, InsOperand(ins, 0), rdx));
              // Note, this relies on tight coupling with the isel which will
              // pick the x86 div instruction the computes both the dividend and
              // remainder
              InsInit(ins, OPC::DIV, rdx, rax, rcx);
              dirty = true;
              continue;
            }
            case OPC::CAS:
            case OPC::CAS_MEM:
            case OPC::CAS_STK: {
              Reg rax = FunFindOrAddCpuReg(fun, GPR_REGS[0], dk);
              inss->push_back(InsNew(OPC::MOV, rax, InsOperand(ins, 1)));
              inss->push_back(ins);
              inss->push_back(InsNew(OPC::MOV, InsOperand(ins, 0), rax));
              InsOperand(ins, 0) = rax;
              InsOperand(ins, 1) = rax;
              dirty = true;
              continue;
            }
            case OPC::SHL:
            case OPC::SHR: {
              const unsigned bw = DKBitWidth(dk);
              const unsigned mask = bw - 1;

              if (InsOperand(ins, 2).kind() == RefKind::REG) {
                Const const_mask = DKFlavor(dk) == DK_FLAVOR_U
                                       ? ConstNewU(dk, mask)
                                       : ConstNewACS(dk, mask);
                Reg rcx = FunFindOrAddCpuReg(fun, GPR_REGS[1], dk);
                inss->push_back(InsNew(OPC::MOV, rcx, InsOperand(ins, 2)));

                inss->push_back(InsNew(OPC::AND, rcx, rcx, const_mask));
                inss->push_back(ins);
                InsOperand(ins, 2) = rcx;
              } else {
                Const op_shift = Const(InsOperand(ins, 2));
                ASSERT(op_shift.kind() == RefKind::CONST, "");
                if (DKFlavor(dk) == DK_FLAVOR_U) {
                  InsOperand(ins, 2) =
                      ConstNewU(dk, ConstValueU(op_shift) & mask);
                } else {
                  InsOperand(ins, 2) =
                      ConstNewACS(dk, ConstValueACS(op_shift) & mask);
                }
                inss->push_back(ins);
              }
              dirty = true;
              continue;
            }
            default:
              break;
          }
        }
      }
      inss->push_back(ins);
    }
    if (dirty) BblReplaceInss(bbl, *inss);
  }
}

int FunMoveEliminationCpu(Fun fun, std::vector<Ins>* to_delete) {
  to_delete->clear();

  for (Bbl bbl : FunBblIter(fun)) {
    for (Ins ins : BblInsIter(bbl)) {
      OPC opc = InsOPC(ins);
      if (opc == OPC::MOV) {
        Reg dst(InsOperand(ins, 0));
        Reg src(InsOperand(ins, 1));
        if (src.kind() == RefKind::REG && RegCpuReg(src) == RegCpuReg(dst)) {
          to_delete->push_back(ins);
        }
      }
    }
  }

  for (Ins ins : *to_delete) {
    BblInsUnlink(ins);
    InsDel(ins);
  }
  return to_delete->size();
}

bool InsNeedsAABFormRewrite(Ins ins) {
  OPC_KIND kind = InsOpcode(ins).kind;
  OPC opc = InsOPC(ins);
  if (kind != OPC_KIND::ALU && kind != OPC_KIND::LEA) {
    return false;
  }
  if ((opc == OPC::DIV || opc == OPC::DIV) &&
      DKFlavor(RegKind(Reg(InsOperand(ins, 0)))) != DK_FLAVOR_F) {
    return false;
  }
  if (opc == OPC::LEA_MEM || opc == OPC::LEA_STK) {
    return false;
  }
  return true;
}

void FunRewriteIntoAABForm(Fun fun, std::vector<Ins>* inss) {
  for (Bbl bbl : FunBblIter(fun)) {
    inss->clear();
    bool dirty = false;
    for (Ins ins : BblInsIter(bbl)) {
      if (InsNeedsAABFormRewrite(ins)) {
        const Reg first = Reg(InsOperand(ins, 0));

        if (InsOperand(ins, 0) == InsOperand(ins, 1)) {
          RegFlags(first) |= +REG_FLAG::TWO_ADDRESS;
        } else if (InsOperand(ins, 0) == InsOperand(ins, 2) &&
                   InsOpcode(ins).HasAttribute(OA::COMMUTATIVE)) {
          InsSwapOps(ins, 1, 2);
          RegFlags(first) |= +REG_FLAG::TWO_ADDRESS;
        } else {
          dirty = true;
          const Reg reg = FunGetScratchReg(fun, RegKind(first), "aab", false);
          RegFlags(reg) |= +REG_FLAG::TWO_ADDRESS;
          inss->push_back(InsNew(OPC::MOV, reg, InsOperand(ins, 1)));
          inss->push_back(ins);
          inss->push_back(InsNew(OPC::MOV, InsOperand(ins, 0), reg));
          InsInit(ins, InsOPC(ins), reg, reg, InsOperand(ins, 2));
          continue;
        }
      }
      inss->push_back(ins);
    }
    if (dirty) BblReplaceInss(bbl, *inss);
  }
}

// Return all global regs in `fun` that map to `rk` after applying `rk_map`
// and whose `lac-ness` matches `is_lac`
void FunFilterGlobalRegs(Fun fun, CPU_REG_KIND rk, bool is_lac,
                         const DK_MAP& rk_map, std::vector<Reg>* out) {
  for (Reg reg : FunRegIter(fun)) {
    if (RegHasFlag(reg, REG_FLAG::GLOBAL) && RegCpuReg(reg).isnull() &&
        RegHasFlag(reg, REG_FLAG::LAC) == is_lac &&
        rk_map[+RegKind(reg)] == +rk) {
      out->push_back(reg);
    }
  }
}

bool SpillingNeeded(const FunRegStats& needed, unsigned num_regs_lac,
                    unsigned num_regs_not_lac) {
  return needed.global_lac + needed.local_lac > num_regs_lac ||
         needed.global_lac + needed.local_lac + needed.global_not_lac +
                 needed.local_not_lac >
             num_regs_lac + num_regs_not_lac;
}

// This assumes that at least count bits are set.
uint32_t FindMaskCoveringTheLowOrderSetBits(uint32_t bits, unsigned count) {
  if (count == 0) return 0;
  uint32_t mask = 1;
  unsigned n = 0;
  while (n < count) {
    if ((mask & bits) != 0) ++n;
    mask <<= 1U;
  }
  return mask - 1;
}

struct PoolMasks {
  uint32_t mask_lac;
  uint32_t mask_not_lac;
};

PoolMasks GetRegPoolsForGlobals(const FunRegStats& needed, uint32_t regs_lac,
                                uint32_t regs_not_lac,
                                uint32_t regs_preallocated) {
  unsigned num_regs_lac = __builtin_popcount(regs_lac);
  unsigned num_regs_not_lac = __builtin_popcount(regs_not_lac);
  bool spilling_needed = SpillingNeeded(needed, num_regs_lac, num_regs_not_lac);

  uint32_t global_lac = regs_lac;
  uint32_t local_lac = 0;
  if (num_regs_lac > needed.global_lac) {
    const uint32_t mask =
        FindMaskCoveringTheLowOrderSetBits(global_lac, needed.global_lac);
    local_lac = global_lac & ~mask;
    global_lac = global_lac & mask;
  }

  uint32_t global_not_lac = 0;
  if (num_regs_not_lac > needed.local_not_lac + spilling_needed) {
    const uint32_t mask = FindMaskCoveringTheLowOrderSetBits(
        regs_not_lac, needed.local_not_lac + spilling_needed);
    global_not_lac = regs_not_lac & ~(mask | regs_preallocated);
  }

  if (__builtin_popcount(local_lac) > needed.local_lac) {
    const uint32_t mask =
        FindMaskCoveringTheLowOrderSetBits(local_lac, needed.local_lac);
    global_not_lac |= local_lac & ~mask;
  }
  return PoolMasks{global_lac, global_not_lac};
}

}  // namespace

void PhaseLegalization(Fun fun, Unit unit, std::ostream* fout) {
  if (fout != nullptr) {
    *fout << "############################################################\n"
          << "# Legalize " << Name(fun) << "\n"
          << "############################################################\n";
  }
  std::vector<Ins> inss;
  FunSetInOutCpuRegs(fun, *PushPopInterfaceX64);

  if (FunKind(fun) != FUN_KIND::NORMAL) return;
  FunPushargConversion(fun, *PushPopInterfaceX64);
  FunPopargConversion(fun, *PushPopInterfaceX64);

  FunEliminateStkLoadStoreWithRegOffset(fun, DK::A64, DK::S32, &inss);
  FunEliminateMemLoadStore(fun, DK::A64, DK::S32, &inss);

  FunEliminateCopySign(fun, &inss);
  FunEliminateCmp(fun, &inss);

  FunCanonicalize(fun);
  // We need to run this before massaging immediates because it changes
  // COND_RRA instruction possibly with immediates.
  FunCfgExit(fun);
  FunRewriteOutOfBoundsImmediates(fun, unit, &inss);
  // FunRenderToAsm(fun, fout);

  FunRewriteDivRemShiftsCAS(fun, unit, &inss);
  FunRewriteIntoAABForm(fun, &inss);
  //
  FunComputeRegStatsExceptLAC(fun);
  FunDropUnreferencedRegs(fun);
  FunNumberReg(fun);
  FunComputeLivenessInfo(fun);
  FunComputeRegStatsLAC(fun);
  FunSeparateLocalRegUsage(fun);
}

void DumpRegStats(Fun fun, const DK_LAC_COUNTS& stats, std::ostream* output) {
  unsigned local_lac = 0;
  unsigned local_not_lac = 0;
  for (size_t i = 0; i < stats.lac.size(); ++i) {
    local_lac += stats.lac[i];
    local_not_lac += stats.not_lac[i];
  }
  std::vector<Reg> global_lac;
  std::vector<Reg> global_not_lac;
  std::vector<Reg> allocated_lac;
  std::vector<Reg> allocated_not_lac;
  for (Reg reg : FunRegIter(fun)) {
    if (!RegHasFlag(reg, REG_FLAG::GLOBAL)) continue;
    if (RegCpuReg(reg).isnull()) {
      if (RegHasFlag(reg, REG_FLAG::LAC))
        global_lac.push_back(reg);
      else
        global_not_lac.push_back(reg);
    } else {
      if (RegHasFlag(reg, REG_FLAG::LAC))
        allocated_lac.push_back(reg);
      else
        allocated_not_lac.push_back(reg);
    }
  }
  if (output != nullptr) {
    *output << "# REGSTATS " << std::left << std::setw(20) << Name(fun)
            << std::right
            << "   "
            //
            << "all: " << std::setw(2) << allocated_lac.size() << " "
            << std::setw(2) << allocated_not_lac.size()
            << "  "
            //
            << "glo: " << std::setw(2) << global_lac.size() << " "
            << std::setw(2) << global_not_lac.size()
            << "  "
            //
            << "loc: " << std::setw(2) << local_lac << " " << std::setw(2)
            << local_not_lac << "\n";
  }
}

void GlobalRegAllocOneKind(Fun fun, CPU_REG_KIND kind,
                           const FunRegStats& needed, uint32_t regs_lac,
                           uint32_t regs_not_lac, uint32_t regs_lac_mask,
                           std::vector<Reg>* regs, std::ostream* debug) {
  uint32_t pre_alloced = 0;
  for (Reg reg : FunRegIter(fun)) {
    CpuReg cpu_reg(RegCpuReg(reg));
    if (cpu_reg.kind() != RefKind::CPU_REG) continue;
    if (CPU_REG_KIND(CpuRegKind(cpu_reg)) == kind) {
      pre_alloced |= CpuRegToAllocMask(cpu_reg);
    }
  }

  auto reg_cmp = [](Reg a, Reg b) -> bool {
    return StrCmpLt(Name(a), Name(b));
  };

  if (debug)
    *debug << "@@  " << EnumToString(kind) << " " << needed.global_lac << " "
           << needed.global_not_lac << " " << needed.local_lac << " "
           << needed.local_not_lac << "\n";

  const auto [global_lac, global_not_lac] =
      GetRegPoolsForGlobals(needed, regs_lac, regs_not_lac, pre_alloced);

  if (debug)
    *debug << "@@ " << EnumToString(kind) << " POOL " << std::hex << global_lac
           << " " << global_not_lac << std::dec << "\n";

  // handle is_lac global regs
  regs->clear();
  FunFilterGlobalRegs(fun, kind, true, DK_TO_CPU_REG_KIND_MAP, regs);
  std::sort(regs->begin(), regs->end(), reg_cmp);  // make things deterministic
  AssignCpuRegOrMarkForSpilling(*regs, global_lac, 0);
  // handle not is_lac global regs
  regs->clear();
  FunFilterGlobalRegs(fun, kind, false, DK_TO_CPU_REG_KIND_MAP, regs);
  std::sort(regs->begin(), regs->end(), reg_cmp);  // make things deterministic
  AssignCpuRegOrMarkForSpilling(*regs, global_not_lac & ~regs_lac_mask,
                                global_not_lac & regs_lac_mask);
}

void PhaseGlobalRegAlloc(Fun fun, Unit unit, std::ostream* fout) {
  if (fout != nullptr) {
    *fout << "############################################################\n"
          << "# GlobalRegAlloc " << Name(fun) << "\n"
          << "############################################################\n";
  }

  std::ostream* debug = nullptr;
  std::vector<Ins> inss;
  // FunSpillRegs(fun, DK::U32, to_be_spilled, &inss, "$gspill");
  FunComputeRegStatsExceptLAC(fun);
  FunDropUnreferencedRegs(fun);
  FunNumberReg(fun);
  FunComputeLivenessInfo(fun);
  FunComputeRegStatsLAC(fun);

  const DK_LAC_COUNTS local_reg_stats =
      FunComputeBblRegUsageStats(fun, DK_TO_CPU_REG_KIND_MAP);
  const DK_LAC_COUNTS global_reg_stats =
      FunGlobalRegStats(fun, DK_TO_CPU_REG_KIND_MAP);

  if (fout != nullptr) {
    DumpRegStats(fun, local_reg_stats, fout);
  }

  std::vector<Reg> regs;
  {
    const FunRegStats needed{global_reg_stats.lac[+CPU_REG_KIND::GPR],      //
                             global_reg_stats.not_lac[+CPU_REG_KIND::GPR],  //
                             local_reg_stats.lac[+CPU_REG_KIND::GPR],       //
                             local_reg_stats.not_lac[+CPU_REG_KIND::GPR]};

    GlobalRegAllocOneKind(
        fun, CPU_REG_KIND::GPR, needed,
        GPR_REGS_MASK & GPR_LAC_REGS_MASK & ~GPR_REG_IMPLICIT_MASK,
        GPR_REGS_MASK & ~GPR_LAC_REGS_MASK & ~GPR_REG_IMPLICIT_MASK,
        GPR_LAC_REGS_MASK, &regs, debug);
  }
  {
    const FunRegStats needed{global_reg_stats.lac[+CPU_REG_KIND::FLT],
                             global_reg_stats.not_lac[+CPU_REG_KIND::FLT],
                             local_reg_stats.lac[+CPU_REG_KIND::FLT],
                             local_reg_stats.not_lac[+CPU_REG_KIND::FLT]};
    GlobalRegAllocOneKind(
        fun, CPU_REG_KIND::FLT, needed, FLT_REGS_MASK & FLT_LAC_REGS_MASK,
        FLT_REGS_MASK & ~FLT_LAC_REGS_MASK, FLT_LAC_REGS_MASK, &regs, debug);
  }
}

void PhaseFinalizeStackAndLocalRegAlloc(Fun fun, Unit unit,
                                        std::ostream* fout) {
  std::vector<Ins> inss;
  FunComputeRegStatsExceptLAC(fun);
  FunDropUnreferencedRegs(fun);
  FunNumberReg(fun);
  FunComputeLivenessInfo(fun);
  FunComputeRegStatsLAC(fun);
  FunAddNop1ForCodeSel(fun, &inss);
  FunLocalRegAlloc(fun, &inss);
  FunFinalizeStackSlots(fun);
  FunMoveEliminationCpu(fun, &inss);
}

void LegalizeAll(Unit unit, bool verbose, std::ostream* fout) {
  std::vector<Fun> seeds;
  Fun fun = UnitFunFind(unit, StrNew("main"));
  if (!fun.isnull()) seeds.push_back(fun);
  fun = UnitFunFind(unit, StrNew("_start"));
  if (!fun.isnull()) seeds.push_back(fun);
  if (!seeds.empty()) UnitRemoveUnreachableCode(unit, seeds);
  for (Fun fun : UnitFunIter(unit)) {
    FunCheck(fun);
    if (FunKind(fun) == FUN_KIND::NORMAL) {
      FunCfgInit(fun);
      FunOptBasic(fun, true);
    }

    FunCheck(fun);
    PhaseLegalization(fun, unit, fout);
  }
}

void RegAllocGlobal(Unit unit, bool verbose, std::ostream* fout) {
  for (Fun fun : UnitFunIter(unit)) {
    FunCheck(fun);
    PhaseGlobalRegAlloc(fun, unit, fout);
  }
}

void RegAllocLocal(Unit unit, bool verbose, std::ostream* fout) {
  for (Fun fun : UnitFunIter(unit)) {
    PhaseFinalizeStackAndLocalRegAlloc(fun, unit, fout);
  }
}

}  // namespace  cwerg::code_gen_x64
