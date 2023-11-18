import pygame
import pygame.camera
from pygame.locals import *
import time
import os
import argparse
from datetime import datetime

def startup():
    # Initialize Pygame and the camera
    pygame.init()
    pygame.camera.init()

    # Set the index of your webcam
    cam_index = 0  # typically 0, or 1 if you have multiple webcams
    # Get a list of available cameras
    camlist = pygame.camera.list_cameras()
    if not camlist:
        raise ValueError("Sorry, no cameras detected.")
    
    cam = pygame.camera.Camera(camlist[cam_index])
    # Start the camera
    cam.start()

    modes = cam.get_size()
    if not modes:
        raise ValueError("Camera doesn't support any modes.")
    
    # Recreate the Camera object with the maximum resolution
    cam = pygame.camera.Camera(camlist[cam_index], modes)
    cam.start()
    
    return cam

# Function to capture images for a set duration
def capture_images(capture_duration,capture_frequency, cam):
    try:
        start_time = time.time()
        current_date = time.strftime("%Y_%m_%d")
        save_path = f'heatmeter_images/{current_date}/'
        if not os.path.exists(save_path):
            os.makedirs(save_path)

        while time.time() - start_time < capture_duration:
            # Capture an image
            img = cam.get_image()

            # Save the image to disk
            now = datetime.now()
            timestamp = time.strftime("%Y%m%d-%H%M%S") + f"{now.microsecond // 1000:03d}"
            pygame.image.save(img, f'{save_path}{timestamp}.jpg')
            print(f'Captured image.')

            # Wait for the next capture
            time.sleep(capture_frequency)

    except KeyboardInterrupt:
        # If interrupted, stop the camera before exiting
        cam.stop()
        pygame.quit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Capture images from a webcam.')
    parser.add_argument('duration', type=float, help='Capture duration in seconds')
    parser.add_argument('frequency', type=float, help='Capture frequency in seconds')

    args = parser.parse_args()
    cam = startup()
    capture_images(args.duration, args.frequency, cam)