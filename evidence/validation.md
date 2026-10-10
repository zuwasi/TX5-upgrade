# Validation record

Recorded on 2026-10-11 (local date). The exact measurement timestamp, compiler,
emulator build, image hashes and samples are in `summary.json`.

## Firmware

- Clang/LLD configure and build: Cortex-M4, Cortex-M55, Cortex-M85, all passed.
- Undefined-symbol inspection: all three ELF files have no unresolved symbols.
- Cortex-M85 ELF attributes identify `cortex-m85`, Armv8.1-M Mainline and
  AAPCS VFP. This is compile/link evidence only.
- Eight alternating repeated QEMU runs per runnable core: M4 8/8, M55 8/8.
- Each run verified CPU part, ThreadX version, RTOS service self-tests,
  all ten LED/button states, nine 25-tick intervals, and successful termination.
- CTest: `qemu_m4_led_demo` and `qemu_m55_led_demo` passed.
- Python verifier tests: 11/11 passed, including ten corrupted-evidence cases.

The original host-time run sometimes crossed a tick boundary during
semihosting output. Final runs use deterministic QEMU icount virtual time.
No hardware latency, speedup, power, WCET or sub-tick jitter is inferred.

## Presentation and PDF

- 33 HTML slides and 33 selectable-text PDF pages.
- Nine generated figures, eight code-diff discussions.
- Local link, image, CSP, replay-data and ELF/evidence-hash checks passed.
- JavaScript syntax and Python bytecode compilation passed.
- Desktop 1366×900 and mobile 390×844 browser checks passed:
  Previous/Next, keyboard arrows, Home, recorded replay controls and all slides.
- No browser page errors or console messages were reported.
- All nine figures loaded; no document-level horizontal overflow was found.
- Screenshots and browser results are in `ui/`.
- The site pre-publication checker reported no errors, warnings or info
  findings for the new deck. The existing site's index has a pre-existing
  missing-CSP info finding; it was not changed outside this task's scope.
- Embedded PDF font metadata was inspected; Roboto OFL 1.1 notices are shipped.

## Review limitation

A Qodo fast review was submitted, but the service could not obtain repository
credentials for the workspace. It failed without producing findings, and
was not retried automatically. No successful external Qodo review is claimed.
Local build/runtime/artifact checks and inspection were completed.

## Still unverified

Cortex-M85 execution, a real M85 SoC BSP, physical GPIO, TrustZone partitioning,
mixed FPU/MVE register preservation stress, production interrupt loads,
full WICED wireless/TLS integration and target-board performance qualification.
