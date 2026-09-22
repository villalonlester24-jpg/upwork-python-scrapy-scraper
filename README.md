<div align="center">

```
  ██    ██ ██████  ██     ██  ██████  ██████  ██   ██
  ██    ██ ██   ██ ██     ██ ██    ██ ██   ██ ██  ██
  ██    ██ ██████  ██  █  ██ ██    ██ ██████  █████
  ██    ██ ██      ██ ███ ██ ██    ██ ██   ██ ██  ██
   ██████  ██       ███ ███   ██████  ██   ██ ██   ██

  ███████  ██████ ██████   █████  ██████  ███████ ██████
  ██      ██      ██   ██ ██   ██ ██   ██ ██      ██   ██
  ███████ ██      ██████  ███████ ██████  █████   ██████
       ██ ██      ██   ██ ██   ██ ██      ██      ██   ██
  ███████  ██████ ██   ██ ██   ██ ██      ███████ ██   ██
                                            // BY LES
```

### Scrapy + ZenRows job scraper for Upwork — **no account required**

[![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Scrapy](https://img.shields.io/badge/Scrapy-2.12-60A839?logo=scrapy&logoColor=white)](https://scrapy.org/)
[![ZenRows](https://img.shields.io/badge/Powered%20by-ZenRows-6C5CE7)](https://www.zenrows.com/)
[![Platform](https://img.shields.io/badge/Platform-Windows-0078D6?logo=windows&logoColor=white)](#)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](#license)

Scrape Upwork job listings from the public search page — Cloudflare handled by
ZenRows, results saved to CSV. No login, no cookies, no browser automation.

</div>

---

## Features

| | |
| --- | --- |
| **Account-free** | Reads the public search results — no Upwork login needed |
| **Anti-bot** | ZenRows rotates proxies + renders JS to get past Cloudflare |
| **Fast list mode** | Up to **50 jobs in one request** (~20s) |
| **Deep detail mode** | Optional full job + client data (one request per job) |
| **Interactive CLI** | A friendly menu with defaults — just press Enter |
| **CSV output** | Timestamped exports in `data/outputs/` |

---

## Quick Start

### 1. Install

```powershell
git clone https://github.com/<you>/upwork-python-scrapy-scraper.git
cd upwork-python-scrapy-scraper
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 2. Add your ZenRows key

Create `.env` (or copy `.env.example`) and paste your key from
[zenrows.com](https://www.zenrows.com/register):

```ini
ZENROWS_API_KEY=your-key-here
ZENROWS_WAIT=5000
CONCURRENT_REQUESTS=1
```

### 3. Run

```powershell
py run.py
```

That's it. The menu appears and you press **Enter** through the defaults:

```text
 1) Job keyword(s)  [none]        ← Enter = no keyword
 2) How many jobs?  [50]
 3) Search type     [1]  Quick list
 4) Posted within   [1]  Any time
 Start scraping? (Y/n):            ← Enter = yes
```

Results land in `data\outputs\`.

---

## Two Spiders

| Spider | Menu option | Requests | Speed (10 jobs) | What you get |
| --- | --- | --- | --- | --- |
| `upwork_search` | Quick list | 1 per 50 jobs | ~20s | title, posted, type, level, duration, description snippet, skills |
| `upwork_jobs` | Full details | 1 per job | ~10–20 min | all of the above + budget, category, applicants, connects, client spend/hires/rating, full description |

<details>
<summary><b>CSV columns — Quick list</b></summary>

`title, url, job_id, posted, job_type, experience_level, duration, est_time,
hours_per_week, description, skills, search_page`

</details>

<details>
<summary><b>CSV columns — Full details (subset)</b></summary>

`title, description, type, hourly_min, hourly_max, fixed_budget_amount,
currency, duration, level, skills, category, categoryGroup_name,
qualifications, questions, applicants, connects_required, ts_create,
ts_publish, client_country, client_company_size, client_industry,
client_rating, client_reviews, client_hires, client_total_spent,
payment_verified, phone_verified, buyer_hire_rate_pct, job_id, url`

</details>

---

## Usage

### Interactive (recommended)

```powershell
py run.py
```

### Raw Scrapy commands

```powershell
# quick list, custom query, up to 50
.\venv\Scripts\python.exe -m scrapy crawl upwork_search -a query="ai automation" -a limit=50

# full details for 10 jobs
.\venv\Scripts\python.exe -m scrapy crawl upwork_jobs -a limit=10
```

### Edit saved searches

Search criteria live in `data/inputs/default_upwork_search.json`
(`query`, `search_any`, `category`, `hourly_min/max`, `days_posted`, `limit`, ...).

---

## How It Works

```text
  run.py  ──►  Scrapy  ──►  ZenRowsMiddleware  ──►  ZenRows API  ──►  Upwork
                                    │                                  │
                                    └────────  rendered HTML  ◄────────┘
                                                    │
                                    parse cards / details ──► CSV
```

- **ZenRows** does the hard part: rotating proxies, a real headless browser,
  and CAPTCHA/Cloudflare handling. We just append `?url=...` to their API.
- **`upwork_search`** parses `article.job-tile` cards on the public search page.
- **`upwork_jobs`** additionally parses each job's `__NUXT_DATA__` JSON via
  `attr_extractor.py`, repaired for the current layout by `enrich.py`.

---

## Project Structure

```text
upwork-python-scrapy-scraper/
├── run.py                     # interactive launcher (py run.py)
├── scrapy.cfg
├── requirements.txt
├── .env.example
├── data/
│   ├── inputs/default_upwork_search.json
│   └── outputs/               # timestamped CSV results
└── upwork/
    ├── settings.py            # ZenRows + concurrency config
    ├── middlewares.py         # ZenRows API middleware
    ├── search_params.py       # build the Upwork search URL from JSON
    ├── attr_extractor.py      # detail-page field extractor
    ├── enrich.py              # detail-page field fixes
    └── spiders/
        ├── search_spider.py   # upwork_search (quick list)
        └── jobs_spider.py     # upwork_jobs (full details)
```

---

## Notes & Caveats

- **No login.** ZenRows is a proxy/rendering API, so it cannot sign in. The
  search list needs no account; login-only fields require an exported session
  cookie in `UPWORK_COOKIE`.
- **Credits.** ZenRows bills per successful request (base 1, `js_render` 5,
  `premium_proxy` 10). A 50-job list scrape is **one** request.
- **Concurrency.** Keep `CONCURRENT_REQUESTS=1` on the free plan; higher causes
  HTTP 429.
- **`ZENROWS_MODE=auto` is not used by default** — it doesn't wait for Upwork's
  JS results. We force `js_render + premium_proxy + wait=5000` instead.

---

## Credits

- Inspired by [calebmwelsh/Upwork-Job-Scraper](https://github.com/calebmwelsh/Upwork-Job-Scraper)
  and [roperi/UpworkScraper](https://github.com/roperi/UpworkScraper).
- Built with [Scrapy](https://github.com/scrapy/scrapy) and
  [ZenRows](https://www.zenrows.com/).

## License

MIT — see [LICENSE](LICENSE).
