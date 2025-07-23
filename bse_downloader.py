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

view_name = 'viewns_Z7_8A401HS0K0L5C06K03V0LHEQF2_:'
tab_result = view_name + 'formPolizas:tablaResultado:'
tab_imprimir_poliza = view_name + 'frmPdf:tabPnlImprimirPoliza:'

btn_search_lctor = Locator(LocatorType.ID, tab_result + "btnBuscar")
arrow_down_lctor = Locator(LocatorType.ID, tab_result + '0:j_id_6r')
btn_print_lctor = Locator(LocatorType.ID, tab_result + '0:j_id_8p')
btn_view_report_lctor = Locator(LocatorType.ID, tab_imprimir_poliza + 'btnValidar')
btn_dwnld_policy_lctor = Locator(LocatorType.ID, tab_imprimir_poliza + 'j_id_2v')

other_docs_checkbox_locators = [
    Locator(LocatorType.ID, f"{tab_imprimir_poliza}j_id_2a:{i}:chkListaPartes")
    for i in range(4)
]

other_docs_checkbox_locators.append(
    Locator(LocatorType.ID, tab_imprimir_poliza + 'checkPoliza')
)

cert_checkbox_locators = [
    Locator(LocatorType.ID, f"{tab_imprimir_poliza}j_id_2o:{i}:chkCert")
    for i in range(2)
]

policy_row_lctor = Locator(LocatorType.CSS, "tr.ui-widget-content")
policy_row_status_lctor = Locator(LocatorType.XPATH, ".//td[contains(@class, 'text-right')][.//div[contains(@class, 'filtroResponsivo')]]")

class BseClickDownloadStarter(ClickDownloadStarter):
    def __init__(self, driver, locator):
        super().__init__(driver, locator)

    def verify_download_in_progress(self, filename: str):
        try:
            locator = Locator(LocatorType.TAG, "pre")
            ele = self.driver.wait_for_element(locator, timeout=5)
            error_message = ele.text.strip()
            logger.error(f"Download BSE error: {error_message}")
            raise CompanyPolicyException(
                company="BSE",
                reason=f"Archivo {filename} no disponible para descargar",
            )
        except DriverException as e:
            pass


