# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class UpworkJobItem(scrapy.Item):
    title = scrapy.Field()
    url = scrapy.Field()
    job_id = scrapy.Field()
    description = scrapy.Field()
    type = scrapy.Field()
    fixed_budget_amount = scrapy.Field()
    hourly_min = scrapy.Field()
    hourly_max = scrapy.Field()
    currency = scrapy.Field()
    duration = scrapy.Field()
    level = scrapy.Field()
    skills = scrapy.Field()
    category = scrapy.Field()
    categoryGroup_name = scrapy.Field()
    qualifications = scrapy.Field()
    questions = scrapy.Field()
    applicants = scrapy.Field()
    connects_required = scrapy.Field()
    ts_create = scrapy.Field()
    ts_publish = scrapy.Field()
    client_country = scrapy.Field()
    client_company_size = scrapy.Field()
    client_industry = scrapy.Field()
    client_rating = scrapy.Field()
    client_reviews = scrapy.Field()
    client_hires = scrapy.Field()
    client_total_spent = scrapy.Field()
    payment_verified = scrapy.Field()
    phone_verified = scrapy.Field()
    buyer_hire_rate_pct = scrapy.Field()
