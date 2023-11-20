from PIL import Image, ImageEnhance, ImageFilter, ImageDraw
import numpy as np
import copy
import os
from skimage import restoration, util

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

def min_position(np_array):
    """ Find the position of the first occurrence of the maximum value in the array """
    return np.argmin(np_array)

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

# Perform Hough Transform to detect lines
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

# Define a function to extract line segments from the accumulator
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

# Draw the lines on the image
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

    img = img.convert('L')
    img = image_grayscale_shifter(img)
    img = Image.fromarray((np.round(np.array(img)/255)*255).astype(np.uint8), mode='L')
    img = img.resize((round(height/4),round(width/4)))
    img = edge_detector(img)
    significant_points = [element * 4 for element in find_significant_points(img)]
    img = draw_points(oimg,significant_points,point_size=20)
    
    cycle_crops = []
    chars = []
    if 0<len(significant_points):
        reference_point = significant_points[np.argmax([np.linalg.norm(point) for point in significant_points])]

        crop_rectangles = [
            (reference_point[0]-288,reference_point[1]-819,reference_point[0]-238,reference_point[1]-789),
            (reference_point[0]-207,reference_point[1]-553,reference_point[0]-158,reference_point[1]-530),
            (reference_point[0]-192,reference_point[1]-349,reference_point[0]-144,reference_point[1]-327),
            (reference_point[0]-179,reference_point[1]-152,reference_point[0]-130,reference_point[1]-126)
        ]

        rotates = [4, 0, 0, -3]
        brightness1_factors = [3, 3, 3, 3]
        contrast1_factors = [5, 5, 5, 5]

        for cycle in range(1, 5):
            cycle_crop = oimg.crop(crop_rectangles[cycle - 1])
            width, height = cycle_crop.size
            zoom = 4
            cycle_crop = cycle_crop.resize((round(width*zoom), round(height*zoom)), Image.BICUBIC)

            cycle_crop = grayscale_with_channel_control(cycle_crop, 0.5, 0.5, 1)

            cycle_crop_np = np.array(cycle_crop)
            cycle_crop_np = restoration.denoise_nl_means(cycle_crop_np, patch_size=2, patch_distance=2, h=1)            
            cycle_crop = Image.fromarray(util.img_as_ubyte(cycle_crop_np))

            cycle_crop = cycle_crop.filter(ImageFilter.SHARPEN)

            enhancer = ImageEnhance.Contrast(cycle_crop)
            cycle_crop = enhancer.enhance(contrast1_factors[cycle - 1])
            enhancer = ImageEnhance.Brightness(cycle_crop)
            cycle_crop = enhancer.enhance(brightness1_factors[cycle - 1])

            cycle_crop = cycle_crop.rotate(rotates[cycle - 1], expand=True, fillcolor='white')
            cycle_crop = crop_to_aspect_ratio(cycle_crop,(2,1))

            thresholding_factor = np.mean(np.array(cycle_crop)[np.array(cycle_crop)<255*0.2])
            cycle_crop = Image.fromarray(util.img_as_ubyte(np.array(cycle_crop) > thresholding_factor))
            
            cycle_crops.append(cycle_crop)

            chars.append(slice_into_chars(cycle_crop))
            
    return img, cycle_crops, chars

if __name__ == "__main__":
    folder_path = 'C:/Users/Beno/Documents/SZAKI/kazankontroll-dashboard/heatmeter_images/2023_11_18'
    image_names = [file for file in os.listdir(folder_path) if file.lower().endswith('.jpg')]

    for image_name in image_names:
        with Image.open(os.path.join(folder_path, image_name)) as img:
            img, cycle_crops, chars = process_image(img)
            img.save(f"batch/{image_name[:-4]}_points.jpg")
            if len(cycle_crops) == 4:
                for cycle in range(1,5):
                    cycle_crops[cycle-1].save(f"batch/{image_name[:-4]}_cycle_{cycle}.jpg")
                    for char in range(1,5):
                        chars[cycle-1][char-1].save(f"batch/chars/{image_name[:-4]}_{cycle}_{char}.jpg")