"""Serial execution support for generated Magboltz campaigns."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import time
from typing import Callable

from magboltz_gui.campaign.campaign import CampaignPlan, CampaignRun, generate_runs
from magboltz_gui.campaign.sweep import ExplicitSweep, LinearSweep, LogSweep, SweepMode
from magboltz_gui.util import parser


@dataclass(frozen=True)
class CampaignExecutionResult:
    """Execution status for one campaign run."""

    run_id: str
    returncode: int
    input_path: Path
    stdout_path: Path
    stderr_path: Path

    @property
    def ok(self) -> bool:
        """Return whether the external command completed successfully."""
        return self.returncode == 0


class CampaignCancelled(Exception):
    """Raised when a campaign execution is cancelled by the caller."""

    def __init__(self, results: list[CampaignExecutionResult]) -> None:
        super().__init__("Campaign run cancelled")
        self.results = results


class SerialCampaignRunner:
    """Write and optionally execute campaign runs one after another."""

    def __init__(self, executable: str = "magboltz", timeout_seconds: float | None = None) -> None:
        self.executable = executable
        self.timeout_seconds = timeout_seconds

    def prepare(self, plan: CampaignPlan, output_dir: Path) -> list[CampaignRun]:
        """Materialize campaign input cards and summary metadata without executing them."""
        runs = generate_runs(plan)
        output_dir.mkdir(parents=True, exist_ok=True)
        parser.save(plan.base_cards, output_dir / "base_input.in")
        for run in runs:
            run_dir = output_dir / run.run_id
            run_dir.mkdir(parents=True, exist_ok=True)
            parser.save(run.input_cards, run_dir / "input.in")
            (run_dir / "parameters.json").write_text(json.dumps(run.parameter_values, indent=2) + "\n", encoding="utf-8")
        self._write_summary(output_dir / "summary.csv", runs)
        self._write_manifest(output_dir / "campaign.json", plan, runs)
        return runs

    def run(
        self,
        plan: CampaignPlan,
        output_dir: Path,
        progress_callback: Callable[[int, int, str], None] | None = None,
        cancel_callback: Callable[[], bool] | None = None,
        prepared_callback: Callable[[int], None] | None = None,
        result_callback: Callable[[CampaignExecutionResult], None] | None = None,
    ) -> list[CampaignExecutionResult]:
        """Materialize and execute all generated runs serially."""
        runs = self.prepare(plan, output_dir)
        results: list[CampaignExecutionResult] = []
        total = len(runs)
        self._write_status(output_dir / "run_status.csv", results)
        if prepared_callback is not None:
            prepared_callback(total)
        for run in runs:
            if cancel_callback is not None and cancel_callback():
                self._write_status(output_dir / "run_status.csv", results)
                raise CampaignCancelled(results)
            run_dir = output_dir / run.run_id
            input_path = run_dir / "input.in"
            stdout_path = run_dir / "stdout.txt"
            stderr_path = run_dir / "stderr.txt"
            returncode = self._run_one(input_path, stdout_path, stderr_path, cancel_callback)
            results.append(
                CampaignExecutionResult(
                    run_id=run.run_id,
                    returncode=returncode,
                    input_path=input_path,
                    stdout_path=stdout_path,
                    stderr_path=stderr_path,
                )
            )
            self._write_status(output_dir / "run_status.csv", results)
            if result_callback is not None:
                result_callback(results[-1])
            if cancel_callback is not None and cancel_callback():
                self._write_status(output_dir / "run_status.csv", results)
                raise CampaignCancelled(results)
            if progress_callback is not None:
                progress_callback(len(results), total, run.run_id)
        self._write_status(output_dir / "run_status.csv", results)
        return results

    def _run_one(
        self,
        input_path: Path,
        stdout_path: Path,
        stderr_path: Path,
        cancel_callback: Callable[[], bool] | None,
    ) -> int:
        input_text = input_path.read_text(encoding="utf-8")
        started_at = time.monotonic()
        with stdout_path.open("w", encoding="utf-8") as stdout_handle, stderr_path.open("w", encoding="utf-8") as stderr_handle:
            process = subprocess.Popen(
                [self.executable],
                stdin=subprocess.PIPE,
                stdout=stdout_handle,
                stderr=stderr_handle,
                text=True,
            )
            assert process.stdin is not None
            process.stdin.write(input_text)
            process.stdin.close()
            while process.poll() is None:
                if cancel_callback is not None and cancel_callback():
                    _terminate_process(process)
                    return process.returncode if process.returncode is not None else -15
                if self.timeout_seconds is not None and time.monotonic() - started_at > self.timeout_seconds:
                    _terminate_process(process)
                    raise subprocess.TimeoutExpired([self.executable], self.timeout_seconds)
                time.sleep(0.1)
            return process.returncode if process.returncode is not None else 0

    def _write_summary(self, path: Path, runs: list[CampaignRun]) -> None:
        labels = list(runs[0].parameter_values) if runs else []
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["run_id", *labels])
            writer.writeheader()
            for run in runs:
                writer.writerow({"run_id": run.run_id, **run.parameter_values})

    def _write_status(self, path: Path, results: list[CampaignExecutionResult]) -> None:
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["run_id", "status", "returncode", "input", "stdout", "stderr"],
            )
            writer.writeheader()
            for result in results:
                writer.writerow(
                    {
                        "run_id": result.run_id,
                        "status": "done" if result.ok else "failed",
                        "returncode": result.returncode,
                        "input": result.input_path.as_posix(),
                        "stdout": result.stdout_path.as_posix(),
                        "stderr": result.stderr_path.as_posix(),
                    }
                )

    def _write_manifest(self, path: Path, plan: CampaignPlan, runs: list[CampaignRun]) -> None:
        manifest = {
            "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "total_runs": len(runs),
            "base_input": "base_input.in",
            "matrix": _matrix_metadata(plan),
            "sweeps": [_sweep_metadata(parameter) for parameter in plan.parameters],
        }
        path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def _matrix_metadata(plan: CampaignPlan) -> dict[str, int]:
    independent = [parameter for parameter in plan.parameters if parameter.mode == SweepMode.PRODUCT]
    coupled = [parameter for parameter in plan.parameters if parameter.mode == SweepMode.COUPLED]
    product_size = _product_size([len(parameter.sweep.values()) for parameter in independent])
    coupled_size = len(coupled[0].sweep.values()) if coupled else 1
    return {
        "independent_rows": len(independent),
        "product_size": product_size,
        "coupled_rows": len(coupled),
        "coupled_size": coupled_size,
        "total": product_size * coupled_size,
    }


def _sweep_metadata(parameter) -> dict[str, object]:
    sweep = parameter.sweep
    metadata: dict[str, object] = {
        "path": parameter.path,
        "label": parameter.label,
        "mode": parameter.mode.value,
        "points": len(sweep.values()),
    }
    if isinstance(sweep, ExplicitSweep):
        metadata.update({"sweep_type": "values", "values": sweep.values()})
    elif isinstance(sweep, LinearSweep):
        metadata.update({"sweep_type": "linear", "start": sweep.start, "stop": sweep.stop})
    elif isinstance(sweep, LogSweep):
        metadata.update({"sweep_type": "logspace", "start": sweep.start, "stop": sweep.stop})
    else:
        metadata.update({"sweep_type": type(sweep).__name__})
    return metadata


def _product_size(sizes: list[int]) -> int:
    total = 1
    for size in sizes:
        total *= size
    return total


def _terminate_process(process: subprocess.Popen) -> None:
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)
