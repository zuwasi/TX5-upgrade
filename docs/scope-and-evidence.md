# Scope and evidence contract

## Historical inputs

WICED reference: SDK 3.1.0, repository commit
`0886ec932a063e12db768cd09428e8a8ab555bce`, with a `WICED/RTOS/ThreadX/ver5.6`
directory and prebuilt CM3/CM4 ThreadX archives. The actual kernel implementation
is not source-available in that SDK. The sample's behavior is two LEDs toggling
every 250 ms unless a corresponding active-low button is held. Holding the
button forces the output on without advancing that LED's toggle latch.

The public PoC contains independently written application and board code,
not a republished WICED application or modified proprietary TX5 kernel.
Consequently no claim of a line-by-line TX5 kernel diff, TX5 benchmark, or
working full WICED wireless SDK migration is justified.

## Version choice

The user supplied the ThreadX `v6.1.12_rel` tag, but also requested the latest
6.x release. Inspection on 2026-10-11 identified `v6.5.2.202603_rel`, commit
`93387b0a60382a29579bbad5045c68328e3751df`. The code uses the current MIT release.
The older tag has Azure RTOS hardware-linked licensing text in its own tree;
do not substitute that checkout while assuming it carries the same MIT text.

## What the build/run proves

The application and ThreadX are compiled by Clang with a matching
`arm-none-eabi`, Cortex-M CPU, Thumb, hard-float ABI, and kernel configuration.
The same source builds on the Cortex-M4, M55, and M85 GNU-syntax ports.

The Cortex-M4 and M55 QEMU runs verify:

- Expected CPU identification and ThreadX version text.
- Higher-priority thread preemption, queue suspension and resumption, event flags.
- Semaphore success and empty-semaphore error behavior.
- Mutex acquire/release and byte-pool allocate/release.
- Ten LED rows, every virtual button state, the held-button latch semantics.
- Nine exact 25-tick sleep intervals, at a configured 100 Hz tick.
- Clean bounded completion with a zero QEMU process exit code.

Negative verifier tests inject bad state, timing, identity, and completion
evidence. A firmware fault that hangs is a failed timeout, not success.

## What remains open

- Cortex-M85 execution. Installed QEMU 11.1.0 lists neither `cortex-m85` nor
  `mps3-an555`. QEMU development documentation mentions AN555, but development
  documentation is not evidence that this installed release can execute it.
- Production BSP: real SoC memory map, startup clock, vector table, reset,
  GPIO mapping/polarity, IRQ sources, cache/MPU/TCM and DMA integration.
- TrustZone partitioning, FPU/MVE context preservation under mixed workloads,
  PACBTI, isolation and security policy. This demo is single-secure only.
- Real-board timing, interrupt latency, context-switch cycles, energy, and WCET.
- Complete WICED Wi-Fi/TLS/network integration and licensed vendor components.

## Measurement rules

The ELF section sizes are actual linked image sizes, including this demo's
service self-tests and diagnostic output, not the minimum ThreadX footprint.
RAM reserved includes the 2 KiB system stack, all static stacks and test objects.
Observed LED thread stack high-water is sampled by ThreadX stack checking.

Tests use `-icount shift=7,align=off,sleep=off`: each emulated instruction
advances virtual time by a synthetic 128 ns. This is deterministic scheduling
test time, not a model of the core's pipeline or cache performance.
Repeated QEMU host wall times include startup, synthetic-time execution, and semihosting.
They compare reproducibility of the test harness, **not** M4 versus M55 silicon
performance. Tick histograms show scheduling correctness, not sub-tick jitter.
There is no M85 performance number and no TX5 memory/performance baseline.
