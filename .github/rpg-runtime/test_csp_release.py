"""The release gate must reject JavaScript execution forbidden by production CSP."""

import subprocess
import tempfile
import unittest
from pathlib import Path

from test_verify_release import SCRIPT, VERIFY


class CSPReleaseTests(unittest.TestCase):
    def verify(self, javascript: str) -> subprocess.CompletedProcess:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            markers = "\n".join(f"// {marker}" for marker in VERIFY.JAVASCRIPT_BRIDGE_MARKERS)
            (output / "easyrpg-player.js").write_text(markers + "\n" + javascript + "\n" + " " * 200_000)
            wasm = b"\x00asm\x01\x00\x00\x00" + b"\x00".join(VERIFY.WASM_BRIDGE_MARKERS)
            (output / "easyrpg-player.wasm").write_bytes(wasm + b"\x00" * 8_000_000)
            return subprocess.run(
                ["python3", str(SCRIPT), "--output", directory,
                 "--repository", "https://github.com/retrom-project/Player",
                 "--tag", "retrom-core-ge68fff4a13a3-r7", "--commit", "a" * 40],
                capture_output=True, text=True, check=False,
            )

    def test_embind_dynamic_invoker_is_rejected(self):
        for code in ('new Function("return 1")', 'Function("return 1")', 'eval("1")'):
            with self.subTest(code=code):
                result = self.verify(code)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("RPG_RUNTIME_RELEASE_CSP_INVALID", result.stderr)

    def test_static_invoker_is_accepted(self):
        result = self.verify("const invoke = (fn, args) => fn(...args);")
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
