from __future__ import annotations

import subprocess
import tempfile
import time
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LLMResult:
    success: bool
    model: str
    duration_ms: int
    text: str
    error: str | None
    exit_code: int | None


class FakeCodexProvider:
    def __init__(self, model: str = "fake-codex") -> None:
        self.model = model

    def run(self, prompt: str) -> LLMResult:
        item_names = _names_from_prompt(prompt)
        item_line = (
            f"相关条目：{'、'.join(item_names)}。"
            if item_names
            else "相关条目：report_json 未列出具体名称。"
        )
        text = "\n".join(
            [
                "数据状态：已读取结构化报告。",
                "组合风险：保留报告中的风险标记和数据质量提示。",
                "自选股状态分布：按 report_json 中的 state_distribution 汇总。",
                "重点观察项：仅复述 report_json 中已有条目。",
                "仓位复核项：仅复述 report_json 中已有条目。",
                item_line,
                "数据质量提示：如有缺失或降级，按 report_json 原样说明。",
                "声明：本摘要仅解释结构化报告，不构成投资建议。",
            ]
        )
        return LLMResult(
            success=True,
            model=self.model,
            duration_ms=0,
            text=text,
            error=None,
            exit_code=0,
        )


class CodexCliProvider:
    def __init__(
        self,
        *,
        cli_path: str | Path,
        model: str,
        timeout_seconds: int,
        sandbox_mode: str,
    ) -> None:
        self.cli_path = Path(cli_path)
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.sandbox_mode = sandbox_mode

    def run(self, prompt: str) -> LLMResult:
        started = time.perf_counter()
        if not self.cli_path.exists():
            return self._failure(started, "cli_path_not_found", None)

        with tempfile.NamedTemporaryFile(
            mode="w+",
            suffix=".txt",
            delete=False,
            encoding="utf-8",
        ) as output:
            output_path = Path(output.name)

        args = [
            str(self.cli_path),
            "exec",
            "-m",
            self.model,
            "--skip-git-repo-check",
            "--sandbox",
            self.sandbox_mode,
            "--output-last-message",
            str(output_path),
        ]
        try:
            completed = subprocess.run(
                args,
                input=prompt,
                text=True,
                capture_output=True,
                timeout=self.timeout_seconds,
                check=False,
            )
        except (subprocess.TimeoutExpired, TimeoutError):
            output_path.unlink(missing_ok=True)
            return self._failure(started, "timeout", None)

        text = ""
        if output_path.exists():
            text = output_path.read_text(encoding="utf-8").strip()
            output_path.unlink(missing_ok=True)
        if completed.returncode != 0:
            return self._failure(
                started,
                (completed.stderr or "codex_cli_failed").strip(),
                completed.returncode,
            )
        if not text:
            text = (completed.stdout or "").strip()
        return LLMResult(
            success=True,
            model=self.model,
            duration_ms=_duration_ms(started),
            text=text,
            error=None,
            exit_code=completed.returncode,
        )

    def _failure(
        self,
        started: float,
        error: str,
        exit_code: int | None,
    ) -> LLMResult:
        return LLMResult(
            success=False,
            model=self.model,
            duration_ms=_duration_ms(started),
            text="",
            error=error,
            exit_code=exit_code,
        )


def _duration_ms(started: float) -> int:
    return max(0, int((time.perf_counter() - started) * 1000))


def _names_from_prompt(prompt: str) -> list[str]:
    try:
        payload = json.loads(prompt)
    except json.JSONDecodeError:
        return []
    report = payload.get("report_json", {})
    if not isinstance(report, dict):
        return []
    names: list[str] = []
    for key in (
        "attention_items",
        "position_review_candidates",
        "rotation_watch_candidates",
    ):
        values = report.get(key, [])
        if not isinstance(values, list):
            continue
        for item in values:
            if isinstance(item, dict) and item.get("name"):
                names.append(str(item["name"]))
    return list(dict.fromkeys(names))
