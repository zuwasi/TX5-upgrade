"""Generate the HTML deck, chart images and PDF specification from measured evidence."""
from __future__ import annotations

import base64
from collections import Counter
import html
import json
import math
from pathlib import Path
from textwrap import dedent

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "presentation"
ASSETS = SITE / "assets"
BG = "#2d2d2d"
FG = "#f5f5f5"
MUTED = "#bdbdbd"
# ESL brand: amber #ffb30b, blue #4f9efb, charcoal #2d2d2d (from the ESL logo).
COLORS = ["#ffb30b", "#4f9efb", "#9cc8fd", "#d3e7ff"]
# Evidence key -> chart label, in migration order.
STAGES = [("tx5-m4", "TX5 M4"), ("m4", "TX6 M4"), ("m85", "TX6 M85*"), ("m55", "TX6 M55+")]
RUNS = [("tx5-m4", "TX5 M4"), ("m4", "TX6 M4"), ("m55", "TX6 M55+")]
ESL_SITE = "https://eswlab.com/"
ESL_CONTACT = "https://eswlab.com/contact-us/"
DANIEL_LINKEDIN = "https://www.linkedin.com/in/liezrowice/"
LOGO = "assets/esl-logo.png"
PHOTO = "assets/daniel-liezrowice.jpg"
CHARCOAL, BLUE, AMBER = "#2d2d2d", "#4f9efb", "#ffb30b"


def data_uri(asset):
    kind = "png" if asset.endswith(".png") else "jpeg"
    return f"data:image/{kind};base64," + base64.b64encode((SITE / asset).read_bytes()).decode()


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


def bars(name, title, groups, values, unit, note, colors=None):
    fig = Figure()
    fig.text(28, 18, title, 28)
    max_value = max(values) * 1.15
    step = 300 / len(values)
    for index, (label, value) in enumerate(zip(groups, values)):
        y = 86 + index * step
        fig.text(28, y, label, 23)
        width = max(3, value / max_value * 640)
        fig.rect(205, y, width, step * 0.55, (colors or COLORS)[index % len(COLORS)])
        fig.text(220 + width, y + 2, f"{value:,} {unit}", 22)
    fig.text(28, 405, note, 18, MUTED)
    fig.save(name)


