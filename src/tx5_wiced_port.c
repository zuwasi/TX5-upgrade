/* SPDX-License-Identifier: MIT */
#include "tx_api.h"

/* The prebuilt WICED ThreadX 5.6 release archive clears 0xb4 bytes per thread
   in _tx_thread_create. Application headers resolved against a different
   tx_user.h (for example one without WICED's `int errno` extension) give a
   smaller TX_THREAD, and the kernel then overwrites the adjacent object. */
_Static_assert(sizeof(TX_THREAD) == 180U,
               "TX_THREAD layout does not match the prebuilt WICED TX5.6 archive");

/* Board hook required by the WICED ThreadX 5.6 idle loop. The kernel passes
   the ticks until the next timer expiry and adds the returned slept ticks to
   its clock. SysTick keeps running here, so no ticks are compensated. */
unsigned long platform_power_down_hook(unsigned long ticks_until_next_timer)
{
    (void)ticks_until_next_timer;
    __asm volatile("wfi");
    return 0UL;
}
