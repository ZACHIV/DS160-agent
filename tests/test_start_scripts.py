from __future__ import annotations

from pathlib import Path
import stat
import subprocess
import shutil
import unittest


ROOT = Path(__file__).resolve().parents[1]
START_SERVER = ROOT / "scripts" / "start-server.sh"
START_CHROME_DEBUG = ROOT / "scripts" / "start-chrome-debug.sh"
START_CHROME_DEBUG_UBUNTU = ROOT / "scripts" / "start-chrome-debug-ubuntu.sh"
START_CHROME_DEBUG_WINDOWS = ROOT / "scripts" / "start-chrome-debug-windows.ps1"
START_MAC = ROOT / "scripts" / "start-mac.sh"
START_UBUNTU = ROOT / "scripts" / "start-ubuntu.sh"
START_WINDOWS = ROOT / "scripts" / "start-windows.ps1"
STOP_MAC = ROOT / "scripts" / "stop-mac.sh"
BASH_SCRIPT_PATHS = [START_SERVER, START_CHROME_DEBUG, START_CHROME_DEBUG_UBUNTU, START_MAC, START_UBUNTU, STOP_MAC]
ALL_SCRIPT_PATHS = [*BASH_SCRIPT_PATHS, START_CHROME_DEBUG_WINDOWS, START_WINDOWS]


class StartScriptsTests(unittest.TestCase):
    def test_scripts_exist(self) -> None:
        for script_path in ALL_SCRIPT_PATHS:
            self.assertTrue(script_path.exists(), f"missing script: {script_path}")

    def test_bash_scripts_are_executable(self) -> None:
        for script_path in BASH_SCRIPT_PATHS:
            mode = script_path.stat().st_mode
            self.assertTrue(mode & stat.S_IXUSR, f"script is not executable: {script_path}")

    def test_bash_scripts_have_valid_bash_syntax(self) -> None:
        for script_path in BASH_SCRIPT_PATHS:
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

    def test_start_chrome_debug_ubuntu_supports_dry_run(self) -> None:
        result = subprocess.run(
            ["bash", str(START_CHROME_DEBUG_UBUNTU), "--dry-run"],
            check=True,
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertIn("--remote-debugging-port=9222", result.stdout)
        self.assertIn("google-chrome", result.stdout)

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

    def test_start_ubuntu_supports_dry_run(self) -> None:
        result = subprocess.run(
            ["bash", str(START_UBUNTU), "--dry-run"],
            check=True,
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertIn("xdg-open", result.stdout)
        self.assertIn("start-server.sh", result.stdout)
        self.assertIn("start-chrome-debug-ubuntu.sh", result.stdout)

    def test_windows_scripts_include_dry_run_support(self) -> None:
        start_windows_text = START_WINDOWS.read_text(encoding="utf-8")
        chrome_windows_text = START_CHROME_DEBUG_WINDOWS.read_text(encoding="utf-8")
        self.assertIn("--dry-run", start_windows_text)
        self.assertIn("start-windows.ps1", start_windows_text)
        self.assertIn("--dry-run", chrome_windows_text)
        self.assertIn("start-chrome-debug-windows.ps1", chrome_windows_text)

    @unittest.skipUnless(shutil.which("pwsh"), "pwsh is required to execute PowerShell dry-run tests")
    def test_windows_scripts_support_dry_run_when_pwsh_is_available(self) -> None:
        chrome_result = subprocess.run(
            ["pwsh", "-NoProfile", "-File", str(START_CHROME_DEBUG_WINDOWS), "--dry-run"],
            check=True,
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertIn("--remote-debugging-port=9222", chrome_result.stdout)
        self.assertIn("chrome.exe", chrome_result.stdout)

        start_result = subprocess.run(
            ["pwsh", "-NoProfile", "-File", str(START_WINDOWS), "--dry-run"],
            check=True,
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertIn("start-windows.ps1", start_result.stdout)
        self.assertIn("start-chrome-debug-windows.ps1", start_result.stdout)
        self.assertIn("visa_agent.server", start_result.stdout)

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
