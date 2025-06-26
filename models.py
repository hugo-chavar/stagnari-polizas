from dataclasses import dataclass, field
from datetime import date, datetime
from typing import List, Optional


@dataclass
class Policy:
    company: str
    policy_number: str
    year: int
    expiration_date: date
    downloaded: bool = False
    contains_cars: bool = False
    soa_only: bool = False
    obs: Optional[str] = None
    timestamp: Optional[datetime] = None
    cars: List["Car"] = field(default_factory=list)


@dataclass
class Car:
    company: str
    policy_number: str
    license_plate: str
    brand: str
    model: str
    year: int
    soa_file_path: Optional[str] = None
    mercosur_file_path: Optional[str] = None
    timestamp: Optional[datetime] = None
