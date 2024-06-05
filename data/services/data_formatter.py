import bisect
import csv
import copy
from datetime import datetime, timedelta
import os
#import matplotlib.pyplot as plt #DEV
import subprocess
import ast

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
        lines = [[],[],[],[],[],[],[],[],[],[]]
        for line in file:
            minutes_since_midnight = 60*int(line.strip().split(",")[0].split(":")[0])+int(line.strip().split(",")[0].split(":")[1])+time_offset
            room = int(line.strip().split(",")[1])
            val = float(line.strip().split(",")[2])
            lines[room - 1].append([minutes_since_midnight,val])

    return lines

def load_room_set_temps_data(daystamp = datetime.now().strftime("%Y-%m-%d"), time_offset = 0):
    with open(data_raw_path+"/"+daystamp+"/set_temps.csv", 'r') as file:
        lines = [[],[],[],[],[],[],[],[],[],[]]
        for line in file:
            minutes_since_midnight = 60*int(line.strip().split(",")[0].split(":")[0])+int(line.strip().split(",")[0].split(":")[1])+time_offset
            room = int(line.strip().split(",")[1])
            val1 = float(line.strip().split(",")[2])
            val2 = float(line.strip().split(",")[3])
            val3 = float(line.strip().split(",")[4])
            lines[room - 1].append([minutes_since_midnight,val1,val2,val3])

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
    for room in range(10):
        line_count = 0
        two_days_temp = measured_temps[0][room] + measured_temps[1][room]
        two_days_set = set_temps[0][room] + set_temps[1][room]
        
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

