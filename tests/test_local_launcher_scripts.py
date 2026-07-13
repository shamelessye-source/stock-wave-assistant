from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
START_SCRIPT = ROOT / "scripts" / "start-local.ps1"
STOP_SCRIPT = ROOT / "scripts" / "stop-local.ps1"
POWERSHELL = shutil.which("powershell") or shutil.which("pwsh")


def _free_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def _run_script(
    script: Path,
    *arguments: str,
    cwd: Path,
    env: dict[str, str] | None = None,
    timeout: int = 60,
) -> subprocess.CompletedProcess[str]:
    assert POWERSHELL is not None
    command = [
        POWERSHELL,
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script),
        *arguments,
    ]
    with (
        tempfile.TemporaryFile(mode="w+", encoding="utf-8") as stdout,
        tempfile.TemporaryFile(mode="w+", encoding="utf-8") as stderr,
    ):
        result = subprocess.run(
            command,
            check=False,
            cwd=cwd,
            env=env,
            stdout=stdout,
            stderr=stderr,
            text=True,
            timeout=timeout,
        )
        stdout.seek(0)
        stderr.seek(0)
        return subprocess.CompletedProcess(
            command,
            result.returncode,
            stdout.read(),
            stderr.read(),
        )


def _launcher_process_ids(*ports: int) -> set[int]:
    assert POWERSHELL is not None
    port_checks = " -or ".join(
        f"$_.CommandLine -like '*--port {port}*'" for port in ports
    )
    command = (
        "Get-CimInstance Win32_Process | "
        "Where-Object { $_.Name -in @('py.exe','python.exe','node.exe') -and "
        f"({port_checks}) }} | ForEach-Object {{ $_.ProcessId }}"
    )
    result = subprocess.run(
        [POWERSHELL, "-NoProfile", "-Command", command],
        check=False,
        capture_output=True,
        text=True,
        timeout=15,
    )
    return {
        int(line.strip())
        for line in result.stdout.splitlines()
        if line.strip().isdigit()
    }


def _wait_for_launcher_processes_to_stop(*ports: int) -> bool:
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if not _launcher_process_ids(*ports):
            return True
        time.sleep(0.1)
    return False


