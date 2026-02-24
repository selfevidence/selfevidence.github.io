"""
Google Trends RSS fallback for the news_tracker project.

Working signals (as of 2026):
  - Daily trending searches  → RSS feed (reliable, includes traffic estimates)

Broken pytrends methods (Google changed endpoints):
  - trending_searches()  → replaced by RSS feed below
  - top_charts()         → returns 404; no reliable replacement
  - interest_over_time() → removed from this module (pytrends unreliable)

Primary data source: Kaggle dataset via kaggle_loader.GoogleTrendsLoader.
This module provides an RSS-based fallback when Kaggle data is unavailable.
"""
import requests
import pandas as pd
import xml.etree.ElementTree as ET
from datetime import date
from email.utils import parsedate_to_datetime

# XML namespace used by the Google Trends RSS feed
_RSS_NS = {"ht": "https://trends.google.com/trending/rss"}
_RSS_URL = "https://trends.google.com/trending/rss?geo={geo}"
_RSS_HEADERS = {"User-Agent": "selfevidence.github.io/1.0 (data research; contact via GitHub)"}


def _parse_traffic(s: str) -> int:
    """Convert approx_traffic strings like '50K+', '1M+', '500+' to integers."""
    s = s.replace("+", "").strip()
    try:
        if s.endswith("M"):
            return int(float(s[:-1]) * 1_000_000)
        if s.endswith("K"):
            return int(float(s[:-1]) * 1_000)
        return int(s)
    except (ValueError, AttributeError):
        return 0


class GoogleTrendsAPI:
    """RSS-based fallback for Google Trends daily trending searches.

    This is a fallback for when the Kaggle dataset is unavailable or stale.
    For primary data access, use kaggle_loader.GoogleTrendsLoader.

    Usage:
        from apis.google_trends_api import GoogleTrendsAPI
        df = GoogleTrendsAPI().get_daily_trends(geo='US')
    """

    def __init__(self):
        self._session = requests.Session()
        self._session.headers.update(_RSS_HEADERS)

    def get_daily_trends(self, geo: str = "US") -> pd.DataFrame:
        """Fetch the current daily trending searches from Google's RSS feed.

        Returns a snapshot of what is trending NOW. Output columns match
        the Kaggle google_trends dataset schema as closely as possible.

        Args:
            geo: Two-letter country code, e.g. 'US', 'GB'.

        Returns:
            DataFrame with columns:
              rank, query, approx_traffic, traffic_min,
              pub_date, fetched_date, top_news_source, geo
        """
        url = _RSS_URL.format(geo=geo)
        try:
            resp = self._session.get(url, timeout=15)
            resp.raise_for_status()
        except Exception as e:
            print(f"  Warning: RSS fetch failed for geo={geo}: {e}")
            return pd.DataFrame()

        try:
            root = ET.fromstring(resp.text)
        except ET.ParseError as e:
            print(f"  Warning: RSS parse failed: {e}")
            return pd.DataFrame()

        rows = []
        for rank, item in enumerate(root.findall(".//item"), start=1):
            title_el = item.find("title")
            traffic_el = item.find("ht:approx_traffic", _RSS_NS)
            pub_el = item.find("pubDate")
            news_items = item.findall("ht:news_item", _RSS_NS)

            query = title_el.text.strip() if title_el is not None else ""
            if not query:
                continue

            traffic_str = traffic_el.text.strip() if traffic_el is not None else ""
            traffic_min = _parse_traffic(traffic_str)

            pub_date = None
            if pub_el is not None and pub_el.text:
                try:
                    pub_date = parsedate_to_datetime(pub_el.text).date().isoformat()
                except Exception:
                    pass

            top_source = ""
            if news_items:
                src_el = news_items[0].find("ht:news_item_source", _RSS_NS)
                top_source = src_el.text.strip() if src_el is not None and src_el.text else ""

            rows.append({
                "rank": rank,
                "query": query,
                "approx_traffic": traffic_str,
                "traffic_min": traffic_min,
                "pub_date": pub_date,
                "fetched_date": date.today().isoformat(),
                "top_news_source": top_source,
                "geo": geo,
            })

        df = pd.DataFrame(rows)
        print(f"  Fetched {len(df)} trending searches via RSS (as of {date.today()}, geo={geo})")
        return df
