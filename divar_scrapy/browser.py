import base64
import json
import random
import time
from pathlib import Path
from typing import Any, Iterator

from selenium import webdriver
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    StaleElementReferenceException,
)
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class BrowserSession:
    """Selenium/CDP session used to discover Divar search XHR responses."""

    def __init__(
        self,
        search_url: str,
        driver_path: str | Path,
        target_url: str,
        target_type: str = "XHR",
        max_captures: int = 100,
        max_scroll_attempts_per_capture: int = 10,
        response_timeout: int = 15,
        poll_interval: float = 0.1,
        random_wait_after_scroll: tuple[float, float] = (2.0, 5.0),
        random_wait_after_click: tuple[float, float] = (3.0, 6.0),
        no_scroll_wait: tuple[float, float] = (3.0, 5.0),
        initial_page_wait: tuple[float, float] = (4.0, 6.0),
        headless: bool = True,
    ) -> None:
        self.search_url = search_url
        self.driver_path = Path(driver_path)
        self.target_url = target_url
        self.target_type = target_type.upper()
        self.max_captures = max_captures
        self.max_scroll_attempts_per_capture = max_scroll_attempts_per_capture
        self.response_timeout = response_timeout
        self.poll_interval = poll_interval
        self.random_wait_after_scroll = random_wait_after_scroll
        self.random_wait_after_click = random_wait_after_click
        self.no_scroll_wait = no_scroll_wait
        self.initial_page_wait = initial_page_wait
        self.headless = headless

    def iter_captures(self) -> Iterator[dict[str, Any]]:
        """Yield one new Divar search response at a time."""
        if self.max_captures <= 0:
            raise ValueError("max_captures must be greater than zero")

        driver = self._build_driver()

        try:
            driver.execute_cdp_cmd("Network.enable", {})
            driver.get(self.search_url)

            self.random_wait(
                *self.initial_page_wait,
                label="initial page load",
            )
            self._wait_for_initial_cards(driver)
            self.clear_network_logs(driver)

            previous_request_ids: set[str] = set()

            for capture_number in range(1, self.max_captures + 1):
                captured: dict[str, Any] | None = None

                for attempt in range(
                    1,
                    self.max_scroll_attempts_per_capture + 1,
                ):
                    self.clear_network_logs(driver)
                    scrolled = self.scroll_to_bottom(driver)

                    if not scrolled:
                        self.random_wait(
                            *self.no_scroll_wait,
                            label="no-scroll/end check",
                        )

                        # If we cannot scroll any further and the explicit
                        # "آگهی‌های بیشتر" button is not present, Divar has
                        # reached the end of this search result set.
                        if self.find_load_more_button(driver) is None:
                            print(
                                f"[+] Search end detected at capture {capture_number}."
                            )
                            return
                    else:
                        self.random_wait(
                            *self.random_wait_after_scroll,
                            label="after scroll",
                        )

                    clicked = self.click_load_more_if_exists(driver)
                    if clicked:
                        self.random_wait(
                            *self.random_wait_after_click,
                            label="after load-more click",
                        )

                    captured = self.wait_for_new_search_response(
                        driver,
                        previous_request_ids,
                        timeout=self.response_timeout,
                    )

                    if captured is not None:
                        break

                    # A load-more button can trigger delayed network activity.
                    # If it disappears during the attempt, let the next pass
                    # perform the same end-of-results check.
                    print(
                        f"[!] No NEW search response for capture {capture_number}, "
                        f"attempt {attempt}."
                    )

                if captured is None:
                    continue

                yield captured

        finally:
            driver.quit()

    def _build_driver(self) -> webdriver.Chrome:
        if not self.driver_path.exists() or not self.driver_path.is_file():
            raise FileNotFoundError(
                "ChromeDriver not found. Configure DIVAR_CHROMEDRIVER_PATH "
                f"in settings.py. Current value: {self.driver_path}"
            )

        options = Options()
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option(
            "excludeSwitches",
            ["enable-automation"],
        )
        options.add_experimental_option(
            "useAutomationExtension",
            False,
        )

        if self.headless:
            options.add_argument("--headless=new")

        options.set_capability(
            "goog:loggingPrefs",
            {"performance": "ALL"},
        )

        service = Service(executable_path=str(self.driver_path))
        return webdriver.Chrome(service=service, options=options)

    def _wait_for_initial_cards(self, driver: webdriver.Chrome) -> None:
        WebDriverWait(driver, 30).until(
            EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, "a[href*='/v/']")
            )
        )

    @staticmethod
    def parse_cdp_message(entry: dict[str, Any]) -> dict[str, Any] | None:
        try:
            outer = json.loads(entry["message"])
            message = outer.get("message")
            if isinstance(message, dict):
                return message
        except (KeyError, TypeError, json.JSONDecodeError):
            pass
        return None

    @staticmethod
    def random_wait(minimum: float, maximum: float, label: str = "") -> None:
        delay = random.uniform(minimum, maximum)
        if label:
            print(f"[+] Random wait ({label}): {delay:.2f}s")
        time.sleep(delay)

    @staticmethod
    def clear_network_logs(driver: webdriver.Chrome) -> None:
        try:
            while driver.get_log("performance"):
                pass
        except Exception:
            pass

    @staticmethod
    def scroll_to_bottom(driver: webdriver.Chrome) -> bool:
        """Scroll to the current bottom and report whether the page moved."""
        previous_height = int(
            driver.execute_script("return document.body.scrollHeight;")
        )
        previous_scroll_y = int(
            driver.execute_script("return window.scrollY;")
        )

        driver.execute_script(
            """
            window.scrollTo({
                top: document.body.scrollHeight,
                behavior: 'smooth'
            });
            """
        )
        time.sleep(1.5)

        stable_counter = 0
        moved = False

        while stable_counter < 2:
            current_height = int(
                driver.execute_script("return document.body.scrollHeight;")
            )
            current_scroll_y = int(
                driver.execute_script("return window.scrollY;")
            )

            if current_height > previous_height:
                moved = True
                previous_height = current_height
                driver.execute_script(
                    """
                    window.scrollTo({
                        top: document.body.scrollHeight,
                        behavior: 'smooth'
                    });
                    """
                )
                time.sleep(1.5)
                stable_counter = 0
                continue

            if current_scroll_y != previous_scroll_y:
                moved = True

            stable_counter += 1
            time.sleep(0.5)

        return moved

    @staticmethod
    def find_load_more_button(driver: webdriver.Chrome):
        selectors = [
            (
                By.XPATH,
                "//button[.//span[contains(normalize-space(), 'آگهی‌های بیشتر')]]",
            ),
            (
                By.CSS_SELECTOR,
                "button[class*='post-list__load-more-btn']",
            ),
        ]

        for by, selector in selectors:
            try:
                elements = driver.find_elements(by, selector)
                for element in elements:
                    try:
                        if element.is_displayed() and element.is_enabled():
                            return element
                    except StaleElementReferenceException:
                        continue
            except Exception:
                continue

        return None

    @classmethod
    def click_load_more_if_exists(cls, driver: webdriver.Chrome) -> bool:
        button = cls.find_load_more_button(driver)
        if button is None:
            return False

        try:
            driver.execute_script(
                """
                arguments[0].scrollIntoView({
                    behavior: 'smooth',
                    block: 'center'
                });
                """,
                button,
            )
            time.sleep(0.5)
            button.click()
            return True
        except (
            ElementClickInterceptedException,
            StaleElementReferenceException,
        ):
            try:
                driver.execute_script("arguments[0].click();", button)
                return True
            except Exception:
                return False
        except Exception:
            return False

    @staticmethod
    def get_response_body(
        driver: webdriver.Chrome,
        request_id: str,
    ) -> str | None:
        try:
            result = driver.execute_cdp_cmd(
                "Network.getResponseBody",
                {"requestId": request_id},
            )
            body = result.get("body", "")

            if result.get("base64Encoded"):
                body = base64.b64decode(body).decode(
                    "utf-8",
                    errors="replace",
                )

            return body
        except Exception:
            return None

    def wait_for_new_search_response(
        self,
        driver: webdriver.Chrome,
        previous_request_ids: set[str],
        timeout: int,
    ) -> dict[str, Any] | None:
        start_time = time.time()
        requests_data: dict[str, dict[str, Any]] = {}

        while time.time() - start_time < timeout:
            logs = driver.get_log("performance")

            for entry in logs:
                message = self.parse_cdp_message(entry)
                if message is None:
                    continue

                method = message.get("method")
                params = message.get("params", {})

                if method == "Network.requestWillBeSent":
                    request = params.get("request", {})
                    request_id = params.get("requestId")
                    url = request.get("url", "")
                    request_method = request.get("method", "")
                    resource_type = params.get("type", "")

                    if not request_id or request_id in previous_request_ids:
                        continue
                    if url != self.target_url:
                        continue
                    if request_method.upper() != "POST":
                        continue
                    if resource_type.upper() != self.target_type:
                        continue

                    requests_data[request_id] = {
                        "id": request_id,
                        "url": url,
                        "method": request_method,
                        "type": resource_type,
                        "headers": request.get("headers", {}),
                        "post_data": request.get("postData"),
                        "_response_received": False,
                    }
                    previous_request_ids.add(request_id)

                elif method == "Network.responseReceived":
                    request_id = params.get("requestId")
                    if request_id not in requests_data:
                        continue

                    response = params.get("response", {})
                    requests_data[request_id]["response"] = {
                        "status": response.get("status"),
                        "status_text": response.get("statusText"),
                        "mime_type": response.get("mimeType"),
                        "protocol": response.get("protocol"),
                        "headers": response.get("headers", {}),
                    }
                    requests_data[request_id]["_response_received"] = True

                elif method == "Network.loadingFinished":
                    request_id = params.get("requestId")
                    if request_id not in requests_data:
                        continue

                    request_data = requests_data[request_id]
                    if not request_data.get("_response_received"):
                        continue

                    body = self.get_response_body(driver, request_id)
                    if body is None:
                        continue

                    try:
                        response_json = json.loads(body)
                    except json.JSONDecodeError:
                        continue

                    request_data["response"]["data"] = response_json
                    request_data.pop("_response_received", None)
                    return request_data

            time.sleep(self.poll_interval)

        return None
