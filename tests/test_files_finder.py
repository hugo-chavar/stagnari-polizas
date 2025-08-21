import os
import sys
import pytest
from unittest.mock import patch, MagicMock

# Add project root to sys.path for module resolution
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from files_finder import find_files


# Helper to patch get_policy_with_cars and Policy.get_car
def make_policy_mock(policy_data, cars_data):
    policy_mock = MagicMock()
    for k, v in policy_data.items():
        setattr(policy_mock, k, v)
    policy_mock.is_expired.return_value = (
        policy_data.get("expiration_date") < "2024-06-01"
        if "expiration_date" in policy_data
        else False
    )
    # Attach cars
    policy_mock.cars = []
    for car in cars_data:
        car_mock = MagicMock()
        for ck, cv in car.items():
            setattr(car_mock, ck, cv)
        policy_mock.cars.append(car_mock)

    # get_car method
    def get_car(plate):
        for car in policy_mock.cars:
            if car.license_plate == plate:
                return car
        return None

    policy_mock.get_car.side_effect = get_car
    return policy_mock


@pytest.mark.parametrize(
    "case",
    [
        # 1. Policy with no cars (contains_cars=0)
        {
            "policy": {
                "company": "SURA",
                "policy_number": "1257719",
                "year": 2026,
                "expiration_date": "2026-03-12",
                "downloaded": 1,
                "contains_cars": 0,
                "soa_only": 0,
                "cancelled": 0,
                "obs": "No es automovil",
            },
            "cars": [],
            "args": ("SURA", "1257719", "", False),
            "expected": (
                False,
                "Poliza 1257719 de SURA no corresponde a un automóvil",
                None,
                None,
            ),
        },
        # 2. Policy with car, valid, not expired, downloaded, not cancelled, not soa_only, has SOA
        {
            "policy": {
                "company": "SURA",
                "policy_number": "1937446",
                "year": 2025,
                "expiration_date": "2025-05-27",
                "downloaded": 1,
                "contains_cars": 1,
                "soa_only": 0,
                "cancelled": 0,
                "obs": "Vencida",
            },
            "cars": [
                {
                    "license_plate": "AAJ4721",
                    "soa_file_path": "soa_path.pdf",
                    "mercosur_file_path": None,
                }
            ],
            "args": ("SURA", "1937446", "AAJ4721", False),
            "expected": (True, "", "soa_path.pdf", None),
        },
        # 3. Policy with car, soa_only=1, user wants mercosur
        {
            "policy": {
                "company": "SURA",
                "policy_number": "1941009",
                "year": 2025,
                "expiration_date": "2025-06-12",
                "downloaded": 1,
                "contains_cars": 1,
                "soa_only": 1,
                "cancelled": 0,
                "obs": "Vencida",
            },
            "cars": [
                {
                    "license_plate": "OAA1684",
                    "soa_file_path": "soa_path.pdf",
                    "mercosur_file_path": None,
                }
            ],
            "args": ("SURA", "1941009", "OAA1684", True),
            "expected": (
                False,
                "Poliza 1941009 de SURA no tiene Certificado Mercosur",
                None,
                None,
            ),
        },
        # 4. Policy cancelled
        {
            "policy": {
                "company": "SURA",
                "policy_number": "1940520",
                "year": 2025,
                "expiration_date": "2025-06-12",
                "downloaded": 1,
                "contains_cars": 1,
                "soa_only": 0,
                "cancelled": 1,
                "obs": "Vencida",
            },
            "cars": [
                {
                    "license_plate": "SDE5091",
                    "soa_file_path": "soa_path.pdf",
                    "mercosur_file_path": None,
                }
            ],
            "args": ("SURA", "1940520", "SDE5091", False),
            "expected": (
                False,
                "Poliza 1940520 fue cancelada ó no figura en el sistema de SURA. Motivo: Vencida",
                None,
                None,
            ),
        },
        # 5. Policy not downloaded
        {
            "policy": {
                "company": "SURA",
                "policy_number": "1964297",
                "year": 2025,
                "expiration_date": "2025-11-01",
                "downloaded": 0,
                "contains_cars": 1,
                "soa_only": 0,
                "cancelled": 0,
                "obs": "OAD3513 - Excluido de la flota",
            },
            "cars": [
                {
                    "license_plate": "OAD3513",
                    "soa_file_path": None,
                    "mercosur_file_path": None,
                }
            ],
            "args": ("SURA", "1964297", "OAD3513", False),
            "expected": (
                False,
                "Poliza 1964297 de SURA. No se pudo descargar los archivos. Motivo: OAD3513 - Excluido de la flota",
                None,
                None,
            ),
        },
        # 6. Policy expired
        {
            "policy": {
                "company": "SURA",
                "policy_number": "1937446",
                "year": 2025,
                "expiration_date": "2020-01-01",
                "downloaded": 1,
                "contains_cars": 1,
                "soa_only": 0,
                "cancelled": 0,
                "obs": "Vencida",
            },
            "cars": [
                {
                    "license_plate": "AAJ4721",
                    "soa_file_path": "soa_path.pdf",
                    "mercosur_file_path": None,
                }
            ],
            "args": ("SURA", "1937446", "AAJ4721", False),
            "expected": (False, "Poliza 1937446 de SURA está vencida", None, None),
        },
        # 7. Policy with multiple cars, no license plate specified
        {
            "policy": {
                "company": "SURA",
                "policy_number": "multi",
                "year": 2025,
                "expiration_date": "2025-12-31",
                "downloaded": 1,
                "contains_cars": 1,
                "soa_only": 0,
                "cancelled": 0,
                "obs": "",
            },
            "cars": [
                {
                    "license_plate": "AAA1111",
                    "soa_file_path": "soa1.pdf",
                    "mercosur_file_path": None,
                },
                {
                    "license_plate": "BBB2222",
                    "soa_file_path": "soa2.pdf",
                    "mercosur_file_path": None,
                },
            ],
            "args": ("SURA", "multi", "", False),
            "expected": (
                False,
                "Poliza multi de SURA contiene más de un vehiculo. Especificar la matrícula",
                None,
                None,
            ),
        },
        # 8. Policy with car, but license plate not found
        {
            "policy": {
                "company": "SURA",
                "policy_number": "2101573",
                "year": 2025,
                "expiration_date": "2025-09-15",
                "downloaded": 1,
                "contains_cars": 1,
                "soa_only": 1,
                "cancelled": 0,
                "obs": "",
            },
            "cars": [
                {
                    "license_plate": "PAR119",
                    "soa_file_path": "soa_path.pdf",
                    "mercosur_file_path": "",
                }
            ],
            "args": ("SURA", "2101573", "NOTFOUND", False),
            "expected": (
                False,
                "Poliza 2101573 de SURA no contiene un vehiculo con matricula NOTFOUND",
                None,
                None,
            ),
        },
        # 9. Policy not found
        {
            "policy": None,
            "cars": [],
            "args": ("SURA", "notfound", "", False),
            "expected": (False, "Poliza notfound inexistente en SURA", None, None),
        },
        # 10. Policy with car, car has no SOA file path but is cancelled
        {
            "policy": {
                "company": "SURA",
                "policy_number": "2089303",
                "year": 2025,
                "expiration_date": "2025-08-07",
                "downloaded": 1,
                "contains_cars": 1,
                "soa_only": 1,
                "cancelled": 1,
                "obs": "",
            },
            "cars": [
                {
                    "license_plate": "AVI1745",
                    "soa_file_path": None,
                    "mercosur_file_path": None,
                }
            ],
            "args": ("SURA", "2089303", "AVI1745", False),
            "expected": (
                False,
                "Poliza 2089303 fue cancelada ó no figura en el sistema de SURA.",
                None,
                None,
            ),
        },
        # 11. Policy with car, not cancelled, but car has no SOA file path
        {
            "policy": {
                "company": "SURA",
                "policy_number": "2089304",
                "year": 2025,
                "expiration_date": "2025-08-07",
                "downloaded": 1,
                "contains_cars": 1,
                "soa_only": 1,
                "cancelled": 0,
                "obs": "",
            },
            "cars": [
                {
                    "license_plate": "TST1745",
                    "soa_file_path": None,
                    "mercosur_file_path": None,
                }
            ],
            "args": ("SURA", "2089304", "TST1745", False),
            "expected": (
                False,
                "Problema inesperado al obtener el SOA de poliza 2089304 de SURA matrícula TST1745. Consulte por asistencia técnica.",
                None,
                None,
            ),
        },
        # 12. Policy with car, not cancelled, but car has no SOA file path. License plate is None
        {
            "policy": {
                "company": "SURA",
                "policy_number": "2089304",
                "year": 2025,
                "expiration_date": "2025-08-07",
                "downloaded": 1,
                "contains_cars": 1,
                "soa_only": 1,
                "cancelled": 0,
                "obs": "",
            },
            "cars": [
                {
                    "license_plate": None,
                    "soa_file_path": None,
                    "mercosur_file_path": None,
                }
            ],
            "args": ("SURA", "2089304", None, False),
            "expected": (
                False,
                "Problema inesperado al obtener el SOA de poliza 2089304 de SURA. Consulte por asistencia técnica.",
                None,
                None,
            ),
        },
        # 13. Policy with car, valid, not expired, downloaded, not cancelled, not soa_only, has SOA
        {
            "policy": {
                "company": "SURA",
                "policy_number": "1937446",
                "year": 2025,
                "expiration_date": "2025-05-27",
                "downloaded": 1,
                "contains_cars": 1,
                "soa_only": 0,
                "cancelled": 0,
                "obs": "Vencida",
            },
            "cars": [
                {
                    "license_plate": "AAJ4721",
                    "soa_file_path": "soa_path.pdf",
                    "mercosur_file_path": "mer_path.pdf",
                }
            ],
            "args": ("SURA", "1937446", "AAJ4721", True),
            "expected": (True, "", "soa_path.pdf", "mer_path.pdf"),
        },
    ],
)
def test_find_files(case):
    # Patch get_policy_with_cars to return our mock
    patch_path = "files_finder.get_policy_with_cars"
    if case["policy"] is None:
        policy_mock = None
    else:
        policy_mock = make_policy_mock(case["policy"], case["cars"])
    with patch(patch_path, return_value=policy_mock):
        # Patch Policy.is_expired to use the expiration_date string
        if policy_mock:
            policy_mock.is_expired.return_value = (
                case["policy"]["expiration_date"] < "2024-06-01"
            )
        result = find_files(*case["args"])
        assert result == case["expected"]
