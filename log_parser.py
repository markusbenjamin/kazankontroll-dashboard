# Imports
import csv
import json
import re
from datetime import datetime
import os

# Helpers
def line_JSONifier(bad_line):
    corrected_line = bad_line.replace("'", "\"")
    corrected_line = re.sub(r'([{,]\s*)(\d+)(\s*:\s*)', r'\1"\2"\3', corrected_line)
    corrected_line = re.sub(r'(:\s*)(\d+\.\d+|\d+|True|False)(\s*[},])', lambda m: f'{m.group(1)}"{m.group(2).lower()}"{m.group(3)}', corrected_line)
    return corrected_line

# Stub for config function
config = {}

with open('log_parser_config.csv') as configFile:
    for line in csv.reader(configFile):
        if line:
            key, value = line
            config[key] = value
    
    last_parsed_line = int(config.get('last_parsed_line', 0))

# Stub for main line sorter function
temp_measurements = []

current_line = 0
with open('log.log', 'r') as logFile:
    for line in logFile:
        if last_parsed_line < current_line and 'temp measurement' in line:
            JSONified_line = line_JSONifier(line)
            try:
                temp_measurements.append(json.loads(JSONified_line))
            except json.JSONDecodeError:
                print(f"Invalid JSON on line {current_line}:")
        current_line += 1

# Temperature data file generator function
def generate_measured_temps_data_file(temp_measurements):
    formatted_entries_by_date_and_room = {}

    for entry in temp_measurements:
        timestamp = entry['4']
        room_number = list(entry['3'].keys())[0] 
        temperature = entry['3'][room_number]
        date = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S').strftime('%Y_%m_%d')
        formatted_entries_by_date_and_room.setdefault((date, room_number), []).append((timestamp, temperature))

    for (date, room_number), data in formatted_entries_by_date_and_room.items():
        directory_name = f'measured_temps/{date}'
        file_name = f'{directory_name}/room_{room_number}.csv'

        if not os.path.exists(directory_name):
            os.makedirs(directory_name)

        with open(file_name, 'a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerows(data)

generate_measured_temps_data_file(temp_measurements)