import logging
from typing import Dict, Any
from policy_driver import Locator, LocatorType, DriverException, TimeoutError
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
select_cert_lctor = Locator(LocatorType.ID, tab_imprimir_poliza + "certificado") 
btn_view_report_lctor = Locator(LocatorType.ID, tab_imprimir_poliza + 'btnValidar')
btn_dwnld_policy_lctor = Locator(LocatorType.ID, tab_imprimir_poliza + 'j_id_2v')

other_docs_checkbox_locators = [
    Locator(LocatorType.ID, f"{tab_imprimir_poliza}j_id_2a:{i}:chkListaPartes")
    for i in range(4)
]

policy_checkbox_lctor = Locator(LocatorType.ID, tab_imprimir_poliza + 'checkPoliza')

other_docs_checkbox_locators.append(policy_checkbox_lctor)

cert_checkbox_locators = [
    Locator(LocatorType.ID, f"{tab_imprimir_poliza}j_id_2o:{i}:chkCert")
    for i in range(2)
]

mercosur_cert_checkbox_locator = cert_checkbox_locators[0]
soa_cert_checkbox_locator = cert_checkbox_locators[1]

policy_row_lctor = Locator(LocatorType.CSS, "tr.ui-widget-content")
policy_row_status_lctor = Locator(LocatorType.XPATH, ".//td[contains(@class, 'text-right')][.//div[contains(@class, 'filtroResponsivo')]]")

download_starter_lctor = Locator(
            LocatorType.ID,
            tab_imprimir_poliza + 'j_id_2v',
        )

