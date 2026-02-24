"""
Shared setup for news_tracker analysis notebooks.
Import this at the top of any notebook to get consistent paths and APIs.
"""
import sys
import os
from pathlib import Path

# Paths: analysis/ lives inside news_tracker/
PROJECT_DIR = Path(os.getcwd()).parent          # projects/news_tracker/
ANALYSIS_DIR = Path(os.getcwd())               # projects/news_tracker/analysis/
OUTPUT_DIR = PROJECT_DIR / "output"
PROCESSED_DATA_DIR = OUTPUT_DIR / "processed_data"
RAW_DATA_DIR = OUTPUT_DIR / "raw_data"
FIGURES_DIR = OUTPUT_DIR / "figures"

DOCS_CHARTS_DIR = PROJECT_DIR.parent.parent / "docs" / "assets" / "charts" / "news_tracker"

# Add project dir to path so we can import from apis/
if str(PROJECT_DIR) not in sys.path:
    sys.path.append(str(PROJECT_DIR))

# Create output directories if they don't exist
for d in [OUTPUT_DIR, PROCESSED_DATA_DIR, RAW_DATA_DIR, FIGURES_DIR, DOCS_CHARTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# APIs
from apis.wikipedia_api import WikipediaCurrentEventsAPI, WikipediaPageviewsAPI

# Standard libraries
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, date, timedelta

import plotly.express as px
import plotly.graph_objects as go

# Configure plotting
plt.style.use("default")
sns.set_palette("husl")

# Initialize APIs
wikipedia = WikipediaCurrentEventsAPI()
wiki_pageviews = WikipediaPageviewsAPI()


# ------------------------------------------------------------------
# Helper functions (mirrors gov_data pattern)
# ------------------------------------------------------------------

def save_data(df, filename, subdir="processed_data"):
    """Save a DataFrame to output/processed_data/ (or raw_data/)."""
    path_map = {
        "processed_data": PROCESSED_DATA_DIR,
        "raw_data": RAW_DATA_DIR,
    }
    save_path = path_map.get(subdir, OUTPUT_DIR / subdir)
    save_path.mkdir(parents=True, exist_ok=True)
    full_path = save_path / filename
    df.to_csv(full_path, index=False)
    print(f"💾 Data saved: {full_path}")
    return full_path


def load_data(filename, subdir="processed_data"):
    """Load a CSV from output/processed_data/ (or raw_data/)."""
    path_map = {
        "processed_data": PROCESSED_DATA_DIR,
        "raw_data": RAW_DATA_DIR,
    }
    file_path = path_map.get(subdir, OUTPUT_DIR / subdir) / filename
    if file_path.exists():
        df = pd.read_csv(file_path)
        print(f"📂 Loaded: {file_path} ({len(df)} rows)")
        return df
    print(f"❌ File not found: {file_path}")
    return None


def save_plotly_figure(fig, filename, formats=["html"], for_blog=False):
    """Save a Plotly figure; optionally copy to docs/assets/charts/news_tracker/."""
    responsive_config = {
        "responsive": True,
        "displayModeBar": True,
        "displaylogo": False,
        "scrollZoom": False,
        "doubleClick": "reset",
        "showTips": False,
        "modeBarButtonsToRemove": ["pan2d", "lasso2d", "zoom2d"],
    }

    saved = {}
    for fmt in formats:
        file_path = FIGURES_DIR / f"{filename}.{fmt}"

        if fmt == "html":
            fig.write_html(
                file_path,
                include_plotlyjs="cdn",
                div_id=f"{filename}-chart",
                config=responsive_config,
            )
            if for_blog:
                blog_path = DOCS_CHARTS_DIR / f"{filename}.html"
                fig.write_html(
                    blog_path,
                    include_plotlyjs="cdn",
                    div_id=f"{filename}-chart",
                    config=responsive_config,
                )
                print(f"📝 Blog version saved: {blog_path}")
        elif fmt in ["png", "pdf", "svg"]:
            fig.write_image(file_path, width=1200, height=700)

        saved[fmt] = file_path

    print(f"📊 Plotly figure saved: {', '.join(f'{k}: {v}' for k, v in saved.items())}")

    if for_blog and "html" in formats:
        print(f"✨ To embed in Jekyll post, use:")
        print(f'<iframe src="{{{{ site.baseurl }}}}/assets/charts/news_tracker/{filename}.html"'
              f' width="100%" height="700" frameborder="0"></iframe>')

    return saved


print("✅ Notebook setup complete!")
print("✅ Available APIs: wikipedia, wiki_pageviews")
print("✅ Available libraries: pd, np, plt, sns, px, go, datetime")
print("✅ Helper functions: save_data(), load_data(), save_plotly_figure()")
print(f"📁 Project directory: {PROJECT_DIR}")
print(f"📁 Output directory:  {OUTPUT_DIR}")
print("📊 Ready for analysis!")
