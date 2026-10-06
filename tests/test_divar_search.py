import tempfile
import unittest
from pathlib import Path

from divar_scrapy.database import SQLiteDatabase
from divar_scrapy.parser import parse_search_response


def make_widget(token: str, city: str = "اصفهان") -> dict:
    return {
        "widget_type": "POST_ROW",
        "data": {
            "token": token,
            "title": f"آگهی {token}",
            "middle_description_text": "۵۱۰,۰۰۰,۰۰۰ تومان",
            "image_url": f"https://example.com/{token}.jpg",
            "image_count": 1,
            "action": {
                "payload": {
                    "token": token,
                    "web_info": {
                        "city_persian": city,
                    },
                }
            },
        },
        "action_log": {
            "server_side_info": {
                "info": {
                    "extra_data": {
                        "jli": {
                            "cities": ["110"],
                            "category": {"value": "cars"},
                        },
                        "last_post_sort_date": "1234567890",
                    }
                }
            }
        },
    }


class DivarSearchTest(unittest.TestCase):
    def test_parser_extracts_unique_ads(self):
        document = {
            "response": {
                "data": {
                    "list_widgets": [
                        make_widget("A001"),
                        make_widget("A001"),
                        make_widget("A002"),
                    ]
                }
            }
        }

        ads = parse_search_response(document)

        self.assertEqual(len(ads), 2)
        self.assertEqual(ads[0]["token"], "A001")
        self.assertEqual(ads[0]["price"], 510_000_000)

    def test_duplicate_ratio_stops_at_configured_threshold(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "divar.db"
            db = SQLiteDatabase(db_path)
            db.connect()

            search_id = db.get_or_create_search_source(
                "auto_iran",
                "https://divar.ir/s/iran/auto",
            )

            for token in [f"A{i:03d}" for i in range(9)]:
                db.upsert_ad({"token": token, "title": token})

            ratio = db.duplicate_ratio(
                [f"A{i:03d}" for i in range(10)]
            )
            self.assertEqual(ratio, 0.9)
            self.assertGreaterEqual(ratio, 0.90)

            for token in [f"A{i:03d}" for i in range(10)]:
                db.upsert_ad({
                    "token": token,
                    "search_id": search_id,
                })

            self.assertEqual(
                len(db.get_existing_tokens([f"A{i:03d}" for i in range(10)])),
                10,
            )

            db.close()

    def test_tokens_persist_across_database_restarts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "divar.db"

            first_db = SQLiteDatabase(db_path)
            first_db.connect()
            first_db.upsert_ad({"token": "PERSIST001", "title": "persistent"})
            first_db.close()

            second_db = SQLiteDatabase(db_path)
            second_db.connect()
            self.assertEqual(
                second_db.duplicate_ratio(["PERSIST001"]),
                1.0,
            )
            second_db.close()

    def test_ratio_below_threshold_continues(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db = SQLiteDatabase(Path(temp_dir) / "divar.db")
            db.connect()

            for token in [f"B{i:03d}" for i in range(8)]:
                db.upsert_ad({"token": token, "title": token})

            ratio = db.duplicate_ratio(
                [f"B{i:03d}" for i in range(10)]
            )
            self.assertEqual(ratio, 0.8)
            self.assertLess(ratio, 0.90)
            db.close()





# Minimal Selenium stubs so pure browser-state tests can run without Selenium installed.
import sys
import types

if "selenium" not in sys.modules:
    selenium = types.ModuleType("selenium")
    webdriver = types.ModuleType("selenium.webdriver")
    webdriver.Chrome = object

    common = types.ModuleType("selenium.common")
    exceptions = types.ModuleType("selenium.common.exceptions")
    exceptions.ElementClickInterceptedException = type(
        "ElementClickInterceptedException", (Exception,), {}
    )
    exceptions.StaleElementReferenceException = type(
        "StaleElementReferenceException", (Exception,), {}
    )

    options_module = types.ModuleType("selenium.webdriver.chrome.options")
    service_module = types.ModuleType("selenium.webdriver.chrome.service")
    options_module.Options = type("Options", (), {})
    service_module.Service = type("Service", (), {})

    by_module = types.ModuleType("selenium.webdriver.common.by")
    by_module.By = type("By", (), {"CSS_SELECTOR": "css", "XPATH": "xpath"})

    ui_module = types.ModuleType("selenium.webdriver.support.ui")
    ec_module = types.ModuleType("selenium.webdriver.support.expected_conditions")
    ui_module.WebDriverWait = type("WebDriverWait", (), {})
    ec_module.presence_of_all_elements_located = lambda locator: locator

    sys.modules.update({
        "selenium": selenium,
        "selenium.webdriver": webdriver,
        "selenium.common": common,
        "selenium.common.exceptions": exceptions,
        "selenium.webdriver.chrome": types.ModuleType("selenium.webdriver.chrome"),
        "selenium.webdriver.chrome.options": options_module,
        "selenium.webdriver.chrome.service": service_module,
        "selenium.webdriver.common": types.ModuleType("selenium.webdriver.common"),
        "selenium.webdriver.common.by": by_module,
        "selenium.webdriver.support": types.ModuleType("selenium.webdriver.support"),
        "selenium.webdriver.support.ui": ui_module,
        "selenium.webdriver.support.expected_conditions": ec_module,
    })


class FakeDriver:
    def __init__(self, heights, scroll_positions):
        self.heights = iter(heights)
        self.scroll_positions = iter(scroll_positions)

    def execute_script(self, script):
        if "return document.body.scrollHeight" in script:
            return next(self.heights)
        if "return window.scrollY" in script:
            return next(self.scroll_positions)
        return None


class BrowserBehaviorTest(unittest.TestCase):
    def test_scroll_reports_no_movement(self):
        import divar_scrapy.browser as browser_module
        BrowserSession = browser_module.BrowserSession
        browser_module.time.sleep = lambda _: None

        # height, scroll_y are unchanged for all stability checks.
        driver = FakeDriver(
            heights=[1000, 1000, 1000],
            scroll_positions=[500, 500, 500],
        )
        self.assertFalse(BrowserSession.scroll_to_bottom(driver))

    def test_scroll_reports_movement(self):
        import divar_scrapy.browser as browser_module
        BrowserSession = browser_module.BrowserSession
        browser_module.time.sleep = lambda _: None

        # The first scroll changes window.scrollY.
        driver = FakeDriver(
            heights=[1000, 1000, 1000],
            scroll_positions=[400, 500, 500],
        )
        self.assertTrue(BrowserSession.scroll_to_bottom(driver))


class SQLiteBatchTest(unittest.TestCase):
    def test_capture_is_committed_as_one_batch(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "divar.db"
            db = SQLiteDatabase(db_path)
            db.connect()
            search_id = db.get_or_create_search_source(
                "auto_iran",
                "https://divar.ir/s/iran/auto",
            )

            ads = [
                {"token": "BATCH001", "title": "one"},
                {"token": "BATCH002", "title": "two"},
            ]
            db.save_search_capture(
                search_id=search_id,
                ads=ads,
                new_tokens={"BATCH001", "BATCH002"},
                capture_count=1,
                new_count=2,
                stop_ratio=0.0,
            )
            db.close()

            second_db = SQLiteDatabase(db_path)
            second_db.connect()
            self.assertEqual(
                second_db.get_existing_tokens(["BATCH001", "BATCH002"]),
                {"BATCH001", "BATCH002"},
            )
            second_db.close()


if __name__ == "__main__":
    unittest.main()