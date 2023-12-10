import RPi.GPIO as GPIO
import time
from datetime import datetime
import os

# Get the absolute path of the current script
script_path = os.path.abspath(__file__)
script_dir = os.path.dirname(script_path)
project_root = os.path.abspath(os.path.join(script_dir, '..', '..'))
data_path = os.path.join(project_root, 'data')

# Define the GPIO pin number
pulse_pin = 17

# Setup the GPIO pin
GPIO.setmode(GPIO.BCM)  # Use the Broadcom pin numbering
GPIO.setup(pulse_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Pull-up resistor enabled

# Define the callback function to run when a signal is detected
def signal_detected(arg):
    daystamp = datetime.now().strftime('%Y-%m-%d')
    save_path = f'{data_path}/raw/{daystamp}/'
    if not os.path.exists(save_path):
        os.makedirs(save_path)
    with open(f"{save_path}gas_pulse_times.txt", "a") as file:
        # Write the current time to the file
        file.write(f"{datetime.now().strftime('%H:%M:%S.%f')}\n")
        print(f"Pulse detected at {datetime.now()}") 

# Add a falling edge detection on the pulse_pin, with a debounce time
GPIO.add_event_detect(pulse_pin, GPIO.FALLING, callback=signal_detected, bouncetime=10000)

try:
    # Main program loop
    while True:
        time.sleep(2.5)  # Sleep for 1 second to reduce CPU usage

except KeyboardInterrupt:
    # Clean up GPIO on CTRL+C exit
    GPIO.cleanup()

# Clean up GPIO on normal exit
GPIO.cleanup()
