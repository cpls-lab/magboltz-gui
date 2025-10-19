from csv import DictReader
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class GasItem:

    id: int
    name: str
    formula: Optional[str]
    year: Optional[int]
    note: Optional[str]
    rating: Optional[int]

    @property
    def pretty_name(self) -> str:
        return f"{self.name} ({self.formula})" if self.formula else self.name

    @property
    def short_name(self) -> str:
        return self.formula if self.formula else self.name


@dataclass
class GasDatabase:
    content: List[GasItem] = field(default_factory=list)

    def load(self, filepath: Path) -> None:
        with open(filepath, newline="", encoding="utf-8") as csvfile:
            reader = DictReader(csvfile)
            for row in reader:
                gas = GasItem(
                    id=int(row["id"]),
                    name=row["name"].strip(),
                    formula=row["formula"].strip() if row["formula"] else None,
                    year=int(row["year"]) if row["year"] else None,
                    note=row["note"].strip() if row["note"] else None,
                    rating=int(row.get("rating", "")) if row["rating"] else None,
                )
                self.content.append(gas)

    def get(self, id: int) -> GasItem:

        for item in self.content:
            if item.id == id:
                return item

        raise KeyError(f"Gas with id {id} not found")
