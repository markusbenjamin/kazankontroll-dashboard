import time
import os
from datetime import datetime, timedelta
import subprocess
import copy
from PIL import Image, ImageEnhance, ImageFilter
import csv
import random
import ast
from io import BytesIO
import math
import itertools
import glob
import numpy as np #DEV
from scipy.ndimage import zoom #DEV

script_path = os.path.abspath(__file__)
script_dir = os.path.dirname(script_path)
project_root = os.path.abspath(os.path.join(script_dir, '..', '..'))
data_path = os.path.join(project_root, 'data')

def capture_image():
    time.sleep(random.randint(1, 20))
    current_date = time.strftime("%Y-%m-%d")
    save_path = f'{data_path}/raw/{current_date}/heatmeter_images/'
    if not os.path.exists(save_path):
        os.makedirs(save_path)

    now = datetime.now()
    timestamp = now.strftime("%H%M")
    image_filename = f'{save_path}{timestamp}.jpg'

    # Capture an image using fswebcam
    try:
        subprocess.run(['fswebcam', '-r', '1280x720', '--no-banner', image_filename])
        report(f'Captured image {image_filename}.')
        return image_filename
    except Exception as e:
        report(f"Couldn't capture image {image_filename} due to {e}.")

def crop_cycles_and_save(img_path):
    crop_rectangles = [
        (186,384,220,402),
        (191,535,225,553),
        (193,684,228,703),
        (180,233,216,252)
    ]

    cycle_crops = []

    with Image.open(img_path) as img:
        # Rotate with antialiasing
        img = img.rotate(90, resample=Image.BICUBIC, expand=True)

        for cycle in range(1, 5):
            try:
                # Create a high-quality intermediate image
                cropped_img = img.crop(crop_rectangles[cycle - 1])
                cropped_img_path = f"{img_path[0:-4]}_{cycle}.png"  # Save as PNG
                cropped_img.save(cropped_img_path, format='PNG')

                # Optionally convert to JPEG with high quality
                # cropped_img.save(cropped_img_path.replace('.png', '.jpg'), format='JPEG', quality=95)

                cycle_crops.append(cropped_img)

                report(f"Cycle {cycle} successfully cropped and saved.")
            except Exception as e:
                report(f"Couldn't crop cycle {cycle} due to {e}.")

def slice_into_chars(img):
    # Calculate the width and height of each piece
    width, height = img.size
    slice_width = width // 4

    # List to hold the image pieces in PIL format
    image_pieces = []

    # Cut the image into four vertical pieces
    for i in range(4):
        # Define the bounding box for the current slice
        left = i * slice_width
        # Ensure the last piece goes all the way to the right edge
        right = width if i == 3 else (i + 1) * slice_width
        bbox = (left, 0, right, height)
        
        # Cut the image and add it to the list
        piece = img.crop(bbox)
        image_pieces.append(piece)

    return image_pieces

def map_to_zero_and_one(lst):
    if not lst:  # Check if the list is empty
        return lst

    min_val = min(lst)
    max_val = max(lst)
    range_val = max_val - min_val

    if range_val != 0:
        return [(x - min_val) / range_val for x in lst]
    else:
        return lst
    
def map_to_zero_and_one_pil(image):
    """ Normalize a PIL Image to have values between 0 and 1 """
    pixels = list(image.getdata())
    min_val = min(pixels)
    max_val = max(pixels)
    range_val = max_val - min_val

    if range_val != 0:
        normalized_pixels = [(pixel - min_val) / range_val for pixel in pixels]
    else:
        normalized_pixels = pixels

    # Convert the normalized values back to a PIL Image
    normalized_image = Image.new(image.mode, image.size)
    normalized_image.putdata([int(pixel * 255) for pixel in normalized_pixels])  # Scaling back to 0-255 range
    return normalized_image

def list_to_image(lst):
    """ Convert a 2D list to a PIL Image. """
    height = len(lst)
    width = len(lst[0])
    img = Image.new('L', (width, height))  # 'L' for grayscale, 'RGB' for color
    pixels = img.load()
    for i in range(width):
        for j in range(height):
            pixels[i, j] = lst[j][i]
    return img

def image_to_list(img):
    """ Convert a PIL Image back to a 2D list. """
    width, height = img.size
    return [[img.getpixel((i, j)) for i in range(width)] for j in range(height)]

