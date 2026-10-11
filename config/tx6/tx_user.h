/* SPDX-License-Identifier: MIT */
#ifndef DEMO_TX_USER_H
#define DEMO_TX_USER_H

/* QEMU boots this standalone demonstrator in secure state. No transitions
   between secure and non-secure worlds are claimed or required. */
#define TX_SINGLE_MODE_SECURE
#define TX_TIMER_TICKS_PER_SECOND 100
#define TX_ENABLE_STACK_CHECKING

#endif
