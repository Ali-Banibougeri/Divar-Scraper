from itemadapter import ItemAdapter

from divar_scrapy.database import SQLiteDatabase
from divar_scrapy.items import AdsDashboardItem, AdsDataItem


class DivarScrapyPipeline:
    def open_spider(self, spider) -> None:
        self.db = SQLiteDatabase(spider.settings.get("DIVAR_SQLITE_DB_PATH"))
        self.db.connect()

    def close_spider(self, spider) -> None:
        self.db.close()

    def process_item(self, item, spider):
        # Search-discovery items are already persisted in one transaction per
        # capture by DivarSpider. Do not write them again one-by-one here.
        if isinstance(item, AdsDashboardItem):
            return item

        data = ItemAdapter(item).asdict()
        self.db.upsert_ad(data)

        search_id = data.get("search_id")
        token = data.get("token") or data.get("ad_id")
        if search_id is not None and token:
            self.db.link_ad_to_search(int(search_id), str(token))

        return item
