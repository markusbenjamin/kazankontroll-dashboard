import bisect
import csv
import copy
from datetime import datetime
import os
import matplotlib.pyplot as plt

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

def select(nested_list, condition_func):
    return [item for item in nested_list if condition_func(item)]

def transpose(rectangular_list):
    return [list(row) for row in zip(*rectangular_list)]

def mean(list):
    return sum(list)/len(list)

def load_albatros_data(daystamp = datetime.now().strftime("%Y-%m-%d"), time_offset = 0):
    with open(data_raw_path+"/"+daystamp+"/albatros_state.csv", 'r') as file:
        lines = []
        for line in file:
            minutes_since_midnight = 60*int(line.strip().split(",")[0].split(":")[0])+int(line.strip().split(",")[0].split(":")[1])+time_offset
            val = int(line.strip().split(",")[1])
            lines.append([minutes_since_midnight,val])
    
    return lines

def load_pump_data(daystamp = datetime.now().strftime("%Y-%m-%d"), time_offset = 0):
    with open(data_raw_path+"/"+daystamp+"/pump_states.csv", 'r') as file:
        lines = [[],[],[],[]]
        for line in file:
            minutes_since_midnight = 60*int(line.strip().split(",")[0].split(":")[0])+int(line.strip().split(",")[0].split(":")[1])+time_offset
            pump = int(line.strip().split(",")[1])-1
            val = int(line.strip().split(",")[2])
            lines[pump].append([minutes_since_midnight,val])

    return lines

def load_room_measured_temps_data(daystamp = datetime.now().strftime("%Y-%m-%d"), time_offset = 0):
    with open(data_raw_path+"/"+daystamp+"/measured_temps.csv", 'r') as file:
        lines = [[],[],[],[],[],[],[],[],[]]
        for line in file:
            minutes_since_midnight = 60*int(line.strip().split(",")[0].split(":")[0])+int(line.strip().split(",")[0].split(":")[1])+time_offset
            room = int(line.strip().split(",")[1])-1
            val = float(line.strip().split(",")[2])
            lines[room].append([minutes_since_midnight,val])

    return lines

def load_room_set_temps_data(daystamp = datetime.now().strftime("%Y-%m-%d"), time_offset = 0):
    with open(data_raw_path+"/"+daystamp+"/set_temps.csv", 'r') as file:
        lines = [[],[],[],[],[],[],[],[],[]]
        for line in file:
            minutes_since_midnight = 60*int(line.strip().split(",")[0].split(":")[0])+int(line.strip().split(",")[0].split(":")[1])+time_offset
            room = int(line.strip().split(",")[1])-1
            val1 = float(line.strip().split(",")[2])
            val2 = float(line.strip().split(",")[3])
            val3 = float(line.strip().split(",")[4])
            lines[room].append([minutes_since_midnight,val1,val2,val3])

    return lines

def load_external_temp_data(daystamp = datetime.now().strftime("%Y-%m-%d"), time_offset = 0):
    with open(data_raw_path+"/"+daystamp+"/external_temp.csv", 'r') as file:
        lines = []
        for line in file:
            minutes_since_midnight = 60*int(line.strip().split(",")[0].split(":")[0])+int(line.strip().split(",")[0].split(":")[1])+time_offset
            val = float(line.strip().split(",")[1])
            lines.append([minutes_since_midnight,val])
    
    return lines