def zoom_array(array, pad_ratio, fill_value=255):
    if isinstance(array, list):  # Check if input is a list
        image = list_to_image(array)
    else:
        image = array  # Assume it's already a PIL Image

        width, height = image.size
    pad_height = int(height * abs(pad_ratio))
    pad_width = int(width * abs(pad_ratio))

    if pad_ratio == 0:
        return image
    else:
        if pad_ratio > 0:
            # Pad the image
            new_width = width + 2 * pad_width
            new_height = height + 2 * pad_height
            new_image = Image.new("RGB", (new_width, new_height), (fill_value, fill_value, fill_value))
            new_image.paste(image, (pad_width, pad_height))
        elif pad_ratio < 0:
            # Crop the image
            left = pad_width
            top = pad_height
            right = width - pad_width
            bottom = height - pad_height
            if left >= right or top >= bottom:
                raise ValueError("Cropping too much - resulting array is empty.")
            new_image = image.crop((left, top, right, bottom))

        # Resize the image back to original dimensions
        resized_image = new_image.resize((width, height), Image.NEAREST)

    if isinstance(array, list):  # Convert back to list if input was a list
        return image_to_list(resized_image)
    else:
        return resized_image
       
def shift_array(array, shift_x_ratio, shift_y_ratio, fill_value=255):
    if isinstance(array, list):  # Check if input is a list
        image = list_to_image(array, fill_value)
    else:
        image = array  # Assume it's already a PIL Image

    width, height = image.size
    shift_x = int(width * shift_x_ratio)
    shift_y = int(height * shift_y_ratio)

    # Create a new image and paste the original image shifted
    new_image = Image.new("L", (width, height), fill_value)
    new_image.paste(image, (shift_x, shift_y))

    if isinstance(array, list):  # Convert back to list if input was a list
        return image_to_list(new_image)
    else:
        return new_image

def flatten_list(lst):
    """ Flatten a 2D list to a 1D list """
    return [item for sublist in lst for item in sublist]

def dot_product(list1, list2):
    """ Calculate the dot product of two lists """
    return sum(x * y for x, y in zip(list1, list2))

def drange(start, stop, step):
    r = start
    while r <= stop:
        yield r
        r += step

def dims(array):
    if not isinstance(array, list):
        return ()
    return (len(array),) + dims(array[0]) if array else ()

def seven_segment_ocr(unknown_image, archetype_images, da1_threshold=0.03, total_da_threshold=0.18, h_shift_min=0, h_shift_max=0.25, h_shift_step=0.05, v_shift_min=-0.1, v_shift_max=0.1, v_shift_step=0.05, zoom_min=0.05, zoom_max=0.25, zoom_step=0.05):
    resized_archetype_images = []
    unknown_dimensions = unknown_image.size
    for archetype_image in archetype_images:
        resized_archetype_images.append(archetype_image.resize(unknown_dimensions,Image.BICUBIC))
    
    unknown_vector = [1 - pixel/255 for pixel in flatten_list(image_to_list(unknown_image))]
    activations = []
    counter = 0
    iter_num = 10*len(list(drange(h_shift_min, h_shift_max, h_shift_step)))*len(list(drange(v_shift_min, v_shift_max, v_shift_step)))*len(list(drange(zoom_min, zoom_max, zoom_step)))
    for h_shift in drange(h_shift_min, h_shift_max, h_shift_step):
        for v_shift in drange(v_shift_min, v_shift_max, v_shift_step):
            for zoom_level in drange(zoom_min, zoom_max, zoom_step):
                activation = {}
                for num in range(10):
                    shifted_resized_archetype_image = shift_array(zoom_array(copy.deepcopy(resized_archetype_images[num]), zoom_level), h_shift, v_shift)
                    archetype_vector = [1 - pixel/255 for pixel in flatten_list(image_to_list(shifted_resized_archetype_image))]
                    activation[num] = dot_product(archetype_vector, unknown_vector) / ((sum(archetype_vector) + sum(unknown_vector)) / 2)
    
                    counter += 1

                activations.append(activation)
 
    def activation_checks(activation_as_list):
        sorted_activations = sorted(activation_as_list)
        gradient = [abs(sorted_activations[i+1] - sorted_activations[i]) for i in range(len(sorted_activations)-1)]
        return total_da_threshold < sum(gradient) and da1_threshold < gradient[-1]

    passed_activations = [activation for activation in activations if activation_checks(list(activation.values()))]

    predictions = [max(activation, key=activation.get) for activation in passed_activations]
    
    char_probs = calculate_relative_frequency(predictions)
    
    return char_probs 

