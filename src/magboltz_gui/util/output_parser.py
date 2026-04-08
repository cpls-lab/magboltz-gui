"""Parse raw Magboltz stdout into the structured run-result model."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import List, Optional

from magboltz_gui.util.run_result import (
    RunResult,
    MixtureGas,
    RunMeta,
    RunInput,
    RunConditions,
    RunIntegration,
    RunFlags,
    RunCounts,
    RunTransport,
    DriftVelocity,
    RunDiffusion,
    DiffusionComponent,
    RunFrequenciesTotal,
    GasFrequencies,
    CollisionProcess,
    ConvergenceRow,
    EnergyRow,
    RunTables,
    RunRaw,
)


_FLOAT_RE = re.compile(r"[-+]?\d*\.\d+(?:[DEde][-+]?\d+)?|[-+]?\d+(?:[DEde][-+]?\d+)?")


def _parse_float(text: str) -> Optional[float]:
    try:
        return float(text.replace("D", "E").replace("d", "E"))
    except Exception:
        return None


def _parse_int(text: str) -> Optional[int]:
    try:
        return int(text)
    except Exception:
        return None


def _find_first_float(line: str) -> Optional[float]:
    m = _FLOAT_RE.search(line)
    if not m:
        return None
    return _parse_float(m.group(0))


def _floats_in_line(line: str) -> List[float]:
    out: List[float] = []
    for m in _FLOAT_RE.finditer(line):
        val = _parse_float(m.group(0))
        if val is not None:
            out.append(val)
    return out


def parse_magboltz_output(stdout_text: str, input_text: Optional[str] = None, input_path: Optional[str] = None) -> RunResult:
    """Extract transport quantities, tables, and metadata from one Magboltz run."""
    warnings: List[str] = []
    lines = stdout_text.splitlines()

    result = RunResult(
        meta=RunMeta(timestamp_utc=datetime.now(timezone.utc).isoformat()),
        input=RunInput(input_text=input_text, input_path=input_path),
        conditions=RunConditions(integration=RunIntegration(), flags=RunFlags()),
        counts=RunCounts(),
        transport=RunTransport(diffusion=RunDiffusion()),
        frequencies_total=RunFrequenciesTotal(),
        tables=RunTables(units={
            "vel": "um/ns",
            "pos": "dimensionless",
            "time": "ps",
            "energy": "eV",
            "difxx": "cm^2/s",
            "difyy": "cm^2/s",
            "difzz": "cm^2/s",
        }),
        raw=RunRaw(stdout_text=stdout_text, parser_warnings=warnings),
    )

    # Tool version
    for line in lines:
        if "PROGRAM MAGBOLTZ" in line and "VERSION" in line:
            result.meta.tool_version = " ".join(line.strip().split())
            break

    # Mixture section
    mix_start = None
    for i, line in enumerate(lines):
        if "GASES  USED" in line and "PERCENTAGE USED" in line:
            mix_start = i + 1
            break
    if mix_start is not None:
        for line in lines[mix_start:]:
            if not line.strip():
                break
            parts = line.strip().split()
            if not parts:
                continue
            try:
                fraction = _parse_float(parts[-1])
                name = parts[0]
                model_tag = " ".join(parts[1:-1]) or None
                result.mixture.append(MixtureGas(name=name, model_tag=model_tag, fraction_percent=fraction))
            except Exception:
                warnings.append(f"Failed to parse mixture line: {line}")

    # Conditions
    for line in lines:
        if "GAS TEMPERATURE" in line:
            result.conditions.gas_temperature_C = _find_first_float(line)
        elif "GAS PRESSURE" in line:
            result.conditions.gas_pressure_torr = _find_first_float(line)
        elif "INTEGRATION FROM" in line and "IN" in line and "STEPS" in line:
            vals = _floats_in_line(line)
            if len(vals) >= 3:
                result.conditions.integration.E_min_eV = vals[0]
                result.conditions.integration.E_max_eV = vals[1]
                result.conditions.integration.n_steps = int(vals[2])
        elif "PENNING EFFECTS" in line:
            result.conditions.flags.penning_included = "INCLUDED" in line and "NOT" not in line
        elif "ANISOTROPIC SCATTERING TYPE" in line:
            m = re.search(r"TYPE\s+(\d+)", line)
            if m:
                result.conditions.flags.anisotropic_scattering_type = _parse_int(m.group(1))
        elif "SHORT DECORRELATION LENGTH" in line:
            m = re.search(r"=\s*([0-9]+)", line)
            if m:
                result.conditions.flags.short_decorrelation_length_collisions = _parse_int(m.group(1))
        elif "THERMAL MOTION OF GAS" in line:
            result.conditions.flags.thermal_motion_included = "INCLUDED" in line
        elif "ELECTRIC FIELD" in line:
            result.conditions.electric_field_V_cm = _find_first_float(line)
        elif "MAGNETIC FIELD" in line:
            result.conditions.magnetic_field_kG = _find_first_float(line)
        elif "ANGLE BETWEEN ELECTRIC AND MAGNETIC FIELD" in line:
            result.conditions.angle_E_B_deg = _find_first_float(line)
        elif "CYCLOTRON FREQ." in line:
            result.conditions.cyclotron_freq_rad_ps = _find_first_float(line)
        elif "INITIAL ELECTRON ENERGY" in line:
            result.conditions.initial_electron_energy_eV = _find_first_float(line)
        elif "TOTAL NUMBER OF REAL COLLISIONS" in line:
            val = _find_first_float(line)
            if val is not None:
                result.counts.total_real_collisions = int(val)

    # Null collision frequency components
    for i, line in enumerate(lines):
        if "NULL COLLISION FREQUENCY FOR EACH GAS COMPONENT" in line:
            for j in range(i + 1, min(i + 6, len(lines))):
                nums = _floats_in_line(lines[j])
                if not nums:
                    break
                result.counts.null_collision_frequency_components.extend(nums)
            break

    # Convergence table
    for i, line in enumerate(lines):
        if line.strip().startswith("VEL") and "DIFZZ" in line:
            for j in range(i + 1, len(lines)):
                row_line = lines[j].strip()
                if not row_line:
                    continue
                if row_line.startswith("-"):
                    break
                vals = _floats_in_line(row_line)
                if len(vals) >= 8:
                    result.tables.convergence_table.append(
                        ConvergenceRow(
                            vel=vals[0],
                            pos=vals[1],
                            time=vals[2],
                            energy=vals[3],
                            count=vals[4],
                            difxx=vals[5],
                            difyy=vals[6],
                            difzz=vals[7],
                        )
                    )
            break

    # Calculated max collision time
    for line in lines:
        if "CALCULATED MAX. COLLISION TIME" in line:
            result.counts.calculated_max_collision_time_ps = _find_first_float(line)
        elif line.strip().startswith("NUMBER OF NULL COLLISIONS"):
            val = _find_first_float(line)
            if val is not None:
                result.counts.num_null_collisions = int(val)

    # Drift velocities
    for line in lines:
        if "Z DRIFT VELOCITY" in line:
            vals = _floats_in_line(line)
            if len(vals) >= 2:
                result.transport.vz_um_ns = DriftVelocity(v_um_ns=vals[0], err_pct=vals[1])
        elif "Y DRIFT VELOCITY" in line:
            vals = _floats_in_line(line)
            if len(vals) >= 2:
                result.transport.vy_um_ns = DriftVelocity(v_um_ns=vals[0], err_pct=vals[1])
        elif "X DRIFT VELOCITY" in line:
            vals = _floats_in_line(line)
            if len(vals) >= 2:
                result.transport.vx_um_ns = DriftVelocity(v_um_ns=vals[0], err_pct=vals[1])

    # Diffusion
    def _parse_diffusion(lines_list: List[str], label: str) -> Optional[int]:
        for i, line in enumerate(lines_list):
            if label in line:
                return i
        return None

    t_idx = _parse_diffusion(lines, "TRANSVERSE DIFFUSION")
    if t_idx is not None:
        vals = _floats_in_line(lines[t_idx])
        if len(vals) >= 2:
            result.transport.diffusion.transverse["DT_cm2_s"] = DiffusionComponent(vals[0], vals[1])
        if t_idx + 1 < len(lines):
            vals = _floats_in_line(lines[t_idx + 1])
            if len(vals) >= 2:
                result.transport.diffusion.transverse["DT_eV"] = DiffusionComponent(vals[0], vals[1])
        if t_idx + 2 < len(lines):
            vals = _floats_in_line(lines[t_idx + 2])
            if len(vals) >= 2:
                result.transport.diffusion.transverse["DT_um_cm05"] = DiffusionComponent(vals[0], vals[1])

    l_idx = _parse_diffusion(lines, "LONGITUDINAL DIFFUSION")
    if l_idx is not None:
        vals = _floats_in_line(lines[l_idx])
        if len(vals) >= 2:
            result.transport.diffusion.longitudinal["DL_cm2_s"] = DiffusionComponent(vals[0], vals[1])
        if l_idx + 1 < len(lines):
            vals = _floats_in_line(lines[l_idx + 1])
            if len(vals) >= 2:
                result.transport.diffusion.longitudinal["DL_eV"] = DiffusionComponent(vals[0], vals[1])
        if l_idx + 2 < len(lines):
            vals = _floats_in_line(lines[l_idx + 2])
            if len(vals) >= 2:
                result.transport.diffusion.longitudinal["DL_um_cm05"] = DiffusionComponent(vals[0], vals[1])

    # Rates and mean energy
    for line in lines:
        if "IONISATION RATE /CM" in line:
            vals = _floats_in_line(line)
            if len(vals) >= 2:
                result.transport.ionisation_rate_per_cm = vals[0]
                result.transport.ionisation_rate_err_pct = vals[1]
        elif "ATTACHMENT RATE /CM" in line:
            vals = _floats_in_line(line)
            if len(vals) >= 2:
                result.transport.attachment_rate_per_cm = vals[0]
                result.transport.attachment_rate_err_pct = vals[1]
        elif "MEAN ELECTRON ENERGY" in line:
            vals = _floats_in_line(line)
            if len(vals) >= 2:
                result.transport.mean_electron_energy_eV = vals[0]
                result.transport.mean_electron_energy_err_pct = vals[1]

    # Frequencies totals
    for line in lines:
        if line.strip().startswith("TOTAL COLL. FREQ."):
            result.frequencies_total.total_coll_freq_1e12_s = _find_first_float(line)
        elif line.strip().startswith("ELASTIC COLL. FREQ."):
            result.frequencies_total.elastic_coll_freq_1e12_s = _find_first_float(line)
        elif line.strip().startswith("INELASTIC COLL. FREQ."):
            result.frequencies_total.inelastic_coll_freq_1e12_s = _find_first_float(line)
        elif line.strip().startswith("IONISATION COLL. FREQ."):
            result.frequencies_total.ionisation_coll_freq_1e12_s = _find_first_float(line)
        elif line.strip().startswith("ATTACHMENT COLL. FREQ."):
            result.frequencies_total.attachment_coll_freq_1e12_s = _find_first_float(line)

    # Detailed collision frequencies (bounded section)
    in_detail = False
    gas_section: Optional[str] = None
    for i, line in enumerate(lines):
        if "DETAILED COLLISION FREQUENCIES" in line:
            in_detail = True
            continue
        if not in_detail:
            continue
        if line.strip().startswith("NORMALISED ENERGY DISTRIBUTION"):
            break
        if not line.strip():
            continue
        # Gas header is followed by a dashed line
        if i + 1 < len(lines) and lines[i + 1].strip().startswith("---"):
            gas_section = " ".join(line.strip().split())
            result.frequencies_by_gas.append(GasFrequencies(gas_name=gas_section))
            continue
        if line.strip().startswith("---"):
            continue
        if gas_section and "+-" in line:
            # Parse process line
            if "ELOSS=" in line:
                m = re.search(r"ELOSS=\s*([-+0-9\.DEde]+)", line)
                eloss = _parse_float(m.group(1)) if m else None
            else:
                eloss = None

            nums = _floats_in_line(line)
            if len(nums) >= 2:
                freq = nums[-2]
                err = nums[-1]
                label = line.strip()
                label = re.sub(r"[-+0-9\.DEde]+\s*\+\-\s*[-+0-9\.DEde]+\s*%?", "", label).strip()
                label = re.sub(r"\s+ELOSS=.*", "", label).strip()
                category = label.split()[0] if label else None
                result.frequencies_by_gas[-1].processes.append(
                    CollisionProcess(
                        label=label,
                        eloss_eV=eloss,
                        freq_1e12_s=freq,
                        err_pct=err,
                        category=category,
                    )
                )

    # Energy distribution
    for i, line in enumerate(lines):
        if "NORMALISED ENERGY DISTRIBUTION" in line:
            for j in range(i + 1, len(lines)):
                row = lines[j].strip()
                if not row:
                    break
                if row.startswith("Process finished"):
                    break
                if "E=" in row and "SPEC=" in row:
                    vals = _floats_in_line(row)
                    if len(vals) >= 2:
                        result.tables.energy_distribution.append(EnergyRow(E_eV=vals[0], spec=vals[1]))
            break

    return result
