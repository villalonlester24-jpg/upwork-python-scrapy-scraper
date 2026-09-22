from urllib.parse import urlencode

from scrapy import Request


class ZenRowsMiddleware:
    """Route requests through the ZenRows scraping API.

    ZenRows handles proxy rotation, headless-browser rendering and CAPTCHA
    solving server-side. Defaults to adaptive ``mode=auto`` so it only pays for
    js_render/premium_proxy when the target actually needs them.
    """

    endpoint = 'https://api.zenrows.com/v1/?'

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings)

    def __init__(self, settings):
        self.api_key = settings.get('ZENROWS_API_KEY')
        self.enabled = settings.getbool('ZENROWS_ENABLED', True)
        self.mode = settings.get('ZENROWS_MODE') or ''
        self.js_render = settings.getbool('ZENROWS_JS_RENDER', True)
        self.premium_proxy = settings.getbool('ZENROWS_PREMIUM_PROXY', True)
        self.wait = settings.get('ZENROWS_WAIT') or ''
        self.proxy_country = settings.get('ZENROWS_PROXY_COUNTRY') or ''

    def _get_zenrows_url(self, request):
        mode = request.meta.get('zenrows_mode', self.mode)
        wait = request.meta.get('zenrows_wait', self.wait)
        payload = {'apikey': self.api_key, 'url': request.url}
        if mode:
            payload['mode'] = mode
        else:
            if self.js_render:
                payload['js_render'] = 'true'
            if self.premium_proxy:
                payload['premium_proxy'] = 'true'
            if self.js_render and wait:
                payload['wait'] = str(wait)
        if self.proxy_country:
            payload['proxy_country'] = self.proxy_country
        return self.endpoint + urlencode(payload)

    def process_request(self, request, spider):
        if not self.enabled or not self.api_key or self.endpoint in request.url:
            return None

        payload_url = self._get_zenrows_url(request)

        # Forward an optional Upwork session cookie so login-only data works.
        headers = {}
        cookie = request.headers.get('Cookie')
        if cookie:
            if isinstance(cookie, (list, tuple)):
                value = b'; '.join(cookie).decode()
            elif isinstance(cookie, bytes):
                value = cookie.decode()
            else:
                value = str(cookie)
            headers['Cookie'] = value
            payload_url += '&custom_headers=true'

        return request.replace(
            cls=Request, url=payload_url, meta=request.meta, headers=headers,
            dont_filter=True)
