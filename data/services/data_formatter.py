import bisect
import csv
import copy
from datetime import datetime, timedelta
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

def process_and_save_gas_pulse_data(daystamp = datetime.now().strftime("%Y-%m-%d"), minute_step = 5, time_offset = 0):
    gas_impulse_times_raw = []
    with open(data_raw_path + "/" + daystamp + "/gas_pulse_times.txt", 'r') as file:
        for line in file:
            seconds_since_midnight = 60*60*int(line.split(":")[0]) + 60*int(line.split(":")[1]) + int(line.strip().split(":")[2]) + time_offset
            gas_impulse_times_raw.append(seconds_since_midnight)
    
    gas_impulse_double_readings_filtered = []
    for n in range(1,len(gas_impulse_times_raw)):
        if 60 < gas_impulse_times_raw[n] - gas_impulse_times_raw[n-1]:
            gas_impulse_double_readings_filtered.append(gas_impulse_times_raw[n]/60)

    gas_impulse_count_window = 15
    gas_pulses_count = []
    gas_pulses_total = 0
    for time in range(0, 24*60 - gas_impulse_count_window, gas_impulse_count_window):
        count = len(select(gas_impulse_double_readings_filtered, lambda x: time - gas_impulse_count_window < x <= time))
        gas_pulses_total += count
        gas_pulses_count.append([time,count])
    gas_stock = round(gas_pulses_total * 0.1, 4)

    gas_smooth_window = 2*60
    gas_flow_smooth = []
    for time in range(0, 24*60):
        flow = mean(transpose(select(gas_pulses_count,lambda x: time - gas_smooth_window < x[0] <= time))[1])*0.1
        gas_flow_smooth.append([time,flow])

    line_count = 0
    for minute in range(0,24*60,minute_step):
        preceding, succeeding = find_closest_in_nested(gas_flow_smooth,minute,0)
        if preceding != 'n' and succeeding != 'n':
            preceding_time = preceding[0]
            preceding_flow = preceding[1]
            succeeding_time = succeeding[0]
            succeeding_flow = succeeding[1]
            time = minute
            flow = round((preceding_flow+succeeding_flow)/2, 4)
        elif preceding != 'n':
            preceding_time = preceding[0]
            preceding_flow = preceding[1]
            time = minute
            flow = round(preceding_flow, 4)
        else:
            time = minute
            flow = 'n'
        
        entry = f'{time},{flow}'
        
        save_path = data_formatted_path+"/"+daystamp+"/"
        if not os.path.exists(save_path):
            os.makedirs(save_path)

        if line_count == 0:
            open(f'{save_path}/gas_flow.csv', 'w', newline='')
            file = open(f'{save_path}/gas_stock.csv', 'w', newline='')
            writer = csv.writer(file)
            writer.writerow([gas_stock])

        with open(f'{save_path}/gas_flow.csv', 'a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(entry.split(','))
        line_count += 1

def process_and_save_heatmeter_readings(daystamp = datetime.now().strftime("%Y-%m-%d"), minute_step = 5, time_offset = 0):
    prev_daystamp = (datetime.strptime(daystamp,"%Y-%m-%d") + timedelta(days=-1)).strftime("%Y-%m-%d")
    try:
        ground_truth = []
        with open(data_formatted_path + "/" + prev_daystamp + "/heat_stock.csv", 'r') as file:
            for line in file:
                entries = list(map(float,line.strip().split(",")))
                ground_truth = entries[1:]
    except Exception as e:
        print(f"Couldn't read in ground truth due to {e}")

    heatmeter_valid_readouts = [[],[],[],[]]
    ground_truth_dist_filter = 500
    with open(data_raw_path + "/" + daystamp + "/heatmeter_readouts.csv", 'r') as file:
        for line in file:
            entries = line.split(",")
            minutes_since_midnight = 60*int(entries[0].split(":")[0]) + int(entries[0].split(":")[1]) + time_offset
            for cycle in range(4):
                cycle_readout = entries[cycle + 1]
                if 'n' not in cycle_readout and int(cycle_readout) - ground_truth[cycle] < ground_truth_dist_filter:
                    heatmeter_valid_readouts[cycle].append([minutes_since_midnight,int(cycle_readout)])
    
    heatmeter_power_filtered_readouts = [[],[],[],[]]
    power_filter = 2
    for cycle in range(4):
        for n in range(1,len(heatmeter_valid_readouts[cycle])):
            prev_readout = heatmeter_valid_readouts[cycle][n-1]
            this_readout = heatmeter_valid_readouts[cycle][n]
            if prev_readout[0] != this_readout[0] or prev_readout[1] != this_readout[1]:
                if prev_readout[0] != this_readout[0]:
                    power = (this_readout[1] - prev_readout[1]) / (this_readout[0] - prev_readout[0])
                    if 0 <= power < power_filter:
                        heatmeter_power_filtered_readouts[cycle].append(this_readout)


    heat_stock_interpolated = []
    line_count = 0
    for minute in range(minute_step,24*60,minute_step):
        cycle_entries = ['n','n','n','n']
        for cycle in range(4):
            preceding, succeeding = find_closest_in_nested(heatmeter_power_filtered_readouts[cycle], minute ,0)
            if preceding != 'n' and succeeding != 'n':
                preceding_time = preceding[0]
                preceding_reading = preceding[1]
                succeeding_time = succeeding[0]
                succeeding_reading = succeeding[1]
                interpolating_factor = (minute - preceding_time)/(succeeding_time - preceding_time)
                cycle_entries[cycle] = round(preceding_reading*(1-interpolating_factor) + succeeding_reading*interpolating_factor,3)
            elif preceding != 'n':
                preceding_time = preceding[0]
                preceding_reading = preceding[1]
                cycle_entries[cycle] = round(preceding_reading,3)
            else:
                cycle_entries[cycle] = round(ground_truth[cycle],3)
            
        heat_stock_interpolated.append([minute,cycle_entries[0],cycle_entries[1],cycle_entries[2],cycle_entries[3]])
        entry = f"{minute},{cycle_entries[0]},{cycle_entries[1]},{cycle_entries[2]},{cycle_entries[3]}"
        
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

def plot(data, scatter = True, join = False):
    data = transpose(data)
    fig, ax = plt.subplots()
    if scatter:
        ax.scatter(data[0], data[1])
    if join:
        ax.plot(data[0], data[1])
    plt.show()

if __name__ == "__main__":
    script_path = os.path.abspath(__file__)
    script_dir = os.path.dirname(script_path)
    root_root = os.path.abspath(os.path.join(script_dir, '..', '..','..'))
    data_raw_path = os.path.join(root_root, 'kazankontroll-dashboard','data/raw')
    data_formatted_path = os.path.join(root_root, 'kazankontroll-dashboard','data/formatted')
    minute_step_spec = 5

    daystamp_spec = datetime.now().strftime("%Y-%m-%d")
    prev_daystamp = (datetime.strptime(daystamp_spec,"%Y-%m-%d") + timedelta(days=-1)).strftime("%Y-%m-%d")

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