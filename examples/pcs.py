import sys
import os
import io
import polars as pl


sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from procyclingstats import (Race, RaceClimbs, RaceStartlist, Ranking, Rider,
                              RiderResults, Scraper, Stage, Team)

""" Example usage of the ProCyclingStats scraper classes. Can be used to sanity check the functionality of the classes. """

RACE_URL = "race/vuelta-a-la-comunidad-valenciana/2026"

def print_parsed_data(scraper_instance, label):
    """
    Helper function to print parsed data from a scraper instance.
    """
    print(f'{label} CLASS')
    for method in scraper_instance.parse().keys():
        print(f"{method}: {scraper_instance.parse()[method]}")

def main():
    import cloudscraper
    import procyclingstats 
    '''
    url = "https://www.procyclingstats.com"
    scraper = cloudscraper.create_scraper()
    html_content: str
    html_content = scraper.get(f"{url}{RACE_URL}/overview").text
    #raceStartlist = pcs.RaceStartlist(f"{RACE_URL}/overview", html_content, update_html=False).startlist()
    race = Race(f"{RACE_URL}/overview")
    print_parsed_data(race, "RACE")
   
    
    
    # Race class 
    
    race = Race(f"{RACE_URL}/overview")#, html_content, update_html=False)
    print(race)
    data=race.parse() 
    data.items() # Pre-parse to avoid multiple fetches
    df=pl.DataFrame(race.prev_editions_select())
    print(df)
    #print_parsed_data(race, "RACE")
    '''
    # Race climbs class
    race_climbs = RaceClimbs(f"{RACE_URL}/route/climbs")
    print_parsed_data(race_climbs, "RACE CLIMBSSSSSS")

    # Race startlist class
    #race_start = RaceStartlist(f"{RACE_URL}/startlist")
    #print_parsed_data(race_start, "RACE STARTLIST")

    # Ranking class
    #ranking = Ranking("rankings/me/individual")
    #print("RANKING CLASS")
    #print(ranking.individual_ranking()[0:5])  # Display first 5 entries

    # Rider class
    rider = Rider("/rider/jesus-herrada-lopez/2022")
    print_parsed_data(rider, "RIDER")

    # Rider results class
    rider_results = RiderResults("/rider/jesus-herrada-lopez/2026")
    print_parsed_data(rider_results, "RIDER RESULTS")

    # Stage class
    #stage = Stage("race/tour-of-slovenia/2025/stage-1/results")
    #print_parsed_data(stage, "STAGE")

    #Team class
    #team = Team("/team/burgos-burpellet-bh-2026")
    #print_parsed_data(team, "TEAM")


if __name__ == "__main__":
    main()

