import time
import os
import argparse
from datetime import datetime
import subprocess
from PIL import Image, ImageEnhance, ImageFilter, ImageDraw

script_path = os.path.abspath(__file__)

# Get the directory of the current script
script_dir = os.path.dirname(script_path)

# Navigate to the project root from the current script directory (go two levels up)
project_root = os.path.abspath(os.path.join(script_dir, '..', '..'))

# Construct the path to the data/raw directory
data_raw_path = os.path.join(project_root, 'data', 'raw')

# Function to capture images for a set duration
def capture_images(capture_duration, capture_frequency):
    start_time = time.time()
    current_date = time.strftime("%Y_%m_%d")
    save_path = f'{data_raw_path}/heatmeter_images/{current_date}/'
    if not os.path.exists(save_path):
        os.makedirs(save_path)

    while time.time() - start_time < capture_duration:
        now = datetime.now()
        timestamp = now.strftime("%Y%m%d-%H%M%S")
        image_filename = f'{save_path}{timestamp}.jpg'

        # Capture an image using fswebcam
        subprocess.run(['fswebcam', '-r', '1280x720', '--no-banner', image_filename])
        print(f'Captured image {image_filename}.')

        # crop_cycles(image_filename)

        # Wait for the next capture
        time.sleep(capture_frequency)

def crop_cycles(img_path):
    crop_rectangles = [
        (182,385,215,401),
        (185,536,218,552),
        (184,685,218,702),
        (176,234,210,249)
    ]

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

                print(f"\tCycle {cycle} successfully cropped.")
            except Exception as e:
                print(f"\tCouldn't crop cycle {cycle} due to {e}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Capture images from a webcam.')
    parser.add_argument('duration', type=float, help='Capture duration in seconds')
    parser.add_argument('frequency', type=float, help='Capture frequency in seconds')

    args = parser.parse_args()
    capture_images(args.duration, args.frequency)
