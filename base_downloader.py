import logging
import os
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from dotenv import load_dotenv
from typing import List, Dict, Any
from pathlib import Path
from pdf_utils import is_valid_pdf
from policy_driver import PolicyDriver

load_dotenv()

logger = logging.getLogger(__name__)


class CompanyPolicyException(Exception):
    def __init__(self, company, reason):
        super().__init__(f"Error en compañia {company} debido a: {reason}.")
        self.company = company
        self.reason = reason


class FilenameRenameStrategy:
    def __init__(self, folder, filename) -> None:
        logger.debug("Using direct filename rename strategy")
        self.folder = folder
        self.filename = filename

    def __str__(self) -> str:
        return self.filename

    def new_filename(self, old_filename):
        return self.filename


class AddSuffixRenameStrategy:
    def __init__(self, suffix) -> None:
        logger.debug("Using add suffix rename strategy")
        self.suffix = suffix

    def __str__(self) -> str:
        return f"archivo con sufijo {self.suffix}"

    def new_filename(self, old_filename):
        new_suffix = f"-{self.suffix}-f1"
        file_name, file_extension = os.path.splitext(old_filename)
        self.filename = file_name + new_suffix + file_extension
        return self.filename


class DownloadStarter(ABC):
    @abstractmethod
    def start_download(self):
        """Initiate the file download"""
        pass

    @abstractmethod
    def verify_download_in_progress(self, _):
        """Verify that the download is in progress"""
        raise NotImplementedError("Subclasses must implement this method")


class ClickDownloadStarter(DownloadStarter):
    def __init__(self, driver, locator):
        self.driver = driver
        self.locator = locator

    def start_download(self):
        self.driver.click(self.locator)


class ScriptDownloadStarter(DownloadStarter):
    def __init__(self, driver, script):
        self.driver = driver
        self.script = script

    def start_download(self):
        self.driver.execute_script(self.script)