def calculate_relative_frequency(numbers_list):
    # Initialize a dictionary with keys from 0 to 9, all values set to 0
    frequency_dict = {i: 0 for i in range(10)}

    # Check if the list is empty
    if not numbers_list:
        return frequency_dict

    # Count the occurrence of each number
    for num in numbers_list:
        if num in frequency_dict:
            frequency_dict[num] += 1

    # Calculate relative frequency
    total_numbers = len(numbers_list)
    for num in frequency_dict:
        frequency_dict[num] = round(frequency_dict[num] / total_numbers,4)

    return frequency_dict

def grayscale_with_channel_control(image, r_weight, g_weight, b_weight):
    # Ensure the image is in RGB mode
    if image.mode != 'RGB':
        image = image.convert('RGB')

    # Split the image into its RGB channels
    r, g, b = image.split()

    # Apply weights to each channel
    r = r.point(lambda i: i * r_weight)
    g = g.point(lambda i: i * g_weight)
    b = b.point(lambda i: i * b_weight)

    # Merge the channels back and convert to grayscale
    image = Image.merge('RGB', (r, g, b)).convert('L')
    return image

def crop_to_aspect_ratio(image, aspect_ratio=(2, 1)):
    width, height = image.size
    target_ratio = aspect_ratio[0] / aspect_ratio[1]

    # Determine new dimensions based on the target aspect ratio
    if width / height > target_ratio:
        # Width is too large
        new_width = int(height * target_ratio)
        left = (width - new_width) / 2
        top = 0
        right = left + new_width
        bottom = height
    else:
        # Height is too large
        new_height = int(width / target_ratio)
        top = (height - new_height) / 2
        left = 0
        bottom = top + new_height
        right = width

    cropped_image = image.crop((left, top, right, bottom))
    return cropped_image

def do_ocr_on_cycle(cycle, cycle_crop):
    rotates = [0, 0, 3, 0]
    brightness1_factors = [1.25, 1.25, 1.25, 1.25]
    contrast1_factors = [2, 2, 2, 2]
    contrast2_factors = [4, 4, 4, 4]

    width, height = cycle_crop.size
    zoom = 4
    cycle_crop = cycle_crop.resize((round(width*zoom), round(height*zoom)), Image.BICUBIC)

    cycle_crop = grayscale_with_channel_control(cycle_crop, 1, 1, 1)
    
    cycle_crop = cycle_crop.filter(ImageFilter.SHARPEN).filter(ImageFilter.SHARPEN).filter(ImageFilter.SHARPEN)

    cycle_crop = map_to_zero_and_one_pil(cycle_crop)        
    
    enhancer = ImageEnhance.Contrast(cycle_crop)
    cycle_crop = enhancer.enhance(contrast1_factors[cycle - 1])
    enhancer = ImageEnhance.Brightness(cycle_crop)
    cycle_crop = enhancer.enhance(brightness1_factors[cycle - 1])

    if rotates[cycle - 1] != 0:
        cycle_crop = cycle_crop.rotate(rotates[cycle - 1], expand=True, fillcolor='white')
        cycle_crop = crop_to_aspect_ratio(cycle_crop,(2,1))
    
    cycle_crop = map_to_zero_and_one_pil(cycle_crop)        

    enhancer = ImageEnhance.Contrast(cycle_crop)
    cycle_crop = enhancer.enhance(contrast2_factors[cycle - 1])

    cycle_char_probs = []
    char_imgs = slice_into_chars(cycle_crop)
    for char in range(1,5):
        unknown_image = char_imgs[char-1]
        #char_probs = seven_segment_ocr(unknown_image, archetype_images, da1_threshold = 0.03, total_da_threshold = 0.18)
        unknown_vector_2D = np.array(unknown_image)
        char_probs = seven_segment_ocr_np(unknown_vector_2D, archetype_vectors_2D, da1_threshold = 0.03, total_da_threshold = 0.18)
        cycle_char_probs.append(char_probs)
    
    return cycle_char_probs