def process_and_save_gas_pulse_data(daystamp = datetime.now().strftime("%Y-%m-%d"), minute_step = 5):
    pulse_conversion_factor = 0.1
    gas_impulse_times_raw = []
    prev_daystamp = (datetime.strptime(daystamp,"%Y-%m-%d") + timedelta(days = -1)).strftime("%Y-%m-%d")
    with open(data_raw_path + "/" + prev_daystamp + "/gas_pulse_times.txt", 'r') as file:
        for line in file:
            seconds_since_midnight = 60*60*int(line.split(":")[0]) + 60*int(line.split(":")[1]) + round(float(line.strip().split(":")[2])) - 60*60*24
            gas_impulse_times_raw.append(seconds_since_midnight)
    with open(data_raw_path + "/" + daystamp + "/gas_pulse_times.txt", 'r') as file:
        for line in file:
            seconds_since_midnight = 60*60*int(line.split(":")[0]) + 60*int(line.split(":")[1]) + round(float(line.strip().split(":")[2]))
            gas_impulse_times_raw.append(seconds_since_midnight)
    
    gas_impulse_double_readings_filtered = []
    for n in range(1,len(gas_impulse_times_raw)):
        if 5 <= gas_impulse_times_raw[n] - gas_impulse_times_raw[n-1]:
            gas_impulse_double_readings_filtered.append(gas_impulse_times_raw[n]/60)

    gas_pulse_count = []
    total_pulse_count = 0
    gas_stock = []
    line_count = 0
    for time in range(0, 24*60, minute_step):
        count = len(select(gas_impulse_double_readings_filtered, lambda x: time - minute_step < x <= time))
        gas_pulse_count.append([time,count])
        total_pulse_count += count
        total_volume = total_pulse_count * pulse_conversion_factor
        gas_stock.append([time,total_volume])
        entry = f'{time},{total_volume}'
        
        save_path = data_formatted_path+"/"+daystamp+"/"
        if not os.path.exists(save_path):
            os.makedirs(save_path)

        if line_count == 0:
            open(f'{save_path}/gas_stock.csv', 'w', newline='')

        with open(f'{save_path}/gas_stock.csv', 'a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(entry.split(','))
        line_count += 1

    gas_smooth_window = 1*60
    gas_flow = []
    line_count = 0
    for time in range(0, 24*60, minute_step):
        gas_pulse_count_part = transpose(select(gas_pulse_count, lambda x: time - gas_smooth_window < x[0] <= time))
        if gas_pulse_count_part:
            flow = mean(gas_pulse_count_part[1])*pulse_conversion_factor
            gas_flow.append([time,flow])
            entry = f'{time},{flow}'
        
            save_path = data_formatted_path+"/"+daystamp+"/"
            if not os.path.exists(save_path):
                os.makedirs(save_path)

            if line_count == 0:
                open(f'{save_path}/gas_flow.csv', 'w', newline='')

            with open(f'{save_path}/gas_flow.csv', 'a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(entry.split(','))
            line_count += 1

def process_and_save_heatmeter_readings(daystamp = datetime.now().strftime("%Y-%m-%d"), minute_step = 5, time_offset = 0):
    processed_day = datetime.strptime(daystamp, "%Y-%m-%d")
    belief_states = [[],[],[],[]]
    last_prior_times = [None, None, None, None]
    for load_day in [processed_day + timedelta(days=-1), processed_day]:
        with open(os.path.join(data_raw_path, load_day.strftime("%Y-%m-%d"),"heatmeter_belief_state.csv"),'r') as belief_file:
            for line in belief_file.readlines():
                cycle_parts = line.split(';')

                for cycle in range(1, 5):
                    timed_prior = [
                            (datetime.strptime(cycle_parts[cycle - 1].split(',', maxsplit = 1)[0],"%Y%m%d%H%M") - processed_day).total_seconds()/60,
                            ast.literal_eval(cycle_parts[cycle - 1].split(',', maxsplit = 1)[1])
                        ]
                    if timed_prior[0] != last_prior_times[cycle - 1]:
                        belief_states[cycle - 1].append(timed_prior)
                        last_prior_times[cycle - 1] = timed_prior[0]

    pump_state_changes = [[],[],[],[]]
    last_state_for_pump = [-1,-1,-1,-1] # To only load changes in state
    for load_day in [processed_day + timedelta(days=-1), processed_day]:
        with open(os.path.join(data_raw_path, load_day.strftime("%Y-%m-%d"),'pump_states.csv'), 'r') as file:
            for line in file.readlines():
                pump_statechange_time = (datetime.strptime(f'{load_day.strftime("%Y-%m-%d ") }{line.strip().split(",")[0]}',"%Y-%m-%d %H:%M:%S")-processed_day).total_seconds()/60
                cycle = int(line.strip().split(",")[1])
                state = int(line.strip().split(",")[2])
                if last_state_for_pump[cycle - 1] != state:
                    pump_state_changes[cycle - 1].append([pump_statechange_time, state])
                    last_state_for_pump[cycle - 1] = state

    heating_periods = [[],[],[],[]]
    for cycle in range(1,5):
        start_time = None
        for time, status in pump_state_changes[cycle - 1]:
            if status == 1 and start_time is None:
                start_time = time
            elif status == 0 and start_time is not None:
                heating_periods[cycle - 1].append((start_time, time))
                start_time = None

    epost_estimates = [[],[],[],[]]
    for cycle in range(1,5):
        for belief_state in belief_states[cycle - 1]:
            epost_estimate = [
                belief_state[0],
                round(sum(key * value for key, value in belief_state[1].items()))
            ]
            epost_estimates[cycle - 1].append(epost_estimate)

    heating_signposts = [[],[],[],[]]
    for cycle in range(1,5):
        for heating_period in heating_periods[cycle - 1]:
            preceding, succeeding = find_closest_in_nested(epost_estimates[cycle - 1],heating_period[0],0)
            if preceding != 'n':
                heating_signposts[cycle - 1].append([heating_period[0],preceding[1]])
    
    heat_stock = []
    for cycle in range(1,5):
        heat_stock.append(sorted(epost_estimates[cycle - 1] + heating_signposts[cycle - 1]))

    interpolation_base = heat_stock
    minute_step = 5
    heat_stock_interpolated = []
    line_count = 0
    for minute in range(0, 24*60, minute_step):
        line = [minute]
        for cycle in range(1,5):
            preceding, succeeding = find_closest_in_nested(interpolation_base[cycle - 1],minute,0)
            val = 'n'
            if preceding != 'n':
                preceding_time = preceding[0]
                preceding_state = preceding[1]
                if succeeding != 'n':
                    succeeding_time = succeeding[0]
                    succeeding_state = succeeding[1]
                    val = preceding_state + (succeeding_state - preceding_state)*(minute - preceding_time)/(succeeding_time - preceding_time)
                else:
                    val = preceding_state

            line.append(val)
        
        heat_stock_interpolated.append(line)
        entry = f"{minute},{line[1]},{line[2]},{line[3]},{line[4]}"
        
        save_path = data_formatted_path+"/"+daystamp+"/"
        if not os.path.exists(save_path):
            os.makedirs(save_path)

        if line_count == 0:
            open(f'{save_path}/heat_stock.csv', 'w', newline='')

        with open(f'{save_path}/heat_stock.csv', 'a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(entry.split(','))
        line_count += 1

    heat_power_raw = [[],[],[],[]]
    time_step = 1
    for minute in range(0, 24*60 - time_step, time_step):
        for cycle in range(4):
            preceding, succeeding = find_closest_in_nested(heat_stock_interpolated, minute ,0)
            if preceding != 'n' and succeeding != 'n':
                preceding_time = preceding[0]
                preceding_stock = preceding[cycle + 1]
                succeeding_time = succeeding[0]
                succeeding_stock = succeeding[cycle + 1]

                time = (preceding_time + succeeding_time) / 2
                power = (succeeding_stock - preceding_stock) / (succeeding_time - preceding_time)

                heat_power_raw[cycle].append([time, power])
    
    power_smooth_window = 60
    heat_power_smooth = [[],[],[],[]]
    for minute in range(0, 24*60 - time_step, time_step):
        for cycle in range(4):
            power_smoothed = list(map(mean,transpose(select(heat_power_raw[cycle], lambda x: minute - power_smooth_window < x[0] <= minute))))
            if power_smoothed:
                heat_power_smooth[cycle].append([minute, power_smoothed[1]])

    heat_power_interpolated = []
    line_count = 0
    for minute in range(minute_step,24*60,minute_step):
        cycle_entries = ['n','n','n','n']
        for cycle in range(4):
            preceding, succeeding = find_closest_in_nested(heat_power_smooth[cycle], minute ,0)
            if preceding != 'n' and succeeding != 'n':
                preceding_time = preceding[0]
                preceding_power = preceding[1]
                succeeding_time = succeeding[0]
                succeeding_power = succeeding[1]
                interpolating_factor = (minute - preceding_time)/(succeeding_time - preceding_time)
                cycle_entries[cycle] = round(preceding_power*(1-interpolating_factor) + succeeding_power*interpolating_factor,5)
            elif preceding != 'n':
                preceding_time = preceding[0]
                preceding_power = preceding[1]
                cycle_entries[cycle] = round(preceding_power,5)
            else:
                cycle_entries[cycle] = 0
            
        heat_power_interpolated.append([minute,cycle_entries[0],cycle_entries[1],cycle_entries[2],cycle_entries[3]])
        entry = f"{minute},{cycle_entries[0]},{cycle_entries[1]},{cycle_entries[2]},{cycle_entries[3]}"
        
        save_path = data_formatted_path+"/"+daystamp+"/"
        if not os.path.exists(save_path):
            os.makedirs(save_path)

        if line_count == 0:
            open(f'{save_path}/heat_flow.csv', 'w', newline='')

        with open(f'{save_path}/heat_flow.csv', 'a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(entry.split(','))
        line_count += 1

def process_and_save_heatmeter_readings_net(daystamp = datetime.now().strftime("%Y-%m-%d"), minute_step = 5, time_offset = 0):
    processed_day = datetime.strptime(daystamp, "%Y-%m-%d")
    belief_states = [[],[],[],[]]
    last_prior_times = [None, None, None, None]
    for load_day in [processed_day + timedelta(days=-1), processed_day]:
        with open(os.path.join(data_raw_path, load_day.strftime("%Y-%m-%d"),"heatmeter_belief_state_net.csv"),'r') as belief_file:
            for line in belief_file.readlines():
                cycle_parts = line.split(';')

                for cycle in range(1, 5):
                    timed_prior = [
                            (datetime.strptime(cycle_parts[cycle - 1].split(',', maxsplit = 1)[0],"%Y%m%d%H%M") - processed_day).total_seconds()/60,
                            ast.literal_eval(cycle_parts[cycle - 1].split(',', maxsplit = 1)[1])
                        ]
                    if timed_prior[0] != last_prior_times[cycle - 1]:
                        belief_states[cycle - 1].append(timed_prior)
                        last_prior_times[cycle - 1] = timed_prior[0]

    pump_state_changes = [[],[],[],[]]
    last_state_for_pump = [-1,-1,-1,-1] # To only load changes in state
    for load_day in [processed_day + timedelta(days=-1), processed_day]:
        with open(os.path.join(data_raw_path, load_day.strftime("%Y-%m-%d"),'pump_states.csv'), 'r') as file:
            for line in file.readlines():
                pump_statechange_time = (datetime.strptime(f'{load_day.strftime("%Y-%m-%d ") }{line.strip().split(",")[0]}',"%Y-%m-%d %H:%M:%S")-processed_day).total_seconds()/60
                cycle = int(line.strip().split(",")[1])
                state = int(line.strip().split(",")[2])
                if last_state_for_pump[cycle - 1] != state:
                    pump_state_changes[cycle - 1].append([pump_statechange_time, state])
                    last_state_for_pump[cycle - 1] = state

    heating_periods = [[],[],[],[]]
    for cycle in range(1,5):
        start_time = None
        for time, status in pump_state_changes[cycle - 1]:
            if status == 1 and start_time is None:
                start_time = time
            elif status == 0 and start_time is not None:
                heating_periods[cycle - 1].append((start_time, time))
                start_time = None

    epost_estimates = [[],[],[],[]]
    for cycle in range(1,5):
        for belief_state in belief_states[cycle - 1]:
            epost_estimate = [
                belief_state[0],
                round(sum(key * value for key, value in belief_state[1].items()))
            ]
            epost_estimates[cycle - 1].append(epost_estimate)

    heating_signposts = [[],[],[],[]]
    for cycle in range(1,5):
        for heating_period in heating_periods[cycle - 1]:
            preceding, succeeding = find_closest_in_nested(epost_estimates[cycle - 1],heating_period[0],0)
            if preceding != 'n':
                heating_signposts[cycle - 1].append([heating_period[0],preceding[1]])
    
    heat_stock = []
    for cycle in range(1,5):
        heat_stock.append(sorted(epost_estimates[cycle - 1] + heating_signposts[cycle - 1]))

    interpolation_base = heat_stock
    minute_step = 5
    heat_stock_interpolated = []
    line_count = 0
    for minute in range(0, 24*60, minute_step):
        line = [minute]
        for cycle in range(1,5):
            preceding, succeeding = find_closest_in_nested(interpolation_base[cycle - 1],minute,0)
            val = 'n'
            if preceding != 'n':
                preceding_time = preceding[0]
                preceding_state = preceding[1]
                if succeeding != 'n':
                    succeeding_time = succeeding[0]
                    succeeding_state = succeeding[1]
                    val = preceding_state + (succeeding_state - preceding_state)*(minute - preceding_time)/(succeeding_time - preceding_time)
                else:
                    val = preceding_state

            line.append(val)
        
        heat_stock_interpolated.append(line)
        entry = f"{minute},{line[1]},{line[2]},{line[3]},{line[4]}"
        
        save_path = data_formatted_path+"/"+daystamp+"/"
        if not os.path.exists(save_path):
            os.makedirs(save_path)

        if line_count == 0:
            open(f'{save_path}/heat_stock_net.csv', 'w', newline='')

        with open(f'{save_path}/heat_stock_net.csv', 'a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(entry.split(','))
        line_count += 1

    heat_power_raw = [[],[],[],[]]
    time_step = 1
    for minute in range(0, 24*60 - time_step, time_step):
        for cycle in range(4):
            preceding, succeeding = find_closest_in_nested(heat_stock_interpolated, minute ,0)
            if preceding != 'n' and succeeding != 'n':
                preceding_time = preceding[0]
                preceding_stock = preceding[cycle + 1]
                succeeding_time = succeeding[0]
                succeeding_stock = succeeding[cycle + 1]

                time = (preceding_time + succeeding_time) / 2
                power = (succeeding_stock - preceding_stock) / (succeeding_time - preceding_time)

                heat_power_raw[cycle].append([time, power])
    
    power_smooth_window = 60
    heat_power_smooth = [[],[],[],[]]
    for minute in range(0, 24*60 - time_step, time_step):
        for cycle in range(4):
            power_smoothed = list(map(mean,transpose(select(heat_power_raw[cycle], lambda x: minute - power_smooth_window < x[0] <= minute))))
            if power_smoothed:
                heat_power_smooth[cycle].append([minute, power_smoothed[1]])

    heat_power_interpolated = []
    line_count = 0
    for minute in range(minute_step,24*60,minute_step):
        cycle_entries = ['n','n','n','n']
        for cycle in range(4):
            preceding, succeeding = find_closest_in_nested(heat_power_smooth[cycle], minute ,0)
            if preceding != 'n' and succeeding != 'n':
                preceding_time = preceding[0]
                preceding_power = preceding[1]
                succeeding_time = succeeding[0]
                succeeding_power = succeeding[1]
                interpolating_factor = (minute - preceding_time)/(succeeding_time - preceding_time)
                cycle_entries[cycle] = round(preceding_power*(1-interpolating_factor) + succeeding_power*interpolating_factor,5)
            elif preceding != 'n':
                preceding_time = preceding[0]
                preceding_power = preceding[1]
                cycle_entries[cycle] = round(preceding_power,5)
            else:
                cycle_entries[cycle] = 0
            
        heat_power_interpolated.append([minute,cycle_entries[0],cycle_entries[1],cycle_entries[2],cycle_entries[3]])
        entry = f"{minute},{cycle_entries[0]},{cycle_entries[1]},{cycle_entries[2]},{cycle_entries[3]}"
        
        save_path = data_formatted_path+"/"+daystamp+"/"
        if not os.path.exists(save_path):
            os.makedirs(save_path)

        if line_count == 0:
            open(f'{save_path}/heat_flow_net.csv', 'w', newline='')

        with open(f'{save_path}/heat_flow_net.csv', 'a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(entry.split(','))
        line_count += 1


#def plot(datasets, scatter = True, join = False): #DEV
#    for dataset in datasets:
#        dataset = transpose(dataset)
#        fig, ax = plt.subplots()
#        if scatter:
#            ax.scatter(dataset[0], dataset[1])
#        if join:
#            ax.plot(dataset[0], dataset[1])
#    plt.show()

def push_to_repo(commit_message, to_add):
    print(f"Start push to repo: {commit_message}.")
    try:
        subprocess.check_call(["git", "pull"])
        for item in to_add:
            subprocess.check_call(["git", "add", item])
        subprocess.check_call(["git", "commit", "-m", commit_message])
        subprocess.check_call(["git", "push"])
        print(f"\tOperation {commit_message} completed successfully.")

    except subprocess.CalledProcessError as e:
        print(f"\tAn error occurred during git operations: {e}. Return code: {e.returncode}, Output: {e.output}")

    except Exception as e:
        print(f"Unexpected system error: {sys.exc_info()[0]} during {commit_message}.")
    
    print(f"Push to repo: {commit_message} finished.\n")

if __name__ == "__main__":
    script_path = os.path.abspath(__file__)
    script_dir = os.path.dirname(script_path)
    root_root = os.path.abspath(os.path.join(script_dir, '..', '..','..'))
    data_raw_path = os.path.join(root_root, 'kazankontroll-dashboard','data','raw')
    data_formatted_path = os.path.join(root_root, 'kazankontroll-dashboard','data','formatted')
    minute_step_spec = 5

    daystamp_spec = datetime.now().strftime("%Y-%m-%d")
    prev_daystamp = (datetime.strptime(daystamp_spec,"%Y-%m-%d") + timedelta(days=-1)).strftime("%Y-%m-%d")

    #data_to_plot = []
    #for cycle in range(1,2):
    #    data_to_plot.append(transpose([transpose(heat_stock_interpolated)[0],transpose(heat_stock_interpolated)[cycle]]))
    #    plot(data_to_plot, scatter = False, join = True)

    if True:
        start_day = datetime(2024, 3, 30)
        end_day = datetime(2024, 3, 30)
        #end_day = datetime(2024, 2, 17)
        day = start_day
        while day <= end_day:
            print(day.strftime("%m-%d"))
            try:
                pass
                process_and_save_heatmeter_readings_net(daystamp = day.strftime("%Y-%m-%d"))
            except Exception as e:
                print(f"Couldn't format heat data due to {e}.")
            day = day + timedelta(days = 1)
    else:
        try:
            try:
                albatros_state = load_albatros_data(daystamp = prev_daystamp, time_offset = -24*60)+ load_albatros_data(daystamp = daystamp_spec)
                pump_states = [
                    load_pump_data(daystamp = prev_daystamp, time_offset = -24*60),
                    load_pump_data(daystamp = daystamp_spec)
                ]
                construct_and_save_formatted_heating_state(daystamp = daystamp_spec, minute_step = minute_step_spec)
            except Exception as e:
                print(f"Couldn't format heating data due to {e}.")
            
            try:
                measured_temps = [
                    load_room_measured_temps_data(daystamp = prev_daystamp, time_offset = -24*60),
                    load_room_measured_temps_data(daystamp = daystamp_spec)
                ]
                set_temps = [
                    load_room_set_temps_data(daystamp = prev_daystamp, time_offset = -24*60),
                    load_room_set_temps_data(daystamp = daystamp_spec)
                ]
                construct_and_save_formatted_room_temps_data(daystamp = daystamp_spec, minute_step = minute_step_spec)
            except Exception as e:
                print(f"Couldn't format room data due to {e}.")

            try:
                external_temp = load_external_temp_data(daystamp = daystamp_spec)
                construct_and_save_formatted_external_temp_data(daystamp = daystamp_spec, minute_step = minute_step_spec)
            except Exception as e:
                print(f"Couldn't format external temp due to {e}.")
            
            try:
                process_and_save_gas_pulse_data(daystamp = daystamp_spec)
            except Exception as e:
                print(f"Couldn't format gas data due to {e}.")

            try:    
                process_and_save_heatmeter_readings(daystamp = daystamp_spec)
            except Exception as e:
                print(f"Couldn't format heat data due to {e}.")
                
            print(f"Successfully formatted data.")
        except Exception as e:
            print(f"Couldn't format data due to {e}.")

        push_to_repo('Data push', [data_raw_path, data_formatted_path])