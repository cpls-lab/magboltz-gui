"""Serial execution support for generated Magboltz campaigns."""

from __future__ import annotations

import csv
from dataclasses import dataclass
import json
from pathlib import Path
import subprocess

from magboltz_gui.campaign.campaign import CampaignPlan, CampaignRun, generate_runs
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


class SerialCampaignRunner:
    """Write and optionally execute campaign runs one after another."""

    def __init__(self, executable: str = "magboltz", timeout_seconds: float | None = None) -> None:
        self.executable = executable
        self.timeout_seconds = timeout_seconds

    def prepare(self, plan: CampaignPlan, output_dir: Path) -> list[CampaignRun]:
        """Materialize campaign input cards and summary metadata without executing them."""
        runs = generate_runs(plan)
        output_dir.mkdir(parents=True, exist_ok=True)
        for run in runs:
            run_dir = output_dir / run.run_id
            run_dir.mkdir(parents=True, exist_ok=True)
            parser.save(run.input_cards, run_dir / "input.in")
            (run_dir / "parameters.json").write_text(json.dumps(run.parameter_values, indent=2) + "\n", encoding="utf-8")
        self._write_summary(output_dir / "summary.csv", runs)
        return runs

    def run(self, plan: CampaignPlan, output_dir: Path) -> list[CampaignExecutionResult]:
        """Materialize and execute all generated runs serially."""
        runs = self.prepare(plan, output_dir)
        results: list[CampaignExecutionResult] = []
        for run in runs:
            run_dir = output_dir / run.run_id
            input_path = run_dir / "input.in"
            stdout_path = run_dir / "stdout.txt"
            stderr_path = run_dir / "stderr.txt"
            completed = subprocess.run(
                [self.executable],
                input=input_path.read_text(encoding="utf-8"),
                text=True,
                capture_output=True,
                timeout=self.timeout_seconds,
                check=False,
            )
            stdout_path.write_text(completed.stdout, encoding="utf-8")
            stderr_path.write_text(completed.stderr, encoding="utf-8")
            results.append(
                CampaignExecutionResult(
                    run_id=run.run_id,
                    returncode=completed.returncode,
                    input_path=input_path,
                    stdout_path=stdout_path,
                    stderr_path=stderr_path,
                )
            )
        return results

    def _write_summary(self, path: Path, runs: list[CampaignRun]) -> None:
        labels = list(runs[0].parameter_values) if runs else []
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["run_id", *labels])
            writer.writeheader()
            for run in runs:
                writer.writerow({"run_id": run.run_id, **run.parameter_values})
