"""
Shared setup for all analysis notebooks
Import this at the top of any notebook to get access to APIs and consistent paths
"""
import sys
import os
from pathlib import Path

# Set up paths - get data directory (parent of analysis)
DATA_DIR = Path(os.getcwd()).parent
ANALYSIS_DIR = Path(os.getcwd())
OUTPUT_DIR = DATA_DIR / "output"
PROCESSED_DATA_DIR = OUTPUT_DIR / "processed_data" 
RAW_DATA_DIR = OUTPUT_DIR / "raw_data"
FIGURES_DIR = OUTPUT_DIR / "figures"

# Add data directory to Python path
if str(DATA_DIR) not in sys.path:
    sys.path.append(str(DATA_DIR))

# Create output directories if they don't exist
OUTPUT_DIR.mkdir(exist_ok=True)
PROCESSED_DATA_DIR.mkdir(exist_ok=True)
RAW_DATA_DIR.mkdir(exist_ok=True)
FIGURES_DIR.mkdir(exist_ok=True)

# Import all APIs
from apis.bls_api import BLSAPI

# Standard data science imports
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime

# Configure plotting
plt.style.use('default')
sns.set_palette("husl")

# Initialize APIs
bls = BLSAPI()

# Helper functions for consistent file operations
def save_data(df, filename, subdir="processed_data"):
    """
    Save DataFrame with consistent path handling
    
    Args:
        df: DataFrame to save
        filename: Name of file (e.g., "inflation_data.csv")
        subdir: Subdirectory in output/ ("processed_data", "raw_data", etc.)
    
    Returns:
        Path where file was saved
    """
    if subdir == "processed_data":
        save_path = PROCESSED_DATA_DIR / filename
    elif subdir == "raw_data":
        save_path = RAW_DATA_DIR / filename  
    elif subdir == "figures":
        save_path = FIGURES_DIR / filename
    else:
        save_path = OUTPUT_DIR / subdir / filename
        save_path.parent.mkdir(exist_ok=True)
    
    df.to_csv(save_path, index=False)
    print(f"💾 Data saved: {save_path}")
    return save_path

def save_figure(fig, filename, formats=['png'], subdir="figures"):
    """
    Save matplotlib figure with consistent path handling
    
    Args:
        fig: Matplotlib figure object
        filename: Name without extension (e.g., "unemployment_trends")  
        formats: List of formats ['png', 'pdf', 'svg']
        subdir: Subdirectory in output/
    
    Returns:
        List of paths where files were saved
    """
    if subdir == "figures":
        save_dir = FIGURES_DIR
    else:
        save_dir = OUTPUT_DIR / subdir
        save_dir.mkdir(exist_ok=True)
    
    saved_paths = []
    for fmt in formats:
        file_path = save_dir / f"{filename}.{fmt}"
        fig.savefig(file_path, dpi=300, bbox_inches='tight')
        saved_paths.append(file_path)
    
    print(f"🖼️  Figure saved: {', '.join([str(p) for p in saved_paths])}")
    return saved_paths

def save_plotly_figure(fig, filename, formats=['html'], subdir="figures", for_blog=False):
    """
    Save Plotly figure in various formats, optimized for web/blog use
    
    Args:
        fig: Plotly figure object
        filename: Name without extension
        formats: List of formats ['html', 'json', 'png', 'pdf', 'svg']
        subdir: Subdirectory in output/
        for_blog: If True, optimizes for Jekyll blog embedding
    
    Returns:
        Dictionary with format: filepath pairs
    """
    if subdir == "figures":
        save_dir = FIGURES_DIR
    else:
        save_dir = OUTPUT_DIR / subdir
        save_dir.mkdir(exist_ok=True)
    
    # Also save to docs/assets/charts for blog use
    if for_blog:
        blog_dir = DATA_DIR.parent / "docs" / "assets" / "charts"
        blog_dir.mkdir(parents=True, exist_ok=True)
    
    saved_files = {}
    
    for fmt in formats:
        file_path = save_dir / f"{filename}.{fmt}"
        
        if fmt == 'html':
            # Responsive configuration for web embedding
            responsive_config = {
                'responsive': True,
                'displayModeBar': True,
                'displaylogo': False,
                'scrollZoom': False,  # Disable scroll wheel zoom
                'doubleClick': 'reset',  # Double-click resets view instead of zoom
                'showTips': False,  # Disable hover tooltips that can interfere on touch
                'modeBarButtonsToRemove': ['pan2d', 'lasso2d']  # Keep zoom buttons, remove pan/select
            }
            
            # Save interactive HTML
            fig.write_html(
                file_path,
                include_plotlyjs='cdn',  # Use CDN for smaller files
                div_id=f"{filename}-chart",
                config=responsive_config
            )
            # Also save to blog assets if requested
            if for_blog:
                blog_path = blog_dir / f"{filename}.html"
                fig.write_html(blog_path, include_plotlyjs='cdn', div_id=f"{filename}-chart", config=responsive_config)
                print(f"📝 Blog version saved: {blog_path}")
                
        elif fmt == 'json':
            # Save as JSON for custom embedding
            with open(file_path, 'w') as f:
                f.write(fig.to_json())
                
        elif fmt in ['png', 'pdf', 'svg']:
            # Static formats
            fig.write_image(file_path, width=1200, height=700)
            
        saved_files[fmt] = file_path
    
    print(f"📊 Plotly figure saved: {', '.join([f'{fmt}: {path}' for fmt, path in saved_files.items()])}")
    
    if for_blog and 'html' in formats:
        print(f"✨ To embed in Jekyll post, use:")
        print(f'<iframe src="{{{{ site.baseurl }}}}/assets/charts/{filename}.html" width="100%" height="700" frameborder="0"></iframe>')
    
    return saved_files

def load_data(filename, subdir="processed_data"):
    """
    Load data with consistent path handling
    
    Args:
        filename: Name of file to load
        subdir: Subdirectory in output/
    
    Returns:
        DataFrame
    """
    if subdir == "processed_data":
        file_path = PROCESSED_DATA_DIR / filename
    elif subdir == "raw_data":
        file_path = RAW_DATA_DIR / filename
    else:
        file_path = OUTPUT_DIR / subdir / filename
    
    if file_path.exists():
        df = pd.read_csv(file_path)
        print(f"📂 Loaded: {file_path} ({len(df)} rows)")
        return df
    else:
        print(f"❌ File not found: {file_path}")
        return None

print("✅ Notebook setup complete!")
print("✅ Available APIs: bls")
print("✅ Available libraries: pd, np, plt, sns, datetime")
print("✅ Helper functions: save_data(), save_figure(), save_plotly_figure(), load_data()")
print(f"📁 Data directory: {DATA_DIR}")
print(f"📁 Output directory: {OUTPUT_DIR}")
print("📊 Ready for analysis!")
