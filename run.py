"""
Upwork Job Scraper - interactive launcher.

Run:
    py run.py

It asks a few simple questions (press Enter to accept the default shown in
brackets), then scrapes and prints the CSV location. It automatically uses
the project's venv, so there is nothing to activate.
"""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / 'data' / 'outputs'


def _venv_python():
    for candidate in (ROOT / 'venv' / 'Scripts' / 'python.exe',
                      ROOT / 'venv' / 'bin' / 'python'):
        if candidate.exists():
            return candidate
    return None


def _reexec_in_venv():
    venv_python = _venv_python()
    if venv_python and Path(sys.executable).resolve() != venv_python.resolve():
        raise SystemExit(subprocess.call(
            [str(venv_python), str(Path(__file__).resolve()), *sys.argv[1:]]))


_reexec_in_venv()

os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
os.environ.setdefault('SCRAPY_SETTINGS_MODULE', 'upwork.settings')

from scrapy.crawler import CrawlerProcess  # noqa: E402
from scrapy.utils.project import get_project_settings  # noqa: E402

from upwork.spiders.jobs_spider import UpworkJobsSpider  # noqa: E402
from upwork.spiders.search_spider import UpworkSearchSpider  # noqa: E402

RESET = '\033[0m'
BOLD = '\033[1m'
DIM = '\033[2m'
CYAN = '\033[96m'
GREEN = '\033[92m'
YELLOW = '\033[93m'

POSTED_OPTIONS = [(1, 'Any time', 0), (2, 'Last 7 days', 7),
                  (3, 'Last 3 days', 3), (4, 'Last 24 hours', 1)]

BANNER = r"""
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
"""


def _enable_ansi():
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
    if os.name != 'nt':
        return
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)
        mode = ctypes.c_uint32()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            kernel32.SetConsoleMode(handle, mode.value | 0x0004)
    except Exception:
        pass


def banner():
    print(f"{CYAN}{BANNER}{RESET}")
    print(f"{DIM}            Upwork job search  -  powered by ZenRows{RESET}")
    print()


def ask_number(prompt, default, minimum=1):
    while True:
        raw = input(f"{prompt}  {DIM}[{default}]{RESET}\n{DIM}    > {RESET}").strip()
        if raw == '':
            return default
        if raw.isdigit() and int(raw) >= minimum:
            return int(raw)
        print(f"{YELLOW}    Please type a number ({minimum} or more).{RESET}")


def ask_choice(prompt, options, default):
    print(prompt)
    for key, label in options:
        print(f"      {key}) {label}")
    valid = {str(key) for key, _ in options}
    while True:
        raw = input(f"{DIM}    Choose [{default}]: {RESET}").strip()
        if raw == '':
            return default
        if raw in valid:
            return int(raw)
        print(f"{YELLOW}    Please type a number from {options[0][0]} to {options[-1][0]}.{RESET}")


def main():
    _enable_ansi()
    banner()

    print(f"{BOLD} 1) Job keyword(s){RESET}  {DIM}[none]{RESET}")
    print(f"{DIM}    e.g. ai automation , python , web scraper"
          f"   (Enter = no keyword){RESET}")
    keyword = input(f"{DIM}    > {RESET}").strip()

    limit = ask_number(f"\n{BOLD} 2) How many jobs?{RESET}", 50)

    mode = ask_choice(
        f"\n{BOLD} 3) Search type{RESET}",
        [(1, 'Quick list    - fast, 1 request, basics'),
         (2, 'Full details  - slower, one request per job')],
        1)

    posted_choice = ask_choice(
        f"\n{BOLD} 4) Posted within{RESET}",
        [(key, label) for key, label, _ in POSTED_OPTIONS],
        1)
    days_posted = next(days for key, _, days in POSTED_OPTIONS if key == posted_choice)
    posted_label = next(label for key, label, _ in POSTED_OPTIONS if key == posted_choice)
    mode_label = 'Quick list' if mode == 1 else 'Full details'

    print()
    print(f"{CYAN}{'-' * 60}{RESET}")
    print(f"  Keyword : {keyword or '(none)'}")
    print(f"  Jobs    : {limit}")
    print(f"  Mode    : {mode_label}")
    print(f"  Posted  : {posted_label}")
    print(f"  Save to : data\\outputs\\")
    print(f"{CYAN}{'-' * 60}{RESET}")

    answer = input(f"{GREEN}  Start scraping? (Y/n): {RESET}").strip().lower()
    if answer not in ('', 'y', 'yes'):
        print('  Cancelled.')
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    before = set(OUTPUT_DIR.glob('*.csv'))
    errors = []

    settings = get_project_settings()
    settings.set('LOG_LEVEL', os.getenv('LOG_LEVEL', 'INFO'))
    process = CrawlerProcess(settings)

    kwargs = dict(query=keyword, limit=limit, days_posted=days_posted)
    if mode == 1:
        deferred = process.crawl(UpworkSearchSpider, **kwargs)
    else:
        deferred = process.crawl(UpworkJobsSpider, max_attempts=3, **kwargs)
    deferred.addErrback(lambda failure: errors.append(failure.getErrorMessage()))
    process.start()

    new_files = sorted(set(OUTPUT_DIR.glob('*.csv')) - before,
                       key=lambda path: path.stat().st_mtime)
    print()
    if new_files:
        print(f"{GREEN}{BOLD}  Done!{RESET} Scraped jobs saved to:")
        print(f"  {new_files[-1]}")
    else:
        print(f"{YELLOW}  Finished, but no CSV was created."
              f" Check the log above.{RESET}")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\n  Cancelled.')
