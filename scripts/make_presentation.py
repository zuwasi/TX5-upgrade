"""Generate the HTML deck, chart images and PDF specification from measured evidence."""
from __future__ import annotations

import base64
from collections import Counter
import html
import json
from pathlib import Path
from textwrap import dedent

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "presentation"
ASSETS = SITE / "assets"
BG = "#0b1424"
FG = "#eaf1fc"
MUTED = "#a7b8d2"
COLORS = ["#58c7fa", "#78e1b3", "#fdc573"]


def font(size=24, mono=False):
    windows = Path(r"C:\Windows\Fonts")
    choices = [windows / ("consola.ttf" if mono else "segoeui.ttf"),
               Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")]
    for candidate in choices:
        if candidate.is_file():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default(size=size)


class Figure:
    """Write the same chart/diagram as resolution-independent SVG and PDF PNG."""
    def __init__(self, width=1120, height=470):
        self.width, self.height = width, height
        self.image = Image.new("RGB", (width * 2, height * 2), BG)
        self.draw = ImageDraw.Draw(self.image)
        self.svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}"'
                    f' role="img"><rect width="{width}" height="{height}" fill="{BG}"/>']

    def text(self, x, y, text, size=22, color=FG, mono=False):
        self.draw.text((x * 2, y * 2), str(text), font=font(size * 2, mono), fill=color)
        family = "monospace" if mono else "sans-serif"
        self.svg.append(f'<text x="{x}" y="{y + size}" fill="{color}" '
                        f'font-family="{family}" font-size="{size}">'
                        f'{html.escape(str(text))}</text>')

    def rect(self, x, y, w, h, color):
        self.draw.rectangle((x * 2, y * 2, (x + w) * 2, (y + h) * 2), fill=color)
        self.svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{color}"/>')

    def line(self, x1, y1, x2, y2, color=MUTED):
        self.draw.line((x1 * 2, y1 * 2, x2 * 2, y2 * 2), fill=color, width=4)
        self.svg.append(f'<path d="M{x1},{y1} L{x2},{y2}" stroke="{color}" stroke-width="2"/>')

    def save(self, name):
        self.svg.append("</svg>")
        (ASSETS / f"{name}.svg").write_text("\n".join(self.svg), encoding="utf-8")
        self.image.save(ASSETS / f"{name}.png")


def bars(name, title, groups, values, unit, note):
    fig = Figure()
    fig.text(28, 18, title, 28)
    max_value = max(values) * 1.15
    for index, (label, value) in enumerate(zip(groups, values)):
        y = 94 + index * 92
        fig.text(28, y, label, 25)
        width = max(3, value / max_value * 650)
        fig.rect(195, y, width, 42, COLORS[index % len(COLORS)])
        fig.text(210 + width, y + 2, f"{value:,} {unit}", 23)
    fig.text(28, 407, note, 19, MUTED)
    fig.save(name)