def weibull_pdf(a, b, c, x):
    if x < c:  # The PDF is zero for x < c
        return 0
    else:
        exponent = ((-c + x) / b) ** a
        if exponent > 10:  # 700 is a rough threshold before exp() overflows
            return 0  # or handle it in another way appropriate for your context

        return (a * ((-c + x) / b) ** (a - 1)) / (b * math.exp(exponent))
    
def power_weighting_function(cycle, start_energy, end_energy, elapsed_heating_time, weibull_parameters):
    power = 0 if elapsed_heating_time == 0 else (end_energy - start_energy) / elapsed_heating_time

    if end_energy < start_energy:
        return 0

    if elapsed_heating_time == 0:
        return 1 if end_energy == start_energy else 0

    a, b, c = weibull_parameters

    return weibull_pdf(a, b, c, power)

def state_to_energy(state):
    return int("".join(map(str, state)))

def energy_to_state(energy):
    energy_str = str(round(energy))
    state = list(map(int, energy_str))
    return [0] * (4 - len(state)) + state

def do_bayesian_inference_reading(inference_time, ocr_net_probs):
    report(f"Start inference for {inference_time.strftime('%m-%d %H:%M')}.")
    # Find latest prior
    belief_file_path = os.path.join(data_path,"raw\\",inference_time.strftime("%Y-%m-%d"))
    last_belief_day = inference_time
    while not os.path.exists(f"{belief_file_path}\\heatmeter_belief_state_net.csv"):
        belief_file_path = os.path.join(data_path,"raw\\",last_belief_day.strftime("%Y-%m-%d"))
        last_belief_day = (inference_time + timedelta(days = -1))

    # Load latest prior
    data_newer_than_latest_prior = [False,False,False,False]
    with open(f"{belief_file_path}\\heatmeter_belief_state_net.csv", 'rb') as file:
        file.seek(0, os.SEEK_END)  # Go to the end of the file
        filesize = file.tell()
        file.seek(max(filesize-1024, 0))  # Go to the end of file, then back 1024 bytes, or to the start
        lines = file.readlines()  # Read to the end

        line = lines[-1].decode()

        report(f"Belief line found: {line.strip()}")
        
        cycle_parts = line.split(';')

        timed_priors = []
        for cycle in range(1, 5):
            timed_prior = [
                    datetime.strptime(cycle_parts[cycle - 1].split(',', maxsplit=1)[0],"%Y%m%d%H%M"),
                    ast.literal_eval(cycle_parts[cycle - 1].split(',', maxsplit=1)[1])
                ]
            timed_priors.append(
                timed_prior
            )
            if timed_prior[0] < inference_time:
                data_newer_than_latest_prior[cycle - 1] = True
    
    # Look for ground truth input for today and yesterday
    ground_truth_days = [inference_time + timedelta(days = -1),inference_time]
    for day in ground_truth_days:
        ground_truth_file_path = os.path.join(data_path,"raw\\", day.strftime("%Y-%m-%d"))
        if os.path.exists(f"{ground_truth_file_path}\\heatmeter_ground_truth.csv"):
            with open(f"{ground_truth_file_path}\\heatmeter_ground_truth.csv",'r') as ground_truth_file:
                for line in ground_truth_file.readlines():
                    cycle_parts = line.split(';')

                    for cycle in range(1, 5):
                        timed_ground_truth = [
                                datetime.strptime(cycle_parts[cycle - 1].split(',', maxsplit=1)[0],"%Y%m%d%H%M"),
                                ast.literal_eval(cycle_parts[cycle - 1].split(',', maxsplit=1)[1])
                            ]
                        if timed_ground_truth[1] != {} and timed_priors[cycle - 1][0] < timed_ground_truth[0] < inference_time:
                            timed_priors[cycle - 1] = timed_ground_truth
                            report(f"Relevant ground truth found for cycle {cycle}: {timed_ground_truth}.")

    report(f"Loaded belief state:")
    for cycle in range(1,5):
        report(f"\tCycle {cycle}: {timed_priors[cycle - 1][0].strftime('%m-%d %H:%M')}, {timed_priors[cycle - 1][1]}")

    if True in data_newer_than_latest_prior:
        # Inference parameters
        belief_update_cutoff = 0.001
        prev_prior_cutoff = 0.001
        weibull_parameters = [
            [3, 10, 0.001],
            [2.3, 10, 0.001],
            [2, 10, 0.001],
            [1.5, 10, 0.001]
        ]
        
        # Do Bayesian inference for each cycle
        update_on_cycle = [False,False,False,False]
        for cycle in range(1,5):
            if timed_priors[cycle - 1][0] < inference_time:
                report(f"Start inference for cycle {cycle}.")
                
                # Generate OCR distributions
                report(f"\tLoad OCR.")
                cycle_char_probs = [[],[],[],[]]
                cycle_na_prob_highest = False
                for char in range(4):
                    if np.argmax(ocr_net_probs[cycle - 1][char]) == 10:
                        cycle_na_prob_highest = True
                        report(f"\t\tChar {char+1} is unreadable.")
                    cycle_char_probs[char] = dict(zip(range(10), ocr_net_probs[cycle - 1][char][0:10]))
                    #report(f"\t\tChar {char+1} probs: {cycle_char_probs[char]}")

                chars_with_enough_prob_pre = []
                not_enough_OCR_input = False
                for prob_dict in cycle_char_probs:
                    filtered_digits = [digit for digit, prob in prob_dict.items() if prob >= 0.5]
                    if not filtered_digits:
                        not_enough_OCR_input = True
                    chars_with_enough_prob_pre.append(filtered_digits)

                if not cycle_na_prob_highest and not not_enough_OCR_input:
                    # Select chars that are probable enough for consideration
                    chars_with_enough_prob = []
                    for char_list in chars_with_enough_prob_pre:
                        new_list = char_list
                        chars_with_enough_prob.append(new_list)

                    report(f"\tProbable chars: {chars_with_enough_prob}.")
                    
                    all_combinations = itertools.product(*chars_with_enough_prob)
                    energy_readouts_with_enough_evidence = [state_to_energy(list(combination)) for combination in all_combinations]
                    current_probable_states = [energy for energy, prob in timed_priors[cycle - 1][1].items() if prob > prev_prior_cutoff]

                    # Calculate OCR likelihood component
                    ocr_likelihoods = []

                    for energy in energy_readouts_with_enough_evidence:
                        state = energy_to_state(energy)  # Convert energy to state
                        total_prob = 0

                        # Calculate total probability for this state
                        for char_index, char in enumerate(state):
                            total_prob += cycle_char_probs[char_index].get(char, 0)

                        # Average the probability and append to the list
                        average_prob = total_prob / 4
                        if 0 < average_prob:
                            ocr_likelihoods.append((energy, round(average_prob,4)))
                    
                    # Calculate heating power based likelihood component
                    report(f"\tCurrent probable energy states: {current_probable_states}.")
                    report(f"\tNext energy state candidates based on OCR evidence: {ocr_likelihoods}.")
                    power_likelihoods = []

                    # Calculate elapsed heating time for cycle
                    elapsed_heating_time = 0
                    load_day = timed_priors[cycle - 1][0]
                    pump_state_changes = []
                    last_state_for_pump = -1 # To only load changes in state
                    while (load_day + timedelta(days = -1)).day != inference_time.day:
                        with open(os.path.join(data_path,"raw\\", load_day.strftime("%Y-%m-%d"),'pump_states.csv'), 'r') as file:
                            for line in file.readlines():
                                pump_statechange_time = datetime.strptime(f'{load_day.strftime("%Y-%m-%d ") }{line.strip().split(",")[0]}',"%Y-%m-%d %H:%M:%S")
                                pump = int(line.strip().split(",")[1])
                                state = int(line.strip().split(",")[2])
                                if cycle == pump and pump_statechange_time < inference_time and last_state_for_pump != state:
                                    pump_state_changes.append([pump_statechange_time, state])
                                    last_state_for_pump = state
                            load_day = (load_day + timedelta(days = 1))

                    for n in range(len(pump_state_changes)):
                        if pump_state_changes[n][1] == 1:
                            on_time = pump_state_changes[n][0]
                            try:
                                off_time = pump_state_changes[n + 1][0]
                                heating_time = (off_time - max(on_time, timed_priors[cycle - 1][0])).total_seconds()/3600
                            except:
                                heating_time = (inference_time - max(on_time, timed_priors[cycle - 1][0])).total_seconds()/3600
                            if 0 < heating_time:
                                elapsed_heating_time += heating_time

                    report(f"\tElapsed heating time: {round(elapsed_heating_time,2)} hours.")
                    for next_energy, _ in ocr_likelihoods:
                        total_likelihood = 0

                        # Calculate total likelihood
                        for previous_energy in current_probable_states:
                            prob = timed_priors[cycle - 1][1][previous_energy]
                            weight = power_weighting_function(cycle, previous_energy, next_energy, elapsed_heating_time, weibull_parameters[cycle - 1])
                            total_likelihood += prob * weight
                        if 0 < total_likelihood:
                            power_likelihoods.append((next_energy, round(total_likelihood,4)))
                    
                    report(f"\tOf these with non-zero likelihood based on heating: {power_likelihoods}.")

                    # Combine likelihoods
                    combined_likelihoods = []

                    ocr_dict = dict(ocr_likelihoods)
                    power_dict = dict(power_likelihoods)

                    for energy in energy_readouts_with_enough_evidence:
                        ocr_prob = ocr_dict.get(energy, 0)
                        power_prob = power_dict.get(energy, 0)
                        combined_prob = ocr_prob * power_prob
                        combined_likelihoods.append((energy, round(combined_prob,4)))
                    
                    belief_update = [item for item in combined_likelihoods if item[1] > belief_update_cutoff]

                    if len(belief_update) > 0:
                        report(f"\tBelief update for cycle {cycle}: {belief_update}.")
                        posterior = [[energy, 0] for energy in range(10000)]
                        for update in belief_update:
                            posterior[update[0]][1] = update[1]
                        total_prob = sum([p[1] for p in posterior])
                        posterior = dict([[p[0], p[1] / total_prob] for p in posterior])
                        
                        timed_priors[cycle - 1][0] = inference_time
                        timed_priors[cycle - 1][1] = {energy:round(prob,4) for energy, prob in posterior.items() if prob > 0}
                        update_on_cycle[cycle - 1] = True
                    else:
                        report(f"\tNot enough evidence for belief update on cycle {cycle}.")
                else:
                    report(f"\tNot enough OCR input, exiting inference for cycle {cycle}.")
            else:
                report(f"Prior newer than inference time for {cycle}.")

        if True in update_on_cycle:
            # Save new belief state
            belief_state_string = ''
            for cycle in range(1,5):
                belief_state_string += f"{';' if cycle != 1 else ''}{timed_priors[cycle - 1][0].strftime('%Y%m%d%H%M')},{timed_priors[cycle - 1][1]}"

            belief_file_path = os.path.join(data_path,"raw\\",inference_time.strftime("%Y-%m-%d"))

            if not os.path.exists(belief_file_path):
                os.makedirs(belief_file_path)

            with open(f"{belief_file_path}/heatmeter_belief_state_net.csv", 'a', newline='') as file:
                writer = csv.writer(file, delimiter=';')
                writer.writerow(belief_state_string.split(';'))
    else:
        report(f"All priors newer than inference time.")
    report(f"End inference for {inference_time.strftime('%m-%d %H:%M')}.\n")

