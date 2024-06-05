from datetime import datetime, timedelta
import os
import glob
from PIL import Image, ImageEnhance, ImageFilter
from io import BytesIO
import numpy as np
import random
import string
import cv2

# Set paths
script_path = os.path.abspath(__file__)
script_dir = os.path.dirname(script_path)
project_root = os.path.abspath(os.path.join(script_dir, '..', '..'))
data_path = os.path.join(project_root, 'data')

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

def extract_char_images(cycle_crop):
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

    char_imgs = slice_into_chars(cycle_crop)
    return char_imgs

def preprocess_image_for_training(image):
    target_size = (224,224)
    # Get original dimensions
    width, height = image.size
    
    # Determine the size to extend to (square dimension)
    new_size = max(width, height)
    
    # Create a new square image with a white background
    new_image = Image.new("RGB", (new_size, new_size), (255, 255, 255))
    
    # Paste the original image centered on the new square image
    new_image.paste(image, ((new_size - width) // 2, (new_size - height) // 2))
    
    # Resize the square image to the target size
    new_image = new_image.resize(target_size, Image.LANCZOS)
    
    return new_image

def generate_random_filename(length=12):
    characters = string.ascii_letters + string.digits
    random_filename = ''.join(random.choice(characters) for _ in range(length))
    return random_filename

if __name__ == "__main__":
    training_set_path = os.path.join(script_dir, 'training_set_2')
    
    #start_day = datetime(2023, 12, 1)
    #end_day = datetime(2023, 12, 1)
    start_day = datetime(2023, 12, 10)
    end_day = datetime(2023, 12, 10)
    day = start_day
    
    while day <= end_day:
        pattern = os.path.join(data_path,'raw\\',f"{day.strftime('%Y-%m-%d')}\\", '*heatmeter_images\\[0-9][0-9][0-9][0-9]_*.png')

        timestamps = []
        for image_path in glob.glob(pattern):
            if image_path[-10:-6] not in timestamps:
                timestamps.append(image_path[-10:-6])
        
        ocr_net_results_data = np.load(os.path.join(data_path,"raw\\",day.strftime("%Y-%m-%d"),'heatmeter_images\\ocr_net_results.npz'))
        ocr_net_results = ocr_net_results_data['array']

        batch_images_list = []
        for i in range(len(timestamps)):
            timestamp = timestamps[i]
            inference_time = datetime(year=day.year, month=day.month, day=day.day, hour=datetime.strptime(timestamp,"%H%M").hour, minute=datetime.strptime(timestamp,"%H%M").minute)
            ocr_net_probs = ocr_net_results[i]
            for cycle in range(1,5):
                hour = inference_time.hour
                if len(str(hour)) == 1:
                    hour = "0"+str(hour)
                minute = inference_time.minute
                if len(str(minute)) == 1:
                    minute = "0"+str(minute)
                cycle_crop_path = os.path.join(data_path,"raw\\",inference_time.strftime("%Y-%m-%d"),'heatmeter_images\\',f'{hour}{minute}_{cycle}.png')
                with Image.open(cycle_crop_path) as img:
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    jpg_image_io = BytesIO()
                    img.save(jpg_image_io, 'JPEG')
                    cycle_crop = Image.open(jpg_image_io)
                char_imgs = extract_char_images(cycle_crop)
                for char in range(0,4):
                    predicted_class = np.argmax(ocr_net_probs[cycle - 1][char])
                    predicted_prob = ocr_net_probs[cycle - 1][char][predicted_class]
                    filename = generate_random_filename()
                    if False: #predicted_prob > 0.7: #
                        label = ['0','1','2','3','4','5','6','7','8','9','na'][predicted_class]
                        save_dir = os.path.join(training_set_path, label)
                        if not os.path.exists(save_dir):
                            os.makedirs(save_dir)
                        preprocess_image_for_training(char_imgs[char]).save(os.path.join(save_dir, f'{filename}.png'))
                    elif 0.7 > predicted_prob:#False:
                        window_label = f'{predicted_class} with {predicted_prob}'
                        # Convert PIL image to OpenCV format
                        open_cv_image = cv2.cvtColor(np.array(char_imgs[char]), cv2.COLOR_RGB2BGR)

                        # Create a blank canvas larger than the image
                        canvas_height, canvas_width = 200, 200  # Desired window size
                        canvas = np.zeros((canvas_height, canvas_width, 3), dtype=np.uint8)

                        # Get the dimensions of the image
                        img_height, img_width, _ = open_cv_image.shape

                        # Calculate the position to center the image on the canvas
                        x_offset = (canvas_width - img_width) // 2
                        y_offset = (canvas_height - img_height) // 2

                        # Place the image on the canvas
                        canvas[y_offset:y_offset+img_height, x_offset:x_offset+img_width] = open_cv_image

                        # Create a named window with WINDOW_NORMAL flag
                        cv2.namedWindow(window_label, cv2.WINDOW_NORMAL)

                        # Move the window to the desired position (x=100, y=100 for example)
                        cv2.moveWindow(window_label, 1000, 500)

                        # Display the canvas in the window
                        cv2.imshow(window_label, canvas)
                        
                        # Wait for user input
                        user_class = ""
                        while True:
                            key = cv2.waitKey(0) & 0xFF
                            if key == 13:  # Enter key
                                break
                            elif key in range(48, 58):  # Digits 0-9
                                user_class = chr(key)
                                break
                        # Close the window
                        cv2.destroyAllWindows()
                        
                        label = "na" if user_class == "" else user_class
                        save_dir = os.path.join(training_set_path, label)
                        if not os.path.exists(save_dir):
                            os.makedirs(save_dir)
                        preprocess_image_for_training(char_imgs[char]).save(os.path.join(save_dir, f'{filename}.png'))
        day = day + timedelta(days = 1)
