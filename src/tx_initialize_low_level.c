/* SPDX-License-Identifier: MIT */
#include <stdint.h>

extern void * _tx_initialize_unused_memory;
extern unsigned char __first_free_ram;
extern const uint32_t demo_vectors[];

#define REG32(address) (*(volatile uint32_t *)(uintptr_t)(address))

#ifdef DEMO_TX5
extern void * _tx_thread_system_stack_ptr;
#endif

void _tx_initialize_low_level(void)
{
    _tx_initialize_unused_memory = &__first_free_ram;
#ifdef DEMO_TX5
    /* The TX5.6 port reads the ISR stack base from here; TX6 uses MSP. */
    _tx_thread_system_stack_ptr = (void *)(uintptr_t)demo_vectors[0];
#endif
    REG32(0xe000ed08U) = (uint32_t)(uintptr_t)demo_vectors;
    /* SVC and PendSV are lowest priority; SysTick remains above them. */
    REG32(0xe000ed1cU) = 0xff000000U;
    REG32(0xe000ed20U) = 0x40ff0000U;
    REG32(0xe000e010U) = 0U;
    REG32(0xe000e014U) = (DEMO_CLOCK_HZ / 100U) - 1U;
    REG32(0xe000e018U) = 0U;
    REG32(0xe000e010U) = 7U;
}
