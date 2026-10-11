"""Collect measured build sizes and repeated QEMU runs for the presentation."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import statistics
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from run_qemu import CURRENT_VERSION, find_qemu, run  # noqa: E402

TX5_VERSION = "G5.6.5.2"
WICED_COMMIT = "0886ec932a063e12db768cd09428e8a8ab555bce"
# build directory -> (stage label, kernel version, QEMU machine/cpu or None)
BUILDS = {
    "tx5-m4": ("Stage 1: TX5.6 / Cortex-M4", TX5_VERSION, ("mps2-an386", "cortex-m4")),
    "m4": ("Stage 2: TX6.5 / Cortex-M4", CURRENT_VERSION, ("mps2-an386", "cortex-m4")),
    "m85": ("Stage 3: TX6.5 / Cortex-M85", CURRENT_VERSION, None),
    "m55": ("Supplement: TX6.5 / Cortex-M55", CURRENT_VERSION, ("mps3-an547", "cortex-m55")),
}


def capture(command: list[str]) -> str:
    return subprocess.run(command, check=True, capture_output=True,
                          text=True).stdout


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeats", type=int, default=8)
    args = parser.parse_args()
    if args.repeats < 2:
        parser.error("--repeats must be at least 2")
    tx5_root = Path(os.environ.get("TX5_ROOT", ""))
    archive = tx5_root / "WICED/RTOS/ThreadX/ThreadX.ARM_CM4.release.a"
    if not archive.is_file():
        raise RuntimeError("Set TX5_ROOT to the external WICED SDK checkout")
    evidence = ROOT / "evidence"
    evidence.mkdir(exist_ok=True)
    llvm_size = shutil.which("llvm-size")
    if not llvm_size:
        raise RuntimeError("llvm-size must be on PATH")
    qemu = find_qemu()
    qemu_machines = capture([qemu, "-machine", "help"])
    qemu_cpus = capture([qemu, "-cpu", "help"])
    data = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "threadx_tag": "v6.5.2.202603_rel",
        "threadx_sha": capture(
            ["git", "-C", str(ROOT / "third_party/threadx"), "rev-parse", "HEAD"]).strip(),
        "tx5": {
            "version": TX5_VERSION,
            "source": "WICED SDK 3.1.0 prebuilt ThreadX.ARM_CM4.release.a (external, not redistributed)",
            "wiced_commit": WICED_COMMIT,
            "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        },
        "compiler": capture(["clang", "--version"]).splitlines()[0],
        "qemu": capture([qemu, "--version"]).splitlines()[0],
        "virtual_time_model": "QEMU icount shift=7,align=off,sleep=off; 128 ns/instruction",
        "measurement_limits": [
            "Host wall time includes emulator startup, guest sleep, and semihosting.",
            "Host timings are not CPU cycle, silicon throughput, or WCET measurements.",
            "M85 is compile/link only; there is no M85 runtime or stack measurement.",
            "TX5 and TX6 images use different kernel configurations; size deltas are not pure kernel growth.",
            "Stack high-water is measured by scanning the 0xEFEFEFEF stack fill pattern.",
        ],
        "builds": {}, "runs": {},
    }
    for core, (label, version, target) in BUILDS.items():
        elf = ROOT / f"build/{core}/threadx_gpio_demo.elf"
        if not elf.is_file():
            raise FileNotFoundError(elf)
        sections_text = capture([llvm_size, "-A", str(elf)])
        sections = {}
        for line in sections_text.splitlines():
            parts = line.split()
            if len(parts) == 3 and parts[0].startswith("."):
                sections[parts[0]] = int(parts[1])
        data["builds"][core] = {
            "stage": label, "threadx_version": version,
            "elf_sha256": hashlib.sha256(elf.read_bytes()).hexdigest(),
            "sections": sections,
            "rom_bytes": sum(sections.get(s, 0)
                             for s in [".vectors", ".text", ".ARM.exidx", ".data"]),
            "ram_reserved_bytes": sum(sections.get(s, 0)
                                      for s in [".data", ".bss", ".stack"]),
            "runtime_status": "PASS" if target else "NOT_RUN",
        }
        (evidence / f"{core}-sections.txt").write_text(sections_text, encoding="utf-8")
    runnable = [(core, version, target) for core, (_, version, target) in BUILDS.items() if target]
    samples = {core: [] for core, _, _ in runnable}
    # Interleave the images so host load affects each one equally.
    for index in range(args.repeats):
        for core, version, (machine, cpu) in runnable:
            print(f"Run {index + 1}/{args.repeats}: {core}", flush=True)
            samples[core].append(run(ROOT / f"build/{core}/threadx_gpio_demo.elf",
                                     machine, cpu, expected_version=version))
    for core, results in samples.items():
        times = [result["host_wall_seconds"] for result in results]
        intervals = [right["tick"] - left["tick"] for result in results
                     for left, right in zip(result["rows"], result["rows"][1:])]
        data["runs"][core] = {
            "repeats": args.repeats, "pass_count": len(results),
            "host_wall_seconds": times,
            "median_host_wall_seconds": statistics.median(times),
            "min_host_wall_seconds": min(times), "max_host_wall_seconds": max(times),
            "tick_intervals": intervals,
            "metrics": results[-1]["metrics"],
        }
        (evidence / f"{core}-run.json").write_text(
            json.dumps(results[-1], indent=2) + "\n", encoding="utf-8")
        (evidence / f"{core}-console.txt").write_text(results[-1]["log"], encoding="utf-8")
    (evidence / "qemu-machines.txt").write_text(qemu_machines, encoding="utf-8")
    (evidence / "qemu-cpus.txt").write_text(qemu_cpus, encoding="utf-8")
    (evidence / "summary.json").write_text(
        json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"Measured evidence written to {evidence}")


if __name__ == "__main__":
    main()
