"""Collect measured build sizes and repeated QEMU runs for the presentation."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import statistics
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from run_qemu import find_qemu, run  # noqa: E402


def capture(command: list[str]) -> str:
    return subprocess.run(command, check=True, capture_output=True,
                          text=True).stdout


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeats", type=int, default=8)
    args = parser.parse_args()
    if args.repeats < 2:
        parser.error("--repeats must be at least 2")
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
        "compiler": capture(["clang", "--version"]).splitlines()[0],
        "qemu": capture([qemu, "--version"]).splitlines()[0],
        "virtual_time_model": "QEMU icount shift=7,align=off,sleep=off; 128 ns/instruction",
        "measurement_limits": [
            "Host wall time includes emulator startup, guest sleep, and semihosting.",
            "Host timings are not CPU cycle, silicon throughput, or WCET measurements.",
            "M85 is compile/link only; there is no M85 runtime or stack measurement.",
            "All compared images use ThreadX 6.5.2.202603; no TX5 runtime is included.",
            "Stack high-water values are observed through ThreadX stack checking.",
        ],
        "builds": {}, "runs": {},
    }
    for core in ["m4", "m55", "m85"]:
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
            "elf_sha256": hashlib.sha256(elf.read_bytes()).hexdigest(),
            "sections": sections,
            "rom_bytes": sum(sections.get(s, 0)
                             for s in [".vectors", ".text", ".ARM.exidx", ".data"]),
            "ram_reserved_bytes": sum(sections.get(s, 0)
                                      for s in [".data", ".bss", ".stack"]),
            "runtime_status": "NOT_RUN" if core == "m85" else "PASS",
        }
        (evidence / f"{core}-sections.txt").write_text(sections_text, encoding="utf-8")
    # Alternate the cores to avoid measuring all of one core under one host load.
    samples = {"m4": [], "m55": []}
    for index in range(args.repeats):
        for core, machine, cpu in [
            ("m4", "mps2-an386", "cortex-m4"),
            ("m55", "mps3-an547", "cortex-m55"),
        ]:
            print(f"Run {index + 1}/{args.repeats}: {cpu}", flush=True)
            result = run(ROOT / f"build/{core}/threadx_gpio_demo.elf", machine, cpu)
            samples[core].append(result)
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
