from PIL import Image, ImageEnhance, ImageFilter, ImageDraw
import numpy as np
import copy
import os
from skimage import restoration, util
from scipy.ndimage import zoom
from datetime import datetime
import csv


script_path = os.path.abspath(__file__)
script_dir = os.path.dirname(script_path)
project_root = os.path.abspath(os.path.join(script_dir, '..', '..'))
data_path = os.path.join(project_root, 'data')

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

def map_to_zero_and_one(np_array):
    """ Normalize a NumPy array to have values between 0 and 1 """
    min_val = np.min(np_array)
    max_val = np.max(np_array)
    range_val = max_val - min_val
    return (np_array - min_val) / range_val if range_val != 0 else np_array

def image_grayscale_shifter(img):
    img_vector = np.array(img)/255

    gradient1 = []
    gradient2 = []
    factor_start = -1
    factor_step = 0.05
    factor_end = 1
    for factor in np.arange(factor_start,factor_end,factor_step):
        gradient1.append(np.sum(map_to_zero_and_one(np.clip(img_vector + factor+factor_step,0,1))) - np.sum(map_to_zero_and_one(np.clip(img_vector + factor,0,1))))
        gradient2.append(np.sum(np.round(img_vector + factor+factor_step)) - np.sum(np.round(img_vector + factor)))

    min_pos = max([
        [np.argmin(gradient1)],
        [np.argmin(gradient2)]
    ])
    factor = np.arange(factor_start,factor_end,factor_step)[min_pos]

    shifted_img_vector = map_to_zero_and_one(np.clip(img_vector + factor,0,1))

    shifted_img = Image.fromarray((shifted_img_vector*255).astype(np.uint8), mode='L')

    return shifted_img

def edge_detector(image):
    # Convert Pillow image to NumPy array and convert to grayscale
    img_array = np.array(image.convert('L'))

    # Use np.gradient to find the gradients
    gradient_y, gradient_x = np.gradient(img_array.astype(float))

    # Compute the magnitude of the gradients
    magnitude = np.sqrt(gradient_x**2 + gradient_y**2)

    # Normalize and convert back to uint8
    magnitude = (magnitude / magnitude.max()) * 255
    magnitude = magnitude.astype(np.uint8)

    # Convert back to PIL Image
    edge_image = Image.fromarray(magnitude)

    return edge_image

def hough_line_detection(binary_img, theta_min, theta_max, theta_res, rho_res):
    thetas = np.deg2rad(np.arange(theta_min, theta_max, theta_res))
    # Rho ranges from the diagonal length of the image in negative to positive
    width, height = binary_img.shape
    diag_len = int(np.ceil(np.sqrt(width**2 + height**2)))
    rhos = np.linspace(-diag_len, diag_len, int(2 * diag_len / rho_res) + 1)

    # Cache some reusable values
    cos_t = np.cos(thetas)
    sin_t = np.sin(thetas)
    num_thetas = len(thetas)

    # Hough accumulator array of theta vs rho
    accumulator = np.zeros((len(rhos), num_thetas), dtype=np.uint64)
    y_idxs, x_idxs = np.nonzero(binary_img)  # (row, col) indexes to edges

    # Vote in the hough accumulator
    for i in range(len(x_idxs)):
        x = x_idxs[i]
        y = y_idxs[i]

        for t_idx in range(num_thetas):
            # Calculate rho. diag_len is added for a positive index
            rho_val = x * cos_t[t_idx] + y * sin_t[t_idx]
            rho_idx = int(round((rho_val + diag_len) / rho_res))
            accumulator[rho_idx, t_idx] += 1

    return accumulator, thetas, rhos

def find_lines(img, thresholding, theta_min, theta_max, theta_res, rho_res, detections_threshold):
    binary_image = np.array(img) > 255*thresholding
    accumulator, thetas, rhos = hough_line_detection(binary_image,theta_min, theta_max, theta_res, rho_res)
    line_endpoints = []
    for rho_idx in range(accumulator.shape[0]):
        for theta_idx in range(accumulator.shape[1]):
            if accumulator[rho_idx, theta_idx] > detections_threshold:
                rho = rhos[rho_idx]
                theta = thetas[theta_idx]
                a = np.cos(theta)
                b = np.sin(theta)
                x0 = a * rho
                y0 = b * rho
                x1 = int(x0 + 1000 * (-b))
                y1 = int(y0 + 1000 * (a))
                x2 = int(x0 - 1000 * (-b))
                y2 = int(y0 - 1000 * (a))
                line_endpoints.append(((x1, y1), (x2, y2)))
    return line_endpoints