def make_figures(evidence):
    builds, runs = evidence["builds"], evidence["runs"]
    labels = [label for _, label in STAGES]
    bars("rom", "Linked ROM footprint (bytes)", labels,
         [builds[key]["rom_bytes"] for key, _ in STAGES], "B",
         "* compile/link only.  + supplemental QEMU core.  TX5 and TX6 kernel configurations differ.")
    bars("ram", "Reserved RAM: .data + .bss + system stack", labels,
         [builds[key]["ram_reserved_bytes"] for key, _ in STAGES], "B",
         "Includes service tests, two task stacks and a 2 KiB system stack; not minimum RTOS RAM.")
    bars("stack", "Observed LED thread stack high-water (fill-pattern scan)",
         [label for _, label in RUNS] + ["Reserved"],
         [runs[key]["metrics"]["led_stack_high_water_bytes"] for key, _ in RUNS] + [1024], "B",
         "Deepest write below the 0xEF fill in this workload. M85 was not run; no M85 value.",
         COLORS[:2] + COLORS[3:] + ["#6b6b6b"])

    fig = Figure()
    fig.text(28, 15, "Test execution cost on the host (not core performance)", 27)
    all_times = [t for key, _ in RUNS for t in runs[key]["host_wall_seconds"]]
    low, high = min(all_times) * 0.85, max(all_times) * 1.05
    run_colors = [COLORS[0], COLORS[1], COLORS[3]]
    for index, (key, label) in enumerate(RUNS):
        y = 95 + index * 95
        fig.text(28, y - 7, label, 23)
        for sample in runs[key]["host_wall_seconds"]:
            x = 200 + (sample - low) / (high - low) * 820
            fig.rect(x - 3, y, 6, 22, run_colors[index])
        median = runs[key]["median_host_wall_seconds"]
        x = 200 + (median - low) / (high - low) * 820
        fig.line(x, y - 14, x, y + 38, FG)
        fig.text(200, y + 38, f"median {median:.3f} s | {runs[key]['pass_count']} of "
                 f"{runs[key]['repeats']} checks passed", 19, MUTED)
    fig.line(200, 372, 1020, 372)
    fig.text(195, 380, f"{low:.2f} s", 19, MUTED)
    fig.text(935, 380, f"{high:.2f} s", 19, MUTED)
    fig.text(28, 428, "TX5 idles in WFI (fast-forwarded by QEMU); TX6 idles in a spin loop. Harness cost only.", 18, MUTED)
    fig.save("host-cost")

    fig = Figure()
    fig.text(28, 15, "Host-time histogram: eight interleaved runs per image", 27)
    start = math.floor(min(all_times) / 0.05) * 0.05
    stop = math.ceil(max(all_times) / 0.05) * 0.05
    edges = [round(start + 0.05 * i, 2) for i in range(round((stop - start) / 0.05) + 1)]
    spacing = 900 / (len(edges) - 1)
    for index in range(len(edges) - 1):
        x = 150 + index * spacing
        for run_index, (key, _) in enumerate(RUNS):
            count = sum(edges[index] <= t < edges[index + 1]
                        for t in runs[key]["host_wall_seconds"])
            height = count * 30
            if count:
                fig.rect(x + run_index * 26, 330 - height, 22, height, run_colors[run_index])
                fig.text(x + run_index * 26 + 4, 304 - height, str(count), 17)
        fig.text(x - 4, 350, f"{edges[index]:.2f}", 16, MUTED)
    for run_index, (_, label) in enumerate(RUNS):
        fig.text(40 + run_index * 150, 388, label, 19, run_colors[run_index])
    fig.text(500, 388, "Bin start in host seconds; width 0.05 s", 18, MUTED)
    fig.text(28, 430, "Distribution measures the test harness, not architectural latency or WCET.", 18, MUTED)
    fig.save("host-histogram")

    fig = Figure()
    fig.text(28, 15, "RTOS sleep interval histogram (virtual ticks)", 27)
    intervals = [i for key, _ in RUNS for i in runs[key]["tick_intervals"]]
    counts = Counter(intervals)
    for index, interval in enumerate((24, 25, 26)):
        x = 250 + index * 240
        count = counts[interval]
        height = count / max(counts.values()) * 250
        fig.rect(x, 337 - height, 105, height, COLORS[2])
        fig.text(x + 25, 302 - height, str(count), 25)
        fig.text(x + 4, 349, f"{interval} ticks", 22, MUTED)
    fig.text(28, 407, f"{counts[25]} of {len(intervals)} intervals = 25 ticks across TX5 M4, TX6 M4 and M55. "
             "Synthetic QEMU time.", 18, MUTED)
    fig.save("tick-histogram")

    fig = Figure(1120, 590)
    fig.text(24, 15, "Source structure: external TX5 kernel vs public repository", 26)
    trees = [
        ("TX5_ROOT: external WICED SDK checkout", [
            "bcm-wiced-sdk/  (sparse, commit 0886ec9)",
            "  WICED/RTOS/ThreadX/",
            "    ver5.6/tx_api.h, tx_user.h ...",
            "    ver5.6/Cortex_M3_M4/GCC/tx_port.h",
            "    ThreadX.ARM_CM4.release.a",
            "      192 objects, soft-float",
            "  (no other SDK component is used)",
            "", "never copied into the repository",
        ]),
        ("TX5-upgrade (MIT original work)", [
            "TX5-upgrade/", "  src/led_demo.c + rtos_selftest.c",
            "  src/startup.S + qemu_board.c",
            "  src/tx5_wiced_port.c  [TX5 only]",
            "  cmake/tx5-wiced-adapter.cmake",
            "  config/tx6/tx_user.h  [TX6 only]",
            "  third_party/threadx/ [pinned MIT 6.5]",
            "  boards/qemu.ld + tests/ + evidence/",
            "  scripts/ + presentation/ + LICENSE",
        ]),
    ]
    for index, (heading, tree) in enumerate(trees):
        x = 25 + index * 555
        fig.text(x, 76, heading, 20, COLORS[index])
        for row, text in enumerate(tree):
            fig.text(x, 129 + row * 39, text, 19, mono=True)
    fig.save("source-trees")

    fig = Figure(1120, 540)
    fig.text(28, 18, "Migration workflow: change one dimension at a time", 26)
    boxes = [
        (30, 110, "1. Inspect TX5", "ABI / symbols / config"),
        (390, 110, "2. Stage 1 run", "TX5.6 on Cortex-M4"),
        (750, 110, "3. Stage 2 run", "swap kernel: TX6 M4"),
        (750, 310, "4. Stage 3 build", "swap core: TX6 M85"),
        (390, 310, "5. M55 run", "Armv8.1-M supplement"),
        (30, 310, "6. Board sign-off", "BSP / timing / FPU / IRQ"),
    ]
    for x, y, title, subtitle in boxes:
        fig.rect(x, y, 320, 108, "#3b3b3b")
        fig.text(x + 18, y + 17, title, 24, COLORS[1])
        fig.text(x + 18, y + 62, subtitle, 20)
    for a, b in [(0, 1), (1, 2), (3, 4), (4, 5)]:
        x1, y1, _, _ = boxes[a]
        x2, y2, _, _ = boxes[b]
        if x2 > x1:
            fig.line(x1 + 322, y1 + 55, x2 - 8, y2 + 55, COLORS[2])
            fig.text(x2 - 23, y2 + 33, ">", 24, COLORS[2])
        else:
            fig.line(x1 - 4, y1 + 55, x2 + 330, y2 + 55, COLORS[2])
            fig.text(x2 + 323, y2 + 33, "<", 24, COLORS[2])
    fig.line(910, 220, 910, 303, COLORS[2])
    fig.text(28, 475, "Steps 1-5 are done (step 4 is compile/link only); step 6 needs the target M85 silicon.", 19, MUTED)
    fig.save("workflow")

    fig = Figure(1120, 520)
    fig.text(28, 20, "The executed path: real ThreadX, virtual board outputs", 27)
    for x, heading, detail in [
        (35, "Application", "same source, all stages"),
        (397, "ThreadX kernel", "TX5.6 archive or TX6.5 src"),
        (759, "CPU port", "PendSV/SVC + task context"),
    ]:
        fig.rect(x, 112, 325, 100, "#3b3b3b")
        fig.text(x + 15, 128, heading, 24, COLORS[1])
        fig.text(x + 15, 172, detail, 18)
    for x in (363, 725):
        fig.text(x, 140, ">", 28, COLORS[2])
    fig.rect(150, 279, 810, 100, "#3b3b3b")
    fig.text(175, 292, "QEMU: Cortex-M4 (TX5 and TX6) or M55, NVIC, SysTick", 24, COLORS[2])
    fig.text(175, 337, "Semihost adapter emits LED states; no physical GPIO driver", 21)
    fig.line(555, 215, 555, 270, COLORS[2])
    fig.text(28, 427, "Port + core model execute real firmware instructions. HTML replay uses saved console evidence.", 19, MUTED)
    fig.save("architecture")


def block(kind, **values):
    return {"kind": kind, **values}


