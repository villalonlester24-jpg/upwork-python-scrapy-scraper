"""
Light post-processing for Upwork job attributes.

The ported ``attr_extractor`` was written for an older Upwork layout. On the
current site it can pick up content from the "Explore similar jobs" tiles
(wrong title/skills) and occasionally capture CSS instead of a duration value.
This module repairs those specific fields using stable, page-level signals.
"""

import re

from bs4 import BeautifulSoup

CSS_JUNK = re.compile(r'[{}\[\];]|:(hover|active|focus|root|before|after)\b|--[a-z-]+\s*:')
DURATION_RE = re.compile(
    r'(More than 6 months|3 to 6 months|1 to 3 months|Less than 1 month|Less than a month)',
    re.IGNORECASE,
)


def enrich_job_attrs(html, attrs):
    """Fix title/skills/duration on an attribute dict extracted from ``html``."""
    soup = BeautifulSoup(html, 'html.parser')

    # --- Title: the <h1> or og:title always refer to the main job, while the
    # extractor can be polluted by "Explore similar jobs" tiles.
    title = None
    h1 = soup.find('h1')
    if h1:
        title = h1.get_text(' ', strip=True)
    if not title:
        og = soup.find('meta', attrs={'property': 'og:title'})
        if og and og.get('content'):
            title = og['content'].strip()
    if title:
        attrs['title'] = title

    # --- Skills: only the badges inside the "Skills and Expertise" section.
    if not attrs.get('skills'):
        heading = soup.find(string=re.compile('Skills and Expertise', re.IGNORECASE))
        if heading:
            section = heading.find_parent('section') or heading.find_parent()
            if section:
                skills = []
                for badge in section.select('[class*="air3-badge"]'):
                    text = badge.get_text(' ', strip=True)
                    if text and text not in skills:
                        skills.append(text)
                if skills:
                    attrs['skills'] = skills

    # --- Duration: drop CSS the extractor may have captured.
    duration = attrs.get('duration')
    if not isinstance(duration, str) or not duration or CSS_JUNK.search(duration):
        match = DURATION_RE.search(html)
        attrs['duration'] = match.group(1) if match else ''

    return attrs
