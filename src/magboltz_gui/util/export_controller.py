from __future__ import annotations

import json
import os
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from magboltz_gui.util.export_types import ExportFormat, ExportType, CsvOptions, JsonOptions, XmlOptions
from magboltz_gui.util.run_result import RunResult, GasFrequencies, CollisionProcess


def _safe_float(val: Optional[float]) -> Optional[float]:
    return None if val is None else float(val)


def _unit_header(name: str, unit: Optional[str], include_units: bool) -> str:
    return f"{name} [{unit}]" if include_units and unit else name


def _write_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("wb", delete=False, dir=path.parent) as tmp:
        tmp.write(data)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_path = Path(tmp.name)
    tmp_path.replace(path)


def _mixture_flat_columns(run: RunResult) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for i, gas in enumerate(run.mixture, start=1):
        out[f"gas{i}_name"] = gas.name
        out[f"gas{i}_model_tag"] = gas.model_tag
        out[f"gas{i}_fraction_percent"] = gas.fraction_percent
    return out


def _summary_dict(run: RunResult) -> Dict[str, Any]:
    cond = run.conditions
    trans = run.transport
    freq = run.frequencies_total
    counts = run.counts
    return {
        "gas_temperature_C": cond.gas_temperature_C,
        "gas_pressure_torr": cond.gas_pressure_torr,
        "electric_field_V_cm": cond.electric_field_V_cm,
        "magnetic_field_kG": cond.magnetic_field_kG,
        "angle_E_B_deg": cond.angle_E_B_deg,
        "cyclotron_freq_rad_ps": cond.cyclotron_freq_rad_ps,
        "initial_electron_energy_eV": cond.initial_electron_energy_eV,
        "integration_E_min_eV": cond.integration.E_min_eV,
        "integration_E_max_eV": cond.integration.E_max_eV,
        "integration_n_steps": cond.integration.n_steps,
        "penning_included": cond.flags.penning_included,
        "thermal_motion_included": cond.flags.thermal_motion_included,
        "anisotropic_scattering_type": cond.flags.anisotropic_scattering_type,
        "short_decorrelation_length_collisions": cond.flags.short_decorrelation_length_collisions,
        "total_real_collisions": counts.total_real_collisions,
        "num_null_collisions": counts.num_null_collisions,
        "calculated_max_collision_time_ps": counts.calculated_max_collision_time_ps,
        "vx_um_ns": trans.vx_um_ns.v_um_ns if trans.vx_um_ns else None,
        "vx_err_pct": trans.vx_um_ns.err_pct if trans.vx_um_ns else None,
        "vy_um_ns": trans.vy_um_ns.v_um_ns if trans.vy_um_ns else None,
        "vy_err_pct": trans.vy_um_ns.err_pct if trans.vy_um_ns else None,
        "vz_um_ns": trans.vz_um_ns.v_um_ns if trans.vz_um_ns else None,
        "vz_err_pct": trans.vz_um_ns.err_pct if trans.vz_um_ns else None,
        "DT_cm2_s": trans.diffusion.transverse.get("DT_cm2_s").value if "DT_cm2_s" in trans.diffusion.transverse else None,
        "DT_cm2_s_err_pct": trans.diffusion.transverse.get("DT_cm2_s").err_pct if "DT_cm2_s" in trans.diffusion.transverse else None,
        "DL_cm2_s": trans.diffusion.longitudinal.get("DL_cm2_s").value if "DL_cm2_s" in trans.diffusion.longitudinal else None,
        "DL_cm2_s_err_pct": trans.diffusion.longitudinal.get("DL_cm2_s").err_pct if "DL_cm2_s" in trans.diffusion.longitudinal else None,
        "ionisation_rate_per_cm": trans.ionisation_rate_per_cm,
        "ionisation_rate_err_pct": trans.ionisation_rate_err_pct,
        "attachment_rate_per_cm": trans.attachment_rate_per_cm,
        "attachment_rate_err_pct": trans.attachment_rate_err_pct,
        "mean_electron_energy_eV": trans.mean_electron_energy_eV,
        "mean_electron_energy_err_pct": trans.mean_electron_energy_err_pct,
        "total_coll_freq_1e12_s": freq.total_coll_freq_1e12_s,
        "elastic_coll_freq_1e12_s": freq.elastic_coll_freq_1e12_s,
        "inelastic_coll_freq_1e12_s": freq.inelastic_coll_freq_1e12_s,
        "ionisation_coll_freq_1e12_s": freq.ionisation_coll_freq_1e12_s,
        "attachment_coll_freq_1e12_s": freq.attachment_coll_freq_1e12_s,
    }


def available_export_types(run: RunResult) -> List[ExportType]:
    types = [ExportType.SUMMARY]
    if run.tables.convergence_table:
        types.append(ExportType.CONVERGENCE_TABLE)
    if run.tables.energy_distribution:
        types.append(ExportType.ENERGY_DISTRIBUTION)
    if run.frequencies_by_gas:
        types.append(ExportType.COLLISION_FREQUENCIES)
    types.append(ExportType.FULL_RUN_ARCHIVE)
    return types