def seven_segment_ocr_np(unknown_vector_2D, archetype_vectors_2D, da1_threshold = 0.03, total_da_threshold = 0.18, h_shift_min=0,h_shift_max=0.25,h_shift_step=0.05,v_shift_min=-0.1,v_shift_max=0.1,v_shift_step=0.05,zoom_min=0.05,zoom_max=0.25,zoom_step=0.05):
    resized_archetype_vectors_2D = []
    archetype_dimensions = archetype_vectors_2D[0].shape
    unknown_dimensions = unknown_vector_2D.shape
    for archetype_vector_2D in archetype_vectors_2D:
        resized_archetype_vectors_2D.append(zoom(archetype_vector_2D, (unknown_dimensions[0] / archetype_dimensions[0], unknown_dimensions[1] / archetype_dimensions[1])))
    
    activations = []
    for h_shift in np.arange(h_shift_min,h_shift_max+h_shift_step,h_shift_step):
        for v_shift in np.arange(v_shift_min,v_shift_max+v_shift_step,v_shift_step):
            for zoom_level in np.arange(zoom_min,zoom_max+zoom_step,zoom_step):
                activation = {}
                for num in np.arange(0,10,1):
                    archetype_vector = 1 - (shift_array_np(zoom_array_np(copy.deepcopy(resized_archetype_vectors_2D[num]), zoom_level),h_shift,v_shift).flatten())/255
                    unknown_vector = 1 - unknown_vector_2D.flatten()/255
                    activation[num] = np.dot(archetype_vector,unknown_vector)/np.mean([np.sum(archetype_vector),np.sum(unknown_vector)])
                activations.append(activation)
        
    def activation_checks(activation_as_array):
        gradient = abs(np.diff(np.sort(activation_as_array)))
        if total_da_threshold < sum(gradient) and da1_threshold < gradient[-1]:
            return True
        else:
            return False

    passed_activations = [activation for activation in activations if activation_checks(np.array(list(activation.values())))]

    predictions = [max(activation, key=activation.get) for activation in passed_activations]
    
    char_probs = calculate_relative_frequency(predictions)
    
    return char_probs 

