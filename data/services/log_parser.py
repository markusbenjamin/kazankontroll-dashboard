import csv
from datetime import datetime
import json
import os

script_path = os.path.abspath(__file__)
script_dir = os.path.dirname(script_path)
root_root = os.path.abspath(os.path.join(script_dir, '..', '..','..'))
logs_path = os.path.join(root_root, 'kazankontroll','logs/')
data_raw_path = os.path.join(root_root, 'kazankontroll-dashboard','data/raw')

def load_daily_log(logfile_name = 'log'):
    log_lines = []
    with open(logs_path+logfile_name, 'r') as file:
        for line in file:
            try:
                json.loads(line)  # Attempt to parse the line as JSON
                log_lines.append(json.loads(line) )  # Add to the list if successful
            except json.JSONDecodeError:
                continue  # Skip the line if there's a JSON parsing error

    return log_lines

def filter_log_lines(log_lines, key, value):
    return [line for line in log_lines if line.get(key) == value]

def extract_and_save_measured_temps(log_lines):
    filtered_lines = filter_log_lines(log_lines,"2","temp measurement")
    line_count = 0
    for line in filtered_lines:
        if "sensor" not in line["3"].keys():
            ymd_stamp = datetime.strptime(line["4"],"%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d")
            hms_stamp = datetime.strptime(line["4"],"%Y-%m-%d %H:%M:%S").strftime("%H:%M:%S")
            room = list(line["3"].keys())[0]
            temp = list(line["3"].values())[0]
            entry = f'{hms_stamp},{room},{temp}'
            #print(entry)

            save_path = os.path.join(data_raw_path, ymd_stamp)
            
            if not os.path.exists(save_path):
                os.makedirs(save_path)

            if line_count == 0:
                open(f'{save_path}/measured_temps.csv', 'w', newline='')

            with open(f'{save_path}/measured_temps.csv', 'a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(entry.split(','))
            
            line_count += 1

def extract_and_save_set_temps(log_lines):
    filtered_lines = filter_log_lines(log_lines,"2","set temp")
    line_count = 0
    for line in filtered_lines:
        ymd_stamp = datetime.strptime(line["4"],"%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d")
        hms_stamp = datetime.strptime(line["4"],"%Y-%m-%d %H:%M:%S").strftime("%H:%M:%S")
        room = list(line["3"].keys())[0]
        temp = list(line["3"].values())[0]
        buff_low = -1
        if "buff low" in line["3"].keys():
            buff_low = line["3"]["buff low"]
        buff_high = -1
        if "buff high" in line["3"].keys():
            buff_high = line["3"]["buff high"]
            
        entry = f'{hms_stamp},{room},{temp},{buff_low},{buff_high}'
        #print(entry)

        save_path = os.path.join(data_raw_path, ymd_stamp)
        
        if not os.path.exists(save_path):
            os.makedirs(save_path)

        if line_count == 0:
            open(f'{save_path}/set_temps.csv', 'w', newline='')

        with open(f'{save_path}/set_temps.csv', 'a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(entry.split(','))
        
        line_count += 1

def extract_and_save_external_temp(log_lines):
    filtered_lines = filter_log_lines(log_lines,"2","external temp")
    line_count = 0
    for line in filtered_lines:
        ymd_stamp = datetime.strptime(line["4"],"%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d")
        hms_stamp = datetime.strptime(line["4"],"%Y-%m-%d %H:%M:%S").strftime("%H:%M:%S")
        temp = line["3"]
        entry = f'{hms_stamp},{temp}'
        #print(entry)

        save_path = os.path.join(data_raw_path, ymd_stamp)
        
        if not os.path.exists(save_path):
            os.makedirs(save_path)

        if line_count == 0:
            open(f'{save_path}/external_temp.csv', 'w', newline='')

        with open(f'{save_path}/external_temp.csv', 'a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(entry.split(','))

        line_count += 1

def extract_and_save_pump_states(log_lines):
    filtered_lines = filter_log_lines(filter_log_lines(log_lines,"1","state"),"2","pump")
    line_count = 0
    for line in filtered_lines:
        ymd_stamp = datetime.strptime(line["4"],"%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d")
        hms_stamp = datetime.strptime(line["4"],"%Y-%m-%d %H:%M:%S").strftime("%H:%M:%S")
        pump = list(line["3"].keys())[0]
        state = list(line["3"].values())[0]
        entry = f'{hms_stamp},{pump},{state}'
        #print(entry)

        save_path = os.path.join(data_raw_path, ymd_stamp)
        
        if not os.path.exists(save_path):
            os.makedirs(save_path)

        if line_count == 0:
            open(f'{save_path}/pump_states.csv', 'w', newline='')

        with open(f'{save_path}/pump_states.csv', 'a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(entry.split(','))
        
        line_count += 1

def extract_and_save_albatros_state(log_lines):
    filtered_lines = filter_log_lines(filter_log_lines(log_lines,"1","state"),"2","albatros")
    line_count = 0
    for line in filtered_lines:
        ymd_stamp = datetime.strptime(line["4"],"%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d")
        hms_stamp = datetime.strptime(line["4"],"%Y-%m-%d %H:%M:%S").strftime("%H:%M:%S")
        state = line["3"]
        entry = f'{hms_stamp},{state}'
        #print(entry)

        save_path = os.path.join(data_raw_path, ymd_stamp)
        
        if not os.path.exists(save_path):
            os.makedirs(save_path)

        if line_count == 0:
            open(f'{save_path}/albatros_state.csv', 'w', newline='')

        with open(f'{save_path}/albatros_state.csv', 'a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(entry.split(','))
        
        line_count += 1


def find_problematic_line(file_path):
    with open(file_path, 'r') as file:
        for i, line in enumerate(file, start=1):
            try:
                json.loads(line)
            except json.JSONDecodeError:
                return f"Error in line {i}: {line.strip()}"

if __name__ == "__main__":
    try:
        daily_log_lines = load_daily_log(logfile_name = 'log')
        extract_and_save_measured_temps(daily_log_lines)
        extract_and_save_set_temps(daily_log_lines)
        extract_and_save_external_temp(daily_log_lines)
        extract_and_save_pump_states(daily_log_lines)
        extract_and_save_albatros_state(daily_log_lines)
        print(f"Successfully parsed logs.")
    except Exception as e:
        print(f"Couldn't parse logs due to {e}.")