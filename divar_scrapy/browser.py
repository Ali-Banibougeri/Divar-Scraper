import re
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class BrowserSession:
    """صفحهٔ سرچ را باز می‌کند: کوکی + UA + توکن آگهی‌ها برمی‌گرداند"""

    def __init__(self, search_url, max_scrolls=20, scroll_pause=2.5, headless=False):
        self.search_url = search_url
        self.max_scrolls = max_scrolls
        self.scroll_pause = scroll_pause
        self.headless = headless

    def collect(self):
        opts = Options()
        opts.add_argument("--window-size=1400,900")
        opts.add_argument("--disable-blink-features=AutomationControlled")
        opts.add_experimental_option("excludeSwitches", ["enable-automation"])
        if self.headless:
            opts.add_argument("--headless=new")

        driver = webdriver.Chrome(options=opts)
        try:
            # ... (همان منطق get + اسکرول + جمع‌کردن توکن‌ها از پیام قبل)
            ...
            return {
                "ua": driver.execute_script("return navigator.userAgent;"),
                "cookies": driver.get_cookies(),
                "tokens": tokens,
            }
        finally:
            driver.quit()