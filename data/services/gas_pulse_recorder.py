# Simple Python script to detect the state of a relay connected to a Raspberry Pi GPIO pin

import RPi.GPIO as GPIO
import time
from datetime import datetime
import os

# Get the absolute path of the current script
script_path = os.path.abspath(__file__)
script_dir = os.path.dirname(script_path)
project_root = os.path.abspath(os.path.join(script_dir, '..', '..'))
data_path = os.path.join(project_root, 'data')

# Set up GPIO using BCM numbering
GPIO.setmode(GPIO.BCM)

# Define the GPIO pin number connected to the relay circuit
relay_pin = 17  # Replace with your actual GPIO pin number

# Set up the GPIO pin as an input with a pull-down resistor
GPIO.setup(relay_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

def record_relay_state():
    try:
        while True:
            # Read the state of the relay
            state = GPIO.input(relay_pin)
            write_relay_state(state)
            # Print "CLOSED" if the circuit is closed, "OPEN" otherwise
            print("CLOSED" if state else "OPEN")

            if state == True and prev_state == False:
                write_pulse_time()

            # Wait for a short period before reading the state again
            prev_state = state
            time.sleep(5)

    except KeyboardInterrupt:
        # Clean up GPIO on CTRL+C exit
        GPIO.cleanup()

def write_relay_state(state):
    daystamp = datetime.now().strftime('%Y-%m-%d')
    save_path = f'{data_path}/raw/{daystamp}/'
    if not os.path.exists(save_path):
        os.makedirs(save_path)
    with open(f"{save_path}gas_relay_state.txt", "a") as file:
        # Write the current time to the file
        file.write(f"{datetime.now().strftime('%H:%M:%S.%f')},{1 if state else 0}\n")

def write_pulse_time():
    daystamp = datetime.now().strftime('%Y-%m-%d')
    save_path = f'{data_path}/raw/{daystamp}/'
    if not os.path.exists(save_path):
        os.makedirs(save_path)
    with open(f"{save_path}gas_pulse_times.txt", "a") as file:
        # Write the current time to the file
        file.write(f"{datetime.now().strftime('%H:%M:%S.%f')}\n")


if __name__ == "__main__":
    record_relay_state()