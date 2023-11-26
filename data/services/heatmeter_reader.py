import time
import os
from datetime import datetime
import subprocess
import copy
from PIL import Image, ImageEnhance, ImageFilter
import csv

script_path = os.path.abspath(__file__)
script_dir = os.path.dirname(script_path)
project_root = os.path.abspath(os.path.join(script_dir, '..', '..'))
data_path = os.path.join(project_root, 'data')

def capture_image():
    current_date = time.strftime("%Y-%m-%d")
    save_path = f'{data_path}/raw/heatmeter_images/{current_date}/'
    if not os.path.exists(save_path):
        os.makedirs(save_path)

    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
    image_filename = f'{save_path}{timestamp}.jpg'

    # Capture an image using fswebcam
    subprocess.run(['fswebcam', '-r', '1280x720', '--no-banner', image_filename])
    print(f'Captured image {image_filename}.')
    return image_filename

def crop_cycles(img_path):
    crop_rectangles = [
        (181,384,216,402),
        (184,535,219,553),
        (183,684,219,703),
        (175,233,211,250)
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

                print(f"Cycle {cycle} successfully cropped.")
            except Exception as e:
                print(f"Couldn't crop cycle {cycle} due to {e}.")

    return cycle_crops

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

def seven_segment_ocr(unknown_image, archetype_images, cycle, char, da1_threshold=0.03, total_da_threshold=0.18, h_shift_min=0, h_shift_max=0.25, h_shift_step=0.05, v_shift_min=-0.1, v_shift_max=0.1, v_shift_step=0.05, zoom_min=0.05, zoom_max=0.25, zoom_step=0.05):
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
                    progress = round(20*counter/iter_num)
                    progress_bar = "|" + "-"*progress+" "*(20-progress)+"|"

                    print(f"\rCycle {cycle} char {char}: {progress_bar}", end="")

                activations.append(activation)
 
    def activation_checks(activation_as_list):
        sorted_activations = sorted(activation_as_list)
        gradient = [abs(sorted_activations[i+1] - sorted_activations[i]) for i in range(len(sorted_activations)-1)]
        return total_da_threshold < sum(gradient) and da1_threshold < gradient[-1]

    passed_activations = [activation for activation in activations if activation_checks(list(activation.values()))]

    predictions = [max(activation, key=activation.get) for activation in passed_activations]

    prediction = max(predictions, key=predictions.count) if predictions else 'n'

    print(f"\t--> {prediction}")

    return prediction 

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

def do_ocr_on_cycles(cycle_crops):
    rotates = [0, 0, 3, 0]
    brightness1_factors = [1.25, 1.25, 1.25, 1.25]
    contrast1_factors = [2, 2, 2, 2]
    contrast2_factors = [4, 4, 4, 4]
    
    cycle_readouts = []
    for cycle in range(1,5):
        cycle_crop = cycle_crops[cycle-1]
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
        
        cycle_crops.append(cycle_crop)

        char_imgs = slice_into_chars(cycle_crop)
        cycle_readout = ''
        for char in range(1,5):
            unknown_vector_2D = char_imgs[char-1]
            prediction = seven_segment_ocr(unknown_vector_2D,archetype_images, cycle, char, da1_threshold = 0.03, total_da_threshold = 0.18)
            cycle_readout += str(prediction)
        cycle_readouts.append(cycle_readout)
        print(f"Readout for cycle {cycle}: {cycle_readout}.")
    
    return f"{datetime.now().strftime('%Y-%m-%d %H:%M')},{cycle_readouts[0]},{cycle_readouts[1]},{cycle_readouts[2]},{cycle_readouts[3]}"
 

if __name__ == "__main__":
    image_filename = capture_image()

    try:
        cycle_crops = crop_cycles(image_filename)

        os.remove(image_filename)

        archetype_images = []
        for n in range(0,10,1):
            with Image.open(f'{data_path}/services/ocr_archetypes/archetype_{n}.png') as img:
                archetype_images.append(img.convert('L'))

        full_readout = do_ocr_on_cycles(cycle_crops)
        print(f"Full readout: {full_readout}.")

        daystamp = datetime.now().strftime('%Y-%m-%d')
        save_path = f'{data_path}/formatted/{daystamp}/'

        if not os.path.exists(save_path):
            os.makedirs(save_path)

        with open(f'{save_path}/heatmeter_readouts.csv', 'a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(full_readout.split(','))
    except Exception as e:
        print(f"Couldn't extract cycle readings due to {e}.")
    #cycle_crops = crop_cycles(image_filename)
#
    #archetype_images = []
    #for n in range(0,10,1):
    #    with Image.open(f'ocr_archetypes/archetype_{n}.png') as img:
    #        archetype_images.append(img.convert('L'))
#
    #full_readout = do_ocr_on_cycles(cycle_crops)
    #print(f"Full readout: {full_readout}.")
#
    #daystamp = datetime.now().strftime('%Y-%m-%d')
    #save_path = f'{data_path}/formatted/{daystamp}/'
#
    #if not os.path.exists(save_path):
    #    os.makedirs(save_path)
#
    #with open(f'{save_path}/heatmeter_readouts.csv', 'a', newline='') as file:
    #    writer = csv.writer(file)
    #    writer.writerow(full_readout.split(','))