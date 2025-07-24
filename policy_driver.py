import logging
import os
import time
from enum import Enum, auto
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    StaleElementReferenceException,
    ElementNotInteractableException,
    WebDriverException,
    ElementClickInterceptedException,
)

load_dotenv()

logger = logging.getLogger(__name__)


class DriverException(Exception):
    """Base exception for all driver-related errors."""

    pass


class ElementNotFoundException(DriverException):
    """Raised when an element cannot be found."""

    def __init__(self, locator):
        super().__init__(f"Element not found: {locator}")
        self.locator = locator


class ElementNotInteractableError(DriverException):
    """Raised when an element exists but can't be interacted with."""

    def __init__(self, locator):
        super().__init__(f"Element not interactable: {locator}")
        self.locator = locator


class LoginFailedException(DriverException):
    """Raised when login fails."""

    def __init__(self, reason):
        super().__init__(f"Login failed: {reason}")
        self.reason = reason


class TimeoutError(DriverException):
    """Raised when an operation times out."""

    def __init__(self, operation):
        super().__init__(f"Timeout during: {operation}")
        self.operation = operation


class LocatorType(Enum):
    ID = auto()
    CSS = auto()
    XPATH = auto()
    CLASS = auto()
    NAME = auto()
    TAG = auto()
    LINK_TEXT = auto()
    PARTIAL_LINK_TEXT = auto()


class Locator:
    _MAPPING = {
        LocatorType.ID: By.ID,
        LocatorType.CSS: By.CSS_SELECTOR,
        LocatorType.XPATH: By.XPATH,
        LocatorType.CLASS: By.CLASS_NAME,
        LocatorType.NAME: By.NAME,
        LocatorType.TAG: By.TAG_NAME,
        LocatorType.LINK_TEXT: By.LINK_TEXT,
        LocatorType.PARTIAL_LINK_TEXT: By.PARTIAL_LINK_TEXT,
    }
    def __init__(self, by: LocatorType, value: str):
        self.by = by
        self.value = value

    def to_selenium(self):
        return (self._MAPPING[self.by], self.value)
    
    def __str__(self):
        return f"{self._MAPPING[self.by]} - {self.value}"


