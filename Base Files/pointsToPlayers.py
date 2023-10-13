import requests
import pandas as pd
import numpy as np

# Define empty dictionaries to store player stats and match stats
player_stats = {}
match_stats = {}

# Point Settings
killPoints = 3
assitPoints = 2
deathPoints = -1
lasthitPoints = 0.02
denyPoints = 0.02
wardsPlaced = 0.2
winUnder25 = 15
KABonus = 2
winBonus = 15

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

def calculate_fantasy_points(player, game_duration):
    kills = player['kills'] * killPoints
    assists = player['assists'] * assitPoints
    deaths = player['deaths'] * deathPoints
    last_hits = player['last_hits'] * lasthitPoints
    denies = player['denies'] * denyPoints
    obs_placed = player.get('obs_placed', 0) or 0
    sen_placed = player.get('sen_placed', 0) or 0
    wards_placed = (obs_placed + sen_placed) * wardsPlaced
    total_points = kills + assists + deaths + last_hits + denies + wards_placed
    # Check if the game duration is under 25 minutes and the player is on the winning team
    if game_duration < 25 and player['win'] == 1:
        total_points += winUnder25  # Add 15 bonus points
    return round(total_points, 2)

def extract_player_stats(match_data):
    game_duration = match_data['duration'] // 60  # Convert duration to minutes
    for player in match_data['players']:
        player_name = player.get('name', player.get('personaname', 'Unknown Player'))
        pro_name = player.get('name', 'Unknown Player')
        # Check if the player has a professional name
        if pro_name != 'Unknown Player':
            player_name = pro_name
        player_stats.setdefault(player_name, {
            'Kills': 0,
            'Deaths': 0,
            'Assists': 0,
            'LastHits': 0,
            'Denies': 0,
            'WardsPlaced': 0,
            'KABonus': 0,
            'WinBonus': 0,
            'FantasyPoints': 0,
        })
        player_stats[player_name]['Kills'] += player['kills']
        player_stats[player_name]['Deaths'] += player['deaths']
        player_stats[player_name]['Assists'] += player['assists']
        player_stats[player_name]['LastHits'] += player['last_hits']
        player_stats[player_name]['Denies'] += player['denies']
        obs_placed = player.get('obs_placed', 0) or 0
        sen_placed = player.get('sen_placed', 0) or 0
        player_stats[player_name]['WardsPlaced'] += (obs_placed + sen_placed)
        player_stats[player_name]['FantasyPoints'] += calculate_fantasy_points(player, game_duration)
        # Check if K/A Bonus is earned
        if player['kills'] + player['assists'] > 20:
            player_stats[player_name]['KABonus'] += KABonus
        # Check if the player is on the winning team and the game duration is under 25 minutes
        if player['win'] == 1 and game_duration < 25:
            player_stats[player_name]['WinBonus'] += winBonus

def extract_match_stats(match_id):
    match_data = get_match_details(match_id)
    if match_data:
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

# Fetch and process match data for each match ID
for match_id in match_ids:
    match_data = get_match_details(match_id)
    if match_data:
        extract_player_stats(match_data)
        match_stats[match_id] = extract_match_stats(match_id)

# Create a DataFrame with player names, stats, K/A Bonus, Win Bonus, and total fantasy points
players_data_df = pd.DataFrame.from_dict(player_stats, orient='index')

# Reorder columns to have KABonus and WinBonus after Assists
players_data_df = players_data_df[['Kills', 'Deaths', 'Assists', 'KABonus', 'LastHits', 'Denies', 'WardsPlaced', 'WinBonus', 'FantasyPoints']]

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
        summary_data['Towers'].append(0)
        summary_data['Barracks'].append(0)
        summary_data['Roshans'].append(0)
        summary_data['FirstBloods'].append(0)
        summary_data['TotalFantasyPoints'].append(0)  # Initialize the new column

    radiant_index = summary_data['Team'].index(radiant_team_name)
    summary_data['Towers'][radiant_index] += match_data['RadiantTowersTaken']
    summary_data['Barracks'][radiant_index] += match_data['RadiantBarracksTaken']
    summary_data['Roshans'][radiant_index] += match_data['RadiantRoshans']
    if match_data['FirstBlood'] == radiant_team_name:
        summary_data['FirstBloods'][radiant_index] += 1

    # Add the Dire Team's stats
    if dire_team_name not in summary_data['Team']:
        summary_data['Team'].append(dire_team_name)
        summary_data['Towers'].append(0)
        summary_data['Barracks'].append(0)
        summary_data['Roshans'].append(0)
        summary_data['FirstBloods'].append(0)
        summary_data['TotalFantasyPoints'].append(0)  # Initialize the new column

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
    )
    summary_data['TotalFantasyPoints'][index] = total_points

summary_df = pd.DataFrame(summary_data)


# Create a list of player names after processing the match data
player_names = list(player_stats.keys())

# Print the list of player names separated by commas
print("Player Names:", ", ".join(player_names))

# Create a dictionary to store participant data
participant_data = {}

while True:
    participant_name = input("Enter a participant's name (or type 'done' to finish): ")
    if participant_name.lower() == 'done':
        break
    elif participant_name not in participant_data:
        participant_data[participant_name] = {}  # Initialize an empty dictionary for the participant
        selected_contestants_input = input(f"Select contestants for {participant_name} from the original list separated by commas: ")
        selected_contestants = [name.strip() for name in selected_contestants_input.split(',')]

        # Associate the player with the selected contestants for the participant
        for i, selected_contestant in enumerate(selected_contestants):
            if selected_contestant in player_names:
                fantasy_points = player_stats[selected_contestant]['FantasyPoints']
                # Multiply the score by 1.5 for the first selected player
                if i == 0:
                    fantasy_points *= 1.5
                participant_data[participant_name][selected_contestant] = fantasy_points
            else:
                print(f"{selected_contestant} is not in the original list.")
    else:
        print(f"{participant_name} has already been entered. Please choose a different name.")

# Create a list of dictionaries for participant and player data
data_list = []

# Iterate through the participant data and add dictionaries to the list
for participant, selections in participant_data.items():
    for player, points in selections.items():
        data_list.append({'Participant': participant, 'Player': player, 'Score': points})

# Create a DataFrame from the list of dictionaries
participant_player_data = pd.DataFrame(data_list)

# Calculate the total score for each participant
total_scores = participant_player_data.groupby('Participant')['Score'].sum().reset_index()
total_scores.columns = ['Participant', 'TotalScore']

# Merge the total_scores DataFrame with the participant_player_data DataFrame
participant_player_data = participant_player_data.merge(total_scores, on='Participant', how='left')

# Create an ExcelWriter object to write multiple DataFrames to a single Excel file
with pd.ExcelWriter('participant_player_data.xlsx', engine='xlsxwriter') as writer:

    # Export participant and player data to the 'PlayerSummary' sheet
    participant_player_data.to_excel(writer, sheet_name='PlayerSummary', index=False)

    # Export summary data to the 'Summary' sheet
    summary_df.to_excel(writer, sheet_name='TeamSummary', index=False)
