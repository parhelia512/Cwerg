module:

fun fun1(a s32, b u32, c r32) u8:
    let x s8 = as(a, s8)
    let y = as(c, r64)
    let z s32 = bitwise_as(c, s32)
    return 66

-- just a compilation test
fun main(argc s32, argv ^^u8) s32:
    return 0
