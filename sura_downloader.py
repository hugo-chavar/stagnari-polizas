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

    def get_vehicles_data(self) -> int:
        table_id = "GrdItems"
        try:
            self.driver.wait_for_element(Locator(LocatorType.ID, table_id))
            vehicle_data = self.driver.extract_table_data(
                table_id, ["Matrícula", "Estado", "Nro."]
            )
            return vehicle_data
        except Exception as e:
            logger.error(f"Error extracting table {table_id} data: {str(e)}")

    def download_policy_files(self, policy: Dict[str, Any], endorsement_line: int):
        """Handle the SURA policy file download."""
        try:
            e_id, ramo_cod = self.select_endorsement_line(endorsement_line)
            if ramo_cod != "11":
                policy["obs"] = "No es automovil"
                logger.info(f"It is not an automobile, skipping policy")
                return

            self.go_to_endorsement_items()

            vehicles_count = self.get_vehicles_count()
            vehicles_data = self.get_vehicles_data()
            logger.info(f"Page vehicles data: {vehicles_data}")
            logger.info(f"Policy vehicles data: {policy["vehicles"]}")
            logger.info(f"Processing {vehicles_count} vehicles for endorsement {e_id}")
            # Redirect to each vehicle detail page
            single_vehicle = (
                vehicles_count == len(policy["vehicles"]) and vehicles_count == 1
            )

            empty_license_plate = 0
            for vehicle in vehicles_data:
                vehicle_id = vehicle["Nro."]
                if vehicle["Matrícula"] == "NOFIGURA":
                    vehicle["Matrícula"] = str(empty_license_plate)
                    empty_license_plate += 1
                vehicle_plate = vehicle["Matrícula"]
                logger.info(f"Processing vehicle {vehicle_plate} with ID {vehicle_id}")
                if vehicle["Estado"] == "Excluido":
                    logger.warning(
                        f"Vehicle {vehicle_plate} is not active, skipping download"
                    )
                    vehicle["status"] = "Skipped"
                    vehicle["reason"] = "Excluido de la flota"
                    continue
                if single_vehicle:
                    requested_vehicle = policy["vehicles"][0]
                    lic_plate = requested_vehicle["license_plate"].strip()
                    if vehicle_plate.strip() != lic_plate:
                        if len(lic_plate) <= 2:
                            requested_vehicle["license_plate"] = vehicle_plate.strip()
                        elif len(vehicle_plate.strip()) <= 2:
                            vehicle["Matrícula"] = lic_plate
                else:
                    requested_vehicle = next(
                        (
                            v
                            for v in policy["vehicles"]
                            if v["license_plate"] == vehicle_plate
                        ),
                        None,
                    )
                if not requested_vehicle:
                    logger.warning(
                        f"Vehicle {vehicle_plate} is not in the spreadsheet, skipping download"
                    )
                    vehicle["status"] = "Skipped"
                    vehicle["reason"] = "No en la planilla"
                    policy["vehicles"].append(vehicle)
                    continue
                if requested_vehicle.get("files_are_valid"):
                    logger.warning(
                        f"Vehicle {vehicle_plate} was previously downloaded, skipping download"
                    )
                    vehicle["status"] = "Skipped"
                    vehicle["reason"] = "Descarga ya realizada"
                    continue
                # Execute the redirect script for each vehicle
                try:
                    script = f"redirectPage('DetalleVehiculo.aspx', {e_id}, {vehicle_id}, false)"
                    self.driver.execute_script(script)
                    starter = SuraClickDownloadStarter(
                        driver=self.driver,
                        locator=Locator(
                            LocatorType.XPATH, "//a[contains(text(),'certificado SOA')]"
                        ),
                    )
                    filename = "soa.pdf"  # Certificado de SOA
                    folder = self.get_folder_path(policy, vehicle_plate)
                    vehicle["folder"] = folder
                    vehicle["soa"] = self.download_file_from_starter(
                        starter, FilenameRenameStrategy(folder, filename)
                    )

                    vehicle["mercosur"] = ""
                    if not policy.get("soa_only", False):
                        starter = SuraClickDownloadStarter(
                            driver=self.driver,
                            locator=Locator(
                                LocatorType.XPATH,
                                "//a[contains(text(),'tarjeta verde')]",
                            ),
                        )
                        filename = "mercosur.pdf"  # Certificado de Mercosur
                        try:
                            vehicle["mercosur"] = self.download_file_from_starter(
                                starter, FilenameRenameStrategy(folder, filename)
                            )
                        except TimeoutError:
                            pass

                    self.driver.back()
                    vehicle["status"] = "Ok"
                    try:
                        self.driver.wait_for_clickable(
                            Locator(LocatorType.CSS, "input#cmdExportarFlota")
                        )
                    except:
                        pass
                    requested_vehicle.update(vehicle)

                except Exception as e:
                    logger.error(f"Error processing vehicle {vehicle_plate}: {str(e)}")
                    vehicle["status"] = "Error"
                    vehicle["reason"] = e.reason if hasattr(e, "reason") else str(e)

        except Exception as e:
            logger.error(f"Error downloading policy files: {str(e)}")
            raise CompanyPolicyException(
                company=self.name(), reason=f"Policy download failed: {str(e)}"
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
