import RPi.GPIO as GPIO
import paho.mqtt.client as mqtt
import json
import time

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

# MQTT settings
broker_address = "localhost"
device_name = "robot"

# Initialize GPIO
GPIO.setmode(GPIO.BCM)
for pin in inputs.values():
    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
for pin in outputs:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)

# MQTT callback functions
def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))
    client.subscribe(f"/{device_name}/command")

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
    client.publish(f"/{device_name}/data", json.dumps(sensor_status))

# MQTT client setup
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect(broker_address, 1883, 60)

try:
    client.loop_start()
    while True:
        # Check for input changes
        for pin_name, pin_number in inputs.items():
            if GPIO.input(pin_number):
                publish_sensor_status(client)
                break
        time.sleep(0.1)  # Adjust sleep time as needed
except KeyboardInterrupt:
    print("Interrupted")
    GPIO.cleanup()
    client.loop_stop()
