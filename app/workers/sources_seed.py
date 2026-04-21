"""Curated seed list of Indian RSS sources.

Applied on first boot (or via `python -m app.workers.seed_sources`). Sources
marked `active=False` can be toggled on from the admin panel when you're ready.

URLs drift — verify before a long ingestion run.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SourceSeed:
    slug: str
    name: str
    rss_url: str
    homepage_url: str
    domain: str
    language: str = "en"
    country: str = "IN"
    priority_weight: float = 1.0
    active: bool = True


SEED_SOURCES: list[SourceSeed] = [
    # ---------- English, national/general ----------
    SourceSeed(
        slug="ndtv-top",
        name="NDTV — Top Stories",
        rss_url="https://feeds.feedburner.com/ndtvnews-top-stories",
        homepage_url="https://www.ndtv.com/",
        domain="ndtv.com",
        priority_weight=1.2,
    ),
    SourceSeed(
        slug="thehindu",
        name="The Hindu — News",
        rss_url="https://www.thehindu.com/news/feeder/default.rss",
        homepage_url="https://www.thehindu.com/",
        domain="thehindu.com",
        priority_weight=1.2,
    ),
    SourceSeed(
        slug="indianexpress",
        name="The Indian Express",
        rss_url="https://indianexpress.com/feed/",
        homepage_url="https://indianexpress.com/",
        domain="indianexpress.com",
        priority_weight=1.1,
    ),
    SourceSeed(
        slug="hindustantimes-india",
        name="Hindustan Times — India",
        rss_url="https://www.hindustantimes.com/feeds/rss/india-news/rssfeed.xml",
        homepage_url="https://www.hindustantimes.com/",
        domain="hindustantimes.com",
        priority_weight=1.1,
    ),
    SourceSeed(
        slug="toi-top",
        name="Times of India — Top Stories",
        rss_url="https://timesofindia.indiatimes.com/rssfeedstopstories.cms",
        homepage_url="https://timesofindia.indiatimes.com/",
        domain="timesofindia.indiatimes.com",
    ),
    SourceSeed(
        slug="indiatoday",
        name="India Today",
        rss_url="https://www.indiatoday.in/rss/1206578",
        homepage_url="https://www.indiatoday.in/",
        domain="indiatoday.in",
    ),
    SourceSeed(
        slug="scroll",
        name="Scroll.in",
        rss_url="https://scroll.in/feeds/all.rss",
        homepage_url="https://scroll.in/",
        domain="scroll.in",
    ),
    SourceSeed(
        slug="thewire",
        name="The Wire",
        rss_url="https://thewire.in/rss",
        homepage_url="https://thewire.in/",
        domain="thewire.in",
    ),
    SourceSeed(
        slug="news18",
        name="News18 — India",
        rss_url="https://www.news18.com/rss/india.xml",
        homepage_url="https://www.news18.com/",
        domain="news18.com",
    ),

    # ---------- Business / finance ----------
    SourceSeed(
        slug="livemint",
        name="LiveMint",
        rss_url="https://www.livemint.com/rss/news",
        homepage_url="https://www.livemint.com/",
        domain="livemint.com",
        priority_weight=1.1,
    ),
    SourceSeed(
        slug="moneycontrol",
        name="Moneycontrol — Latest",
        rss_url="https://www.moneycontrol.com/rss/latestnews.xml",
        homepage_url="https://www.moneycontrol.com/",
        domain="moneycontrol.com",
      
    ),
    SourceSeed(
        slug="economictimes",
        name="Economic Times — Top Stories",
        rss_url="https://economictimes.indiatimes.com/rssfeedstopstories.cms",
        homepage_url="https://economictimes.indiatimes.com/",
        domain="economictimes.indiatimes.com",
       
    ),
    SourceSeed(
        slug="businessstandard",
        name="Business Standard — Latest",
        rss_url="https://www.business-standard.com/rss/latest.rss",
        homepage_url="https://www.business-standard.com/",
        domain="business-standard.com",
       
    ),
    SourceSeed(
        slug="yourstory",
        name="YourStory",
        rss_url="https://yourstory.com/feed",
        homepage_url="https://yourstory.com/",
        domain="yourstory.com",
        
    ),
    SourceSeed(
        slug="inc42",
        name="Inc42",
        rss_url="https://inc42.com/feed/",
        homepage_url="https://inc42.com/",
        domain="inc42.com",
        
    ),

    # ---------- Hindi ----------
    SourceSeed(
        slug="bhaskar-national",
        name="Dainik Bhaskar — National",
        rss_url="https://www.bhaskar.com/rss-v1--category-1061.xml",
        homepage_url="https://www.bhaskar.com/",
        domain="bhaskar.com",
        language="hi",
    ),
    SourceSeed(
        slug="amarujala-breaking",
        name="Amar Ujala — Breaking",
        rss_url="https://www.amarujala.com/rss/breaking-news.xml",
        homepage_url="https://www.amarujala.com/",
        domain="amarujala.com",
        language="hi",
    ),
    SourceSeed(
        slug="livehindustan",
        name="Live Hindustan — Home",
        rss_url="https://www.livehindustan.com/rss/home-rssfeed",
        homepage_url="https://www.livehindustan.com/",
        domain="livehindustan.com",
        language="hi",
    ),
    SourceSeed(
        slug="aajtak",
        name="Aaj Tak",
        rss_url="https://www.aajtak.in/rssfeeds/?id=home",
        homepage_url="https://www.aajtak.in/",
        domain="aajtak.in",
        language="hi",
    ),

    # ---------- Regional ----------
    SourceSeed(
        slug="thehindu-tamil",
        name="The Hindu Tamil",
        rss_url="https://www.hindutamil.in/rss/news.xml",
        homepage_url="https://www.hindutamil.in/",
        domain="hindutamil.in",
        language="ta",
    ),
    SourceSeed(
        slug="eenadu-ap",
        name="Eenadu — Andhra Pradesh",
        rss_url="https://www.eenadu.net/rss/ap-top-news.xml",
        homepage_url="https://www.eenadu.net/",
        domain="eenadu.net",
        language="te",
    ),
    SourceSeed(
        slug="anandabazar",
        name="Anandabazar Patrika",
        rss_url="https://www.anandabazar.com/rssfeed.xml",
        homepage_url="https://www.anandabazar.com/",
        domain="anandabazar.com",
        language="bn",
    ),
    SourceSeed(
        slug="lokmat-top",
        name="Lokmat — Top News",
        rss_url="https://www.lokmat.com/rss/top-news.xml",
        homepage_url="https://www.lokmat.com/",
        domain="lokmat.com",
        language="mr",
    ),
    SourceSeed(
        slug="manorama",
        name="Manorama Online — Latest",
        rss_url="https://www.manoramaonline.com/news.feeds.latest-news.rss",
        homepage_url="https://www.manoramaonline.com/",
        domain="manoramaonline.com",
        language="ml",
    ),
]
