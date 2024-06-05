from datetime import datetime, timedelta
import os
import glob
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
from io import BytesIO
import numpy as np
import tensorflow as tf
from keras.layers import TFSMLayer
from keras import Input, Model

# Define the input shape (modify according to your input shape)
input_shape = (224, 224, 3)  # Replace with the shape of your preprocessed image

# Create an input layer
inputs = Input(shape=input_shape)

# Set the number of threads for parallelism
num_threads = 6  # Number of CPU cores

os.environ['TF_NUM_INTEROP_THREADS'] = str(num_threads)
os.environ['TF_NUM_INTRAOP_THREADS'] = str(num_threads)

# Optionally, you can set these in the TensorFlow configuration
tf.config.threading.set_inter_op_parallelism_threads(num_threads)
tf.config.threading.set_intra_op_parallelism_threads(num_threads)

# Load the model using TFSMLayer
model_layer = TFSMLayer('models/second/model.savedmodel', call_endpoint='serving_default')(inputs)

# Create the model
model = Model(inputs=inputs, outputs=model_layer)

# Load the labels
with open('models/second/labels.txt', 'r') as f:
    labels = f.read().splitlines()

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

def prepare_image_for_model_prediction(image):
    """
    Converts a 224x224 PIL image to a NumPy array suitable for model prediction.

    Parameters:
    image (PIL.Image): The input image to preprocess.

    Returns:
    numpy.ndarray: The processed image ready for model prediction.
    """
    # Convert the image to a NumPy array
    img_array = np.array(image).astype('float32') / 255.0
    
    # Ensure the image has the shape (224, 224, 3)
    if img_array.shape != (224, 224, 3):
        raise ValueError(f"Expected image shape (224, 224, 3), but got {img_array.shape}")
    
    # Add batch dimension
    img_array = np.expand_dims(img_array, axis=0)  # Shape: (1, 224, 224, 3)
    
    return img_array

def preprocess_training_set():
    # Define the source and destination directories
    source_dir = 'input/training_set'
    destination_dir = 'input/training_set_preprocessed'

    # Iterate through the directory structure
    for root, dirs, files in os.walk(source_dir):
        # Create corresponding directories in the destination
        for dir in dirs:
            os.makedirs(os.path.join(destination_dir, os.path.relpath(os.path.join(root, dir), source_dir)), exist_ok=True)
        
        # Process and save each image
        for file in files:
            if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                img_path = os.path.join(root, file)
                img = Image.open(img_path)
                processed_img = preprocess_image_for_training(img)
                
                # Determine the save path
                relative_path = os.path.relpath(root, source_dir)
                save_path = os.path.join(destination_dir, relative_path, file)
                
                # Save the processed image
                processed_img.save(save_path)

if __name__ == "__main__":
    start_day = datetime(2023, 11, 21)
    end_day = datetime(2024, 3, 28)
    day = start_day
    
    while day <= end_day:
        pattern = os.path.join(data_path,'raw\\',f"{day.strftime('%Y-%m-%d')}\\", '*heatmeter_images\\[0-9][0-9][0-9][0-9]_*.png')

        timestamps = []
        for image_path in glob.glob(pattern):
            if image_path[-10:-6] not in timestamps:
                timestamps.append(image_path[-10:-6])
        #timestamps = timestamps[0:2]

        batch_images_list = []
        for timestamp in timestamps:
            inference_time = datetime(year=day.year, month=day.month, day=day.day, hour=datetime.strptime(timestamp,"%H%M").hour, minute=datetime.strptime(timestamp,"%H%M").minute)
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
                batch_images_list.append([prepare_image_for_model_prediction(preprocess_image_for_training(char_img))[0] for char_img in char_imgs])
        
        print("Predict "+inference_time.strftime("%Y-%m-%d"))
        batch_images = np.concatenate(batch_images_list, axis=0)
        predictions = model.predict(batch_images)['sequential_18'].reshape((len(timestamps),4,4,11))
        np.savez_compressed(os.path.join(data_path,"raw\\",inference_time.strftime("%Y-%m-%d"),'heatmeter_images\\ocr_net_results.npz'), array=predictions)
        
        day = day + timedelta(days = 1)