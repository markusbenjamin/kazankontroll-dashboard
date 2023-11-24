import time
import os
import argparse
from datetime import datetime
import subprocess

# Get the absolute path of the current script
script_path = os.path.abspath(__file__)
script_dir = os.path.dirname(script_path)
project_root = os.path.abspath(os.path.join(script_dir, '..', '..'))
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

        # Wait for the next capture
        time.sleep(capture_frequency)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Capture images from a webcam.')
    parser.add_argument('duration', type=float, help='Capture duration in seconds')
    parser.add_argument('frequency', type=float, help='Capture frequency in seconds')

    args = parser.parse_args()
    capture_images(args.duration, args.frequency)