def slides(e):
    b, r, tx5 = e["builds"], e["runs"], e["tx5"]
    s = []
    def add(title, subtitle, *blocks):
        s.append({"title": title, "subtitle": subtitle, "blocks": list(blocks)})
    p = lambda text: block("p", text=text)
    bullets = lambda *items: block("bullets", items=list(items))
    code = lambda text, label="": block("code", text=dedent(text).strip(), label=label)
    fig = lambda name, caption: block("figure", name=name, caption=caption)
    table = lambda heads, rows: block("table", heads=heads, rows=rows)
    note = lambda text: block("note", text=text)
    hw = {key: r[key]["metrics"]["led_stack_high_water_bytes"] for key in r}
    total_intervals = sum(len(r[key]["tick_intervals"]) for key in r)

    add("ESL – Engineering Software Lab", "Embedded software consultancy · optimizing and migrating embedded projects",
        block("esl-intro",
              about=["Embedded software consultancy specializing in optimizing and migrating embedded projects.",
                     "Parasoft and Perforce partner in Israel for over 20 years.",
                     "This proof was designed and built by ESL to show a migration path with evidence, "
                     "not just a plan."],
              name="Daniel Liezrowice", role="CTO, ESL",
              fact="Has used ThreadX for over 25 years."))
    add("ThreadX 5.6 → 6.5, Cortex-M4 → M85", "One application, three migration stages, executable evidence",
        p("The same Clang-built application runs on the real ThreadX 5.6 kernel, then on current "
          "MIT ThreadX 6.5, then is built for Cortex-M85."),
        table(["Stage", "Kernel / core", "Evidence achieved"], [
            ["1  TX5-M4", f"ThreadX {tx5['version']} prebuilt archive / Cortex-M4",
             f"Built, executed: {r['tx5-m4']['pass_count']}/{r['tx5-m4']['repeats']} runs"],
            ["2  TX6-M4", "ThreadX 6.5.2.202603 / Cortex-M4",
             f"Built, executed: {r['m4']['pass_count']}/{r['m4']['repeats']} runs"],
            ["3  TX6-M85", "ThreadX 6.5.2.202603 / Cortex-M85", "Compiled and linked only"],
            ["+  TX6-M55", "ThreadX 6.5.2.202603 / Cortex-M55",
             f"Supplement, executed: {r['m55']['pass_count']}/{r['m55']['repeats']} runs"]]),
        note("Use ← / →, touch arrows, or swipe. Home returns to the start."),
        block("toc"))
    add("Change one thing per stage", "So every difference has exactly one cause",
        table(["Step", "Kernel", "Core / ABI", "Application source"], [
            ["Stage 1 → 2", "TX5.6 → TX6.5", "Cortex-M4 unchanged; soft-float → hard-float", "Unchanged"],
            ["Stage 2 → 3", "TX6.5 unchanged", "Cortex-M4 → Cortex-M85", "Unchanged"],
            ["Supplement", "TX6.5 unchanged", "Cortex-M55: newest core this QEMU runs", "Unchanged"]]),
        bullets("Stage 1 → 2 isolates the RTOS migration on the core the TX5 kernel was built for.",
                "Stage 2 → 3 isolates the CPU port change on an unchanged kernel release.",
                "M55 shares the Armv8.1-M port family with M85, so it is the closest runnable proxy, "
                "not a substitute for M85 execution."),
        note("The float ABI change in stage 1 → 2 is forced by the TX5 archive, not chosen. "
             "It is called out as its own diff later."))
    add("The challenges of this project", "What we did not have, and how each gap was closed",
        table(["Challenge", "Why it matters", "How ESL handled it"], [
            ["No ThreadX 5 source code: only a prebuilt binary archive",
             "The port contract, ABI and configuration cannot be read from source or rebuilt",
             "Recovered them from build attributes, symbols and disassembly of the 192 archive objects"],
            ["No real target hardware: no M4 board, no M85 silicon",
             "No physical GPIO, clocks, interrupts or cycle-accurate timing",
             "QEMU MPS2 AN386 (M4) and MPS3 AN547 (M55), virtual LEDs and buttons, deterministic icount time"],
            ["No Cortex-M85 emulator available",
             "Stage 3 cannot execute anywhere in this setup",
             "Ran the closest Armv8.1-M core (M55); M85 verified by build attributes and a full link"],
            ["TX5 binary licence restrictions and a fixed soft-float ABI",
             "The kernel cannot be redistributed, and every object must match its ABI",
             "Linked from an external checkout only; Stage 1 built soft-float with packed enums; TCB size asserted"],
            ["Compiler change from GCC to Clang",
             "The TX5 archive was built by GCC; Clang has different defaults and assembler behaviour",
             "Matched the archive ABI explicitly; fixed a flag-dependent startup loop found by QEMU trace"]]),
        note("Each gap that could not be closed without hardware is listed again on the acceptance-gate slide, "
             "so nothing is silently assumed."))
    add("ThreadX 5 and 6: what actually changes", "Same service model; different delivery, port contract and licence",
        table(["Concern", "ThreadX 5.6 (WICED archive)", "ThreadX 6.5 (Eclipse)"], [
            ["Delivery", "Headers + prebuilt GCC archive, no kernel source", "Full C source + CPU/toolchain ports"],
            ["Licence", "Commercial; SDK copy restricted to WICED use", "MIT"],
            ["Ports in this delivery", "One Cortex-M3/M4 port", "M4, M55, M85 and many more"],
            ["Float ABI", "Soft-float; r4-r11 context only", "Hard-float; FPU context in the port"],
            ["Thread start / handlers", "SVC; __tx_PendSVHandler, __tx_SVCallHandler", "PendSV; PendSV_Handler"],
            ["Configuration", "Fixed by archive: errno extension, no error checking", "Rebuilt from tx_user.h"]]),
        note("Rows are findings from this specific SDK archive and its headers. Other licensed TX5 "
             "distributions may have been built with different options."))
    add("Where the ThreadX 5 kernel comes from", "TX5 was never open source; the WICED SDK ships it as binaries",
        bullets("The public WICED SDK 3.1.0 contains ThreadX 5.6 headers and ThreadX.ARM_CM4.release.a.",
                "Its README restricts those objects to WICED use, so nothing from the SDK is in this repository.",
                "The build links the archive from TX5_ROOT, a separate checkout; configuration fails if TX5_ROOT is inside the repository.",
                "CI clones the same SDK commit into the runner's temp directory for every run."),
        code(f"""
            git clone --filter=blob:none --no-checkout \\
                https://github.com/wwwllllllll/bcm-wiced-sdk.git $TX5_ROOT
            git -C $TX5_ROOT sparse-checkout set --no-cone '/WICED/RTOS/ThreadX/'
            git -C $TX5_ROOT checkout {tx5['wiced_commit']}
            # ThreadX.ARM_CM4.release.a sha256:
            # {tx5['archive_sha256']}
        """, "Reproducible external dependency, identified by commit and hash"))
    add("Reading a binary-only kernel", "No source, so inspect build attributes, symbols and machine code",
        code("""
            $ llvm-readelf -A tx_thread_create.o
              CPU_name: Cortex-M4        CPU_arch: ARM v7E-M
              ABI_enum_size: Packed      (no ABI_VFP_args, no FP_arch)
            $ llvm-nm tx_thread_schedule.o
              T __tx_PendSVHandler   T __tx_SVCallHandler
              U tx_low_power_enter   U _tx_thread_system_stack_ptr
            $ llvm-strings tx_thread_initialize.o
              ThreadX Cortex-M3/GNU Version G5.6.5.2
        """, "Actual inspection of the WICED ThreadX.ARM_CM4.release.a members"),
        bullets("No VFP tag: the archive is soft-float, so every object in the image must be soft-float.",
                "Packed enums: GCC -fshort-enums; Clang must match it.",
                "The CM4 archive is the Cortex-M3 port: it never saves FPU registers.",
                "Unresolved WICED hooks show exactly what the board layer must provide."))
    add("The exact versions, not moving targets", "Every kernel input is pinned and identifiable",
        table(["Input", "Identity"], [
            ["TX5 kernel", f"ThreadX {tx5['version']}, WICED SDK 3.1.0 commit {tx5['wiced_commit'][:12]}"],
            ["TX5 archive sha256", tx5["archive_sha256"]],
            ["TX6 kernel", "Eclipse ThreadX v6.5.2.202603_rel, latest observed on 2026-10-11"],
            ["TX6 commit", e["threadx_sha"]],
            ["Compiler", e["compiler"]],
            ["Emulator", e["qemu"]]]),
        note("The originally linked v6.1.12_rel tag carries Azure RTOS hardware-linked licence text in its "
             "own tree; it is not substituted for the MIT release."))
    add("Cortex-M4, M55 and M85", "Keep CPU architecture distinct from a particular microcontroller",
        table(["Property", "Cortex-M4", "Cortex-M55", "Cortex-M85"], [
            ["Architecture", "Armv7E-M", "Armv8.1-M", "Armv8.1-M"],
            ["DSP / vectors", "Scalar DSP extensions", "Helium / MVE", "Helium / MVE"],
            ["Floating point", "Optional single precision", "Configuration-dependent FP/MVE", "Configuration-dependent FP/MVE"],
            ["Security model", "No Armv8-M TrustZone", "Armv8-M TrustZone", "TrustZone; PACBTI capability"],
            ["This proof", "TX5 and TX6 run on MPS2 AN386", "TX6 run on MPS3 AN547", "TX6 compile/link only"]]),
        note("Core IP features and SoC implementations vary. A new core does not bring the old "
             "board's GPIO, clocks, memory addresses, DMA or wiring with it."))
    add("The most modern runnable QEMU Cortex-M here", "Probe the installed executable instead of relying on development docs",
        code("""
            qemu-system-arm --version
            qemu-system-arm -machine help
            qemu-system-arm -cpu help
            # installed: 11.1.0
            # present: mps2-an386 / cortex-m4, mps3-an547 / cortex-m55
            # absent:  mps3-an555 / cortex-m85
        """, "Actual local inventory, saved in evidence/qemu-*.txt"),
        p("M55 is the newest Cortex-M CPU exposed by this installed QEMU build. "
          "QEMU development documentation mentions AN555, but it is not in the tested binary."),
        note("An M85 image is never run under an M55 CPU and labelled M85. "
             "The M85 ELF remains a separate, explicitly unexecuted build artifact."))
    add("Licensing is an engineering input", "Public on GitHub does not mean free to redistribute",
        bullets("The WICED SDK README limits its ThreadX / NetX objects to use with WICED.",
                "The TX5 archive and headers are linked from an external checkout and never committed or published.",
                "The application, board layer, adapter and tests are independently written; original work is MIT.",
                "ThreadX 6.5 is pinned as an MIT submodule with its upstream notices.",
                "PDF typography embeds Roboto under OFL 1.1, with the notice shipped beside the PDF."),
        note("This is an engineering demonstration, not a legal opinion on WICED licence scope. "
             "Product use of a TX5 kernel needs its own licence."))
    add("The source trees", "The TX5 kernel stays outside; the repository holds only original work",
        fig("source-trees", "Left: what TX5_ROOT must contain. Right: the public repository."),
        note("TX5-only and TX6-only files are small and named for their stage: one adapter, "
             "one board hook, one tx_user.h."))
    add("Migration workflow", "Change one dimension at a time",
        fig("workflow", "Kernel first on the original core, then the core on the new kernel."),
        p("Stages 1 and 2 give a like-for-like Cortex-M4 run on each kernel. "
          "Stage 3 then needs only the CPU port change."))
    add("What really executes", "No mock RTOS, no fake emulator success",
        fig("architecture", "Clang-built firmware runs the real TX5.6 or TX6.5 scheduler under QEMU."),
        note("The board adapter virtualizes two LEDs and deterministic active-low buttons. "
             "It does not emulate or access a physical GPIO controller."))
    add("Diff 1: how each kernel enters the build", "Imported binary archive vs rebuilt source",
        code("""
            # Stage 1: cmake/tx5-wiced-adapter.cmake
            - add_library(threadx STATIC IMPORTED GLOBAL)
            - IMPORTED_LOCATION  ${TX5_ROOT}/.../ThreadX.ARM_CM4.release.a
            - INTERFACE_COMPILE_DEFINITIONS  TX_INCLUDE_USER_DEFINE_FILE
            - include dirs: ver5.6/ and ver5.6/Cortex_M3_M4/GCC/
            # Stages 2-3: CMakeLists.txt
            + set(THREADX_ARCH ${TX_CORE})        # cortex_m4 / m55 / m85
            + set(TX_USER_FILE config/tx6/tx_user.h)
            + add_subdirectory(third_party/threadx)
            # all stages
              target_link_libraries(threadx_gpio_demo PRIVATE threadx)
        """, "Actual build integration; the application target is identical"),
        p("With source, the kernel is recompiled for the application's ABI and configuration. "
          "With a binary, the application must adopt the archive's ABI and configuration instead."))
    add("Diff 2: the float ABI is dictated by the archive", "Hard-float objects cannot link against this TX5 kernel",
        code("""
            # cmake/clang-arm-none-eabi.cmake
            - TX5: -mcpu=cortex-m4 -mthumb -mfloat-abi=soft -fshort-enums
            + TX6: -mcpu=cortex-m4 -mthumb -mfloat-abi=hard
            # TX5.6 PendSV: integer context only
              mrs   r12, psp
              stmdb r12!, {r4-r11}       @ no s16-s31, no lazy FP state
              ...
              mvn   lr, #2               @ EXC_RETURN 0xFFFFFFFD
        """, "Toolchain change plus disassembly of __tx_ts_handler in the archive"),
        bullets("A hard-float task on this TX5 port would break: it saves no s16-s31 and always returns with a non-FP EXC_RETURN.",
                "Stage 2 is therefore also the first point where FPU code becomes safe on M4.",
                "The image attributes confirm it: TX5 has no FP_arch tag; TX6 M4 has VFPv4-D16 and AAPCS VFP."))
    add("Diff 3: vectors and the first context switch", "TX5.6 starts threads through SVC, TX6 does not",
        code("""
            # TX5.6 _tx_thread_schedule (from the archive)
              str   r1, [r0, #0x10]      @ SysTick CTRL |= ENABLE
              cpsie i
              svc   #0                   @ first thread starts in SVCall
            # src/startup.S vector table
            - .word DEMO_SVC_HANDLER     @ TX5: __tx_SVCallHandler
            - .word DEMO_PENDSV_HANDLER  @ TX5: __tx_PendSVHandler
            + .word DEMO_SVC_HANDLER     @ TX6: fault_handler (unused)
            + .word DEMO_PENDSV_HANDLER  @ TX6: PendSV_Handler
        """, "Handler names are per-stage CMake defaults, validated as plain symbols"),
        note("Leaving SVC at the TX6 default fault handler makes TX5 hang before the first thread runs. "
             "The verifier treats that as a timeout failure."))
    add("Diff 4: low-level init and the idle hook", "Contracts recovered from disassembly, implemented in MIT code",
        code("""
            void _tx_initialize_low_level(void) {
                _tx_initialize_unused_memory = &__first_free_ram;
            #ifdef DEMO_TX5
            -   _tx_thread_system_stack_ptr = (void *)demo_vectors[0];
            #endif
                /* VTOR, SHPR2/3 priorities, 100 Hz SysTick: shared */
            }
            - unsigned long platform_power_down_hook(unsigned long ticks) {
            -     __asm volatile("wfi");
            -     return 0UL;        /* ticks slept; SysTick kept running */
            - }
        """, "src/tx_initialize_low_level.c and src/tx5_wiced_port.c"),
        bullets("The TX5 port objects reference _tx_thread_system_stack_ptr; the TX6 Cortex-M4 port sources do not use it.",
                "The WICED idle loop calls tx_low_power_enter, which calls platform_power_down_hook(ticks to next timer).",
                "A non-zero return is added to the kernel clock (tickless mode). Returning 0 keeps normal ticking."))
    add("Diff 5: a 4-byte configuration bug", "Found by the metrics, then made impossible to build",
        code("""
            [metric] sizeof_TX_THREAD=176        <- application's view
            _tx_thread_create:  movs r2, #0xb4   <- archive clears 180 B
                                bl   memset
            [metric] led_stack_high_water_bytes=1024   <- impossible
            # cause: -Iinclude found the TX6 tx_user.h before WICED's,
            #        dropping "#define TX_THREAD_USER_EXTENSION int errno;"
            + move TX6 config to config/tx6/tx_user.h
            + _Static_assert(sizeof(TX_THREAD) == 180U, ...);
            [metric] sizeof_TX_THREAD=180   led_stack_high_water_bytes=196
        """, "Actual first Stage 1 run, root cause and fix"),
        p("The kernel cleared 4 bytes past each 176-byte thread object. led_thread_stack follows "
          "led_thread in RAM, so its first fill word was zeroed and the stack scan reported a full stack. "
          "The functional test still passed: only the measurement exposed the corruption."),
        note("With a binary kernel, the header configuration is part of the ABI. "
             "It must be the configuration the archive was built with, and it should be asserted."))
    add("Diff 6: API and configuration details", "Small differences that break builds or change behaviour",
        table(["Item", "TX5.6 archive", "TX6.5 build here"], [
            ["_tx_version_id", "extern const CHAR[]", "extern CHAR[]"],
            ["Thread extension", "int errno; (WICED tx_user.h)", "None"],
            ["Error checking", "Disabled in release archive", "Enabled (txe_ wrappers)"],
            ["Preemption-threshold", "Disabled", "Enabled"],
            ["Timer expiry", "Processed in the SysTick ISR", "System timer thread (default)"],
            ["Stack checking", "Off; stacks still filled with 0xEF", "On"]]),
        bullets("The application dropped its own _tx_version_id declaration and uses the port header's.",
                "Stack high-water is measured by scanning the 0xEF fill, which works on both kernels.",
                "Thread resumption is checked with an application flag, not scheduler internals."))
    add("Diff 7: milliseconds versus RTOS ticks", "Keep units visible; avoid a silent tenfold delay error",
        code("""
            #define TX_TIMER_TICKS_PER_SECOND 100   // tick rate used by both stages
            #define LED_UPDATE_TICKS 25U
            tx_thread_sleep(LED_UPDATE_TICKS);      // 250 ms virtual time
            SysTick reload = DEMO_CLOCK_HZ / 100 - 1
            SysTick_Handler -> _tx_timer_interrupt  // same symbol in TX5 and TX6
        """, "Timing integration, plus a measured tick invariant"),
        p("The tested board clock constants are 25 MHz for MPS2-M4 and 32 MHz for MPS3-M55. "
          "The M85 build reuses the demonstration map and clock; a real M85 SoC must replace them."),
        note("QEMU icount is synthetic: 128 ns per emulated instruction. "
             "The tick invariant is a scheduler test, not a physical time or jitter guarantee."))
    add("Diff 8: preserve the held-button latch", "A subtle behavioural detail, checked at release as well as press",
        code("""
            - toggle the same boolean even while the button is held
            + if (!button0) toggle0 = !toggle0;
            + output0 = button0 || toggle0;
            + qemu_led_set(0, output0);
            # cycle 1: latch OFF / output OFF
            # cycles 2-3: latch unchanged / held button forces ON
            # cycle 4: button released / next toggle yields ON
        """, "Application behaviour, identical on every stage"),
        note("The verifier deliberately rejects a cycle-4 OFF result."))
    add("Diff 9: startup assembly under Clang", "A real encountered failure, with a trace-supported fix",
        code("""
            - sub r2, r2, r1   // Clang emitted sub.w, without updating flags
            - beq copy_done    // branches on stale flags
            + copy_loop:
            +     cmp r1, r2   // explicit end-pointer comparison
            +     bhs copy_done
            +     ldrb r3, [r0], #1
            +     strb r3, [r1], #1
            +     b copy_loop
        """, "Compared with the upstream TX6 example startup, not Broadcom source"),
        p("QEMU traced a bus fault at 0x00080000 during the endless startup copy. "
          "The replacement uses explicit comparisons, copies .data, clears .bss and enables CP10/CP11."))
    add("Diff 10: TX6 security mode and BSP scope", "Scope down the first proof; make omitted features explicit",
        code("""
            # config/tx6/tx_user.h
            + #define TX_SINGLE_MODE_SECURE
            + #define TX_TIMER_TICKS_PER_SECOND 100
            + #define TX_ENABLE_STACK_CHECKING
            # boards/qemu.ld (all stages)
              CODE 0x00000000 512 KiB, RAM 0x20000000 32 KiB
              system stack 2048 B, 8-byte aligned; VTOR = demo_vectors
              PendSV/SVC priority 0xff, SysTick 0x40
        """, "Demonstrator configuration, not a production M85 BSP"),
        bullets("Single-secure avoids exercising secure-stack paths without a non-secure image.",
                "Do not infer a TrustZone security policy from a successful boot.",
                "A real M85 SoC has its own memory map, clocks, IRQ routing, caches and MPU."))
    add("Diff 11: success is a checked contract", "Fail on missing, wrong or partial output",
        code("""
            + require exactly one banner version, equal to the stage's
            +     TX5: G5.6.5.2      TX6: 6.5.2.202603
            + verify the CPUID part number for the requested core
            + require queue / event / semaphore / mutex / pool self-test PASS
            + check all 10 button + LED rows and 9 intervals of 25 ticks
            + require explicit completion and QEMU exit status 0
            + reject timeout, wrong identity, wrong state or partial log
        """, "tests/run_qemu.py + 15 verifier unit tests"),
        p("A TX6 image cannot pass as a TX5 run: the expected version is per stage and must match exactly. "
          "CMake also refuses a TX5 build on any core but M4, or with TX5_ROOT inside the repository."))
    add("The RTOS services really switch tasks", "A higher-priority worker must preempt, suspend, resume and signal",
        code("""
            // LED task priority 5; worker priority 4
            worker: worker_progress = 1;
                    tx_queue_receive(&queue, &value, TX_WAIT_FOREVER);
                    worker_progress = 2;
                    tx_event_flags_set(&flags, 1, TX_OR);
            LED:    require(worker_progress == 1);   // preempted, then suspended
                    tx_queue_send(&queue, &message, TX_NO_WAIT);
                    require(worker_progress == 2);   // resumed by the send
            // observed on all three runtime images:
            //   worker_thread_runs = 2; led_thread_runs = 12
        """, "Condensed from the independently written service self-test"),
        bullets("The progress flag is application state, so the check does not depend on TCB internals.",
                "The timer wakes the sleeping LED task nine times through each kernel's real timer path.",
                "Mutex and pool checks are basic operations, not contention or fragmentation stress."))
    add("Replay the verified LED run", "Recorded Stage 1 QEMU evidence, not a browser-side emulator",
        block("replay"),
        p("Two buttons are scripted active-low inputs. A held button forces its LED on; "
          "the paused toggle resumes after release. Step through cycles 0–9."),
        note("Embedded from evidence/tx5-m4-run.json. The generator checks that the TX6 M4 and M55 "
             "runs produced identical rows."))
    add("Console evidence: Stage 1, ThreadX 5.6", "Cortex-M4, prebuilt WICED kernel",
        code((ROOT / "evidence/tx5-m4-console.txt").read_text(encoding="utf-8"),
             "Actual QEMU console, not generated example output"))
    add("Console evidence: Stage 2, ThreadX 6.5", "Same Cortex-M4, same application, new kernel",
        code((ROOT / "evidence/m4-console.txt").read_text(encoding="utf-8"),
             "Actual QEMU console, not generated example output"),
        note("Only the banner and stack high-water differ from Stage 1. Every LED row and tick is identical."))
    add("Memory chart: linked ROM", "Clang -O3; same application and service tests on every image",
        fig("rom", "ROM = .vectors + .text + .ARM.exidx + .data load image."),
        p(f'TX5 M4: {b["tx5-m4"]["rom_bytes"]:,} B; TX6 M4: {b["m4"]["rom_bytes"]:,} B '
          f'(+{b["m4"]["rom_bytes"] - b["tx5-m4"]["rom_bytes"]:,} B); '
          f'TX6 M85: {b["m85"]["rom_bytes"]:,} B; TX6 M55: {b["m55"]["rom_bytes"]:,} B.'),
        note("The TX5→TX6 delta is not pure kernel growth: the TX6 build enables error checking, "
             "preemption-threshold and a system timer thread, which the WICED release archive leaves out."))
    add("Memory chart: reserved RAM", "Include stacks and test infrastructure, not only global data",
        fig("ram", "RAM = .data + .bss + 2 KiB system stack. Static task stacks are inside .bss."),
        p(f'TX5 M4: {b["tx5-m4"]["ram_reserved_bytes"]:,} B; TX6 M4: {b["m4"]["ram_reserved_bytes"]:,} B. '
          "TX6 adds a system timer thread and its stack; TX5 processes timers in the ISR. "
          "sizeof(TX_THREAD) happens to be 180 bytes on both kernels with these configurations."))
    add("Stack headroom is measured, not assumed", "The same fill-pattern scan on both kernels",
        fig("stack", "Deepest LED-thread stack write under the test workload; 1024 bytes reserved."),
        p(f"TX5 M4 {hw['tx5-m4']} B, TX6 M4 {hw['m4']} B, TX6 M55 {hw['m55']} B. "
          "Differences come from the ABI, compiler code generation and each port's stack frame; "
          "they are not attributed to one cause."),
        note("Production worst-case paths, nested interrupts, FPU/MVE context and M85 behaviour "
             "still require stress and hardware validation."))
    add("Performance chart: emulator test cost", "Measure what was run, and say what the number means",
        fig("host-cost", "Eight interleaved QEMU runs per image on this Windows host, using deterministic icount."),
        note("TX5 looks faster because its idle hook executes WFI, which QEMU skips to the next timer, while "
             "TX6 idles in a spin loop that QEMU must emulate. This is idle strategy, not kernel speed."))
    add("Histogram: repeatability of the host harness", "Samples are retained, not reduced to an unexplained mean",
        fig("host-histogram", "Every plotted sample is in evidence/summary.json."),
        p("Use this to budget an automated test job and spot host variability. "
          "Do not turn the median differences into CPU or kernel performance claims."))
    add("Histogram: scheduler timing contract", f"{total_intervals} measured intervals, all at the requested 25 ticks",
        fig("tick-histogram", f"8 runs × 9 intervals × 3 images = {total_intervals} intervals."),
        note("The 100 Hz tick gives 250 ms in the configured virtual-time model on both kernels. "
             "Synthetic instruction time cannot establish physical sub-tick jitter."))
    add("What the M85 build proves", "Correct target attributes and resolved symbols, not execution",
        code("""
            llvm-readelf -A build/m85/threadx_gpio_demo.elf
            CPU_name: cortex-m85
            CPU_arch: ARM v8.1-M Mainline
            FP_arch:  ARMv8-a FP-D16      ABI_VFP_args: AAPCS VFP
            MVE_arch: MVE integer and float
            llvm-nm --undefined-only build/m85/threadx_gpio_demo.elf
            # no undefined symbols
        """, "Actual attribute inspection; build uses upstream ports/cortex_m85/gnu"),
        p("Clang compiled and LLD linked the unchanged application with the M85 port. "
          "The demo linker map and clock are not a production M85 SoC definition."),
        note("There is no M85 runtime, performance, power, PACBTI or mixed FPU/MVE correctness result."))
    add("The hardware acceptance gate", "Turn this proof into a product migration with explicit tests",
        table(["Workstream", "Required evidence before production"], [
            ["Board / SoC", "Vendor startup, linker map, GPIO polarity, clock tree, IRQ map"],
            ["Context / ABI", "Preemption + nested IRQ + mixed scalar/FPU/MVE tasks; inspect saved context"],
            ["Security", "TrustZone policy, secure gateways/stacks, MPU and optional PACBTI"],
            ["Performance", "On-silicon cycles, IRQ latency, deadline/WCET, throughput and energy, TX5 vs TX6"],
            ["Application", "Peripheral, network, watchdog and low-power regression, incl. tickless idle"],
            ["Governance", "Licensing, SBOM, safety/change-impact assessment, traceable requirements"]]),
        note("The proof reduces feasibility risk. It does not claim that Wi-Fi, TLS, OTA, "
             "safety certification or all application deadlines have migrated."))
    add("Reproduce the result", "Public source, pinned dependencies, raw evidence and automated checks",
        code("""
            git clone --recurse-submodules https://github.com/zuwasi/TX5-upgrade.git
            # fetch the external SDK into TX5_ROOT (see README), then:
            cmake --preset tx5-m4  && cmake --build --preset tx5-m4
            cmake --preset tx6-m4  && cmake --build --preset tx6-m4
            cmake --preset tx6-m85 && cmake --build --preset tx6-m85
            cmake --preset m55     && cmake --build --preset m55
            ctest --test-dir build/tx5-m4 ; ctest --test-dir build/m4
            ctest --test-dir build/m55
            python -m unittest discover -s tests -p test_verifier.py -v
            python scripts/collect_evidence.py --repeats 8
        """, "Tools: Clang/LLVM, LLD, CMake, Ninja, Python and ARM QEMU"),
        p("GitHub CI runs all four images, including Stage 1 against a fresh SDK clone. "
          "CI uses Linux packaged tools, so versions may differ from the recorded Windows run."),
        note("Only run firmware you trust with host semihosting enabled."))
    add("The technical conclusion", "A bounded yes, backed by executable evidence",
        bullets("YES: the application runs unchanged on the real ThreadX 5.6 Cortex-M4 kernel and on ThreadX 6.5.",
                "YES: behaviour, service checks and every tick match between TX5 and TX6 on the same core.",
                "YES: the same application compiles and links with the upstream Cortex-M85 port.",
                "LEARNED: with a binary kernel, its ABI and header configuration are part of the contract.",
                "NOT YET: M85 runtime and real-board BSP / timing / security qualification."),
        note("Next: choose the target M85 SoC and run the hardware acceptance suite, "
             "including a TX5-vs-TX6 cycle comparison on M4 silicon if that baseline matters."),
        p("Public source: github.com/zuwasi/TX5-upgrade\n"
          "Presentation: zuwasi.github.io/Public-html-pages/tx5-upgrade/"))
    add("Sources and evidence trail", "Primary references and local measured artifacts",
        block("sources", items=[
            ("WICED SDK 3.1.0 (external TX5 kernel source)", "https://github.com/wwwllllllll/bcm-wiced-sdk"),
            ("WICED GPIO behaviour reference", "https://github.com/wwwllllllll/bcm-wiced-sdk/tree/master/apps/snip/gpio"),
            ("Originally linked ThreadX release", "https://github.com/eclipse-threadx/threadx/tree/v6.1.12_rel"),
            ("Selected release", "https://github.com/eclipse-threadx/threadx/tree/v6.5.2.202603_rel"),
            ("ThreadX release history", "https://github.com/eclipse-threadx/threadx/releases"),
            ("Current MIT license", "https://github.com/eclipse-threadx/threadx/blob/v6.5.2.202603_rel/LICENSE.txt"),
            ("Arm Cortex-M85", "https://www.arm.com/products/silicon-ip-cpu/cortex-m/cortex-m85"),
            ("Arm M-profile architecture", "https://www.arm.com/architecture/cpu/m-profile"),
            ("Arm Helium", "https://www.arm.com/technologies/helium"),
            ("QEMU MPS2/MPS3 development docs", "https://qemu-project.gitlab.io/qemu/system/arm/mps2.html"),
            ("Raw measurements", "evidence/summary.json"),
            ("Stage 1 TX5 M4 console", "evidence/tx5-m4-console.txt"),
            ("Stage 2 TX6 M4 console", "evidence/m4-console.txt"),
            ("Supplement M55 console", "evidence/m55-console.txt"),
        ]),
        note("Source and licence inventory checked on 2026-10-11. Runtime evidence records the exact "
             "compiler, emulator version, image and archive hashes and the virtual-time model."))
    add("Planning an embedded migration?", "Talk to ESL about optimizing or migrating your embedded project",
        block("contact"))
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
    if kind == "esl-intro":
        about = "".join(f"<li>{esc(item)}</li>" for item in b["about"])
        return f"""<div class="esl-intro">
          <a class="esl-logo-large" href="{ESL_SITE}"><img src="{LOGO}" alt="ESL – Engineering Software Lab"></a>
          <div class="esl-columns"><ul class="esl-about">{about}</ul>
          <div class="person-card">
            <a href="{DANIEL_LINKEDIN}"><img src="{PHOTO}" alt="{esc(b['name'])}"></a>
            <div><strong>{esc(b['name'])}</strong><span>{esc(b['role'])}</span>
            <p>{esc(b['fact'])}</p>
            <a class="linkedin" href="{DANIEL_LINKEDIN}">LinkedIn profile</a></div>
          </div></div></div>"""
    if kind == "contact":
        return f"""<div class="contact">
          <a class="esl-logo-large" href="{ESL_SITE}"><img src="{LOGO}" alt="ESL – Engineering Software Lab"></a>
          <p>Embedded software consultancy specializing in optimizing and migrating embedded projects.
          Parasoft and Perforce partner in Israel for over 20 years.</p>
          <div class="contact-actions">
            <a class="primary" href="{ESL_CONTACT}">Contact ESL</a>
            <a href="{DANIEL_LINKEDIN}">Daniel Liezrowice on LinkedIn</a>
            <a href="https://github.com/zuwasi/TX5-upgrade">Source and evidence</a>
          </div></div>"""
    if kind == "replay":
        return """<div class="replay" aria-label="Recorded QEMU LED evidence replay">
          <div class="replay-top"><strong>QEMU Cortex-M4 · ThreadX G5.6.5.2 · verified recording</strong>
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


def replay_rows():
    """Stage 1 rows, which every other runtime image must reproduce exactly."""
    runs = {key: json.loads((ROOT / f"evidence/{key}-run.json").read_text(encoding="utf-8"))["rows"]
            for key, _ in RUNS}
    if any(rows != runs["tx5-m4"] for rows in runs.values()):
        raise RuntimeError("LED/tick rows differ between runtime images")
    return runs["tx5-m4"]


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
                rows = replay_rows()
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
                            {"table": {"widths": ["*"], "body": [[
                                {"text": b["text"], "style": "code", "fillColor": CHARCOAL}]]},
                             "layout": "noBorders", "margin": [0, 2, 0, 14]}]
            elif kind == "esl-intro":
                content.append({"columns": [
                    {"width": "*", "stack": [
                        {"image": "esl_logo", "width": 300, "link": ESL_SITE,
                         "margin": [0, 0, 0, 18]},
                        {"ul": b["about"], "style": "p"}]},
                    {"width": 190, "stack": [
                        {"image": "daniel_photo", "width": 150, "link": DANIEL_LINKEDIN},
                        {"text": b["name"], "bold": True, "fontSize": 14, "margin": [0, 8, 0, 0]},
                        {"text": b["role"], "color": BLUE},
                        {"text": b["fact"], "margin": [0, 6, 0, 6]},
                        {"text": "LinkedIn profile", "link": DANIEL_LINKEDIN, "color": BLUE,
                         "decoration": "underline"}]}], "columnGap": 30})
            elif kind == "contact":
                content += [
                    {"image": "esl_logo", "width": 320, "link": ESL_SITE, "margin": [0, 10, 0, 20]},
                    {"text": "Embedded software consultancy specializing in optimizing and migrating "
                     "embedded projects. Parasoft and Perforce partner in Israel for over 20 years.",
                     "style": "p"},
                    {"ul": [
                        {"text": f"Contact ESL: {ESL_CONTACT}", "link": ESL_CONTACT},
                        {"text": f"Daniel Liezrowice on LinkedIn: {DANIEL_LINKEDIN}", "link": DANIEL_LINKEDIN},
                        {"text": "Source and evidence: https://github.com/zuwasi/TX5-upgrade",
                         "link": "https://github.com/zuwasi/TX5-upgrade"}], "style": "p"}]
            elif kind == "table":
                head = [{"text": text, "bold": True, "color": "#ffffff", "fillColor": CHARCOAL}
                        for text in b["heads"]]
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
        "info": {"title": "ThreadX 5.6 to 6.5: Cortex-M4 to M85 migration proof",
                 "author": "ESL – Engineering Software Lab", "subject": "Clang / QEMU migration evidence"},
        "pageMargins": [46, 62, 46, 40],
        "header": {"margin": [46, 18, 46, 0], "columns": [
            {"canvas": [{"type": "rect", "x": 0, "y": 0, "w": 9, "h": 9, "color": BLUE},
                        {"type": "rect", "x": 5, "y": 5, "w": 9, "h": 9, "color": AMBER}],
             "width": 20, "margin": [0, 6, 0, 0]},
            {"text": "THREADX MIGRATION PROOF", "fontSize": 8, "bold": True, "color": "#7a7a7a",
             "characterSpacing": 1.5, "margin": [0, 9, 0, 0]},
            {"image": "esl_logo", "width": 76, "link": ESL_SITE, "alignment": "right",
             "margin": [0, 0, 0, 0]}]},
        "defaultStyle": {"font": "Roboto", "fontSize": 13, "color": CHARCOAL},
        "styles": {
            "h1": {"fontSize": 25, "bold": True, "color": CHARCOAL, "margin": [0, 0, 0, 7]},
            "subtitle": {"fontSize": 14, "color": "#4a7fc0", "margin": [0, 0, 0, 18]},
            "p": {"fontSize": 13, "lineHeight": 1.15, "margin": [0, 7, 0, 12]},
            "note": {"fontSize": 11, "color": "#8a5d00", "margin": [0, 9, 0, 8]},
            "code": {"fontSize": 10, "lineHeight": 1.15, "color": "#f5f5f5",
                     "margin": [10, 9, 10, 9]},
            "label": {"fontSize": 10, "color": "#6b6b6b", "margin": [0, 5, 0, 6]},
        },
        "footer": {"text": "ESL – Engineering Software Lab · eswlab.com · ThreadX 5.6 to 6.5 migration proof · "
                           "M85 runtime remains unverified",
                   "link": ESL_SITE, "alignment": "center", "fontSize": 8, "color": "#7a7a7a"},
        "content": content,
        # Registered once so the logo on every page header is embedded a single time.
        "images": {"esl_logo": data_uri(LOGO), "daniel_photo": data_uri(PHOTO)},
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
                        f'<div class="eyebrow"><span class="mark" aria-hidden="true"></span>'
                        f'THREADX MIGRATION · {index + 1:02d}</div>'
                        f'<h1 id="title-{index}">{html.escape(slide["title"])}</h1>'
                        f'<p class="subtitle">{html.escape(slide["subtitle"])}</p>'
                        + "".join(render_block(b) for b in slide["blocks"]) + "</section>")
    replay = replay_rows()
    document = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'none'; object-src 'none'; base-uri 'none'">
<meta name="description" content="ThreadX 5.6 to 6.5 and Cortex-M4 to M85 migration proof: one application on the real TX5 kernel and on TX6, Clang builds, QEMU tests, code diffs and measured evidence.">
<title>ThreadX 5.6 → 6.5 | Cortex-M4 → M85 migration proof</title>
<link rel="stylesheet" href="deck.css"><script src="deck.js" defer></script></head>
<body><header class="topbar"><div class="brand-group">
<a class="esl-logo" href=\"""" + ESL_SITE + """\"><img src=\"""" + LOGO + """\" alt="ESL – Engineering Software Lab"></a>
<a href="#slide-1" id="brand">ThreadX 5 → 6 migration</a></div>
<div class="links"><a href="threadx-migration.pdf">Download PDF</a>
<a href=\"""" + ESL_CONTACT + """\">Contact ESL</a>
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
    for name in ["summary.json", "tx5-m4-console.txt", "m4-console.txt", "m55-console.txt",
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
    print(f"Generated {len(deck)} slides and 9 chart/diagram assets")


if __name__ == "__main__":
    main()
