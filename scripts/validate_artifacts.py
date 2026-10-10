"""Verify local deck/PDF/evidence consistency before publication."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse
import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup
from PIL import Image
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "presentation"


def main():
    deck = json.loads((SITE / "slides.json").read_text(encoding="utf-8"))
    soup = BeautifulSoup((SITE / "index.html").read_text(encoding="utf-8"), "html.parser")
    assert soup.html.get("lang") == "en"
    assert len(soup.select(".slide")) == len(deck) == 33
    assert len(soup.select(".code")) >= 8
    assert soup.find("meta", attrs={"name": "viewport"})
    assert soup.find("meta", attrs={"http-equiv": "Content-Security-Policy"})
    assert all(soup.find(id=identifier) for identifier in ["home", "prev", "next"])
    for node in soup.find_all(True):
        assert not any(key.lower().startswith("on") for key in node.attrs), "Inline handler"
    for script in soup.find_all("script"):
        assert script.get("src") == "deck.js" or script.get("type") == "application/json"
    for node in soup.find_all(["img", "script", "link", "a"]):
        location = node.get("src") or node.get("href")
        if not location or urlparse(location).scheme or location.startswith("#"):
            continue
        assert (SITE / location).is_file(), f"Missing local link: {location}"
    replay = json.loads(soup.find(id="recorded-run").string)
    run = json.loads((ROOT / "evidence/m55-run.json").read_text(encoding="utf-8"))
    assert replay == run["rows"], "Replay differs from verified firmware evidence"
    summary = json.loads((ROOT / "evidence/summary.json").read_text(encoding="utf-8"))
    assert summary["threadx_sha"] == "93387b0a60382a29579bbad5045c68328e3751df"
    assert summary["builds"]["m85"]["runtime_status"] == "NOT_RUN"
    assert "m85" not in summary["runs"], "Unexpected M85 runtime claim"
    for core in ["m4", "m55", "m85"]:
        elf = ROOT / f"build/{core}/threadx_gpio_demo.elf"
        assert hashlib.sha256(elf.read_bytes()).hexdigest() == \
            summary["builds"][core]["elf_sha256"], f"Stale measured image: {core}"
    for core in ["m4", "m55"]:
        assert summary["runs"][core]["pass_count"] == 8
        assert len(summary["runs"][core]["tick_intervals"]) == 72
        assert set(summary["runs"][core]["tick_intervals"]) == {25}
    assert (SITE / "evidence/summary.json").read_bytes() == \
        (ROOT / "evidence/summary.json").read_bytes()
    images = list((SITE / "assets").glob("*.png"))
    assert len(images) == 9
    for png in images:
        with Image.open(png) as image:
            image.verify()
        tree = ET.parse(png.with_suffix(".svg"))
        assert not any(element.tag.endswith("script") for element in tree.iter())
    pdf = ROOT / "outputs/threadx-migration.pdf"
    assert pdf.read_bytes().startswith(b"%PDF-")
    assert pdf.read_bytes() == (SITE / pdf.name).read_bytes()
    reader = PdfReader(pdf)
    assert len(reader.pages) == len(deck)
    for index, page in enumerate(reader.pages):
        text = page.extract_text()
        assert len(text) > 100
        assert "\x00" not in text, f"Unmapped PDF character on page {index + 1}"
    print("PASS: 33 slides/pages, 9 figures, source links, CSP, replay and measured image hashes")


if __name__ == "__main__":
    main()
