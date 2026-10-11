#include "qemu_board.h"

#include "tx_api.h"

#include <stddef.h>

#ifndef LED_DEMO_MAX_CYCLES
#define LED_DEMO_MAX_CYCLES 10
#endif

#define LED_THREAD_STACK_BYTES 1024U
#define LED_THREAD_PRIORITY 5U
#define LED_UPDATE_TICKS 25U

static TX_THREAD led_thread;
static ULONG led_thread_stack[LED_THREAD_STACK_BYTES / sizeof(ULONG)];
extern void rtos_selftest(void);

/* Both ThreadX 5.6 and 6.x fill new stacks with this pattern. Scanning for it
   measures every stack write, not just the SPs seen at context switches, and
   works whether or not the kernel was built with stack checking. */
#define DEMO_STACK_FILL 0xEFEFEFEFUL

static uint32_t stack_high_water_bytes(void)
{
    size_t untouched = 0U;

    while (untouched < sizeof(led_thread_stack) / sizeof(led_thread_stack[0]) &&
           led_thread_stack[untouched] == DEMO_STACK_FILL) {
        ++untouched;
    }
    return (uint32_t)(sizeof(led_thread_stack) - untouched * sizeof(led_thread_stack[0]));
}

static void led_thread_entry(ULONG input)
{
    bool toggle0 = false;
    bool toggle1 = false;
    uint32_t cycle = 0U;

    (void)input;
    qemu_board_initialize();
    /* Declared by tx_port.h: const in TX5.6, non-const in TX6. */
    qemu_write(_tx_version_id);
    qemu_write("\n");
    qemu_metric("sizeof_TX_THREAD", (uint32_t)sizeof(TX_THREAD));
    qemu_metric("led_stack_reserved", sizeof(led_thread_stack));
    rtos_selftest();

    for (;;) {
        const bool button0 = qemu_button_pressed(0U, cycle);
        const bool button1 = qemu_button_pressed(1U, cycle);

        /* A held active-low button forces its paired LED on. Otherwise the
           LED toggles once per RTOS sleep interval. */
        if (!button0) {
            toggle0 = !toggle0;
        }
        if (!button1) {
            toggle1 = !toggle1;
        }
        qemu_led_set(0U, button0 || toggle0);
        qemu_led_set(1U, button1 || toggle1);
        qemu_report_cycle(cycle, button0, button1, tx_time_get());

        ++cycle;
#if LED_DEMO_MAX_CYCLES > 0
        if (cycle >= (uint32_t)LED_DEMO_MAX_CYCLES) {
            qemu_metric("led_thread_runs", led_thread.tx_thread_run_count);
            qemu_metric("led_stack_high_water_bytes", stack_high_water_bytes());
            qemu_report_pass();
        }
#endif
        if (tx_thread_sleep(LED_UPDATE_TICKS) != TX_SUCCESS) {
            qemu_report_failure("tx_thread_sleep failed");
        }
    }
}

int main(void)
{
    tx_kernel_enter();
    for (;;) {
        __asm volatile("wfi");
    }
}

void tx_application_define(void *first_unused_memory)
{
    UINT status;

    (void)first_unused_memory;
    status = tx_thread_create(&led_thread,
                              "gpio-led-demo",
                              led_thread_entry,
                              0U,
                              led_thread_stack,
                              sizeof(led_thread_stack),
                              LED_THREAD_PRIORITY,
                              LED_THREAD_PRIORITY,
                              TX_NO_TIME_SLICE,
                              TX_AUTO_START);
    if (status != TX_SUCCESS) {
        qemu_report_failure("tx_thread_create failed");
    }
}
