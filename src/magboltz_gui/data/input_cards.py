from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class InputGas:

    gas_id: int
    # NGAS etc.: gas number identifiers (between 1 and 80) see gas list below for identifying numbers.

    gas_frac: float
    # FRAC etc.: percentage fraction of gas1 etc.;


@dataclass
class InputCards:

    @property
    def number_of_gases(self) -> int:
        # NGAS: number of gases in mixture
        return len(self.gases)

    number_of_real_collisions: int = 5
    # NMAX: number of real collisions (multiple of 10**7), use a value between 2 and 5 for inelastic gas to obtain 1 % accuracy, use a value above 10 for better than 0.5 % accuracy and a value of at least 10 for pure elastic gases like Argon

    enable_penning: bool = False
    # IPEN   = 0 Penning effects not included, 1 Penning effects included (see instructions above)

    enable_thermal: bool = True
    # ITHRM  = 0 gas motion assumed to be at 0 Kelvin (static gas)
    # ITHRM  = 1 gas motion taken to be at input temperature

    final_energy: float = 0.0
    # EFINAL: upper limit of the electron energy in electron Volts, if EFINAL = 0.0, program automatically calculates upper integration energy limit

    gas_temperature: float = 20.0
    # TEMP: temperature of gas in centigrade

    gas_pressure: float = 760.0
    # TORR: pressure of gas in Torr

    electric_field: float = 1000.0
    # EFIELD: electric field in Volt/cm

    magnetic_field: float = 0.0
    # BMAG: magnitude of the magnetic field in kilogauss

    angle: float = 0.0
    # BTHETA: angle between the electric and magnetic fields in degrees

    gases: List[InputGas] = field(default_factory=list)