def make_figures(evidence):
    builds, runs = evidence["builds"], evidence["runs"]
    bars("rom", "Linked ROM footprint (bytes)", ["M4", "M55", "M85*"],
         [builds[core]["rom_bytes"] for core in ("m4", "m55", "m85")], "B",
         "* M85: compile/link only. All three images use ThreadX 6.5.2.202603.")
    bars("ram", "Reserved RAM: .data + .bss + system stack", ["M4", "M55", "M85*"],
         [builds[core]["ram_reserved_bytes"] for core in ("m4", "m55", "m85")], "B",
         "Includes service tests, two task stacks and a 2 KiB system stack; not minimum RTOS RAM.")
    bars("stack", "Observed LED thread stack high-water", ["M4", "M55", "Reserved"],
         [runs["m4"]["metrics"]["led_stack_high_water_bytes"],
          runs["m55"]["metrics"]["led_stack_high_water_bytes"], 1024], "B",
         "ThreadX stack-check samples in this workload. M85 was not run; no M85 stack value.")

    fig = Figure()
    fig.text(28, 15, "Test execution cost on the host (not core performance)", 27)
    all_times = [t for run in runs.values() for t in run["host_wall_seconds"]]
    low, high = min(all_times) * 0.9, max(all_times) * 1.05
    for index, core in enumerate(("m4", "m55")):
        y = 125 + index * 125
        fig.text(30, y - 7, core.upper(), 26)
        for sample in runs[core]["host_wall_seconds"]:
            x = 190 + (sample - low) / (high - low) * 830
            fig.rect(x - 3, y, 6, 23, COLORS[index])
        median = runs[core]["median_host_wall_seconds"]
        x = 190 + (median - low) / (high - low) * 830
        fig.line(x, y - 18, x, y + 44, FG)
        fig.text(190, y + 49, f"median {median:.3f} s | 8 of 8 checks passed", 22, MUTED)
    fig.line(190, 361, 1030, 361)
    fig.text(185, 370, f"{low:.2f} s", 20, MUTED)
    fig.text(940, 370, f"{high:.2f} s", 20, MUTED)
    fig.text(28, 423, "Windows host; QEMU icount 128 ns/instruction. No silicon speedup inference.", 19, MUTED)
    fig.save("host-cost")

    fig = Figure()
    fig.text(28, 15, "Host-time histogram: eight alternating runs per core", 27)
    edges = [0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60]
    for index in range(len(edges) - 1):
        x = 160 + index * 145
        for core_index, core in enumerate(("m4", "m55")):
            count = sum(edges[index] <= t < edges[index + 1]
                        for t in runs[core]["host_wall_seconds"])
            height = count * 45
            fig.rect(x + core_index * 42, 330 - height, 34, height, COLORS[core_index])
            fig.text(x + core_index * 42, 298 - height, str(count), 20)
        fig.text(x - 5, 352, f"{edges[index]:.2f}-{edges[index+1]:.2f}", 17, MUTED)
    fig.text(45, 395, "M4", 20, COLORS[0])
    fig.text(120, 395, "M55", 20, COLORS[1])
    fig.text(260, 395, "Bins in host seconds; count = completed QEMU processes", 20, MUTED)
    fig.text(28, 430, "Distribution measures the test harness, not architectural latency or WCET.", 19, MUTED)
    fig.save("host-histogram")

    fig = Figure()
    fig.text(28, 15, "RTOS sleep interval histogram (virtual ticks)", 27)
    counts = Counter(runs["m4"]["tick_intervals"] + runs["m55"]["tick_intervals"])
    for index, interval in enumerate((24, 25, 26)):
        x = 250 + index * 240
        count = counts[interval]
        height = count / max(counts.values()) * 250
        fig.rect(x, 337 - height, 105, height, COLORS[1])
        fig.text(x + 25, 302 - height, str(count), 25)
        fig.text(x + 4, 349, f"{interval} ticks", 22, MUTED)
    fig.text(28, 407, "144 of 144 intervals = 25 ticks. Synthetic QEMU time; not sub-tick jitter.", 20, MUTED)
    fig.save("tick-histogram")

    fig = Figure(1120, 590)
    fig.text(24, 15, "Source structure: historical inputs vs public proof", 26)
    trees = [
        ("WICED 3.1.0 reference (not redistributed)", [
            "bcm-wiced-sdk/", "  apps/snip/gpio/",
            "    gpio.c [proprietary notice]", "  WICED/RTOS/ThreadX/",
            "    ver5.6/ [headers]",
            "    ThreadX.ARM_CM4.*.a [binary]",
            "  WICED/platform/MCU/STM32F4xx/",
            "  tools/ARM_GNU/", "  LICENSE.txt",
        ]),
        ("TX5-upgrade (MIT original work)", [
            "TX5-upgrade/", "  src/led_demo.c + rtos_selftest.c",
            "  src/startup.S + qemu_board.c",
            "  boards/qemu.ld",
            "  cmake/clang-arm-none-eabi.cmake",
            "  third_party/threadx/ [pinned MIT]",
            "    common/ + ports/cortex_m{4,55,85}",
            "  tests/ + evidence/ + scripts/",
            "  presentation/ + outputs/ + LICENSE",
        ]),
    ]
    for index, (heading, tree) in enumerate(trees):
        x = 25 + index * 555
        fig.text(x, 76, heading, 20, COLORS[index])
        for row, text in enumerate(tree):
            fig.text(x, 129 + row * 39, text, 19, mono=True)
    fig.save("source-trees")

    fig = Figure(1120, 540)
    fig.text(28, 18, "Migration workflow: separate OS, CPU and board concerns", 26)
    boxes = [
        (30, 110, "1. Audit TX5", "versions / rights / APIs"),
        (390, 110, "2. Replace RTOS", "pinned MIT ThreadX 6"),
        (750, 110, "3. Rebuild M4", "Clang + control run"),
        (750, 310, "4. Execute M55", "new port / same behavior"),
        (390, 310, "5. Compile M85", "runtime remains open"),
        (30, 310, "6. Board sign-off", "BSP / timing / FPU / IRQ"),
    ]
    for x, y, title, subtitle in boxes:
        fig.rect(x, y, 320, 108, "#182840")
        fig.text(x + 18, y + 17, title, 24, COLORS[0])
        fig.text(x + 18, y + 62, subtitle, 20)
    for a, b in [(0, 1), (1, 2), (3, 4), (4, 5)]:
        x1, y1, _, _ = boxes[a]
        x2, y2, _, _ = boxes[b]
        if x2 > x1:
            fig.line(x1 + 322, y1 + 55, x2 - 8, y2 + 55, COLORS[1])
            fig.text(x2 - 23, y2 + 33, ">", 24, COLORS[1])
        else:
            fig.line(x1 - 4, y1 + 55, x2 + 330, y2 + 55, COLORS[1])
            fig.text(x2 + 323, y2 + 33, "<", 24, COLORS[1])
    fig.line(910, 220, 910, 303, COLORS[1])
    fig.text(28, 475, "PoC completed through compile stage; silicon acceptance is a separate engineering gate.", 19, MUTED)
    fig.save("workflow")

    fig = Figure(1120, 520)
    fig.text(28, 20, "The executed path: real ThreadX, virtual board outputs", 27)
    for x, heading, detail in [
        (35, "Application", "LED latch + RTOS services"),
        (397, "ThreadX common", "ready lists / tick / IPC"),
        (759, "CPU port", "PendSV + task context"),
    ]:
        fig.rect(x, 112, 325, 100, "#182840")
        fig.text(x + 15, 128, heading, 24, COLORS[0])
        fig.text(x + 15, 172, detail, 18)
    for x in (363, 725):
        fig.text(x, 140, ">", 28, COLORS[1])
    fig.rect(150, 279, 810, 100, "#182840")
    fig.text(175, 292, "QEMU: Cortex-M4 or M55, NVIC, SysTick and memory", 24, COLORS[1])
    fig.text(175, 337, "Semihost adapter emits LED states; no physical GPIO driver", 21)
    fig.line(555, 215, 555, 270, COLORS[1])
    fig.text(28, 427, "Port + core model execute real firmware instructions. HTML replay uses saved console evidence.", 19, MUTED)
    fig.save("architecture")


def block(kind, **values):
    return {"kind": kind, **values}


