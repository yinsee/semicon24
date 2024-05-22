import RPi.GPIO as GPIO
import paho.mqtt.client as mqtt
import json
import time
from datetime import datetime, timedelta

# Define GPIO pins for inputs and outputs
inputs = { #check state movement of the robot/ robot motion sequence
    "pick_oven": 2,# ROBOT PIN1
    "put_oven": 3,# ROBOT PIN2
    "pick_desiccator": 4,# ROBOT PIN3
    "put_desiccator": 17# ROBOT PIN4
}

outputs = {
    "pick_oven": 14,# ROBOT PIN4
    "put_oven": 15,# ROBOT PIN5
    "pick_desiccator": 18,# ROBOT PIN6
    "put_desiccator": 23,# ROBOT PIN7
}  # Assuming 4 output pins

# MQTT Settings
BROKER = 'localhost'
PORT = 1883
DEVICE_NAME = "robot"

# Initialize GPIO
START_STOP_SYS = 25# ROBOT PIN8
GPIO.setmode(GPIO.BCM)
for pin in inputs.values():
    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
for pin in outputs.values():
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)

GPIO.setup(START_STOP_SYS, GPIO.OUT)
GPIO.output(START_STOP_SYS, GPIO.HIGH)

# pick status
sensor_status = None
previous_status = None
pick_count = 0
last_pick_oven_state = GPIO.input(inputs["pick_oven"])
next_reset_time = datetime.now() + timedelta(hours=1)

# MQTT callback functions
def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))
    client.subscribe(f"/{DEVICE_NAME}/command")

def on_message(client, userdata, msg):
    payload = msg.payload.decode('utf-8')
    print(f"Received message: {payload} on topic {msg.topic}")
    if payload == "start":
        GPIO.output(START_STOP_SYS, GPIO.LOW)
    elif payload == "stop":
        GPIO.output(START_STOP_SYS, GPIO.HIGH)
    else:
        for pin_name, pin_number in outputs.items():
            GPIO.output(pin_number, GPIO.LOW if pin_name != payload else GPIO.HIGH)
        time.sleep(1)
        for pin_name, pin_number in outputs.items():
            GPIO.output(pin_number, GPIO.LOW)

# Function to publish sensor status
def publish_sensor_status(client):
    global sensor_status
    sensor_status = {}
    for pin_name, pin_number in inputs.items():
        sensor_status[pin_name] = GPIO.input(pin_number)
    sensor_status['pick_count'] = pick_count
    sensor_status['stop'] = GPIO.input(START_STOP_SYS)

    if sensor_status != previous_status:
        client.publish(f"/{DEVICE_NAME}/data", json.dumps(sensor_status), retain=True)
        print(f"Published sensor status: {sensor_status}")

# MQTT client setup
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect(BROKER, PORT, 60)
client.loop_start()

try:

    while True:

        # Check for input changes and reset the counter every hour
        current_time = datetime.now()
        if current_time >= next_reset_time:
            pick_count = 0
            next_reset_time = current_time + timedelta(hours=1)

        current_pick_oven_state = GPIO.input(inputs["pick_oven"])
        if last_pick_oven_state == GPIO.HIGH and current_pick_oven_state == GPIO.LOW:
            pick_count += 1

        last_pick_oven_state = current_pick_oven_state

        publish_sensor_status(client)
        previous_status = sensor_status

        time.sleep(0.5)  # Adjust sleep time as needed

except KeyboardInterrupt:
    print("Exiting program")

finally:
    client.loop_stop()
    client.disconnect()
    GPIO.cleanup()
