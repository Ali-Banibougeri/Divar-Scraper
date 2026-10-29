import json
import sqlite3
from pathlib import Path
from typing import Any, Iterable


class SQLiteDatabase:
    """Small SQLite persistence layer for Divar discovery and detail data."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.connection: sqlite3.Connection | None = None

    def connect(self) -> None:
        if self.connection is not None:
            return

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.db_path, timeout=30)
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA journal_mode = WAL")
        self.connection.execute("PRAGMA synchronous = FULL")
        self.connection.execute("PRAGMA busy_timeout = 30000")
        self.initialize_schema()

    def close(self) -> None:
        if self.connection is None:
            return

        try:
            self.connection.execute("PRAGMA wal_checkpoint(PASSIVE)")
        finally:
            self.connection.close()
            self.connection = None

    def initialize_schema(self) -> None:
        connection = self._require_connection()
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS search_sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                url TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                last_run_at TEXT,
                last_stop_ratio REAL,
                last_capture_count INTEGER DEFAULT 0,
                last_new_count INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS ads (
                token TEXT PRIMARY KEY,
                url TEXT,
                title TEXT,
                description TEXT,
                price INTEGER,
                price_text TEXT,
                location TEXT,
                city_code TEXT,
                category TEXT,
                seller_name TEXT,
                seller_type TEXT,
                attributes TEXT,
                images TEXT,
                image_count INTEGER,
                published_at TEXT,
                scraped_at TEXT,
                source_url TEXT,
                discovered_at TEXT,
                last_post_sort_date TEXT,
                crawl_status TEXT,
                raw_data TEXT,
                first_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                last_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS search_ads (
                search_id INTEGER NOT NULL,
                token TEXT NOT NULL,
                first_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                last_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (search_id, token),
                FOREIGN KEY (search_id) REFERENCES search_sources(id)
            );

            CREATE INDEX IF NOT EXISTS idx_ads_category ON ads(category);
            CREATE INDEX IF NOT EXISTS idx_ads_location ON ads(location);
            CREATE INDEX IF NOT EXISTS idx_search_ads_token ON search_ads(token);
            """
        )
        connection.commit()

    def get_or_create_search_source(self, name: str, url: str) -> int:
        connection = self._require_connection()
        row = connection.execute(
            "SELECT id FROM search_sources WHERE name = ?",
            (name,),
        ).fetchone()

        if row:
            search_id = int(row[0])
            connection.execute(
                "UPDATE search_sources SET url = ?, last_run_at = CURRENT_TIMESTAMP WHERE id = ?",
                (url, search_id),
            )
            connection.commit()
            return search_id

        cursor = connection.execute(
            "INSERT INTO search_sources(name, url, last_run_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
            (name, url),
        )
        connection.commit()
        return int(cursor.lastrowid)

    def get_existing_tokens(self, tokens: Iterable[str]) -> set[str]:
        token_list = list(dict.fromkeys(str(token) for token in tokens if token))
        if not token_list:
            return set()

        connection = self._require_connection()
        existing: set[str] = set()

        for start in range(0, len(token_list), 500):
            chunk = token_list[start : start + 500]
            placeholders = ",".join("?" for _ in chunk)
            rows = connection.execute(
                f"SELECT token FROM ads WHERE token IN ({placeholders})",
                chunk,
            ).fetchall()
            existing.update(str(row[0]) for row in rows)

        return existing

    def duplicate_ratio(
        self,
        tokens: Iterable[str],
        known_in_run: Iterable[str] = (),
    ) -> float:
        token_list = list(dict.fromkeys(str(token) for token in tokens if token))
        if not token_list:
            return 0.0

        existing = self.get_existing_tokens(token_list)
        existing.update(str(token) for token in known_in_run)
        duplicate_count = sum(token in existing for token in token_list)
        return duplicate_count / len(token_list)

    def save_search_capture(
        self,
        *,
        search_id: int,
        ads: Iterable[dict[str, Any]],
        new_tokens: set[str],
        capture_count: int,
        new_count: int,
        stop_ratio: float,
    ) -> None:
        """Persist one parsed search response in a single transaction.

        New ads are inserted/updated as one batch and every token is linked to
        its search source. The transaction is committed before the caller
        continues to the next scroll/capture.
        """
        connection = self._require_connection()

        unique_ads: dict[str, dict[str, Any]] = {}
        all_tokens: list[str] = []

        for ad in ads:
            token = str(ad.get("token") or "").strip()
            if not token:
                continue
            unique_ads[token] = ad
            all_tokens.append(token)

        unique_tokens = list(dict.fromkeys(all_tokens))

        with connection:
            new_rows = [
                self._ad_values(unique_ads[token])
                for token in unique_tokens
                if token in new_tokens
            ]

            if new_rows:
                connection.executemany(
                    """
                    INSERT INTO ads (
                        token, url, title, description, price, price_text,
                        location, city_code, category, seller_name, seller_type,
                        attributes, images, image_count, published_at, scraped_at,
                        source_url, discovered_at, last_post_sort_date, crawl_status,
                        raw_data
                    )
                    VALUES (
                        :token, :url, :title, :description, :price, :price_text,
                        :location, :city_code, :category, :seller_name, :seller_type,
                        :attributes, :images, :image_count, :published_at, :scraped_at,
                        :source_url, :discovered_at, :last_post_sort_date, :crawl_status,
                        :raw_data
                    )
                    ON CONFLICT(token) DO UPDATE SET
                        url = COALESCE(excluded.url, ads.url),
                        title = COALESCE(excluded.title, ads.title),
                        price = COALESCE(excluded.price, ads.price),
                        price_text = COALESCE(excluded.price_text, ads.price_text),
                        location = COALESCE(excluded.location, ads.location),
                        city_code = COALESCE(excluded.city_code, ads.city_code),
                        category = COALESCE(excluded.category, ads.category),
                        images = COALESCE(excluded.images, ads.images),
                        image_count = COALESCE(excluded.image_count, ads.image_count),
                        source_url = COALESCE(excluded.source_url, ads.source_url),
                        discovered_at = COALESCE(excluded.discovered_at, ads.discovered_at),
                        last_post_sort_date = COALESCE(excluded.last_post_sort_date, ads.last_post_sort_date),
                        crawl_status = COALESCE(excluded.crawl_status, ads.crawl_status),
                        raw_data = COALESCE(excluded.raw_data, ads.raw_data),
                        last_seen_at = CURRENT_TIMESTAMP
                    """,
                    new_rows,
                )

            connection.executemany(
                """
                INSERT INTO search_ads(search_id, token)
                VALUES (?, ?)
                ON CONFLICT(search_id, token) DO UPDATE SET
                    last_seen_at = CURRENT_TIMESTAMP
                """,
                [(search_id, token) for token in unique_tokens],
            )

            connection.execute(
                """
                UPDATE search_sources
                SET last_run_at = CURRENT_TIMESTAMP,
                    last_capture_count = ?,
                    last_new_count = ?,
                    last_stop_ratio = ?
                WHERE id = ?
                """,
                (capture_count, new_count, stop_ratio, search_id),
            )

    def upsert_ad(self, item: dict[str, Any]) -> None:
        connection = self._require_connection()
        token = item.get("token")
        if not token:
            return

        values = self._ad_values(item)
        connection.execute(
            """
            INSERT INTO ads (
                token, url, title, description, price, price_text,
                location, city_code, category, seller_name, seller_type,
                attributes, images, image_count, published_at, scraped_at,
                source_url, discovered_at, last_post_sort_date, crawl_status,
                raw_data
            )
            VALUES (
                :token, :url, :title, :description, :price, :price_text,
                :location, :city_code, :category, :seller_name, :seller_type,
                :attributes, :images, :image_count, :published_at, :scraped_at,
                :source_url, :discovered_at, :last_post_sort_date, :crawl_status,
                :raw_data
            )
            ON CONFLICT(token) DO UPDATE SET
                url = COALESCE(excluded.url, ads.url),
                title = COALESCE(excluded.title, ads.title),
                description = COALESCE(excluded.description, ads.description),
                price = COALESCE(excluded.price, ads.price),
                price_text = COALESCE(excluded.price_text, ads.price_text),
                location = COALESCE(excluded.location, ads.location),
                city_code = COALESCE(excluded.city_code, ads.city_code),
                category = COALESCE(excluded.category, ads.category),
                seller_name = COALESCE(excluded.seller_name, ads.seller_name),
                seller_type = COALESCE(excluded.seller_type, ads.seller_type),
                attributes = COALESCE(excluded.attributes, ads.attributes),
                images = COALESCE(excluded.images, ads.images),
                image_count = COALESCE(excluded.image_count, ads.image_count),
                published_at = COALESCE(excluded.published_at, ads.published_at),
                scraped_at = COALESCE(excluded.scraped_at, ads.scraped_at),
                source_url = COALESCE(excluded.source_url, ads.source_url),
                discovered_at = COALESCE(excluded.discovered_at, ads.discovered_at),
                last_post_sort_date = COALESCE(excluded.last_post_sort_date, ads.last_post_sort_date),
                crawl_status = COALESCE(excluded.crawl_status, ads.crawl_status),
                raw_data = COALESCE(excluded.raw_data, ads.raw_data),
                last_seen_at = CURRENT_TIMESTAMP
            """,
            values,
        )
        connection.commit()

    def link_ad_to_search(self, search_id: int, token: str) -> None:
        connection = self._require_connection()
        connection.execute(
            """
            INSERT INTO search_ads(search_id, token)
            VALUES (?, ?)
            ON CONFLICT(search_id, token) DO UPDATE SET
                last_seen_at = CURRENT_TIMESTAMP
            """,
            (search_id, str(token)),
        )
        connection.commit()

    def update_search_run(
        self,
        search_id: int,
        capture_count: int,
        new_count: int,
        stop_ratio: float,
    ) -> None:
        connection = self._require_connection()
        connection.execute(
            """
            UPDATE search_sources
            SET last_run_at = CURRENT_TIMESTAMP,
                last_capture_count = ?,
                last_new_count = ?,
                last_stop_ratio = ?
            WHERE id = ?
            """,
            (capture_count, new_count, stop_ratio, search_id),
        )
        connection.commit()

    @classmethod
    def _ad_values(cls, item: dict[str, Any]) -> dict[str, Any]:
        token = item.get("token")
        return {
            "token": str(token),
            "url": item.get("url") or f"https://divar.ir/v/{token}",
            "title": item.get("title"),
            "description": item.get("description"),
            "price": item.get("price"),
            "price_text": item.get("price_text"),
            "location": item.get("location") or item.get("city"),
            "city_code": item.get("city_code"),
            "category": item.get("category"),
            "seller_name": item.get("seller_name"),
            "seller_type": item.get("seller_type"),
            "attributes": cls._serialize(item.get("attributes")),
            "images": cls._serialize(item.get("images")),
            "image_count": item.get("image_count"),
            "published_at": item.get("published_at"),
            "scraped_at": item.get("scraped_at"),
            "source_url": item.get("source_url"),
            "discovered_at": item.get("discovered_at"),
            "last_post_sort_date": item.get("last_post_sort_date"),
            "crawl_status": item.get("crawl_status") or "new",
            "raw_data": cls._serialize(item.get("raw_data")),
        }

    @staticmethod
    def _serialize(value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False)
        return str(value)

    def _require_connection(self) -> sqlite3.Connection:
        if self.connection is None:
            self.connect()
        assert self.connection is not None
        return self.connection
