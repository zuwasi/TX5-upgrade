# Validation record

Recorded on 2026-10-11 (local date). The exact measurement timestamp, compiler,
emulator build, image and TX5 archive hashes and samples are in `summary.json`.

## Firmware

- Clang/LLD configure and build passed for all four images: `tx5-m4`
  (ThreadX G5.6.5.2, WICED prebuilt archive, soft-float), `tx6-m4`, `m55` and
  `tx6-m85` (ThreadX 6.5.2.202603, hard-float).
- Undefined-symbol inspection: no ELF has unresolved symbols.
- ELF attributes: `tx5-m4` has no FP_arch / VFP-args tag and packed enums,
  matching the archive; TX6 M4 has VFPv4-D16 and AAPCS VFP; the M85 ELF
  identifies `cortex-m85`, Armv8.1-M Mainline, MVE integer and float. M85 is
  compile/link evidence only.
- Eight interleaved repeated QEMU runs per runnable image: TX5-M4 8/8,
  TX6-M4 8/8, M55 8/8. 216 of 216 sleep intervals were 25 ticks.
- Each run verified the CPU part, the exact per-stage kernel banner version,
  RTOS service self-tests, all ten LED/button states, nine 25-tick intervals,
  and successful termination. LED/tick rows are identical on all three images.
- CTest: `tx5-m4`, `m4` and `m55` QEMU tests passed.
- Python verifier tests: 15/15 passed, including corrupted-evidence and
  version-mismatch cases.
- Configuration guards: a TX5 build is refused without `TX5_ROOT`, with
  `TX5_ROOT` inside the repository, on a non-M4 core, against a directory
  that is not a WICED checkout, or with a non-TX5 expected version.

The first Stage 1 run found a header-configuration mismatch: the project's TX6
`tx_user.h` shadowed WICED's, giving a 176-byte `TX_THREAD` while the archive
clears 180 bytes per thread. The TX6 configuration moved to `config/tx6/`, and
a static assertion now rejects the mismatch. The recorded runs are after the fix.

QEMU icount virtual time is deterministic and synthetic. No hardware latency,
speedup, power, WCET or sub-tick jitter is inferred.

## Presentation and PDF

- 41 HTML slides and 41 selectable-text PDF pages (one page per slide).
- Nine regenerated figures, eleven code-diff discussions.
- Local link, image, CSP, replay-data and ELF/evidence-hash checks passed.
- Figures were inspected visually after generation.
- The ESL-branded deck was checked in desktop and 390-pixel mobile views,
  including the introduction and challenges table. PDF introduction, challenges,
  code and contact pages were rendered and inspected.
- Browser screenshots in `ui/` are historical, from the earlier 33-slide deck;
  current local visual checks are in the untracked `tmp/shots/` directory.

## Review limitation

An earlier Qodo fast review failed because the service could not obtain
repository credentials for the workspace. No successful external Qodo review
is claimed.

## Still unverified

Cortex-M85 execution, a real M85 SoC BSP, physical GPIO, TrustZone partitioning,
mixed FPU/MVE register preservation stress, production interrupt loads,
WICED wireless/TLS integration and target-board performance qualification,
including any TX5-vs-TX6 cycle comparison on silicon.
