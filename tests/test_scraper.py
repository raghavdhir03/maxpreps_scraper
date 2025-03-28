import requests
import pandas as pd
from bs4 import BeautifulSoup
from io import StringIO
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from maxpreps_scraper.scraper import MaxPrepsScraper
from concurrent.futures import ThreadPoolExecutor
import concurrent.futures
import re


## testing scraping state rankings
'''scraper = MaxPrepsScraper()
table = scraper.get_rankings('de', 'basketball', '21-22', boys=False)
print(table.head())'''

## testing scraping contests
scraper = MaxPrepsScraper()
#football_data = scraper.get_contests('de', 'football', '21-22')
#basketball_data = scraper.get_contests('tx', 'basketball', '21-22', cities=['austin', 'san antonio'])
baseball_data = scraper.get_contests('hi', 'baseball', '21-22')
#lacrosse_data = scraper.get_contests('tx', 'lacrosse', '21-22', boys=False)
#soccer_data = scraper.get_contests('la', 'soccer', '21-22')
#softball_data = scraper.get_contests('de', 'softball', '21-22')
#print(football_data.head())
#print(basketball_data.head())
print(baseball_data.head())
#print(softball_data.head())
#print(lacrosse_data.head())
#print(soccer_data.head())

"""baseball_rankings = scraper.get_rankings('de', 'baseball', '21-22')
print(baseball_rankings.head())"""


##testing roster function
"""scraper = MaxPrepsScraper()
roster = scraper.get_roster('https://www.maxpreps.com/tx/austin/bowie-bulldogs/basketball/21-22/roster/')
print(roster.head())"""

