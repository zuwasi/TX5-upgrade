#include "qemu_board.h"

#include <stddef.h>

static bool virtual_leds[2];

static void semihost_write0(const char *text)
{
    register uintptr_t operation __asm("r0") = 0x04U;
    register const char *argument __asm("r1") = text;

    __asm volatile("bkpt 0xab"
                   : "+r"(operation)
                   : "r"(argument)
                   : "memory");
}

static void semihost_exit_success(void)
{
    register uintptr_t operation __asm("r0") = 0x18U;
    register uintptr_t reason __asm("r1") = 0x20026U;

    __asm volatile("bkpt 0xab"
                   : "+r"(operation)
                   : "r"(reason)
                   : "memory");

    for (;;) {
        __asm volatile("wfi");
    }
}

static void write_decimal(uint32_t value)
{
    char digits[11];
    size_t count = 0U;

    do {
        digits[count++] = (char)('0' + (value % 10U));
        value /= 10U;
    } while (value != 0U && count < sizeof(digits));

    while (count != 0U) {
        char output[2];
        output[0] = digits[--count];
        output[1] = '\0';
        semihost_write0(output);
    }
}

void qemu_board_initialize(void)
{
    semihost_write0("[boot] ThreadX GPIO behavior demo; LED output is semihosted\n");
    semihost_write0("[core] " DEMO_CORE_NAME "\n");
    qemu_metric("cpuid", *(volatile uint32_t *)(uintptr_t)0xe000ed00U);
}

bool qemu_button_pressed(uint32_t button, uint32_t cycle)
{
    bool active_low_level = true;

    /* Reproducible virtual input: button 0 is held for cycles 2-3;
       button 1 is held for cycle 5. The input wire is active-low. */
    if (button == 0U && (cycle == 2U || cycle == 3U)) {
        active_low_level = false;
    } else if (button == 1U && cycle == 5U) {
        active_low_level = false;
    }

    return !active_low_level;
}

void qemu_led_set(uint32_t led, bool on)
{
    if (led < 2U) {
        virtual_leds[led] = on;
    }
}

void qemu_report_cycle(uint32_t cycle, bool button0, bool button1,
                       uint32_t tick)
{
    semihost_write0("cycle=");
    write_decimal(cycle);
    semihost_write0(" BTN0=");
    semihost_write0(button0 ? "PRESSED" : "released");
    semihost_write0(" BTN1=");
    semihost_write0(button1 ? "PRESSED" : "released");
    semihost_write0(" LED0=");
    semihost_write0(virtual_leds[0] ? "ON" : "OFF");
    semihost_write0(" LED1=");
    semihost_write0(virtual_leds[1] ? "ON" : "OFF");
    semihost_write0(" tick=");
    write_decimal(tick);
    semihost_write0("\n");
}

void qemu_write(const char *text)
{
    semihost_write0(text);
}

void qemu_metric(const char *name, uint32_t value)
{
    semihost_write0("[metric] ");
    semihost_write0(name);
    semihost_write0("=");
    write_decimal(value);
    semihost_write0("\n");
}
void qemu_report_pass(void)
{
    semihost_write0("[pass] bounded LED sequence completed\n");
    semihost_exit_success();
}

void qemu_report_failure(const char *reason)
{
    semihost_write0("[fail] ");
    semihost_write0(reason);
    semihost_write0("\n");
    for (;;) {
        __asm volatile("wfi");
    }
}
