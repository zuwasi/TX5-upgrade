"""Run and verify the ThreadX firmware, never treating a timeout as success."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
ROW = re.compile(
    r"cycle=(\d+) BTN0=(PRESSED|released) BTN1=(PRESSED|released) "
    r"LED0=(ON|OFF) LED1=(ON|OFF) tick=(\d+)"
)
CORE_PARTS = {"cortex-m4": 0xC24, "cortex-m55": 0xD22}


def find_qemu() -> str:
    candidates = [
        os.environ.get("QEMU_ARM"),
        shutil.which("qemu-system-arm"),
        r"C:\Program Files\qemu\qemu-system-arm.exe",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return candidate
    raise RuntimeError("Set QEMU_ARM or put qemu-system-arm on PATH")


def validate(text: str, core: str) -> list[dict]:
    if "[pass] bounded LED sequence completed" not in text or "[fail]" in text:
        raise AssertionError("Firmware did not report a clean successful completion")
    if "[selftest] queue/preemption/events/semaphore/mutex/byte-pool PASS" not in text:
        raise AssertionError("RTOS service self-test did not pass")
    if "Version 6.5.2.202603" not in text or f"[core] {core}" not in text:
        raise AssertionError("Wrong RTOS version or core identity")
    cpuid = re.search(r"\[metric\] cpuid=(\d+)", text)
    if not cpuid or ((int(cpuid[1]) >> 4) & 0xFFF) != CORE_PARTS[core]:
        raise AssertionError("Emulated CPUID does not match the requested core")
    matches = list(ROW.finditer(text))
    if len(matches) != 10:
        raise AssertionError(f"Expected 10 LED rows, got {len(matches)}")
    toggle = [False, False]
    rows = []
    first_tick = int(matches[0][6])
    for cycle, match in enumerate(matches):
        values = match.groups()
        if int(values[0]) != cycle:
            raise AssertionError("Cycle count is not consecutive")
        pressed = [cycle in (2, 3), cycle == 5]
        actual_buttons = [values[1] == "PRESSED", values[2] == "PRESSED"]
        if actual_buttons != pressed:
            raise AssertionError(f"Wrong virtual input at cycle {cycle}")
        for led in (0, 1):
            if not pressed[led]:
                toggle[led] = not toggle[led]
            expected = pressed[led] or toggle[led]
            if (values[led + 3] == "ON") != expected:
                raise AssertionError(f"LED{led} behavior mismatch at cycle {cycle}")
        tick = int(values[5])
        if tick != first_tick + cycle * 25:
            raise AssertionError(f"RTOS sleep tick interval mismatch at cycle {cycle}")
        rows.append({
            "cycle": cycle, "tick": tick,
            "buttons": pressed, "leds": [values[3] == "ON", values[4] == "ON"],
        })
    return rows


def run(elf: Path, machine: str, core: str, timeout: float = 20.0) -> dict:
    if not elf.is_file():
        raise FileNotFoundError(elf)
    qemu = find_qemu()
    command = [
        qemu, "-machine", machine, "-cpu", core,
        "-display", "none", "-monitor", "none", "-serial", "none",
        "-icount", "shift=7,align=off,sleep=off",
        "-semihosting-config", "enable=on,target=native", "-kernel", str(elf),
    ]
    start = time.perf_counter()
    completed = subprocess.run(
        command, capture_output=True, text=True, timeout=timeout, check=False,
    )
    elapsed = time.perf_counter() - start
    text = completed.stdout + completed.stderr
    if completed.returncode != 0:
        raise AssertionError(f"QEMU exit {completed.returncode}:\n{text}")
    rows = validate(text, core)
    return {
        "status": "PASS", "machine": machine, "core": core,
        "virtual_time_model": "QEMU icount shift=7 (128 ns per emulated instruction)",
        "host_wall_seconds": elapsed, "rows": rows, "log": text,
        "metrics": {name: int(value) for name, value in
                    re.findall(r"\[metric\] (\w+)=(\d+)", text)},
        "elf": str(elf.relative_to(ROOT)) if elf.is_relative_to(ROOT) else elf.name,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--elf", required=True, type=Path)
    parser.add_argument("--machine", required=True, choices=["mps2-an386", "mps3-an547"])
    parser.add_argument("--cpu", required=True, choices=list(CORE_PARTS))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = run(args.elf.resolve(), args.machine, args.cpu)
    except (AssertionError, OSError, RuntimeError, subprocess.TimeoutExpired) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print(result["log"], end="")
    print(f"PASS: host wall time {result['host_wall_seconds']:.3f}s "
          "(emulator measurement, not silicon performance)")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
