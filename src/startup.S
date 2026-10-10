/* SPDX-License-Identifier: MIT */
.syntax unified
.thumb

.section .vectors, "a", %progbits
.balign 512
.global demo_vectors
demo_vectors:
    .word __stack_top
    .word reset_handler
    .word fault_handler
    .word fault_handler
    .word fault_handler
    .word fault_handler
    .word fault_handler
#ifdef DEMO_M4
    .word 0
#else
    .word fault_handler
#endif
    .word 0, 0, 0
    .word fault_handler /* No SVC calls in single-secure mode. */
    .word fault_handler
    .word 0
    .word PendSV_Handler
    .word SysTick_Handler
    .rept 112
    .word fault_handler
    .endr

.section .text.reset_handler, "ax", %progbits
.global reset_handler
.type reset_handler, %function
.thumb_func
reset_handler:
    cpsid i
    ldr r0, =__stack_top
    mov sp, r0
    ldr r0, =__data_load
    ldr r1, =__data_start
    ldr r2, =__data_end
1:
    cmp r1, r2
    bhs 2f
    ldrb r3, [r0], #1
    strb r3, [r1], #1
    b 1b
2:
    ldr r1, =__bss_start
    ldr r2, =__bss_end
    movs r3, #0
3:
    cmp r1, r2
    bhs 4f
    strb r3, [r1], #1
    b 3b
4:
    /* Enable CP10/CP11 for the hard-float ABI, including MVE FP sharing. */
    ldr r0, =0xe000ed88
    ldr r1, [r0]
    orr r1, r1, #0x00f00000
    str r1, [r0]
    dsb
    isb
    bl main
    b fault_handler
.size reset_handler, .-reset_handler

.section .text.SysTick_Handler, "ax", %progbits
.global SysTick_Handler
.type SysTick_Handler, %function
.thumb_func
SysTick_Handler:
    push {r0, lr}
    bl _tx_timer_interrupt
    pop {r0, lr}
    bx lr
.size SysTick_Handler, .-SysTick_Handler

.section .text.fault_handler, "ax", %progbits
.global fault_handler
.type fault_handler, %function
.thumb_func
fault_handler:
    b fault_handler
.size fault_handler, .-fault_handler
