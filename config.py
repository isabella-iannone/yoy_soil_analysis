"""Shared settings for the Year over Year Analysis app.
 
Import these anywhere they're needed, for example:
    from config import MATCHES_PATH, ANALYSIS_PAGE
"""
 
from pathlib import Path
 
# Folder this file lives in (C:\Users\isabe\year_or_year_testing_info)
BASE_DIR = Path(__file__).resolve().parent
 
# Where confirmed field matches are saved by the Home page
# and read by the Analysis page
MATCHES_PATH = BASE_DIR / "matches.csv"