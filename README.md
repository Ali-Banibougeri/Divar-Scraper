<div align="center">

# 🏙️ Divar Scraper

**کشف آگهی‌های دیوار با Selenium و ذخیره‌سازی پایدار در SQLite**

![Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python&logoColor=white)
![Scrapy](https://img.shields.io/badge/Scrapy-2.x-green?logo=scrapy)
![Selenium](https://img.shields.io/badge/Selenium-4.x-orange?logo=selenium&logoColor=white)
![Database](https://img.shields.io/badge/Database-SQLite-blue)

</div>

---

## معرفی

این نسخه از پروژه با Selenium صفحهٔ جست‌وجوی دیوار را باز می‌کند، پاسخ‌های شبکهٔ مربوط به جست‌وجو را از طریق Chrome DevTools Protocol (CDP) دریافت می‌کند، توکن آگهی‌ها را استخراج می‌کند و اطلاعات کشف‌شده را در SQLite ذخیره می‌کند.

> **محدودهٔ فعلی:** مسیر اصلی فعلی کشف آگهی‌ها و ذخیرهٔ داده‌های موجود در نتایج جست‌وجو است. دریافت کامل متن صفحهٔ آگهی، جزئیات فروشنده و دانلود فایل تصاویر، هنوز به‌عنوان مرحلهٔ جداگانهٔ استخراج جزئیات پیاده‌سازی نشده است.

## معماری فعلی

1. **Selenium / Chrome:** باز کردن صفحهٔ جست‌وجو و پیمایش نتایج.
2. **CDP:** دریافت پاسخ‌های شبکهٔ جست‌وجو.
3. **Parser:** استخراج اطلاعات موجود در ویجت‌های `POST_ROW` و حذف توکن‌های تکراری در هر پاسخ.
4. **SQLite:** ذخیرهٔ دسته‌ای اطلاعات هر Capture و ارتباط آگهی با منبع جست‌وجو.
5. **Scrapy Pipeline:** ذخیره‌سازی آیتم‌های سازگار با مدل داده در دیتابیس.

## ساختار مخزن

```text
Divar-Scraper/
├── divar_scrapy/
│   ├── browser.py           # Selenium و دریافت پاسخ‌های شبکه با CDP
│   ├── database.py          # طرح SQLite و عملیات ذخیره‌سازی
│   ├── items.py             # مدل آیتم‌های کشف و جزئیات
│   ├── middlewares.py       # میان‌افزارهای Scrapy
│   ├── parser.py             # تجزیهٔ پاسخ جست‌وجو
│   ├── pipelines.py         # ذخیره‌سازی آیتم‌ها
│   ├── settings.py          # تنظیمات اجرا
│   └── spiders/
│       └── divar.py         # اسپایدر اصلی
├── tests/
│   └── test_divar_search.py
├── chromedriver-win64/      # باید محلی تهیه شود؛ در مخزن نگهداری نمی‌شود
├── requirements.txt
├── scrapy.cfg
└── README.md
```

## پیش‌نیازها

- Python 3.11 یا 3.12 پیشنهاد می‌شود.
- Google Chrome نصب‌شده.
- ChromeDriver سازگار با نسخهٔ نصب‌شدهٔ Chrome.
- اتصال اینترنت برای دسترسی به دیوار.

## نصب و اجرا در ویندوز

دستورات زیر را در **PowerShell** و از پوشه‌ای که می‌خواهی پروژه در آن قرار بگیرد اجرا کن.

### ۱. دریافت پروژه

```powershell
git clone https://github.com/Ali-Banibougeri/Divar-Scraper.git
cd Divar-Scraper
```

اگر پروژه از قبل روی سیستم وجود دارد، به پوشهٔ پروژه برو و آخرین تغییرات را دریافت کن:

```powershell
git switch main
git pull origin main
```

### ۲. ساخت محیط مجازی و نصب کتابخانه‌ها

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

اگر PowerShell اجازهٔ فعال‌سازی محیط مجازی نداد، می‌توانی بدون فعال‌سازی نیز دستورها را از طریق پایتون محیط مجازی اجرا کنی:

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### ۳. نصب و تنظیم ChromeDriver

ChromeDriver را از منبع رسمی و متناسب با نسخهٔ Chrome نصب‌شده تهیه کن. در تنظیمات پیش‌فرض، مسیر آن چنین است:

```text
chromedriver-win64/chromedriver.exe
```

بررسی کن که فایل در مسیر مورد انتظار موجود باشد:

```powershell
Test-Path .\chromedriver-win64\chromedriver.exe
```

اگر خروجی `False` بود، درایور را در این مسیر قرار بده یا مقدار `DIVAR_CHROMEDRIVER_PATH` را در `divar_scrapy/settings.py` به مسیر واقعی فایل تغییر بده. مسیر درایور نباید به مخزن Git اضافه شود.

### ۴. بررسی شناسایی اسپایدر

```powershell
python -m scrapy list
```

خروجی باید شامل این نام باشد:

```text
divar
```

### ۵. اجرای جمع‌آوری

```powershell
python -m scrapy crawl divar -L INFO
```

در اجرا، گزارش‌های مراحل جست‌وجو، تعداد آگهی‌های کشف‌شده، نسبت تکراری‌ها و نتیجهٔ ذخیره‌سازی SQLite در ترمینال نمایش داده می‌شود.

## اجرای پروژه در Linux / macOS

```bash
git clone https://github.com/Ali-Banibougeri/Divar-Scraper.git
cd Divar-Scraper
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m scrapy list
python -m scrapy crawl divar -L INFO
```

برای Linux/macOS باید ChromeDriver متناسب با سیستم‌عامل نصب و مقدار `DIVAR_CHROMEDRIVER_PATH` در `divar_scrapy/settings.py` به مسیر صحیح آن تنظیم شود. مسیر پیش‌فرض فعلی پروژه برای ویندوز است.

## تنظیمات اصلی

تنظیمات در `divar_scrapy/settings.py` قرار دارند.

| تنظیم | کاربرد |
|---|---|
| `DIVAR_SEARCHES` | نام و آدرس صفحه‌های جست‌وجو |
| `DIVAR_CHROMEDRIVER_PATH` | مسیر فایل اجرایی ChromeDriver |
| `DIVAR_TARGET_URL` | نشانی endpoint شبکه‌ای که پاسخ جست‌وجو از آن دریافت می‌شود |
| `DIVAR_TARGET_TYPE` | نوع درخواست شبکه برای فیلتر کردن Capture |
| `DIVAR_MAX_CAPTURES` | حداکثر تعداد پاسخ‌های جست‌وجو برای هر منبع |
| `DIVAR_MAX_SCROLL_ATTEMPTS_PER_CAPTURE` | تعداد تلاش برای دریافت پاسخ جدید |
| `DIVAR_RESPONSE_TIMEOUT` | مهلت انتظار برای پاسخ شبکه |
| `DIVAR_HEADLESS` | اجرای Chrome بدون پنجرهٔ قابل مشاهده |
| `DIVAR_DUPLICATE_STOP_RATIO` | آستانهٔ نسبت توکن‌های تکراری برای توقف جست‌وجو |
| `DIVAR_SQLITE_DB_PATH` | مسیر دیتابیس SQLite |
| `CONCURRENT_REQUESTS_PER_DOMAIN` | سقف درخواست‌های هم‌زمان Scrapy |
| `DOWNLOAD_DELAY` | تأخیر ثابت درخواست‌های Scrapy |

توجه: تنظیمات هم‌زمانی Scrapy روی درخواست‌هایی اثر می‌گذارد که خود Scrapy ارسال می‌کند؛ مرحلهٔ Selenium و اسکرول مرورگر همچنان ترتیبی است.

## دیتابیس و محل داده‌ها

به‌صورت پیش‌فرض دیتابیس در مسیر زیر ساخته می‌شود:

```text
data/divar.db
```

جدول‌های اصلی:

- `ads`: اطلاعات آگهی‌های کشف‌شده و فیلدهای در نظر گرفته‌شده برای جزئیات.
- `search_sources`: منابع جست‌وجو و خلاصهٔ اجرای آن‌ها.
- `search_ads`: ارتباط بین آگهی‌ها و منابعی که آن‌ها را پیدا کرده‌اند.

SQLite با حالت WAL تنظیم شده است. اطلاعات هر Capture در یک تراکنش دسته‌ای ثبت می‌شوند تا ذخیره‌سازی قبل از ادامهٔ اسکرول انجام شود. فایل دیتابیس، فایل‌های WAL و داده‌های محلی عمداً نباید به Git اضافه شوند.

برای مشاهدهٔ دیتابیس می‌توان از [DB Browser for SQLite](https://sqlitebrowser.org/) یا افزونهٔ SQLite در VS Code استفاده کرد.

## تست

تست‌های موجود در پوشهٔ `tests/` قرار دارند. برای اجرای آن‌ها:

```powershell
python -m pip install pytest
python -m pytest -q
```

اجرای تست‌ها به‌تنهایی جای تست واقعی مرورگر و اتصال به دیوار را نمی‌گیرد؛ تست end-to-end را جداگانه و با نرخ درخواست مسئولانه انجام بده.

## رفع اشکال

| نشانه | بررسی پیشنهادی |
|---|---|
| `ChromeDriver not found` | مسیر `DIVAR_CHROMEDRIVER_PATH` و وجود فایل اجرایی را بررسی کن. |
| خطای Session یا ناسازگاری مرورگر | نسخهٔ Chrome و ChromeDriver باید سازگار باشند. |
| `No DIVAR_SEARCHES configured` | فهرست `DIVAR_SEARCHES` را در تنظیمات بررسی کن. |
| پاسخ جست‌وجو دریافت نمی‌شود | آدرس هدف، نوع درخواست و اتصال مرورگر به اینترنت را بررسی کن؛ ممکن است ساختار شبکهٔ دیوار تغییر کرده باشد. |
| دیتابیس ساخته نمی‌شود | دسترسی نوشتن به پوشهٔ پروژه و مقدار `DIVAR_SQLITE_DB_PATH` را بررسی کن. |
| دستور Scrapy اسپایدر را پیدا نمی‌کند | از ریشهٔ مخزن اجرا کن و ابتدا `python -m scrapy list` را بررسی کن. |

## وضعیت قابلیت‌ها

| قابلیت | وضعیت فعلی |
|---|---|
| باز کردن جست‌وجو با Selenium | پیاده‌سازی شده |
| دریافت پاسخ جست‌وجو از CDP | پیاده‌سازی شده |
| استخراج توکن و داده‌های موجود در ردیف آگهی | پیاده‌سازی شده |
| تشخیص توکن‌های تکراری | پیاده‌سازی شده |
| ذخیرهٔ SQLite و ارتباط با منبع جست‌وجو | پیاده‌سازی شده |
| استخراج کامل متن و جزئیات صفحهٔ هر آگهی | مرحلهٔ بعد |
| دریافت و ذخیرهٔ فایل تصاویر آگهی | مرحلهٔ بعد |
| تست خودکار end-to-end مرورگر | نیازمند اجرای مستقل |

## استفادهٔ مسئولانه

این پروژه برای یادگیری و پژوهش ساخته شده است. پیش از جمع‌آوری داده، شرایط استفاده و محدودیت‌های سرویس را بررسی کن؛ از ارسال درخواست‌های پرتعداد و دور زدن کنترل‌های دسترسی خودداری کن و اطلاعات را مطابق قوانین و حریم خصوصی کاربران مدیریت کن.

## مشارکت و مجوز

برای گزارش مشکل یا پیشنهاد تغییر، از [Issues](https://github.com/Ali-Banibougeri/Divar-Scraper/issues) و Pull Request استفاده کن. پروژه تحت مجوز [MIT](LICENSE) منتشر شده است.
