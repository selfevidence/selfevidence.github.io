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
print("✅ Helper functions: save_data(), save_figure(), load_data()")
print(f"📁 Data directory: {DATA_DIR}")
print(f"📁 Output directory: {OUTPUT_DIR}")
print("📊 Ready for analysis!")
