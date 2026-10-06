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


if __name__ == "__main__":
    unittest.main()
