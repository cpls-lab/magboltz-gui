from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ExportType(str, Enum):
    SUMMARY = "summary"
    CONVERGENCE_TABLE = "convergence_table"
    ENERGY_DISTRIBUTION = "energy_distribution"
    COLLISION_FREQUENCIES = "collision_frequencies"
    FULL_RUN_ARCHIVE = "full_run"


class ExportFormat(str, Enum):
    CSV = "csv"
    JSON = "json"
    XML = "xml"


@dataclass
class CsvOptions:
    delimiter: str = ","
    include_units: bool = True
    include_metadata: bool = True
    flatten_mixture: bool = True


@dataclass
class JsonOptions:
    include_input_text: bool = True
    include_raw_stdout: bool = False
    include_parser_warnings: bool = True
    pretty_print: bool = True


@dataclass
class XmlOptions:
    include_input_text: bool = True
    include_raw_stdout: bool = False
    include_parser_warnings: bool = True
