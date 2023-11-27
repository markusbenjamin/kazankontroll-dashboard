import bisect
import csv
from datetime import datetime
import os

def find_closest_in_nested(sorted_list, target, compare_index = 0):
    """Finds the closest values around the target in a sorted nested list."""
    if len(sorted_list) != 0:
        # Extract the comparison elements
        compare_elements = [item[compare_index] for item in sorted_list]

        # Find the position in the comparison list
        idx = bisect.bisect_left(compare_elements, target)

        # Determine the preceding and succeeding elements
        preceding = sorted_list[idx - 1] if idx > 0 else "n"
        succeeding = sorted_list[idx] if idx < len(sorted_list) else "n"
    else:
        preceding = 'n'
        succeeding = 'n'

    return preceding, succeeding

def load_albatros_data(daystamp = datetime.now().strftime("%Y-%m-%d")):
    with open(data_raw_path+"/"+daystamp+"/albatros_state.csv", 'r') as file:
        lines = []
        for line in file:
            minutes_since_midnight = 60*int(line.strip().split(",")[0].split(":")[0])+int(line.strip().split(",")[0].split(":")[1])
            val = int(line.strip().split(",")[1])
            lines.append([minutes_since_midnight,val])
    
    return lines

def load_pump_data(daystamp = datetime.now().strftime("%Y-%m-%d")):
    with open(data_raw_path+"/"+daystamp+"/pump_states.csv", 'r') as file:
        lines = [[],[],[],[]]
        for line in file:
            minutes_since_midnight = 60*int(line.strip().split(",")[0].split(":")[0])+int(line.strip().split(",")[0].split(":")[1])
            pump = int(line.strip().split(",")[1])-1
            val = int(line.strip().split(",")[2])
            lines[pump].append([minutes_since_midnight,val])

    return lines

def load_room_measured_temps_data(daystamp = datetime.now().strftime("%Y-%m-%d")):
    with open(data_raw_path+"/"+daystamp+"/measured_temps.csv", 'r') as file:
        lines = [[],[],[],[],[],[],[],[],[]]
        for line in file:
            minutes_since_midnight = 60*int(line.strip().split(",")[0].split(":")[0])+int(line.strip().split(",")[0].split(":")[1])
            room = int(line.strip().split(",")[1])-1
            val = float(line.strip().split(",")[2])
            lines[room].append([minutes_since_midnight,val])

    return lines

def load_room_set_temps_data(daystamp = datetime.now().strftime("%Y-%m-%d")):
    with open(data_raw_path+"/"+daystamp+"/set_temps.csv", 'r') as file:
        lines = [[],[],[],[],[],[],[],[],[]]
        for line in file:
            minutes_since_midnight = 60*int(line.strip().split(",")[0].split(":")[0])+int(line.strip().split(",")[0].split(":")[1])
            room = int(line.strip().split(",")[1])-1
            val1 = float(line.strip().split(",")[2])
            val2 = float(line.strip().split(",")[3])
            val3 = float(line.strip().split(",")[4])
            lines[room].append([minutes_since_midnight,val1,val2,val3])

    return lines

def load_external_temp_data(daystamp = datetime.now().strftime("%Y-%m-%d")):
    with open(data_raw_path+"/"+daystamp+"/external_temp.csv", 'r') as file:
        lines = []
        for line in file:
            minutes_since_midnight = 60*int(line.strip().split(",")[0].split(":")[0])+int(line.strip().split(",")[0].split(":")[1])
            val = float(line.strip().split(",")[1])
            lines.append([minutes_since_midnight,val])
    
    return lines

