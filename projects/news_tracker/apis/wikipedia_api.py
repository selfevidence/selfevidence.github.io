"""
Wikipedia Current Events Portal API

Fetches and parses the curated monthly event lists from:
https://en.wikipedia.org/wiki/Portal:Current_events
"""
import re
import time
import requests
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime
from typing import Optional


class WikipediaCurrentEventsAPI:
    """Fetches curated events from Wikipedia's Current Events Portal.

    Each month's page is a human-edited list of notable events organized by
    date and category (Armed conflicts, Politics, Science, etc.), making it
    a reliable ground-truth signal for what actually mattered in a given month.
    """

    BASE_URL = "https://en.wikipedia.org/w/api.php"
    USER_AGENT = "selfevidence.github.io/1.0 (data research project; contact via GitHub)"

    MONTH_NAMES = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    ]

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.USER_AGENT})

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _page_name(self, year: int, month: int) -> str:
        return f"Portal:Current_events/{self.MONTH_NAMES[month - 1]}_{year}"

    def _fetch_html(self, year: int, month: int) -> str:
        """Return the rendered HTML for a monthly current events page."""
        params = {
            "action": "parse",
            "page": self._page_name(year, month),
            "prop": "text",
            "format": "json",
            "disablelimitreport": True,
        }
        response = self.session.get(self.BASE_URL, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        if "error" in data:
            raise ValueError(f"Wikipedia API error: {data['error']['info']}")

        return data["parse"]["text"]["*"]

    @staticmethod
    def _extract_sources(li) -> list[str]:
        """Return source names from external citation links in a leaf event li."""
        sources = []
        for a in li.find_all("a", class_="external"):
            name = a.get_text(" ", strip=True).strip("()")
            if name:
                sources.append(name)
        return sources

    @staticmethod
    def _extract_wiki_links(li) -> list[str]:
        """Return Wikipedia article titles linked in a leaf event li,
        excluding namespace links (Portal:, Help:, Special:, etc.) and
        external links."""
        skip_prefixes = ("/wiki/Portal:", "/wiki/Help:", "/wiki/Special:",
                         "/wiki/Wikipedia:", "/wiki/Talk:")
        return [
            a.get("title", "").strip()
            for a in li.find_all("a")
            if a.get("href", "").startswith("/wiki/")
            and not any(a.get("href", "").startswith(p) for p in skip_prefixes)
            and "external" not in a.get("class", [])
            and a.get("title")
        ]

    def _parse_html(self, html: str, year: int, month: int) -> pd.DataFrame:
        """Parse rendered HTML into a structured DataFrame.

        Each day is a div.current-events containing:
          div.current-events-heading  → date (ISO string in span.bday)
          div.current-events-content  → alternating p / ul blocks

        Each p that contains a <b> child is a category heading.
        p elements without <b> are stray source citations — ignored.

        Within each ul, events are nested by sub-topic:
          ul (category)
            li (sub-topic, has child ul)  ← sub_topic name = first wiki link
              ul
                li (leaf event, no child ul)  ← the actual event row

        Some events have no sub-topic (li is itself a leaf).
        """
        soup = BeautifulSoup(html, "html.parser")
        rows = []

        for day_div in soup.find_all("div", class_="current-events"):
            # ISO date from structured span — no string parsing needed
            date_span = day_div.find("span", class_="bday")
            if not date_span:
                continue
            try:
                event_date = datetime.strptime(date_span.get_text(strip=True), "%Y-%m-%d").date()
            except ValueError:
                continue

            content = day_div.find("div", class_="current-events-content")
            if not content:
                continue

            current_category = None
            for element in content.children:
                if not hasattr(element, "name") or not element.name:
                    continue

                # Category heading — must have a <b> child to distinguish from
                # stray source-citation <p> elements like <p>(The Hindu)</p>
                if element.name == "p":
                    if element.find("b"):
                        current_category = element.get_text(strip=True)
                    continue

                if element.name != "ul" or not current_category:
                    continue

                # Each direct-child li of the category ul is a "topic" entry.
                # Its first internal wiki link is the sub-topic name.
                for topic_li in element.find_all("li", recursive=False):
                    sub_topic = ""
                    for a in topic_li.children:
                        if (hasattr(a, "name") and a.name == "a"
                                and a.get("href", "").startswith("/wiki/")
                                and "external" not in a.get("class", [])
                                and a.get("title")):
                            sub_topic = a.get("title", "").strip()
                            break

                    # Collect leaf events (li without a child ul)
                    leaf_lis = [li for li in topic_li.find_all("li")
                                if not li.find("ul")]
                    # If the topic_li itself has no children ul, it IS the leaf
                    if not topic_li.find("ul"):
                        leaf_lis = [topic_li]

                    for leaf_li in leaf_lis:
                        description = leaf_li.get_text(" ", strip=True)
                        if not description or len(description) < 10:
                            continue

                        rows.append({
                            "date": event_date,
                            "year": year,
                            "month": month,
                            "category": current_category,
                            "sub_topic": sub_topic,
                            "description": description,
                            "wiki_links": "|".join(self._extract_wiki_links(leaf_li)),
                            "sources": "|".join(self._extract_sources(leaf_li)),
                        })

        return pd.DataFrame(rows)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get_month(self, year: int, month: int) -> pd.DataFrame:
        """Fetch and parse events for a single month.

        Args:
            year:  Four-digit year (e.g. 2025)
            month: 1-indexed month (1 = January)

        Returns:
            DataFrame with columns: date, year, month, category,
            description, links
        """
        html = self._fetch_html(year, month)
        df = self._parse_html(html, year, month)
        df["date"] = pd.to_datetime(df["date"])
        print(f"  Fetched {len(df)} events for {self.MONTH_NAMES[month - 1]} {year}")
        return df

    def get_months(
        self,
        start_year: int,
        start_month: int,
        end_year: int,
        end_month: int,
        delay: float = 1.0,
    ) -> pd.DataFrame:
        """Fetch events for a range of months (inclusive on both ends).

        Args:
            start_year, start_month: First month to fetch
            end_year, end_month:     Last month to fetch
            delay: Seconds to wait between requests (be polite to Wikipedia)

        Returns:
            Combined DataFrame sorted by date, then category.
        """
        dfs = []
        y, m = start_year, start_month

        while (y, m) <= (end_year, end_month):
            try:
                dfs.append(self.get_month(y, m))
            except Exception as e:
                print(f"  Warning: failed to fetch {self.MONTH_NAMES[m - 1]} {y}: {e}")

            # advance one month
            if m == 12:
                y, m = y + 1, 1
            else:
                m += 1

            time.sleep(delay)

        if not dfs:
            return pd.DataFrame()

        df = pd.concat(dfs, ignore_index=True)
        df = df.sort_values(["date", "category"]).reset_index(drop=True)
        return df
