
.mem newline 4 rodata
    .data 1 "\n"
.endmem

# This is called with r0:argc r1:argv
.fun main 16
    add_imm al r10 r0 0
    add_imm al r11 r1 0
    b al expr:jump24:argc_check
.bbl loop 4
    ldr_imm_add_post al r1 r11 4
    sub_imm al r10 r10 1

# strlen computation: r1 contains string r2 will contain it's length
    mov_imm al r2 0
    b al expr:jump24:null_check
.bbl next_byte 4
    add_imm al r2 r2 1
.bbl null_check 4
    ldrb_reg_add al r0 r1 r2 lsl 0
    cmp_imm al r0 0
    b ne expr:jump24:next_byte
# print string
    mov_imm al r0 1
    mov_imm al r7 4
    svc al 0
# print newline
    mov_imm al r2 1
    movw  al r1 expr:movw_abs_nc:newline:0
    movt  al r1 expr:movt_abs:newline:0
    mov_imm al r0 1
    mov_imm al r7 4
    svc al 0

.bbl argc_check 4
    cmp_imm al r10 0
    b ne expr:jump24:loop
# exit
    mov_imm al r0 0
    bx al lr
.endfun	

.fun _start 16
    ldr_imm_add al r0 sp 0
    add_imm al r1 sp 4                        
    bl expr:call:main                          
    movw al r7 1                            
    svc al 0                                 
    ud2 al
.endfun	