def construct_and_save_formatted_heating_state(daystamp = datetime.now().strftime("%Y-%m-%d"), minute_step = 5):
    line_count = 0
    for minute in range(0,24*60,minute_step):
        preceding, succeeding = find_closest_in_nested(albatros_state, minute)
        if preceding == 'n' and succeeding == 'n':
            albatros_val = 0
        elif preceding == 'n':
            albatros_val = 0 if succeeding[1] == 1 else 1
        else:
            albatros_val = preceding[1]

        pump_vals = ['n','n','n','n']
        for pump in range(4):
            preceding,succeeding = find_closest_in_nested(pump_states[pump],minute)
            if preceding == 'n' and succeeding == 'n':
                pump_vals[pump] = 0
            elif preceding == 'n':
                pump_vals[pump] = 0 if succeeding[1] == 1 else 1
            else:
                pump_vals[pump] = preceding[1]

        entry = f"{minute},{albatros_val},{pump_vals[0]},{pump_vals[1]},{pump_vals[2]},{pump_vals[3]}"
        #print(entry)

        save_path = data_formatted_path+"/"+daystamp+"/"
        if not os.path.exists(save_path):
            os.makedirs(save_path)

        if line_count == 0:
            open(f'{save_path}/heating_state.csv', 'w', newline='')

        with open(f'{save_path}/heating_state.csv', 'a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(entry.split(','))
        line_count += 1

def construct_and_save_formatted_room_temps_data(daystamp = datetime.now().strftime("%Y-%m-%d"), minute_step = 5):
    line_count = [0,0,0,0,0,0,0,0,0]
    for minute in range(0,24*60,minute_step):
        room_vals = [
            ['n','n','n','n'],
            ['n','n','n','n'],
            ['n','n','n','n'],
            ['n','n','n','n'],
            ['n','n','n','n'],
            ['n','n','n','n'],
            ['n','n','n','n'],
            ['n','n','n','n'],
            ['n','n','n','n']
            ]
        for room in range(9):
            preceding,succeeding = find_closest_in_nested(measured_temps[room],minute)
            if preceding == 'n' and succeeding == 'n':
                room_vals[room][0] = 'n'
            elif preceding == 'n':
                room_vals[room][0] = round(succeeding[1],2)
            elif succeeding == 'n':
                room_vals[room][0] = round(preceding[1],2)
            else:
                linear_interpolation_time = (minute-preceding[0])/(succeeding[0]-preceding[0])
                room_vals[room][0] = round(preceding[1]+(succeeding[1]-preceding[1])*linear_interpolation_time,2)

            preceding,succeeding = find_closest_in_nested(set_temps[room],minute)
            if preceding == 'n' and succeeding == 'n':
                room_vals[room][1] = 'n'
                room_vals[room][3] = 'n'
                room_vals[room][4] = 'n'
            elif preceding == 'n':
                room_vals[room][1] = succeeding[1]
                room_vals[room][2] = succeeding[2]
                room_vals[room][3] = succeeding[3]
            else:
                room_vals[room][1] = preceding[1]
                room_vals[room][2] = preceding[2]
                room_vals[room][3] = preceding[3]

            entry = f"{minute},{room_vals[room][0]},{room_vals[room][1]},{room_vals[room][2]},{room_vals[room][3]}"
            #print(entry)

            save_path = data_formatted_path+"/"+daystamp+"/"
            if not os.path.exists(save_path):
                os.makedirs(save_path)

            if line_count[room] == 0:
                open(f'{save_path}/room_{room+1}_temps.csv', 'w', newline='')

            with open(f'{save_path}/room_{room+1}_temps.csv', 'a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(entry.split(','))
            line_count[room] += 1

def construct_and_save_formatted_external_temp_data(daystamp = datetime.now().strftime("%Y-%m-%d"), minute_step = 5):
    line_count = 0
    for minute in range(0,24*60,minute_step):
        preceding, succeeding = find_closest_in_nested(external_temp, minute)
        if preceding == 'n' and succeeding == 'n':
            external_temp_val = 'n'
        elif preceding == 'n':
            external_temp_val = round(succeeding[1],2)
        elif succeeding == 'n':
            external_temp_val = round(preceding[1],2)
        else:
            linear_interpolation_time = (minute-preceding[0])/(succeeding[0]-preceding[0])
            external_temp_val = round(preceding[1]+(succeeding[1]-preceding[1])*linear_interpolation_time,2)

        entry = f"{minute},{external_temp_val}"
        #print(entry)

        save_path = data_formatted_path+"/"+daystamp+"/"
        if not os.path.exists(save_path):
            os.makedirs(save_path)

        if line_count == 0:
            open(f'{save_path}/external_temp.csv', 'w', newline='')

        with open(f'{save_path}/external_temp.csv', 'a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(entry.split(','))
        line_count += 1


if __name__ == "__main__":
    script_path = os.path.abspath(__file__)
    script_dir = os.path.dirname(script_path)
    root_root = os.path.abspath(os.path.join(script_dir, '..', '..','..'))
    data_raw_path = os.path.join(root_root, 'kazankontroll-dashboard','data/raw')
    data_formatted_path = os.path.join(root_root, 'kazankontroll-dashboard','data/formatted')
    daystamp_spec = '2023-11-25'
    minute_step_spec = 5

    try:
        albatros_state = load_albatros_data(daystamp = daystamp_spec)
        pump_states = load_pump_data(daystamp = daystamp_spec)
        construct_and_save_formatted_heating_state(daystamp = daystamp_spec, minute_step = minute_step_spec)
       
        measured_temps = load_room_measured_temps_data(daystamp = daystamp_spec)
        set_temps = load_room_set_temps_data(daystamp = daystamp_spec)
        construct_and_save_formatted_room_temps_data(daystamp = daystamp_spec, minute_step = minute_step_spec)

        external_temp = load_external_temp_data(daystamp = daystamp_spec)
        construct_and_save_formatted_external_temp_data(daystamp = daystamp_spec, minute_step = minute_step_spec)
    except Exception as e:
        print(f"Couldn't format data due to {e}.")