"""
Upwork search-parameter normalization and search-URL building.

Ported from the original Upwork-Job-Scraper (execution/upwork_core.py) so the
Scrapy spider can turn a friendly JSON config into an Upwork search URL.
"""

import logging
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

UPWORK_MAIN_CATEGORIES = {
    # Main Categories
    "accounting & consulting": "531770282584862721",
    "admin support": "531770282580668416",
    "customer service": "531770282580668417",
    "data science & analytics": "531770282580668420",
    "design & creative": "531770282580668421",
    "engineering & architecture": "531770282584862722",
    "it & networking": "531770282580668419",
    "legal": "531770282584862723",
    "sales & marketing": "531770282580668422",
    "translation": "531770282584862720",
    "web, mobile & software dev": "531770282580668418",
    "writing": "531770282580668423",
}

# Subcategories
UPWORK_SUBCATEGORIES = {
    # accounting & consulting
    "personal & professional coaching": "1534904461833879552",
    "accounting & bookkeeping": "531770282601639943",
    "financial planning": "531770282601639945",
    "recruiting & human resources": "531770282601639946",
    "management consulting & analysis": "531770282601639944",
    "other - accounting & consulting": "531770282601639947",
    # admin support
    "data entry & transcription services": "531770282584862724",
    "virtual assistance": "531770282584862725",
    "project management": "531770282584862728",
    "market research & product reviews": "531770282584862726",
    # customer service
    "community management & tagging": "1484275072572772352",
    "customer service & tech support": "531770282584862730",
    # data science & analytics
    "data analysis & testing": "531770282593251330",
    "data extraction & etl": "531770282593251331",
    "data mining & management": "531770282589057038",
    "ai & machine learning": "531770282593251329",
    # design & creative
    "art & illustration": "531770282593251335",
    "audio & music production": "531770282593251341",
    "branding & logo design": "1044578476142100480",
    "nft, ar/vr & game art": "1356688560628174848",
    "graphic, editorial & presentation design": "531770282593251334",
    "performing arts": "1356688565288046592",
    "photography": "531770282593251340",
    "product design": "531770282601639953",
    "video & animation": "1356688570056970240",
    # engineering & architecture
    "building & landscape architecture": "531770282601639949",
    "chemical engineering": "531770282605834240",
    "civil & structural engineering": "531770282601639950",
    "contract manufacturing": "531770282605834241",
    "electrical & electronic engineering": "531770282601639951",
    "interior & trade show design": "531770282605834242",
    "energy & mechanical engineering": "531770282601639952",
    "physical sciences": "1301900647896092672",
    "3d modeling & cad": "531770282601639948",
    # it & networking
    "database management & administration": "531770282589057033",
    "erp & crm software": "531770282589057034",
    "information security & compliance": "531770282589057036",
    "network & system administration": "531770282589057035",
    "devops & solution architecture": "531770282589057037",
    # legal
    "corporate & contract law": "531770282605834246",
    "international & immigration law": "1484275156546932736",
    "finance & tax law": "531770283696353280",
    "public law": "1484275408410693632",
    # sales & marketing
    "digital marketing": "531770282597445636",
    "lead generation & telemarketing": "531770282597445634",
    "marketing, pr & brand strategy": "531770282593251343",
    # translation
    "language tutoring & interpretation": "1534904461842268160",
    "translation & localization services": "531770282601639939",
    # web, mobile & software dev
    "blockchain, nft & cryptocurrency": "1517518458442309632",
    "ai apps and integration": "1737190722360750082",
    "desktop application development": "531770282589057025",
    "ecommerce development": "531770282589057026",
    "game design & development": "531770282589057027",
    "mobile development": "531770282589057024",
    "other - software development": "531770282589057032",
    "product management": "531770282589057030",
    "qa & testing": "531770282589057031",
    "scripts & utilities": "531770282589057028",
    "web & mobile design": "531770282589057029",
    "web development": "531770282584862733",
    # writing
    "sales & marketing copywriting": "1534904462131675136",
    "content writing": "1301900640421842944",
    "editing & proofreading services": "531770282597445644",
    "professional & business writing": "531770282597445646",
}


