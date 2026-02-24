from pprint import pprint

from procyclingstats import Race, RaceClimbs, Stage

# RACE_URL can be replaced with any valid stage race URL
RACE_URL = "https://www.procyclingstats.com/race/ruta-del-sol/2026"
race = Race(f"{RACE_URL}/overview")
race_climbs = RaceClimbs(f"{RACE_URL}/route/climbs")

stages = race.stages()
climbs_table = race_climbs.climbs()
# make dict to access climbs by their URLs
#print("Climbs grouped by stages:"+str(climbs_table))
climbs = {climb['climb_url']: climb for climb in climbs_table}

stages_climbs = {}
# group climbs by stages
for stage_info in stages:
    stage = Stage(stage_info['stage_url'])
    stage_climbs = [climbs[s['climb_url']] for s in stage.climbs()]
    stages_climbs[stage_info['stage_url']] = stage_climbs
pprint("Climbs grouped by stages:"+str(stages_climbs))    
#stage_climbs_list = stages_climbs["race/tour-of-slovenia/2025/stage-5"]
#for climb in stage_climbs_list:
 #   print(climb['climb_name'], climb['steepness'], climb['length'], climb['top'], climb['km_before_finnish'])