def shift_array_np(array, shift_x_ratio, shift_y_ratio, fill_value=255):
    shift_x_ratio *= -1
    shift_y_ratio *= -1
    height, width = array.shape
    shift_x = int(width * shift_x_ratio)
    shift_y = int(height * shift_y_ratio)

    # Create an array filled with the fill_value
    shifted_array = np.full_like(array, fill_value)

    # Calculate the new coordinates after shifting
    start_x = max(0, -shift_x)
    end_x = min(width, width - shift_x)
    start_y = max(0, -shift_y)
    end_y = min(height, height - shift_y)

    # Assign the shifted values
    shifted_array[start_y:end_y, start_x:end_x] = array[max(0, shift_y):min(height, height + shift_y), max(0, shift_x):min(width, width + shift_x)]

    return shifted_array

def zoom_array_np(array, pad_ratio, fill_value=255):
    height, width = array.shape
    pad_height = int(height * abs(pad_ratio))
    pad_width = int(width * abs(pad_ratio))

    if pad_ratio == 0:
        return array
    else:
        if pad_ratio > 0:
            # Pad the array
            padded_or_cropped_array = np.pad(array, ((pad_height, pad_height), (pad_width, pad_width)), mode='constant', constant_values=fill_value)
        elif pad_ratio <0:
            # Crop the array
            padded_or_cropped_array = array[pad_height:-pad_height, pad_width:-pad_width]
            if padded_or_cropped_array.size == 0:
                raise ValueError("Cropping too much - resulting array is empty.")

        # Calculate new zoom factors to resize back to original dimensions
        zoom_factor_y = height / padded_or_cropped_array.shape[0]
        zoom_factor_x = width / padded_or_cropped_array.shape[1]

        # Resize the array
        resized_array = zoom(padded_or_cropped_array, (zoom_factor_y, zoom_factor_x))

        return resized_array

