from pathlib import Path


BOT_NAME = "divar_scrapy"
SPIDER_MODULES = ["divar_scrapy.spiders"]
NEWSPIDER_MODULE = "divar_scrapy.spiders"
ADDONS = {}


# ============================================================
# DIVAR SEARCH CONFIGURATION
# ============================================================

DIVAR_SEARCHES = [
    {
        "name": "auto_iran",
        "url": "https://divar.ir/s/iran/auto?recent_ads=3h",
    },
]

# مسیر واقعی chromedriver.exe روی سیستم شما
DIVAR_CHROMEDRIVER_PATH = r"chromedriver-win64\chromedriver.exe"

DIVAR_TARGET_URL = "https://api.divar.ir/v8/postlist/w/search"
DIVAR_TARGET_TYPE = "XHR"

# حداکثر تعداد Search Response برای هر URL
DIVAR_MAX_CAPTURES = 100

# حداکثر تلاش برای رسیدن به Response جدید در هر Capture
DIVAR_MAX_SCROLL_ATTEMPTS_PER_CAPTURE = 10

DIVAR_RESPONSE_TIMEOUT = 15
DIVAR_POLL_INTERVAL = 0.1

DIVAR_RANDOM_WAIT_AFTER_SCROLL = (2.0, 5.0)
DIVAR_RANDOM_WAIT_AFTER_CLICK = (3.0, 6.0)
DIVAR_INITIAL_PAGE_WAIT = (4.0, 6.0)

DIVAR_HEADLESS = True

# وقتی درصد توکن‌های تکراری این مقدار یا بیشتر شود، همان Search متوقف می‌شود.
DIVAR_DUPLICATE_STOP_RATIO = 0.90


# ============================================================
# SQLITE
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DIVAR_SQLITE_DB_PATH = PROJECT_ROOT / "data" / "divar.db"


# ============================================================
# SCRAPY
# ============================================================

CONCURRENT_REQUESTS_PER_DOMAIN = 8
DOWNLOAD_DELAY = 0
ROBOTSTXT_OBEY = True

ITEM_PIPELINES = {
    "divar_scrapy.pipelines.DivarScrapyPipeline": 300,
}

FEED_EXPORT_ENCODING = "utf-8"