class BseDownloader(BaseDownloader):
    """Downloader implementation for BSE insurance company."""

    
    def name(self) -> str:
        return "BSE"

    def wait_login_page(self):
        """Wait for BSE login page elements to be ready."""
        try:
            self.driver.wait_for_element(Locator(LocatorType.ID, "userID"))
            self.driver.wait_for_element(Locator(LocatorType.ID, "password"))
        except Exception as e:
            raise CompanyPolicyException(
                company=self.name(), reason=f"Login page not loaded properly: {str(e)}"
            )

    def wait_login_confirmation(self):
        """Wait for confirmation that login was successful."""
        try:
            self.driver.wait_for_element(
                Locator(LocatorType.CLASS, "user-profile")
            )
            logger.info("Login en BSE exitoso")
        except Exception:
            msg = self.driver.wait_for_element(
                Locator(LocatorType.CLASS, "wpsFieldSuccessText")
            )
            error_message = f"Error Login BSE: {msg.text}"
            logger.info(error_message)
            raise CompanyPolicyException(company=self.name(), reason=error_message)

    def do_login(self):
        """Perform BSE login with credentials."""
        try:
            # Enter username
            self.driver.send_keys(Locator(LocatorType.ID, "userID"), self.user)

            # Enter password
            self.driver.send_keys(
                Locator(LocatorType.ID, "password"), self.password
            )

            # Click login button
            self.driver.click(Locator(LocatorType.ID, "login.button.login"))
        except Exception as e:
            raise CompanyPolicyException(
                company=self.name(), reason=f"Login operation failed: {str(e)}"
            )

    def do_logout(self):
        """Perform BSE logout."""
        # BSE uses default logout, this method shouln't be called directly.
        logger.warning("BSE does not require a custom logout implementation.")
        raise NotImplementedError()

    def wait_clickable(self, locator):
        """Wait for the buscar button to appear."""
        try:
            btn = self.driver.wait_for_clickable(
                locator=locator
            )
            logger.debug(f"The clickable '{str(locator)}' has appeared")
            return btn
        except Exception as e:
            raise CompanyPolicyException(
                company=self.name(), reason=f"Buscar clickable '{str(locator)}' not appear: {str(e)}"
            )

    def find_policy_input(self):
        """Find and return the policy number input field."""
        loc = Locator(LocatorType.ID, tab_result + "filNroPoliza")
        try:
            self.wait_clickable(btn_search_lctor)
            return self.driver.wait_for_element(loc)
        except Exception as e:
            raise CompanyPolicyException(
                company=self.name(), reason=f"Policy input not found: {str(e)}"
            )

    def search_policy(self):
        """Execute the policy search operation."""
        try:
            logger.info("Searching for policy in BSE system")

            # Click the search button
            self.driver.click(btn_search_lctor)
            logger.debug("Search button clicked, waiting for results")

            self.wait_clickable(btn_search_lctor)

        except Exception as e:
            raise CompanyPolicyException(
                company=self.name(), reason=f"Policy search failed: {str(e)}"
            )

    def get_endorsements_count(self) -> int:
        """Get the number of rows in the fleet table."""
        return 1

    def get_vehicles_data(self) -> list[dict]:
        try:
            second_column = self.driver.find_element(
                Locator(LocatorType.CSS, "div.column.second-col")
            )
            items = self.driver.find_elements(
                Locator(LocatorType.CSS, "div > div"),
                context=second_column
            )
            data = {}
            for item in items:
                try:
                    label = self.driver.find_element(
                        Locator(LocatorType.CSS, "label"),
                        context=item
                    ).text.strip()
                    value = self.driver.find_element(
                        Locator(LocatorType.CSS, "div.desc"),
                        context=item
                    ).text.strip()
                    data[label] = value
                except:
                    continue

            
            return [{
                "Marca": data.get('Marca', None),
                "Modelo": data.get('Modelo', None),
                "Matrícula": data.get('Matrícula', ""),
            }]
        except Exception as e:
            logger.error(f"Error extracting vehicles data: {str(e)}")

    def reconcile_vehicles(
        self, page_data: list[dict], policy_data: list[dict]
    ) -> list[dict]:
        reconciled_vehicles = []

        if len(page_data) == 1 and len(policy_data) == 1:
            page_vehicle = page_data[0]
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
                }
            )

            reconciled_vehicles.append(reconciled_vehicle)

        return reconciled_vehicles

    def download_policy_files(self, policy: Dict[str, Any], validation_data: Dict[str, Any]):
        """Handle the BSE policy file download."""
        try:
            
            logger.debug(f"Validation data: {str(validation_data)}")
            page_vehicles = self.get_vehicles_data()
            policy_vehicles = policy["vehicles"]
            logger.info(f"Page vehicles: {page_vehicles}")
            logger.info(f"Policy vehicles: {policy_vehicles}")

            reconciled_vehicles = self.reconcile_vehicles(
                page_vehicles, policy_vehicles
            )
            logger.info(f"Reconciled vehicles: {reconciled_vehicles}")
            self.is_downloaded(policy)
            if policy["downloaded"]:
                logger.info("ALREADY DOWNLOADED")
                return
            for vehicle in reconciled_vehicles:
                if vehicle["status"] != "Pending":
                    continue

                vehicle_plate = vehicle["license_plate"]
                
                for locator in other_docs_checkbox_locators:
                    self.driver.set_checkbox_state(locator, False)
                
                logger.info(f"Processing vehicle {vehicle_plate}")

                try:
                    self.execute_download_starters(policy, vehicle, vehicle_plate)

                except Exception as e:
                    logger.error(f"Error processing vehicle {vehicle_plate}: {str(e)}")
                    vehicle["status"] = "Error"
                    vehicle["reason"] = e.reason if hasattr(e, "reason") else str(e)
            policy["vehicles"] = reconciled_vehicles
        except Exception as e:
            logger.error(f"Error downloading policy files: {str(e)}")
            raise CompanyPolicyException(
                company=self.name(), reason=f"Policy download failed: {str(e)}"
            )

    def validate_policy(self, policy, endorsement_line):
        validation_data = {
            "valid": False
        }
        policy_status = self.get_policy_status()
        if policy_status in ["ANULADA", "VENCIDA"]:
            policy["obs"] = policy_status
            logger.info(f"Policy status: {policy_status}")

        self.expand_policy_details()
        
        policy_type = self.get_policy_type()
        if policy_type in ["ANULADA", "VENCIDA"]:
            policy["obs"] = "No es automóvil"
            logger.info(f"Policy type: {policy_type}")
            
        validation_data["valid"] = True
        
    def get_download_starter(self):
        lctor = Locator(
                    LocatorType.ID,
                    tab_imprimir_poliza + 'j_id_2v',
                )

        return BseClickDownloadStarter(
                            driver=self.driver,
                            locator=lctor,
                        )

    def get_soa_download_starter(self):
        checkbox_locator = cert_checkbox_locators[0]
        self.driver.set_checkbox_state(checkbox_locator, True)
        return self.get_download_starter()
    
    def get_mercosur_download_starter(self):
        checkbox_locator = cert_checkbox_locators[0]
        self.driver.set_checkbox_state(checkbox_locator, False)
        checkbox_locator = cert_checkbox_locators[1]
        self.driver.set_checkbox_state(checkbox_locator, True)
        return self.get_download_starter()

    def expand_policy_details(self):

        item_tab_element = self.driver.wait_for_clickable(arrow_down_lctor)

        item_tab_element.click()

    def get_policy_status(self) -> str:
        """
        Returns:
            str: The status of the current policy

        Raises:
            ElementNotFoundException: If row or cell not found
            DriverException: For other WebDriver errors
        """
        try:
            #row = driver.find_element_by_css_selector("tr.ui-widget-content")
            current_lctor = policy_row_lctor
            row_el = self.driver.find_element(current_lctor)

            #estado = row.find_element_by_xpath(".//td[contains(@class, 'text-right')][.//div[contains(@class, 'filtroResponsivo')]]").text
            current_lctor = policy_row_status_lctor
            status_el = self.driver.find_element(current_lctor, context=row_el)
            status = status_el.text.strip()
            logger.debug(f"Estado: {status}")
            return status

        except Exception as e:
            msg = f"Failed to get policy status, locator {str(current_lctor)} : {str(e)}"
            logger.error(msg)
            raise CompanyPolicyException(
                company=self.name(), reason=msg
            )

    def get_policy_type(self) -> str:
        # TODO: implement
        return ""