def _csv_rows_summary(run: RunResult, opts: CsvOptions) -> Tuple[List[str], List[List[Any]]]:
    data = _summary_dict(run)
    if opts.flatten_mixture:
        data.update(_mixture_flat_columns(run))
    if opts.include_metadata:
        data = {
            "tool_version": run.meta.tool_version,
            "timestamp_utc": run.meta.timestamp_utc,
            "input_path": run.input.input_path,
            **data,
        }
    headers = list(data.keys())
    units = {
        "gas_temperature_C": "C",
        "gas_pressure_torr": "torr",
        "electric_field_V_cm": "V/cm",
        "magnetic_field_kG": "kG",
        "angle_E_B_deg": "deg",
        "cyclotron_freq_rad_ps": "rad/ps",
        "initial_electron_energy_eV": "eV",
        "integration_E_min_eV": "eV",
        "integration_E_max_eV": "eV",
        "vx_um_ns": "um/ns",
        "vy_um_ns": "um/ns",
        "vz_um_ns": "um/ns",
        "DT_cm2_s": "cm^2/s",
        "DL_cm2_s": "cm^2/s",
        "ionisation_rate_per_cm": "1/cm",
        "attachment_rate_per_cm": "1/cm",
        "mean_electron_energy_eV": "eV",
        "total_coll_freq_1e12_s": "1e12/s",
        "elastic_coll_freq_1e12_s": "1e12/s",
        "inelastic_coll_freq_1e12_s": "1e12/s",
        "ionisation_coll_freq_1e12_s": "1e12/s",
        "attachment_coll_freq_1e12_s": "1e12/s",
    }
    if opts.include_units:
        headers = [_unit_header(h, units.get(h), True) for h in headers]
    row = [data[k] for k in data.keys()]
    return headers, [row]


def _csv_rows_convergence(run: RunResult, opts: CsvOptions) -> Tuple[List[str], List[List[Any]]]:
    headers = ["vel", "pos", "time", "energy", "count", "difxx", "difyy", "difzz"]
    units = {"vel": "um/ns", "pos": "", "time": "ps", "energy": "eV", "count": "", "difxx": "cm^2/s", "difyy": "cm^2/s", "difzz": "cm^2/s"}
    if opts.include_units:
        headers = [_unit_header(h, units.get(h), True) for h in headers]
    rows = [[r.vel, r.pos, r.time, r.energy, r.count, r.difxx, r.difyy, r.difzz] for r in run.tables.convergence_table]
    if opts.include_metadata:
        rows = [[run.meta.tool_version, run.meta.timestamp_utc, run.input.input_path, *row] for row in rows]
        headers = ["tool_version", "timestamp_utc", "input_path", *headers]
    return headers, rows


def _csv_rows_energy(run: RunResult, opts: CsvOptions) -> Tuple[List[str], List[List[Any]]]:
    headers = ["E_eV", "spec"]
    units = {"E_eV": "eV", "spec": ""}
    if opts.include_units:
        headers = [_unit_header(h, units.get(h), True) for h in headers]
    rows = [[r.E_eV, r.spec] for r in run.tables.energy_distribution]
    if opts.include_metadata:
        rows = [[run.meta.tool_version, run.meta.timestamp_utc, run.input.input_path, *row] for row in rows]
        headers = ["tool_version", "timestamp_utc", "input_path", *headers]
    return headers, rows


def _csv_rows_collfreq(run: RunResult, opts: CsvOptions) -> Tuple[List[str], List[List[Any]]]:
    headers = ["gas_name", "process_label", "category", "eloss_eV", "freq_1e12_s", "err_pct"]
    if opts.include_units:
        headers = [_unit_header("eloss_eV", "eV", True) if h == "eloss_eV" else h for h in headers]
    rows: List[List[Any]] = []
    for gas in run.frequencies_by_gas:
        for proc in gas.processes:
            rows.append([gas.gas_name, proc.label, proc.category, proc.eloss_eV, proc.freq_1e12_s, proc.err_pct])
    if opts.include_metadata:
        rows = [[run.meta.tool_version, run.meta.timestamp_utc, run.input.input_path, *row] for row in rows]
        headers = ["tool_version", "timestamp_utc", "input_path", *headers]
    return headers, rows


def export_csv(run: RunResult, export_type: ExportType, path: Path, opts: CsvOptions) -> None:
    if export_type == ExportType.SUMMARY:
        headers, rows = _csv_rows_summary(run, opts)
    elif export_type == ExportType.CONVERGENCE_TABLE:
        headers, rows = _csv_rows_convergence(run, opts)
    elif export_type == ExportType.ENERGY_DISTRIBUTION:
        headers, rows = _csv_rows_energy(run, opts)
    elif export_type == ExportType.COLLISION_FREQUENCIES:
        headers, rows = _csv_rows_collfreq(run, opts)
    else:
        raise ValueError("CSV does not support full run archive")

    lines = [opts.delimiter.join(str(h) for h in headers)]
    for row in rows:
        lines.append(opts.delimiter.join("" if v is None else str(v) for v in row))
    data = ("\n".join(lines) + "\n").encode("utf-8")
    _write_atomic(path, data)