class BaseDownloader(ABC):
    """Abstract base class for insurance policy downloaders."""

    def __init__(self, driver: PolicyDriver):
        self.driver = driver
        self.logged_in = False

        # Load company-specific configuration from environment
        self.login_url = os.getenv(f"{self.name()}_LOGIN_URL")
        self.logout_url = os.getenv(f"{self.name()}_LOGOUT_URL")
        self.search_url = os.getenv(f"{self.name()}_SEARCH_URL")
        self.user = os.getenv(f"{self.name()}_USER")
        self.password = os.getenv(f"{self.name()}_PASSWORD")
        self.login_timeout = int(os.getenv(f"{self.name()}_LOGIN_TIMEOUT"))
        self.download_folder = os.getenv(f"DOWNLOAD_FOLDER")

    @abstractmethod
    def name(self) -> str:
        """Return the name of the company (e.g., "BSE", "SANCOR")."""
        raise NotImplementedError()

    @abstractmethod
    def wait_login_page(self):
        """Wait for the login page to load and be ready for interaction."""
        raise NotImplementedError()

    @abstractmethod
    def wait_login_confirmation(self):
        """Wait for confirmation that login was successful."""
        raise NotImplementedError()

    @abstractmethod
    def do_login(self):
        """Perform the login operation with company-specific credentials."""
        raise NotImplementedError()

    @abstractmethod
    def do_logout(self):
        """Perform the logout operation with company-specific steps."""
        raise NotImplementedError()

    @abstractmethod
    def get_endorsements_count(self) -> int:
        """Get the number of rows in the fleet table."""
        raise NotImplementedError()

    @abstractmethod
    def find_policy_input(self):
        """Find and return the policy number input field."""
        raise NotImplementedError()

    @abstractmethod
    def search_policy(self):
        """Execute the policy search operation."""
        raise NotImplementedError()

    @abstractmethod
    def download_policy_files(self, policy: Dict[str, Any], endorsment_line: int):
        """Handle the actual file download process."""
        raise NotImplementedError()

    @abstractmethod
    def get_soa_download_starter(self, policy=None):
        """Handler to start the soa file download process."""
        raise NotImplementedError()

    @abstractmethod
    def get_mercosur_download_starter(self, policy=None):
        """Handler to start the mercosur file download process."""
        raise NotImplementedError()

    @abstractmethod
    def validate_policy(self, policy, endorsement_line):
        """Check on the website if the policy is valid"""
        raise NotImplementedError()

    @abstractmethod
    def prepare_next_vehicle_search(self):
        raise NotImplementedError()

    @abstractmethod
    def reconcile_vehicles(
        self, page_data: list[dict], policy_data: list[dict]
    ) -> list[dict]:
        raise NotImplementedError()

    def login(self):
        """Template method for the login process."""
        self.driver.init_driver()
        logger.info(f"Logging in to {self.name()} at {self.login_url}")
        self.driver.navigate(self.login_url)
        self.wait_login_page()
        self.do_login()

        try:
            self.wait_login_confirmation()
            self.logged_in = True
            self.login_time = datetime.now().replace(second=0, microsecond=0)
            logger.debug("Login successful")
        except Exception as e:
            error_message = f"Error logging into {self.name()}: {str(e)}"
            logger.error(error_message)
            raise CompanyPolicyException(company=self.name(), reason=error_message)

    def login_session_expired(self):
        current_time = datetime.now().replace(second=0, microsecond=0)

        time_diff = current_time - self.login_time
        return time_diff >= timedelta(minutes=self.login_timeout)

    def logout(self):
        """Template method for the logout process."""
        if self.logged_in:
            logger.debug(f"Logging out from {self.name()}")
            if self.logout_url:
                self.driver.navigate(self.logout_url)
            else:
                self.do_logout()
            self.logged_in = False
            logger.info("Logout successful")

    def download_policies(self, policies: List[Dict[str, str]]):
        """Download multiple policies using the provided policy data."""
        for policy in policies:
            if self.login_session_expired():
                logger.info(f"Login time has expired")
                return
            try:
                if not policy.get("number"):
                    logger.error(f"Policy number is required for policy: {policy}")
                    continue
                if not policy.get("year"):
                    logger.error(f"Policy year is required for policy: {policy}")
                    continue
                # Check if year is greater than or equal to the current year
                if int(policy["year"]) < int(time.strftime("%Y")):
                    logger.error(
                        f"Policy year {policy['year']} is in the past for policy: {policy}"
                    )
                    policy["obs"] = "Vencida"
                    continue
                if policy["expired"]:
                    logger.debug(f"The expiration date has passed for policy: {policy}")
                    policy["obs"] = "Vencida"
                    continue
                if not policy["contains_cars"]:
                    logger.debug(f"Policy: {policy} is not a car policy")
                    policy["obs"] = "No es automovil"
                    continue

                if not policy["downloaded"]:
                    logger.info(
                        f"Starts download process for policy: {policy['number']}"
                    )
                    if self.download_policy(policy):
                        logger.info(
                            f"Policy {policy['number']} downloaded SUCCESSFULLY"
                        )
                    else:
                        if policy["cancelled"]:
                            logger.warning(f"Policy {policy['number']} was CANCELLED")
                        else:
                            logger.warning(f"Policy {policy['number']} NOT downloaded")
                            logger.warning(str(policy))
                else:
                    logger.info(f"Policy {policy['number']} already downloaded")
            except CompanyPolicyException as e:
                logger.error(f"Failed to download policy {str(policy)}: {e.reason}")
            except Exception as e:
                logger.error(
                    f"Unexpected error downloading policy {policy['number']}: {str(e)}"
                )

    def download_policy(self, policy: Dict[str, str]) -> bool:
        """Template method for the complete policy download process."""

        try:
            self._search_for_policy(policy)
            count = self.get_endorsements_count()
            logger.debug(f"Policy has {count} endorsements")
            spreadsheet_vehicle_count = len(policy["vehicles"])
            logger.debug(f"Policy has {spreadsheet_vehicle_count} vehicles")

            for i in range(0, count):
                logger.debug(f"Checking row {i} in the main grid")

                logger.debug(
                    f"Downloading files, policy: {policy['number']} endorsement: {i}"
                )
                validation_data = self.validate_policy(policy, i)
                if validation_data["valid"]:

                    self.download_policy_files(policy, validation_data)

                    download_success = all(
                        v.get("status", "") == "Ok" for v in policy["vehicles"]
                    )

                    if download_success:
                        break

                    cars_excluded = all(
                        v.get("status", "") == "Skipped"
                        and v.get("reason", "") in ["Excluido de la flota", "No en la web"]
                        for v in policy["vehicles"]
                    )

                    if cars_excluded:
                        break

                if i < count - 1:
                    self._search_for_policy(policy)

            for v in policy["vehicles"]:
                v.pop("files_are_valid")
                if v.get("status") is None:
                    v["status"] = "Skipped"
                    v["reason"] = "No en la web"

            policy["cancelled"] = all(
                v.get("status", "") == "Skipped"
                and v.get("reason", "") == "No en la web"
                for v in policy["vehicles"]
            )
            download_success = all(
                v.get("status", "") == "Ok" for v in policy["vehicles"]
            )
            policy["downloaded"] = download_success or policy["cancelled"]

            return download_success
        except Exception as e:
            error_message = f"Error downloading policy {policy['number']} from {self.name()}: {str(e)}"
            logger.error(error_message)
            policy["obs"] = error_message
            return False

    def _search_for_policy(self, policy: Dict[str, str]) -> None:
        """Helper method to search for a policy."""
        self.driver.navigate(self.search_url)
        policy_input = self.find_policy_input()
        logger.debug(f"Found policy input field: {policy_input}")
        policy_input.clear()
        logger.debug(f"Entering policy number: {policy['number']}")
        policy_input.send_keys(policy["number"])
        self.search_policy()

    def is_downloaded(self, policy):
        exp_date = datetime.strptime(policy["expiration_date"], "%d/%m/%Y").date()
        policy_expired = exp_date < datetime.now().date()
        policy_cancelled = policy.get("cancelled", False)
        soa_only = policy.get("soa_only", False)
        policy["expired"] = policy_expired
        policy["downloaded"] = (
            policy_cancelled or policy_expired or not policy["contains_cars"]
        )
        if policy["downloaded"]:
            return

        for vehicle in policy["vehicles"]:
            license_plate = vehicle.get("license_plate")
            rel_path = self.get_relative_path(policy, license_plate)
            folder = self.get_folder_path(rel_path)
            soa_file_is_valid, _ = is_valid_pdf(folder, "soa.pdf")
            if soa_file_is_valid:
                vehicle["folder"] = folder
                vehicle["soa"] = f"{rel_path}/soa.pdf"
            if soa_only:
                vehicle["files_are_valid"] = soa_file_is_valid
            else:
                mercosur_file_is_valid, _ = is_valid_pdf(folder, "mercosur.pdf")
                if mercosur_file_is_valid:
                    vehicle["mercosur"] = f"{rel_path}/mercosur.pdf"
                vehicle["files_are_valid"] = (
                    soa_file_is_valid and mercosur_file_is_valid
                )
            if vehicle["files_are_valid"]:
                vehicle["status"] = "Ok"
        policy["downloaded"] = all(
            vehicle.get("files_are_valid", False) for vehicle in policy["vehicles"]
        )

    def mark_downloaded_policies(self, policies):
        """Check if all policies have been downloaded successfully."""
        for policy in policies:
            policy["obs"] = ""
            self.is_downloaded(policy)

    def check_if_all_downloaded(self, policies) -> bool:
        """Check if all policies in the list have been downloaded successfully."""
        self.mark_downloaded_policies(policies)
        all_downloaded = all(policy.get("downloaded", False) for policy in policies)
        if not all_downloaded:
            logger.warning("Not all policies were downloaded successfully.")
        else:
            logger.info("All policies were downloaded successfully.")
        return all_downloaded

    def get_relative_path(self, policy, vehicle_plate):
        return (
            f"{self.name()}/{policy["number"]}/{policy["year"]}"
            f"{f'/{vehicle_plate}' if vehicle_plate else ''}"
        )

    def get_folder_path(self, rel_path):
        return os.path.join(
            self.download_folder,
            rel_path,
        )

    def clean_tmp_folder(self):
        tmp_path = self.driver.folder
        try:
            for path in Path(tmp_path).glob("**/*"):
                if path.is_file() and not os.path.basename(path).endswith(".ini"):
                    path.unlink()
        except FileNotFoundError:
            err_msg = f"Carpeta no encontrada: {tmp_path}"
            logger.error(err_msg)
            raise FileNotFoundError(err_msg)

    def _wait_download_and_rename_file(self, rename_strategy, timeout=300):
        logger.debug("Inicia _wait_download_and_rename_file")
        end_time = time.time() + timeout
        tmp_path = self.driver.folder
        download_started = False
        while time.time() < end_time:
            try:
                file_list = [
                    f for f in os.listdir(tmp_path) if not f.lower().endswith(".ini")
                ]
            except FileNotFoundError:
                error_message = f"Carpeta no encontrada: {tmp_path}"
                logger.error(error_message)
                raise FileNotFoundError(error_message)

            if file_list:
                logger.debug(
                    f"Verificando archivo descargado para renombrar a {str(rename_strategy)}"
                )
                try:
                    # se necesita el try .. except porque el archivo puede ser renombrado un instante antes y termina en error
                    newest_file = max(
                        file_list,
                        key=lambda x: os.path.getctime(os.path.join(tmp_path, x)),
                    )
                    logger.debug(f"Se encontro archivo temporal: {newest_file}")
                except:
                    newest_file = None

                if (
                    not newest_file
                    or "crdownload" in newest_file
                    or newest_file.endswith(".tmp")
                ):
                    if not download_started:
                        end_time += 10
                        download_started = True
                    logger.debug(f"Archivo aun descargandose, {newest_file} ...")
                else:

                    new_file_path = rename_strategy.folder
                    if not os.path.exists(new_file_path):
                        os.makedirs(new_file_path)
                    downloaded_file_path = os.path.join(tmp_path, newest_file)
                    new_file_name = rename_strategy.new_filename(newest_file)
                    new_file_path = os.path.join(new_file_path, new_file_name)

                    # Si el archivo existe lo elimino
                    if os.path.isfile(new_file_path):
                        os.remove(new_file_path)
                        logger.info(f"Se elimino archivo {new_file_name} existente")

                    # esperamos a que Chrome termine el proceso de descarga
                    time.sleep(2)
                    logger.debug(f"Old file path: {downloaded_file_path}")
                    logger.debug(f"New file path: {new_file_path}")
                    os.rename(downloaded_file_path, new_file_path)
                    logger.debug(f"Se renombro archivo {newest_file} a {new_file_name}")
                    return new_file_path, True
            else:
                logger.debug("La descarga no inicio aun, se espera")
            time.sleep(3)
        # Sale por timeout
        return None, False

    def download_file_from_starter(
        self, starter, rename_strategy, timeout=120, max_attempts=2
    ):
        attempts = 1
        downloaded_ok = False
        MAX_ATTEMPTS = max_attempts

        while attempts < MAX_ATTEMPTS and not downloaded_ok:
            self.clean_tmp_folder()
            starter.start_download()
            starter.verify_download_in_progress(str(rename_strategy))

            logger.debug(f"Renombrando archivo {self.name()} a {str(rename_strategy)}")

            try:
                full_path, downloaded_ok = self._wait_download_and_rename_file(
                    rename_strategy, timeout
                )

                if downloaded_ok:
                    logger.info(f"Renombrado correcto. FullPath: {full_path}")

                else:
                    attempts += 1
                    logger.info(f"Fallo la descarga. Se reintenta por {attempts} vez ")
            except Exception as e:
                error_msg = e.msg if hasattr(e, "msg") else str(e)
                error_message = f"ERROR Renombrando archivo {self.name()} a {str(rename_strategy)}. {type(e).__name__}: {error_msg}"
                logger.error(error_message)
                raise Exception(error_message)

        if attempts >= MAX_ATTEMPTS and not downloaded_ok:
            error_message = f"Maxima cantidad de intentos superada para descargar: {str(rename_strategy)}. Empresa: {self.name()}"
            raise CompanyPolicyException(self.name(), error_message)
        return full_path

    def process_policies(self, policies):
        try:
            is_all_downloaded = self.check_if_all_downloaded(policies)
            if not is_all_downloaded:
                logger.info(
                    "Not all policies are downloaded, proceeding with login and download."
                )

                self.login()
                self.download_policies(policies)
                logger.info(f"Downloaded files: {policies}")
        except Exception as e:
            logger.exception("Detailed error:")
            logger.error(f"Error during policy download: {str(e)}")
        finally:
            self.logout()
            logger.info("Logout completed")

    def execute_download_starters(self, policy, vehicle, vehicle_plate):
        rel_path = self.get_relative_path(policy, vehicle_plate)
        folder = self.get_folder_path(rel_path)
        if not vehicle.get("soa"):
            starter = self.get_soa_download_starter(policy)
            filename = "soa.pdf"  # Certificado de SOA
            vehicle["folder"] = folder
            self.download_file_from_starter(
                            starter, FilenameRenameStrategy(folder, filename)
                        )
            vehicle["soa"] = f"{rel_path}/{filename}"

        if not vehicle.get("mercosur"):
            vehicle["mercosur"] = ""
            if not policy.get("soa_only", False):
                starter = self.get_mercosur_download_starter(policy)
                filename = "mercosur.pdf"  # Certificado de Mercosur
                try:
                    self.download_file_from_starter(
                                    starter, FilenameRenameStrategy(folder, filename)
                                )
                    vehicle["mercosur"] = f"{rel_path}/{filename}"
                except TimeoutError:
                    pass

        vehicle["status"] = "Ok"

    def download_policy_files(self, policy: Dict[str, Any], validation_data: Dict[str, Any]):
        """Handle the policy file download."""
        try:
            logger.debug(f"Validation data: {str(validation_data)}")
            page_vehicles = self.get_vehicles_data()
            policy_vehicles = policy["vehicles"]
            logger.debug(f"Page vehicles: {page_vehicles}")
            logger.debug(f"Policy vehicles: {policy_vehicles}")

            reconciled_vehicles = self.reconcile_vehicles(
                page_vehicles, policy_vehicles
            )
            logger.debug(f"Reconciled vehicles: {reconciled_vehicles}")
            self.is_downloaded(policy)
            if policy["downloaded"]:
                logger.debug("ALREADY DOWNLOADED")
                return
            for index, vehicle in enumerate(reconciled_vehicles):
                if vehicle["status"] != "Pending":
                    continue

                vehicle_plate = vehicle["license_plate"]

                try:
                    self.go_to_vehicle_download_page(vehicle, validation_data)
                    self.execute_download_starters(policy, vehicle, vehicle_plate)
                    if index < len(reconciled_vehicles) - 1:
                        self.prepare_next_vehicle_search()
                except Exception as e:
                    logger.error(f"Error processing vehicle {vehicle_plate}: ({type(e).__name__}) {str(e)}")
                    vehicle["status"] = "Error"
                    vehicle["reason"] = e.reason if hasattr(e, "reason") else str(e)
            policy["vehicles"] = reconciled_vehicles
        except Exception as e:
            logger.error(f"Error downloading policy files: {str(e)}")
            raise CompanyPolicyException(
                company=self.name(), reason=f"Policy download failed: {str(e)}"
            )

