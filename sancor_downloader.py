import logging, time, re
from datetime import datetime, timedelta
from policy_driver import Locator, LocatorType, DriverException, PolicyDriver
from base_downloader import (
    BaseDownloader,
    ClickDownloadStarter,
    CompanyPolicyException,
)

logger = logging.getLogger(__name__)


class SancorClickDownloadStarter(ClickDownloadStarter):
    def __init__(self, driver: PolicyDriver, locator):
        super().__init__(driver, locator)

    def verify_download_in_progress(self, filename: str):
        pass


class SancorDownloader(BaseDownloader):
    """Downloader implementation for SANCOR insurance company."""

    def name(self) -> str:
        return "SANCOR"

    def get_login_username_locator(self):
        return Locator(LocatorType.CSS, '[name="username"]')
    
    def get_login_pass_locator(self):
        return Locator(LocatorType.CSS, '[name="password"]')
    
    def get_login_btn_locator(self):
        return Locator(LocatorType.CLASS, 'auth0-label-submit')
    
    def wait_login_confirmation(self):
        """Wait for confirmation that login was successful."""
        try:
            self.driver.wait_for_element(
                Locator(LocatorType.XPATH, "//ul[@class='LinkBar']")
            )
            logger.info(f"Login en {self.name()} exitoso")
        except Exception as e:
            msg = ""
            try:
                el = self.driver.wait_for_element(
                    Locator(LocatorType.CSS, "span.animated.fadeInUp")
                )
                if "usuario" in el.text.lower() or "cuenta" in el.text.lower():
                    msg = el.text
            except:
                msg = str(e)
                pass
            error_message = f"Error Login {self.name()}: {msg}"
            logger.info(error_message)
            raise CompanyPolicyException(company=self.name(), reason=error_message)

    def do_logout(self):
        """Perform SANCOR logout."""
        # SANCOR uses default logout, this method shouln't be called directly.
        logger.warning("SANCOR does not require a custom logout implementation.")
        raise NotImplementedError()

    def find_policy_input(self):
        """Find and return the policy number input field."""
        loc = Locator(LocatorType.ID, "ReferenceNumber")
        try:
            return self.driver.wait_for_element(loc)
        except Exception as e:
            raise CompanyPolicyException(
                company=self.name(), reason=f"Policy input not found: {str(e)}"
            )

    def search_policy(self):
        """Execute the policy search operation."""
        try:
            logger.info("Searching for policy in SANCOR system")

            # Click the search button
            self.driver.click(Locator(LocatorType.ID, "searchPolicy"))
            logger.debug("Search button clicked, waiting for results")
            try:
                r = self.driver.find_element(Locator(LocatorType.CLASS, "xgrid_rows"))
                l = self.driver.find_element(Locator(LocatorType.CLASS, "label"), r)
                l.click()
            except:
                sancor_message = None
                try:
                    sancor_message = self.driver.find_element(Locator(LocatorType.CLASS, "dummyRow")).text
                except:
                    sancor_message = "No hay resultados"
                error_message = f"SANCOR informa: {sancor_message}. Revise que los datos sean correctos"
                raise Exception(error_message)

        except Exception as e:
            raise CompanyPolicyException(
                company=self.name(), reason=f"Policy search failed: {str(e)}"
            )

    def get_endorsements_count(self) -> int:
        """Get the number of rows in the fleet table."""
        return 1

    def get_vehicles_count(self) -> int:
        """Get the number of rows in the endorsement."""
        return 1

    def get_vehicles_data(self) -> list[dict]:
        return [{}]

    def reconcile_vehicles(
        self, page_data: list[dict], policy_data: list[dict]
    ) -> list[dict]:
        reconciled_vehicles = []

        for policy_vehicle in policy_data:
            license_plate = policy_vehicle.get("license_plate", "").strip()

            reconciled_vehicle = policy_vehicle.copy()

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

    def find_valid_row(self):
        logger.debug('fvr 1')
        table = self.driver.wait_for_element(Locator(LocatorType.ID, "historicalPolicy"))
        logger.debug('fvr 2')
        filas = self.driver.find_elements(Locator(LocatorType.TAG, "tr"), table)
        logger.debug('fvr 3')

        fecha_actual_value = self.driver.find_element(Locator(LocatorType.ID, "movementDate")).get_attribute('value')
        logger.debug('fvr 4')
        fecha_actual = datetime.strptime(fecha_actual_value, '%d/%m/%Y')
        # fecha_actual += timedelta(days=20)
        filas_vigentes = {}
        fila_vigente = None

        for fila in filas:
            columnas = self.driver.find_elements(Locator(LocatorType.TAG, 'td'), fila)

            vigencia_desde_text = columnas[7].text.strip() if len(columnas) > 7 else None
            # Verificar si la fila tiene las columnas de vigencia
            if vigencia_desde_text:
                tipo_mov = columnas[3].text.strip()
                vigencia_desde = datetime.strptime(vigencia_desde_text, '%d/%m/%Y')
                vigencia_hasta = columnas[8].text
                es_emision = re.match(r"(Emis|Renov).*liza", tipo_mov) is not None
                if not es_emision:
                    continue
                logger.info(f"Mov: {tipo_mov}. Vigencia desde: {vigencia_desde.strftime('%d/%m/%Y')} hasta: {vigencia_hasta}")

                # Verificar si la vigencia hasta no está vacía
                if vigencia_hasta.strip() != '':
                    vigencia_hasta = datetime.strptime(vigencia_hasta, '%d/%m/%Y')
                else:
                    test_date = vigencia_desde + timedelta(days=364)
                    if test_date > fecha_actual:
                        vigencia_hasta = vigencia_desde + timedelta(days=364)
                    else:
                        vigencia_hasta = None
                
                if vigencia_hasta:
                    # Verificar si la fecha actual está entre las fechas de vigencia
                    if vigencia_desde <= fecha_actual <= vigencia_hasta:
                        filas_vigentes[vigencia_desde] = fila

        if filas_vigentes:
            fila_vigente = filas_vigentes[max(filas_vigentes.keys())]
            logger.info(fila_vigente.get_attribute('outerHTML'))
        logger.debug('fvr 5')
        return fila_vigente

    def go_to_vehicle_download_page(self, vehicle, validation_data):
        logger.debug('gtvdp 1')
        valid_row = self.find_valid_row()
        logger.debug('gtvdp 2')
        if not valid_row:
            logger.debug('gtvdp 3')
            time.sleep(600)
            error_message = 'No se encuentra una poliza vigente en los proximos 20 dias'
            raise CompanyPolicyException(self.name(), error_message)
        logger.debug('gtvdp 4')
        logger.info(f"Poliza vigente encontrada. \n{valid_row.get_attribute('outerHTML')}")
        valid_row.click()
        logger.info('Click ok valid_row')

    def validate_policy(self, policy, endorsement_line):
        validation_data = {
            "valid": True
        }
        return validation_data

    def get_mercosur_download_starter(self, policy=None):
        return SancorClickDownloadStarter(
                            driver=self.driver,
                            locator=Locator(
                                LocatorType.ID,
                                '88Mercosur',
                            ),
                        )

    def get_soa_download_starter(self, policy=None):
        return SancorClickDownloadStarter(
                        driver=self.driver,
                        locator=Locator(
                            LocatorType.ID, 
                            '132Certificado de Cobertura SOA'
                        ),
                    )