def slides(e):
    b, r = e["builds"], e["runs"]
    s = []
    def add(title, subtitle, *blocks):
        s.append({"title": title, "subtitle": subtitle, "blocks": list(blocks)})
    p = lambda text: block("p", text=text)
    bullets = lambda *items: block("bullets", items=list(items))
    code = lambda text, label="": block("code", text=dedent(text).strip(), label=label)
    fig = lambda name, caption: block("figure", name=name, caption=caption)
    table = lambda heads, rows: block("table", heads=heads, rows=rows)
    note = lambda text: block("note", text=text)
    add("ThreadX 5.6 → current 6.x", "Cortex-M4 → modern Cortex-M, with executable evidence",
        p("A reproducible Clang + QEMU proof, not a promise of a full WICED board conversion."),
        table(["Target", "Evidence achieved"], [
            ["Cortex-M4 / ThreadX 6", "Compiled, linked, executed: 8/8 repeated runs"],
            ["Cortex-M55 / ThreadX 6", "Compiled, linked, executed: 8/8 repeated runs"],
            ["Cortex-M85 / ThreadX 6", "Compiled and linked only; no M85 runtime claim"]]),
        note("Start with the OS/core differences, then inspect the code changes and measured results. "
             "Use ← / →, touch arrows, or swipe. Home returns here."),
        block("toc"))
    add("ThreadX 5 and 6: what actually changes", "Same RTOS service concepts, different source / port / licensing baseline",
        table(["Concern", "WICED ThreadX 5.6", "Current Eclipse ThreadX 6.x"], [
            ["Kernel delivery", "CM3/CM4 prebuilt archives; headers", "Public common C source + CPU/toolchain ports"],
            ["Scheduling / services", "Threads, priority scheduling, queues, semaphores", "Same service families; retest semantics and configuration"],
            ["Architecture", "SDK contains a Cortex-M3/M4 port", "Pinned release contains M4, M55 and M85 ports"],
            ["Rights in this SDK", "WICED-only RTOS binary terms", "Current selected release has MIT license"],
            ["Integration", "Vendor SDK and old GNU build", "Rebuilt source, matching ABI, Clang + CMake"]]),
        note("This is an evidence-based comparison of the supplied SDK, not a claim that every ThreadX 5 "
             "distribution had identical ports or rights. Kernel source is absent from the historical SDK."))
    add("Why choose current 6.x for this project?", "Remove the opaque binary / port dependency before changing the core",
        bullets("We need source we can rebuild for the target ABI and freely share.",
                "The selected current release includes an upstream Cortex-M85 port.",
                "A pinned open source baseline enables review, regression tests and reproducible build evidence.",
                "Later 6.x versions include fixes and port updates; audit relevant release notes, do not freeze at the linked 2022 tag.",
                "An old licensed TX5 kernel could theoretically be custom-ported. That is different scope, risk and rights."),
        note("A version number alone does not make a product faster, secure, certified or production-ready. "
             "6.x is the practical source/port/licensing baseline for THIS public PoC."))
    add("The exact version, not a moving branch", "The linked 6.1.12 release is not the latest release",
        table(["Input", "Finding / decision"], [
            ["WICED reference", "SDK 3.1.0; ThreadX ver5.6; commit 0886ec932a063e12db768cd09428e8a8ab555bce"],
            ["User's ThreadX link", "v6.1.12_rel, 2022-era Azure RTOS release"],
            ["Selected new baseline", "v6.5.2.202603_rel, observed latest on 2026-10-11"],
            ["Pinned source commit", e["threadx_sha"]],
            ["License", "Current selected release: MIT; preserve upstream notices"]]),
        p("Do not swap in the older tag while assuming its checked-in license text is the same. "
          "The old tag contains hardware-linked Azure RTOS licensing language."),
        code("git submodule update --init --recursive\n"
             "git -C third_party/threadx rev-parse HEAD", "Reproduce the exact source selection"))
    add("Cortex-M4, M55 and M85", "Keep CPU architecture distinct from a particular microcontroller",
        table(["Property", "Cortex-M4", "Cortex-M55", "Cortex-M85"], [
            ["Architecture", "Armv7E-M", "Armv8.1-M", "Armv8.1-M"],
            ["DSP / vectors", "Scalar DSP extensions", "Helium / MVE", "Helium / MVE"],
            ["Floating point", "Optional single precision", "Configuration-dependent FP/MVE", "Configuration-dependent FP/MVE"],
            ["Security model", "No Armv8-M TrustZone", "Armv8-M TrustZone", "TrustZone; PACBTI capability/configuration"],
            ["This proof", "QEMU MPS2 AN386 run", "QEMU MPS3 AN547 run", "Compile/link only"]]),
        note("Core IP features and SoC implementations vary. A new core does not bring the old "
             "STM32F4 GPIO, clocks, memory addresses, DMA or board wiring with it."))
    add("Compatibility stops at the hardware boundary", "Portable C is only one layer of an RTOS migration",
        bullets("Recompile all RTOS-facing code and control blocks; never relink a CM4 binary on the strength of API names.",
                "Match CPU, Thumb ISA, float ABI, kernel flags and stack alignment across every translation unit.",
                "Verify exception return, PSP/MSP context, IRQ priorities and SysTick routing.",
                "Plan the SoC linker map, VTOR, caches/TCM, MPU, TrustZone and DMA coherency separately.",
                "Test FPU/MVE task switching and security state on real M85 hardware before claiming those paths."),
        code("""
            -mcpu=cortex-m4   # same-release control build
            -mcpu=cortex-m55  # executable QEMU proof
            -mcpu=cortex-m85  # compile/link proof only
            # common: --target=arm-none-eabi -mthumb -mfloat-abi=hard
        """, "Compiler target change, not a complete BSP port"))
    add("The most modern runnable QEMU Cortex-M here", "Probe the installed executable instead of relying on development docs",
        code("""
            qemu-system-arm --version
            qemu-system-arm -machine help
            qemu-system-arm -cpu help
            # installed: 11.1.0
            # present: mps3-an547 / cortex-m55
            # absent:  mps3-an555 / cortex-m85
        """, "Actual local inventory, saved in evidence/qemu-*.txt"),
        p("M55 is the newest Cortex-M CPU exposed by this installed QEMU build. "
          "QEMU development documentation mentions AN555, but it is not available in the tested binary."),
        note("We never run an M85 image under an M55 CPU and label it M85. "
             "The M85 ELF remains a separate, explicitly unexecuted build artifact."))
    add("Licensing is an engineering input", "Public GitHub visibility does not imply permission to redistribute",
        bullets("The supplied GPIO .c and .mk files explicitly carry proprietary Broadcom notices.",
                "The SDK README says its ThreadX / NetX objects are free for WICED use only.",
                "No proprietary GPIO file, TX5 archive, Wi-Fi firmware or restricted vendor stack is included.",
                "The new demo is independently written to preserve the LED/button behavior.",
                "Original work uses MIT; the pinned ThreadX source retains its upstream MIT license.",
                "PDF typography embeds open-source Roboto fonts under OFL 1.1, with notices shipped beside the PDF.",
                "Clang and QEMU are external tools, not firmware components relicensed as MIT."),
        note("This proves the migration approach on shareable code. It does not claim the complete old "
             "WICED SDK is OSS or that a technical audit replaces legal review."))
    add("The source trees tell the migration story", "Remove a binary dependency; preserve a narrow behavioral contract",
        fig("source-trees", "Historical tree is descriptive only. The old Broadcom source and binaries are not redistributed."),
        note("One pinned RTOS dependency; original application, startup, adapter, build scripts and evidence are reviewable."))
    add("Upgrade in separate dimensions", "Avoid attributing an OS change to a CPU change",
        fig("workflow", "Control: ThreadX 6 on M4. New runtime proof: same ThreadX 6 on M55. M85: same source, separate port build."),
        p("The TX5 reference is a behavior/source-inventory baseline, not a runnable benchmark baseline. "
          "Separating the dimensions makes the remaining hardware work visible."))
    add("What really executes", "No mock RTOS, no fake emulator success",
        fig("architecture", "Clang-built ARM firmware uses real ThreadX scheduler and service code under QEMU."),
        note("The board adapter virtualizes two LEDs and deterministic active-low buttons. "
             "It does not emulate or access a physical GPIO controller."))
    add("Diff 1: RTOS delivery and build", "A conceptual integration diff, not copied proprietary SDK code",
        code("""
            - RTOS input: opaque ThreadX.ARM_CM4.release.a
            - Toolchain: vendor SDK make + legacy GNU assumptions
            + RTOS input: pinned third_party/threadx/common + selected CPU port
            + add_subdirectory(third_party/threadx)
            + target_link_libraries(threadx_gpio_demo PRIVATE threadx)
            + Clang C + integrated assembler + LLD
            + --target=arm-none-eabi -mcpu=<selected core>
        """, "Build-layer migration, representative rather than an applied WICED patch"),
        p("Source rebuild avoids mixing TX5 headers with TX6 object layouts. Kernel configuration "
          "comes from a single tx_user.h shared by the library and application."))
    add("Diff 2: task lifecycle is explicit", "Initialize static objects before allowing the scheduler to run",
        code("""
            - application behavior entered through vendor SDK startup
            + int main(void) { tx_kernel_enter(); /* never returns */ }
            + void tx_application_define(void *unused) {
            +     tx_thread_create(&led_thread, "gpio-led-demo",
            +         led_thread_entry, 0, led_thread_stack,
            +         sizeof led_thread_stack, 5, 5,
            +         TX_NO_TIME_SLICE, TX_AUTO_START);
            + }
        """, "Representative lifecycle diff; implementation checks every creation status"),
        bullets("Lower numeric priority is higher priority in ThreadX.",
                "Stack storage is static and aligned as ULONG; lifetime exceeds the task.",
                "Application and RTOS objects are freshly compiled, not ABI-reused."))
    add("Diff 3: milliseconds versus RTOS ticks", "Keep units visible; avoid a silent tenfold or hundredfold delay error",
        code("""
            - delay API accepts 250 milliseconds
            + #define TX_TIMER_TICKS_PER_SECOND 100
            + #define LED_UPDATE_TICKS 25U
            + tx_thread_sleep(LED_UPDATE_TICKS);   // 250 ms virtual time
            + SysTick reload = DEMO_CLOCK_HZ / 100 - 1
            + SysTick_Handler -> _tx_timer_interrupt
        """, "Timing integration diff, plus a measured tick invariant"),
        p("The tested board clock constants are 25 MHz for MPS2-M4 and 32 MHz for MPS3-M55. "
          "The M85 build reuses the demonstration map/clock; a real M85 SoC must replace them."),
        note("QEMU icount is synthetic: 128 ns per emulated instruction. "
             "The tick invariant is a scheduler test, not a physical time or jitter guarantee."))
    add("Diff 4: preserve the held-button latch", "A subtle behavioral detail, checked at release as well as press",
        code("""
            - toggle the same boolean even while the button is held
            + if (!button0) toggle0 = !toggle0;
            + output0 = button0 || toggle0;
            + qemu_led_set(0, output0);
            # cycle 1: latch OFF / output OFF
            # cycles 2-3: latch unchanged / held button forces ON
            # cycle 4: button released / next toggle yields ON
        """, "Actual correction in the new application, not a TX5 kernel diff"),
        p("The reference behavior pauses the toggle latch while the button is held. "
          "An implementation that merely sets the latch true while held changes the release behavior."),
        note("The verifier deliberately rejects a cycle-4 OFF result."))
    add("Diff 5: startup assembly under Clang", "A real encountered failure, with a trace-supported fix",
        code("""
            - sub r2, r2, r1   // Clang emitted sub.w, without updating flags
            - beq copy_done    // branches on stale flags
            - sub r2, r2, #1   // same hidden flag dependency
            - bne copy_loop    // loop fails to terminate
            + copy_loop:
            +     cmp r1, r2   // explicit end-pointer comparison
            +     bhs copy_done
            +     ldrb r3, [r0], #1
            +     strb r3, [r1], #1
            +     b copy_loop
        """, "Compared to the current MIT upstream example startup, not Broadcom source"),
        p("QEMU traced a precise bus fault at 0x00080000 during the endless startup copy. "
          "The replacement has explicit comparisons, copies .data, clears .bss, and enables CP10/CP11."),
        note("Changing compiler is not just changing an executable name. Assembly flag semantics need testing."))
    add("Diff 6: one security mode and one ABI", "Scope down the first proof; make omitted features explicit",
        code("""
            + // include/tx_user.h: compiled into kernel AND application
            + #define TX_SINGLE_MODE_SECURE
            + #define TX_TIMER_TICKS_PER_SECOND 100
            + #define TX_ENABLE_STACK_CHECKING
            + // no secure/non-secure task transitions in this demo
            + // use hard-float ABI consistently; enable CP10/CP11 at reset
        """, "Actual demonstrator configuration"),
        bullets("Single-secure avoids falsely exercising secure-stack allocation paths without a non-secure image.",
                "Hard-float compile/link is established; dedicated mixed FPU/MVE context stress remains pending.",
                "SVC is unused in this configuration; PendSV handles context switching.",
                "Do not infer a TrustZone security policy from a successful boot."))
    add("Diff 7: IRQ, vectors and memory belong to the BSP", "Minimal executable map now; production SoC map later",
        code("""
            + .vectors: initial MSP, Reset, faults, PendSV, SysTick
            + VTOR = address of demo_vectors
            + PendSV priority = 0xff; SysTick priority = 0x40
            + CODE: 0x00000000, 512 KiB
            + RAM:  0x20000000, 32 KiB
            + system stack: 2048 bytes, 8-byte aligned
            + linker ASSERT: reserved RAM must fit
        """, "boards/qemu.ld + src/startup.S + src/tx_initialize_low_level.c"),
        note("These are demonstrator settings, not a claimed M85 board port. "
             "A Cortex-M85 core can appear in SoCs with different memory, clocks, controllers and IRQ routing."))
    add("Diff 8: success becomes a checked contract", "Fail on missing, wrong or partial output",
        code("""
            - visually inspect a blinking LED and assume migration works
            + verify CPUID part number and RTOS version
            + require queue / event / semaphore / mutex / pool self-test PASS
            + check all 10 button + LED rows
            + require 9 intervals of exactly 25 virtual ticks
            + require explicit completion and QEMU exit status 0
            + reject timeout, wrong identity, wrong state or partial log
        """, "tests/run_qemu.py + 11 verifier unit tests"),
        p("One positive verifier fixture plus ten deliberately corrupted fixtures pass their expected assertions. "
          "The firmware's real run is tested separately through CTest."))
    add("The RTOS services really switch tasks", "A higher-priority worker must suspend, resume and signal",
        code("""
            // LED task priority 5; worker priority 4
            worker: tx_queue_receive(&queue, &value, TX_WAIT_FOREVER);
                    assert(value == 0x1234);
                    tx_event_flags_set(&flags, 1, TX_OR);
            LED:    tx_queue_send(&queue, &message, TX_NO_WAIT);
                    tx_event_flags_get(&flags, 1, TX_OR_CLEAR,
                                       &actual, TX_NO_WAIT);
            // observed: worker_thread_runs = 2; led_thread_runs = 12
        """, "Condensed from the independently written service self-test"),
        bullets("Worker creation preempts the LED task; an empty queue suspends the worker.",
                "Sending the payload resumes the worker; the event proves execution reached the receiver.",
                "The timer wakes the sleeping LED task nine times through the real ThreadX timer path.",
                "Mutex and pool checks are basic operations, not exhaustive contention/fragmentation stress."))
    add("Replay the verified LED run", "Recorded QEMU evidence, not a browser-side ARM emulator",
        block("replay"),
        p("Two buttons are scripted active-low inputs. Buttons force their paired LED on while held; "
          "the paused toggle resumes after release. Step through cycles 0–9."),
        note("The replay data is embedded from evidence/m55-run.json, after the host verifier accepted it."))
    add("A visible runtime result", "Cortex-M55 console evidence from the final measured image",
        code((ROOT / "evidence/m55-console.txt").read_text(encoding="utf-8"),
             "Actual QEMU console, not generated example output"))
    add("Memory chart: linked ROM", "Clang -O3; same RTOS release, same app and service tests",
        fig("rom", "ROM = .vectors + .text (including constants) + .ARM.exidx + .data load image."),
        p(f'M4: {b["m4"]["rom_bytes"]:,} B; M55: {b["m55"]["rom_bytes"]:,} B; '
          f'M85 compile-only: {b["m85"]["rom_bytes"]:,} B.'),
        note("No TX5 size delta is claimed. These are actual ELF sections for this instrumented workload, "
             "not marketing estimates or minimum kernel footprints."))
    add("Memory chart: reserved RAM", "Include stacks and test infrastructure, not only global data",
        fig("ram", "RAM = .data + .bss + 2 KiB system stack. Static task stacks are already inside .bss."),
        p("The M4 and M55 runtime report sizeof(TX_THREAD) = 180 bytes in this build configuration. "
          "That observation is not permission to treat every TX5 or differently configured TCB as ABI-compatible."))
    add("Stack headroom is measured, not assumed", "Useful early evidence; not production stack qualification",
        fig("stack", "Observed LED thread stack high-water under the test workload; 1024 bytes reserved."),
        note("Values are ThreadX stack-check samples. Production worst-case paths, nested interrupts, "
             "FPU/MVE context and M85 behavior still require stress and hardware validation."))
    add("Performance chart: emulator test cost", "Measure what was actually run, and state what the number means",
        fig("host-cost", "Eight alternating QEMU runs per core on this Windows host, using deterministic icount."),
        note("These host durations include launch, TCG, virtual sleeps, self-tests and console I/O. "
             "They do not measure M4/M55 throughput, context-switch cycles, interrupt latency or M85 speed."))
    add("Histogram: repeatability of the host harness", "Samples are retained, not reduced to an unexplained mean",
        fig("host-histogram", "Every plotted sample is in evidence/summary.json."),
        p("Use this to budget an automated test job and spot test-host variability. "
          "Do not turn the median difference into a CPU performance claim."))
    add("Histogram: scheduler timing contract", "144 measured intervals, all at the requested 25 ticks",
        fig("tick-histogram", "8 runs × 9 intervals × 2 cores = 144 intervals, all 25 virtual ticks."),
        note("The 100 Hz tick gives 250 ms in the configured virtual-time model. "
             "Tick quantization and synthetic instruction time cannot establish physical sub-tick jitter."))
    add("What the M85 build proves", "Correct target attributes and resolved symbols, not execution",
        code("""
            llvm-readelf -A build/m85/threadx_gpio_demo.elf
            CPU_name: cortex-m85
            CPU_arch: ARM v8.1-M Mainline
            ABI_VFP_args: AAPCS VFP
            MVE_arch: MVE integer and float
            llvm-nm --undefined-only build/m85/threadx_gpio_demo.elf
            # no undefined symbols
        """, "Actual attribute inspection; build uses upstream ports/cortex_m85/gnu"),
        p("This establishes that Clang compiled and LLD linked the application with the M85 port. "
          "The demo linker/clock are not a production M85 SoC definition."),
        note("There is no M85 runtime, performance, power, PACBTI or mixed FPU/MVE correctness result."))
    add("The hardware acceptance gate", "Turn this PoC into a product migration with explicit tests",
        table(["Workstream", "Required evidence before production"], [
            ["Board / SoC", "Vendor-approved startup, linker map, GPIO polarity, clock tree, IRQ map"],
            ["Context / ABI", "Stress preemption + nested IRQ + mixed scalar/FPU/MVE tasks; inspect saved context"],
            ["Security", "TrustZone policy, secure gateways/stacks, MPU and optional PACBTI configuration"],
            ["Performance", "On-silicon cycles, IRQ latency distribution, deadline/WCET, throughput and energy"],
            ["Application", "Regression suite for peripheral, network, watchdog and low-power interactions"],
            ["Governance", "Licensing, SBOM, safety/change-impact assessment, traceable requirements"]]),
        note("The LED PoC reduces feasibility risk. It is not a claim that Wi-Fi, TLS, OTA, "
             "safety certification or all application deadlines have migrated."))
    add("Reproduce the result", "Public source, pinned dependency, raw evidence and automated checks",
        code("""
            git clone --recurse-submodules https://github.com/zuwasi/TX5-upgrade.git
            cd TX5-upgrade
            cmake --preset m4 && cmake --build --preset m4
            cmake --preset m55 && cmake --build --preset m55
            cmake --preset m85 && cmake --build --preset m85
            ctest --test-dir build/m4 --output-on-failure
            ctest --test-dir build/m55 --output-on-failure
            python -m unittest discover -s tests -p test_verifier.py -v
            python scripts/collect_evidence.py --repeats 8
        """, "Tools: Clang/LLVM, LLD, CMake, Ninja, Python and ARM QEMU"),
        p("The GitHub workflow uses a Linux package toolchain, so CI tool versions may differ from "
          "the recorded Windows Clang 22.1.3 / QEMU 11.1.0 measurements. Local evidence lists exact versions."),
        note("Only run firmware you trust with host semihosting enabled."))
    add("The technical conclusion", "A bounded yes, backed by executable evidence",
        bullets("YES: the legacy GPIO behavior is implementable on current MIT ThreadX.",
                "YES: the same application and service tests execute on M4 and modern M55 QEMU targets.",
                "YES: Clang compiles and links the same application using the upstream Cortex-M85 port.",
                "NOT YET: M85 runtime and real-board BSP / timing / security qualification.",
                "NEXT: choose the actual M85 SoC and run the hardware acceptance suite."),
        note("Approve a hardware migration spike with measurable exit criteria, "
             "rather than treating a successful LED demo as a full-product release."),
        p("Public source: github.com/zuwasi/TX5-upgrade\n"
          "Presentation: zuwasi.github.io/Public-html-pages/tx5-upgrade/"))
    add("Sources and evidence trail", "Primary references and local measured artifacts",
        block("sources", items=[
            ("Historical WICED SDK", "https://github.com/wwwllllllll/bcm-wiced-sdk"),
            ("Historical GPIO behavior reference", "https://github.com/wwwllllllll/bcm-wiced-sdk/tree/master/apps/snip/gpio"),
            ("Originally linked ThreadX release", "https://github.com/eclipse-threadx/threadx/tree/v6.1.12_rel"),
            ("Selected release", "https://github.com/eclipse-threadx/threadx/tree/v6.5.2.202603_rel"),
            ("ThreadX release history", "https://github.com/eclipse-threadx/threadx/releases"),
            ("Current MIT license", "https://github.com/eclipse-threadx/threadx/blob/v6.5.2.202603_rel/LICENSE.txt"),
            ("Arm Cortex-M85", "https://www.arm.com/products/silicon-ip-cpu/cortex-m/cortex-m85"),
            ("Arm M-profile architecture", "https://www.arm.com/architecture/cpu/m-profile"),
            ("Arm Helium", "https://www.arm.com/technologies/helium"),
            ("QEMU MPS2/MPS3 development docs", "https://qemu-project.gitlab.io/qemu/system/arm/mps2.html"),
            ("Raw measurements", "evidence/summary.json"),
            ("M55 verified console", "evidence/m55-console.txt"),
            ("M4 verified console", "evidence/m4-console.txt"),
        ]),
        note("License/source inventory was checked on 2026-10-11. Runtime evidence includes exact "
             "compiler, emulator version, image hashes and the virtual-time model."))
    return s


