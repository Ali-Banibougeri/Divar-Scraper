import os
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
        "url": "https://divar.ir/s/iran/auto",
    },
]

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Override this value with an absolute path if ChromeDriver is elsewhere.
# Windows default: <project root>/chromedriver-win64/chromedriver.exe
# Linux/macOS users should set this to their platform-specific executable.
DIVAR_CHROMEDRIVER_PATH = Path(
    os.environ.get(
        "DIVAR_CHROMEDRIVER_PATH",
        str(PROJECT_ROOT / "chromedriver-win64" / "chromedriver.exe"),
    )
).expanduser().resolve()

DIVAR_TARGET_URL = "https://api.divar.ir/v8/postlist/w/search"
DIVAR_TARGET_TYPE = "XHR"

# Maximum number of search responses captured per configured search URL.
DIVAR_MAX_CAPTURES = 100

# Maximum attempts to find a new response for each capture.
DIVAR_MAX_SCROLL_ATTEMPTS_PER_CAPTURE = 10

DIVAR_RESPONSE_TIMEOUT = 15
DIVAR_POLL_INTERVAL = 0.1

DIVAR_RANDOM_WAIT_AFTER_SCROLL = (2.0, 5.0)
DIVAR_RANDOM_WAIT_AFTER_CLICK = (3.0, 6.0)
DIVAR_NO_SCROLL_WAIT = (3.0, 5.0)
DIVAR_INITIAL_PAGE_WAIT = (4.0, 6.0)

DIVAR_HEADLESS = True

# Stop a search when this fraction of tokens in a capture are duplicates.
DIVAR_DUPLICATE_STOP_RATIO = 0.90


# ============================================================
# SQLITE
# ============================================================

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
