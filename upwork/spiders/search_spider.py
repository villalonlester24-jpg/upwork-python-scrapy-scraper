"""
Upwork job-search spider (list only, no account required).

Scrapes the public search results page and extracts one row per job card:
posted date, title, type, experience level, duration, description and skills.
Because it reads only the search results it needs a single request per 50 jobs.

Usage:
    scrapy crawl upwork_search
    scrapy crawl upwork_search -a query="ai automation" -a limit=50
    scrapy crawl upwork_search -a search_params=data/inputs/my_search.json
"""

import json
from math import ceil
from pathlib import Path

import scrapy

from upwork.search_params import build_upwork_search_url, normalize_search_params

DEFAULT_SEARCH_PARAMS = 'data/inputs/default_upwork_search.json'
PER_PAGE = 50


class UpworkSearchSpider(scrapy.Spider):
    name = 'upwork_search'

    custom_settings = {
        'FEEDS': {
            'data/outputs/upwork_search_%(time)s.csv': {'format': 'csv'},
        },
    }

    def __init__(self, search_params=DEFAULT_SEARCH_PARAMS, query=None, limit=50,
                 mode=None, days_posted=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.search_params_path = search_params
        self.query_override = query
        self.limit_override = int(limit) if limit else None
        self.mode_override = mode
        self.days_posted = int(days_posted) if days_posted is not None else None
        self.seen_jobs = set()
        self.item_count = 0

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
        if self.mode_override is not None:
            meta['zenrows_mode'] = self.mode_override
        headers = {}
        cookie = self.settings.get('UPWORK_COOKIE')
        if cookie:
            headers['Cookie'] = cookie
        return scrapy.Request(
            url, callback=callback, meta=meta, headers=headers, dont_filter=True)

    def start_requests(self):
        if self.query_override is not None:
            # Explicit query override (empty string = no keyword at all).
            params = {'query': self.query_override} if self.query_override else {}
        else:
            params = self.load_search_params()
            if not params:
                return
        if self.limit_override:
            params['limit'] = self.limit_override
        self._apply_days_posted(params)

        # Public data only, so the login-gated filters are left out.
        normalized, limit = normalize_search_params(
            params, credentials_provided=False, buffer=0)
        normalized['per_page'] = str(PER_PAGE)
        search_url = build_upwork_search_url(normalized)

        pages_needed = max(1, ceil(limit / PER_PAGE))
        self.logger.info("Search URL: %s", search_url)
        self.logger.info("Scraping up to %s jobs across %s page(s).", limit, pages_needed)

        for page in range(1, pages_needed + 1):
            url = search_url if page == 1 else f"{search_url}&page={page}"
            yield self._request(
                url, self.parse_search,
                {'page': page, 'search_url': url, 'limit': limit})

    def parse_search(self, response):
        cards = response.css('article.job-tile')
        if not cards:
            if not response.meta.get('retried'):
                self.logger.warning("No job cards on page %s; retrying with full "
                                    "render.", response.meta['page'])
                meta = dict(response.meta)
                meta['retried'] = True
                meta['zenrows_mode'] = ''  # force js_render + premium_proxy
                yield self._request(response.meta['search_url'], self.parse_search, meta)
            else:
                self.logger.error("No job cards after retry: %s",
                                  response.meta.get('search_url'))
            return

        self.logger.info("Page %s: %s cards.", response.meta['page'], len(cards))
        max_jobs = response.meta.get('limit', 0)
        for card in cards:
            if max_jobs and self.item_count >= max_jobs:
                break
            uid = card.attrib.get('data-ev-job-uid')
            if uid in self.seen_jobs:
                continue
            self.seen_jobs.add(uid)
            self.item_count += 1

            duration = self._text(card, '[data-test="duration-label"]')
            est_time, hours_per_week = self._split_duration(duration)
            skills = [
                text for text in (
                    self._text(token, '') for token in card.css('[data-test="token"]')
                ) if text
            ]

            yield {
                'title': self._text(card, '[data-test="job-tile-title-link"]'),
                'url': f"https://www.upwork.com/jobs/~02{uid}" if uid else '',
                'job_id': uid,
                'posted': self._text(card, '[data-test*="job-pub"]'),
                'job_type': self._text(card, '[data-test="job-type-label"]'),
                'experience_level': self._text(card, '[data-test="experience-level"]'),
                'duration': duration,
                'est_time': est_time,
                'hours_per_week': hours_per_week,
                'description': (self._text(card, 'p.rr-mask')
                                or self._text(card, '.air3-line-clamp-wrapper p')),
                'skills': skills,
                'search_page': response.meta['page'],
            }

    def _apply_days_posted(self, params):
        """0 = any time (drop the filter); N>0 = last N days."""
        if self.days_posted is None:
            return
        if self.days_posted > 0:
            params['days_posted'] = self.days_posted
        else:
            params.pop('days_posted', None)

    @staticmethod
    def _text(node, selector):
        if selector:
            selected = node.css(selector)
            if not selected:
                return ''
        else:
            selected = node
        return ' '.join(' '.join(selected.xpath('.//text()').getall()).split())

    @staticmethod
    def _split_duration(value):
        if 'Est. time:' in value:
            rest = value.split('Est. time:', 1)[1]
            parts = [part.strip() for part in rest.split(',', 1)]
            return parts[0], (parts[1] if len(parts) > 1 else '')
        return value, ''
