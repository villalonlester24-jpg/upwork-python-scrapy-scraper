import os
from pathlib import Path

# Load .env from the project root (if python-dotenv is installed).
try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent.parent / '.env')
except ImportError:
    pass


BOT_NAME = 'upwork'

SPIDER_MODULES = ['upwork.spiders']
NEWSPIDER_MODULE = 'upwork.spiders'


# Obey robots.txt rules
ROBOTSTXT_OBEY = False

## ZenRows scraping API (https://www.zenrows.com/register). No Upwork account
#  is required: ZenRows handles proxy rotation, headless rendering and CAPTCHAs.
ZENROWS_API_KEY = os.getenv('ZENROWS_API_KEY', '')
ZENROWS_ENABLED = os.getenv('ZENROWS_ENABLED', 'True').lower() == 'true'
# 'auto' = adaptive, but Upwork needs the results list to render, so by default
# we force js_render + premium_proxy and wait for the tiles. Leave empty to use
# the explicit flags below; set 'auto' only if you know it renders.
ZENROWS_MODE = os.getenv('ZENROWS_MODE', '')
ZENROWS_JS_RENDER = os.getenv('ZENROWS_JS_RENDER', 'True').lower() == 'true'
ZENROWS_PREMIUM_PROXY = os.getenv('ZENROWS_PREMIUM_PROXY', 'True').lower() == 'true'
# Extra milliseconds to let the JS-rendered job list load (requires js_render).
ZENROWS_WAIT = os.getenv('ZENROWS_WAIT', '5000')
ZENROWS_PROXY_COUNTRY = os.getenv('ZENROWS_PROXY_COUNTRY', '')

## Optional Upwork session cookie. Not needed for the public search spider.
UPWORK_COOKIE = os.getenv('UPWORK_COOKIE', '')

DOWNLOADER_MIDDLEWARES = {
    'upwork.middlewares.ZenRowsMiddleware': 725,
}

# ZenRows plans cap concurrency (the free plan is effectively 1). Raise this
# only if your plan allows more, otherwise you'll get HTTP 429.
CONCURRENT_REQUESTS = int(os.getenv('CONCURRENT_REQUESTS', '1'))
CONCURRENT_REQUESTS_PER_DOMAIN = CONCURRENT_REQUESTS

# ZenRows adds its own latency; no politeness delay needed.
DOWNLOAD_DELAY = float(os.getenv('DOWNLOAD_DELAY', '0'))

RETRY_TIMES = 2
DOWNLOAD_TIMEOUT = int(os.getenv('DOWNLOAD_TIMEOUT', '120'))
FEED_EXPORT_ENCODING = 'utf-8'
