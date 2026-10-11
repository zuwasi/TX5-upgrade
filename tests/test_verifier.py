"""Negative tests for the evidence verifier, using a previously verified run."""
from pathlib import Path
import json
import unittest

from run_qemu import ROOT, validate


class VerifierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = json.loads((ROOT / "evidence/m55-run.json").read_text(
            encoding="utf-8"))["log"]

    def test_verified_run(self):
        self.assertEqual(len(validate(self.text, "cortex-m55")), 10)

    def reject(self, text):
        with self.assertRaises(AssertionError):
            validate(text, "cortex-m55")

    def test_missing_completion(self):
        self.reject(self.text.replace("[pass]", "[incomplete]"))

    def test_error_marker(self):
        self.reject(self.text + "[fail] injected\n")

    def test_wrong_version(self):
        self.reject(self.text.replace("Version 6.5.2.202603", "Version 5.6"))

    def test_wrong_core(self):
        self.reject(self.text.replace("[core] cortex-m55", "[core] cortex-m85"))

    def test_wrong_cpuid(self):
        self.reject(self.text.replace("cpuid=1091555873", "cpuid=1091551808"))

    def test_wrong_button(self):
        self.reject(self.text.replace("cycle=2 BTN0=PRESSED", "cycle=2 BTN0=released"))

    def test_wrong_led(self):
        self.reject(self.text.replace(
            "cycle=4 BTN0=released BTN1=released LED0=ON",
            "cycle=4 BTN0=released BTN1=released LED0=OFF"))

    def test_wrong_tick(self):
        self.reject(self.text.replace("tick=100", "tick=101"))

    def test_missing_row(self):
        self.reject("\n".join(row for row in self.text.splitlines()
                              if not row.startswith("cycle=8 ")))

    def test_missing_selftest(self):
        self.reject(self.text.replace(
            "[selftest] queue/preemption/events/semaphore/mutex/byte-pool PASS", ""))

    def test_version_prefix_is_not_exact_match(self):
        self.reject(self.text.replace("Version 6.5.2.202603", "Version 6.5.2.2026031"))

    def test_duplicate_version_is_rejected(self):
        self.reject(self.text + "Version 6.5.2.202603\n")

    def test_requested_tx5_does_not_accept_tx6(self):
        with self.assertRaises(AssertionError):
            validate(self.text, "cortex-m55", "5.6")

    def test_invalid_version_is_rejected(self):
        with self.assertRaises(ValueError):
            validate(self.text, "cortex-m55", "5.*")


if __name__ == "__main__":
    unittest.main()
