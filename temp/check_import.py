import os
import sys
import pathlib

sys.path.insert(0, os.path.abspath("procyclingstats"))

import procyclingstats
import procyclingstats.scraper as scraper_module

scraper_path = pathlib.Path(scraper_module.__file__)
content = scraper_path.read_text(encoding="utf-8", errors="ignore")

print(procyclingstats.__file__)
print(scraper_module.__file__)
print("PRINT" if 'print("Fetching HTML using cloudscraper")' in content else "NO_PRINT")
print("DEBUG" if 'logger.debug("Fetching HTML using cloudscraper' in content else "NO_DEBUG")
