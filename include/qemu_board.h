#ifndef QEMU_BOARD_H
#define QEMU_BOARD_H

#include <stdbool.h>
#include <stdint.h>

void qemu_board_initialize(void);
bool qemu_button_pressed(uint32_t button, uint32_t cycle);
void qemu_led_set(uint32_t led, bool on);
void qemu_report_cycle(uint32_t cycle, bool button0, bool button1,
                       uint32_t tick);
void qemu_write(const char *text);
void qemu_metric(const char *name, uint32_t value);
void qemu_report_pass(void);
void qemu_report_failure(const char *reason);

#endif
