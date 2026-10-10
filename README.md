# ThreadX 5.6 to 6.x and Cortex-M migration proof

This repository is an independently written proof of concept for moving the behavior of a
legacy WICED GPIO snippet onto current Eclipse ThreadX and a newer Cortex-M
port. It deliberately does **not** contain WICED source or Broadcom's
WICED-only ThreadX 5.6 binaries.

## What is in scope

- Historical baseline: Broadcom WICED SDK 3.1.0, which identifies its
  ThreadX port as `ver5.6` and provides prebuilt Cortex-M4 archives.
- New RTOS: Eclipse ThreadX `v6.5.2.202603_rel`, pinned as a submodule.
  The originally linked `v6.1.12_rel` is an older release.
- Compiler: Clang targeting `arm-none-eabi`; both C and GNU-style port
  assembly are compiled with Clang.
- Runnable QEMU target: Cortex-M55 on `mps3-an547` using QEMU 11.1.0.
- Cortex-M85: the same application and ThreadX M85 GNU port are built as an
  ELF image. QEMU 11.1.0 does not list an M85 CPU or MPS3 AN555 machine, so
  the M85 image is compile/link evidence only, not an M85 runtime test.
- Demo: two LED state machines, two deterministic active-low virtual buttons,
  and a ThreadX thread that sleeps for 25 ticks between updates. QEMU
  semihosting emits the LED/button state to the host console. This is a
  scheduler/application simulation, not a model of a physical GPIO controller.
- Service checks: a higher-priority worker suspends on a queue, resumes on send,
  and signals an event. The firmware also checks semaphore success/error cases,
  a mutex, byte-pool allocation/release, and exact 25-tick LED sleep intervals.
- The firmware is a single secure image. TrustZone transitions, PACBTI,
  MVE/FPU register preservation stress, and production interrupt loads are not
  covered by these tests.

## Build

Initialize the pinned ThreadX dependency:

```powershell
git submodule update --init --recursive
```

Configure and build the runnable Cortex-M55 image:

```powershell
cmake --preset m55
cmake --build --preset m55
python tests/run_qemu.py --elf build/m55/threadx_gpio_demo.elf --machine mps3-an547 --cpu cortex-m55
```

Build the Cortex-M85 image (compile/link only):

```powershell
cmake --preset m85
cmake --build --preset m85
```

The Cortex-M4 preset is a same-release control build:

```powershell
cmake --preset m4
cmake --build --preset m4
python tests/run_qemu.py --elf build/m4/threadx_gpio_demo.elf --machine mps2-an386 --cpu cortex-m4
```

Requirements: CMake, Ninja, Python 3, LLVM/Clang with ARM target support, and
QEMU system emulation for ARM. The local demonstration uses semihosting, so
QEMU must be started with semihosting enabled.

## Evidence limits

The proof shows that the application behavior can be rebuilt against the
current ThreadX release for Cortex-M4, M55, and M85 ports with Clang, and that
the M55 image runs under QEMU. It does not prove compatibility of the complete
WICED SDK, Broadcom wireless stack, a production board's GPIO driver, M85
runtime behavior, hardware timing, WCET, or performance parity with an
unavailable/proprietary ThreadX 5.6 binary.

All memory and performance numbers must be generated from the checked-in
scripts and actual build/run artifacts. QEMU TCG timing is not a substitute
for target silicon measurement. The harness uses QEMU instruction-count
virtual time (`shift=7`, 128 ns per emulated instruction) for reproducible
scheduler tests, not a cycle-accurate core model.

See `presentation/` for the technical slide deck source and generated
deliverables, and `docs/presentation.md` for regeneration instructions.

## Share with stakeholders

- [Interactive technical presentation](https://zuwasi.github.io/Public-html-pages/tx5-upgrade/)
- [Download PDF](https://zuwasi.github.io/Public-html-pages/tx5-upgrade/threadx-migration.pdf)
- [Public source and backup](https://github.com/zuwasi/TX5-upgrade)
