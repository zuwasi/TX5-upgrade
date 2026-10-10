"""Render the prepared presentation PDF and verify it before removing the temporary renderer."""
from pathlib import Path
import shutil
import subprocess

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
RENDERER = r"""
const fs = require("node:fs");
const path = require("node:path");
const pdfmake = require("./document-tools/node_modules/pdfmake/build/pdfmake.js");
const fonts = require("./document-tools/node_modules/pdfmake/build/vfs_fonts.js");
pdfmake.addVirtualFileSystem(fonts);
const root = path.resolve(__dirname, "..");
const definition = JSON.parse(fs.readFileSync(
  path.join(__dirname, "threadx-migration.pdf.json"), "utf8"));
fs.mkdirSync(path.join(root, "outputs"), {recursive: true});
pdfmake.createPdf(definition).getBuffer(buffer => {
  const output = path.join(root, "outputs", "threadx-migration.pdf");
  fs.writeFileSync(output, buffer);
  fs.copyFileSync(output, path.join(root, "presentation", "threadx-migration.pdf"));
  console.log(`Rendered ${buffer.length} bytes: ${output}`);
});
"""


def main():
    node = shutil.which("node")
    if not node:
        raise RuntimeError("Node.js must be on PATH")
    library = ROOT / "tmp/document-tools/node_modules/pdfmake/build/pdfmake.js"
    if not library.is_file():
        raise RuntimeError(
            "Install temporary rendering tools: "
            "npm install --prefix tmp/document-tools --ignore-scripts pdfmake@0.2.20")
    script = ROOT / "tmp/render-pdf.cjs"
    script.write_text(RENDERER, encoding="utf-8")
    subprocess.run([node, str(script)], check=True, timeout=120)
    output = ROOT / "outputs/threadx-migration.pdf"
    assert output.read_bytes().startswith(b"%PDF-"), "Invalid PDF signature"
    document = PdfReader(output)
    assert len(document.pages) == 33, "PDF page count changed unexpectedly"
    assert all(page.extract_text() for page in document.pages), "Empty PDF page"
    script.unlink()
    print(f"Verified {len(document.pages)} selectable-text PDF pages")


if __name__ == "__main__":
    main()
