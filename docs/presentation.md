# Presentation and evidence

Public HTML: <https://zuwasi.github.io/Public-html-pages/tx5-upgrade/>

Public source: <https://github.com/zuwasi/TX5-upgrade>

The presentation has 33 technical slides, eight code-diff discussions,
source-tree/workflow/architecture diagrams, linked ROM and reserved RAM charts,
stack high-water observations, host-time distributions and histograms,
and a virtual-tick histogram. The browser LED replay uses recorded verified
QEMU rows, not a browser-side emulator.

The HTML supports Previous/Next buttons, left/right arrow keys, Home,
touch swipe and a first-slide table of contents. Source and PDF links are
available at the top. The deck uses no CDN scripts, analytics or external fonts.

## Regenerate

First build/run the firmware and collect the evidence as described in the
main README. Then, from the repository root:

```powershell
python -m pip install Pillow beautifulsoup4 pypdf
npm install --prefix tmp/document-tools --ignore-scripts pdfmake@0.2.20
python scripts/make_presentation.py
python scripts/render_pdf.py
python scripts/validate_artifacts.py
```

The PDF is written to `outputs/threadx-migration.pdf` and also copied into
`presentation/` for website deployment.

## Publication

Copy the `presentation/` contents into `tx5-upgrade/` in
`zuwasi/Public-html-pages`. Keep the existing site's unrelated files unchanged.
The checked-in site includes the generated figures and the raw measurement
summary/console logs so readers can inspect the evidence behind the claims.

The source repository contains the firmware, pinned ThreadX dependency,
tests, evidence, generation scripts, HTML and PDF. Its GitHub workflow builds
all three cores and runs M4/M55 tests under QEMU.

## Validation boundaries

The local Windows proof uses Clang 22.1.3 and QEMU 11.1.0.
Linux CI uses packaged versions, recorded in CI output rather than treated as
identical to the local toolchain.

All M85 execution and target-hardware performance qualification remain open.
The earlier Qodo checkpoint could not obtain repository credentials for this
workspace, so no successful external Qodo review is claimed.
