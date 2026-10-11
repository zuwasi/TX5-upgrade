# Scope and evidence contract

## Migration stages

1. `tx5-m4`: the shared application on ThreadX `G5.6.5.2`, the prebuilt
   Cortex-M3/M4 release archive from WICED SDK 3.1.0 (repository commit
   `0886ec932a063e12db768cd09428e8a8ab555bce`), linked from an external
   checkout. Status: built and run on QEMU.
2. `tx6-m4`: the same application on MIT Eclipse ThreadX 6, Cortex-M4.
   Status: built and run on QEMU.
3. `tx6-m85`: the same application on MIT Eclipse ThreadX 6, Cortex-M85.
   Status: compile/link only.

Cortex-M55 on QEMU is supplemental runtime evidence for the Armv8.1-M port
family. It is not reported as Stage 3.

The application and board code are independently written. The behaviour (two
LEDs toggling every 250 ms unless the corresponding active-low button is held;
a held button forces the LED on without advancing its toggle latch) is modelled
on the WICED GPIO snippet, but no WICED application or platform code is used.

## ThreadX 5 dependency and licence boundary

ThreadX 5 is not open source. The WICED SDK is published with ThreadX 5.6
headers and prebuilt archives whose README restricts them to WICED use. The
repository links them from `TX5_ROOT` outside the source tree and never copies
them. The kernel source is not available, so TX5 findings come from its public
headers, the archive's symbols and build attributes, disassembly of port
objects, and runtime behaviour.

## Version choice

The user supplied the ThreadX `v6.1.12_rel` tag, but also requested the latest
6.x release. Inspection on 2026-10-11 identified `v6.5.2.202603_rel`, commit
`93387b0a60382a29579bbad5045c68328e3751df`. The code uses the current MIT release.
The older tag has Azure RTOS hardware-linked licensing text in its own tree;
do not substitute that checkout while assuming it carries the same MIT text.

## What the build/run proves

The same application source is compiled by Clang for all stages. Stage 1 uses
the archive's ABI (soft-float, packed enums) and the WICED `tx_user.h`; the TX6
stages use hard-float and `config/tx6/tx_user.h`. A static assertion checks the
TX5 `TX_THREAD` size against the 180 bytes the archive clears per thread.

The TX5-M4, TX6-M4 and M55 QEMU runs each verify:

- The exact kernel banner version and the expected CPUID part number.
- Higher-priority thread preemption, queue suspension and resumption, event flags.
- Semaphore success and empty-semaphore error behaviour.
- Mutex acquire/release and byte-pool allocate/release.
- Ten LED rows, every virtual button state, the held-button latch semantics.
- Nine exact 25-tick sleep intervals at a configured 100 Hz tick.
- Clean bounded completion with a zero QEMU process exit code.

Negative verifier tests inject bad state, timing, identity, version and
completion evidence. A firmware fault that hangs is a failed timeout, not
success.

## What remains open

- Cortex-M85 execution. Installed QEMU 11.1.0 lists neither `cortex-m85` nor
  `mps3-an555`.
- Production BSP: real SoC memory map, startup clock, vector table, reset,
  GPIO mapping/polarity, IRQ sources, cache/MPU/TCM and DMA integration.
- TrustZone partitioning, FPU/MVE context preservation under mixed workloads,
  PACBTI, isolation and security policy. The images are single-secure only.
- Real-board timing, interrupt latency, context-switch cycles, energy and WCET.
- The WICED Wi-Fi, network and platform stack. Only its RTOS archive is used.

## Measurement rules

ELF section sizes are actual linked image sizes, including service self-tests
and diagnostics, not minimum kernel footprints. TX5 and TX6 sizes also reflect
different kernel configurations: the WICED release archive disables error
checking and preemption-threshold and processes timers in the ISR. They are
not a pure measure of kernel growth. RAM reserved includes the 2 KiB system
stack, all static stacks and test objects.

LED thread stack high-water is measured by scanning for the `0xEFEFEFEF`
fill pattern that both kernels write at thread creation.

Tests use `-icount shift=7,align=off,sleep=off`: each emulated instruction
advances virtual time by a synthetic 128 ns. This is deterministic scheduling
test time, not a model of pipeline or cache performance. Repeated host wall
times include emulator startup and semihosting; they measure the harness, not
silicon performance. There is no M85 runtime or performance figure.
