from __future__ import annotations

from pathlib import Path
import os
import stat
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
START_SERVER = ROOT / "scripts" / "start-server.sh"
START_CHROME_DEBUG = ROOT / "scripts" / "start-chrome-debug.sh"
START_MAC = ROOT / "scripts" / "start-mac.sh"
STOP_MAC = ROOT / "scripts" / "stop-mac.sh"
SCRIPT_PATHS = [START_SERVER, START_CHROME_DEBUG, START_MAC, STOP_MAC]


class StartScriptsTests(unittest.TestCase):
    def test_scripts_exist(self) -> None:
        for script_path in SCRIPT_PATHS:
            self.assertTrue(script_path.exists(), f"missing script: {script_path}")

    def test_scripts_are_executable(self) -> None:
        for script_path in SCRIPT_PATHS:
            mode = script_path.stat().st_mode
            self.assertTrue(mode & stat.S_IXUSR, f"script is not executable: {script_path}")

    def test_scripts_have_valid_bash_syntax(self) -> None:
        for script_path in SCRIPT_PATHS:
            subprocess.run(["bash", "-n", str(script_path)], check=True, cwd=ROOT)

    def test_start_server_supports_dry_run(self) -> None:
        result = subprocess.run(
            ["bash", str(START_SERVER), "--dry-run"],
            check=True,
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertIn("visa_agent.server", result.stdout)
        self.assertIn("PYTHONPATH", result.stdout)

    def test_start_chrome_debug_supports_dry_run(self) -> None:
        result = subprocess.run(
            ["bash", str(START_CHROME_DEBUG), "--dry-run"],
            check=True,
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertIn("--remote-debugging-port=9222", result.stdout)
        self.assertIn("Google Chrome", result.stdout)

    def test_start_mac_supports_dry_run(self) -> None:
        result = subprocess.run(
            ["bash", str(START_MAC), "--dry-run"],
            check=True,
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertIn("Safari", result.stdout)
        self.assertIn("start-server.sh", result.stdout)
        self.assertIn("start-chrome-debug.sh", result.stdout)

    def test_stop_mac_supports_dry_run(self) -> None:
        result = subprocess.run(
            ["bash", str(STOP_MAC), "--dry-run"],
            check=True,
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertIn("stop-mac.sh", result.stdout)
        self.assertIn("127.0.0.1:8765", result.stdout)
        self.assertIn("--remote-debugging-port=9222", result.stdout)


if __name__ == "__main__":
    unittest.main()
