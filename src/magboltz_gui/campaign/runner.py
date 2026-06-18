"""Execution support for generated Magboltz campaigns."""

from __future__ import annotations

from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import threading
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
    executed_at: str

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
    """Write and optionally execute campaign runs.

    The class name is kept for API compatibility; ``max_workers`` enables
    bounded parallel execution of independent Magboltz subprocesses.
    """

    def __init__(
        self,
        executable: str = "magboltz",
        timeout_seconds: float | None = None,
        max_workers: int = 1,
    ) -> None:
        self.executable = executable
        self.timeout_seconds = timeout_seconds
        self.max_workers = max_workers
        self._processes: set[subprocess.Popen] = set()
        self._process_lock = threading.Lock()

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
        """Materialize and execute all generated runs."""
        runs = self.prepare(plan, output_dir)
        results_by_id: dict[str, CampaignExecutionResult] = {}
        total = len(runs)
        self._write_status(output_dir / "run_status.csv", [])
        if prepared_callback is not None:
            prepared_callback(total)
        if total == 0:
            return []

        workers = min(_effective_worker_count(self.max_workers), total)
        if workers <= 1:
            return self._run_serial(
                runs,
                output_dir,
                progress_callback=progress_callback,
                cancel_callback=cancel_callback,
                result_callback=result_callback,
            )
        return self._run_parallel(
            runs,
            output_dir,
            workers,
            progress_callback=progress_callback,
            cancel_callback=cancel_callback,
            result_callback=result_callback,
            results_by_id=results_by_id,
        )

    def _run_serial(
        self,
        runs: list[CampaignRun],
        output_dir: Path,
        progress_callback: Callable[[int, int, str], None] | None,
        cancel_callback: Callable[[], bool] | None,
        result_callback: Callable[[CampaignExecutionResult], None] | None,
    ) -> list[CampaignExecutionResult]:
        results: list[CampaignExecutionResult] = []
        total = len(runs)
        try:
            for run in runs:
                if cancel_callback is not None and cancel_callback():
                    self._write_status(output_dir / "run_status.csv", results)
                    raise CampaignCancelled(results)
                result = self._execute_run(output_dir, run, cancel_callback)
                results.append(result)
                self._write_status(output_dir / "run_status.csv", results)
                if result_callback is not None:
                    result_callback(result)
                if cancel_callback is not None and cancel_callback():
                    self._write_status(output_dir / "run_status.csv", results)
                    raise CampaignCancelled(results)
                if progress_callback is not None:
                    progress_callback(len(results), total, run.run_id)
        except CampaignCancelled:
            self._terminate_running_processes()
            raise
        self._write_status(output_dir / "run_status.csv", results)
        return results

    def _run_parallel(
        self,
        runs: list[CampaignRun],
        output_dir: Path,
        workers: int,
        progress_callback: Callable[[int, int, str], None] | None,
        cancel_callback: Callable[[], bool] | None,
        result_callback: Callable[[CampaignExecutionResult], None] | None,
        results_by_id: dict[str, CampaignExecutionResult],
    ) -> list[CampaignExecutionResult]:
        total = len(runs)
        run_order = {run.run_id: index for index, run in enumerate(runs)}

        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="magboltz-campaign") as executor:
            futures: dict[Future[CampaignExecutionResult], CampaignRun] = {
                executor.submit(self._execute_run, output_dir, run, cancel_callback): run for run in runs
            }
            pending = set(futures)
            while pending:
                if cancel_callback is not None and cancel_callback():
                    self._terminate_running_processes()
                    for future in pending:
                        future.cancel()
                    results = _ordered_results(results_by_id, run_order)
                    self._write_status(output_dir / "run_status.csv", results)
                    raise CampaignCancelled(results)

                done, pending = wait(pending, timeout=0.1, return_when=FIRST_COMPLETED)
                for future in done:
                    try:
                        result = future.result()
                    except CampaignCancelled:
                        self._terminate_running_processes()
                        results = _ordered_results(results_by_id, run_order)
                        self._write_status(output_dir / "run_status.csv", results)
                        raise CampaignCancelled(results) from None
                    results_by_id[result.run_id] = result
                    results = _ordered_results(results_by_id, run_order)
                    self._write_status(output_dir / "run_status.csv", results)
                    if result_callback is not None:
                        result_callback(result)
                    if progress_callback is not None:
                        progress_callback(len(results_by_id), total, result.run_id)

        results = _ordered_results(results_by_id, run_order)
        self._write_status(output_dir / "run_status.csv", results)
        return results

    def _execute_run(
        self,
        output_dir: Path,
        run: CampaignRun,
        cancel_callback: Callable[[], bool] | None,
    ) -> CampaignExecutionResult:
        if cancel_callback is not None and cancel_callback():
            raise CampaignCancelled([])
        run_dir = output_dir / run.run_id
        input_path = run_dir / "input.in"
        stdout_path = run_dir / "stdout.txt"
        stderr_path = run_dir / "stderr.txt"
        returncode = self._run_one(input_path, stdout_path, stderr_path, cancel_callback)
        return CampaignExecutionResult(
            run_id=run.run_id,
            returncode=returncode,
            input_path=input_path,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            executed_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        )

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
            self._register_process(process)
            try:
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
            finally:
                self._unregister_process(process)

    def _register_process(self, process: subprocess.Popen) -> None:
        with self._process_lock:
            self._processes.add(process)

    def _unregister_process(self, process: subprocess.Popen) -> None:
        with self._process_lock:
            self._processes.discard(process)

    def _terminate_running_processes(self) -> None:
        with self._process_lock:
            processes = list(self._processes)
        for process in processes:
            if process.poll() is None:
                _terminate_process(process)

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
                fieldnames=["run_id", "status", "returncode", "executed_at", "input", "stdout", "stderr"],
            )
            writer.writeheader()
            for result in results:
                writer.writerow(
                    {
                        "run_id": result.run_id,
                        "status": "done" if result.ok else "failed",
                        "returncode": result.returncode,
                        "executed_at": result.executed_at,
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


def _effective_worker_count(max_workers: int) -> int:
    if max_workers == 0:
        return max(os.cpu_count() or 1, 1)
    return max(max_workers, 1)


def _ordered_results(
    results_by_id: dict[str, CampaignExecutionResult],
    run_order: dict[str, int],
) -> list[CampaignExecutionResult]:
    return sorted(results_by_id.values(), key=lambda result: run_order.get(result.run_id, len(run_order)))


def _terminate_process(process: subprocess.Popen) -> None:
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)
