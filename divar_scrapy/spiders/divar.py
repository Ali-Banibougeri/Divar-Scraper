from datetime import datetime

import scrapy

from divar_scrapy.browser import BrowserSession
from divar_scrapy.database import SQLiteDatabase
from divar_scrapy.items import AdsDashboardItem
from divar_scrapy.parser import parse_search_response


class DivarSpider(scrapy.Spider):
    name = "divar"
    allowed_domains = ["divar.ir"]

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super().from_crawler(crawler, *args, **kwargs)
        spider.db = SQLiteDatabase(
            crawler.settings.get("DIVAR_SQLITE_DB_PATH")
        )
        spider.db.connect()
        return spider

    def closed(self, reason):
        if hasattr(self, "db"):
            self.db.close()

    async def start(self):
        """Run Selenium-based search discovery without creating dummy HTTP requests."""
        for item in self._discover_ads_from_searches():
            yield item

    def _discover_ads_from_searches(self):
        searches = self.settings.get("DIVAR_SEARCHES", [])
        stop_ratio = float(
            self.settings.get("DIVAR_DUPLICATE_STOP_RATIO", 0.90)
        )

        if not searches:
            self.logger.warning("No DIVAR_SEARCHES configured.")
            return

        for search in searches:
            name = str(search.get("name", "")).strip()
            search_url = str(search.get("url", "")).strip()

            if not name or not search_url:
                self.logger.warning(
                    "Skipping invalid search config: %r",
                    search,
                )
                continue

            search_id = self.db.get_or_create_search_source(
                name=name,
                url=search_url,
            )

            self.logger.info(
                "Starting search: %s | %s",
                name,
                search_url,
            )

            session = BrowserSession(
                search_url=search_url,
                driver_path=self.settings.get("DIVAR_CHROMEDRIVER_PATH"),
                target_url=self.settings.get("DIVAR_TARGET_URL"),
                target_type=self.settings.get("DIVAR_TARGET_TYPE", "XHR"),
                max_captures=int(
                    self.settings.get("DIVAR_MAX_CAPTURES", 100)
                ),
                max_scroll_attempts_per_capture=int(
                    self.settings.get(
                        "DIVAR_MAX_SCROLL_ATTEMPTS_PER_CAPTURE",
                        10,
                    )
                ),
                response_timeout=int(
                    self.settings.get("DIVAR_RESPONSE_TIMEOUT", 15)
                ),
                poll_interval=float(
                    self.settings.get("DIVAR_POLL_INTERVAL", 0.1)
                ),
                random_wait_after_scroll=tuple(
                    self.settings.get(
                        "DIVAR_RANDOM_WAIT_AFTER_SCROLL",
                        (2.0, 5.0),
                    )
                ),
                random_wait_after_click=tuple(
                    self.settings.get(
                        "DIVAR_RANDOM_WAIT_AFTER_CLICK",
                        (3.0, 6.0),
                    )
                ),
                no_scroll_wait=tuple(
                    self.settings.get(
                        "DIVAR_NO_SCROLL_WAIT",
                        (3.0, 5.0),
                    )
                ),
                initial_page_wait=tuple(
                    self.settings.get(
                        "DIVAR_INITIAL_PAGE_WAIT",
                        (4.0, 6.0),
                    )
                ),
                headless=self.settings.getbool("DIVAR_HEADLESS", True),
            )

            known_in_run: set[str] = set()
            capture_count = 0
            discovered_new_count = 0
            last_ratio = 0.0

            try:
                for capture_count, request_data in enumerate(
                    session.iter_captures(),
                    start=1,
                ):
                    response_data = request_data.get("response", {}).get(
                        "data",
                        {},
                    )
                    ads = parse_search_response(response_data)
                    tokens = list(
                        dict.fromkeys(
                            str(ad["token"])
                            for ad in ads
                            if ad.get("token")
                        )
                    )

                    if not tokens:
                        self.logger.info(
                            "Search %s | capture %s: no POST_ROW ads found.",
                            name,
                            capture_count,
                        )
                        continue

                    database_known = self.db.get_existing_tokens(tokens)
                    effective_known = database_known | known_in_run
                    duplicate_count = sum(
                        token in effective_known
                        for token in tokens
                    )
                    last_ratio = duplicate_count / len(tokens)
                    new_count = len(tokens) - duplicate_count
                    discovered_new_count += new_count

                    self.logger.info(
                        "Search %s | capture=%s | ads=%s | new=%s | duplicate_ratio=%.2f%%",
                        name,
                        capture_count,
                        len(tokens),
                        new_count,
                        last_ratio * 100,
                    )

                    discovered_at = datetime.now().isoformat(timespec="seconds")
                    source_url = search_url
                    new_tokens = {
                        token
                        for token in tokens
                        if token not in effective_known
                    }

                    # Persist this capture immediately as one SQLite transaction.
                    # The next scroll does not start until this commit succeeds.
                    capture_ads = []
                    for ad in ads:
                        capture_ad = dict(ad)
                        capture_ad["source_url"] = source_url
                        capture_ad["discovered_at"] = discovered_at
                        capture_ad["crawl_status"] = (
                            "new" if capture_ad.get("token") in new_tokens else "known"
                        )
                        capture_ads.append(capture_ad)

                    self.db.save_search_capture(
                        search_id=search_id,
                        ads=capture_ads,
                        new_tokens=new_tokens,
                        capture_count=capture_count,
                        new_count=new_count,
                        stop_ratio=last_ratio,
                    )
                    self.logger.info(
                        "SQLite commit complete: %s | capture=%s | new=%s",
                        name,
                        capture_count,
                        new_count,
                    )

                    for ad in capture_ads:
                        token = str(ad["token"])
                        is_known = token not in new_tokens
                        known_in_run.add(token)

                        yield AdsDashboardItem(
                            search_id=search_id,
                            ad_id=token,
                            token=token,
                            url=f"https://divar.ir/v/{token}",
                            title=ad.get("title"),
                            price=ad.get("price"),
                            price_text=ad.get("price_text"),
                            location=ad.get("city"),
                            city_code=ad.get("city_code"),
                            category=ad.get("category"),
                            last_post_sort_date=ad.get(
                                "last_post_sort_date"
                            ),
                            images=ad.get("images"),
                            image_count=ad.get("image_count"),
                            source_url=source_url,
                            discovered_at=discovered_at,
                            crawl_status="known" if is_known else "new",
                        )

                    if last_ratio >= stop_ratio:
                        self.logger.info(
                            "Stopping search %s: duplicate ratio %.2f%% >= %.2f%%.",
                            name,
                            last_ratio * 100,
                            stop_ratio * 100,
                        )
                        break

            except Exception:
                self.logger.exception(
                    "Search failed: %s | %s",
                    name,
                    search_url,
                )
            finally:
                self.db.update_search_run(
                    search_id=search_id,
                    capture_count=capture_count,
                    new_count=discovered_new_count,
                    stop_ratio=last_ratio,
                )