def render_block(b):
    kind = b["kind"]
    esc = html.escape
    if kind == "p":
        return f'<p>{esc(b["text"]).replace(chr(10), "<br>")}</p>'
    if kind == "note":
        return f'<aside class="note">{esc(b["text"])}</aside>'
    if kind == "bullets":
        return '<ul>' + "".join(f"<li>{esc(item)}</li>" for item in b["items"]) + "</ul>"
    if kind == "code":
        lines = []
        for line in b["text"].splitlines():
            css = "add" if line.startswith("+") else "remove" if line.startswith("- ") else ""
            lines.append(f'<span class="{css}">{esc(line)}</span>')
        return f'<figure class="code"><figcaption>{esc(b["label"])}</figcaption><pre><code>' + \
            "\n".join(lines) + "</code></pre></figure>"
    if kind == "table":
        head = "".join(f"<th scope='col'>{esc(h)}</th>" for h in b["heads"])
        rows = "".join("<tr>" + "".join(f"<td>{esc(str(v))}</td>" for v in row) + "</tr>"
                       for row in b["rows"])
        return f'<div class="table-scroll"><table><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div>'
    if kind == "figure":
        return f'<figure><img src="assets/{b["name"]}.svg" alt="{esc(b["caption"])}">' \
            f'<figcaption>{esc(b["caption"])}</figcaption></figure>'
    if kind == "sources":
        return '<ul class="sources">' + "".join(
            f'<li><a href="{esc(url)}">{esc(title)}</a></li>' for title, url in b["items"]) + "</ul>"
    if kind == "toc":
        return '<div id="toc" class="toc"></div>'
    if kind == "replay":
        return """<div class="replay" aria-label="Recorded QEMU LED evidence replay">
          <div class="replay-top"><strong>QEMU M55 · verified recording</strong>
            <span id="replay-cycle">Cycle 0 / tick 0</span></div>
          <div class="board"><div><span id="led0" class="led"></span><b>LED 0</b>
            <span id="button0" class="button-state"></span></div>
          <div><span id="led1" class="led"></span><b>LED 1</b>
            <span id="button1" class="button-state"></span></div></div>
          <pre id="replay-row"></pre><div class="replay-actions">
          <button id="replay-play">Play recorded sequence</button>
          <button id="replay-step">Step</button><button id="replay-reset">Reset</button>
          </div></div>"""
    raise ValueError(kind)


