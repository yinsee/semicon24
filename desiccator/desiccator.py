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
LIMIT_SWITCH_PINS = [11, 5, 6, 13]
CYLINDER_TOP_PIN = 27
CYLINDER_BOTTOM_PIN = 10
CYLINDER_EXTEND_PIN = 4
CYLINDER_RETRACT_PIN = 17
DHT_SENSOR_PIN = 9  # The GPIO pin connected to the DHT sensor
GAS_PIN = 2
ALARM_PIN = 3
CURTAIN_PIN = 22

# DHT Sensor Type
DHT_SENSOR = Adafruit_DHT.DHT22  # Change to Adafruit_DHT.DHT11 if using DHT11

previous_status = None
sensor_status = None
temperature = None
humidity = None

# Initial GPIO setup
GPIO.setmode(GPIO.BCM)
for pin in LIMIT_SWITCH_PINS + [CYLINDER_TOP_PIN, CYLINDER_BOTTOM_PIN, CURTAIN_PIN]:
    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

for pin in [CYLINDER_EXTEND_PIN, CYLINDER_RETRACT_PIN, ALARM_PIN, GAS_PIN]:
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
    global sensor_status, humidity, temperature

    # Read DHT sensor data
    humidity, temperature = Adafruit_DHT.read(DHT_SENSOR, DHT_SENSOR_PIN)

    try:
        if humidity is None or temperature is None:
            temperature = previous_status['temperature']
            humidity = previous_status['humidity']
    except:
        pass

    sensor_status = {
        "limit_switches": [GPIO.input(pin) for pin in LIMIT_SWITCH_PINS],
        "cylinder_top": GPIO.input(CYLINDER_TOP_PIN),
        "cylinder_bottom": GPIO.input(CYLINDER_BOTTOM_PIN),
        "safety_curtain": GPIO.input(CURTAIN_PIN),
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

        GPIO.output(ALARM_PIN, GPIO.LOW)

        if GPIO.input(CURTAIN_PIN) == GPIO.LOW:
            GPIO.output(ALARM_PIN, GPIO.HIGH)

        # check temperature and turn on alarm if needed
        if temperature is not None:
            if temperature > 30:
                GPIO.output(ALARM_PIN, GPIO.HIGH)

        # check humidity and pump gas if needed
        if humidity is not None:
            if humidity > 20:
                GPIO.output(GAS_PIN, GPIO.HIGH)

            if humidity > 80:
                GPIO.output(ALARM_PIN, GPIO.HIGH)

        publish_sensor_status(client)
        previous_status = sensor_status

        time.sleep(0.2)

except KeyboardInterrupt:
    print("Exiting program")

finally:
    client.loop_stop()
    client.disconnect()
    GPIO.cleanup()