class PolicyDriver:
    """
    Wrapper class for Selenium WebDriver that abstracts all Selenium-specific details.
    """

    def __init__(self, driver_creator, headless=True):
        self.folder = os.getenv("TMP_DOWNLOAD_FOLDER")
        self.screenshot_folder = os.getenv("DEBUG_SCREENSHOT_FOLDER", self.folder)
        self.screenshot_counter = 0
        self.headless = headless
        self.driver_creator = driver_creator
        if not os.path.exists(self.folder):
            os.makedirs(self.folder)

    def init_driver(self):
        chrome_options = webdriver.ChromeOptions()
        if self.headless:
            chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-browser-side-navigation")
        chrome_options.add_argument("enable-automation")
        chrome_options.add_argument(
            "--window-size=1920,1080"
        )  # Ensure consistent viewport
        chrome_options.add_argument(
            "--force-device-scale-factor=1"
        )  # Prevent scaling issues

        prefs = {
            "download.default_directory": self.folder,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "plugins.always_open_pdf_externally": True,
            "profile.managed_default_content_settings.images": 2,
        }
        chrome_options.add_experimental_option("prefs", prefs)

        self.driver = self.driver_creator.create(chrome_options)
        self.driver.implicitly_wait(10)
        logger.info("WebDriver instance created")

    def navigate(self, url: str):
        """Navigate to the specified URL."""
        try:
            self.driver.get(url)
        except WebDriverException as e:
            raise DriverException(f"Failed to navigate to {url}: {str(e)}")

    def close(self):
        """Close the browser and clean up resources."""
        if self.driver:
            self.driver.close()
            self.driver.quit()
            logger.info("WebDriver instance closed completely")

    def find_element(self, locator: Locator, context=None):
        """Find a single element, optionally within a context element.

        Args:
            locator: The locator for the element to find
            context: Optional parent WebElement to search within

        Returns:
            WebElement: The found element

        Raises:
            ElementNotFoundException: If element not found
            ElementNotInteractableError: If element exists but can't be interacted with
        """
        try:
            if context:
                return context.find_element(*locator.to_selenium())
            return self.driver.find_element(*locator.to_selenium())
        except NoSuchElementException:
            raise ElementNotFoundException(locator.value)
        except ElementNotInteractableException:
            raise ElementNotInteractableError(locator.value)

    def find_elements(self, locator: Locator, context=None):
        """Find multiple elements, optionally within a context element.

        Args:
            locator: The locator for the elements to find
            context: Optional parent WebElement to search within

        Returns:
            list[WebElement]: List of found elements (empty list if none found)

        Raises:
            DriverException: For WebDriver errors other than "not found"
        """
        try:
            if context:
                return context.find_elements(*locator.to_selenium())
            return self.driver.find_elements(*locator.to_selenium())
        except NoSuchElementException:
            return (
                []
            )  # Differently from find_element, returns empty list rather than raise
        except StaleElementReferenceException:
            raise DriverException(
                f"Elements became stale while searching: {locator.value}"
            )
        except Exception as e:
            raise DriverException(f"Error finding elements: {str(e)}")

    def wait_for_element(self, locator: Locator, timeout=20):
        """Wait for an element to be present and visible."""
        try:
            wait = WebDriverWait(self.driver, timeout)
            return wait.until(EC.visibility_of_element_located(locator.to_selenium()))
        except TimeoutException:
            # self._take_debug_screenshot(f"timeout_waiting_for_{locator.value}")
            raise TimeoutError(
                f"Waiting for element {locator.value}. Screenshot saved."
            )
        except NoSuchElementException:
            # self._take_debug_screenshot(f"element_not_found_{locator.value}")
            raise ElementNotFoundException(locator.value)
        except Exception as e:
            # self._take_debug_screenshot(f"unexpected_error_{locator.value}")
            raise DriverException(f"Unexpected error waiting for element: {str(e)}")

    def wait_for_invisibility(self, locator: Locator, timeout=10, poll_frequency=0.2):
        """Wait for an element to become invisible or not present in the DOM.

        Args:
            locator: The locator for the element to wait for
            timeout: Maximum time to wait in seconds

        Returns:
            bool: True if element became invisible within timeout, False if element wasn't present to begin with

        Raises:
            TimeoutError: If element remains visible after timeout
            DriverException: For other WebDriver errors
        """
        try:
            wait = WebDriverWait(
                self.driver, timeout=timeout, poll_frequency=poll_frequency
            )
            return wait.until(EC.invisibility_of_element_located(locator.to_selenium()))
        except TimeoutException:
            raise TimeoutError(
                f"Element {locator.value} remained visible after {timeout} seconds"
            )
        except Exception as e:
            raise DriverException(f"Error waiting for element invisibility: {str(e)}")

    def wait_for_clickable(self, locator: Locator, timeout=20):
        """Wait for an element to be clickable."""
        try:
            wait = WebDriverWait(self.driver, timeout)
            return wait.until(EC.element_to_be_clickable(locator.to_selenium()))
        except TimeoutException:
            raise TimeoutError(f"Waiting for clickable element {str(locator)}")
        except NoSuchElementException:
            raise ElementNotFoundException(str(locator))

    def wait_for_staleness(self, element, timeout=20):
        try:
            wait = WebDriverWait(self.driver, timeout)
            return wait.until(EC.staleness_of(element))
        except TimeoutException:
            raise TimeoutError(f"Waiting for element to become stale {element}")
        
    def click(self, locator: Locator):
        """Click on the specified element."""
        attempts = 0
        max_attempts = 3
        try:
            element = self.wait_for_clickable(locator)
            element.click()
        except ElementClickInterceptedException:
            # Retry clicking if intercepted
            while attempts < max_attempts:
                try:
                    time.sleep(0.5)
                    element = self.wait_for_clickable(locator)
                    element.click()
                    return
                except ElementClickInterceptedException:
                    attempts += 1
            raise ElementNotInteractableError(str(locator))

    def send_keys(self, locator: Locator, text: str):
        """Send text to the specified element."""
        try:
            element = self.wait_for_element(locator)
            element.send_keys(text)
        except ElementNotInteractableException:
            raise ElementNotInteractableError(str(locator))

    def select_dropdown_by_value(self, locator: Locator, value: str):
        """Select an option from a dropdown by value."""
        try:
            from selenium.webdriver.support.select import Select

            element = self.wait_for_element(locator)
            select = Select(element)
            select.select_by_value(value)
        except NoSuchElementException:
            raise ElementNotFoundException(f"Option with value {value} not found")
        except ElementNotInteractableException:
            raise ElementNotInteractableError(str(locator))

    def is_element_present(self, locator: Locator, timeout=5):
        """Check if an element is present without waiting the full timeout."""
        try:
            wait = WebDriverWait(self.driver, timeout)
            wait.until(EC.presence_of_element_located(locator.to_selenium()))
            return True
        except (TimeoutException, NoSuchElementException):
            return False

    def get_current_url(self) -> str:
        """Get the current URL of the browser."""
        return self.driver.current_url

    def _take_debug_screenshot(self, name_prefix):
        """Take a screenshot and save it with a descriptive name."""
        try:
            if not self.screenshot_folder:
                logger.warning("Screenshot folder not set")
                return
            if not os.path.exists(self.screenshot_folder):
                os.makedirs(self.screenshot_folder)
            from datetime import datetime

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            alnum_chars = [c for c in name_prefix if c.isalnum()]
            pfx = "".join(alnum_chars[:4])
            filename = f"{pfx}_{self.screenshot_counter}_{timestamp}.png"
            self.screenshot_counter += 1
            screenshot_path = os.path.join(self.screenshot_folder, filename)

            # Debug: Print paths before attempting
            print(f"Attempting to save screenshot to: {screenshot_path}")
            print(f"Download folder exists: {os.path.exists(self.folder)}")

            # Ensure directory exists
            os.makedirs(os.path.dirname(screenshot_path), exist_ok=True)

            # Take screenshot
            print("Attempting to take screenshot...")
            self.driver.save_screenshot(screenshot_path)

            # Verify file was created
            if os.path.exists(screenshot_path):
                print(f"Screenshot successfully saved to: {screenshot_path}")
                logger.error(f"Debug screenshot saved to: {screenshot_path}")
            else:
                print("ERROR: Screenshot file not created after save_screenshot call")

        except Exception as e:
            print(f"EXCEPTION in screenshot: {str(e)}")
            logger.error(f"Failed to take debug screenshot: {str(e)}")
            logger.error(f"Failed to take debug screenshot: {str(e)}")

    def get_table_row_count(self, locator: Locator) -> int:
        """
        Returns the number of rows in a table matching the locator.

        Args:
            locator: Locator for the table rows (should target TR elements)

        Returns:
            int: Number of rows found

        Raises:
            ElementNotFoundException: If no rows are found
            DriverException: For other WebDriver errors
        """
        try:
            rows = self.find_elements(locator)
            if not rows:
                logger.warning(f"No rows found matching locator: {str(locator)}")
            return len(rows)
        except ElementNotFoundException:
            # Return 0 if the element pattern exists but no rows are present
            return 0
        except Exception as e:
            raise DriverException(f"Error getting row count: {str(e)} - locator: {str(locator)}")

    def execute_script(self, script: str):
        """Execute the specified script."""
        try:
            self.driver.execute_script(script)
        except WebDriverException as e:
            raise DriverException(f"Failed to execute script {script}: {str(e)}")

    def extract_table_data(
        self, table_id: str, columns_needed: list[str]
    ) -> list[dict]:
        """
        Extracts specified columns from an HTML table.

        Args:
            table_id: ID of the table element
            columns_needed: List of column headers to extract

        Returns:
            List of dictionaries where each dict represents a row with the requested columns

        Example:
            extract_table_data("GrdItems", ["Matrícula", "Nro."])
            Returns:
                [
                    {"Matrícula": "LTP5136", "Nro.": "1"},
                    {"Matrícula": "MTP2437", "Nro.": "2"},
                    {"Matrícula": "NTP2559", "Nro.": "3"}
                ]
        """
        try:
            # Locate the table
            table_locator = Locator(LocatorType.ID, table_id)
            table = self.wait_for_element(table_locator)

            # Get column headers
            header_locator = Locator(LocatorType.CSS, "thead tr th")
            headers = [
                h.text.strip()
                for h in self.find_elements(header_locator, context=table)
            ]

            # Validate requested columns exist
            missing_columns = [col for col in columns_needed if col not in headers]
            if missing_columns:
                raise DriverException(f"Columns not found in table: {missing_columns}")

            # Get column indices for requested columns
            column_indices = {col: headers.index(col) for col in columns_needed}

            # Extract rows
            rows_data = []
            row_locator = Locator(LocatorType.CSS, "tbody tr")
            rows = self.find_elements(row_locator, context=table)

            for row in rows:
                cell_locator = Locator(LocatorType.CSS, "td")
                cells = self.find_elements(cell_locator, context=row)

                row_data = {
                    col: cells[idx].text.strip()
                    for col, idx in column_indices.items()
                    if idx < len(cells)  # Handle rows with fewer cells
                }

                if row_data:  # Only add rows with all requested columns
                    rows_data.append(row_data)

            return rows_data

        except Exception as e:
            raise DriverException(f"Failed to extract table data: {str(e)}")

    def back(self):
        """Navigate back in browser history."""
        try:
            self.driver.back()
        except WebDriverException as e:
            raise DriverException(f"Failed to navigate back: {str(e)}")


    def set_checkbox_state(self, locator, desired_state):
        """
        Set checkbox to desired state (True=checked, False=unchecked)
        Only clicks if current state doesn't match desired state
        """
        element = self.find_element(locator)
        current_state = element.is_selected()
        if current_state != desired_state:
            element.click()