def _filter_run_for_export(run: RunResult, export_type: ExportType, opts: JsonOptions | XmlOptions) -> Dict[str, Any]:
    data = run.to_dict()
    if not opts.include_input_text:
        data["input"]["input_text"] = None
    if not opts.include_raw_stdout:
        data["raw"]["stdout_text"] = None
    if not opts.include_parser_warnings:
        data["raw"]["parser_warnings"] = []
    if export_type == ExportType.FULL_RUN_ARCHIVE:
        return data
    if export_type == ExportType.SUMMARY:
        return _summary_dict(run)
    if export_type == ExportType.CONVERGENCE_TABLE:
        return [asdict(r) for r in run.tables.convergence_table]
    if export_type == ExportType.ENERGY_DISTRIBUTION:
        return [asdict(r) for r in run.tables.energy_distribution]
    if export_type == ExportType.COLLISION_FREQUENCIES:
        rows = []
        for gas in run.frequencies_by_gas:
            for proc in gas.processes:
                rows.append(
                    {
                        "gas_name": gas.gas_name,
                        "process_label": proc.label,
                        "category": proc.category,
                        "eloss_eV": proc.eloss_eV,
                        "freq_1e12_s": proc.freq_1e12_s,
                        "err_pct": proc.err_pct,
                    }
                )
        return rows
    raise ValueError("Unknown export type")


def export_json(run: RunResult, export_type: ExportType, path: Path, opts: JsonOptions) -> None:
    payload = {
        "schema_version": "1.0",
        "export_type": export_type.value,
        "data": _filter_run_for_export(run, export_type, opts),
        "units": run.tables.units,
    }
    text = json.dumps(payload, indent=2 if opts.pretty_print else None)
    _write_atomic(path, text.encode("utf-8"))


def _xml_append(parent: ET.Element, key: str, value: Any) -> None:
    if isinstance(value, list):
        list_elem = ET.SubElement(parent, key)
        for item in value:
            if isinstance(item, dict):
                row = ET.SubElement(list_elem, "row")
                for k, v in item.items():
                    if v is not None:
                        row.set(k, str(v))
            else:
                ET.SubElement(list_elem, "item").text = str(item)
        return
    if isinstance(value, dict):
        elem = ET.SubElement(parent, key)
        for k, v in value.items():
            _xml_append(elem, k, v)
        return
    elem = ET.SubElement(parent, key)
    if value is not None:
        elem.text = str(value)


def export_xml(run: RunResult, export_type: ExportType, path: Path, opts: XmlOptions) -> None:
    root = ET.Element("magboltz_export", schema_version="1.0", export_type=export_type.value)
    data = _filter_run_for_export(run, export_type, opts)
    _xml_append(root, "data", data)
    units = ET.SubElement(root, "units")
    for k, v in run.tables.units.items():
        if v:
            units.set(k, v)
    xml_bytes = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    _write_atomic(path, xml_bytes)


def export_to_file(
    run: RunResult,
    export_type: ExportType,
    export_format: ExportFormat,
    path: Path,
    csv_options: Optional[CsvOptions] = None,
    json_options: Optional[JsonOptions] = None,
    xml_options: Optional[XmlOptions] = None,
) -> None:
    if export_type == ExportType.CONVERGENCE_TABLE and not run.tables.convergence_table:
        raise ValueError("Selected dataset missing: convergence table")
    if export_type == ExportType.ENERGY_DISTRIBUTION and not run.tables.energy_distribution:
        raise ValueError("Selected dataset missing: energy distribution")
    if export_type == ExportType.COLLISION_FREQUENCIES and not run.frequencies_by_gas:
        raise ValueError("Selected dataset missing: collision frequencies")

    if export_format == ExportFormat.CSV:
        if export_type == ExportType.FULL_RUN_ARCHIVE:
            raise ValueError("Full run archive is not supported for CSV")
        export_csv(run, export_type, path, csv_options or CsvOptions())
    elif export_format == ExportFormat.JSON:
        export_json(run, export_type, path, json_options or JsonOptions())
    elif export_format == ExportFormat.XML:
        export_xml(run, export_type, path, xml_options or XmlOptions())
    else:
        raise ValueError("Unknown export format")


def default_filename(run: RunResult, export_type: ExportType, ext: str) -> str:
    mix = "_".join([f"{g.name}{int(g.fraction_percent or 0)}" for g in run.mixture]) or "run"
    field = run.conditions.electric_field_V_cm
    field_str = f"E{int(field)}" if field is not None else "E"
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"{mix}_{field_str}_{export_type.value}_{ts}.{ext}"
