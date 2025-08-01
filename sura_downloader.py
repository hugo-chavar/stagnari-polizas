import logging
from typing import Dict, Any
from policy_driver import Locator, LocatorType, DriverException
from base_downloader import (
    BaseDownloader,
    ClickDownloadStarter,
    CompanyPolicyException,
    FilenameRenameStrategy,
)

logger = logging.getLogger(__name__)


class SuraClickDownloadStarter(ClickDownloadStarter):
    def __init__(self, driver, locator):
        super().__init__(driver, locator)

    def verify_download_in_progress(self, filename: str):
        try:
            locator = Locator(LocatorType.TAG, "pre")
            ele = self.driver.wait_for_element(locator, timeout=5)
            error_message = ele.text.strip()
            logger.error(f"Download SURA error: {error_message}")
            raise CompanyPolicyException(
                company="SURA",
                reason=f"Archivo {filename} no disponible para descargar",
            )
        except DriverException as e:
            pass


class SuraDownloader(BaseDownloader):
    """Downloader implementation for SURA insurance company."""

    def name(self) -> str:
        return "SURA"

    def wait_login_page(self):
        """Wait for SURA login page elements to be ready."""
        try:
            self.driver.wait_for_element(Locator(LocatorType.ID, "Login1_UserName"))
            self.driver.wait_for_element(Locator(LocatorType.ID, "Login1_Password"))
        except Exception as e:
            raise CompanyPolicyException(
                company=self.name(), reason=f"Login page not loaded properly: {str(e)}"
            )

    def wait_login_confirmation(self):
        """Wait for confirmation that login was successful."""
        self.driver.wait_for_element(
            Locator(LocatorType.CSS, "p#nombreUsuario.datosUsuario")
        )

    def do_login(self):
        """Perform SURA login with credentials."""
        try:
            # Enter username
            self.driver.send_keys(Locator(LocatorType.ID, "Login1_UserName"), self.user)

            # Enter password
            self.driver.send_keys(
                Locator(LocatorType.ID, "Login1_Password"), self.password
            )

            # Click login button
            self.driver.click(Locator(LocatorType.ID, "Login1_LoginButton"))
        except Exception as e:
            raise CompanyPolicyException(
                company=self.name(), reason=f"Login operation failed: {str(e)}"
            )

    def do_logout(self):
        """Perform SURA logout."""
        # SURA uses default logout, this method shouln't be called directly.
        logger.warning("SURA does not require a custom logout implementation.")
        raise NotImplementedError()

    def wait_overlay_invisibility(self):
        """Wait for any blocking overlays to disappear."""
        try:
            self.driver.wait_for_invisibility(
                locator=Locator(LocatorType.CSS, "div.blockUI.blockOverlay"),
                poll_frequency=0.1,
            )
            logger.debug("Overlay is not blocking the search operation")
        except Exception as e:
            raise CompanyPolicyException(
                company=self.name(), reason=f"Overlay did not disappear: {str(e)}"
            )

    def find_policy_input(self):
        """Find and return the policy number input field."""
        loc = Locator(LocatorType.ID, "TxtNroPoliza")
        try:
            self.wait_overlay_invisibility()
            return self.driver.wait_for_element(loc)
        except Exception as e:
            raise CompanyPolicyException(
                company=self.name(), reason=f"Policy input not found: {str(e)}"
            )

    def search_policy(self):
        """Execute the policy search operation."""
        try:
            logger.info("Searching for policy in SURA system")
            # self.wait_overlay_invisibility()

            # Click the search button
            self.driver.click(Locator(LocatorType.ID, "btnConsultar"))
            logger.debug("Search button clicked, waiting for results")

            self.wait_overlay_invisibility()

        except Exception as e:
            raise CompanyPolicyException(
                company=self.name(), reason=f"Policy search failed: {str(e)}"
            )

    def get_endorsements_count(self) -> int:
        """Get the number of rows in the fleet table."""
        specific_locator = Locator(LocatorType.CSS, "table#grilla > tbody > tr.jqgrow")
        return self.driver.get_table_row_count(specific_locator)

    def get_vehicles_count(self) -> int:
        """Get the number of rows in the endorsement."""
        specific_locator = Locator(LocatorType.CSS, "table#GrdItems > tbody > tr")
        self.driver.wait_for_element(specific_locator)
        vehicles_count = self.driver.get_table_row_count(specific_locator)
        logger.info(f"Number of vehicles in endorsement: {vehicles_count}")

        if vehicles_count == 0:
            raise CompanyPolicyException(
                company=self.name(), reason="No vehicles found in endorsement"
            )
        return vehicles_count

    def get_vehicles_data(self) -> list[dict]:
        table_id = "GrdItems"
        try:
            self.driver.wait_for_element(Locator(LocatorType.ID, table_id))
            vehicle_data = self.driver.extract_table_data(
                table_id, ["Matrícula", "Estado", "Nro."]
            )
            return vehicle_data
        except Exception as e:
            logger.error(f"Error extracting table {table_id} data: {str(e)}")

    def reconcile_vehicles(
        self, page_data: list[dict], policy_data: list[dict]
    ) -> list[dict]:
        reconciled_vehicles = []

        current_page_data = [
            page_vehicle
            for page_vehicle in page_data
            if page_vehicle.get("Estado") != "Excluido"
        ]

        if len(current_page_data) == 1 and len(policy_data) == 1:
            page_vehicle = current_page_data[0]
            policy_vehicle = policy_data[0]

            page_has_empty_plate = page_vehicle.get("Matrícula", "").upper() in (
                "NOFIGURA",
                "0KM",
                "",
            )
            if page_has_empty_plate:
                page_vehicle["Matrícula"] = policy_vehicle.get("license_plate", "")
            elif not policy_vehicle.get("license_plate") and not page_has_empty_plate:
                policy_vehicle["license_plate"] = page_vehicle["Matrícula"]

        for policy_vehicle in policy_data:
            license_plate = policy_vehicle.get("license_plate", "").strip()

            page_vehicle = next(
                (
                    v
                    for v in page_data
                    if v.get("Matrícula", "").strip() == license_plate
                ),
                None,
            )

            reconciled_vehicle = policy_vehicle.copy()
            reconciled_vehicle["license_plate"] = license_plate

            if not page_vehicle:
                reconciled_vehicle.update(
                    {"status": "Skipped", "reason": "No en la web"}
                )
                reconciled_vehicles.append(reconciled_vehicle)
                continue

            if page_vehicle.get("Estado") == "Excluido":
                reconciled_vehicle.update(
                    {"status": "Skipped", "reason": "Excluido de la flota"}
                )
                reconciled_vehicles.append(reconciled_vehicle)
                continue

            if policy_vehicle.get("files_are_valid"):
                logger.warning(
                    f"Vehicle {license_plate} was previously downloaded, skipping download"
                )
                reconciled_vehicle.update(
                    {"status": "Skipped", "reason": "Descarga ya realizada"}
                )
                reconciled_vehicles.append(reconciled_vehicle)
                continue

            reconciled_vehicle.update(
                {
                    "status": "Pending",
                    "page_id": page_vehicle.get("Nro."),
                }
            )

            reconciled_vehicles.append(reconciled_vehicle)

        return reconciled_vehicles

    def prepare_next_vehicle_search(self):
        try:
            self.driver.back()
            self.driver.wait_for_clickable(
                                Locator(LocatorType.CSS, "input#cmdExportarFlota")
                            )
        except:
            pass

    def go_to_vehicle_download_page(self, vehicle, validation_data):
                # Execute the redirect script for the vehicle
                vehicle_id = vehicle["page_id"]
                logger.info(f"Go to download page of vehicle {vehicle["license_plate"]} with ID {vehicle_id}")
                script = f"redirectPage('DetalleVehiculo.aspx', {validation_data["id"]}, {vehicle_id}, false)"
                logger.debug(f"Executing script: {script}")
                self.driver.execute_script(script)
                logger.debug("Script finished")

    def validate_policy(self, policy, endorsement_line):
        e_id, ramo_cod = self.select_endorsement_line(endorsement_line)
        if ramo_cod != "11":
            policy["obs"] = "No es automovil"
            logger.info(f"It is not an automobile, skipping policy")
            validation_data = {
                    "valid": False
                }
        else:
            validation_data = {
                    "valid": True,
                    "id": e_id
                }

        self.go_to_endorsement_items()

        vehicles_count = self.get_vehicles_count()
        logger.debug(f"Processing {vehicles_count} vehicles for endorsement {e_id}")
        return validation_data

    def get_mercosur_download_starter(self):
        return SuraClickDownloadStarter(
                            driver=self.driver,
                            locator=Locator(
                                LocatorType.XPATH,
                                "//a[contains(text(),'tarjeta verde')]",
                            ),
                        )

    def get_soa_download_starter(self):
        return SuraClickDownloadStarter(
                        driver=self.driver,
                        locator=Locator(
                            LocatorType.XPATH, 
                            "//a[contains(text(),'certificado SOA')]"
                        ),
                    )
        
    def go_to_endorsement_items(self):
        items_tab_locator = Locator(LocatorType.CSS, f"a[href='#Items']")

        item_tab_element = self.driver.wait_for_clickable(items_tab_locator)

        item_tab_element.click()

    def select_endorsement_line(self, endorsement_line: str) -> str:
        """
        Selects an endorsement line and returns its ID_PV value.

        Args:
            endorsement_line: The row ID to select (e.g., "0")

        Returns:
            str: The ID_PV value from the selected row

        Raises:
            ElementNotFoundException: If row or cell not found
            DriverException: For other WebDriver errors
        """
        # Locate and wait for the row to be clickable
        row_locator = Locator(
            LocatorType.CSS, f"table#grilla tr[id='{endorsement_line}']"
        )
        row_element = self.driver.wait_for_clickable(row_locator)

        # Find the ID_PV cell within the row
        id_pv_locator = Locator(LocatorType.CSS, "td[aria-describedby='grilla_id_pv']")

        try:
            ramo_ltor = Locator(
                LocatorType.CSS, "td[aria-describedby='grilla_cod_ramo']"
            )
            ramo_cell = self.driver.find_element(ramo_ltor, context=row_element)
            ramo_value = self.driver.driver.execute_script(
                "return arguments[0].textContent", ramo_cell
            ).strip()

            if ramo_value != "11":
                return None, ramo_value

            # Get the cell text value
            id_pv_cell = self.driver.find_element(id_pv_locator, context=row_element)
            id_pv_value = id_pv_cell.text.strip()
            id_pv_value = self.driver.driver.execute_script(
                "return arguments[0].textContent", id_pv_cell
            ).strip()

            # Click the row
            row_element.click()
            logger.debug(f"Endorsement {endorsement_line} clicked")
            self.wait_overlay_invisibility()

            logger.info(
                f"Selected endorsement line {endorsement_line}, ID_PV: {id_pv_value}"
            )
            return id_pv_value, ramo_value

        except Exception as e:
            logger.error(
                f"Failed to select endorsement line {endorsement_line}: {str(e)}"
            )
            raise CompanyPolicyException(
                company=self.name(), reason=f"Endorsement selection failed: {str(e)}"
            )
