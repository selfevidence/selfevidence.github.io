"""
Wikipedia APIs for the news_tracker project.

Classes:
  WikipediaCurrentEventsAPI  — curated monthly event lists from the Current Events Portal
  WikipediaPageviewsAPI      — daily top 100 most-viewed articles (Wikimedia REST API)
"""
import re
import time
import requests
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime, date, timedelta
from pathlib import Path
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

        Supports two page formats:

        Current format (approx. 2020+):
          div.current-events
            div.current-events-heading  → date in span.bday
            div.current-events-content  → alternating <p> / <ul> blocks
              <p><b>Category</b></p>    → category heading

        Older format (pre-2020, e.g. 2016):
          div.current-events-main.vevent
            div.current-events-heading  → date in span.bday
            div.current-events-content  → div.current-events-content-heading + <ul>
              div.current-events-content-heading → category heading

        Within each ul, events are nested by sub-topic:
          ul (category)
            li (sub-topic, has child ul)  ← sub_topic name = first wiki link
              ul
                li (leaf event, no child ul)  ← the actual event row

        Some events have no sub-topic (li is itself a leaf).
        """
        soup = BeautifulSoup(html, "html.parser")
        rows = []

        # Support both the current and older page formats
        day_divs = soup.find_all("div", class_="current-events")
        if not day_divs:
            day_divs = soup.find_all("div", class_="current-events-main")

        for day_div in day_divs:
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

                # Category heading — two formats:
                #   Current: <p><b>Category name</b></p>
                #   Older:   <div class="current-events-content-heading">Category name</div>
                if element.name == "div" and "current-events-content-heading" in element.get("class", []):
                    current_category = element.get_text(strip=True)
                    continue

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
        if df.empty or "date" not in df.columns:
            print(f"  Warning: no events parsed for {self.MONTH_NAMES[month - 1]} {year} "
                  f"(page structure may differ from current format)")
            return pd.DataFrame()
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


class WikipediaPageviewsAPI:
    """Fetches daily top 100 most-viewed Wikipedia articles.

    Uses the Wikimedia REST API — no authentication required.
    Data is available from 2015-07-01 onwards.

    Usage:
        wiki_pageviews = WikipediaPageviewsAPI()

        # Fetch a single day:
        df = wiki_pageviews.get_day(date(2024, 1, 15))

        # Backfill a range, saving incrementally (safe to interrupt and resume):
        df = wiki_pageviews.backfill(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            save_path=RAW_DATA_DIR / '01_wikipedia_pageviews.csv',
        )
    """

    BASE_URL = (
        "https://wikimedia.org/api/rest_v1/metrics/pageviews/top"
        "/en.wikipedia/all-access/{year}/{month:02d}/{day:02d}"
    )
    USER_AGENT = "selfevidence.github.io/1.0 (data research project; contact via GitHub)"
    TOP_N = 100

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.USER_AGENT})

    def get_day(self, d: date) -> tuple[pd.DataFrame, bool]:
        """Fetch top 100 articles for a single day.

        Args:
            d: The date to fetch.

        Returns:
            (df, is_missing) — df is empty on failure;
            is_missing=True means a 404 (no data for that date, not an error).
        """
        url = self.BASE_URL.format(year=d.year, month=d.month, day=d.day)
        try:
            resp = self.session.get(url, timeout=30)
            if resp.status_code == 404:
                return pd.DataFrame(), True
            resp.raise_for_status()
        except Exception as e:
            print(f"  Warning: failed to fetch {d}: {e}")
            return pd.DataFrame(), False

        articles = resp.json()["items"][0]["articles"][: self.TOP_N]
        df = pd.DataFrame(articles)[["rank", "article", "views"]]
        df.insert(0, "date", pd.Timestamp(d))
        return df, False

    def backfill(
        self,
        start_date: date,
        end_date: date,
        save_path: Path,
        delay: float = 0.5,
    ) -> pd.DataFrame:
        """Fetch a date range, skipping dates already in save_path.

        Saves after each day so progress is preserved if interrupted.
        Re-running picks up where it left off.

        Args:
            start_date: First date to fetch (inclusive).
            end_date:   Last date to fetch (inclusive).
            save_path:  CSV path to append results to.
            delay:      Seconds between requests.

        Returns:
            Full DataFrame loaded from save_path after fetching.
        """
        save_path = Path(save_path)

        # Load already-fetched dates to skip
        fetched_dates: set = set()
        if save_path.exists():
            existing = pd.read_csv(save_path, usecols=["date"])
            fetched_dates = set(pd.to_datetime(existing["date"]).dt.date)

        all_dates = [
            start_date + timedelta(days=i)
            for i in range((end_date - start_date).days + 1)
        ]
        to_fetch = [d for d in all_dates if d not in fetched_dates]

        if not to_fetch:
            print(f"  Already up to date — {len(all_dates)} days in {save_path.name}")
        else:
            print(f"  Fetching {len(to_fetch)} days ({to_fetch[0]} → {to_fetch[-1]}) ...")
            write_header = not save_path.exists()
            missing_count = 0
            for i, d in enumerate(to_fetch, 1):
                df_day, is_missing = self.get_day(d)
                if is_missing:
                    missing_count += 1
                elif not df_day.empty:
                    df_day.to_csv(
                        save_path,
                        mode="a",
                        header=write_header,
                        index=False,
                    )
                    write_header = False
                if i % 100 == 0:
                    print(f"    {i}/{len(to_fetch)} days fetched ...")
                time.sleep(delay)
            summary = f"  Done. Saved to {save_path}"
            if missing_count:
                summary += f" ({missing_count} days had no data in Wikimedia's API)"
            print(summary)

        df = pd.read_csv(save_path)
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values(["date", "rank"]).reset_index(drop=True)
        print(f"  Loaded {len(df):,} rows — {df['date'].dt.date.nunique()} days")
        return df