class BseClickDownloadStarter(ClickDownloadStarter):
    def __init__(self, driver, locator):
        super().__init__(driver, locator)

    def verify_download_in_progress(self, filename: str):
        # TODO: implement this
        pass
        # try:
        #     locator = Locator(LocatorType.TAG, "pre")
        #     ele = self.driver.wait_for_element(locator, timeout=5)
        #     error_message = ele.text.strip()
        #     logger.error(f"Download BSE error: {error_message}")
        #     raise CompanyPolicyException(
        #         company="BSE",
        #         reason=f"Archivo {filename} no disponible para descargar",
        #     )
        # except DriverException as e:
        #     pass


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
            self.driver.click_wait_for_stale(
                staleable_lctor=policy_row_lctor,
                btn_lctor=btn_search_lctor
            )

            logger.debug("Page has been refreshed, waiting for results")

        except Exception as e:
            raise CompanyPolicyException(
                company=self.name(), reason=f"Policy search failed: {str(e)}"
            )

    def get_endorsements_count(self) -> int:
        """Get the number of rows in the fleet table."""
        return 1

    def get_vehicles_data(self) -> list[dict]:
        try:
            expanded_content_el = self.driver.find_element(
                Locator(LocatorType.CSS, "tr.ui-expanded-row-content")
            )
            second_col_el = self.driver.find_element(
                Locator(LocatorType.CSS, "div.column.second-col"),
                context=expanded_content_el
            )
            brand_el = self.driver.find_elements(
                Locator(LocatorType.XPATH, ".//div[./label[contains(text(), 'Marca')]]/div[@class='desc']"),
                context=second_col_el
            )
            model_el = self.driver.find_elements(
                Locator(LocatorType.XPATH, ".//div[./label[contains(text(), 'Modelo')]]/div[@class='desc']"),
                context=second_col_el
            )
            license_plate_el = self.driver.find_elements(
                Locator(LocatorType.XPATH, ".//div[./label[contains(text(), 'Matrícula')]]/div[@class='desc']"),
                context=second_col_el
            )
            
            brand = brand_el[0].text.strip() if len(brand_el) > 0 else None
            model = model_el[0].text.strip() if len(model_el) > 0 else None
            license_plate = license_plate_el[0].text.strip() if len(license_plate_el) > 0 else ""
    
            return [{
                "Marca": brand,
                "Modelo": model,
                "Matrícula": license_plate,
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

    def prepare_next_vehicle_search(self):
        pass

    def go_to_vehicle_download_page(self, vehicle, validation_data):
        logger.info(f"Go to download page of vehicle {vehicle["license_plate"]}")
        self.driver.click(btn_print_lctor)
        logger.debug("Print button clicked, waiting for refresh")
        old_el = self.driver.find_element(btn_view_report_lctor)

        self.driver.set_select_value(select_cert_lctor, value='1')
        logger.debug(f"Select changed, waiting for {btn_view_report_lctor} to become stale")
        self.driver.wait_for_staleness(old_el, desc=str(btn_view_report_lctor))
        logger.debug("Page has became stale, waiting for refresh")

        # self.driver.wait_for_element(btn_view_report_lctor)
        
        self.driver.click(btn_view_report_lctor)
        self.driver.wait_for_element(policy_checkbox_lctor)
        logger.debug("Page has been refreshed, checkbox are visible")
        
        for index, locator in enumerate(other_docs_checkbox_locators):
            if index < len(other_docs_checkbox_locators) - 1:
                next_lctor = other_docs_checkbox_locators[index + 1]
            else:
                next_lctor = mercosur_cert_checkbox_locator
            old_next = self.driver.wait_for_element(next_lctor)
            if self.driver.set_checkbox_state(locator, False):
                logger.debug(f"Waiting for {next_lctor} to become stale")
                self.driver.wait_for_staleness(old_next, desc=str(next_lctor))
            self.driver.wait_for_element(next_lctor)
                

    def validate_policy(self, policy, endorsement_line):
        validation_data = {
            "valid": False
        }
        policy_status = self.get_policy_status()
        if policy_status in ["ANULADA", "VENCIDA"]:
            policy["obs"] = policy_status
            logger.info(f"Policy status: {policy_status}")

        logger.debug("Expanding policy details")
        self.expand_policy_details()
        logger.debug("Policy details expanded")
        
        policy_type = self.get_policy_type()
        logger.debug(f"Policy type: {policy_type}")
        # TODO: Fix this
        if policy_type in ["ANULADA", "VENCIDA"]:
            policy["obs"] = "No es automóvil"
            
        validation_data["valid"] = True
        logger.debug("Validation finished")
        return validation_data
        
    def get_download_starter(self):

        return BseClickDownloadStarter(
                            driver=self.driver,
                            locator=download_starter_lctor,
                        )

    def get_soa_download_starter(self):
        return self.wait_for_download_starter(
            on_checkbox_lctor=soa_cert_checkbox_locator,
            off_checkbox_lctor=mercosur_cert_checkbox_locator
        )

    def wait_for_download_starter(self, on_checkbox_lctor, off_checkbox_lctor):
        logger.info(f"Waiting for {off_checkbox_lctor}")
        old_next = self.driver.wait_for_element(off_checkbox_lctor)
        logger.info(f"Old {off_checkbox_lctor} {old_next}")
        self.driver.set_checkbox_state(off_checkbox_lctor, False)
        logger.info(f"Waiting for {download_starter_lctor}")
        old_next = self.driver.wait_for_element(download_starter_lctor)
        if self.driver.set_checkbox_state(on_checkbox_lctor, True):
            logger.debug(f"Checkbox changed, waiting for {download_starter_lctor} to become stale")
            try:
                self.driver.wait_for_staleness(old_next, desc=str(download_starter_lctor))
                logger.debug(f"Waiting for {download_starter_lctor}")
                self.driver.wait_for_element(download_starter_lctor)
            except TimeoutError:
                pass
        
        return self.get_download_starter()
    
    def get_mercosur_download_starter(self):
        # off_checkbox_lctor = soa_cert_checkbox_locator
        # on_checkbox_lctor = mercosur_cert_checkbox_locator
        # logger.info(f"Waiting for {off_checkbox_lctor}")
        # old_next = self.driver.wait_for_element(off_checkbox_lctor)
        # logger.info(f"Old {off_checkbox_lctor} {old_next}")
        # self.driver.set_checkbox_state(off_checkbox_lctor, False)
        # if self.driver.set_checkbox_state(checkbox_locator, False):
        #     logger.info(f"Old2 {off_checkbox_lctor} {old_next}")
        #     try:
        #         self.driver.wait_for_staleness(old_next, desc=str(off_checkbox_lctor))
        #     except TimeoutError:
        #         logger.info(f"Timeout staleness check {soa_cert_checkbox_locator} {old_next}")
        #         pass
        return self.wait_for_download_starter(
            on_checkbox_lctor=mercosur_cert_checkbox_locator,
            off_checkbox_lctor=soa_cert_checkbox_locator
        )

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