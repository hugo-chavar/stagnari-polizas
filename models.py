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
    cancelled: bool = False
    obs: Optional[str] = None
    timestamp: Optional[datetime] = None
    cars: List["Car"] = field(default_factory=list)

    def get_car(self, license_plate: str) -> Optional["Car"]:
        """
        Returns the Car object from self.cars with the given license_plate.
        Returns None if not found.
        """
        for car in self.cars:
            if car.license_plate == license_plate:
                return car
        return None

    def is_expired(self) -> bool:
        """
        Returns True if the policy's expiration_date is before today.
        """
        return self.expiration_date < datetime.now().date()

    def to_dict(self) -> dict:
        """Convert instance to dictionary with proper serialization."""
        result = {}
        for field_name, field_value in self.__dict__.items():
            if isinstance(field_value, (datetime, date)):
                result[field_name] = field_value.isoformat()
            elif hasattr(field_value, 'to_dict'):
                result[field_name] = field_value.to_dict()
            elif isinstance(field_value, list):
                result[field_name] = [
                    item.to_dict() if hasattr(item, 'to_dict') else item
                    for item in field_value
                ]
            else:
                result[field_name] = field_value
        return result

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
    obs: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert instance to dictionary with proper serialization."""
        result = {}
        for field_name, field_value in self.__dict__.items():
            if isinstance(field_value, (datetime, date)):
                result[field_name] = field_value.isoformat()
            else:
                result[field_name] = field_value
        return result