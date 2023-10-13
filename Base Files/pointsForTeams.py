import requests
import pandas as pd
import numpy as np

# Define empty dictionaries to store player stats and match stats
player_stats = {}
match_stats = {}

# Create an empty dictionary to store the contestant data
contestant_data = {}

# Function to add contestants and their points to the dictionary
def add_contestants(contestants, points):
    for name, score in zip(contestants, points):
        contestant_data[name] = float(score)

# Function to associate a player with a list of contestants and points
def associate_player(player_name, selected_contestants):
    player_results = []
    for selected_contestant in selected_contestants:
        if selected_contestant in contestant_data:
            player_results.append(f"{player_name}: {selected_contestant} {contestant_data[selected_contestant]}")
        else:
            player_results.append(f"{selected_contestant} is not in the original list.")
    return player_results

def get_match_details(match_id):
    url = f'https://api.opendota.com/api/matches/{match_id}'
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching data for match {match_id}: {response.status_code}")
    return None

def extract_match_stats(match_id):
    match_data = get_match_details(match_id)
    if match_data is not None:
        radiant_team_name = match_data['radiant_team']['name']
        dire_team_name = match_data['dire_team']['name']
        
        match_stats = calculate_match_stats(match_data)
        match_stats['RadiantTeam'] = radiant_team_name
        match_stats['DireTeam'] = dire_team_name
        
        return match_stats
    return None

def calculate_match_stats(match_data):
    radiant_towers_taken = 11 - bin(match_data['tower_status_radiant']).count('1')
    dire_towers_taken = 11 - bin(match_data['tower_status_dire']).count('1')


    radiant_barracks_taken = 6 - bin(match_data['barracks_status_radiant']).count('1')
    dire_barracks_taken = 6 - bin(match_data['barracks_status_dire']).count('1')

    radiant_roshans = 0
    dire_roshans = 0

    # Count Roshan kills for each team
    for player in match_data['players']:
        if player['player_slot'] < 128:
            radiant_roshans += player.get('roshans_killed', 0)
        else:
            dire_roshans += player.get('roshans_killed', 0)

    # Determine first blood based on player kills
    radiant_first_blood = any(player['player_slot'] < 128 and player['kills'] > 0 for player in match_data['players'])
    dire_first_blood = any(player['player_slot'] >= 128 and player['kills'] > 0 for player in match_data['players'])

    if radiant_first_blood:
        first_blood = match_data['dire_team']['name']
    elif dire_first_blood:
        first_blood = match_data['radiant_team']['name']
    else:
        first_blood = "No First Blood"

    return {
        'RadiantTowersTaken': dire_towers_taken,
        'DireTowersTaken': radiant_towers_taken,
        'RadiantBarracksTaken': dire_barracks_taken,
        'DireBarracksTaken': radiant_barracks_taken,
        'RadiantRoshans': radiant_roshans,
        'DireRoshans': dire_roshans,
        'FirstBlood': first_blood,
    }

# Prompt the user to input match IDs
match_ids_input = input("Enter match IDs (comma-separated): ")
match_ids = [int(match_id) for match_id in match_ids_input.split(",")]
processed_match_ids = set()
# Fetch and process match data for each match ID
for match_id in match_ids:
    if match_id in processed_match_ids:
        print(f"Match ID {match_id} has already been processed. Skipping...")
        continue
    match_data = get_match_details(match_id)
    if match_data:
        match_stats[match_id] = extract_match_stats(match_id)
    processed_match_ids.add(match_id)

# Initialize the summary_data dictionary with empty lists
summary_data = {
    'Team': [],
    'Towers': [],
    'Barracks': [],
    'Roshans': [],
    'FirstBloods': [],
    'TotalFantasyPoints': [],  # Add a new column for Total Fantasy Points
}

# Create a combined summary DataFrame for towers, barracks, roshans, and first blood
for match_id in match_ids:
    match_data = match_stats[match_id]
    radiant_team_name = match_data['RadiantTeam']
    dire_team_name = match_data['DireTeam']

    # Add the Radiant Team's stats
    if radiant_team_name not in summary_data['Team']:
        summary_data['Team'].append(radiant_team_name)
        summary_data['TotalFantasyPoints'].append(0)  # Initialize the new column
        summary_data['Towers'].append(0)
        summary_data['Barracks'].append(0)
        summary_data['Roshans'].append(0)
        summary_data['FirstBloods'].append(0)
        

    radiant_index = summary_data['Team'].index(radiant_team_name)
    summary_data['Towers'][radiant_index] += match_data['RadiantTowersTaken']
    summary_data['Barracks'][radiant_index] += match_data['RadiantBarracksTaken']
    summary_data['Roshans'][radiant_index] += match_data['RadiantRoshans']
    if match_data['FirstBlood'] == radiant_team_name:
        summary_data['FirstBloods'][radiant_index] += 1

    # Add the Dire Team's stats
    if dire_team_name not in summary_data['Team']:
        summary_data['Team'].append(dire_team_name)
        summary_data['TotalFantasyPoints'].append(0)  # Initialize the new column
        summary_data['Towers'].append(0)
        summary_data['Barracks'].append(0)
        summary_data['Roshans'].append(0)
        summary_data['FirstBloods'].append(0)
        

    dire_index = summary_data['Team'].index(dire_team_name)
    summary_data['Towers'][dire_index] += match_data['DireTowersTaken']
    summary_data['Barracks'][dire_index] += match_data['DireBarracksTaken']
    summary_data['Roshans'][dire_index] += match_data['DireRoshans']
    if match_data['FirstBlood'] == dire_team_name:
        summary_data['FirstBloods'][dire_index] += 1

# Calculate Total Fantasy Points for each team
for index in range(len(summary_data['Team'])):
    total_points = (
        summary_data['Towers'][index] +
        summary_data['Barracks'][index] +
        3 * summary_data['Roshans'][index] +
        2 * summary_data['FirstBloods'][index]
    )/2
    summary_data['TotalFantasyPoints'][index] = total_points

summary_df = pd.DataFrame(summary_data)


# Create an ExcelWriter object to write multiple DataFrames to a single Excel file
with pd.ExcelWriter('team_data.xlsx', engine='xlsxwriter') as writer:

    # Export summary data to the 'Summary' sheet
    summary_df.to_excel(writer, sheet_name='TeamSummary', index=False)
