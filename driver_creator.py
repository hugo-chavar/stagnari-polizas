import os
from selenium import webdriver

class DriverCreator:
    def create(self, chrome_options):
        # Connect to the Selenium server running in the container
        selenium_host = os.getenv(
            "SELENIUM_HOST", "localhost"
        )
        chrome_options.page_load_strategy = 'eager'
        chrome_options.add_argument("--disable-software-rasterizer")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")

        return webdriver.Remote(
            command_executor=f"http://{selenium_host}:4444/wd/hub",
            options=chrome_options,
        )