def pdf_spec(deck):
    content = []
    for index, slide in enumerate(deck):
        heading = {"text": f'{index + 1:02d}  {slide["title"]}', "style": "h1"}
        if index:
            heading["pageBreak"] = "before"
        content += [heading, {"text": slide["subtitle"], "style": "subtitle"}]
        for b in slide["blocks"]:
            kind = b["kind"]
            if kind == "toc":
                content.append({"text": "Navigate in the interactive edition with arrows, swipe and Home. "
                                "This PDF contains every slide in sequence.", "style": "note"})
            elif kind == "replay":
                rows = json.loads((ROOT / "evidence/m55-run.json").read_text(encoding="utf-8"))["rows"]
                body = [["Cycle", "Tick", "Button 0", "Button 1", "LED 0", "LED 1"]]
                for row in rows:
                    body.append([str(row["cycle"]), str(row["tick"])] +
                                ["held" if value else "released" for value in row["buttons"]] +
                                ["ON" if value else "OFF" for value in row["leds"]])
                content.append({"table": {"headerRows": 1, "widths": ["auto"] * 6, "body": body},
                                "layout": "lightHorizontalLines", "fontSize": 11})
            elif kind in ("p", "note"):
                content.append({"text": b["text"], "style": kind})
            elif kind == "bullets":
                content.append({"ul": b["items"], "style": "p"})
            elif kind == "code":
                content += [{"text": b["label"], "style": "label"},
                            {"text": b["text"], "style": "code"}]
            elif kind == "table":
                head = [{"text": text, "bold": True, "color": "#126085"} for text in b["heads"]]
                content.append({"table": {"headerRows": 1,
                                "widths": ["*"] * len(head), "body": [head] + b["rows"]},
                                "layout": "lightHorizontalLines", "fontSize": 11,
                                "margin": [0, 4, 0, 15]})
            elif kind == "figure":
                encoded = base64.b64encode((ASSETS / f'{b["name"]}.png').read_bytes()).decode()
                content += [{"image": f"data:image/png;base64,{encoded}", "fit": [690, 325]},
                            {"text": b["caption"], "style": "label"}]
            elif kind == "sources":
                content.append({"ul": [
                    {"text": f"{title}: {url}", "link": url} for title, url in b["items"]
                ], "fontSize": 10, "margin": [0, 6, 0, 10]})
    definition = {
        "pageSize": "A4", "pageOrientation": "landscape",
        "pageMargins": [46, 42, 46, 36],
        "info": {"title": "ThreadX 5.6 to 6.x: Cortex-M migration proof",
                 "author": "zuwasi", "subject": "Clang / QEMU migration evidence"},
        "defaultStyle": {"font": "Roboto", "fontSize": 13, "color": "#182840"},
        "styles": {
            "h1": {"fontSize": 25, "bold": True, "color": "#103a5e", "margin": [0, 0, 0, 9]},
            "subtitle": {"fontSize": 14, "color": "#56718b", "margin": [0, 0, 0, 20]},
            "p": {"fontSize": 13, "lineHeight": 1.15, "margin": [0, 7, 0, 12]},
            "note": {"fontSize": 11, "color": "#80551a", "margin": [0, 9, 0, 8]},
            "code": {"fontSize": 10, "lineHeight": 1.15, "margin": [0, 5, 0, 16]},
            "label": {"fontSize": 10, "color": "#56718b", "margin": [0, 5, 0, 9]},
        },
        "footer": {"text": "ThreadX migration proof · MIT original work · M85 runtime remains unverified",
                   "alignment": "center", "fontSize": 8, "color": "#6c7e91"},
        "content": content,
    }
    # The bundled Roboto font does not map every arrow for selectable PDF text.
    # Keep symbols in the HTML deck, use explicit words in the PDF.
    return json.loads(json.dumps(definition, ensure_ascii=False).replace(
        "→", "to").replace("←", "left"))