def normalize_search_params(params, credentials_provided, buffer=5):
    """
    Normalize friendly search params into Upwork query-string parameters.

    :param params: dict of search parameters from config/user input
    :param credentials_provided: whether an authenticated session is available
    :return: tuple(normalized_params dict, limit int)
    """
    result = {}

    try:
        limit = int(params.get('limit', 5)) + buffer
    except (ValueError, TypeError):
        limit = 5
        logger.warning("Invalid limit value in config, using default limit of 5")

    allowed_per_page = [10, 20, 50]
    per_page = min([v for v in allowed_per_page if v >= limit] or [50])
    result['per_page'] = str(per_page)

    # Fixed price categories and custom range
    if 'fixed_price_catagory_num' in params:
        amount_ranges = {
            "1": "0-99",
            "2": "100-499",
            "3": "500-999",
            "4": "1000-4999",
            "5": "5000-",
        }
        ranges = []
        for cat in params['fixed_price_catagory_num']:
            if cat in amount_ranges:
                ranges.append(amount_ranges[cat])
        if params.get('fixed_min') and params.get('fixed_max'):
            ranges.append(f"{params['fixed_min']}-{params['fixed_max']}")
        if ranges:
            result['amount'] = ','.join(ranges)

    # Client hires (convert min/max to ranges)
    if 'hires_min' in params or 'hires_max' in params:
        ranges = []
        min_val = int(params.get('hires_min', 0))
        max_val = int(params.get('hires_max', float('inf')))
        if min_val <= 9 and max_val >= 1:
            ranges.append('1-9')
        if max_val >= 10:
            ranges.append('10-')
        if ranges:
            result['client_hires'] = ','.join(ranges)

    if 'expertise_level_number' in params:
        result['contractor_tier'] = ','.join(params['expertise_level_number'])

    if 'projectDuration' in params:
        result['duration_v3'] = ','.join(params['projectDuration'])

    if 'hourly_min' in params and 'hourly_max' in params:
        result['hourly_rate'] = f"{params['hourly_min']}-{params['hourly_max']}"

    job_types = []
    if params.get('hourly'):
        job_types.append('0')
    if params.get('fixed'):
        job_types.append('1')
    if job_types:
        result['t'] = ','.join(job_types)

    if 'workload' in params:
        workload_map = {
            'part_time': 'as_needed',
            'full_time': 'full_time',
        }
        result['workload'] = ','.join(
            workload_map[w] for w in params['workload'] if w in workload_map
        )

    if 'sort' in params:
        sort_map = {
            'relevance': 'relevance+desc',
            'newest': 'recency',
            'client_total_charge': 'client_total_charge+desc',
            'client_rating': 'client_rating+desc',
        }
        result['sort'] = sort_map.get(params['sort'], params['sort'])

    # Query building
    q_parts = []
    if params.get('query'):
        q_parts.append(params['query'])
    if params.get('search_any'):
        words = params['search_any'].split()
        q_parts.append(f"({' OR '.join(words)})")
    if params.get('search_exact'):
        q_parts.append(f'"{params["search_exact"]}"')
    if params.get('search_none'):
        q_parts.append(' '.join(f'-{w}' for w in params['search_none'].split()))
    if params.get('search_title'):
        q_parts.append(' '.join(f'title:{w}' for w in params['search_title'].split()))
    if q_parts:
        result['q'] = ' '.join(q_parts)

    for key in ['contract_to_hire', 'previous_clients']:
        if key in params:
            result[key] = str(params[key]).lower()

    if 'days_posted' in params:
        result['days_posted'] = params['days_posted']

    # Login-required fields
    if not credentials_provided:
        result['proposals'] = ""
        result['payment_verified'] = ""
        result['previous_clients'] = ""
    else:
        if params.get('proposal_num'):
            result['proposals'] = ','.join(params['proposal_num'])
        if params.get('payment_verified'):
            result['payment_verified'] = '1'

    # Categories (main category UID and subcategory UID)
    if params.get('category'):
        main_cat_uids = []
        sub_cat_uids = []
        for cat_name in params['category']:
            cat_name_lower = cat_name.lower()
            if cat_name_lower in UPWORK_MAIN_CATEGORIES:
                main_cat_uids.append(UPWORK_MAIN_CATEGORIES[cat_name_lower])
            elif cat_name_lower in UPWORK_SUBCATEGORIES:
                sub_cat_uids.append(UPWORK_SUBCATEGORIES[cat_name_lower])
            else:
                logger.warning("Category '%s' not found, skipping.", cat_name_lower)

        if main_cat_uids:
            result['category2_uid'] = ','.join(main_cat_uids)
        if sub_cat_uids:
            result['subcategory2_uid'] = ','.join(sub_cat_uids)

    return result, limit


def build_upwork_search_url(params):
    """
    Build an Upwork job search URL from a normalized params dict.
    """
    base_url = params.get('base_url', 'https://www.upwork.com/nx/search/jobs/')

    q_parts = []
    if params.get('all_words'):
        q_parts.append(params['all_words'])
    if params.get('any_words'):
        q_parts.append('(' + ' OR '.join(params['any_words'].split()) + ')')
    if params.get('none_words'):
        q_parts.append(' '.join(f'-{w}' for w in params['none_words'].split()))
    if params.get('exact_phrase'):
        q_parts.append(f'"{params["exact_phrase"]}"')
    if params.get('title_search'):
        q_parts.append(' '.join(f'title:{w}' for w in params['title_search'].split()))
    q = ' '.join(q_parts) if q_parts else params.get('q', '')

    minimal_keys = {'q', 'base_url'}
    if q and (set(params.keys()).issubset(minimal_keys) or len(params) == 1):
        return f"{base_url}?" + urlencode({'q': q})

    url_params = {}
    if q:
        url_params['q'] = q
    filter_keys = [
        'amount', 'client_hires', 'hourly_rate', 'payment_verified', 'per_page',
        'sort', 't', 'contract_to_hire', 'contractor_tier', 'duration_v3',
        'nbs', 'previous_clients', 'proposals', 'workload', 'category2_uid',
        'subcategory2_uid',
    ]
    for k in filter_keys:
        if k in params and params[k] not in (None, ''):
            url_params[k] = params[k]

    for k in params:
        if (k not in url_params and k not in [
                'base_url', 'all_words', 'any_words', 'none_words',
                'exact_phrase', 'title_search', 'q',
        ] and params[k] not in (None, '')):
            url_params[k] = params[k]

    return f"{base_url}?" + urlencode(url_params)
