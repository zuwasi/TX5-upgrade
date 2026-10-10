/* SPDX-License-Identifier: MIT
   Demonstrator map shared by the QEMU MPS2-M4 and MPS3-M55 images.
   This is NOT a production M85 SoC linker script. */
ENTRY(reset_handler)
MEMORY
{
    CODE (rx) : ORIGIN = 0x00000000, LENGTH = 512K
    RAM (rw)  : ORIGIN = 0x20000000, LENGTH = 32K
}
SECTIONS
{
    .vectors : ALIGN(512) { KEEP(*(.vectors)) } > CODE
    .text : ALIGN(4) { *(.text*) *(.rodata*) } > CODE
    .ARM.exidx : ALIGN(4) { *(.ARM.exidx*) } > CODE
    .data : ALIGN(8)
    {
        __data_start = .;
        *(.data*)
        __data_end = .;
    } > RAM AT > CODE
    __data_load = LOADADDR(.data);
    .bss (NOLOAD) : ALIGN(8)
    {
        __bss_start = .;
        *(.bss*) *(COMMON)
        __bss_end = .;
    } > RAM
    .stack (NOLOAD) : ALIGN(8)
    {
        __stack_limit = .;
        . += 2048;
        __stack_top = .;
    } > RAM
    __first_free_ram = .;
    /DISCARD/ : { *(.comment) *(.note*) }
    ASSERT(__first_free_ram <= ORIGIN(RAM) + LENGTH(RAM), "RAM overflow")
}
