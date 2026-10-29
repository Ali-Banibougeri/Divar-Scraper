import scrapy


class AdsDashboardItem(scrapy.Item):
    """Lightweight ad data discovered from Divar search responses."""

    search_id = scrapy.Field()
    ad_id = scrapy.Field()
    token = scrapy.Field()
    url = scrapy.Field()

    title = scrapy.Field()
    price = scrapy.Field()
    price_text = scrapy.Field()
    location = scrapy.Field()
    city_code = scrapy.Field()

    category = scrapy.Field()
    last_post_sort_date = scrapy.Field()
    images = scrapy.Field()
    image_count = scrapy.Field()

    source_url = scrapy.Field()
    discovered_at = scrapy.Field()
    crawl_status = scrapy.Field()


class AdsDataItem(scrapy.Item):
    """Full ad data extracted from the ad detail page."""

    search_id = scrapy.Field()
    ad_id = scrapy.Field()
    token = scrapy.Field()
    url = scrapy.Field()

    title = scrapy.Field()
    description = scrapy.Field()

    price = scrapy.Field()
    location = scrapy.Field()
    category = scrapy.Field()

    seller_name = scrapy.Field()
    seller_type = scrapy.Field()

    attributes = scrapy.Field()
    images = scrapy.Field()

    published_at = scrapy.Field()
    scraped_at = scrapy.Field()

    raw_data = scrapy.Field()