def report(text):
    if False:
        print(text)

if __name__ == "__main__":
    start_day = datetime(2024, 3, 30)
    end_day = datetime(2024, 3, 30)
    day = start_day
    while day <= end_day:
        print(f"Start inference for {day.strftime('%Y-%m-%d')}")
        pattern = os.path.join(data_path,'raw\\',f"{day.strftime('%Y-%m-%d')}\\", '*heatmeter_images\\[0-9][0-9][0-9][0-9]_*.png')

        timestamps = []
        for image_path in glob.glob(pattern):
            if image_path[-10:-6] not in timestamps:
                timestamps.append(image_path[-10:-6])

        ocr_net_results_data = np.load(os.path.join(data_path,"raw\\",day.strftime("%Y-%m-%d"),'heatmeter_images\\ocr_net_results.npz'))
        ocr_net_results = ocr_net_results_data['array']

        for i in range(len(timestamps)):
            timestamp = timestamps[i]
            inference_time = datetime(year=day.year, month=day.month, day=day.day, hour=datetime.strptime(timestamp,"%H%M").hour, minute=datetime.strptime(timestamp,"%H%M").minute)
            ocr_net_probs = ocr_net_results[i]
            do_bayesian_inference_reading(inference_time, ocr_net_probs)
        
        day = day + timedelta(days = 1)