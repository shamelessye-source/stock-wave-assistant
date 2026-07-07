from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
START_SCRIPT = ROOT / "scripts" / "start-local.ps1"
STOP_SCRIPT = ROOT / "scripts" / "stop-local.ps1"


def test_start_local_script_declares_safe_launcher_flow() -> None:
    text = START_SCRIPT.read_text(encoding="utf-8")

    assert "Test-PortAvailable" in text
    assert "Require-Command \"py\"" in text
    assert "Require-Command \"node\"" in text
    assert "Require-Command \"npm" in text
    assert "py -m pip install -e" in text
    assert "npm.cmd install" in text
    assert "app.main:app" in text
    assert "node_modules" in text and "vite" in text
    assert "Start-Process $WebUrl" in text
    assert ".local" in text and "local-launcher.json" in text
    assert "scripts\\stop-local.ps1" in text


def test_stop_local_script_only_uses_recorded_project_processes() -> None:
    text = STOP_SCRIPT.read_text(encoding="utf-8")

    assert "local-launcher.json" in text
    assert "Get-CimInstance" in text
    assert "Stop-RecordedProcess" in text
    assert "projectRoot" in text
    assert "Stop-Process -Id" in text
    assert "[int]$Pid" not in text
    assert "Stop-Process -Name python" not in text
    assert "Stop-Process -Name node" not in text
    assert "taskkill /IM" not in text


def test_launcher_scripts_have_valid_powershell_syntax() -> None:
    powershell = shutil.which("powershell") or shutil.which("pwsh")
    if powershell is None:
        return

    for script in [START_SCRIPT, STOP_SCRIPT]:
        relative_script = script.relative_to(ROOT).as_posix()
        command = (
            "$tokens=$null;$errors=$null;"
            f"[System.Management.Automation.Language.Parser]::ParseFile('{relative_script}',"
            "[ref]$tokens,[ref]$errors) | Out-Null;"
            "if ($errors.Count -gt 0) { $errors | ForEach-Object { $_.Message }; exit 1 }"
        )
        result = subprocess.run(
            [powershell, "-NoProfile", "-Command", command],
            check=False,
            capture_output=True,
            cwd=ROOT,
            text=True,
        )
        assert result.returncode == 0, result.stdout + result.stderr
