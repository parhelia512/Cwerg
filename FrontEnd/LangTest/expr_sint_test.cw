-- expr
module:

import test

fun test_s64(a s64, b s64) void:
    test::AssertEq#(a + b, 0x9999999999999999_s64)
    test::AssertEq#(a - b, 0x7530eca97530eca9_s64)
    test::AssertEq#(a max b, 0x1234567812345678_s64)
    test::AssertEq#(a min b, 0x8765432187654321_s64)
    test::AssertEq#(a or b, 0x9775577997755779_s64)
    test::AssertEq#(a and b, 0x0224422002244220_s64)
    test::AssertEq#(a xor b, 0x9551155995511559_s64)
    test::AssertEq#(a * b, 0xeb11e7f570b88d78_s64)
    -- 
    --     (test::AssertEq# (/ a b) 0x7_u64)
    --     (test::AssertEq# (% a b) 0x7f6e5d907f6e5d9_u64)
    --     @doc ""
    --     
    test::AssertEq#(a << 0, 0x8765432187654321_s64)
    test::AssertEq#(a << 32, 0x8765432100000000_s64)
    test::AssertEq#(a << 64, 0x8765432187654321_s64)
    -- 
    test::AssertEq#(a >> 0, 0x8765432187654321_s64)
    test::AssertEq#(a >> 32, 0xffffffff87654321_s64)
    test::AssertEq#(a >> 64, 0x8765432187654321_s64)
    -- 
    test::AssertEq#(a < b, true)
    test::AssertEq#(a <= b, true)
    test::AssertEq#(a > b, false)
    test::AssertEq#(a >= b, false)
    test::AssertEq#(a == b, false)
    test::AssertEq#(a != b, true)
    -- 
    test::AssertEq#(a < a, false)
    test::AssertEq#(a <= a, true)
    test::AssertEq#(a > a, false)
    test::AssertEq#(a >= a, true)
    test::AssertEq#(a == a, true)
    test::AssertEq#(a != a, false)

fun test_s32(a s32, b s32) void:
    test::AssertEq#(a + b, 0x99999999_s32)
    test::AssertEq#(a - b, 0x7530eca9_s32)
    test::AssertEq#(a max b, 0x12345678_s32)
    test::AssertEq#(a min b, 0x87654321_s32)
    test::AssertEq#(a or b, 0x97755779_s32)
    test::AssertEq#(a and b, 0x02244220_s32)
    test::AssertEq#(a xor b, 0x95511559_s32)
    test::AssertEq#(a * b, 0x70b88d78_s32)
    -- 
    --     (test::AssertEq# (/ a b) 0x7_s32)
    --     (test::AssertEq# (% a b) 0x7f6e5d9_s32)
    --     @doc ""
    --     
    test::AssertEq#(!a, 0x789abcde_s32)
    test::AssertEq#(-a, 0x789abcdf_s32)
    -- 
    test::AssertEq#(a << 0, 0x87654321_s32)
    test::AssertEq#(a << 16, 0x43210000_s32)
    test::AssertEq#(a << 32, 0x87654321_s32)
    -- 
    test::AssertEq#(a >> 0, 0x87654321_s32)
    test::AssertEq#(a >> 16, 0xffff8765_s32)
    test::AssertEq#(a >> 32, 0x87654321_s32)
    -- 
    test::AssertEq#(a < b, true)
    test::AssertEq#(a <= b, true)
    test::AssertEq#(a > b, false)
    test::AssertEq#(a >= b, false)
    test::AssertEq#(a == b, false)
    test::AssertEq#(a != b, true)
    -- 
    test::AssertEq#(a < a, false)
    test::AssertEq#(a <= a, true)
    test::AssertEq#(a > a, false)
    test::AssertEq#(a >= a, true)
    test::AssertEq#(a == a, true)
    test::AssertEq#(a != a, false)

fun test_s16(a s16, b s16) void:
    test::AssertEq#(a + b, 0x9999_s16)
    test::AssertEq#(a - b, 0x7531_s16)
    test::AssertEq#(a max b, 0x1234_s16)
    test::AssertEq#(a min b, 0x8765_s16)
    test::AssertEq#(a or b, 0x9775_s16)
    test::AssertEq#(a and b, 0x0224_s16)
    test::AssertEq#(a xor b, 0x9551_s16)
    -- 
    --     (test::AssertEq# (* a b) 0xf4b4_s16)
    --     (test::AssertEq# (/ a b) 0x3_s16)
    --     (test::AssertEq# (% a b) 0xc85_s16)
    --     @doc ""
    --     (test::AssertEq# (! a) 0xbcde_s16)
    --     (test::AssertEq# (~ a) 0xbcdf_s16)
    --     @doc ""
    --     
    test::AssertEq#(a << 0, 0x8765_s16)
    test::AssertEq#(a << 8, 0x6500_s16)
    test::AssertEq#(a << 16, 0x8765_s16)
    -- 
    test::AssertEq#(a >> 0, 0x8765_s16)
    test::AssertEq#(a >> 8, 0xff87_s16)
    test::AssertEq#(a >> 16, 0x8765_s16)
    -- 
    test::AssertEq#(a < b, true)
    test::AssertEq#(a <= b, true)
    test::AssertEq#(a > b, false)
    test::AssertEq#(a >= b, false)
    test::AssertEq#(a == b, false)
    test::AssertEq#(a != b, true)
    -- 
    test::AssertEq#(a < a, false)
    test::AssertEq#(a <= a, true)
    test::AssertEq#(a > a, false)
    test::AssertEq#(a >= a, true)
    test::AssertEq#(a == a, true)
    test::AssertEq#(a != a, false)

fun test_s8(a s8, b s8) void:
    test::AssertEq#(a + b, 0xff_s8)
    test::AssertEq#(a - b, 0xf_s8)
    test::AssertEq#(a max b, 0x78_s8)
    test::AssertEq#(a min b, 0x87_s8)
    test::AssertEq#(a or b, 0xff_s8)
    test::AssertEq#(a and b, 0x0_s8)
    test::AssertEq#(a xor b, 0xff_s8)
    --  needs backend fixes (test::AssertEq# (* a b) 0x48_s8)
    --     (test::AssertEq# (/ a b) 0x1_s8)
    --     (test::AssertEq# (% a b) 0xf_s8)
    --     @doc ""
    --     
    test::AssertEq#(!a, 0x78_s8)
    test::AssertEq#(-a, 0x79_s8)
    -- 
    test::AssertEq#(a << 0, 0x87_s8)
    test::AssertEq#(a << 32, 0x87_s8)
    test::AssertEq#(a << 64, 0x87_s8)
    -- 
    test::AssertEq#(a >> 0, 0x87_s8)
    test::AssertEq#(a >> 32, 0x87_s8)
    test::AssertEq#(a >> 64, 0x87_s8)
    -- 
    test::AssertEq#(a < b, true)
    test::AssertEq#(a <= b, true)
    test::AssertEq#(a > b, false)
    test::AssertEq#(a >= b, false)
    test::AssertEq#(a == b, false)
    test::AssertEq#(a != b, true)
    -- 
    test::AssertEq#(a < a, false)
    test::AssertEq#(a <= a, true)
    test::AssertEq#(a > a, false)
    test::AssertEq#(a >= a, true)
    test::AssertEq#(a == a, true)
    test::AssertEq#(a != a, false)

fun main(argc s32, argv ^^s8) s32:
    do test_s64(0x8765432187654321, 0x1234567812345678)
    do test_s32(0x87654321, 0x12345678)
    do test_s16(0x8765, 0x1234)
    do test_s8(0x87, 0x78)
    -- test end
    test::Success#()
    return 0
