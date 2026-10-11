# ThreadX 5 to 6 and Cortex-M4 to M85 migration proof

One independently written application and QEMU board layer, built with Clang
in three migration stages:

| Stage | Preset | Kernel | Core | Evidence |
| --- | --- | --- | --- | --- |
| 1 | `tx5-m4` | ThreadX `G5.6.5.2`, prebuilt Cortex-M3/M4 archive from the WICED SDK 3.1.0 | Cortex-M4, soft-float | Built and run on QEMU `mps2-an386` |
| 2 | `tx6-m4` | Eclipse ThreadX `v6.5.2.202603_rel` (MIT) | Cortex-M4, hard-float | Built and run on QEMU `mps2-an386` |
| 3 | `tx6-m85` | Eclipse ThreadX `v6.5.2.202603_rel` (MIT) | Cortex-M85, hard-float | Compile/link only |

A supplemental `m55` preset runs the same application on Cortex-M55
(`mps3-an547`), the newest Armv8.1-M core the installed QEMU 11.1.0 can
execute. It is extra runtime evidence for the Armv8.1-M port family, not a
substitute for Stage 3 execution.

## The ThreadX 5 dependency

ThreadX 5 was never open source. The WICED SDK is publicly available and ships
the ThreadX 5.6 headers and prebuilt `ThreadX.ARM_CM4.release.a`; its README
limits those objects to use with WICED. This repository therefore never
contains any SDK file. Stage 1 links the archive from a separate checkout
(`TX5_ROOT`) and configuration fails if that path is inside this repository.

```powershell
git clone --filter=blob:none --no-checkout https://github.com/wwwllllllll/bcm-wiced-sdk.git C:\Projects\tx5-external\bcm-wiced-sdk
git -C C:\Projects\tx5-external\bcm-wiced-sdk sparse-checkout set --no-cone '/WICED/RTOS/ThreadX/'
git -C C:\Projects\tx5-external\bcm-wiced-sdk checkout 0886ec932a063e12db768cd09428e8a8ab555bce
$env:TX5_ROOT = 'C:\Projects\tx5-external\bcm-wiced-sdk'
```

## Build and test

```powershell
git submodule update --init --recursive

cmake --preset tx5-m4;  cmake --build --preset tx5-m4;  ctest --test-dir build/tx5-m4 --output-on-failure
cmake --preset tx6-m4;  cmake --build --preset tx6-m4;  ctest --test-dir build/m4 --output-on-failure
cmake --preset tx6-m85; cmake --build --preset tx6-m85
cmake --preset m55;     cmake --build --preset m55;     ctest --test-dir build/m55 --output-on-failure
python -m unittest discover -s tests -p test_verifier.py
```

`tx6-m4` and `tx6-m85` share build directories with the `m4` and `m85`
presets. Requirements: CMake 3.21+, Ninja, Python 3, LLVM/Clang with ARM
support and `qemu-system-arm` with semihosting.

## What the shared application covers

- Two LED state machines and two deterministic active-low virtual buttons. A
  held button forces its LED on without advancing that LED's toggle latch.
- A thread that sleeps 25 ticks per update at a 100 Hz tick.
- A higher-priority worker that preempts, suspends on an empty queue, resumes
  on send and sets an event flag; semaphore success and empty-semaphore error;
  mutex get/put; byte-pool allocate/release.
- Run counts from `tx_thread_run_count` and stack high-water measured by
  scanning the `0xEFEFEFEF` fill pattern, which both kernels write.
- The verifier requires the exact kernel banner version (`G5.6.5.2` or
  `6.5.2.202603`), the CPUID part number, all ten LED rows and exact
  25-tick intervals.

Output is through QEMU semihosting. This simulates application and scheduler
behaviour, not a physical GPIO controller. The images are single-secure;
TrustZone, PACBTI, FPU/MVE context stress and production interrupt loads are
not covered.

## What changed between TX5.6 and TX6 for this application

The application source is the same for all stages. The port layer differs:

| Item | TX5.6 (WICED archive) | TX6.5 |
| --- | --- | --- |
| Float ABI | Soft-float; context switch saves r4-r11 only | Hard-float; FPU context handled by the port |
| Enum size | Packed (`-fshort-enums`), must match the archive | Default |
| PendSV / SVC handlers | `__tx_PendSVHandler` / `__tx_SVCallHandler` | `PendSV_Handler` / unused |
| First thread start | `_tx_thread_schedule` issues `svc #0` | PendSV |
| Low-level init | Must set `_tx_thread_system_stack_ptr` | Not needed |
| Idle hook | Calls `platform_power_down_hook(ticks)` | None |
| `_tx_version_id` | `const CHAR[]` | `CHAR[]` |
| Configuration | WICED `tx_user.h`: `int errno` thread extension, no error checking, no preemption threshold, timers in ISR | Project `config/tx6/tx_user.h` |

The WICED `tx_user.h` must be the one the application sees. If another
`tx_user.h` is found first, `TX_THREAD` shrinks from 180 to 176 bytes while the
archive still clears 180 bytes per thread, overwriting the next object. A
compile-time assertion in `src/tx5_wiced_port.c` now rejects that build.

## Evidence limits

Section sizes are linked image sizes including diagnostics and self-tests.
TX5 and TX6 sizes also reflect different kernel configurations (see above), so
they are not a pure measure of kernel growth. Tests use QEMU instruction-count
virtual time (`-icount shift=7`, 128 ns per emulated instruction), not a
cycle-accurate model. Host wall times measure the test harness, not silicon
performance. There is no M85 runtime or performance figure.

See `docs/scope-and-evidence.md` for the evidence contract.

## Published deck

- [Interactive technical presentation](https://zuwasi.github.io/Public-html-pages/tx5-upgrade/)
- [Download PDF](https://zuwasi.github.io/Public-html-pages/tx5-upgrade/threadx-migration.pdf)
- [Public source](https://github.com/zuwasi/TX5-upgrade)
