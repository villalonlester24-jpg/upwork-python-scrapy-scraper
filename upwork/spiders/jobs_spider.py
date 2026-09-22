"""
Upwork job spider.

Crawls the Upwork job search using the parameters in a JSON config, follows
each job tile to its detail page, and extracts the full set of job/client
attributes. All traffic goes through the ScrapeOps proxy.

Usage:
    scrapy crawl upwork_jobs
    scrapy crawl upwork_jobs -a limit=20
    scrapy crawl upwork_jobs -a search_params=data/inputs/my_search.json
    scrapy crawl upwork_jobs -a render_js=false
"""

import json
import re
from math import ceil
from pathlib import Path

import scrapy

from upwork.attr_extractor import extract_job_attributes
from upwork.enrich import enrich_job_attrs
from upwork.search_params import build_upwork_search_url, normalize_search_params

JOB_ID_RE = re.compile(r'~([0-9a-zA-Z]+)')
DEFAULT_SEARCH_PARAMS = 'data/inputs/default_upwork_search.json'


class UpworkJobsSpider(scrapy.Spider):
    name = 'upwork_jobs'
    buffer = 5

    custom_settings = {
        'FEEDS': {
            'data/outputs/upwork_jobs_%(time)s.csv': {'format': 'csv'},
        },
    }

    def __init__(self, search_params=DEFAULT_SEARCH_PARAMS, limit=None,
                 render_js=None, residential=None, max_attempts=3,
                 query=None, days_posted=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.search_params_path = search_params
        self.limit_override = int(limit) if limit else None
        self._render_js = self._as_bool(render_js)
        self._residential = self._as_bool(residential)
        self.max_attempts = max(1, int(max_attempts))
        self.query_override = query
        self.days_posted = int(days_posted) if days_posted is not None else None
        self.seen_jobs = set()
        self.scheduled_jobs = 0

    def _apply_days_posted(self, params):
        """0 = any time (drop the filter); N>0 = last N days."""
        if self.days_posted is None:
            return
        if self.days_posted > 0:
            params['days_posted'] = self.days_posted
        else:
            params.pop('days_posted', None)

    @staticmethod
    def _as_bool(value):
        if value is None:
            return None
        return str(value).lower() in ('1', 'true', 'yes', 'y', 'on')

    def load_search_params(self):
        paths = [
            Path(self.search_params_path),
            Path(__file__).resolve().parent.parent.parent / self.search_params_path,
        ]
        for path in paths:
            if path.exists():
                with path.open(encoding='utf-8') as handle:
                    return json.load(handle)
        self.logger.error("Search params file not found: %s", self.search_params_path)
        return {}

    def _request(self, url, callback, meta):
        meta = dict(meta)
        meta.setdefault('sops_render_js', self.settings.getbool('SOPS_RENDER_JS', True))
        meta.setdefault('sops_residential', self.settings.getbool('SOPS_RESIDENTIAL', False))
        if self._render_js is not None:
            meta['sops_render_js'] = self._render_js
        if self._residential is not None:
            meta['sops_residential'] = self._residential

        headers = {}
        cookie = self.settings.get('UPWORK_COOKIE')
        if cookie:
            headers['Cookie'] = cookie
            meta['sops_keep_headers'] = True

        return scrapy.Request(
            url, callback=callback, meta=meta, headers=headers,
            errback=self.on_error, dont_filter=True)

    def _next_attempt(self, meta, target, callback, reason):
        """Return an escalated retry request, or None when attempts are spent."""
        attempt = meta.get('attempt', 1)
        if attempt >= self.max_attempts:
            self.logger.error("Giving up on %s after %s attempt(s): %s",
                              target, attempt, reason)
            return None
        new_meta = dict(meta)
        new_meta['attempt'] = attempt + 1
        new_meta['sops_residential'] = not meta.get('sops_residential', False)
        self.logger.warning("Attempt %s/%s failed for %s (%s); retrying (residential=%s).",
                            attempt, self.max_attempts, target, reason,
                            new_meta['sops_residential'])
        return self._request(target, callback, new_meta)

    def on_error(self, failure):
        """Retry requests that failed at the network/proxy layer (e.g. 5xx)."""
        meta = dict(failure.request.meta)
        target = meta.get('job_url') or meta.get('search_url') or failure.request.url
        callback = self.parse_job if meta.get('job_url') else self.parse_search_results
        retry = self._next_attempt(meta, target, callback, f"download error: {failure.value}")
        if retry is not None:
            yield retry

    def start_requests(self):
        if self.query_override is not None:
            params = {'query': self.query_override} if self.query_override else {}
        else:
            params = self.load_search_params()
            if not params:
                return
        if self.limit_override:
            params['limit'] = self.limit_override
        self._apply_days_posted(params)

        credentials_provided = bool(self.settings.get('UPWORK_COOKIE'))
        normalized, limit = normalize_search_params(
            params, credentials_provided, buffer=self.buffer)
        search_url = build_upwork_search_url(normalized)

        try:
            per_page = int(normalized.get('per_page', 10))
        except (TypeError, ValueError):
            per_page = 10
        per_page = per_page or 10
        pages_needed = max(1, ceil(limit / per_page))

        self.logger.info("Search URL: %s", search_url)
        self.logger.info("Scraping up to %s jobs across %s page(s).", limit - self.buffer, pages_needed)

        for page in range(1, pages_needed + 1):
            url = search_url if page == 1 else f"{search_url}&page={page}"
            yield self._request(
                url,
                self.parse_search_results,
                {'page': page, 'limit': limit, 'search_url': url},
            )

    def parse_search_results(self, response):
        search_url = response.meta.get('search_url', response.url)
        job_urls = [] if self.is_challenge(response.text) else self.parse_job_urls(response.text)

        if not job_urls:
            retry = self._next_attempt(
                response.meta, search_url, self.parse_search_results,
                'challenge/no job tiles')
            if retry is not None:
                yield retry
            return

        self.logger.info("Page %s: found %s job links.", response.meta['page'], len(job_urls))
        max_jobs = response.meta.get('limit', 0)
        for job_url in job_urls:
            if max_jobs and self.scheduled_jobs >= max_jobs:
                break
            if job_url in self.seen_jobs:
                continue
            self.seen_jobs.add(job_url)
            self.scheduled_jobs += 1
            yield self._request(
                job_url,
                self.parse_job,
                {'page': response.meta['page'], 'job_url': job_url},
            )

    @staticmethod
    def is_challenge(html):
        match = re.search(r'<title[^>]*>(.*?)</title>', html, re.S | re.I)
        title = match.group(1).strip().lower() if match else ''
        return ('just a moment' in title or 'challenge' in title
                or 'attention required' in title)

    @staticmethod
    def parse_job_urls(html):
        selector = scrapy.Selector(text=html)

        # Current Upwork search tiles carry no href; the job cipher is derived
        # from the tile's uid as "~02<uid>" (verified against the page payload).
        uids = selector.css('article.job-tile::attr(data-ev-job-uid)').getall()
        if not uids:
            uids = selector.css('[data-ev-job-uid]::attr(data-ev-job-uid)').getall()

        job_urls = [f"https://www.upwork.com/jobs/~02{uid}" for uid in dict.fromkeys(uids)]

        if not job_urls:
            # Fallback: raw ciphertexts embedded in the page payload.
            for cipher in dict.fromkeys(re.findall(r'~[0-9a-f]{20,}', html)):
                job_urls.append(f"https://www.upwork.com/jobs/{cipher}")
        return job_urls

    def parse_job(self, response):
        job_url = response.meta.get('job_url', response.url)
        no_data = 'id="__NUXT_DATA__"' not in response.text
        if self.is_challenge(response.text) or no_data:
            retry = self._next_attempt(
                response.meta, job_url, self.parse_job, 'challenge/no data')
            if retry is not None:
                yield retry
            return

        attrs = extract_job_attributes(response.text)
        attrs = enrich_job_attrs(response.text, attrs)
        match = JOB_ID_RE.search(job_url)
        attrs['job_id'] = match.group(1) if match else ''
        attrs['url'] = job_url
        attrs['search_page'] = response.meta.get('page')
        yield attrs