def find_intersection(line1, line2):
    # Each line is represented as ((x1, y1), (x2, y2))
    (x1, y1), (x2, y2) = line1
    (x3, y3), (x4, y4) = line2

    # Calculate the slopes (m1, m2) and y-intercepts (c1, c2) of the lines
    m1 = (y2 - y1) / float(x2 - x1) if x2 != x1 else float('inf')
    m2 = (y4 - y3) / float(x4 - x3) if x4 != x3 else float('inf')
    c1 = y1 - m1 * x1
    c2 = y3 - m2 * x3

    # If the slopes are equal, the lines are parallel (or coincident)
    if m1 == m2:
        return None

    # Find the intersection point
    x_intersect = (c2 - c1) / float(m1 - m2)
    y_intersect = m1 * x_intersect + c1

    return (x_intersect, y_intersect)

def draw_lines(image, lines):
    draw = ImageDraw.Draw(image)
    for line in lines:
        draw.line(line, fill=255, width=2)
    return image

def draw_points(image, points, point_size=5):
    draw = ImageDraw.Draw(image)
    for point in points:
        x, y = point
        bounding_box = [x - point_size // 2, y - point_size // 2, x + point_size // 2, y + point_size // 2]
        draw.ellipse(bounding_box, fill=255)
    return image

def find_significant_points(img):
    width, height = img.size
    h_lines = find_lines(copy.deepcopy(img), 0.5, 80, 100, 1, 1, 40)
    v_lines = find_lines(copy.deepcopy(img), 0.5, -10, 10, 1, 1, 58)
    #draw_lines(draw_lines(copy.deepcopy(img), v_lines),h_lines).save("detected_lines.jpg")
    intersects = []
    for line1 in v_lines:
        for line2 in h_lines:
            intersects.append(np.round(find_intersection(line1,line2)))

    x_res, y_res = round(width/20), round(height/20)  # Change these values as needed

    # List to hold average positions
    averaged_intersects = []

    # Iterate over the image with the set resolution
    for y in range(0, height, y_res):
        for x in range(0, width, x_res):
            # Collect points that lie within the current section
            section_points = [point for point in intersects if x <= point[0] < x + x_res and y <= point[1] < y + y_res]

            # Calculate the average position of points in the section, if any
            if section_points:
                avg_position = np.round(np.mean(section_points, axis=0))
                averaged_intersects.append(avg_position)
    
    return averaged_intersects

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

def process_image(img):
    width, height = img.size
    img = img.transpose(Image.ROTATE_90)
    oimg = copy.deepcopy(img)

    #img = img.convert('L')
    #img = image_grayscale_shifter(img)
    #img = Image.fromarray((np.round(np.array(img)/255)*255).astype(np.uint8), mode='L')
    #img = img.resize((round(height/4),round(width/4)))
    #img = edge_detector(img)
    #significant_points = [element * 4 for element in find_significant_points(img)]
    #img = draw_points(oimg,significant_points,point_size=20)
    
    cycle_crops = []
    chars = []
    crop_rectangles = [
        (182,385,215,401),
        (185,536,218,552),
        (184,685,218,702),
        (176,234,210,249)
    ]

    rotates = [0, 0, 3, 0]
    brightness1_factors = [1.25, 1.25, 1.25, 1.25]
    contrast1_factors = [2, 2, 2, 2]
    contrast2_factors = [4, 4, 4, 4]

    for cycle in range(1, 5):
        cycle_crop = oimg.crop(crop_rectangles[cycle - 1])
        width, height = cycle_crop.size
        zoom = 4
        cycle_crop = cycle_crop.resize((round(width*zoom), round(height*zoom)), Image.BICUBIC)

        cycle_crop = grayscale_with_channel_control(cycle_crop, 1, 1, 1)

        cycle_crop_np = np.array(cycle_crop)
        cycle_crop_np = restoration.denoise_nl_means(cycle_crop_np, patch_size=2, patch_distance=2, h=1)            
        cycle_crop = Image.fromarray(util.img_as_ubyte(cycle_crop_np))
        
        cycle_crop = cycle_crop.filter(ImageFilter.SHARPEN).filter(ImageFilter.SHARPEN).filter(ImageFilter.SHARPEN)

        cycle_crop_np = np.array(cycle_crop)
        cycle_crop_np = restoration.denoise_nl_means(cycle_crop_np, patch_size=2, patch_distance=2, h=1)    
        cycle_crop_np = map_to_zero_and_one(cycle_crop_np)        
        cycle_crop = Image.fromarray(util.img_as_ubyte(cycle_crop_np))
        
        enhancer = ImageEnhance.Contrast(cycle_crop)
        cycle_crop = enhancer.enhance(contrast1_factors[cycle - 1])
        enhancer = ImageEnhance.Brightness(cycle_crop)
        cycle_crop = enhancer.enhance(brightness1_factors[cycle - 1])

        if rotates[cycle - 1] != 0:
            cycle_crop = cycle_crop.rotate(rotates[cycle - 1], expand=True, fillcolor='white')
            cycle_crop = crop_to_aspect_ratio(cycle_crop,(2,1))

        #thresholding_factor = np.mean(np.array(cycle_crop)[np.array(cycle_crop)<255*0.9])
        #cycle_crop = Image.fromarray(util.img_as_ubyte(np.array(cycle_crop) > thresholding_factor))
        
        cycle_crop_np = np.array(cycle_crop)
        cycle_crop_np = map_to_zero_and_one(cycle_crop_np)        
        cycle_crop = Image.fromarray(util.img_as_ubyte(cycle_crop_np))

        enhancer = ImageEnhance.Contrast(cycle_crop)
        cycle_crop = enhancer.enhance(contrast2_factors[cycle - 1])
        #enhancer = ImageEnhance.Brightness(cycle_crop)
        #cycle_crop = enhancer.enhance(brightness1_factors[cycle - 1])
        
        cycle_crops.append(cycle_crop)

        chars.append(slice_into_chars(cycle_crop))
            
    return img, cycle_crops, chars

def shift_array(array, shift_x_ratio, shift_y_ratio, fill_value=255):
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

def zoom_array(array, pad_ratio, fill_value=255):
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

def seven_segment_ocr(unknown_vector_2D,archetype_vectors_2D, da1_threshold = 0.03, total_da_threshold = 0.18, h_shift_min=0,h_shift_max=0.25,h_shift_step=0.05,v_shift_min=-0.1,v_shift_max=0.1,v_shift_step=0.05,zoom_min=0.05,zoom_max=0.25,zoom_step=0.05):
    resized_archetype_vectors_2D = []
    archetype_dimensions = archetype_vectors_2D[0].shape
    unknown_dimensions = unknown_vector_2D.shape
    for archetype_vector_2D in archetype_vectors_2D:
        resized_archetype_vectors_2D.append(zoom(archetype_vector_2D, (unknown_dimensions[0] / archetype_dimensions[0], unknown_dimensions[1] / archetype_dimensions[1])))
    
    activations = []
    counter = 0
    iter_num = 10*len(list(np.arange(h_shift_min, h_shift_max+h_shift_step, h_shift_step)))*len(list(np.arange(v_shift_min, v_shift_max+v_shift_step, v_shift_step)))*len(list(np.arange(zoom_min, zoom_max+zoom_step, zoom_step)))
    for h_shift in np.arange(h_shift_min,h_shift_max+h_shift_step,h_shift_step):
        for v_shift in np.arange(v_shift_min,v_shift_max+v_shift_step,v_shift_step):
            for zoom_level in np.arange(zoom_min,zoom_max+zoom_step,zoom_step):
                activation = {}
                for num in np.arange(0,10,1):
                    archetype_vector = 1 - (shift_array(zoom_array(copy.deepcopy(resized_archetype_vectors_2D[num]), zoom_level),h_shift,v_shift).flatten())/255
                    unknown_vector = 1 - unknown_vector_2D.flatten()/255
                    activation[num] = np.dot(archetype_vector,unknown_vector)/np.mean([np.sum(archetype_vector),np.sum(unknown_vector)])
                    counter += 1
                    progress = round(20*counter/iter_num)
                    progress_bar = "|"+"-"*progress+" "*(20-progress)+"|"
                    print(f"\r{progress_bar}", end="")
                activations.append(activation)


    def activation_checks(activation_as_array):
        gradient = abs(np.diff(np.sort(activation_as_array)))
        if total_da_threshold < sum(gradient) and da1_threshold < gradient[-1]:
            return True
        else:
            return False

    passed_activations = [activation for activation in activations if activation_checks(np.array(list(activation.values())))]

    predictions = []
    for activation in passed_activations:
        predictions.append(np.argmax(list(activation.values())))

    if 0<len(predictions):
        prediction = max(predictions, key=predictions.count)
    else:
        prediction = -1

    print(f"\t--> {prediction}")

    return prediction

if __name__ == "__main__":
    folder_path = 'unprocessed heatmeter images'
    image_names = [file for file in os.listdir(folder_path) if file.lower().endswith('.jpg')]

    archetype_vectors_2D = []
    for n in np.arange(0,10,1):
        with Image.open(f'archetypes/archetype_{n}.png') as img:
            archetype_vectors_2D.append(np.array(img.convert('L')))

    for image_name in image_names:
        with Image.open(os.path.join(folder_path, image_name)) as img:
            timestamp = datetime.strptime(image_name[0:-4:], "%Y%m%d-%H%M%S")
            img, cycle_crops, chars = process_image(img)
            if len(cycle_crops) == 4:
                cycle_readouts = []
                for cycle in range(1,5):
                    cycle_readout = ''
                    for char in range(1,5):
                        unknown_vector_2D = np.array(chars[cycle-1][char-1])
                        prediction = seven_segment_ocr(unknown_vector_2D,archetype_vectors_2D, da1_threshold = 0.03, total_da_threshold = 0.18)
                        cycle_readout += str(prediction)
                    cycle_readouts.append(cycle_readout)
            readout = f"{timestamp.strftime('%Y.%m.%d %H:%M:%S')},{cycle_readouts[0]},{cycle_readouts[1]},{cycle_readouts[2]},{cycle_readouts[3]}"
    
            print(readout)
            with open('heatmeter_readouts.csv', 'a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(readout.split(','))