import paho.mqtt.client as mqtt
import RPi.GPIO as GPIO
import Adafruit_DHT
import time
import json

# MQTT Settings
BROKER = '192.168.0.42'
PORT = 1883
DEVICE_NAME = 'desiccator'
COMMAND_TOPIC = f'/{DEVICE_NAME}/command'
DATA_TOPIC = f'/{DEVICE_NAME}/data'

# GPIO Pins
LIMIT_SWITCH_PINS = [17, 27, 22, 23]
CYLINDER_TOP_PIN = 24
CYLINDER_BOTTOM_PIN = 25
CYLINDER_EXTEND_PIN = 5
CYLINDER_RETRACT_PIN = 6
DHT_SENSOR_PIN = 9  # The GPIO pin connected to the DHT sensor

# DHT Sensor Type
DHT_SENSOR = Adafruit_DHT.DHT22  # Change to Adafruit_DHT.DHT11 if using DHT11

previous_status = {
    "limit_switches": [0,0,0,0],
    "cylinder_top": 0,
    "cylinder_bottom": 0,
    "temperature": 0,
    "humidity": 0
}
sensor_status = previous_status

# Initial GPIO setup
GPIO.setmode(GPIO.BCM)
for pin in LIMIT_SWITCH_PINS + [CYLINDER_TOP_PIN, CYLINDER_BOTTOM_PIN]:
    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

for pin in [CYLINDER_EXTEND_PIN, CYLINDER_RETRACT_PIN]:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)

# MQTT callbacks
def on_connect(client, userdata, flags, rc):
    print(f"Connected with result code {rc}")
    client.subscribe(COMMAND_TOPIC)

def on_message(client, userdata, msg):
    payload = msg.payload.decode('utf-8')
    print(f"Received message: {payload} on topic {msg.topic}")
    if payload == 'close':
        GPIO.output(CYLINDER_EXTEND_PIN, GPIO.HIGH)
        GPIO.output(CYLINDER_RETRACT_PIN, GPIO.LOW)
    elif payload == 'open':
        GPIO.output(CYLINDER_EXTEND_PIN, GPIO.LOW)
        GPIO.output(CYLINDER_RETRACT_PIN, GPIO.HIGH)
    else:
        print("Unknown command")

def publish_sensor_status(client):
    global sensor_status

    # Read DHT sensor data
    humidity, temperature = Adafruit_DHT.read(DHT_SENSOR, DHT_SENSOR_PIN)

    if humidity is None or temperature is None:
        temperature = previous_status['temperature']
        humidity = previous_status['humidity']

    sensor_status = {
        "limit_switches": [GPIO.input(pin) for pin in LIMIT_SWITCH_PINS],
        "cylinder_top": GPIO.input(CYLINDER_TOP_PIN),
        "cylinder_bottom": GPIO.input(CYLINDER_BOTTOM_PIN),
        "temperature": temperature,
        "humidity": humidity
    }

    if sensor_status != previous_status:
        client.publish(DATA_TOPIC, json.dumps(sensor_status), retain=True)
        print(f"Published sensor status: {sensor_status}")

# MQTT client setup
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect(BROKER, PORT, 60)
client.loop_start()

# Main loop
try:
    while True:

        publish_sensor_status(client)
        previous_status = sensor_status

        time.sleep(0.5)

except KeyboardInterrupt:
    print("Exiting program")

finally:
    client.loop_stop()
    client.disconnect()
    GPIO.cleanup()
