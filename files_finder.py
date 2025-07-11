import logging
from typing import Tuple
from chat_history_db import get_policy_with_cars
from models import Car, Policy
from dotenv import load_dotenv


load_dotenv()

logger = logging.getLogger(__name__)


def get_file_paths(policy: Policy, car: Car) -> Tuple[bool, str, str, str]:
    if not car.soa_file_path:
        message = (
            f"Problema inesperado al obtener el SOA de poliza {policy.policy_number} de {policy.company}"
            f"{f' matrícula {car.license_plate}. ' if car.license_plate else '. '}"
            "Consulte por asistencia técnica."
        )
        return False, message, None, None

    return True, "", car.soa_file_path, car.mercosur_file_path


def find_files(
    company: str,
    policy_number: str,
    licence_plate: str,
    user_wants_mercosur_file: bool,
) -> Tuple[bool, str, str, str]:
    if company.strip().upper() != "SURA":
        message = f"Poliza {policy_number}. Aún no es posible la descarga de certificados de {company} "
        return False, message, None, None

    policy = get_policy_with_cars(company, policy_number)
    if not policy:
        message = f"Poliza {policy_number} inexistente en {company}"
        return False, message, None, None

    if not policy.downloaded:
        reason = policy.obs
        message = (
            f"Poliza {policy_number} de {company}. No se pudo descargar los archivos"
            f"{f'. Motivo: {reason}' if reason else '.'}"
        )
        return False, message, None, None

    if policy.is_expired():
        message = f"Poliza {policy_number} de {company} está vencida"
        return False, message, None, None

    if policy.cancelled:
        reason = policy.obs
        message = (
            f"Poliza {policy_number} fue cancelada ó no figura en el sistema de {company}"
            f"{f'. Motivo: {reason}' if reason else '.'}"
        )
        return False, message, None, None

    if not policy.contains_cars:
        message = f"Poliza {policy_number} de {company} no corresponde a un automóvil"
        return False, message, None, None

    if policy.soa_only and user_wants_mercosur_file:
        message = f"Poliza {policy_number} de {company} no tiene Certificado Mercosur"
        return False, message, None, None

    if licence_plate:
        car = policy.get_car(licence_plate)
        if not car:
            message = f"Poliza {policy_number} de {company} no contiene un vehiculo con matricula {licence_plate}"
            return False, message, None, None

        return get_file_paths(policy, car)

    cars = policy.cars
    if len(cars) > 1:
        # TODO: add all license plates to message
        message = f"Poliza {policy_number} de {company} contiene más de un vehiculo. Especificar la matrícula"
        return False, message, None, None

    return get_file_paths(policy, cars[0])