def construct_and_save_formatted_heating_state(daystamp = datetime.now().strftime("%Y-%m-%d"), minute_step = 5):
    line_count = 0
    for minute in range(0, 24*60, minute_step):
        preceding, succeeding = find_closest_in_nested(albatros_state, minute)
        if preceding == 'n' and succeeding == 'n':
            albatros_val = 'n'
        elif preceding == 'n':
            albatros_val = 0 if succeeding[1] == 1 else 1
        else:
            albatros_val = preceding[1]

        pump_vals = ['n','n','n','n']
        for pump in range(4):
            preceding, succeeding = find_closest_in_nested(pump_states[0][pump] + pump_states[1][pump], minute)
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
    for room in range(9):
        line_count = 0
        two_days_temp = measured_temps[0][room-1] + measured_temps[1][room-1]
        two_days_set = set_temps[0][room-1] + set_temps[1][room-1]
        
        two_days_temp_repeated_readings_filtered = []
        for n in range(1,len(two_days_temp)):
            time = two_days_temp[n][0]
            temp = two_days_temp[n][1]
            pre_time = two_days_temp[n-1][0]
            pre_temp = two_days_temp[n-1][1]
            if temp != pre_temp:
                two_days_temp_repeated_readings_filtered.append([time,temp])


        two_days_temp_repeated_readings_filtered_smoothed = []
        time_step = 1
        time_window = 2 * 60
        for time in range(0, 24 * 60, time_step):
            window_vals = select(two_days_temp_repeated_readings_filtered, lambda x: time - time_window/2 < x[0] < time + time_window/2)
            if window_vals:
                time, temp = list(map(mean,transpose(window_vals)))
                two_days_temp_repeated_readings_filtered_smoothed.append([time,temp])

        no_signal_time_tolerance = 1*60
        for minute in range(0, 24 * 60, minute_step):
            entry_array = [minute]

            temp_entry = 'n'
            pre_val, su_val = find_closest_in_nested(two_days_temp_repeated_readings_filtered_smoothed, minute, compare_index = 0)
            if pre_val != 'n' and su_val != 'n':
                pre_time, pre_temp = pre_val
                su_time, su_temp = su_val

                if su_time - pre_time <= no_signal_time_tolerance:
                    time = minute
                    #temp = pre_temp + (su_temp-pre_temp)*((su_time - minute)/(su_time - pre_time))
                    temp = mean([pre_temp,su_temp])
                    temp_entry = round(temp,2)
                else:
                    temp_entry = 'n'
            elif pre_val != 'n' and minute - pre_val[1] < no_signal_time_tolerance:
                temp_entry = round(pre_val[1],2)
            else:
                temp_entry = 'n'
                
            entry_array.append(temp_entry)

            set_entry = []
            pre_val, su_val = find_closest_in_nested(two_days_set, minute, compare_index = 0)
            if pre_val == 'n' and su_val == 'n':
                set_entry = ['n','n','n']
            elif pre_val == 'n':
                set_entry = su_val[1:]
            else:
                set_entry = pre_val[1:]
            
            entry_array += set_entry

            entry = f"{entry_array[0]},{entry_array[1]},{entry_array[2]},{entry_array[3]},{entry_array[4]}"
            #print(entry)

            save_path = data_formatted_path + "/" + daystamp + "/"
            if not os.path.exists(save_path):
                os.makedirs(save_path)

            if line_count == 0:
                open(f'{save_path}/room_{room+1}_temps.csv', 'w', newline='')

            with open(f'{save_path}/room_{room+1}_temps.csv', 'a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(entry.split(','))
            line_count += 1

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
    daystamp_spec = '2023-11-26'
    minute_step_spec = 5

    try:
        albatros_state = load_albatros_data(daystamp = '2023-11-25', time_offset = -24*60)+ load_albatros_data(daystamp = '2023-11-26')
        pump_states = [
            load_pump_data(daystamp = '2023-11-25', time_offset = -24*60),
            load_pump_data(daystamp = '2023-11-26')
        ]
        construct_and_save_formatted_heating_state(daystamp = daystamp_spec, minute_step = minute_step_spec)
       
        measured_temps = [
            load_room_measured_temps_data(daystamp = '2023-11-25', time_offset = -24*60), #DEV: kell majd megfelelő daystampot generálni, ha már élesben fut serviceként
            load_room_measured_temps_data(daystamp = '2023-11-26')
        ]
        set_temps = [
            load_room_set_temps_data(daystamp = '2023-11-25', time_offset = -24*60),
            load_room_set_temps_data(daystamp = '2023-11-25')
        ]
        construct_and_save_formatted_room_temps_data(daystamp = daystamp_spec, minute_step = minute_step_spec)

        external_temp = load_external_temp_data(daystamp = daystamp_spec)
        construct_and_save_formatted_external_temp_data(daystamp = daystamp_spec, minute_step = minute_step_spec)
    except Exception as e:
        print(f"Couldn't format data due to {e}.")