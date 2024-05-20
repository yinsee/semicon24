import RPi.GPIO as GPIO
import paho.mqtt.client as mqtt
import json
import time
from datetime import datetime, timedelta

# Define GPIO pins for inputs and outputs
inputs = {
    "pick_oven": 17,
    "put_oven": 18,
    "pick_desiccator": 22,
    "put_desiccator": 23
}

outputs = {
    "pick_oven": 2,
    "put_oven": 3,
    "pick_desiccator": 4,
    "put_desiccator": 5
}  # Assuming 4 output pins

# MQTT Settings
BROKER = 'localhost'
PORT = 1883
DEVICE_NAME = "robot"

# pick status
sensor_status = None
previous_status = None
pick_count = 0
last_pick_oven_state = GPIO.input(inputs["pick_oven"])
next_reset_time = datetime.now() + timedelta(hours=1)

# Initialize GPIO
GPIO.setmode(GPIO.BCM)
for pin in inputs.values():
    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
for pin in outputs.values():
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)

# MQTT callback functions
def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))
    client.subscribe(f"/{DEVICE_NAME}/command")

def on_message(client, userdata, msg):
    payload = msg.payload.decode('utf-8')
    print(f"Received message: {payload} on topic {msg.topic}")
    for pin_name, pin_number in outputs.items():
        GPIO.output(pin_number, GPIO.LOW if pin_name != payload else GPIO.HIGH)

# Function to publish sensor status
def publish_sensor_status(client):
    sensor_status = {}
    for pin_name, pin_number in inputs.items():
        sensor_status[pin_name] = GPIO.input(pin_number)
    sensor_status['pick_count'] = pick_count

    if sensor_status != previous_status:
        client.publish(f"/{DEVICE_NAME}/data", json.dumps(sensor_status))
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

        time.sleep(0.1)  # Adjust sleep time as needed

except KeyboardInterrupt:
    print("Exiting program")

finally:
    client.loop_stop()
    client.disconnect()
    GPIO.cleanup()