def main():
    ASSETS.mkdir(parents=True, exist_ok=True)
    evidence = json.loads((ROOT / "evidence/summary.json").read_text(encoding="utf-8"))
    make_figures(evidence)
    deck = slides(evidence)
    sections = []
    for index, slide in enumerate(deck):
        sections.append(f'<section class="slide" id="slide-{index + 1}" '
                        f'aria-labelledby="title-{index}">'
                        f'<div class="eyebrow">THREADX / ARM MIGRATION · {index + 1:02d}</div>'
                        f'<h1 id="title-{index}">{html.escape(slide["title"])}</h1>'
                        f'<p class="subtitle">{html.escape(slide["subtitle"])}</p>'
                        + "".join(render_block(b) for b in slide["blocks"]) + "</section>")
    replay = json.loads((ROOT / "evidence/m55-run.json").read_text(encoding="utf-8"))["rows"]
    document = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'none'; object-src 'none'; base-uri 'none'">
<meta name="description" content="Technical ThreadX 5.6 to current 6.x and Cortex-M migration proof: Clang builds, QEMU tests, code diffs and measured evidence.">
<title>ThreadX 5.6 → 6.x | Cortex-M migration proof</title>
<link rel="stylesheet" href="deck.css"><script src="deck.js" defer></script></head>
<body><header class="topbar"><a href="#slide-1" id="brand">TX5 → TX6 · Engineering proof</a>
<div><a href="threadx-migration.pdf">Download PDF</a>
<a href="https://github.com/zuwasi/TX5-upgrade">Source</a>
<a href="https://zuwasi.github.io/Public-html-pages/">Site home</a></div></header>
<main id="deck">""" + "\n".join(sections) + """</main>
<nav class="controls" aria-label="Slide navigation">
<button id="home" aria-label="Go to first slide">Home</button>
<button id="prev" aria-label="Previous slide">← Previous</button>
<span id="position" aria-live="polite"></span>
<button id="next" aria-label="Next slide">Next →</button></nav>
<script type="application/json" id="recorded-run">""" + json.dumps(replay) + """</script>
<noscript><p class="nojs">JavaScript is disabled. All slides remain readable below. Download the PDF for an offline copy.</p></noscript>
</body></html>"""
    (SITE / "index.html").write_text(document, encoding="utf-8")
    (SITE / "slides.json").write_text(json.dumps(deck, indent=2) + "\n", encoding="utf-8")
    for name in ["summary.json", "m55-console.txt", "m4-console.txt",
                 "qemu-machines.txt", "qemu-cpus.txt"]:
        target = SITE / "evidence" / name
        target.parent.mkdir(exist_ok=True)
        target.write_bytes((ROOT / "evidence" / name).read_bytes())
    (SITE / "licenses").mkdir(exist_ok=True)
    (SITE / "licenses/Roboto-OFL.txt").write_bytes(
        (ROOT / "licenses/Roboto-OFL.txt").read_bytes())
    (SITE / "LICENSE").write_bytes((ROOT / "LICENSE").read_bytes())
    (SITE / "THIRD_PARTY_NOTICES.md").write_bytes(
        (ROOT / "THIRD_PARTY_NOTICES.md").read_bytes())
    temp = ROOT / "tmp"
    temp.mkdir(exist_ok=True)
    (temp / "threadx-migration.pdf.json").write_text(
        json.dumps(pdf_spec(deck), ensure_ascii=False), encoding="utf-8")
    print(f"Generated {len(deck)} technical slides and 9 chart/diagram assets")


if __name__ == "__main__":
    main()
