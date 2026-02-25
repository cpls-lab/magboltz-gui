from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, cast


@dataclass
class RunMeta:
    tool_name: str = "magboltz"
    tool_version: Optional[str] = None
    timestamp_utc: Optional[str] = None
    gui_version: Optional[str] = None
    schema_version: str = "1.0"


@dataclass
class RunInput:
    input_text: Optional[str] = None
    input_path: Optional[str] = None


@dataclass
class RunIntegration:
    E_min_eV: Optional[float] = None
    E_max_eV: Optional[float] = None
    n_steps: Optional[int] = None


@dataclass
class RunFlags:
    penning_included: Optional[bool] = None
    thermal_motion_included: Optional[bool] = None
    anisotropic_scattering_type: Optional[int] = None
    short_decorrelation_length_collisions: Optional[int] = None


@dataclass
class RunConditions:
    gas_temperature_C: Optional[float] = None
    gas_pressure_torr: Optional[float] = None
    electric_field_V_cm: Optional[float] = None
    magnetic_field_kG: Optional[float] = None
    angle_E_B_deg: Optional[float] = None
    cyclotron_freq_rad_ps: Optional[float] = None
    initial_electron_energy_eV: Optional[float] = None
    integration: RunIntegration = field(default_factory=RunIntegration)
    flags: RunFlags = field(default_factory=RunFlags)


@dataclass
class MixtureGas:
    name: str
    model_tag: Optional[str]
    fraction_percent: Optional[float]


@dataclass
class RunCounts:
    total_real_collisions: Optional[int] = None
    num_null_collisions: Optional[int] = None
    calculated_max_collision_time_ps: Optional[float] = None
    null_collision_frequency_components: List[float] = field(default_factory=list)


@dataclass
class DriftVelocity:
    v_um_ns: Optional[float] = None
    err_pct: Optional[float] = None


@dataclass
class DiffusionComponent:
    value: Optional[float] = None
    err_pct: Optional[float] = None


@dataclass
class RunDiffusion:
    transverse: Dict[str, DiffusionComponent] = field(default_factory=dict)
    longitudinal: Dict[str, DiffusionComponent] = field(default_factory=dict)


@dataclass
class RunTransport:
    vx_um_ns: Optional[DriftVelocity] = None
    vy_um_ns: Optional[DriftVelocity] = None
    vz_um_ns: Optional[DriftVelocity] = None
    diffusion: RunDiffusion = field(default_factory=RunDiffusion)
    ionisation_rate_per_cm: Optional[float] = None
    ionisation_rate_err_pct: Optional[float] = None
    attachment_rate_per_cm: Optional[float] = None
    attachment_rate_err_pct: Optional[float] = None
    mean_electron_energy_eV: Optional[float] = None
    mean_electron_energy_err_pct: Optional[float] = None


@dataclass
class RunFrequenciesTotal:
    total_coll_freq_1e12_s: Optional[float] = None
    elastic_coll_freq_1e12_s: Optional[float] = None
    inelastic_coll_freq_1e12_s: Optional[float] = None
    ionisation_coll_freq_1e12_s: Optional[float] = None
    attachment_coll_freq_1e12_s: Optional[float] = None


@dataclass
class CollisionProcess:
    label: str
    eloss_eV: Optional[float]
    freq_1e12_s: Optional[float]
    err_pct: Optional[float]
    category: Optional[str] = None


@dataclass
class GasFrequencies:
    gas_name: str
    processes: List[CollisionProcess] = field(default_factory=list)


@dataclass
class ConvergenceRow:
    vel: float
    pos: float
    time: float
    energy: float
    count: float
    difxx: float
    difyy: float
    difzz: float


@dataclass
class EnergyRow:
    E_eV: float
    spec: float
    bin_width_eV: Optional[float] = None


@dataclass
class RunTables:
    convergence_table: List[ConvergenceRow] = field(default_factory=list)
    energy_distribution: List[EnergyRow] = field(default_factory=list)
    units: Dict[str, str] = field(default_factory=dict)


@dataclass
class RunRaw:
    stdout_text: Optional[str] = None
    parser_warnings: List[str] = field(default_factory=list)


@dataclass
class RunResult:
    meta: RunMeta = field(default_factory=RunMeta)
    input: RunInput = field(default_factory=RunInput)
    conditions: RunConditions = field(default_factory=RunConditions)
    mixture: List[MixtureGas] = field(default_factory=list)
    counts: RunCounts = field(default_factory=RunCounts)
    transport: RunTransport = field(default_factory=RunTransport)
    frequencies_total: RunFrequenciesTotal = field(default_factory=RunFrequenciesTotal)
    frequencies_by_gas: List[GasFrequencies] = field(default_factory=list)
    tables: RunTables = field(default_factory=RunTables)
    raw: RunRaw = field(default_factory=RunRaw)

    def to_dict(self) -> Dict[str, Any]:
        def _serialize(obj: Any) -> Any:
            if hasattr(obj, "__dict__"):
                return {k: _serialize(v) for k, v in obj.__dict__.items()}
            if isinstance(obj, list):
                return [_serialize(v) for v in obj]
            return obj

        return cast(Dict[str, Any], _serialize(self))