def _cleanup_launcher_processes(*ports: int) -> None:
    assert POWERSHELL is not None
    process_ids = _launcher_process_ids(*ports)
    if not process_ids:
        return
    ids = ",".join(str(process_id) for process_id in process_ids)
    subprocess.run(
        [
            POWERSHELL,
            "-NoProfile",
            "-Command",
            f"@({ids}) | ForEach-Object {{ Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }}",
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=15,
    )


@pytest.fixture
def launcher_project(tmp_path: Path, request: pytest.FixtureRequest) -> Path:
    if os.name != "nt" or POWERSHELL is None:
        pytest.skip("Windows PowerShell is required for launcher integration tests")

    project = tmp_path / getattr(request, "param", "launcher-project")
    project.mkdir()
    for directory in ["app", "config", "scripts", "web"]:
        shutil.copytree(
            ROOT / directory,
            project / directory,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
    for filename in ["index.html", "package.json", "tsconfig.json"]:
        shutil.copy2(ROOT / filename, project / filename)

    node_modules = project / "node_modules"
    junction = subprocess.run(
        [
            "cmd.exe",
            "/d",
            "/c",
            "mklink",
            "/J",
            str(node_modules),
            str(ROOT / "node_modules"),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert junction.returncode == 0, junction.stdout + junction.stderr

    yield project

    subprocess.run(
        ["cmd.exe", "/d", "/c", "rmdir", str(node_modules)],
        check=False,
        capture_output=True,
        text=True,
        timeout=15,
    )


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
    if POWERSHELL is None:
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
            [POWERSHELL, "-NoProfile", "-Command", command],
            check=False,
            capture_output=True,
            cwd=ROOT,
            text=True,
        )
        assert result.returncode == 0, result.stdout + result.stderr


def test_browser_open_has_nonfatal_failure_boundary() -> None:
    text = START_SCRIPT.read_text(encoding="utf-8")
    browser_section = text[text.index("if (-not $NoBrowser)") :]

    assert 'Invoke-TestFailure -Point "browser_open"' in browser_section
    assert "Browser could not be opened" in browser_section
    assert "Open $WebUrl manually" in browser_section


def test_start_refuses_existing_state_without_changing_it(
    launcher_project: Path,
) -> None:
    api_port = _free_port()
    web_port = _free_port()
    state_dir = launcher_project / ".local"
    state_dir.mkdir()
    state_path = state_dir / "local-launcher.json"
    original_state = '{"sentinel":"keep"}\n'
    state_path.write_text(original_state, encoding="utf-8")

    try:
        result = _run_script(
            launcher_project / "scripts" / "start-local.ps1",
            "-ApiPort",
            str(api_port),
            "-WebPort",
            str(web_port),
            "-NoBrowser",
            cwd=launcher_project,
        )

        assert result.returncode != 0
        assert "scripts\\stop-local.ps1" in result.stdout + result.stderr
        assert state_path.read_text(encoding="utf-8") == original_state
        assert _launcher_process_ids(api_port, web_port) == set()
    finally:
        _cleanup_launcher_processes(api_port, web_port)


def test_frontend_start_failure_rolls_back_backend(
    launcher_project: Path,
) -> None:
    api_port = _free_port()
    web_port = _free_port()
    state_dir = launcher_project / ".local"
    env = os.environ.copy()
    env["STOCK_WAVE_LAUNCHER_TEST_FAILURE"] = "frontend_start"

    try:
        result = _run_script(
            launcher_project / "scripts" / "start-local.ps1",
            "-ApiPort",
            str(api_port),
            "-WebPort",
            str(web_port),
            "-NoBrowser",
            cwd=launcher_project,
            env=env,
        )

        assert result.returncode != 0
        assert not (state_dir / "local-launcher.json").exists()
        assert _wait_for_launcher_processes_to_stop(api_port, web_port)
    finally:
        _cleanup_launcher_processes(api_port, web_port)


def test_state_write_failure_rolls_back_both_processes(
    launcher_project: Path,
) -> None:
    api_port = _free_port()
    web_port = _free_port()
    env = os.environ.copy()
    env["STOCK_WAVE_LAUNCHER_TEST_FAILURE"] = "state_write"

    try:
        result = _run_script(
            launcher_project / "scripts" / "start-local.ps1",
            "-ApiPort",
            str(api_port),
            "-WebPort",
            str(web_port),
            "-NoBrowser",
            cwd=launcher_project,
            env=env,
        )

        assert result.returncode != 0
        assert "after creating incomplete state file" in result.stdout + result.stderr
        assert not (launcher_project / ".local" / "local-launcher.json").exists()
        assert _wait_for_launcher_processes_to_stop(api_port, web_port)
    finally:
        _cleanup_launcher_processes(api_port, web_port)


def test_state_write_failure_injection_writes_incomplete_file_before_throw() -> None:
    text = START_SCRIPT.read_text(encoding="utf-8")

    incomplete_write = 'Set-Content -LiteralPath $StatePath -Value \'{"incomplete":\''
    injected_error = "after creating incomplete state file"
    assert incomplete_write in text
    assert injected_error in text
    assert text.index(incomplete_write) < text.index(injected_error)


def test_failure_injection_is_ignored_without_pytest_context(
    launcher_project: Path,
) -> None:
    api_port = _free_port()
    web_port = _free_port()
    start_script = launcher_project / "scripts" / "start-local.ps1"
    stop_script = launcher_project / "scripts" / "stop-local.ps1"
    env = os.environ.copy()
    env.pop("PYTEST_CURRENT_TEST", None)
    env["STOCK_WAVE_LAUNCHER_TEST_FAILURE"] = "frontend_start"

    try:
        start = _run_script(
            start_script,
            "-ApiPort",
            str(api_port),
            "-WebPort",
            str(web_port),
            "-NoBrowser",
            cwd=launcher_project,
            env=env,
        )
        assert start.returncode == 0, start.stdout + start.stderr
        assert (launcher_project / ".local" / "local-launcher.json").exists()

        with urllib.request.urlopen(
            f"http://127.0.0.1:{api_port}/api/health", timeout=5
        ) as response:
            assert json.load(response)["status"] == "ok"
        with urllib.request.urlopen(f"http://127.0.0.1:{web_port}", timeout=5) as response:
            assert response.status == 200
    finally:
        state_path = launcher_project / ".local" / "local-launcher.json"
        if state_path.exists():
            _run_script(stop_script, cwd=launcher_project)
        _cleanup_launcher_processes(api_port, web_port)


def test_browser_open_failure_keeps_services_running(
    launcher_project: Path,
) -> None:
    api_port = _free_port()
    web_port = _free_port()
    start_script = launcher_project / "scripts" / "start-local.ps1"
    stop_script = launcher_project / "scripts" / "stop-local.ps1"
    env = os.environ.copy()
    env["STOCK_WAVE_LAUNCHER_TEST_FAILURE"] = "browser_open"

    try:
        start = _run_script(
            start_script,
            "-ApiPort",
            str(api_port),
            "-WebPort",
            str(web_port),
            cwd=launcher_project,
            env=env,
        )
        output = start.stdout + start.stderr
        assert start.returncode == 0, output
        assert "Browser could not be opened" in output
        assert f"http://127.0.0.1:{web_port}" in output

        state_path = launcher_project / ".local" / "local-launcher.json"
        state = json.loads(state_path.read_text(encoding="utf-8-sig"))
        assert state["backend"]["port"] == api_port
        assert state["frontend"]["port"] == web_port

        with urllib.request.urlopen(
            f"http://127.0.0.1:{api_port}/api/health", timeout=5
        ) as response:
            assert json.load(response)["status"] == "ok"
        with urllib.request.urlopen(f"http://127.0.0.1:{web_port}", timeout=5) as response:
            assert response.status == 200

        stop = _run_script(stop_script, cwd=launcher_project)
        assert stop.returncode == 0, stop.stdout + stop.stderr
    finally:
        state_path = launcher_project / ".local" / "local-launcher.json"
        if state_path.exists():
            _run_script(stop_script, cwd=launcher_project)
        _cleanup_launcher_processes(api_port, web_port)


def test_browser_warning_stays_nonterminating_when_warning_preference_is_stop(
    launcher_project: Path,
) -> None:
    api_port = _free_port()
    web_port = _free_port()
    stop_script = launcher_project / "scripts" / "stop-local.ps1"
    wrapper_script = launcher_project / "warning-stop-launcher.ps1"
    wrapper_script.write_text(
        '$WarningPreference = "Stop"\n'
        '& (Join-Path $PSScriptRoot "scripts\\start-local.ps1") @args\n'
        "exit $LASTEXITCODE\n",
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["STOCK_WAVE_LAUNCHER_TEST_FAILURE"] = "browser_open"

    try:
        start = _run_script(
            wrapper_script,
            "-ApiPort",
            str(api_port),
            "-WebPort",
            str(web_port),
            cwd=launcher_project,
            env=env,
        )
        output = start.stdout + start.stderr
        assert start.returncode == 0, output
        assert "Browser could not be opened" in output
        assert f"http://127.0.0.1:{web_port}" in output

        state_path = launcher_project / ".local" / "local-launcher.json"
        state = json.loads(state_path.read_text(encoding="utf-8-sig"))
        assert state["backend"]["port"] == api_port
        assert state["frontend"]["port"] == web_port

        with urllib.request.urlopen(
            f"http://127.0.0.1:{api_port}/api/health", timeout=5
        ) as response:
            assert json.load(response)["status"] == "ok"
        with urllib.request.urlopen(f"http://127.0.0.1:{web_port}", timeout=5) as response:
            assert response.status == 200
    finally:
        _run_script(stop_script, cwd=launcher_project)
        _cleanup_launcher_processes(api_port, web_port)


@pytest.mark.parametrize(
    "launcher_project", ["launcher project with spaces"], indirect=True
)
def test_launcher_runs_from_project_path_with_spaces(
    launcher_project: Path,
) -> None:
    api_port = _free_port()
    web_port = _free_port()
    start_script = launcher_project / "scripts" / "start-local.ps1"
    stop_script = launcher_project / "scripts" / "stop-local.ps1"

    try:
        start = _run_script(
            start_script,
            "-ApiPort",
            str(api_port),
            "-WebPort",
            str(web_port),
            "-NoBrowser",
            cwd=launcher_project,
            timeout=30,
        )
        assert start.returncode == 0, start.stdout + start.stderr

        with urllib.request.urlopen(
            f"http://127.0.0.1:{api_port}/api/health", timeout=5
        ) as response:
            assert json.load(response)["status"] == "ok"
        with urllib.request.urlopen(f"http://127.0.0.1:{web_port}", timeout=5) as response:
            assert response.status == 200

        stop = _run_script(stop_script, cwd=launcher_project)
        assert stop.returncode == 0, stop.stdout + stop.stderr
        second_stop = _run_script(stop_script, cwd=launcher_project)
        assert second_stop.returncode == 0, second_stop.stdout + second_stop.stderr
        assert not (launcher_project / ".local" / "local-launcher.json").exists()
        assert _wait_for_launcher_processes_to_stop(api_port, web_port)
    finally:
        state_path = launcher_project / ".local" / "local-launcher.json"
        if state_path.exists():
            _run_script(stop_script, cwd=launcher_project)
        _cleanup_launcher_processes(api_port, web_port)


def test_stop_keeps_state_when_recorded_pid_does_not_match(
    launcher_project: Path,
) -> None:
    state_dir = launcher_project / ".local"
    state_dir.mkdir()
    state_path = state_dir / "local-launcher.json"
    state_path.write_text(
        json.dumps(
            {
                "projectRoot": str(launcher_project.resolve()),
                "frontend": {"pid": os.getpid(), "port": _free_port()},
                "backend": None,
            }
        ),
        encoding="utf-8",
    )

    result = _run_script(
        launcher_project / "scripts" / "stop-local.ps1",
        cwd=launcher_project,
    )

    assert result.returncode != 0
    assert "was not stopped" in result.stdout + result.stderr
    assert state_path.exists()
