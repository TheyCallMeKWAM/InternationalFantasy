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
winUnder25Bonus = 15
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

    #Adds All Bonus Points after getting score
    if player['kills'] + player['assists'] > 20:
        total_points += KABonus

    if game_duration < 25 and player['win'] == 1:
        total_points += winUnder25Bonus

    if player['win'] == 1:
        total_points += winBonus
    return round(total_points, 2)


def extract_player_stats(match_data):
    game_duration = match_data['duration'] // 60
    for player in match_data['players']:
        player_name = player.get('name', player.get('personaname', 'Unknown Player'))
        pro_name = player.get('name', 'Unknown Player')

        #Gets Pros Name and Sets all Values for them to 0
        if pro_name != 'Unknown Player':
            player_name = pro_name
        player_stats.setdefault(player_name, {
            'Kills': 0,
            'Deaths': 0,
            'Assists': 0,
            'LastHits': 0,
            'Denies': 0,
            'WardsPlaced': 0,
            'FantasyPoints': 0,
        })
        #Gets all Stats from Game Data
        player_stats[player_name]['Kills'] += player['kills']
        player_stats[player_name]['Deaths'] += player['deaths']
        player_stats[player_name]['Assists'] += player['assists']
        player_stats[player_name]['LastHits'] += player['last_hits']
        player_stats[player_name]['Denies'] += player['denies']
        player_stats[player_name]['WardsPlaced'] += wardsPlaced
        #Calls for the Calculation of the Data
        player_stats[player_name]['FantasyPoints'] += calculate_fantasy_points(player, game_duration)


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
        extract_player_stats(match_data)
    
    processed_match_ids.add(match_id)
# Create a DataFrame with player names, stats, K/A Bonus, Win Bonus, and total fantasy points
players_data_df = pd.DataFrame.from_dict(player_stats, orient='index')

players_data_df = players_data_df[['Kills', 'Deaths', 'Assists', 'LastHits', 'Denies', 'WardsPlaced', 'FantasyPoints']]


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