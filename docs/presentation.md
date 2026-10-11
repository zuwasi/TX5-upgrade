# Presentation and evidence

Public HTML: <https://zuwasi.github.io/Public-html-pages/tx5-upgrade/>

Public source: <https://github.com/zuwasi/TX5-upgrade>

The presentation has 41 slides, including an ESL introduction, the project's
five main challenges, and a closing contact slide. The technical slides cover the three migration stages
(TX5.6 on Cortex-M4, TX6.5 on Cortex-M4, TX6.5 on Cortex-M85) plus the M55
supplement: eleven code-diff discussions, binary-kernel inspection,
source-tree/workflow/architecture diagrams, linked ROM and reserved RAM charts,
stack high-water observations, host-time distributions and histograms, and a
virtual-tick histogram. The browser LED replay uses the recorded Stage 1 QEMU
rows, which the generator checks are identical on every runtime image.

The HTML supports Previous/Next buttons, left/right arrow keys, Home,
touch swipe and a table of contents on the technical overview slide. Source,
PDF and ESL contact links are available at the top. The light slide design uses
ESL blue and amber with charcoal code and chart panels. Every slide has a linked
ESL logo; the introduction includes Daniel Liezrowice's photo and LinkedIn link.
The PDF uses the same branding and linked logos. The deck uses no CDN scripts,
analytics or external fonts.

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
all four images and runs the TX5-M4, TX6-M4 and M55 tests under QEMU, fetching
the external WICED SDK into the runner's temp directory for Stage 1.
`scripts/collect_evidence.py` needs `TX5_ROOT` set to that external checkout.

## Validation boundaries

The local Windows proof uses Clang 22.1.3 and QEMU 11.1.0.
Linux CI uses packaged versions, recorded in CI output rather than treated as
identical to the local toolchain.

All M85 execution and target-hardware performance qualification remain open.
The earlier Qodo checkpoint could not obtain repository credentials for this
workspace, so no successful external Qodo review is claimed.
