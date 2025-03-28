import requests
from bs4 import BeautifulSoup
from tqdm import tqdm
import pandas as pd
from io import StringIO
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor, as_completed
import re

class MaxPrepsScraper():

    BASE_URL = 'https://www.maxpreps.com'

    def __init__(self):
        """Initialize scraper settings (headers, session, etc.)."""
        self.session = requests.Session()

    def get_rankings(self, state: str, sport: str, year: str, boys=True):
        """
        Get rankings for a given sport, state, and year.
        Returns a Pandas DataFrame with:
        - School Name
        - State Rank
        - Strength of Schedule (SOS)
        - Team Rating
        - Team URL
        """

        if sport not in ['basketball', 'football', 'baseball', 'soccer', 'volleyball', 'lacrosse', 'softball']:
            raise ValueError(f"Sport '{sport}' is not supported. Please choose from: basketball, football, baseball, soccer, volleyball, lacrosse, softball")
        
        if (boys == False and sport in ['football', 'baseball']) or (boys and sport in ['softball', 'volleyball']):
            raise ValueError(f"{'boys' if boys else 'girls'} {sport} is not supported")
        
        if sport == 'soccer' and state not in ['tx', 'la', 'ms', 'hi', 'ca', 'fl', 'az']:
            raise ValueError(f"Soccer is not supported in {state}")
        
        state_url = f"{self.BASE_URL}/{state}/{sport}/{'' if (boys or sport in ['softball', 'volleyball']) else 'girls/'}{'winter/' if sport == 'soccer' else ''}{year}/rankings"
       
        page = 1
        full_df = pd.DataFrame()

        while True:
            page_url = f'{state_url}/{page}/'
        
            response = requests.get(page_url)

            # Stop if the page does not exist
            if response.status_code != 200:
                break

            soup = BeautifulSoup(response.text, 'html.parser')

            # You can add extra checks here to stop if there's no data
            table = soup.find('table')
            if not table:
                break

            # Process your table here
            df = self._scrape_table(soup)

            full_df = pd.concat([full_df, df]).reset_index(drop=True)

            page += 1
        
        full_df['Team'] = full_df['Team'].str.replace(r'^([A-Z])\1', r'\1', regex=True) #take care of schools with no mascot. Turns AAustin into Austin

        return full_df
    
    #sports that this function suppoprts: basketball, football, baseball, soccer, volleyball, lacrosse, softball, 
    def get_contests(self, state: str, sport: str, year: str, boys: bool = True, cities=None):

        if sport not in ['basketball', 'football', 'baseball', 'soccer', 'volleyball', 'lacrosse', 'softball']:
            raise ValueError(f"Sport '{sport}' is not supported. Please choose from: basketball, football, baseball, soccer, volleyball, lacrosse, softball")
        
        if (boys == False and sport in ['football', 'baseball']) or (boys and sport in ['softball', 'volleyball']):
            raise ValueError(f"{'boys' if boys else 'girls'} {sport} is not supported")
        
        if sport == 'soccer' and state not in ['tx', 'la', 'ms', 'hi', 'ca', 'fl', 'az']:
            raise ValueError(f"Soccer is not supported in {state}")
        

        state_url = f"{self.BASE_URL}/{state}/{sport}/{'' if (boys or sport in ['softball', 'volleyball']) else 'girls/'}{'winter/' if sport == 'soccer' else ''}{year}/rankings"
        page = 1
        school_list = []

        # Step 1: Collect all school links
        while True:
            page_url = f'{state_url}/{page}/'
            #print(page_url)
            response = requests.get(page_url)

            if response.status_code != 200:
                break

            soup = BeautifulSoup(response.text, 'html.parser')
            page_list = self._get_school_list(soup, cities)
            #print(page_list)
            school_list += page_list
            #print(len(school_list))
            page += 1
        
        

        # Step 2: Thread-safe scrape function that still uses self._scrape_table()
        def _fetch_and_scrape(school, url, base_url='https://www.maxpreps.com'):
            try:
                response = requests.get(base_url + url, timeout=10)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    table = self._scrape_table(soup)
                    table['Team 2 URL'] = self._extract_opponent_urls(soup)
                    location_info = self._extract_location_info(soup)
                    table['Team 1'] = school
                    table['Team 1 Address'] = location_info['address']
                    table['Team 1 City'] = location_info['city']
                    table['Team 1 State'] = location_info['state']
                    table['Team 1 Zipcode'] = location_info['zipcode']
                    table['Team 1 URL'] = url
                    return table
                else:
                    print(f"Failed to fetch {url} (status code: {response.status_code})")
            except Exception as e:
                print(f"Error scraping {school} at {url}: {e}")
            return None

        # Step 3: Run threads
       
        full_df = pd.DataFrame()
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(_fetch_and_scrape, school, url) for school, url in school_list]

            with tqdm(total=len(futures), desc=f"Scraping Schools for {', '.join(city for city in cities) if cities else ''} {state}", unit=" schools") as pbar:
                for future in as_completed(futures):
                    result_df = future.result()
                    if result_df is not None and not result_df.empty:
                        full_df = pd.concat([full_df, result_df], ignore_index=True)
                    pbar.update(1)
        
        
        full_df = self._clean_contest_data(full_df)

        return full_df


    def _scrape_table(self, soup):
        table = soup.find('table')
        html = str(table)
        df = pd.read_html(StringIO(html))[0]
        return df

    def _get_school_list(self, soup, cities=None, base_url='https://www.maxpreps.com'):
        """
        Extracts school names and links to schedule pages based on new MaxPreps HTML structure.
        """
        school_data = []

        for td in soup.find_all('td'):
            a_tag = td.find('a', href=True)
            if a_tag and 'schedule' in a_tag['href']:
                href = a_tag['href']
                
                # Check if cities is None (no filter), or if any city is in the href
                if cities is None or any(city.lower().replace(" ", "-") == href.lower().split('/')[2] for city in cities):
                    name = a_tag.get_text(strip=True)
                    link = href
                    school_data.append((name, link))


        return school_data

    def _extract_location_info(self, soup):

        address_element = soup.select_one('address')
        if not address_element:
            return {
                "address": None,
                "city": None,
                "state": None,
                "zipcode": None
            }

        # Get city/state/zip from <span>
        city_state_span = address_element.find('span')
        if city_state_span:
            city_state_text = city_state_span.get_text(strip=True)
            city_state_span.decompose()  # Remove span from the address block
        else:
            city_state_text = ""

        # Now get street address (without the span)
        street_address = address_element.get_text(strip=True)

        # Parse city, state, and zip using regex
        city, state, zipcode = None, None, None
        match = re.match(r'^(.*?),\s*([A-Z]{2})\s*(\d{5})(?:-\d{4})?$', city_state_text)
        if match:
            city, state, zipcode = match.groups()

        return {
            "address": street_address or None,
            "city": city,
            "state": state,
            "zipcode": zipcode
        }
    
    def _extract_opponent_urls(self, soup): #Extracts a list of opponent URLs (or None) from the 'Opponent' column in the schedule table.
        
        opponent_urls = []

        # Find the schedule table
        table = soup.find('table')
        if not table:
            return []

        # Step 1: Get header row and find the column index for 'Opponent'
        header_row = table.find('tr')
        headers = [th.get_text(strip=True).lower() for th in header_row.find_all('th')]
        
        try:
            opponent_idx = headers.index('opponent')
        except ValueError:
            return []

        # Step 2: Go through all remaining rows and get href from the opponent column
        for row in table.find_all('tr')[1:]:  # skip header row
            cells = row.find_all('td')
            if len(cells) > opponent_idx:
                opponent_cell = cells[opponent_idx]
                a_tag = opponent_cell.find('a', href=True)

                if a_tag and a_tag['href'].endswith('/schedule/'):
                    opponent_urls.append(a_tag['href'])
                else:
                    opponent_urls.append(None)

        return opponent_urls
    
    def _clean_contest_data(self, df):
        # --- 1. Clean 'Opponent' column ---
        opponent_pattern = r'(?P<VenueRaw>vs\.?|@)?\s*(?P<Team2>.+?)(?P<Star>\*{0,3})$'

        opponent_info = df['Opponent'].str.extract(opponent_pattern)

        # Venue
        opponent_info['Venue'] = opponent_info['VenueRaw'].map({
            'vs': 'Home',
            'vs.': 'Home',
            '@': 'Away'
        }).fillna('Neutral')

        # Game Type
        opponent_info['Game Type'] = opponent_info['Star'].map({
            '': 'Regular Season',
            '*': 'District',
            '**': 'Playoff',
            '***': 'Tournament'
        }).fillna('Regular Season')

        df['Team 2'] = opponent_info['Team2'].str.strip()
        df['Venue'] = opponent_info['Venue']
        df['Game Type'] = opponent_info['Game Type']

        # --- 2. Clean 'Result' column ---
        result_pattern = r'(?P<Outcome>[WL])(?: (?P<Team1_Score>\d+)-(?P<Team2_Score>\d+)|\((?P<Forfeit>FF)\))'

        result_info = df['Result'].str.extract(result_pattern)

        df['Outcome'] = result_info['Outcome']
        df['Team 1 Score'] = pd.to_numeric(result_info['Team1_Score'], errors='coerce')
        df['Team 2 Score'] = pd.to_numeric(result_info['Team2_Score'], errors='coerce')
        df['Forfeit'] = result_info['Forfeit'].notna()

        cols_to_drop = ['Opponent', 'Result', 'Game Info', 'Match Info']
        df.drop(columns=[col for col in cols_to_drop if col in df.columns], inplace=True)

        df.loc[df['Outcome'] == 'L', ['Team 1 Score', 'Team 2 Score']] = df.loc[df['Outcome'] == 'L', ['Team 2 Score', 'Team 1 Score']].values # Swap scores if team 1 lost

        df['Team 1'] = df['Team 1'].str.replace(r'(^[A-Z])\1', '', regex=True) #take care of schools with no mascot. Turns AAustin into Austin

        # Reorder columns
        new_order = ['Date', 'Team 1', 'Team 2', 'Team 1 Score', 'Team 2 Score', 'Outcome', 'Forfeit', 'Venue', 'Game Type', 'Team 1 Address', 'Team 1 City', 'Team 1 State', 'Team 1 Zipcode', 'Team 1 URL', 'Team 2 URL'] 
        df = df[new_order]

        return df

